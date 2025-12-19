# KitBank.net 🏦

A **digital banking platform** built with FastAPI, PostgreSQL, Redis, and Docker.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- Git

### Run with Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/kitbank.git
cd kitbank/backend

# 2. Start all services (PostgreSQL, Redis, Backend)
docker compose up --build

# 3. Wait for "Application startup complete" in logs

# 4. Access the API
open http://localhost:8000/docs
```

That's it! The API is now running with a PostgreSQL database and Redis cache.

---

## 📖 API Documentation

| Endpoint | Description |
|----------|-------------|
| [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI (Interactive) |
| [http://localhost:8000/redoc](http://localhost:8000/redoc) | ReDoc (Clean docs) |
| [http://localhost:8000/health](http://localhost:8000/health) | Health Check |

---

## 🐳 Docker Commands

```bash
# Start services in background
docker compose up -d --build

# View logs (follow mode)
docker compose logs -f backend

# Stop all services
docker compose down

# Stop and remove all data (fresh start)
docker compose down -v

# Restart backend only (after code changes)
docker compose restart backend

# Rebuild and restart (after requirements.txt changes)
docker compose up --build -d

# Shell into backend container
docker exec -it kitbank_backend bash

# Run database migrations manually
docker exec -it kitbank_backend alembic upgrade head
```

---

## 🏗️ Architecture

### Services

| Container | Port | Description |
|-----------|------|-------------|
| `kitbank_backend` | 8000 | FastAPI Application |
| `kitbank_postgres` | 5432 | PostgreSQL 15 Database |
| `kitbank_redis` | 6379 | Redis 7 Cache |

### API Modules

| Module | Endpoints | Description |
|--------|-----------|-------------|
| **Users** | `/api/v1/users` | Registration, profiles, KYC |
| **Accounts** | `/api/v1/accounts` | Bank accounts, balances |
| **Transactions** | `/api/v1/transactions` | Transfers, payments |
| **Loans** | `/api/v1/loans` | Applications, repayments |
| **Cards** | `/api/v1/cards` | Virtual/physical cards |
| **Security** | `/api/v1/security` | Auth, 2FA, audit logs |
| **Notifications** | `/api/v1/notifications` | SMS, Email, Push alerts |
| **Budgeting** | `/api/v1/budgeting` | Budgets, goals, analytics |

---

## 📁 Project Structure

```
kitbank/backend/
├── app/
│   ├── core/                 # Config, database, auth
│   │   ├── config.py         # Settings (env variables)
│   │   ├── database.py       # SQLAlchemy async setup
│   │   └── dependencies.py   # FastAPI dependencies
│   └── modules/              # Feature modules
│       ├── users/            # User management
│       ├── accounts/         # Account management
│       ├── transactions/     # Transaction processing
│       ├── loans/            # Loan services
│       ├── cards/            # Card management
│       ├── security/         # Security features
│       ├── notifications/    # Multi-channel alerts
│       └── budgeting/        # Personal finance
├── alembic/                  # Database migrations
│   └── versions/             # Migration files
├── main.py                   # FastAPI app entry point
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container definition
├── docker-compose.yml        # Multi-service orchestration
└── .env.example              # Environment template
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://kitbank:kitbank_password@postgres:5432/kitbank_db
DATABASE_SYNC_URL=postgresql://kitbank:kitbank_password@postgres:5432/kitbank_db

# Redis
REDIS_URL=redis://redis:6379/0

# JWT Authentication
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (SendGrid)
SENDGRID_API_KEY=your-sendgrid-key
SENDGRID_FROM_EMAIL=noreply@kitbank.net

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890

# Environment
DEBUG=true
ENVIRONMENT=development
```

---

## 🛠️ Development

### Local Development (Without Docker)

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start PostgreSQL and Redis (using Docker)
docker compose up postgres redis -d

# 4. Run migrations
alembic upgrade head

# 5. Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Run all tests
docker exec -it kitbank_backend pytest -v

# Run with coverage
docker exec -it kitbank_backend pytest --cov=app tests/
```

### Code Quality

```bash
# Linting
docker exec -it kitbank_backend flake8 app/

# Type checking
docker exec -it kitbank_backend mypy app/
```

---

## 🔐 Authentication

The API uses **JWT Bearer tokens** for authentication.

```bash
# 1. Register a new user
curl -X POST http://localhost:8000/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}'

# 2. Login to get token
curl -X POST http://localhost:8000/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}'

# Response: {"access_token": "eyJ...", "token_type": "bearer"}

# 3. Use token for authenticated requests
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer eyJ..."
```

---

## 📊 Database Migrations

```bash
# Create new migration
docker exec -it kitbank_backend alembic revision --autogenerate -m "description"

# Apply all migrations
docker exec -it kitbank_backend alembic upgrade head

# Rollback last migration
docker exec -it kitbank_backend alembic downgrade -1

# View migration history
docker exec -it kitbank_backend alembic history
```

---

## 🚢 Production Deployment

### Environment Setup

1. Set `DEBUG=false` and `ENVIRONMENT=production`
2. Use strong `SECRET_KEY`
3. Configure real database credentials
4. Set up SSL/TLS termination
5. Configure CORS origins

### Docker Production

```bash
# Build production image
docker build -t kitbank-backend:latest .

# Run with production settings
docker run -d \
  --name kitbank-backend \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/kitbank \
  -e DEBUG=false \
  kitbank-backend:latest
```

---

## 📈 Tech Stack

| Category | Technology |
|----------|------------|
| **Framework** | FastAPI (async) |
| **Database** | PostgreSQL 15 + SQLAlchemy 2.0 |
| **Cache** | Redis 7 |
| **ORM** | SQLAlchemy (async) |
| **Validation** | Pydantic v2 |
| **Auth** | JWT + Argon2 |
| **Email** | SendGrid |
| **SMS** | Twilio |
| **Container** | Docker & Docker Compose |
| **CI/CD** | GitHub Actions |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <b>KitBank.net</b> - Modern Digital Banking Platform
</p>
