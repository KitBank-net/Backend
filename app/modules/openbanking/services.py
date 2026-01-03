"""
Open Banking Gateway - Service Layer

Implements business logic for consent management, OAuth2 provider,
third-party app management, and OBP-compatible data transformations.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from passlib.context import CryptContext

from app.core.config import settings
from app.modules.openbanking.models import (
    ThirdPartyApp, Consent, OAuthToken, APIRequestLog, SandboxUser,
    ConsentStatus, ConsentType, AppStatus, TokenType, GrantType
)
from app.modules.openbanking.schemas import (
    ThirdPartyAppCreate, ConsentCreateRequest, ConsentPermissions,
    OAuth2TokenRequest, OBPAccountBasic, OBPAccountDetail, OBPAccountBalance,
    OBPTransaction, PaymentInitiationRequest
)
from app.modules.users.models import User
from app.modules.accounts.models import Account
from app.modules.transactions.models import Transaction


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class OpenBankingService:
    """Core Open Banking service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================================
    # Third-Party App Management
    # ============================================================
    
    async def register_app(
        self, 
        developer_id: int,
        data: ThirdPartyAppCreate
    ) -> Tuple[ThirdPartyApp, str]:
        """Register a new third-party application"""
        # Generate credentials
        client_id = secrets.token_urlsafe(32)
        client_secret = secrets.token_urlsafe(32)  # 32 bytes = 43 chars, well under bcrypt 72-byte limit
        client_secret_hash = pwd_context.hash(client_secret)
        
        app = ThirdPartyApp(
            developer_id=developer_id,
            organization_name=data.organization_name,
            organization_email=data.organization_email,
            organization_website=data.organization_website,
            name=data.name,
            description=data.description,
            logo_url=data.logo_url,
            privacy_policy_url=data.privacy_policy_url,
            terms_of_service_url=data.terms_of_service_url,
            client_id=client_id,
            client_secret_hash=client_secret_hash,
            redirect_uris=data.redirect_uris,
            allowed_scopes=data.requested_scopes,
            app_type=data.app_type,
            status=AppStatus.SANDBOX  # Start in sandbox
        )
        
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)
        
        return app, client_secret
    
    async def get_app_by_client_id(self, client_id: str) -> Optional[ThirdPartyApp]:
        """Get app by client ID"""
        result = await self.db.execute(
            select(ThirdPartyApp).where(ThirdPartyApp.client_id == client_id)
        )
        return result.scalar_one_or_none()
    
    async def verify_client_credentials(
        self, 
        client_id: str, 
        client_secret: str
    ) -> Optional[ThirdPartyApp]:
        """Verify client credentials"""
        app = await self.get_app_by_client_id(client_id)
        if not app:
            return None
        
        if not pwd_context.verify(client_secret, app.client_secret_hash):
            return None
        
        if app.status not in [AppStatus.APPROVED, AppStatus.SANDBOX]:
            return None
        
        return app
    
    async def get_developer_apps(self, developer_id: int) -> List[ThirdPartyApp]:
        """Get all apps for a developer"""
        result = await self.db.execute(
            select(ThirdPartyApp)
            .where(ThirdPartyApp.developer_id == developer_id)
            .order_by(ThirdPartyApp.created_at.desc())
        )
        return result.scalars().all()
    
    async def approve_app(
        self, 
        app_id: int, 
        admin_id: int
    ) -> ThirdPartyApp:
        """Approve an app for production"""
        result = await self.db.execute(
            select(ThirdPartyApp).where(ThirdPartyApp.id == app_id)
        )
        app = result.scalar_one_or_none()
        if not app:
            raise ValueError("App not found")
        
        app.status = AppStatus.APPROVED
        app.approved_at = datetime.utcnow()
        app.approved_by = admin_id
        
        await self.db.commit()
        await self.db.refresh(app)
        return app
    
    async def regenerate_credentials(
        self, 
        app_id: int, 
        developer_id: int
    ) -> Tuple[str, str]:
        """Regenerate client credentials"""
        result = await self.db.execute(
            select(ThirdPartyApp).where(
                and_(
                    ThirdPartyApp.id == app_id,
                    ThirdPartyApp.developer_id == developer_id
                )
            )
        )
        app = result.scalar_one_or_none()
        if not app:
            raise ValueError("App not found")
        
        # Generate new credentials
        client_secret = secrets.token_urlsafe(32)  # 32 bytes = 43 chars, well under bcrypt 72-byte limit
        app.client_secret_hash = pwd_context.hash(client_secret)
        
        await self.db.commit()
        return app.client_id, client_secret
    
    # ============================================================
    # Consent Management
    # ============================================================
    
    async def create_consent(
        self,
        app_id: int,
        user_id: int,
        data: ConsentCreateRequest
    ) -> Consent:
        """Create a consent request"""
        consent_id = secrets.token_urlsafe(32)
        
        consent = Consent(
            consent_id=consent_id,
            user_id=user_id,
            app_id=app_id,
            consent_type=data.consent_type,
            status=ConsentStatus.PENDING,
            accounts_access=data.permissions.accounts,
            balances_access=data.permissions.balances,
            transactions_access=data.permissions.transactions,
            payment_initiation=data.permissions.payments,
            account_ids=data.account_ids or [],
            frequency_per_day=data.frequency_per_day,
            valid_from=datetime.utcnow(),
            valid_until=data.valid_until
        )
        
        self.db.add(consent)
        await self.db.commit()
        await self.db.refresh(consent)
        
        return consent
    
    async def get_consent(self, consent_id: str) -> Optional[Consent]:
        """Get consent by ID"""
        result = await self.db.execute(
            select(Consent).where(Consent.consent_id == consent_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_consents(self, user_id: int) -> List[Consent]:
        """Get all consents for a user"""
        result = await self.db.execute(
            select(Consent)
            .where(Consent.user_id == user_id)
            .order_by(Consent.created_at.desc())
        )
        return result.scalars().all()
    
    async def authorize_consent(
        self,
        consent_id: str,
        user_id: int,
        authorized: bool,
        selected_accounts: Optional[List[str]] = None
    ) -> Consent:
        """User authorizes or rejects consent"""
        consent = await self.get_consent(consent_id)
        if not consent:
            raise ValueError("Consent not found")
        
        if consent.user_id != user_id:
            raise ValueError("Unauthorized")
        
        if consent.status != ConsentStatus.PENDING:
            raise ValueError("Consent already processed")
        
        if authorized:
            consent.status = ConsentStatus.AUTHORIZED
            consent.authorized_at = datetime.utcnow()
            # Generate authorization code
            consent.authorization_code = secrets.token_urlsafe(32)
            consent.authorization_code_expires = datetime.utcnow() + timedelta(minutes=10)
            
            if selected_accounts:
                consent.account_ids = selected_accounts
        else:
            consent.status = ConsentStatus.REJECTED
        
        await self.db.commit()
        await self.db.refresh(consent)
        return consent
    
    async def revoke_consent(
        self,
        consent_id: str,
        user_id: int,
        reason: Optional[str] = None
    ) -> Consent:
        """User revokes consent"""
        consent = await self.get_consent(consent_id)
        if not consent:
            raise ValueError("Consent not found")
        
        if consent.user_id != user_id:
            raise ValueError("Unauthorized")
        
        consent.status = ConsentStatus.REVOKED
        consent.revoked_at = datetime.utcnow()
        consent.revocation_reason = reason
        
        # Revoke all associated tokens
        await self.db.execute(
            select(OAuthToken)
            .where(OAuthToken.consent_id == consent.id)
        )
        # Mark tokens as revoked...
        
        await self.db.commit()
        await self.db.refresh(consent)
        return consent
    
    async def validate_consent(
        self,
        consent_id: str,
        required_scopes: List[str]
    ) -> bool:
        """Validate consent is active and has required scopes"""
        consent = await self.get_consent(consent_id)
        if not consent:
            return False
        
        if consent.status != ConsentStatus.AUTHORIZED:
            return False
        
        if consent.valid_until < datetime.utcnow():
            consent.status = ConsentStatus.EXPIRED
            await self.db.commit()
            return False
        
        # Check required scopes
        for scope in required_scopes:
            if scope == "accounts" and not consent.accounts_access:
                return False
            if scope == "balances" and not consent.balances_access:
                return False
            if scope == "transactions" and not consent.transactions_access:
                return False
            if scope == "payments" and not consent.payment_initiation:
                return False
        
        return True
    
    # ============================================================
    # OAuth2 Token Management
    # ============================================================
    
    async def exchange_authorization_code(
        self,
        app: ThirdPartyApp,
        code: str,
        redirect_uri: str
    ) -> Tuple[str, str, int]:
        """Exchange authorization code for tokens"""
        # Find consent with this code
        result = await self.db.execute(
            select(Consent).where(
                and_(
                    Consent.authorization_code == code,
                    Consent.app_id == app.id
                )
            )
        )
        consent = result.scalar_one_or_none()
        
        if not consent:
            raise ValueError("Invalid authorization code")
        
        if consent.authorization_code_expires < datetime.utcnow():
            raise ValueError("Authorization code expired")
        
        # Clear the code (one-time use)
        consent.authorization_code = None
        
        # Generate tokens
        access_token = secrets.token_urlsafe(48)
        refresh_token = secrets.token_urlsafe(64)
        
        access_expires = datetime.utcnow() + timedelta(hours=1)
        refresh_expires = datetime.utcnow() + timedelta(days=30)
        
        # Store access token
        access_token_record = OAuthToken(
            user_id=consent.user_id,
            app_id=app.id,
            consent_id=consent.id,
            token_type=TokenType.ACCESS,
            token_hash=hashlib.sha256(access_token.encode()).hexdigest(),
            grant_type=GrantType.AUTHORIZATION_CODE,
            scopes=self._consent_to_scopes(consent),
            expires_at=access_expires
        )
        self.db.add(access_token_record)
        
        # Store refresh token
        refresh_token_record = OAuthToken(
            user_id=consent.user_id,
            app_id=app.id,
            consent_id=consent.id,
            token_type=TokenType.REFRESH,
            token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
            grant_type=GrantType.AUTHORIZATION_CODE,
            scopes=self._consent_to_scopes(consent),
            expires_at=refresh_expires
        )
        self.db.add(refresh_token_record)
        
        await self.db.commit()
        
        return access_token, refresh_token, 3600  # expires_in seconds
    
    async def refresh_access_token(
        self,
        app: ThirdPartyApp,
        refresh_token: str
    ) -> Tuple[str, int]:
        """Refresh an access token"""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        result = await self.db.execute(
            select(OAuthToken).where(
                and_(
                    OAuthToken.token_hash == token_hash,
                    OAuthToken.token_type == TokenType.REFRESH,
                    OAuthToken.app_id == app.id,
                    OAuthToken.is_revoked == False
                )
            )
        )
        token_record = result.scalar_one_or_none()
        
        if not token_record:
            raise ValueError("Invalid refresh token")
        
        if token_record.expires_at < datetime.utcnow():
            raise ValueError("Refresh token expired")
        
        # Generate new access token
        new_access_token = secrets.token_urlsafe(48)
        access_expires = datetime.utcnow() + timedelta(hours=1)
        
        access_token_record = OAuthToken(
            user_id=token_record.user_id,
            app_id=app.id,
            consent_id=token_record.consent_id,
            token_type=TokenType.ACCESS,
            token_hash=hashlib.sha256(new_access_token.encode()).hexdigest(),
            grant_type=GrantType.REFRESH_TOKEN,
            scopes=token_record.scopes,
            expires_at=access_expires,
            refresh_token_id=token_record.id
        )
        self.db.add(access_token_record)
        await self.db.commit()
        
        return new_access_token, 3600
    
    async def validate_access_token(
        self,
        token: str,
        required_scopes: List[str] = None
    ) -> Optional[OAuthToken]:
        """Validate access token and return token record"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        result = await self.db.execute(
            select(OAuthToken).where(
                and_(
                    OAuthToken.token_hash == token_hash,
                    OAuthToken.token_type == TokenType.ACCESS,
                    OAuthToken.is_revoked == False
                )
            )
        )
        token_record = result.scalar_one_or_none()
        
        if not token_record:
            return None
        
        if token_record.expires_at < datetime.utcnow():
            return None
        
        # Check scopes
        if required_scopes:
            token_scopes = set(token_record.scopes or [])
            if not token_scopes.issuperset(set(required_scopes)):
                return None
        
        # Update usage
        token_record.last_used_at = datetime.utcnow()
        token_record.use_count += 1
        await self.db.commit()
        
        return token_record
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke an access or refresh token"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        result = await self.db.execute(
            select(OAuthToken).where(OAuthToken.token_hash == token_hash)
        )
        token_record = result.scalar_one_or_none()
        
        if not token_record:
            return False
        
        token_record.is_revoked = True
        token_record.revoked_at = datetime.utcnow()
        await self.db.commit()
        
        return True
    
    def _consent_to_scopes(self, consent: Consent) -> List[str]:
        """Convert consent permissions to scope list"""
        scopes = []
        if consent.accounts_access:
            scopes.append("accounts")
        if consent.balances_access:
            scopes.append("balances")
        if consent.transactions_access:
            scopes.append("transactions")
        if consent.payment_initiation:
            scopes.append("payments")
        return scopes
    
    # ============================================================
    # OBP Data Transformation
    # ============================================================
    
    async def get_user_accounts_obp(
        self,
        user_id: int,
        consent: Optional[Consent] = None
    ) -> List[OBPAccountBasic]:
        """Get user accounts in OBP format"""
        query = select(Account).where(Account.user_id == user_id)
        
        # Filter by consent if provided
        if consent and consent.account_ids:
            query = query.where(Account.id.in_(consent.account_ids))
        
        result = await self.db.execute(query)
        accounts = result.scalars().all()
        
        obp_accounts = []
        for acc in accounts:
            obp_accounts.append(OBPAccountBasic(
                id=str(acc.id),
                bank_id="kitbank",
                label=acc.account_name or f"{acc.account_type.value} Account",
                account_type=acc.account_type.value,
                account_routings=[
                    {"scheme": "AccountNumber", "address": acc.account_number},
                    {"scheme": "IBAN", "address": acc.iban or ""}
                ]
            ))
        
        return obp_accounts
    
    async def get_account_detail_obp(
        self,
        account_id: int,
        user_id: int
    ) -> Optional[OBPAccountDetail]:
        """Get account detail in OBP format"""
        result = await self.db.execute(
            select(Account).where(
                and_(Account.id == account_id, Account.user_id == user_id)
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            return None
        
        # Get user for owner info
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        return OBPAccountDetail(
            id=str(account.id),
            bank_id="kitbank",
            label=account.account_name or f"{account.account_type.value} Account",
            number=account.account_number,
            account_type=account.account_type.value,
            balance=OBPAccountBalance(
                currency=account.currency.value,
                amount=str(account.current_balance)
            ),
            IBAN=account.iban,
            swift_bic=account.swift_bic,
            owners=[{
                "id": str(user.id),
                "provider": "kitbank",
                "display_name": f"{user.first_name} {user.last_name}"
            }] if user else [],
            account_routings=[
                {"scheme": "AccountNumber", "address": account.account_number},
                {"scheme": "IBAN", "address": account.iban or ""}
            ]
        )
    
    async def get_account_transactions_obp(
        self,
        account_id: int,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[OBPTransaction]:
        """Get account transactions in OBP format"""
        # Verify account ownership
        acc_result = await self.db.execute(
            select(Account).where(
                and_(Account.id == account_id, Account.user_id == user_id)
            )
        )
        account = acc_result.scalar_one_or_none()
        if not account:
            return []
        
        # Get transactions
        result = await self.db.execute(
            select(Transaction).where(
                or_(
                    Transaction.source_account_id == account_id,
                    Transaction.destination_account_id == account_id
                )
            )
            .order_by(Transaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        transactions = result.scalars().all()
        
        obp_transactions = []
        for txn in transactions:
            is_outgoing = txn.source_account_id == account_id
            
            obp_transactions.append(OBPTransaction(
                id=str(txn.id),
                bank_id="kitbank",
                account_id=str(account_id),
                this_account={
                    "id": str(account_id),
                    "bank_id": "kitbank"
                },
                other_account={
                    "id": str(txn.destination_account_id if is_outgoing else txn.source_account_id),
                    "bank_id": "kitbank",
                    "holder": {"name": txn.recipient_name or "Unknown"}
                },
                details={
                    "type": txn.transaction_type.value,
                    "description": txn.description or "",
                    "posted": txn.created_at.isoformat() if txn.created_at else None,
                    "completed": txn.completed_at.isoformat() if txn.completed_at else None,
                    "value": {
                        "currency": txn.currency.value,
                        "amount": str(-txn.amount if is_outgoing else txn.amount)
                    },
                    "status": txn.status.value
                }
            ))
        
        return obp_transactions
    
    # ============================================================
    # Rate Limiting
    # ============================================================
    
    async def log_api_request(
        self,
        app_id: int,
        user_id: Optional[int],
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        client_ip: str
    ):
        """Log API request for rate limiting and audit"""
        log = APIRequestLog(
            app_id=app_id,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            client_ip=client_ip
        )
        self.db.add(log)
        await self.db.commit()
    
    async def check_rate_limit(
        self,
        app_id: int,
        limit_per_minute: int,
        limit_per_day: int
    ) -> Tuple[bool, int, int]:
        """Check if app is within rate limits"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)
        
        # Count requests in last minute
        minute_result = await self.db.execute(
            select(func.count(APIRequestLog.id)).where(
                and_(
                    APIRequestLog.app_id == app_id,
                    APIRequestLog.requested_at >= minute_ago
                )
            )
        )
        minute_count = minute_result.scalar() or 0
        
        # Count requests in last day
        day_result = await self.db.execute(
            select(func.count(APIRequestLog.id)).where(
                and_(
                    APIRequestLog.app_id == app_id,
                    APIRequestLog.requested_at >= day_ago
                )
            )
        )
        day_count = day_result.scalar() or 0
        
        allowed = minute_count < limit_per_minute and day_count < limit_per_day
        
        return allowed, limit_per_minute - minute_count, limit_per_day - day_count
