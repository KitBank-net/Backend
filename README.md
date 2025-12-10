# KitBank.net 🏦

A modular digital banking platform built with FastAPI, PostgreSQL, Redis, and Docker.

## Quick Start (Docker)

```bash
# Navigate to project root
cd /Users/Franko/Desktop/kitbank

# Build and start all services
docker-compose up --build

# API available at http://localhost:8000
```

## Access Points

| Service | URL |
|---------|-----|
| **Swagger UI** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |
| **Health Check** | http://localhost:8000/health |

## Docker Commands

```bash
# Start services
docker-compose up --build

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart backend only
docker-compose restart backend

# Rebuild after code changes
docker-compose up --build
```

## Services

| Container | Port | Purpose |
|-----------|------|---------|
| `kitbank_backend` | 8000 | FastAPI backend |
| `kitbank_postgres` | 5432 | PostgreSQL database |
| `kitbank_redis` | 6379 | Redis cache |

## Project Structure

```
kitbank/
├── backend/
│   ├── app/modules/     # Feature modules (users, accounts, etc.)
│   ├── main.py          # Application entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env             # Environment config
├── docker-compose.yml   # Multi-service orchestration
└── .github/workflows/   # CI/CD
```

## API Modules

- **Users** - User registration, profiles, KYC
- **Accounts** - Bank account management
- **Transactions** - Transfers and payments
- **Loans** - Loan applications and repayments
- **Security** - Authentication, 2FA, audit logs

## Tech Stack

- **Backend**: FastAPI (async)
- **Database**: PostgreSQL + SQLAlchemy (async)
- **Cache**: Redis
- **Auth**: JWT + Argon2
- **Container**: Docker & Docker Compose
# BACKEND
