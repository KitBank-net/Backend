from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date, timedelta

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.modules.users.models import User
from app.modules.budgeting import schemas
from app.modules.budgeting.services import (
    SpendingCategoryService, BudgetService, SavingsGoalService, SpendingAnalyticsService
)
from app.modules.budgeting.models import GoalStatus, CategoryType

router = APIRouter(prefix="/api/v1/budgeting", tags=["budgeting"])


# ============ Spending Categories ============

@router.get("/categories", response_model=List[schemas.SpendingCategoryResponse])
async def get_categories(
    include_system: bool = Query(True, description="Include system categories"),
    category_type: Optional[str] = Query(None, description="Filter by category type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all spending categories.
    
    - Returns both system-defined and user-defined categories
    - Filter by category type if needed
    """
    categories = await SpendingCategoryService.get_categories(db, current_user.id)
    return categories


@router.get("/categories/types")
async def get_category_types(
    current_user: User = Depends(get_current_active_user)
):
    """Get all available category types"""
    return {
        "types": [
            {"value": t.value, "label": t.value.replace("_", " ").title()}
            for t in CategoryType
        ]
    }


@router.post("/categories", response_model=schemas.SpendingCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: schemas.SpendingCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a custom spending category.
    
    - User can define custom categories beyond system defaults
    - Add keywords for auto-categorization
    """
    category = await SpendingCategoryService.create_category(db, current_user.id, data)
    return category


@router.get("/categories/{category_id}", response_model=schemas.SpendingCategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific category details"""
    category = await SpendingCategoryService.get_category(db, category_id, current_user.id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/categories/{category_id}", response_model=schemas.SpendingCategoryResponse)
async def update_category(
    category_id: int,
    data: schemas.SpendingCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update custom category (cannot update system categories)"""
    category = await SpendingCategoryService.update_category(db, category_id, current_user.id, data)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found or cannot be modified")
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_200_OK)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete custom category (cannot delete system categories)"""
    success = await SpendingCategoryService.delete_category(db, category_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found or cannot be deleted")
    return {"message": "Category deleted successfully"}


@router.get("/categories/{category_id}/spending", response_model=schemas.CategorySpending)
async def get_category_spending(
    category_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get spending details for a specific category"""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    spending = await SpendingAnalyticsService.get_category_spending(
        db, current_user.id, category_id, start_date, end_date
    )
    if not spending:
        raise HTTPException(status_code=404, detail="Category not found")
    return spending


# ============ Budgets ============

@router.get("/budgets", response_model=List[schemas.BudgetResponse])
async def get_budgets(
    active_only: bool = Query(True, description="Show only active budgets"),
    period: Optional[str] = Query(None, description="Filter by period: weekly, monthly, yearly"),
    sort_by: str = Query("created_at", description="Sort by: created_at, amount, spent_percentage"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all user budgets.
    
    - Filter by active status
    - Filter by period type
    - Sort by various fields
    """
    budgets = await BudgetService.get_budgets(db, current_user.id, active_only)
    return [schemas.BudgetResponse(
        **{k: v for k, v in b.__dict__.items() if not k.startswith('_')},
        remaining_amount=b.remaining_amount,
        spent_percentage=b.spent_percentage,
        is_over_budget=b.is_over_budget
    ) for b in budgets]


@router.get("/budgets/summary", response_model=schemas.BudgetSummary)
async def get_budget_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get budget summary for dashboard.
    
    - Total budgeted vs spent
    - Count of budgets on track, over budget, and warning
    """
    summary = await BudgetService.get_budget_summary(db, current_user.id)
    return summary


@router.get("/budgets/alerts")
async def get_budget_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get budgets that are over threshold or over budget"""
    alerts = await BudgetService.get_budget_alerts(db, current_user.id)
    return {"alerts": alerts}


@router.get("/budgets/recommendations")
async def get_budget_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get AI-powered budget recommendations based on spending patterns"""
    recommendations = await BudgetService.get_budget_recommendations(db, current_user.id)
    return {"recommendations": recommendations}


@router.post("/budgets", response_model=schemas.BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: schemas.BudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new budget.
    
    - Set spending limit for a category
    - Choose period: weekly, monthly, or yearly
    - Set alert threshold percentage
    """
    budget = await BudgetService.create_budget(db, current_user.id, data)
    return schemas.BudgetResponse(
        **{k: v for k, v in budget.__dict__.items() if not k.startswith('_')},
        remaining_amount=budget.remaining_amount,
        spent_percentage=budget.spent_percentage,
        is_over_budget=budget.is_over_budget
    )


@router.get("/budgets/{budget_id}", response_model=schemas.BudgetResponse)
async def get_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific budget details"""
    budget = await BudgetService.get_budget(db, budget_id, current_user.id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return schemas.BudgetResponse(
        **{k: v for k, v in budget.__dict__.items() if not k.startswith('_')},
        remaining_amount=budget.remaining_amount,
        spent_percentage=budget.spent_percentage,
        is_over_budget=budget.is_over_budget
    )


@router.get("/budgets/{budget_id}/transactions")
async def get_budget_transactions(
    budget_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get transactions counted against this budget"""
    transactions = await BudgetService.get_budget_transactions(
        db, budget_id, current_user.id, skip, limit
    )
    return {"transactions": transactions}


@router.get("/budgets/{budget_id}/history")
async def get_budget_history(
    budget_id: int,
    months: int = Query(6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get historical spending for this budget over past periods"""
    history = await BudgetService.get_budget_history(db, budget_id, current_user.id, months)
    return {"history": history}


@router.put("/budgets/{budget_id}", response_model=schemas.BudgetResponse)
async def update_budget(
    budget_id: int,
    data: schemas.BudgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update budget amount, threshold, or status"""
    budget = await BudgetService.update_budget(db, budget_id, current_user.id, data)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return schemas.BudgetResponse(
        **{k: v for k, v in budget.__dict__.items() if not k.startswith('_')},
        remaining_amount=budget.remaining_amount,
        spent_percentage=budget.spent_percentage,
        is_over_budget=budget.is_over_budget
    )


@router.post("/budgets/{budget_id}/reset")
async def reset_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Reset budget spent amount for new period"""
    budget = await BudgetService.reset_budget(db, budget_id, current_user.id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget reset successfully", "budget_id": budget_id}


@router.post("/budgets/{budget_id}/duplicate", response_model=schemas.BudgetResponse)
async def duplicate_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Duplicate an existing budget with same settings"""
    budget = await BudgetService.duplicate_budget(db, budget_id, current_user.id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return schemas.BudgetResponse(
        **{k: v for k, v in budget.__dict__.items() if not k.startswith('_')},
        remaining_amount=budget.remaining_amount,
        spent_percentage=budget.spent_percentage,
        is_over_budget=budget.is_over_budget
    )


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_200_OK)
async def delete_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete budget"""
    success = await BudgetService.delete_budget(db, budget_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget deleted successfully"}


# ============ Savings Goals ============

@router.get("/goals", response_model=List[schemas.SavingsGoalResponse])
async def get_goals(
    status: Optional[str] = Query(None, description="Filter by status: active, completed, paused"),
    sort_by: str = Query("created_at", description="Sort by: created_at, target_date, progress"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all savings goals.
    
    - Filter by status
    - Track progress toward financial targets
    """
    goal_status = GoalStatus(status) if status else None
    goals = await SavingsGoalService.get_goals(db, current_user.id, goal_status)
    return [schemas.SavingsGoalResponse(
        **{k: v for k, v in g.__dict__.items() if not k.startswith('_')},
        progress_percentage=g.progress_percentage,
        remaining_amount=g.remaining_amount,
        is_completed=g.is_completed
    ) for g in goals]


@router.get("/goals/summary")
async def get_goals_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get summary of all savings goals"""
    summary = await SavingsGoalService.get_goals_summary(db, current_user.id)
    return summary


@router.get("/goals/upcoming")
async def get_upcoming_goals(
    days: int = Query(30, ge=1, le=365, description="Goals due within X days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get goals with upcoming target dates"""
    goals = await SavingsGoalService.get_upcoming_goals(db, current_user.id, days)
    return {"goals": goals}


@router.post("/goals", response_model=schemas.SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    data: schemas.SavingsGoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new savings goal.
    
    - Set target amount and optional deadline
    - Enable auto-save for automatic contributions
    - Link to specific account (optional)
    """
    goal = await SavingsGoalService.create_goal(db, current_user.id, data)
    return schemas.SavingsGoalResponse(
        **{k: v for k, v in goal.__dict__.items() if not k.startswith('_')},
        progress_percentage=goal.progress_percentage,
        remaining_amount=goal.remaining_amount,
        is_completed=goal.is_completed
    )


@router.get("/goals/{goal_id}", response_model=schemas.SavingsGoalResponse)
async def get_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific goal details"""
    goal = await SavingsGoalService.get_goal(db, goal_id, current_user.id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return schemas.SavingsGoalResponse(
        **{k: v for k, v in goal.__dict__.items() if not k.startswith('_')},
        progress_percentage=goal.progress_percentage,
        remaining_amount=goal.remaining_amount,
        is_completed=goal.is_completed
    )


@router.get("/goals/{goal_id}/contributions")
async def get_goal_contributions(
    goal_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get contribution history for a goal"""
    contributions = await SavingsGoalService.get_contributions(
        db, goal_id, current_user.id, skip, limit
    )
    return {"contributions": contributions}


@router.get("/goals/{goal_id}/projection")
async def get_goal_projection(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get projected completion date based on current savings rate"""
    projection = await SavingsGoalService.get_goal_projection(db, goal_id, current_user.id)
    if not projection:
        raise HTTPException(status_code=404, detail="Goal not found")
    return projection


@router.put("/goals/{goal_id}", response_model=schemas.SavingsGoalResponse)
async def update_goal(
    goal_id: int,
    data: schemas.SavingsGoalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update savings goal"""
    goal = await SavingsGoalService.update_goal(db, goal_id, current_user.id, data)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return schemas.SavingsGoalResponse(
        **{k: v for k, v in goal.__dict__.items() if not k.startswith('_')},
        progress_percentage=goal.progress_percentage,
        remaining_amount=goal.remaining_amount,
        is_completed=goal.is_completed
    )


@router.post("/goals/{goal_id}/contribute", response_model=schemas.SavingsGoalResponse)
async def contribute_to_goal(
    goal_id: int,
    data: schemas.SavingsGoalContribution,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add contribution to savings goal.
    
    - Manually add funds toward goal
    - Updates progress automatically
    - Marks goal complete when target reached
    """
    goal = await SavingsGoalService.contribute_to_goal(db, goal_id, current_user.id, data)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found or not active")
    return schemas.SavingsGoalResponse(
        **{k: v for k, v in goal.__dict__.items() if not k.startswith('_')},
        progress_percentage=goal.progress_percentage,
        remaining_amount=goal.remaining_amount,
        is_completed=goal.is_completed
    )


@router.post("/goals/{goal_id}/withdraw")
async def withdraw_from_goal(
    goal_id: int,
    data: schemas.SavingsGoalContribution,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Withdraw funds from savings goal"""
    goal = await SavingsGoalService.withdraw_from_goal(db, goal_id, current_user.id, data)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found or insufficient funds")
    return schemas.SavingsGoalResponse(
        **{k: v for k, v in goal.__dict__.items() if not k.startswith('_')},
        progress_percentage=goal.progress_percentage,
        remaining_amount=goal.remaining_amount,
        is_completed=goal.is_completed
    )


@router.post("/goals/{goal_id}/pause")
async def pause_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Pause a savings goal"""
    goal = await SavingsGoalService.update_goal_status(db, goal_id, current_user.id, GoalStatus.PAUSED)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"message": "Goal paused successfully"}


@router.post("/goals/{goal_id}/resume")
async def resume_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Resume a paused goal"""
    goal = await SavingsGoalService.update_goal_status(db, goal_id, current_user.id, GoalStatus.ACTIVE)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"message": "Goal resumed successfully"}


@router.delete("/goals/{goal_id}", status_code=status.HTTP_200_OK)
async def delete_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete savings goal"""
    success = await SavingsGoalService.delete_goal(db, goal_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"message": "Goal deleted successfully"}


# ============ Spending Analytics ============

@router.get("/spending/summary", response_model=schemas.SpendingSummary)
async def get_spending_summary(
    start_date: Optional[date] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get spending summary by category.
    
    - Total income vs expenses
    - Net savings
    - Breakdown by category with percentages
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    summary = await SpendingAnalyticsService.get_spending_summary(db, current_user.id, start_date, end_date)
    return summary


@router.get("/spending/trends", response_model=schemas.SpendingTrendsResponse)
async def get_spending_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get monthly spending trends.
    
    - Historical spending over months
    - Identify highest/lowest spending periods
    - Average monthly spending
    """
    trends = await SpendingAnalyticsService.get_spending_trends(db, current_user.id, months)
    return trends


@router.get("/spending/daily")
async def get_daily_spending(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get daily spending breakdown"""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    daily = await SpendingAnalyticsService.get_daily_spending(db, current_user.id, start_date, end_date)
    return {"daily_spending": daily}


@router.get("/spending/comparison")
async def get_spending_comparison(
    period1_start: date = Query(..., description="First period start"),
    period1_end: date = Query(..., description="First period end"),
    period2_start: date = Query(..., description="Second period start"),
    period2_end: date = Query(..., description="Second period end"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Compare spending between two time periods"""
    comparison = await SpendingAnalyticsService.compare_periods(
        db, current_user.id,
        period1_start, period1_end,
        period2_start, period2_end
    )
    return comparison


@router.get("/spending/top-merchants")
async def get_top_merchants(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get top merchants/payees by spending"""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    merchants = await SpendingAnalyticsService.get_top_merchants(
        db, current_user.id, start_date, end_date, limit
    )
    return {"merchants": merchants}


@router.get("/spending/recurring")
async def get_recurring_expenses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Identify recurring/subscription expenses"""
    recurring = await SpendingAnalyticsService.get_recurring_expenses(db, current_user.id)
    return {"recurring_expenses": recurring}


# ============ Insights & Reports ============

@router.get("/insights")
async def get_spending_insights(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get AI-generated spending insights.
    
    - Spending pattern analysis
    - Budget recommendations
    - Savings opportunities
    """
    insights = await SpendingAnalyticsService.get_insights(db, current_user.id, limit)
    return {"insights": insights}


@router.get("/insights/{insight_id}")
async def get_insight_detail(
    insight_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific insight details"""
    insight = await SpendingAnalyticsService.get_insight(db, insight_id, current_user.id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight


@router.put("/insights/{insight_id}/dismiss")
async def dismiss_insight(
    insight_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Dismiss an insight"""
    success = await SpendingAnalyticsService.dismiss_insight(db, insight_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"message": "Insight dismissed"}


@router.get("/reports/monthly")
async def get_monthly_report(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate monthly financial report"""
    report = await SpendingAnalyticsService.generate_monthly_report(db, current_user.id, month, year)
    return report


@router.get("/reports/annual")
async def get_annual_report(
    year: int = Query(..., ge=2020),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate annual financial summary"""
    report = await SpendingAnalyticsService.generate_annual_report(db, current_user.id, year)
    return report


@router.get("/reports/export")
async def export_financial_data(
    start_date: date = Query(...),
    end_date: date = Query(...),
    format: str = Query("json", description="Export format: json, csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export financial data for external use"""
    data = await SpendingAnalyticsService.export_data(
        db, current_user.id, start_date, end_date, format
    )
    return data


# ============ Financial Health ============

@router.get("/health-score")
async def get_financial_health_score(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get overall financial health score (0-100).
    
    Based on:
    - Budget adherence
    - Savings rate
    - Spending patterns
    - Goal progress
    """
    score = await SpendingAnalyticsService.calculate_health_score(db, current_user.id)
    return score


@router.get("/health-tips")
async def get_financial_health_tips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get personalized tips to improve financial health"""
    tips = await SpendingAnalyticsService.get_health_tips(db, current_user.id)
    return {"tips": tips}
