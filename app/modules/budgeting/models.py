from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class CategoryType(str, enum.Enum):
    """Default spending categories"""
    FOOD_DINING = "food_dining"
    TRANSPORTATION = "transportation"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    BILLS_UTILITIES = "bills_utilities"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    TRAVEL = "travel"
    GROCERIES = "groceries"
    PERSONAL_CARE = "personal_care"
    INVESTMENTS = "investments"
    TRANSFERS = "transfers"
    INCOME = "income"
    OTHER = "other"


class BudgetPeriod(str, enum.Enum):
    """Budget period type"""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class GoalStatus(str, enum.Enum):
    """Savings goal status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class SpendingCategory(Base):
    """
    Spending categories for transaction classification.
    Includes both system defaults and user-defined categories.
    """
    __tablename__ = "spending_categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL = system category
    
    name = Column(String(100), nullable=False)
    category_type = Column(SQLEnum(CategoryType), nullable=False)
    icon = Column(String(50), nullable=True)  # Icon name for UI
    color = Column(String(7), nullable=True)  # Hex color code
    
    is_system = Column(Boolean, default=False, nullable=False)  # System-defined vs user-defined
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Keywords for auto-categorization
    keywords = Column(JSON, nullable=True)  # ["uber", "lyft", "taxi"]
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="spending_categories", lazy="selectin")
    budgets = relationship("Budget", back_populates="category", lazy="selectin")

    def __repr__(self):
        return f"<SpendingCategory(id={self.id}, name={self.name}, type={self.category_type})>"


class Budget(Base):
    """
    Budget allocation for spending categories.
    Users can set limits per category with alerts.
    """
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("spending_categories.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)  # Budget limit
    currency = Column(String(3), default="USD", nullable=False)
    period = Column(SQLEnum(BudgetPeriod), default=BudgetPeriod.MONTHLY, nullable=False)
    
    # Current period tracking
    spent_amount = Column(Float, default=0.0, nullable=False)
    period_start_date = Column(Date, nullable=False)
    period_end_date = Column(Date, nullable=False)
    
    # Alerts
    alert_threshold = Column(Float, default=80.0, nullable=False)  # Alert at 80% spent
    alert_enabled = Column(Boolean, default=True, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="budgets", lazy="selectin")
    category = relationship("SpendingCategory", back_populates="budgets", lazy="selectin")

    @property
    def remaining_amount(self) -> float:
        """Calculate remaining budget"""
        return max(0, self.amount - self.spent_amount)

    @property
    def spent_percentage(self) -> float:
        """Calculate percentage spent"""
        if self.amount == 0:
            return 0
        return min(100, (self.spent_amount / self.amount) * 100)

    @property
    def is_over_budget(self) -> bool:
        """Check if over budget"""
        return self.spent_amount > self.amount

    def __repr__(self):
        return f"<Budget(id={self.id}, name={self.name}, amount={self.amount}, spent={self.spent_amount})>"


class SavingsGoal(Base):
    """
    Savings goals for users to track progress toward financial targets.
    """
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)  # Optional linked account
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Goal timeline
    target_date = Column(Date, nullable=True)
    status = Column(SQLEnum(GoalStatus), default=GoalStatus.ACTIVE, nullable=False)
    
    # Visual customization
    icon = Column(String(50), nullable=True)
    color = Column(String(7), nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # Auto-save settings
    auto_save_enabled = Column(Boolean, default=False, nullable=False)
    auto_save_amount = Column(Float, nullable=True)  # Amount to auto-save
    auto_save_frequency = Column(SQLEnum(BudgetPeriod), nullable=True)  # weekly, monthly
    
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="savings_goals", lazy="selectin")

    @property
    def progress_percentage(self) -> float:
        """Calculate progress toward goal"""
        if self.target_amount == 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)

    @property
    def remaining_amount(self) -> float:
        """Amount remaining to reach goal"""
        return max(0, self.target_amount - self.current_amount)

    @property
    def is_completed(self) -> bool:
        """Check if goal is reached"""
        return self.current_amount >= self.target_amount

    def __repr__(self):
        return f"<SavingsGoal(id={self.id}, name={self.name}, target={self.target_amount}, current={self.current_amount})>"


class SpendingInsight(Base):
    """
    AI-generated spending insights and recommendations.
    """
    __tablename__ = "spending_insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    insight_type = Column(String(50), nullable=False)  # spending_trend, budget_alert, saving_tip
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Related data
    category_id = Column(Integer, ForeignKey("spending_categories.id"), nullable=True)
    data = Column(JSON, nullable=True)  # Additional insight data
    
    is_read = Column(Boolean, default=False, nullable=False)
    is_dismissed = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", backref="spending_insights", lazy="selectin")
    category = relationship("SpendingCategory", lazy="selectin")

    def __repr__(self):
        return f"<SpendingInsight(id={self.id}, type={self.insight_type}, title={self.title})>"
