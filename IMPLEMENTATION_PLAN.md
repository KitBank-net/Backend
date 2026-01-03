# KitBank.net - Implementation Plan

> **Document Version:** 1.0  
> **Created:** January 3, 2026  
> **Priority:** High-priority modules for KitBank completion

---

## 📋 Table of Contents

1. [Implementation Phases Overview](#implementation-phases-overview)
2. [Phase 1: Complete Core Banking](#phase-1-complete-core-banking)
3. [Phase 2: Open Banking Gateway](#phase-2-open-banking-gateway)
4. [Phase 3: Crypto Wallet Management](#phase-3-crypto-wallet-management)
5. [Phase 4: AI & Machine Learning Engine](#phase-4-ai--machine-learning-engine)
6. [Phase 5: Messaging Banking](#phase-5-messaging-banking)
7. [Phase 6: Admin & Compliance Console](#phase-6-admin--compliance-console)
8. [Phase 7: Analytics & Reporting](#phase-7-analytics--reporting)
9. [Timeline Estimate](#timeline-estimate)
10. [Technical Dependencies](#technical-dependencies)

---

## Implementation Phases Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    KITBANK IMPLEMENTATION ROADMAP                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PHASE 1          PHASE 2           PHASE 3          PHASE 4           │
│  ┌─────────┐     ┌─────────┐       ┌─────────┐      ┌─────────┐        │
│  │ CORE    │────▶│  OPEN   │──────▶│ CRYPTO  │─────▶│   AI    │        │
│  │ BANKING │     │ BANKING │       │ WALLET  │      │ ENGINE  │        │
│  │ 2 weeks │     │ 3 weeks │       │ 3 weeks │      │ 4 weeks │        │
│  └─────────┘     └─────────┘       └─────────┘      └─────────┘        │
│                                                                         │
│  PHASE 5          PHASE 6           PHASE 7                             │
│  ┌─────────┐     ┌─────────┐       ┌─────────┐                         │
│  │MESSAGING│────▶│ ADMIN   │──────▶│ANALYTICS│                         │
│  │ BANKING │     │ CONSOLE │       │DASHBOARD│                         │
│  │ 2 weeks │     │ 3 weeks │       │ 2 weeks │                         │
│  └─────────┘     └─────────┘       └─────────┘                         │
│                                                                         │
│  TOTAL ESTIMATED TIME: 19 weeks (4.75 months)                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Complete Core Banking

**Duration:** 2 weeks  
**Priority:** 🔴 Critical  
**Status:** 60% Complete

### Objective
Complete the existing core banking modules with missing features.

### Tasks

#### 1.1 Transactions Module Enhancement
**Files to modify:** `app/modules/transactions/`

```python
# New transaction types to add
class TransactionType(str, enum.Enum):
    INTERNAL_TRANSFER = "internal_transfer"
    EXTERNAL_TRANSFER = "external_transfer"
    P2P_TRANSFER = "p2p_transfer"
    QR_PAYMENT = "qr_payment"
    BILL_PAYMENT = "bill_payment"
    MOBILE_MONEY = "mobile_money"
    INTERNATIONAL_REMITTANCE = "international_remittance"
    CARD_PAYMENT = "card_payment"
    MERCHANT_PAYMENT = "merchant_payment"
```

**New Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/transactions/p2p` | Peer-to-peer transfer |
| POST | `/api/v1/transactions/qr-payment` | QR code payment |
| POST | `/api/v1/transactions/bill-pay` | Bill payment |
| POST | `/api/v1/transactions/mobile-money` | Mobile money transfer |
| POST | `/api/v1/transactions/international` | International remittance |
| GET | `/api/v1/transactions/fx-rates` | Get exchange rates |

#### 1.2 Loans Module Enhancement
**Files to modify:** `app/modules/loans/`

**New Features:**
- Loan application workflow (apply → review → approve/reject → disburse)
- Repayment schedule generation
- Interest calculation engine
- Late payment handling
- Credit limit management

**New Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/loans/apply` | Submit loan application |
| GET | `/api/v1/loans/{id}/schedule` | Get repayment schedule |
| POST | `/api/v1/loans/{id}/repay` | Make repayment |
| GET | `/api/v1/loans/{id}/status` | Check loan status |
| PUT | `/api/v1/loans/{id}/approve` | Approve loan (admin) |
| PUT | `/api/v1/loans/{id}/disburse` | Disburse loan funds |

#### 1.3 Cards Module - Visa/Mastercard Integration
**Files to modify:** `app/modules/cards/`

**New Features:**
- Card activation flow
- PIN management
- Transaction history per card
- Spending analytics
- Temporary block/unblock

---

## Phase 2: Open Banking Gateway

**Duration:** 3 weeks  
**Priority:** 🔴 Critical  
**Status:** Not Started

### Objective
Implement Open Banking compliant APIs following OBP and PSD2 standards.

### New Module Structure

```
app/modules/openbanking/
├── __init__.py
├── router.py                 # OBP-style API endpoints
├── schemas.py                # Standardized response formats
├── services.py               # Open Banking business logic
├── models.py                 # Database models
├── consent/
│   ├── __init__.py
│   ├── models.py             # Consent records
│   ├── schemas.py            # Consent request/response
│   └── services.py           # Consent management logic
├── oauth/
│   ├── __init__.py
│   ├── models.py             # Third-party app registration
│   ├── schemas.py            # OAuth schemas
│   └── services.py           # OAuth2 provider logic
└── sandbox/
    ├── __init__.py
    └── services.py           # Sandbox data generation
```

### 2.1 Consent Management

**Database Model:**
```python
class Consent(Base):
    __tablename__ = "consents"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    third_party_id = Column(Integer, ForeignKey("third_party_apps.id"), nullable=False)
    
    # Consent details
    consent_type = Column(SQLEnum(ConsentType), nullable=False)  # AIS, PIS, CBPII
    status = Column(SQLEnum(ConsentStatus), default=ConsentStatus.PENDING)
    
    # Permissions
    accounts_access = Column(Boolean, default=False)
    balances_access = Column(Boolean, default=False)
    transactions_access = Column(Boolean, default=False)
    payment_initiation = Column(Boolean, default=False)
    
    # Validity
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    
    # Audit
    created_at = Column(DateTime, server_default=func.now())
    revoked_at = Column(DateTime, nullable=True)
```

**Consent Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/consents` | Create consent request |
| GET | `/api/v1/consents` | List user's consents |
| GET | `/api/v1/consents/{id}` | Get consent details |
| DELETE | `/api/v1/consents/{id}` | Revoke consent |
| PUT | `/api/v1/consents/{id}/authorize` | Authorize consent |

### 2.2 Third-Party App Registration

**Database Model:**
```python
class ThirdPartyApp(Base):
    __tablename__ = "third_party_apps"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # OAuth credentials
    client_id = Column(String(100), unique=True, nullable=False)
    client_secret_hash = Column(String(255), nullable=False)
    
    # App details
    redirect_uris = Column(ARRAY(String))
    logo_url = Column(String(500))
    website_url = Column(String(500))
    
    # Permissions
    allowed_scopes = Column(ARRAY(String))  # accounts, transactions, payments
    
    # Status
    status = Column(SQLEnum(AppStatus), default=AppStatus.PENDING)
    approved_at = Column(DateTime)
    approved_by = Column(Integer, ForeignKey("users.id"))
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_day = Column(Integer, default=10000)
```

### 2.3 OBP-Compatible API Endpoints

**Account Information Service (AIS):**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/obp/v5.1.0/my/accounts` | Get user's accounts |
| GET | `/obp/v5.1.0/banks/{bank_id}/accounts/{account_id}` | Get account details |
| GET | `/obp/v5.1.0/banks/{bank_id}/accounts/{account_id}/balances` | Get account balance |
| GET | `/obp/v5.1.0/banks/{bank_id}/accounts/{account_id}/transactions` | Get transactions |

**Payment Initiation Service (PIS):**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/obp/v5.1.0/banks/{bank_id}/accounts/{account_id}/transactions` | Create transaction |
| GET | `/obp/v5.1.0/banks/{bank_id}/payments/{payment_id}` | Get payment status |

**Developer Portal:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/developers/register` | Register as developer |
| POST | `/api/v1/developers/apps` | Register new app |
| GET | `/api/v1/developers/apps` | List developer's apps |
| POST | `/api/v1/developers/apps/{id}/credentials` | Generate credentials |

### 2.4 OAuth2 Provider

```python
# OAuth2 flows to implement
class OAuth2Flow(str, enum.Enum):
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"
```

**OAuth Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/oauth/authorize` | Authorization page |
| POST | `/oauth/token` | Token exchange |
| POST | `/oauth/revoke` | Revoke token |
| GET | `/oauth/userinfo` | Get user info |
| GET | `/.well-known/openid-configuration` | OpenID discovery |

---

## Phase 3: Crypto Wallet Management

**Duration:** 3 weeks  
**Priority:** 🔴 Critical  
**Status:** Not Started

### Objective
Enable cryptocurrency functionality with Bitcoin, Ethereum, and stablecoin support.

### New Module Structure

```
app/modules/crypto/
├── __init__.py
├── router.py                 # Crypto endpoints
├── schemas.py                # Request/Response schemas
├── services.py               # Crypto business logic
├── models.py                 # Wallet models
├── wallets/
│   ├── __init__.py
│   ├── bitcoin.py            # BTC wallet service
│   ├── ethereum.py           # ETH wallet service
│   └── stablecoin.py         # USDT/USDC service
├── blockchain/
│   ├── __init__.py
│   ├── web3_provider.py      # Web3 connection
│   └── transaction_monitor.py # Transaction monitoring
└── exchange/
    ├── __init__.py
    └── services.py           # Crypto exchange/swap logic
```

### 3.1 Crypto Wallet Model

```python
class CryptoWallet(Base):
    __tablename__ = "crypto_wallets"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Wallet details
    wallet_type = Column(SQLEnum(CryptoType), nullable=False)  # BTC, ETH, USDT, USDC
    address = Column(String(100), unique=True, nullable=False)
    address_encrypted = Column(Text, nullable=False)  # Encrypted private key
    
    # Balance (updated via blockchain sync)
    balance = Column(Numeric(28, 18), default=0)
    pending_balance = Column(Numeric(28, 18), default=0)
    
    # Status
    status = Column(SQLEnum(WalletStatus), default=WalletStatus.ACTIVE)
    
    # Compliance
    kyc_verified = Column(Boolean, default=False)
    aml_risk_score = Column(Integer, default=0)  # 0-100
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class CryptoType(str, enum.Enum):
    BTC = "bitcoin"
    ETH = "ethereum"
    USDT = "tether"
    USDC = "usdc"
```

### 3.2 Crypto Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/crypto/wallets` | Create crypto wallet |
| GET | `/api/v1/crypto/wallets` | List user's crypto wallets |
| GET | `/api/v1/crypto/wallets/{id}` | Get wallet details |
| GET | `/api/v1/crypto/wallets/{id}/balance` | Get wallet balance |
| GET | `/api/v1/crypto/wallets/{id}/transactions` | Get crypto transactions |
| POST | `/api/v1/crypto/send` | Send cryptocurrency |
| GET | `/api/v1/crypto/receive/{wallet_id}` | Get receive address/QR |
| POST | `/api/v1/crypto/swap` | Swap between cryptocurrencies |
| GET | `/api/v1/crypto/prices` | Get current prices |
| GET | `/api/v1/crypto/prices/history` | Get price history |

### 3.3 Blockchain Integration

**Bitcoin (using python-bitcoinlib or blockcypher):**
```python
# services/bitcoin.py
class BitcoinWalletService:
    async def create_wallet(self, user_id: int) -> CryptoWallet:
        # Generate new Bitcoin address
        pass
    
    async def get_balance(self, address: str) -> Decimal:
        # Query blockchain for balance
        pass
    
    async def send_transaction(self, from_wallet: CryptoWallet, to_address: str, amount: Decimal) -> str:
        # Create and broadcast transaction
        pass
```

**Ethereum (using Web3.py):**
```python
# services/ethereum.py
from web3 import Web3

class EthereumWalletService:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_RPC_URL))
    
    async def create_wallet(self, user_id: int) -> CryptoWallet:
        account = self.w3.eth.account.create()
        # Store encrypted private key
        pass
    
    async def get_balance(self, address: str) -> Decimal:
        balance_wei = self.w3.eth.get_balance(address)
        return self.w3.from_wei(balance_wei, 'ether')
    
    async def send_transaction(self, from_wallet: CryptoWallet, to_address: str, amount: Decimal) -> str:
        # Build, sign, and send transaction
        pass
```

### 3.4 Required Dependencies

```txt
# requirements.txt additions
web3>=6.0.0
python-bitcoinlib>=0.12.0
eth-account>=0.8.0
cryptocompare>=0.7.6
```

---

## Phase 4: AI & Machine Learning Engine

**Duration:** 4 weeks  
**Priority:** 🟡 Medium  
**Status:** Not Started

### Objective
Implement AI-powered features for risk scoring, fraud detection, and personalization.

### New Module Structure

```
app/modules/ai/
├── __init__.py
├── router.py                 # AI API endpoints
├── schemas.py                # Request/Response schemas
├── models/
│   ├── __init__.py
│   ├── credit_score.py       # Credit scoring model
│   ├── fraud_detection.py    # Fraud detection model
│   └── recommendation.py     # Recommendation engine
├── services/
│   ├── __init__.py
│   ├── scoring_service.py    # Credit scoring logic
│   ├── fraud_service.py      # Fraud detection logic
│   └── chatbot_service.py    # AI chatbot
└── training/
    ├── __init__.py
    └── pipeline.py           # ML training pipelines
```

### 4.1 Credit Scoring Model

**Features for scoring:**
```python
class CreditScoreInput(BaseModel):
    # User demographics
    age: int
    employment_status: str
    monthly_income: Decimal
    
    # Account history
    account_age_months: int
    average_balance: Decimal
    minimum_balance_last_6m: Decimal
    
    # Transaction patterns
    transaction_count_30d: int
    income_transactions_30d: Decimal
    expense_transactions_30d: Decimal
    
    # Loan history
    existing_loans: int
    loan_repayment_rate: float  # 0.0 - 1.0
    missed_payments: int
    
    # External data (optional)
    credit_bureau_score: Optional[int]

class CreditScoreOutput(BaseModel):
    score: int  # 300-850
    risk_level: str  # low, medium, high
    max_loan_amount: Decimal
    recommended_interest_rate: Decimal
    factors: List[str]  # Key factors affecting score
```

### 4.2 Fraud Detection

**Real-time transaction screening:**
```python
class FraudCheckInput(BaseModel):
    transaction_id: int
    user_id: int
    amount: Decimal
    currency: str
    transaction_type: str
    
    # Context
    device_fingerprint: str
    ip_address: str
    location: Optional[dict]  # lat, lng
    
    # Behavioral
    time_since_last_transaction: int
    unusual_amount: bool
    new_recipient: bool

class FraudCheckOutput(BaseModel):
    risk_score: float  # 0.0 - 1.0
    is_suspicious: bool
    action: str  # allow, review, block
    reasons: List[str]
```

### 4.3 AI Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ai/credit-score` | Calculate credit score |
| POST | `/api/v1/ai/fraud-check` | Check transaction for fraud |
| POST | `/api/v1/ai/budget-prediction` | Predict monthly spending |
| GET | `/api/v1/ai/recommendations` | Get personalized recommendations |
| POST | `/api/v1/ai/chatbot` | AI chatbot interaction |

### 4.4 Required Dependencies

```txt
# requirements.txt additions
scikit-learn>=1.3.0
tensorflow>=2.13.0
pandas>=2.0.0
numpy>=1.24.0
joblib>=1.3.0
```

---

## Phase 5: Messaging Banking

**Duration:** 2 weeks  
**Priority:** 🟡 Medium  
**Status:** Not Started

### Objective
Enable banking via WhatsApp and Telegram.

### New Module Structure

```
app/modules/messaging/
├── __init__.py
├── router.py                 # Webhook endpoints
├── schemas.py                # Message schemas
├── services/
│   ├── __init__.py
│   ├── whatsapp.py           # WhatsApp Business API
│   ├── telegram.py           # Telegram Bot API
│   └── message_handler.py    # Common message logic
├── intents/
│   ├── __init__.py
│   ├── balance.py            # Balance inquiry
│   ├── transfer.py           # Money transfer
│   ├── history.py            # Transaction history
│   └── support.py            # Customer support
└── templates/
    ├── __init__.py
    └── messages.py           # Message templates
```

### 5.1 WhatsApp Integration

**Webhook Endpoint:**
```python
@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    # Verify webhook signature
    # Parse incoming message
    # Route to appropriate intent handler
    # Send response
    pass
```

**Supported Commands:**
| Command | Action |
|---------|--------|
| `balance` | Check account balance |
| `send [amount] to [phone]` | Transfer money |
| `history` | Last 5 transactions |
| `help` | Show available commands |
| `support` | Connect to human agent |

### 5.2 Telegram Bot

**Bot Commands:**
```python
# Telegram bot commands
/start - Register/link account
/balance - Check balance
/send - Transfer money
/history - Transaction history
/settings - Account settings
/help - Get help
```

### 5.3 Required Dependencies

```txt
# requirements.txt additions
python-telegram-bot>=20.0
httpx>=0.24.0  # For WhatsApp API calls
```

---

## Phase 6: Admin & Compliance Console

**Duration:** 3 weeks  
**Priority:** 🔴 Critical  
**Status:** Not Started

### Objective
Build back-office management tools for administrators.

### New Module Structure

```
app/modules/admin/
├── __init__.py
├── router.py                 # Admin API endpoints
├── schemas.py                # Admin schemas
├── services/
│   ├── __init__.py
│   ├── user_management.py    # User admin functions
│   ├── kyc_review.py         # KYC review workflow
│   ├── fraud_management.py   # Fraud case management
│   ├── compliance.py         # Compliance reporting
│   └── audit.py              # Audit logging
└── models.py                 # Admin-specific models
```

### 6.1 Admin Endpoints

**User Management:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/users` | List all users (paginated) |
| GET | `/api/v1/admin/users/{id}` | Get user details |
| PUT | `/api/v1/admin/users/{id}/status` | Update user status |
| PUT | `/api/v1/admin/users/{id}/kyc` | Approve/reject KYC |
| POST | `/api/v1/admin/users/{id}/notes` | Add internal note |

**Transaction Management:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/transactions` | List all transactions |
| GET | `/api/v1/admin/transactions/flagged` | Flagged transactions |
| PUT | `/api/v1/admin/transactions/{id}/review` | Review transaction |
| POST | `/api/v1/admin/transactions/{id}/refund` | Issue refund |

**Compliance:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/compliance/reports` | Compliance reports |
| GET | `/api/v1/admin/compliance/aml-alerts` | AML alerts |
| POST | `/api/v1/admin/compliance/sar` | File SAR report |

### 6.2 Role-Based Access Control

```python
class AdminRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    KYC_OFFICER = "kyc_officer"
    COMPLIANCE_OFFICER = "compliance_officer"
    SUPPORT_AGENT = "support_agent"
    ANALYST = "analyst"


class Permission(str, enum.Enum):
    VIEW_USERS = "view_users"
    EDIT_USERS = "edit_users"
    APPROVE_KYC = "approve_kyc"
    VIEW_TRANSACTIONS = "view_transactions"
    REFUND_TRANSACTIONS = "refund_transactions"
    VIEW_REPORTS = "view_reports"
    MANAGE_ADMINS = "manage_admins"
```

---

## Phase 7: Analytics & Reporting

**Duration:** 2 weeks  
**Priority:** 🟡 Medium  
**Status:** Not Started

### Objective
Provide dashboards and reports for business intelligence.

### New Module Structure

```
app/modules/analytics/
├── __init__.py
├── router.py                 # Analytics endpoints
├── schemas.py                # Report schemas
├── services/
│   ├── __init__.py
│   ├── dashboard.py          # Dashboard data
│   ├── reports.py            # Report generation
│   └── exports.py            # CSV/PDF exports
└── queries/
    ├── __init__.py
    └── sql_queries.py        # Optimized SQL queries
```

### 7.1 Analytics Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/dashboard` | Dashboard KPIs |
| GET | `/api/v1/analytics/users/growth` | User growth metrics |
| GET | `/api/v1/analytics/transactions/volume` | Transaction volume |
| GET | `/api/v1/analytics/loans/performance` | Loan performance |
| GET | `/api/v1/analytics/revenue` | Revenue metrics |
| GET | `/api/v1/analytics/reports/{type}` | Generate report |
| GET | `/api/v1/analytics/export/{format}` | Export data |

### 7.2 Dashboard KPIs

```python
class DashboardKPIs(BaseModel):
    # Users
    total_users: int
    active_users_30d: int
    new_users_today: int
    kyc_pending: int
    
    # Transactions
    transactions_today: int
    transaction_volume_today: Decimal
    average_transaction_size: Decimal
    
    # Accounts
    total_accounts: int
    total_balance: Decimal
    
    # Loans
    active_loans: int
    loans_disbursed_mtd: Decimal
    loan_repayment_rate: float
    overdue_loans: int
    
    # Revenue
    revenue_mtd: Decimal
    fees_collected_today: Decimal
```

---

## Timeline Estimate

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: Core Banking | 2 weeks | Week 1 | Week 2 |
| Phase 2: Open Banking | 3 weeks | Week 3 | Week 5 |
| Phase 3: Crypto Wallet | 3 weeks | Week 6 | Week 8 |
| Phase 4: AI/ML Engine | 4 weeks | Week 9 | Week 12 |
| Phase 5: Messaging | 2 weeks | Week 13 | Week 14 |
| Phase 6: Admin Console | 3 weeks | Week 15 | Week 17 |
| Phase 7: Analytics | 2 weeks | Week 18 | Week 19 |

**Total: 19 weeks (~4.75 months)**

---

## Technical Dependencies

### New Python Packages Required

```txt
# requirements.txt additions for all phases

# Phase 2: Open Banking
python-jose[cryptography]>=3.3.0  # JWT handling
authlib>=1.2.0                     # OAuth2 provider

# Phase 3: Crypto
web3>=6.0.0                        # Ethereum
python-bitcoinlib>=0.12.0          # Bitcoin
eth-account>=0.8.0                 # Ethereum accounts
cryptocompare>=0.7.6               # Price feeds
pycryptodome>=3.18.0               # Encryption

# Phase 4: AI/ML
scikit-learn>=1.3.0
tensorflow>=2.13.0
pandas>=2.0.0
numpy>=1.24.0
joblib>=1.3.0

# Phase 5: Messaging
python-telegram-bot>=20.0
httpx>=0.24.0

# Phase 7: Analytics
openpyxl>=3.1.0                    # Excel exports
reportlab>=4.0.0                   # PDF generation
```

### Infrastructure Requirements

| Service | Purpose | Estimated Cost |
|---------|---------|----------------|
| **Ethereum Node** | Web3 connection | $50-200/month (Infura/Alchemy) |
| **Bitcoin Node** | BTC integration | $50-100/month (BlockCypher) |
| **WhatsApp Business API** | Messaging | $0.005-0.09/message |
| **Telegram Bot** | Messaging | Free |
| **ML Model Hosting** | AI inference | $100-500/month |
| **Redis Cluster** | Caching | $50-200/month |
| **PostgreSQL (Production)** | Database | $100-500/month |

---

## Quick Start Commands

### Create New Module Template
```bash
# Create a new module directory
mkdir -p app/modules/{module_name}
touch app/modules/{module_name}/__init__.py
touch app/modules/{module_name}/router.py
touch app/modules/{module_name}/schemas.py
touch app/modules/{module_name}/services.py
touch app/modules/{module_name}/models.py
```

### Generate Alembic Migration
```bash
docker exec -it kitbank_backend alembic revision --autogenerate -m "Add {feature_name}"
docker exec -it kitbank_backend alembic upgrade head
```

### Run Tests for New Module
```bash
docker exec -it kitbank_backend pytest tests/modules/{module_name}/ -v
```

---

## Success Criteria

| Phase | Success Criteria |
|-------|------------------|
| Phase 1 | All transaction types working, loan workflow complete |
| Phase 2 | OBP endpoints passing compliance tests, OAuth2 working |
| Phase 3 | BTC/ETH wallets created, transfers working |
| Phase 4 | Credit scores generated, fraud alerts firing |
| Phase 5 | WhatsApp/Telegram bots responding to commands |
| Phase 6 | Admin can manage users, review KYC, see reports |
| Phase 7 | Dashboard showing real-time KPIs, exports working |

---

*This implementation plan should be reviewed and updated as development progresses.*
