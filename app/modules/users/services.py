from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, UploadFile
from datetime import datetime, timedelta, date
from typing import Optional, List
import secrets
import os
from pathlib import Path

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_otp,
    generate_verification_token,
    validate_password_strength
)
from app.core.config import settings
from app.core.database import get_redis
from app.modules.users.models import User, KYCStatus, AccountStatus, TwoFactorMethod
from app.modules.users.kyc_models import KYCDocument, KYCDocumentStatus, GovernmentIDType
from app.modules.users import schemas


class UserService:
    """Service layer for user management operations"""
    
    @staticmethod
    async def register_user(db: AsyncSession, user_data: schemas.UserRegistrationRequest) -> User:
        """Register a new user with complete profile"""
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if phone already exists
        result = await db.execute(select(User).where(User.phone_number == user_data.phone_number))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Create user
        user = User(
            email=user_data.email,
            phone_number=user_data.phone_number,
            hashed_password=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            date_of_birth=user_data.date_of_birth,
            nationality=user_data.nationality,
            country_of_residence=user_data.country_of_residence,
            street_address=user_data.street_address,
            city=user_data.city,
            state=user_data.state,
            postal_code=user_data.postal_code,
            country=user_data.country,
            occupation=user_data.occupation,
            source_of_funds=user_data.source_of_funds,
            monthly_income_range=user_data.monthly_income_range,
            tax_identification_number=user_data.tax_identification_number,
            accepted_terms=user_data.accepted_terms,
            accepted_privacy_policy=user_data.accepted_privacy_policy,
            marketing_consent=user_data.marketing_consent,
            account_status=AccountStatus.PENDING,
            kyc_status=KYCStatus.PENDING
        )
        
        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Generate and store email verification OTP
            await UserService.send_email_verification(user.email, user.id)
            
            # Generate and store phone verification OTP
            await UserService.send_phone_verification(user.phone_number, user.id)
            
            return user
            
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User registration failed. Please try again."
            )
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, email_or_phone: str, password: str) -> Optional[User]:
        """Authenticate user with email/phone and password"""
        
        # Find user by email or phone
        result = await db.execute(
            select(User).where(
                or_(
                    User.email == email_or_phone,
                    User.phone_number == email_or_phone
                )
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Check if account is locked
        if user.account_locked_until and user.account_locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is locked until {user.account_locked_until}"
            )
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            # Increment login attempts
            user.login_attempts += 1
            
            # Lock account after max attempts
            if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.account_locked_until = datetime.utcnow() + timedelta(
                    minutes=settings.ACCOUNT_LOCK_DURATION_MINUTES
                )
            
            await db.commit()
            return None
        
        # Reset login attempts on successful login
        user.login_attempts = 0
        user.last_login_at = datetime.utcnow()
        user.account_locked_until = None
        await db.commit()
        
        return user
    
    @staticmethod
    async def create_tokens(user_id: int) -> dict:
        """Create access and refresh tokens"""
        access_token = create_access_token(data={"sub": str(user_id)})
        refresh_token = create_refresh_token(data={"sub": str(user_id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    @staticmethod
    async def logout_user(token: str):
        """Logout user by blacklisting token"""
        redis = await get_redis()
        
        # Add token to blacklist with expiration
        await redis.setex(
            f"blacklist:{token}",
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "1"
        )
    
    @staticmethod
    async def send_email_verification(email: str, user_id: int) -> str:
        """Generate and send email verification OTP"""
        redis = await get_redis()
        otp = generate_otp()
        
        # Store OTP in Redis with expiration
        await redis.setex(
            f"email_otp:{user_id}",
            settings.OTP_EXPIRY_MINUTES * 60,
            otp
        )
        
        # TODO: Send email via SendGrid
        # For now, just return OTP (in production, this should be sent via email)
        print(f"Email OTP for {email}: {otp}")
        
        return otp
    
    @staticmethod
    async def send_phone_verification(phone: str, user_id: int) -> str:
        """Generate and send phone verification OTP"""
        redis = await get_redis()
        otp = generate_otp()
        
        # Store OTP in Redis with expiration
        await redis.setex(
            f"phone_otp:{user_id}",
            settings.OTP_EXPIRY_MINUTES * 60,
            otp
        )
        
        # TODO: Send SMS via Twilio
        # For now, just return OTP (in production, this should be sent via SMS)
        print(f"Phone OTP for {phone}: {otp}")
        
        return otp
    
    @staticmethod
    async def verify_email(db: AsyncSession, user_id: int, otp: str) -> bool:
        """Verify email with OTP"""
        redis = await get_redis()
        
        # Get stored OTP
        stored_otp = await redis.get(f"email_otp:{user_id}")
        
        if not stored_otp or stored_otp != otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        # Update user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.email_verified = True
        
        # Activate account if both email and phone are verified
        if user.phone_verified:
            user.account_status = AccountStatus.ACTIVE
        
        await db.commit()
        
        # Delete OTP from Redis
        await redis.delete(f"email_otp:{user_id}")
        
        return True
    
    @staticmethod
    async def verify_phone(db: AsyncSession, user_id: int, otp: str) -> bool:
        """Verify phone with OTP"""
        redis = await get_redis()
        
        # Get stored OTP
        stored_otp = await redis.get(f"phone_otp:{user_id}")
        
        if not stored_otp or stored_otp != otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        # Update user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.phone_verified = True
        
        # Activate account if both email and phone are verified
        if user.email_verified:
            user.account_status = AccountStatus.ACTIVE
        
        await db.commit()
        
        # Delete OTP from Redis
        await redis.delete(f"phone_otp:{user_id}")
        
        return True
    
    @staticmethod
    async def initiate_password_reset(db: AsyncSession, email: str) -> str:
        """Initiate password reset process"""
        # Find user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            # Don't reveal if email exists
            return "If the email exists, a reset link has been sent"
        
        # Generate reset token
        reset_token = generate_verification_token()
        
        # Store token in Redis with expiration
        redis = await get_redis()
        await redis.setex(
            f"password_reset:{reset_token}",
            30 * 60,  # 30 minutes
            str(user.id)
        )
        
        # TODO: Send email with reset link
        print(f"Password reset token for {email}: {reset_token}")
        
        return reset_token
    
    @staticmethod
    async def reset_password(db: AsyncSession, token: str, new_password: str) -> bool:
        """Reset password with token"""
        redis = await get_redis()
        
        # Get user ID from token
        user_id_str = await redis.get(f"password_reset:{token}")
        
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Update password
        user_id = int(user_id_str)
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.hashed_password = get_password_hash(new_password)
        await db.commit()
        
        # Delete reset token
        await redis.delete(f"password_reset:{token}")
        
        return True
    
    @staticmethod
    async def update_profile(db: AsyncSession, user_id: int, profile_data: schemas.UserProfileUpdate) -> User:
        """Update user profile"""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        update_data = profile_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def save_uploaded_file(file: UploadFile, user_id: int, file_type: str) -> str:
        """Save uploaded file locally or to S3"""
        
        # Validate file type
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file_ext} not allowed. Allowed types: {allowed_extensions}"
            )
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{user_id}_{file_type}_{timestamp}{file_ext}"
        
        if settings.USE_LOCAL_STORAGE:
            # Save locally
            upload_dir = Path(settings.LOCAL_STORAGE_PATH) / "kyc_documents"
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = upload_dir / filename
            
            # Save file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            return str(file_path)
        else:
            # TODO: Upload to S3
            # For now, save locally
            upload_dir = Path(settings.LOCAL_STORAGE_PATH) / "kyc_documents"
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = upload_dir / filename
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            return str(file_path)
    
    @staticmethod
    async def submit_kyc(
        db: AsyncSession,
        user_id: int,
        kyc_data: schemas.KYCSubmissionRequest,
        id_front: UploadFile,
        id_back: Optional[UploadFile],
        selfie: UploadFile,
        proof_of_address: UploadFile
    ) -> KYCDocument:
        """Submit KYC documents"""
        
        # Check if user exists
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Upload files
        id_front_url = await UserService.save_uploaded_file(id_front, user_id, "id_front")
        selfie_url = await UserService.save_uploaded_file(selfie, user_id, "selfie")
        proof_address_url = await UserService.save_uploaded_file(proof_of_address, user_id, "proof_address")
        
        id_back_url = None
        if id_back:
            id_back_url = await UserService.save_uploaded_file(id_back, user_id, "id_back")
        
        # Create KYC document
        kyc_doc = KYCDocument(
            user_id=user_id,
            government_id_type=kyc_data.government_id_type,
            government_id_number=kyc_data.government_id_number,
            government_id_front_url=id_front_url,
            government_id_back_url=id_back_url,
            selfie_with_id_url=selfie_url,
            proof_of_address_url=proof_address_url,
            proof_of_address_type=kyc_data.proof_of_address_type,
            document_issue_date=kyc_data.document_issue_date,
            document_expiry_date=kyc_data.document_expiry_date,
            status=KYCDocumentStatus.SUBMITTED
        )
        
        db.add(kyc_doc)
        
        # Update user KYC status
        user.kyc_status = KYCStatus.SUBMITTED
        
        await db.commit()
        await db.refresh(kyc_doc)
        
        return kyc_doc
    
    @staticmethod
    async def get_kyc_status(db: AsyncSession, user_id: int) -> dict:
        """Get user KYC status"""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "kyc_status": user.kyc_status.value,
            "kyc_rejection_reason": user.kyc_rejection_reason,
            "kyc_verified_at": user.kyc_verified_at
        }
    
    @staticmethod
    async def close_account(db: AsyncSession, user_id: int, reason: str, password: str) -> bool:
        """Request account closure"""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        
        # Soft delete
        user.account_status = AccountStatus.CLOSED
        user.deleted_at = datetime.utcnow()
        
        await db.commit()
        
        return True
