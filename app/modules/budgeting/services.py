from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update, extract
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Tuple, Any
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import logging

from app.modules.budgeting.models import (
    SpendingCategory, Budget, SavingsGoal, SpendingInsight,
    CategoryType, BudgetPeriod, GoalStatus
)
from app.modules.budgeting.schemas import (
    SpendingCategoryCreate, SpendingCategoryUpdate, BudgetCreate, BudgetUpdate,
    SavingsGoalCreate, SavingsGoalUpdate, SavingsGoalContribution,
    CategorySpending, SpendingSummary, SpendingTrend
)
from app.modules.transactions.models import Transaction
from app.modules.accounts.models import Account

logger = logging.getLogger(__name__)


class SpendingCategoryService:
    """Service for managing spending categories"""

    @staticmethod
    async def get_categories(db: AsyncSession, user_id: int) -> List[SpendingCategory]:
        """Get all categories (system + user-defined)"""
        query = select(SpendingCategory).where(
            (SpendingCategory.user_id == user_id) | (SpendingCategory.is_system == True)
        ).where(SpendingCategory.is_active == True)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_category(db: AsyncSession, category_id: int, user_id: int) -> Optional[SpendingCategory]:
        """Get specific category"""
        query = select(SpendingCategory).where(
            and_(
                SpendingCategory.id == category_id,
                (SpendingCategory.user_id == user_id) | (SpendingCategory.is_system == True)
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_category(db: AsyncSession, user_id: int, data: SpendingCategoryCreate) -> SpendingCategory:
        """Create user-defined category"""
        category = SpendingCategory(
            user_id=user_id,
            name=data.name,
            category_type=CategoryType(data.category_type.value),
            icon=data.icon,
            color=data.color,
            keywords=data.keywords,
            is_system=False
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def update_category(db: AsyncSession, category_id: int, user_id: int, data: SpendingCategoryUpdate) -> Optional[SpendingCategory]:
        """Update user-defined category (cannot update system categories)"""
        query = select(SpendingCategory).where(
            and_(SpendingCategory.id == category_id, SpendingCategory.user_id == user_id, SpendingCategory.is_system == False)
        )
        result = await db.execute(query)
        category = result.scalar_one_or_none()
        
        if not category:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def delete_category(db: AsyncSession, category_id: int, user_id: int) -> bool:
        """Delete user-defined category (cannot delete system categories)"""
        query = select(SpendingCategory).where(
            and_(SpendingCategory.id == category_id, SpendingCategory.user_id == user_id, SpendingCategory.is_system == False)
        )
        result = await db.execute(query)
        category = result.scalar_one_or_none()
        
        if not category:
            return False
        
        await db.delete(category)
        await db.commit()
        return True

    @staticmethod
    async def init_system_categories(db: AsyncSession) -> None:
        """Initialize default system categories"""
        default_categories = [
            {"name": "Food & Dining", "type": CategoryType.FOOD_DINING, "icon": "restaurant", "color": "#FF6B6B"},
            {"name": "Transportation", "type": CategoryType.TRANSPORTATION, "icon": "car", "color": "#4ECDC4"},
            {"name": "Shopping", "type": CategoryType.SHOPPING, "icon": "shopping_bag", "color": "#45B7D1"},
            {"name": "Entertainment", "type": CategoryType.ENTERTAINMENT, "icon": "movie", "color": "#96CEB4"},
            {"name": "Bills & Utilities", "type": CategoryType.BILLS_UTILITIES, "icon": "receipt", "color": "#FFEAA7"},
            {"name": "Healthcare", "type": CategoryType.HEALTHCARE, "icon": "medical", "color": "#DDA0DD"},
            {"name": "Groceries", "type": CategoryType.GROCERIES, "icon": "cart", "color": "#98D8C8"},
            {"name": "Other", "type": CategoryType.OTHER, "icon": "more", "color": "#B8B8B8"},
        ]

        for cat_data in default_categories:
            existing = await db.execute(
                select(SpendingCategory).where(
                    and_(SpendingCategory.is_system == True, SpendingCategory.category_type == cat_data["type"])
                )
            )
            if not existing.scalar_one_or_none():
                category = SpendingCategory(
                    name=cat_data["name"],
                    category_type=cat_data["type"],
                    icon=cat_data["icon"],
                    color=cat_data["color"],
                    is_system=True,
                    user_id=None
                )
                db.add(category)

        await db.commit()


class BudgetService:
    """Service for managing budgets"""

    @staticmethod
    def _get_period_dates(period: BudgetPeriod, reference_date: date = None) -> Tuple[date, date]:
        """Calculate period start and end dates"""
        if reference_date is None:
            reference_date = date.today()

        if period == BudgetPeriod.WEEKLY:
            start = reference_date - timedelta(days=reference_date.weekday())
            end = start + timedelta(days=6)
        elif period == BudgetPeriod.MONTHLY:
            start = reference_date.replace(day=1)
            end = (start + relativedelta(months=1)) - timedelta(days=1)
        else:  # YEARLY
            start = reference_date.replace(month=1, day=1)
            end = reference_date.replace(month=12, day=31)

        return start, end

    @staticmethod
    async def get_budgets(db: AsyncSession, user_id: int, active_only: bool = True) -> List[Budget]:
        """Get all user budgets"""
        query = select(Budget).where(Budget.user_id == user_id)
        if active_only:
            query = query.where(Budget.is_active == True)
        query = query.options(selectinload(Budget.category))
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_budget(db: AsyncSession, budget_id: int, user_id: int) -> Optional[Budget]:
        """Get specific budget"""
        query = select(Budget).where(
            and_(Budget.id == budget_id, Budget.user_id == user_id)
        ).options(selectinload(Budget.category))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_budget(db: AsyncSession, user_id: int, data: BudgetCreate) -> Budget:
        """Create a new budget"""
        period = BudgetPeriod(data.period.value)
        start_date, end_date = BudgetService._get_period_dates(period)

        budget = Budget(
            user_id=user_id,
            category_id=data.category_id,
            name=data.name,
            amount=data.amount,
            currency=data.currency,
            period=period,
            period_start_date=start_date,
            period_end_date=end_date,
            alert_threshold=data.alert_threshold,
            alert_enabled=data.alert_enabled,
            spent_amount=0.0
        )
        db.add(budget)
        await db.commit()
        await db.refresh(budget)
        return budget

    @staticmethod
    async def update_budget(db: AsyncSession, budget_id: int, user_id: int, data: BudgetUpdate) -> Optional[Budget]:
        """Update budget"""
        budget = await BudgetService.get_budget(db, budget_id, user_id)
        if not budget:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(budget, field, value)

        await db.commit()
        await db.refresh(budget)
        return budget

    @staticmethod
    async def delete_budget(db: AsyncSession, budget_id: int, user_id: int) -> bool:
        """Delete budget"""
        budget = await BudgetService.get_budget(db, budget_id, user_id)
        if not budget:
            return False
        await db.delete(budget)
        await db.commit()
        return True

    @staticmethod
    async def reset_budget(db: AsyncSession, budget_id: int, user_id: int) -> Optional[Budget]:
        """Reset budget for new period"""
        budget = await BudgetService.get_budget(db, budget_id, user_id)
        if not budget:
            return None
        
        budget.spent_amount = 0.0
        start_date, end_date = BudgetService._get_period_dates(budget.period)
        budget.period_start_date = start_date
        budget.period_end_date = end_date
        
        await db.commit()
        await db.refresh(budget)
        return budget

    @staticmethod
    async def duplicate_budget(db: AsyncSession, budget_id: int, user_id: int) -> Optional[Budget]:
        """Duplicate budget with same settings"""
        original = await BudgetService.get_budget(db, budget_id, user_id)
        if not original:
            return None
        
        start_date, end_date = BudgetService._get_period_dates(original.period)
        
        new_budget = Budget(
            user_id=user_id,
            category_id=original.category_id,
            name=f"{original.name} (Copy)",
            amount=original.amount,
            currency=original.currency,
            period=original.period,
            period_start_date=start_date,
            period_end_date=end_date,
            alert_threshold=original.alert_threshold,
            alert_enabled=original.alert_enabled,
            spent_amount=0.0
        )
        db.add(new_budget)
        await db.commit()
        await db.refresh(new_budget)
        return new_budget

    @staticmethod
    async def get_budget_summary(db: AsyncSession, user_id: int) -> Dict:
        """Get budget summary for dashboard"""
        budgets = await BudgetService.get_budgets(db, user_id)

        total_budgeted = sum(b.amount for b in budgets)
        total_spent = sum(b.spent_amount for b in budgets)
        
        budgets_on_track = sum(1 for b in budgets if b.spent_percentage < b.alert_threshold)
        budgets_warning = sum(1 for b in budgets if b.alert_threshold <= b.spent_percentage < 100)
        budgets_over = sum(1 for b in budgets if b.is_over_budget)

        return {
            "total_budgeted": total_budgeted,
            "total_spent": total_spent,
            "total_remaining": total_budgeted - total_spent,
            "budgets_on_track": budgets_on_track,
            "budgets_warning": budgets_warning,
            "budgets_over": budgets_over
        }

    @staticmethod
    async def get_budget_alerts(db: AsyncSession, user_id: int) -> List[Dict]:
        """Get budgets that need attention"""
        budgets = await BudgetService.get_budgets(db, user_id)
        alerts = []
        
        for budget in budgets:
            if budget.is_over_budget:
                alerts.append({
                    "budget_id": budget.id,
                    "name": budget.name,
                    "type": "over_budget",
                    "message": f"Budget exceeded by {budget.currency} {budget.spent_amount - budget.amount:.2f}",
                    "severity": "high"
                })
            elif budget.spent_percentage >= budget.alert_threshold:
                alerts.append({
                    "budget_id": budget.id,
                    "name": budget.name,
                    "type": "threshold_warning",
                    "message": f"Spent {budget.spent_percentage:.0f}% of budget",
                    "severity": "medium"
                })
        
        return alerts

    @staticmethod
    async def get_budget_recommendations(db: AsyncSession, user_id: int) -> List[Dict]:
        """Get budget recommendations based on spending"""
        budgets = await BudgetService.get_budgets(db, user_id)
        recommendations = []
        
        for budget in budgets:
            if budget.is_over_budget:
                recommendations.append({
                    "type": "increase_budget",
                    "budget_id": budget.id,
                    "message": f"Consider increasing your {budget.name} budget",
                    "suggested_amount": budget.spent_amount * 1.2
                })
            elif budget.spent_percentage < 50:
                recommendations.append({
                    "type": "reduce_budget",
                    "budget_id": budget.id,
                    "message": f"You might be able to reduce your {budget.name} budget",
                    "suggested_amount": budget.amount * 0.8
                })
        
        return recommendations

    @staticmethod
    async def get_budget_transactions(db: AsyncSession, budget_id: int, user_id: int, skip: int, limit: int) -> List[Dict]:
        """Get transactions for a budget period"""
        budget = await BudgetService.get_budget(db, budget_id, user_id)
        if not budget:
            return []
        
        # Get user accounts
        accounts_query = select(Account.id).where(Account.user_id == user_id)
        result = await db.execute(accounts_query)
        account_ids = list(result.scalars().all())
        
        if not account_ids:
            return []
        
        # Get transactions in budget period
        txn_query = select(Transaction).where(
            and_(
                Transaction.account_id.in_(account_ids),
                func.date(Transaction.created_at) >= budget.period_start_date,
                func.date(Transaction.created_at) <= budget.period_end_date,
                Transaction.transaction_type == "debit"
            )
        ).offset(skip).limit(limit)
        
        result = await db.execute(txn_query)
        transactions = result.scalars().all()
        
        return [{"id": t.id, "amount": t.amount, "date": str(t.created_at), "reference": t.reference_code} for t in transactions]

    @staticmethod
    async def get_budget_history(db: AsyncSession, budget_id: int, user_id: int, months: int) -> List[Dict]:
        """Get historical spending for this budget"""
        budget = await BudgetService.get_budget(db, budget_id, user_id)
        if not budget:
            return []
        
        history = []
        for i in range(months):
            period_date = date.today() - relativedelta(months=i)
            history.append({
                "period": period_date.strftime("%Y-%m"),
                "budgeted": budget.amount,
                "spent": budget.spent_amount if i == 0 else 0,  # Simplified
                "remaining": budget.remaining_amount if i == 0 else budget.amount
            })
        
        return history


class SavingsGoalService:
    """Service for managing savings goals"""

    @staticmethod
    async def get_goals(db: AsyncSession, user_id: int, status: Optional[GoalStatus] = None) -> List[SavingsGoal]:
        """Get user savings goals"""
        query = select(SavingsGoal).where(SavingsGoal.user_id == user_id)
        if status:
            query = query.where(SavingsGoal.status == status)
        query = query.order_by(SavingsGoal.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_goal(db: AsyncSession, goal_id: int, user_id: int) -> Optional[SavingsGoal]:
        """Get specific goal"""
        query = select(SavingsGoal).where(
            and_(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_goal(db: AsyncSession, user_id: int, data: SavingsGoalCreate) -> SavingsGoal:
        """Create savings goal"""
        goal = SavingsGoal(
            user_id=user_id,
            account_id=data.account_id,
            name=data.name,
            description=data.description,
            target_amount=data.target_amount,
            currency=data.currency,
            target_date=data.target_date,
            icon=data.icon,
            color=data.color,
            auto_save_enabled=data.auto_save_enabled,
            auto_save_amount=data.auto_save_amount,
            auto_save_frequency=BudgetPeriod(data.auto_save_frequency.value) if data.auto_save_frequency else None
        )
        db.add(goal)
        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def update_goal(db: AsyncSession, goal_id: int, user_id: int, data: SavingsGoalUpdate) -> Optional[SavingsGoal]:
        """Update goal"""
        goal = await SavingsGoalService.get_goal(db, goal_id, user_id)
        if not goal:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data:
            update_data["status"] = GoalStatus(update_data["status"])

        for field, value in update_data.items():
            setattr(goal, field, value)

        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def update_goal_status(db: AsyncSession, goal_id: int, user_id: int, status: GoalStatus) -> Optional[SavingsGoal]:
        """Update goal status"""
        goal = await SavingsGoalService.get_goal(db, goal_id, user_id)
        if not goal:
            return None
        
        goal.status = status
        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def contribute_to_goal(
        db: AsyncSession, 
        goal_id: int, 
        user_id: int, 
        data: SavingsGoalContribution
    ) -> Optional[SavingsGoal]:
        """Add contribution to goal"""
        goal = await SavingsGoalService.get_goal(db, goal_id, user_id)
        if not goal or goal.status != GoalStatus.ACTIVE:
            return None

        goal.current_amount += data.amount

        if goal.is_completed:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def withdraw_from_goal(
        db: AsyncSession,
        goal_id: int,
        user_id: int,
        data: SavingsGoalContribution
    ) -> Optional[SavingsGoal]:
        """Withdraw from goal"""
        goal = await SavingsGoalService.get_goal(db, goal_id, user_id)
        if not goal or goal.current_amount < data.amount:
            return None
        
        goal.current_amount -= data.amount
        
        if goal.status == GoalStatus.COMPLETED and goal.current_amount < goal.target_amount:
            goal.status = GoalStatus.ACTIVE
            goal.completed_at = None
        
        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def get_contributions(db: AsyncSession, goal_id: int, user_id: int, skip: int, limit: int) -> List[Dict]:
        """Get contribution history (simplified)"""
        goal = await SavingsGoalService.get_goal(db, goal_id, user_id)
        if not goal:
            return []
        
        return [{
            "date": str(goal.created_at),
            "amount": goal.current_amount,
            "type": "initial"
        }]

    @staticmethod
    async def get_goal_projection(db: AsyncSession, goal_id: int, user_id: int) -> Optional[Dict]:
        """Project goal completion date"""
        goal = await SavingsGoalService.get_goal(db, goal_id, user_id)
        if not goal:
            return None
        
        if goal.is_completed:
            return {
                "status": "completed",
                "completed_at": str(goal.completed_at),
                "days_taken": (goal.completed_at.date() - goal.created_at.date()).days if goal.completed_at else 0
            }
        
        monthly_rate = goal.auto_save_amount if goal.auto_save_enabled else goal.current_amount / max(1, (date.today() - goal.created_at.date()).days / 30)
        
        if monthly_rate > 0:
            months_remaining = goal.remaining_amount / monthly_rate
            projected_date = date.today() + relativedelta(months=int(months_remaining))
        else:
            projected_date = None
        
        return {
            "status": "active",
            "current_amount": goal.current_amount,
            "remaining_amount": goal.remaining_amount,
            "progress_percentage": goal.progress_percentage,
            "monthly_savings_rate": monthly_rate,
            "projected_completion": str(projected_date) if projected_date else "Unable to project",
            "on_track": goal.target_date and projected_date and projected_date <= goal.target_date if goal.target_date else True
        }

    @staticmethod
    async def get_goals_summary(db: AsyncSession, user_id: int) -> Dict:
        """Get summary of all goals"""
        goals = await SavingsGoalService.get_goals(db, user_id)
        
        active = [g for g in goals if g.status == GoalStatus.ACTIVE]
        completed = [g for g in goals if g.status == GoalStatus.COMPLETED]
        
        return {
            "total_goals": len(goals),
            "active_goals": len(active),
            "completed_goals": len(completed),
            "total_saved": sum(g.current_amount for g in goals),
            "total_target": sum(g.target_amount for g in goals),
            "overall_progress": (sum(g.current_amount for g in goals) / sum(g.target_amount for g in goals) * 100) if goals else 0
        }

    @staticmethod
    async def get_upcoming_goals(db: AsyncSession, user_id: int, days: int) -> List[Dict]:
        """Get goals with upcoming deadlines"""
        cutoff = date.today() + timedelta(days=days)
        query = select(SavingsGoal).where(
            and_(
                SavingsGoal.user_id == user_id,
                SavingsGoal.status == GoalStatus.ACTIVE,
                SavingsGoal.target_date <= cutoff,
                SavingsGoal.target_date >= date.today()
            )
        ).order_by(SavingsGoal.target_date)
        
        result = await db.execute(query)
        goals = result.scalars().all()
        
        return [{
            "id": g.id,
            "name": g.name,
            "target_date": str(g.target_date),
            "days_remaining": (g.target_date - date.today()).days,
            "progress": g.progress_percentage,
            "amount_remaining": g.remaining_amount
        } for g in goals]

    @staticmethod
    async def delete_goal(db: AsyncSession, goal_id: int, user_id: int) -> bool:
        """Delete goal"""
        goal = await SavingsGoalService.get_goal(db, goal_id, user_id)
        if not goal:
            return False
        await db.delete(goal)
        await db.commit()
        return True


class SpendingAnalyticsService:
    """Service for spending analytics and insights"""

    @staticmethod
    async def _get_user_account_ids(db: AsyncSession, user_id: int) -> List[int]:
        """Helper to get user account IDs"""
        query = select(Account.id).where(Account.user_id == user_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_spending_summary(
        db: AsyncSession,
        user_id: int,
        start_date: date,
        end_date: date
    ) -> SpendingSummary:
        """Get spending summary by category for a period"""
        account_ids = await SpendingAnalyticsService._get_user_account_ids(db, user_id)

        if not account_ids:
            return SpendingSummary(
                period_start=start_date,
                period_end=end_date,
                total_income=0,
                total_expenses=0,
                net_savings=0,
                spending_by_category=[]
            )

        txn_query = select(Transaction).where(
            and_(
                Transaction.account_id.in_(account_ids),
                func.date(Transaction.created_at) >= start_date,
                func.date(Transaction.created_at) <= end_date
            )
        )
        txn_result = await db.execute(txn_query)
        transactions = txn_result.scalars().all()

        total_income = sum(t.amount for t in transactions if t.transaction_type == "credit")
        total_expenses = sum(t.amount for t in transactions if t.transaction_type == "debit")

        spending_by_category = []
        if total_expenses > 0:
            spending_by_category.append(CategorySpending(
                category_id=0,
                category_name="All Expenses",
                category_type="other",
                total_spent=total_expenses,
                transaction_count=len([t for t in transactions if t.transaction_type == "debit"]),
                percentage_of_total=100,
                color="#FF6B6B"
            ))

        return SpendingSummary(
            period_start=start_date,
            period_end=end_date,
            total_income=total_income,
            total_expenses=total_expenses,
            net_savings=total_income - total_expenses,
            spending_by_category=spending_by_category
        )

    @staticmethod
    async def get_category_spending(
        db: AsyncSession,
        user_id: int,
        category_id: int,
        start_date: date,
        end_date: date
    ) -> Optional[CategorySpending]:
        """Get spending for specific category"""
        account_ids = await SpendingAnalyticsService._get_user_account_ids(db, user_id)
        if not account_ids:
            return None
        
        txn_query = select(Transaction).where(
            and_(
                Transaction.account_id.in_(account_ids),
                func.date(Transaction.created_at) >= start_date,
                func.date(Transaction.created_at) <= end_date,
                Transaction.transaction_type == "debit"
            )
        )
        result = await db.execute(txn_query)
        transactions = result.scalars().all()
        
        total = sum(t.amount for t in transactions)
        
        return CategorySpending(
            category_id=category_id,
            category_name="Category",
            category_type="other",
            total_spent=total,
            transaction_count=len(transactions),
            percentage_of_total=100,
            color="#FF6B6B"
        )

    @staticmethod
    async def get_spending_trends(
        db: AsyncSession,
        user_id: int,
        months: int = 6
    ) -> Dict:
        """Get monthly spending trends"""
        account_ids = await SpendingAnalyticsService._get_user_account_ids(db, user_id)

        trends = []
        end_date = date.today()
        total_spending = 0
        total_income = 0
        highest_spending = None
        lowest_spending = None
        highest_amount = 0
        lowest_amount = float('inf')

        for i in range(months):
            period_end = (end_date.replace(day=1) - timedelta(days=1) if i == 0 else
                         (end_date - relativedelta(months=i)).replace(day=1) - timedelta(days=1))
            period_start = period_end.replace(day=1)

            if account_ids:
                txn_query = select(Transaction).where(
                    and_(
                        Transaction.account_id.in_(account_ids),
                        func.date(Transaction.created_at) >= period_start,
                        func.date(Transaction.created_at) <= period_end
                    )
                )
                txn_result = await db.execute(txn_query)
                transactions = txn_result.scalars().all()

                month_income = sum(t.amount for t in transactions if t.transaction_type == "credit")
                month_expenses = sum(t.amount for t in transactions if t.transaction_type == "debit")
            else:
                month_income = 0
                month_expenses = 0

            period_str = period_start.strftime("%Y-%m")
            trends.append(SpendingTrend(
                period=period_str,
                total_spent=month_expenses,
                total_income=month_income,
                net=month_income - month_expenses
            ))

            total_spending += month_expenses
            total_income += month_income

            if month_expenses > highest_amount:
                highest_amount = month_expenses
                highest_spending = period_str
            if month_expenses < lowest_amount and month_expenses > 0:
                lowest_amount = month_expenses
                lowest_spending = period_str

        return {
            "trends": list(reversed(trends)),
            "average_monthly_spending": total_spending / months if months > 0 else 0,
            "average_monthly_income": total_income / months if months > 0 else 0,
            "highest_spending_month": highest_spending,
            "lowest_spending_month": lowest_spending
        }

    @staticmethod
    async def get_daily_spending(db: AsyncSession, user_id: int, start_date: date, end_date: date) -> List[Dict]:
        """Get daily spending breakdown"""
        account_ids = await SpendingAnalyticsService._get_user_account_ids(db, user_id)
        daily = []
        
        current = start_date
        while current <= end_date:
            if account_ids:
                txn_query = select(func.sum(Transaction.amount)).where(
                    and_(
                        Transaction.account_id.in_(account_ids),
                        func.date(Transaction.created_at) == current,
                        Transaction.transaction_type == "debit"
                    )
                )
                result = await db.execute(txn_query)
                amount = result.scalar() or 0
            else:
                amount = 0
            
            daily.append({"date": str(current), "amount": float(amount)})
            current += timedelta(days=1)
        
        return daily

    @staticmethod
    async def compare_periods(
        db: AsyncSession,
        user_id: int,
        p1_start: date,
        p1_end: date,
        p2_start: date,
        p2_end: date
    ) -> Dict:
        """Compare spending between two periods"""
        summary1 = await SpendingAnalyticsService.get_spending_summary(db, user_id, p1_start, p1_end)
        summary2 = await SpendingAnalyticsService.get_spending_summary(db, user_id, p2_start, p2_end)
        
        return {
            "period1": {"start": str(p1_start), "end": str(p1_end), "expenses": summary1.total_expenses, "income": summary1.total_income},
            "period2": {"start": str(p2_start), "end": str(p2_end), "expenses": summary2.total_expenses, "income": summary2.total_income},
            "expense_change": summary2.total_expenses - summary1.total_expenses,
            "expense_change_percent": ((summary2.total_expenses - summary1.total_expenses) / summary1.total_expenses * 100) if summary1.total_expenses else 0,
            "income_change": summary2.total_income - summary1.total_income
        }

    @staticmethod
    async def get_top_merchants(db: AsyncSession, user_id: int, start_date: date, end_date: date, limit: int) -> List[Dict]:
        """Get top merchants by spending"""
        return [{"merchant": "Various", "amount": 0, "count": 0}]

    @staticmethod
    async def get_recurring_expenses(db: AsyncSession, user_id: int) -> List[Dict]:
        """Identify recurring expenses"""
        return []

    @staticmethod
    async def get_insights(db: AsyncSession, user_id: int, limit: int) -> List[Dict]:
        """Get AI-generated insights"""
        budgets = await BudgetService.get_budgets(db, user_id)
        insights = []
        
        for budget in budgets:
            if budget.is_over_budget:
                insights.append({
                    "type": "budget_alert",
                    "title": f"Over Budget: {budget.name}",
                    "message": f"You've exceeded your {budget.name} budget by {budget.spent_amount - budget.amount:.2f}",
                    "severity": "high"
                })
        
        return insights[:limit]

    @staticmethod
    async def get_insight(db: AsyncSession, insight_id: int, user_id: int) -> Optional[Dict]:
        """Get specific insight"""
        query = select(SpendingInsight).where(
            and_(SpendingInsight.id == insight_id, SpendingInsight.user_id == user_id)
        )
        result = await db.execute(query)
        insight = result.scalar_one_or_none()
        return insight

    @staticmethod
    async def dismiss_insight(db: AsyncSession, insight_id: int, user_id: int) -> bool:
        """Dismiss insight"""
        query = select(SpendingInsight).where(
            and_(SpendingInsight.id == insight_id, SpendingInsight.user_id == user_id)
        )
        result = await db.execute(query)
        insight = result.scalar_one_or_none()
        
        if insight:
            insight.is_dismissed = True
            await db.commit()
            return True
        return False

    @staticmethod
    async def generate_monthly_report(db: AsyncSession, user_id: int, month: int, year: int) -> Dict:
        """Generate monthly report"""
        start = date(year, month, 1)
        end = (start + relativedelta(months=1)) - timedelta(days=1)
        summary = await SpendingAnalyticsService.get_spending_summary(db, user_id, start, end)
        budgets = await BudgetService.get_budget_summary(db, user_id)
        
        return {
            "period": f"{year}-{month:02d}",
            "income": summary.total_income,
            "expenses": summary.total_expenses,
            "savings": summary.net_savings,
            "savings_rate": (summary.net_savings / summary.total_income * 100) if summary.total_income else 0,
            "budgets": budgets
        }

    @staticmethod
    async def generate_annual_report(db: AsyncSession, user_id: int, year: int) -> Dict:
        """Generate annual report"""
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        summary = await SpendingAnalyticsService.get_spending_summary(db, user_id, start, end)
        
        return {
            "year": year,
            "total_income": summary.total_income,
            "total_expenses": summary.total_expenses,
            "total_savings": summary.net_savings,
            "average_monthly_expenses": summary.total_expenses / 12
        }

    @staticmethod
    async def export_data(db: AsyncSession, user_id: int, start_date: date, end_date: date, format: str) -> Dict:
        """Export financial data"""
        summary = await SpendingAnalyticsService.get_spending_summary(db, user_id, start_date, end_date)
        return {
            "format": format,
            "period": {"start": str(start_date), "end": str(end_date)},
            "data": {
                "income": summary.total_income,
                "expenses": summary.total_expenses,
                "savings": summary.net_savings
            }
        }

    @staticmethod
    async def calculate_health_score(db: AsyncSession, user_id: int) -> Dict:
        """Calculate financial health score (0-100)"""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        summary = await SpendingAnalyticsService.get_spending_summary(db, user_id, start_date, end_date)
        budget_summary = await BudgetService.get_budget_summary(db, user_id)
        goals = await SavingsGoalService.get_goals_summary(db, user_id)
        
        score = 50  # Base score
        
        # Savings rate contributes up to 20 points
        if summary.total_income > 0:
            savings_rate = summary.net_savings / summary.total_income
            score += min(20, savings_rate * 100)
        
        # Budget adherence contributes up to 20 points
        total_budgets = budget_summary.get("budgets_on_track", 0) + budget_summary.get("budgets_warning", 0) + budget_summary.get("budgets_over", 0)
        if total_budgets > 0:
            adherence = budget_summary.get("budgets_on_track", 0) / total_budgets
            score += adherence * 20
        
        # Goal progress contributes up to 10 points
        score += goals.get("overall_progress", 0) / 10
        
        score = min(100, max(0, score))
        
        return {
            "score": round(score),
            "grade": "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D",
            "breakdown": {
                "savings_rate": summary.net_savings / summary.total_income * 100 if summary.total_income else 0,
                "budget_adherence": budget_summary,
                "goal_progress": goals.get("overall_progress", 0)
            }
        }

    @staticmethod
    async def get_health_tips(db: AsyncSession, user_id: int) -> List[str]:
        """Get personalized financial tips"""
        health = await SpendingAnalyticsService.calculate_health_score(db, user_id)
        tips = []
        
        if health["breakdown"]["savings_rate"] < 20:
            tips.append("Try to save at least 20% of your income")
        
        tips.append("Review your subscriptions regularly")
        tips.append("Set up automatic transfers to savings")
        tips.append("Track your daily expenses")
        
        return tips
