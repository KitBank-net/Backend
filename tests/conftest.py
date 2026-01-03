"""
Test configuration and fixtures for KitBank backend tests.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from decimal import Decimal
from datetime import datetime, date

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from app.core.database import Base, get_db
from app.core.config import settings
from main import app


# ============================================================
# Database Fixtures
# ============================================================

# Use SQLite for testing (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for each test"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with database override (alias for client)"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# ============================================================
# User Fixtures
# ============================================================

@pytest.fixture
async def test_user(db_session):
    """Create a test user"""
    from app.modules.users.models import User, KYCStatus, AccountStatus, SourceOfFunds, MonthlyIncomeRange, TwoFactorMethod
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user = User(
        email="test@kitbank.net",
        phone_number="+1234567890",
        hashed_password=pwd_context.hash("TestPassword123!"),
        first_name="Test",
        last_name="User",
        date_of_birth=date(1990, 1, 1),
        nationality="US",
        country_of_residence="US",
        street_address="123 Test St",
        city="Test City",
        state="TS",
        postal_code="12345",
        country="US",
        occupation="Engineer",
        source_of_funds=SourceOfFunds.EMPLOYMENT,
        monthly_income_range=MonthlyIncomeRange.RANGE_5001_10000,
        kyc_status=KYCStatus.APPROVED,
        account_status=AccountStatus.ACTIVE,
        email_verified=True,
        phone_verified=True,
        two_factor_enabled=False,
        two_factor_method=TwoFactorMethod.NONE,
        login_attempts=0,
        accepted_terms=True,
        accepted_privacy_policy=True,
        marketing_consent=False
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture
async def test_account(db_session, test_user):
    """Create a test account"""
    from app.modules.accounts.models import Account, AccountType, Currency, AccountTier, AccountStatusEnum
    
    account = Account(
        user_id=test_user.id,
        account_number="100000000001",
        routing_number="123456789",
        account_type=AccountType.CHECKING,
        currency=Currency.USD,
        account_tier=AccountTier.BASIC,
        current_balance=Decimal("10000.00"),
        available_balance=Decimal("10000.00"),
        ledger_balance=Decimal("10000.00"),
        overdraft_limit=Decimal("0.00"),
        overdraft_enabled=False,
        interest_rate=Decimal("0.01"),
        minimum_balance=Decimal("0.00"),
        daily_transaction_limit=Decimal("10000.00"),
        daily_withdrawal_limit=Decimal("5000.00"),
        monthly_transaction_limit=Decimal("100000.00"),
        check_writing_enabled=True,
        wire_transfer_enabled=True,
        ach_transfer_enabled=True,
        international_transfer_enabled=True,
        direct_deposit_enabled=True,
        bill_pay_enabled=True,
        debit_card_enabled=True,
        account_status=AccountStatusEnum.ACTIVE,
        opened_date=date.today()
    )
    
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    
    return account


@pytest.fixture
async def auth_headers(test_user):
    """Generate auth headers for test user"""
    from app.core.security import create_access_token
    
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# Loan Fixtures
# ============================================================

@pytest.fixture
async def test_loan_product(db_session):
    """Create a test loan product"""
    from app.modules.loans.models import LoanProduct, LoanType, RepaymentFrequency
    
    product = LoanProduct(
        name="Personal Loan",
        loan_type=LoanType.PERSONAL,
        description="Standard personal loan",
        min_interest_rate=Decimal("10.00"),
        max_interest_rate=Decimal("20.00"),
        default_interest_rate=Decimal("15.00"),
        min_amount=Decimal("1000.00"),
        max_amount=Decimal("50000.00"),
        min_term_months=6,
        max_term_months=60,
        processing_fee_percentage=Decimal("0.02"),
        processing_fee_flat=Decimal("50.00"),
        late_payment_fee=Decimal("25.00"),
        requires_collateral=False,
        repayment_frequency=RepaymentFrequency.MONTHLY,
        grace_period_days=5,
        is_active=True
    )
    
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    
    return product
