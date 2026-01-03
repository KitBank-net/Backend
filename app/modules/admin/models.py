from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class AdminRole(str, enum.Enum):
    """Admin role levels"""
    SUPER_ADMIN = "super_admin"         # Full access
    ADMIN = "admin"                      # Most operations
    LOAN_OFFICER = "loan_officer"        # Loan approvals
    SUPPORT = "support"                  # Customer support
    COMPLIANCE = "compliance"            # KYC/AML
    AUDITOR = "auditor"                  # Read-only access


class AdminPermission(str, enum.Enum):
    """Granular permissions"""
    # User management
    VIEW_USERS = "view_users"
    EDIT_USERS = "edit_users"
    SUSPEND_USERS = "suspend_users"
    DELETE_USERS = "delete_users"
    
    # KYC
    VIEW_KYC = "view_kyc"
    APPROVE_KYC = "approve_kyc"
    REJECT_KYC = "reject_kyc"
    
    # Accounts
    VIEW_ACCOUNTS = "view_accounts"
    FREEZE_ACCOUNTS = "freeze_accounts"
    CLOSE_ACCOUNTS = "close_accounts"
    
    # Transactions
    VIEW_TRANSACTIONS = "view_transactions"
    REVERSE_TRANSACTIONS = "reverse_transactions"
    REFUND_TRANSACTIONS = "refund_transactions"
    
    # Loans
    VIEW_LOANS = "view_loans"
    APPROVE_LOANS = "approve_loans"
    REJECT_LOANS = "reject_loans"
    DISBURSE_LOANS = "disburse_loans"
    
    # Cards
    VIEW_CARDS = "view_cards"
    BLOCK_CARDS = "block_cards"
    
    # Settings
    VIEW_SETTINGS = "view_settings"
    EDIT_SETTINGS = "edit_settings"
    MANAGE_FEES = "manage_fees"
    MANAGE_PRODUCTS = "manage_products"
    
    # Reports
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"
    
    # Audit
    VIEW_AUDIT_LOGS = "view_audit_logs"


class AdminUser(Base):
    """Admin users with role-based access"""
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to regular user (optional)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    
    # Admin credentials (if separate from user)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=True)
    
    # Role
    role = Column(SQLEnum(AdminRole), nullable=False, default=AdminRole.SUPPORT)
    
    # Custom permissions (JSON-like string for flexibility)
    custom_permissions = Column(Text, nullable=True)  # Comma-separated permissions
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Security
    two_factor_enabled = Column(Boolean, default=True, nullable=False)
    two_factor_secret = Column(String(255), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AdminUser(id={self.id}, email={self.email}, role={self.role})>"


class AuditLog(Base):
    """Audit log for all admin actions"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Who
    admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    admin_email = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # What
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)  # user, loan, transaction, etc.
    resource_id = Column(Integer, nullable=True)
    
    # Details
    description = Column(Text, nullable=True)
    old_values = Column(Text, nullable=True)  # JSON
    new_values = Column(Text, nullable=True)  # JSON
    
    # Result
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # When
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    admin = relationship("AdminUser", foreign_keys=[admin_id])
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_type})>"


class SystemSetting(Base):
    """System-wide configuration settings"""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), nullable=False, default="string")  # string, int, float, bool, json
    
    category = Column(String(50), nullable=False, index=True)  # general, security, limits, fees, etc.
    description = Column(Text, nullable=True)
    
    is_sensitive = Column(Boolean, default=False, nullable=False)  # Hide from logs
    is_readonly = Column(Boolean, default=False, nullable=False)  # Can't edit via UI
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("admin_users.id"), nullable=True)


# Role to default permissions mapping
ROLE_PERMISSIONS = {
    AdminRole.SUPER_ADMIN: list(AdminPermission),  # All permissions
    AdminRole.ADMIN: [
        AdminPermission.VIEW_USERS, AdminPermission.EDIT_USERS, AdminPermission.SUSPEND_USERS,
        AdminPermission.VIEW_KYC, AdminPermission.APPROVE_KYC, AdminPermission.REJECT_KYC,
        AdminPermission.VIEW_ACCOUNTS, AdminPermission.FREEZE_ACCOUNTS,
        AdminPermission.VIEW_TRANSACTIONS, AdminPermission.REVERSE_TRANSACTIONS,
        AdminPermission.VIEW_LOANS, AdminPermission.APPROVE_LOANS, AdminPermission.REJECT_LOANS, AdminPermission.DISBURSE_LOANS,
        AdminPermission.VIEW_CARDS, AdminPermission.BLOCK_CARDS,
        AdminPermission.VIEW_SETTINGS, AdminPermission.MANAGE_FEES, AdminPermission.MANAGE_PRODUCTS,
        AdminPermission.VIEW_REPORTS, AdminPermission.EXPORT_REPORTS,
        AdminPermission.VIEW_AUDIT_LOGS
    ],
    AdminRole.LOAN_OFFICER: [
        AdminPermission.VIEW_USERS,
        AdminPermission.VIEW_KYC,
        AdminPermission.VIEW_ACCOUNTS,
        AdminPermission.VIEW_LOANS, AdminPermission.APPROVE_LOANS, AdminPermission.REJECT_LOANS, AdminPermission.DISBURSE_LOANS,
        AdminPermission.VIEW_REPORTS
    ],
    AdminRole.SUPPORT: [
        AdminPermission.VIEW_USERS, AdminPermission.EDIT_USERS,
        AdminPermission.VIEW_ACCOUNTS,
        AdminPermission.VIEW_TRANSACTIONS,
        AdminPermission.VIEW_LOANS,
        AdminPermission.VIEW_CARDS, AdminPermission.BLOCK_CARDS
    ],
    AdminRole.COMPLIANCE: [
        AdminPermission.VIEW_USERS,
        AdminPermission.VIEW_KYC, AdminPermission.APPROVE_KYC, AdminPermission.REJECT_KYC,
        AdminPermission.VIEW_ACCOUNTS, AdminPermission.FREEZE_ACCOUNTS,
        AdminPermission.VIEW_TRANSACTIONS,
        AdminPermission.VIEW_REPORTS, AdminPermission.EXPORT_REPORTS,
        AdminPermission.VIEW_AUDIT_LOGS
    ],
    AdminRole.AUDITOR: [
        AdminPermission.VIEW_USERS,
        AdminPermission.VIEW_KYC,
        AdminPermission.VIEW_ACCOUNTS,
        AdminPermission.VIEW_TRANSACTIONS,
        AdminPermission.VIEW_LOANS,
        AdminPermission.VIEW_CARDS,
        AdminPermission.VIEW_SETTINGS,
        AdminPermission.VIEW_REPORTS, AdminPermission.EXPORT_REPORTS,
        AdminPermission.VIEW_AUDIT_LOGS
    ]
}
