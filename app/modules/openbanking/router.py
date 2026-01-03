"""
Open Banking Gateway - Main Router

Aggregates all Open Banking sub-routers.
"""
from fastapi import APIRouter

from app.modules.openbanking.routers.consent import router as consent_router
from app.modules.openbanking.routers.oauth import router as oauth_router
from app.modules.openbanking.routers.accounts import router as accounts_router
from app.modules.openbanking.routers.payments import router as payments_router
from app.modules.openbanking.routers.developers import router as developers_router

# Main Open Banking router
router = APIRouter(prefix="/openbanking", tags=["open-banking"])

# Include all sub-routers
router.include_router(consent_router)
router.include_router(oauth_router)
router.include_router(accounts_router)
router.include_router(payments_router)
router.include_router(developers_router)
