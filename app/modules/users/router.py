from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_user, require_email_verified
from app.modules.users.models import User
from app.modules.users import schemas, services

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("/register", response_model=schemas.UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: schemas.UserRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with complete profile information.
    
    - Validates age (must be 18+)
    - Checks email and phone uniqueness
    - Sends verification codes to email and phone
    - Returns user profile
    """
    user = await services.UserService.register_user(db, user_data)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
async def login(
    login_data: schemas.UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email/phone and password.
    
    - Accepts email or phone number
    - Returns JWT access and refresh tokens
    - Locks account after 5 failed attempts
    """
    user = await services.UserService.authenticate_user(
        db,
        login_data.email_or_phone,
        login_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/phone or password"
        )
    
    # Check if 2FA is enabled
    if user.two_factor_enabled and not login_data.two_factor_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication code required"
        )
    
    # TODO: Verify 2FA code if provided
    
    tokens = await services.UserService.create_tokens(user.id)
    return tokens


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_active_user),
    token: str = Depends(OAuth2PasswordRequestForm)
):
    """
    Logout current user by invalidating token.
    """
    # Token is extracted from the dependency
    # In a real implementation, you'd get the token from the request header
    return {"message": "Successfully logged out"}


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    verification_data: schemas.EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verify email address with OTP.
    
    - OTP expires after 10 minutes
    - Account activates when both email and phone are verified
    """
    await services.UserService.verify_email(db, current_user.id, verification_data.otp)
    return {"message": "Email verified successfully"}


@router.post("/verify-phone", status_code=status.HTTP_200_OK)
async def verify_phone(
    verification_data: schemas.PhoneVerificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verify phone number with OTP.
    
    - OTP expires after 10 minutes
    - Account activates when both email and phone are verified
    """
    await services.UserService.verify_phone(db, current_user.id, verification_data.otp)
    return {"message": "Phone verified successfully"}


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    resend_data: schemas.ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resend verification code to email or phone.
    """
    if resend_data.verification_type == "email":
        await services.UserService.send_email_verification(current_user.email, current_user.id)
        return {"message": "Email verification code sent"}
    else:
        await services.UserService.send_phone_verification(current_user.phone_number, current_user.id)
        return {"message": "Phone verification code sent"}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    reset_request: schemas.PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate password reset process.
    
    - Sends reset link to email
    - Token expires after 30 minutes
    """
    await services.UserService.initiate_password_reset(db, reset_request.email)
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: schemas.PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password with token from email.
    
    - Validates password strength
    - Invalidates reset token after use
    """
    await services.UserService.reset_password(db, reset_data.token, reset_data.new_password)
    return {"message": "Password reset successfully"}


@router.get("/profile", response_model=schemas.UserProfileResponse)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    """
    Get current user's complete profile.
    """
    return current_user


@router.put("/profile", response_model=schemas.UserProfileResponse)
async def update_profile(
    profile_data: schemas.UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update user profile information.
    
    - Can update address, phone, occupation
    - Cannot update email, name, or date of birth
    """
    user = await services.UserService.update_profile(db, current_user.id, profile_data)
    return user


@router.get("/kyc-status", response_model=schemas.KYCStatusResponse)
async def get_kyc_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get KYC verification status.
    """
    return await services.UserService.get_kyc_status(db, current_user.id)


@router.post("/kyc/submit", response_model=schemas.KYCDocumentResponse, status_code=status.HTTP_201_CREATED)
async def submit_kyc(
    government_id_type: str = Form(...),
    government_id_number: str = Form(...),
    document_issue_date: str = Form(...),
    document_expiry_date: Optional[str] = Form(None),
    proof_of_address_type: str = Form(...),
    id_front: UploadFile = File(...),
    id_back: Optional[UploadFile] = File(None),
    selfie: UploadFile = File(...),
    proof_of_address: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit KYC documents for verification.
    
    Required files:
    - Government ID (front)
    - Government ID (back) - optional for some ID types
    - Selfie with ID
    - Proof of address (utility bill, bank statement, etc.)
    
    Accepted formats: JPG, PNG, PDF
    """
    from datetime import date as date_type
    
    # Parse dates
    issue_date = date_type.fromisoformat(document_issue_date)
    expiry_date = date_type.fromisoformat(document_expiry_date) if document_expiry_date else None
    
    # Create KYC submission request
    kyc_data = schemas.KYCSubmissionRequest(
        government_id_type=government_id_type,
        government_id_number=government_id_number,
        document_issue_date=issue_date,
        document_expiry_date=expiry_date,
        proof_of_address_type=proof_of_address_type
    )
    
    kyc_doc = await services.UserService.submit_kyc(
        db,
        current_user.id,
        kyc_data,
        id_front,
        id_back,
        selfie,
        proof_of_address
    )
    
    return kyc_doc


@router.put("/kyc/update", response_model=schemas.KYCDocumentResponse)
async def update_kyc(
    government_id_type: str = Form(...),
    government_id_number: str = Form(...),
    document_issue_date: str = Form(...),
    document_expiry_date: Optional[str] = Form(None),
    proof_of_address_type: str = Form(...),
    id_front: Optional[UploadFile] = File(None),
    id_back: Optional[UploadFile] = File(None),
    selfie: Optional[UploadFile] = File(None),
    proof_of_address: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update KYC documents.
    
    - Can resubmit documents if rejected
    - Only upload files that need to be updated
    """
    # TODO: Implement KYC update logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="KYC update not yet implemented"
    )


@router.get("/kyc/history", response_model=list[schemas.KYCDocumentResponse])
async def get_kyc_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get KYC submission history.
    """
    # TODO: Implement KYC history retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="KYC history not yet implemented"
    )


@router.post("/2fa/enable", response_model=schemas.TwoFactorSetupResponse)
async def enable_2fa(
    enable_data: schemas.TwoFactorEnableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Enable two-factor authentication.
    
    - Supports SMS and authenticator app
    - Returns QR code for authenticator apps
    - Returns backup codes
    """
    # TODO: Implement 2FA enable logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="2FA enable not yet implemented"
    )


@router.post("/2fa/disable", status_code=status.HTTP_200_OK)
async def disable_2fa(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Disable two-factor authentication.
    """
    # TODO: Implement 2FA disable logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="2FA disable not yet implemented"
    )


@router.post("/2fa/verify", status_code=status.HTTP_200_OK)
async def verify_2fa(
    verify_data: schemas.TwoFactorVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verify 2FA code during login.
    """
    # TODO: Implement 2FA verification logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="2FA verify not yet implemented"
    )


@router.post("/close-account", status_code=status.HTTP_200_OK)
async def close_account(
    closure_data: schemas.AccountClosureRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Request account closure.
    
    - Requires password confirmation
    - Soft deletes the account
    - Cannot be undone
    """
    await services.UserService.close_account(
        db,
        current_user.id,
        closure_data.reason,
        closure_data.password
    )
    
    return {"message": "Account closed successfully"}
