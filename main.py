from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import Base, async_engine, close_redis
from app.core.config import settings
from app.modules.users.router import router as users_router
from app.modules.accounts.router import router as accounts_router
from app.modules.transactions.router import router as transactions_router
from app.modules.loans.router import router as loans_router
from app.modules.cards.router import router as cards_router
from app.modules.security.router import router as security_router
from app.modules.notifications.router import router as notifications_router
from app.modules.budgeting.router import router as budgeting_router
from app.modules.admin.router import router as admin_router
from app.modules.openbanking.router import router as openbanking_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    async with async_engine.begin() as conn:
        # Create all tables (for development - use Alembic in production)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Shutdown
    await close_redis()
    await async_engine.dispose()


app = FastAPI(
    title="KitBank.net API",
    description="Digital Banking Platform - Phase 1",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users_router)
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(loans_router)
app.include_router(cards_router)
app.include_router(security_router)
app.include_router(notifications_router)
app.include_router(budgeting_router)
app.include_router(admin_router)
app.include_router(openbanking_router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to KitBank.net API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

