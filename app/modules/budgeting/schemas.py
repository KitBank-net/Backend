from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


class CategoryTypeEnum(str, Enum):
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


class BudgetPeriodEnum(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class GoalStatusEnum(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


# ============ Spending Category Schemas ============

class SpendingCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    category_type: CategoryTypeEnum
    icon: Optional[str] = None
    color: Optional[str] = None
    keywords: Optional[List[str]] = None


class SpendingCategoryCreate(SpendingCategoryBase):
    pass


class SpendingCategoryUpdate(BaseModel):
    """Schema for updating category (all optional)"""
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    keywords: Optional[List[str]] = None
    is_active: Optional[bool] = None


class SpendingCategoryResponse(SpendingCategoryBase):
    id: int
    user_id: Optional[int] = None
    is_system: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Budget Schemas ============

class BudgetBase(BaseModel):
    name: str = Field(..., max_length=100)
    category_id: int
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    period: BudgetPeriodEnum = BudgetPeriodEnum.MONTHLY
    alert_threshold: float = Field(default=80.0, ge=0, le=100)
    alert_enabled: bool = True


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    alert_threshold: Optional[float] = None
    alert_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class BudgetResponse(BudgetBase):
    id: int
    user_id: int
    spent_amount: float
    period_start_date: date
    period_end_date: date
    is_active: bool
    remaining_amount: float
    spent_percentage: float
    is_over_budget: bool
    created_at: datetime
    category: Optional[SpendingCategoryResponse] = None

    class Config:
        from_attributes = True


class BudgetSummary(BaseModel):
    total_budgeted: float
    total_spent: float
    total_remaining: float
    budgets_on_track: int
    budgets_over: int
    budgets_warning: int  # Above alert threshold


# ============ Savings Goal Schemas ============

class SavingsGoalBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    target_amount: float = Field(..., gt=0)
    currency: str = "USD"
    target_date: Optional[date] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class SavingsGoalCreate(SavingsGoalBase):
    account_id: Optional[int] = None
    auto_save_enabled: bool = False
    auto_save_amount: Optional[float] = None
    auto_save_frequency: Optional[BudgetPeriodEnum] = None


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[float] = None
    target_date: Optional[date] = None
    status: Optional[GoalStatusEnum] = None
    auto_save_enabled: Optional[bool] = None
    auto_save_amount: Optional[float] = None


class SavingsGoalContribution(BaseModel):
    amount: float = Field(..., gt=0)
    note: Optional[str] = None


class SavingsGoalResponse(SavingsGoalBase):
    id: int
    user_id: int
    account_id: Optional[int] = None
    current_amount: float
    status: GoalStatusEnum
    progress_percentage: float
    remaining_amount: float
    is_completed: bool
    auto_save_enabled: bool
    auto_save_amount: Optional[float] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Spending Analytics Schemas ============

class CategorySpending(BaseModel):
    category_id: int
    category_name: str
    category_type: CategoryTypeEnum
    total_spent: float
    transaction_count: int
    percentage_of_total: float
    color: Optional[str] = None


class SpendingSummary(BaseModel):
    period_start: date
    period_end: date
    total_income: float
    total_expenses: float
    net_savings: float
    spending_by_category: List[CategorySpending]


class SpendingTrend(BaseModel):
    period: str  # "2025-01", "2025-02"
    total_spent: float
    total_income: float
    net: float


class SpendingTrendsResponse(BaseModel):
    trends: List[SpendingTrend]
    average_monthly_spending: float
    average_monthly_income: float
    highest_spending_month: Optional[str] = None
    lowest_spending_month: Optional[str] = None


# ============ Spending Insight Schemas ============

class SpendingInsightResponse(BaseModel):
    id: int
    insight_type: str
    title: str
    message: str
    category_id: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
