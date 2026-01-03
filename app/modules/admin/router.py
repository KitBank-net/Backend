"""
Admin module sub-routers organized by domain.
"""
from fastapi import APIRouter

from app.modules.admin.routers.auth import router as auth_router
from app.modules.admin.routers.dashboard import router as dashboard_router
from app.modules.admin.routers.customers import router as customers_router
from app.modules.admin.routers.kyc import router as kyc_router
from app.modules.admin.routers.accounts import router as accounts_router
from app.modules.admin.routers.transactions import router as transactions_router
from app.modules.admin.routers.loans import router as loans_router
from app.modules.admin.routers.cards import router as cards_router
from app.modules.admin.routers.settings import router as settings_router
from app.modules.admin.routers.reports import router as reports_router

# Main admin router
router = APIRouter(prefix="/admin", tags=["admin"])

# Include all sub-routers
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(customers_router)
router.include_router(kyc_router)
router.include_router(accounts_router)
router.include_router(transactions_router)
router.include_router(loans_router)
router.include_router(cards_router)
router.include_router(settings_router)
router.include_router(reports_router)
