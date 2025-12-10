from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class GovernmentIDType(str, enum.Enum):
    """Government ID type enumeration"""
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"


class ProofOfAddressType(str, enum.Enum):
    """Proof of address document type"""
    UTILITY_BILL = "utility_bill"
    BANK_STATEMENT = "bank_statement"
    TAX_BILL = "tax_bill"
    RENTAL_AGREEMENT = "rental_agreement"


class KYCDocumentStatus(str, enum.Enum):
    """KYC document verification status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class KYCDocument(Base):
    """KYC document model for identity verification"""
    __tablename__ = "kyc_documents"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Government ID Information
    government_id_type = Column(SQLEnum(GovernmentIDType), nullable=False)
    government_id_number = Column(String(100), nullable=False)
    government_id_front_url = Column(String(500), nullable=False)
    government_id_back_url = Column(String(500), nullable=True)
    
    # Selfie Verification
    selfie_with_id_url = Column(String(500), nullable=False)
    
    # Proof of Address
    proof_of_address_url = Column(String(500), nullable=False)
    proof_of_address_type = Column(SQLEnum(ProofOfAddressType), nullable=False)
    
    # Document Dates
    document_issue_date = Column(Date, nullable=False)
    document_expiry_date = Column(Date, nullable=True)
    
    # Verification Status
    status = Column(SQLEnum(KYCDocumentStatus), default=KYCDocumentStatus.PENDING, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    
    # Review Information
    reviewed_by = Column(Integer, nullable=True)  # Admin user ID
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="kyc_documents")
    
    def __repr__(self):
        return f"<KYCDocument(id={self.id}, user_id={self.user_id}, status={self.status})>"
