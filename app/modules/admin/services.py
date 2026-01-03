from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import json

from passlib.context import CryptContext

from app.modules.admin.models import (
    AdminUser, AuditLog, SystemSetting,
    AdminRole, AdminPermission, ROLE_PERMISSIONS
)
from app.modules.admin.schemas import (
    AdminUserCreate, AdminUserUpdate, AuditLogFilter,
    DashboardStats, KYCReviewRequest
)
from app.modules.users.models import User, KYCStatus, AccountStatus
from app.modules.accounts.models import Account
from app.modules.transactions.models import Transaction, TransactionStatus
from app.modules.loans.models import Loan, LoanStatus
from app.modules.cards.models import VirtualCard, CardStatus

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminService:
    """Service for admin operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================================
    # Admin User Management
    # ============================================================
    
    async def create_admin_user(
        self,
        data: AdminUserCreate,
        created_by: Optional[int] = None
    ) -> AdminUser:
        """Create a new admin user"""
        # Check if email exists
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.email == data.email)
        )
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")
        
        admin = AdminUser(
            email=data.email,
            hashed_password=pwd_context.hash(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone_number=data.phone_number,
            role=data.role,
            user_id=data.user_id,
            created_by=created_by
        )
        
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)
        
        return admin
    
    async def get_admin_user(self, admin_id: int) -> Optional[AdminUser]:
        """Get admin user by ID"""
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.id == admin_id)
        )
        return result.scalar_one_or_none()
    
    async def get_admin_by_email(self, email: str) -> Optional[AdminUser]:
        """Get admin user by email"""
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.email == email)
        )
        return result.scalar_one_or_none()
    
    async def authenticate_admin(self, email: str, password: str) -> Optional[AdminUser]:
        """Authenticate admin user"""
        admin = await self.get_admin_by_email(email)
        
        if not admin:
            return None
        
        if not admin.is_active:
            raise ValueError("Account is disabled")
        
        if admin.locked_until and admin.locked_until > datetime.utcnow():
            raise ValueError("Account is locked")
        
        if not pwd_context.verify(password, admin.hashed_password):
            admin.login_attempts += 1
            if admin.login_attempts >= 5:
                admin.locked_until = datetime.utcnow() + timedelta(minutes=30)
            await self.db.commit()
            return None
        
        # Successful login
        admin.login_attempts = 0
        admin.last_login_at = datetime.utcnow()
        await self.db.commit()
        
        return admin
    
    def get_admin_permissions(self, admin: AdminUser) -> List[str]:
        """Get all permissions for an admin user"""
        default_perms = ROLE_PERMISSIONS.get(admin.role, [])
        perms = [p.value for p in default_perms]
        
        # Add custom permissions
        if admin.custom_permissions:
            custom = admin.custom_permissions.split(",")
            perms.extend(custom)
        
        return list(set(perms))
    
    def has_permission(self, admin: AdminUser, permission: AdminPermission) -> bool:
        """Check if admin has a specific permission"""
        perms = self.get_admin_permissions(admin)
        return permission.value in perms
    
    async def get_all_admins(self) -> List[AdminUser]:
        """Get all admin users"""
        result = await self.db.execute(
            select(AdminUser).order_by(AdminUser.created_at.desc())
        )
        return list(result.scalars().all())
    
    # ============================================================
    # Audit Logging
    # ============================================================
    
    async def log_action(
        self,
        admin_id: Optional[int],
        admin_email: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        description: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log an admin action"""
        log = AuditLog(
            admin_id=admin_id,
            admin_email=admin_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(log)
        await self.db.commit()
        
        return log
    
    async def get_audit_logs(
        self,
        filters: Optional[AuditLogFilter] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[AuditLog], int]:
        """Get audit logs with filtering"""
        query = select(AuditLog)
        
        if filters:
            if filters.admin_id:
                query = query.where(AuditLog.admin_id == filters.admin_id)
            if filters.action:
                query = query.where(AuditLog.action == filters.action)
            if filters.resource_type:
                query = query.where(AuditLog.resource_type == filters.resource_type)
            if filters.resource_id:
                query = query.where(AuditLog.resource_id == filters.resource_id)
            if filters.success is not None:
                query = query.where(AuditLog.success == filters.success)
            if filters.start_date:
                query = query.where(AuditLog.created_at >= filters.start_date)
            if filters.end_date:
                query = query.where(AuditLog.created_at <= filters.end_date)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Paginate
        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        logs = list(result.scalars().all())
        
        return logs, total
    
    # ============================================================
    # Dashboard Statistics
    # ============================================================
    
    async def get_dashboard_stats(self) -> DashboardStats:
        """Get dashboard statistics"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        
        # Users
        total_users = await self.db.execute(select(func.count(User.id)))
        active_users = await self.db.execute(
            select(func.count(User.id)).where(User.account_status == AccountStatus.ACTIVE)
        )
        pending_kyc = await self.db.execute(
            select(func.count(User.id)).where(User.kyc_status == KYCStatus.SUBMITTED)
        )
        new_users_today = await self.db.execute(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )
        new_users_week = await self.db.execute(
            select(func.count(User.id)).where(User.created_at >= week_start)
        )
        
        # Accounts
        total_accounts = await self.db.execute(select(func.count(Account.id)))
        total_balance = await self.db.execute(select(func.sum(Account.current_balance)))
        
        # Transactions
        txn_today = await self.db.execute(
            select(func.count(Transaction.id)).where(
                and_(
                    Transaction.created_at >= today_start,
                    Transaction.status == TransactionStatus.COMPLETED
                )
            )
        )
        txn_week = await self.db.execute(
            select(func.count(Transaction.id)).where(
                and_(
                    Transaction.created_at >= week_start,
                    Transaction.status == TransactionStatus.COMPLETED
                )
            )
        )
        vol_today = await self.db.execute(
            select(func.sum(Transaction.amount)).where(
                and_(
                    Transaction.created_at >= today_start,
                    Transaction.status == TransactionStatus.COMPLETED
                )
            )
        )
        vol_week = await self.db.execute(
            select(func.sum(Transaction.amount)).where(
                and_(
                    Transaction.created_at >= week_start,
                    Transaction.status == TransactionStatus.COMPLETED
                )
            )
        )
        
        # Loans
        total_loans = await self.db.execute(select(func.count(Loan.id)))
        pending_loans = await self.db.execute(
            select(func.count(Loan.id)).where(Loan.status == LoanStatus.SUBMITTED)
        )
        active_loans = await self.db.execute(
            select(func.count(Loan.id)).where(Loan.status == LoanStatus.ACTIVE)
        )
        total_loan_amount = await self.db.execute(
            select(func.sum(Loan.disbursed_amount)).where(Loan.disbursed_amount.isnot(None))
        )
        overdue_loans = await self.db.execute(
            select(func.count(Loan.id)).where(Loan.status == LoanStatus.OVERDUE)
        )
        
        # Cards
        total_cards = await self.db.execute(select(func.count(VirtualCard.id)))
        active_cards = await self.db.execute(
            select(func.count(VirtualCard.id)).where(VirtualCard.status == CardStatus.ACTIVE)
        )
        
        return DashboardStats(
            total_users=total_users.scalar() or 0,
            active_users=active_users.scalar() or 0,
            pending_kyc=pending_kyc.scalar() or 0,
            new_users_today=new_users_today.scalar() or 0,
            new_users_this_week=new_users_week.scalar() or 0,
            total_accounts=total_accounts.scalar() or 0,
            total_balance=total_balance.scalar() or Decimal("0"),
            transactions_today=txn_today.scalar() or 0,
            transactions_this_week=txn_week.scalar() or 0,
            transaction_volume_today=vol_today.scalar() or Decimal("0"),
            transaction_volume_this_week=vol_week.scalar() or Decimal("0"),
            total_loans=total_loans.scalar() or 0,
            pending_loan_applications=pending_loans.scalar() or 0,
            active_loans=active_loans.scalar() or 0,
            total_loan_amount=total_loan_amount.scalar() or Decimal("0"),
            overdue_loans=overdue_loans.scalar() or 0,
            total_cards=total_cards.scalar() or 0,
            active_cards=active_cards.scalar() or 0
        )
    
    # ============================================================
    # User Management
    # ============================================================
    
    async def get_users(
        self,
        search: Optional[str] = None,
        kyc_status: Optional[KYCStatus] = None,
        account_status: Optional[AccountStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[User], int]:
        """Get users with filtering"""
        query = select(User)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    User.email.ilike(search_term),
                    User.phone_number.ilike(search_term),
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term)
                )
            )
        
        if kyc_status:
            query = query.where(User.kyc_status == kyc_status)
        
        if account_status:
            query = query.where(User.account_status == account_status)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Paginate
        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        users = list(result.scalars().all())
        
        return users, total
    
    async def review_kyc(
        self,
        request: KYCReviewRequest,
        reviewer_id: int
    ) -> User:
        """Review and approve/reject KYC"""
        result = await self.db.execute(
            select(User).where(User.id == request.user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        if user.kyc_status not in [KYCStatus.SUBMITTED, KYCStatus.UNDER_REVIEW]:
            raise ValueError("KYC is not pending review")
        
        if request.approved:
            user.kyc_status = KYCStatus.APPROVED
            user.kyc_verified_at = datetime.utcnow()
        else:
            user.kyc_status = KYCStatus.REJECTED
            user.kyc_rejection_reason = request.rejection_reason
        
        user.kyc_reviewer_id = reviewer_id
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def suspend_user(self, user_id: int, reason: str) -> User:
        """Suspend a user account"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        user.account_status = AccountStatus.SUSPENDED
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def reactivate_user(self, user_id: int) -> User:
        """Reactivate a suspended user"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        user.account_status = AccountStatus.ACTIVE
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    # ============================================================
    # System Settings
    # ============================================================
    
    async def get_settings(self, category: Optional[str] = None) -> List[SystemSetting]:
        """Get system settings"""
        query = select(SystemSetting)
        if category:
            query = query.where(SystemSetting.category == category)
        query = query.order_by(SystemSetting.category, SystemSetting.key)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_setting(
        self,
        key: str,
        value: str,
        admin_id: int
    ) -> SystemSetting:
        """Update a system setting"""
        result = await self.db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            raise ValueError("Setting not found")
        
        if setting.is_readonly:
            raise ValueError("Setting is read-only")
        
        setting.value = value
        setting.updated_by = admin_id
        
        await self.db.commit()
        await self.db.refresh(setting)
        
        return setting
