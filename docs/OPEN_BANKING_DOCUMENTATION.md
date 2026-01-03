# KitBank Open Banking Gateway
## Technical Documentation & API Reference

---

# Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Developer Registration](#3-developer-registration)
4. [OAuth2 Authorization Flow](#4-oauth2-authorization-flow)
5. [Consent Management](#5-consent-management)
6. [Account Information Service (AIS)](#6-account-information-service-ais)
7. [Payment Initiation Service (PIS)](#7-payment-initiation-service-pis)
8. [Security Model](#8-security-model)
9. [API Reference](#9-api-reference)
10. [Error Handling](#10-error-handling)

---

# 1. Introduction

## What is Open Banking?

Open Banking is a regulatory framework that enables third-party applications to securely access bank account data and initiate payments with explicit user consent. KitBank implements the **PSD2** (Payment Services Directive 2) standards and is compatible with the **Open Bank Project (OBP)** API specification.

## Key Benefits

| Stakeholder | Benefit |
|-------------|---------|
| **Users** | Connect financial apps without sharing passwords |
| **Fintech Apps** | Access bank data via standardized APIs |
| **KitBank** | Expand ecosystem, attract partners |

## Terminology

| Term | Definition |
|------|------------|
| **TPP** | Third-Party Provider (the fintech app) |
| **ASPSP** | Account Servicing Payment Service Provider (KitBank) |
| **AIS** | Account Information Service - read account data |
| **PIS** | Payment Initiation Service - make payments |
| **SCA** | Strong Customer Authentication - 2FA for payments |
| **Consent** | User's explicit permission for data access |

---

# 2. Architecture Overview

## System Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              USER                                         │
│                           (Bank Customer)                                 │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                     ┌─────────▼─────────┐
                     │   3. User Login   │
                     │   & Consent       │
                     └─────────┬─────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────────┐
│                        KITBANK OPEN BANKING GATEWAY                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Developer  │  │   OAuth2    │  │   Consent   │  │   OBP APIs      │  │
│  │   Portal    │  │   Server    │  │  Management │  │ (AIS/PIS)       │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
         ▲                                                      │
         │ 1. Register                                         │ 5. Data
         │    App                                              ▼
┌────────┴─────────────────────────────────────────────────────────────────┐
│                         THIRD-PARTY APP                                   │
│                      (Budgeting App, Fintech)                            │
└──────────────────────────────────────────────────────────────────────────┘
```

## Database Models

### ThirdPartyApp
Stores registered third-party applications.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| client_id | String(64) | OAuth client identifier (public) |
| client_secret_hash | String(255) | Hashed client secret |
| organization_name | String(200) | Company name |
| name | String(200) | App name |
| redirect_uris | JSON | Allowed callback URLs |
| allowed_scopes | JSON | ["accounts", "balances", "transactions", "payments"] |
| status | Enum | pending, sandbox, approved, suspended, revoked |
| rate_limit_per_minute | Integer | Default: 60 |
| rate_limit_per_day | Integer | Default: 10,000 |

### Consent
Stores user consent records.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| consent_id | String(64) | Public consent identifier |
| user_id | FK → users | The bank customer |
| app_id | FK → third_party_apps | The requesting app |
| consent_type | Enum | ais, pis, cbpii, combined |
| status | Enum | pending, authorized, rejected, revoked, expired |
| accounts_access | Boolean | Can read accounts |
| balances_access | Boolean | Can read balances |
| transactions_access | Boolean | Can read transactions |
| payment_initiation | Boolean | Can make payments |
| valid_from | DateTime | Consent start date |
| valid_until | DateTime | Consent expiry (max 90 days) |
| authorization_code | String(64) | One-time OAuth code |

### OAuthToken
Stores access and refresh tokens.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| user_id | FK → users | Token owner |
| app_id | FK → third_party_apps | Token recipient app |
| consent_id | FK → consents | Associated consent |
| token_type | Enum | access, refresh, authorization_code |
| token_hash | String(255) | SHA-256 hash of token |
| scopes | JSON | Granted scopes |
| expires_at | DateTime | Token expiration |
| is_revoked | Boolean | Revocation flag |

---

# 3. Developer Registration

## Step 1: Register Your Application

**Endpoint:** `POST /openbanking/developers/apps`

**Request:**
```json
{
    "organization_name": "BudgetMaster Inc",
    "organization_email": "developers@budgetmaster.com",
    "organization_website": "https://budgetmaster.com",
    "name": "BudgetMaster Pro",
    "description": "A personal finance management app",
    "logo_url": "https://budgetmaster.com/logo.png",
    "privacy_policy_url": "https://budgetmaster.com/privacy",
    "terms_of_service_url": "https://budgetmaster.com/terms",
    "redirect_uris": [
        "https://budgetmaster.com/callback",
        "https://budgetmaster.com/oauth/callback"
    ],
    "requested_scopes": ["accounts", "balances", "transactions"],
    "app_type": "web"
}
```

**Response:**
```json
{
    "client_id": "xK8f2h9Jm3nP7qRtUvWxYz4bCdEfGhIjKlMnOpQrStUv",
    "client_secret": "mN3j7kL9pQ2rS5tU8vW1xY4zA7bC0dE3fG6hI9jK2lMnOpQrStUvWxYz",
    "message": "Store these credentials securely. The client_secret will not be shown again."
}
```

> ⚠️ **IMPORTANT:** The `client_secret` is shown only once. Store it securely!

## Step 2: App Status Lifecycle

```
SANDBOX → PENDING → APPROVED
    ↓         ↓         ↓
    └─────────┴─────────┴──→ SUSPENDED → REVOKED
```

| Status | Description |
|--------|-------------|
| **SANDBOX** | Initial state, can only access sandbox data |
| **PENDING** | Submitted for production review |
| **APPROVED** | Can access real production data |
| **SUSPENDED** | Temporarily blocked (policy violation) |
| **REVOKED** | Permanently blocked |

---

# 4. OAuth2 Authorization Flow

KitBank implements OAuth 2.0 Authorization Code flow with PKCE support.

## Complete Flow Diagram

```
┌─────────────┐                              ┌─────────────┐                              ┌─────────────┐
│   User's    │                              │  KitBank    │                              │ Third-Party │
│   Browser   │                              │   Server    │                              │     App     │
└──────┬──────┘                              └──────┬──────┘                              └──────┬──────┘
       │                                            │                                            │
       │  1. User clicks "Connect Bank Account"     │                                            │
       │ ◀──────────────────────────────────────────┼────────────────────────────────────────────│
       │                                            │                                            │
       │  2. Redirect to /oauth/authorize           │                                            │
       │ ──────────────────────────────────────────▶│                                            │
       │    ?client_id=...&scope=accounts           │                                            │
       │    &redirect_uri=...&state=...             │                                            │
       │                                            │                                            │
       │  3. Show login + consent page              │                                            │
       │ ◀──────────────────────────────────────────│                                            │
       │                                            │                                            │
       │  4. User approves consent                  │                                            │
       │ ──────────────────────────────────────────▶│                                            │
       │                                            │                                            │
       │  5. Redirect to callback with code         │                                            │
       │ ◀──────────────────────────────────────────│                                            │
       │    ?code=AUTH_CODE&state=...               │                                            │
       │                                            │                                            │
       │  6. Browser follows redirect               │                                            │
       │ ────────────────────────────────────────────────────────────────────────────────────────▶│
       │                                            │                                            │
       │                                            │  7. Exchange code for tokens               │
       │                                            │ ◀────────────────────────────────────────────│
       │                                            │    POST /oauth/token                       │
       │                                            │    code=...&client_secret=...              │
       │                                            │                                            │
       │                                            │  8. Return access_token                    │
       │                                            │ ────────────────────────────────────────────▶│
       │                                            │                                            │
       │                                            │  9. Call APIs with token                   │
       │                                            │ ◀────────────────────────────────────────────│
       │                                            │    Authorization: Bearer {token}           │
       │                                            │                                            │
```

## Step-by-Step Guide

### Step 1: Authorization Request

**Endpoint:** `GET /openbanking/oauth/authorize`

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| response_type | Yes | Must be "code" |
| client_id | Yes | Your app's client ID |
| redirect_uri | Yes | Must match registered URI |
| scope | Yes | Space-separated: "accounts balances transactions" |
| state | Yes | CSRF protection token (random string) |
| code_challenge | PKCE | Base64-URL-encoded SHA256 hash of verifier |
| code_challenge_method | PKCE | Must be "S256" |

**Example:**
```
https://kitbank.net/api/openbanking/oauth/authorize
  ?response_type=code
  &client_id=xK8f2h9Jm3nP7qRtUvWxYz4bCdEfGhIjKlMnOpQrStUv
  &redirect_uri=https://budgetmaster.com/callback
  &scope=accounts%20balances%20transactions
  &state=abc123xyz
```

### Step 2: User Authenticates & Consents

KitBank shows the user:
1. Login page (if not logged in)
2. Consent page showing:
   - App name and logo
   - Requested permissions
   - Data access duration (max 90 days)

### Step 3: Authorization Response

After user approves, redirect to:
```
https://budgetmaster.com/callback
  ?code=AUTH_CODE_xyz123abc456
  &state=abc123xyz
```

### Step 4: Token Exchange

**Endpoint:** `POST /openbanking/oauth/token`

**Request:**
```bash
curl -X POST https://kitbank.net/api/openbanking/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTH_CODE_xyz123abc456" \
  -d "redirect_uri=https://budgetmaster.com/callback" \
  -d "client_id=xK8f2h9Jm3nP7qRtUvWxYz4bCdEfGhIjKlMnOpQrStUv" \
  -d "client_secret=mN3j7kL9pQ2rS5tU8vW1xY4zA7bC0dE3fG6hI9jK2lMnOpQrStUvWxYz"
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
    "scope": "accounts balances transactions"
}
```

### Step 5: Token Refresh

**Endpoint:** `POST /openbanking/oauth/token`

```bash
curl -X POST https://kitbank.net/api/openbanking/oauth/token \
  -d "grant_type=refresh_token" \
  -d "refresh_token=dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..." \
  -d "client_id=xK8f2h9Jm3nP7qRtUvWxYz4bCdEfGhIjKlMnOpQrStUv" \
  -d "client_secret=mN3j7kL9pQ2rS5tU8vW1xY4zA7bC0dE3fG6hI9jK2lMnOpQrStUvWxYz"
```

---

# 5. Consent Management

## Consent Types

| Type | Code | Permissions |
|------|------|-------------|
| Account Information | AIS | Read accounts, balances, transactions |
| Payment Initiation | PIS | Initiate payments |
| Card-Based Payment | CBPII | Check funds availability |
| Combined | COMBINED | AIS + PIS |

## Consent Lifecycle

```
PENDING → AUTHORIZED → EXPIRED
    ↓         ↓
    └─────────┴──→ REJECTED
                   REVOKED
```

## User Consent Endpoints

### List User's Consents

**Endpoint:** `GET /openbanking/consents`

**Response:**
```json
{
    "consents": [
        {
            "consent_id": "abc123xyz",
            "consent_type": "ais",
            "status": "authorized",
            "accounts_access": true,
            "balances_access": true,
            "transactions_access": true,
            "payment_initiation": false,
            "valid_from": "2026-01-03T12:00:00Z",
            "valid_until": "2026-04-03T12:00:00Z"
        }
    ],
    "total": 1
}
```

### Revoke Consent

**Endpoint:** `DELETE /openbanking/consents/{consent_id}`

User can revoke consent at any time, immediately blocking the third-party app's access.

---

# 6. Account Information Service (AIS)

All AIS endpoints require OAuth2 access token with appropriate scope.

## Get User's Accounts

**Endpoint:** `GET /openbanking/obp/v5.1.0/my/accounts`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
    "accounts": [
        {
            "id": "123",
            "bank_id": "kitbank",
            "label": "Main Checking",
            "account_type": "checking",
            "account_routings": [
                {"scheme": "AccountNumber", "address": "1234567890"},
                {"scheme": "IBAN", "address": "KE12KITB0001234567890"}
            ]
        },
        {
            "id": "456",
            "bank_id": "kitbank",
            "label": "Savings",
            "account_type": "savings",
            "account_routings": [
                {"scheme": "AccountNumber", "address": "0987654321"}
            ]
        }
    ]
}
```

## Get Account Details

**Endpoint:** `GET /openbanking/obp/v5.1.0/banks/{bank_id}/accounts/{account_id}/account`

**Response:**
```json
{
    "id": "123",
    "bank_id": "kitbank",
    "label": "Main Checking",
    "number": "1234567890",
    "account_type": "checking",
    "balance": {
        "currency": "USD",
        "amount": "5432.10"
    },
    "IBAN": "KE12KITB0001234567890",
    "swift_bic": "KITBKENA",
    "owners": [
        {
            "id": "789",
            "provider": "kitbank",
            "display_name": "John Doe"
        }
    ],
    "account_routings": [
        {"scheme": "AccountNumber", "address": "1234567890"},
        {"scheme": "IBAN", "address": "KE12KITB0001234567890"}
    ]
}
```

## Get Account Balance

**Endpoint:** `GET /openbanking/obp/v5.1.0/banks/{bank_id}/accounts/{account_id}/balances`

**Response:**
```json
{
    "account_id": "123",
    "bank_id": "kitbank",
    "balances": [
        {
            "currency": "USD",
            "amount": "5432.10"
        }
    ]
}
```

## Get Transactions

**Endpoint:** `GET /openbanking/obp/v5.1.0/banks/{bank_id}/accounts/{account_id}/transactions`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| limit | Integer | Results per page (max 100) |
| offset | Integer | Pagination offset |
| from_date | String | Filter: start date (ISO 8601) |
| to_date | String | Filter: end date (ISO 8601) |

**Response:**
```json
{
    "transactions": [
        {
            "id": "txn_001",
            "bank_id": "kitbank",
            "account_id": "123",
            "this_account": {
                "id": "123",
                "bank_id": "kitbank"
            },
            "other_account": {
                "id": "456",
                "bank_id": "kitbank",
                "holder": {"name": "Jane Smith"}
            },
            "details": {
                "type": "transfer",
                "description": "Payment for services",
                "posted": "2026-01-02T14:30:00Z",
                "completed": "2026-01-02T14:30:05Z",
                "value": {
                    "currency": "USD",
                    "amount": "-150.00"
                },
                "status": "completed"
            }
        }
    ]
}
```

---

# 7. Payment Initiation Service (PIS)

PIS allows third-party apps to initiate payments on behalf of users. All payments require **Strong Customer Authentication (SCA)**.

## Initiate Payment

**Endpoint:** `POST /openbanking/payments`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
    "debtor_account": "123",
    "creditor_account": "KE98765432109876543210",
    "creditor_name": "John's Coffee Shop",
    "amount": 25.50,
    "currency": "USD",
    "reference": "INV-2026-001",
    "description": "Coffee purchase"
}
```

**Response:**
```json
{
    "payment_id": "pay_abc123xyz",
    "status": "pending",
    "created_at": "2026-01-03T12:00:00Z",
    "debtor_account": "123",
    "creditor_account": "KE98765432109876543210",
    "creditor_name": "John's Coffee Shop",
    "amount": 25.50,
    "currency": "USD",
    "authorization_url": "https://kitbank.net/payments/pay_abc123xyz/authorize"
}
```

## Payment Lifecycle

```
PENDING → PROCESSING → COMPLETED
    ↓         ↓
    └─────────┴──→ FAILED
                   CANCELLED
```

## Get Payment Status

**Endpoint:** `GET /openbanking/payments/{payment_id}`

**Response:**
```json
{
    "payment_id": "pay_abc123xyz",
    "status": "completed",
    "created_at": "2026-01-03T12:00:00Z",
    "updated_at": "2026-01-03T12:00:30Z",
    "completed_at": "2026-01-03T12:00:30Z",
    "failure_reason": null
}
```

## Authorize Payment (SCA)

**Endpoint:** `POST /openbanking/payments/{payment_id}/authorize`

User must complete Strong Customer Authentication (e.g., biometric, OTP) to authorize the payment.

## Cancel Payment

**Endpoint:** `POST /openbanking/payments/{payment_id}/cancel`

Only pending payments can be cancelled.

---

# 8. Security Model

## Authentication Layers

| Layer | Method | Purpose |
|-------|--------|---------|
| **App Authentication** | client_id + client_secret | Verify the third-party app |
| **User Authentication** | OAuth2 access token | Verify the bank customer |
| **Consent Verification** | Consent record | Verify user granted permission |
| **Scope Validation** | Token scopes | Verify access to specific resources |

## Token Security

| Token Type | Lifetime | Storage |
|------------|----------|---------|
| Authorization Code | 10 minutes | Hashed (SHA-256) |
| Access Token | 1 hour | Hashed (SHA-256) |
| Refresh Token | 30 days | Hashed (SHA-256) |
| Client Secret | Permanent | Hashed (bcrypt) |

> ⚠️ **Never store tokens in plain text!** All tokens are stored as SHA-256 hashes.

## Rate Limiting

| Limit | Default |
|-------|---------|
| Per Minute | 60 requests |
| Per Day | 10,000 requests |

Rate limit headers in response:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 55
X-RateLimit-Reset: 2026-01-03T12:01:00Z
```

## Strong Customer Authentication (SCA)

Required for:
- Payment initiation (all amounts)
- First-time consent authorization
- Token refresh after 90 days

SCA methods:
- Biometric (fingerprint, face)
- One-Time Password (OTP)
- Hardware security key

---

# 9. API Reference

## Base URL

```
Production: https://kitbank.net/api/openbanking
Sandbox:    https://sandbox.kitbank.net/api/openbanking
```

## Complete Endpoint List

### Developer Portal

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /developers/apps | Register new app |
| GET | /developers/apps | List your apps |
| GET | /developers/apps/{id} | Get app details |
| PUT | /developers/apps/{id} | Update app |
| DELETE | /developers/apps/{id} | Delete app |
| POST | /developers/apps/{id}/credentials | Regenerate credentials |
| POST | /developers/apps/{id}/submit-for-review | Submit for production |
| GET | /developers/sandbox/test-users | Get sandbox test users |
| GET | /developers/documentation | Get API docs links |

### OAuth2

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /oauth/authorize | Authorization endpoint |
| POST | /oauth/token | Token exchange |
| POST | /oauth/revoke | Revoke token |
| GET | /oauth/userinfo | Get user info (OpenID Connect) |
| GET | /.well-known/openid-configuration | Discovery document |
| GET | /.well-known/jwks.json | JSON Web Key Set |

### Consent Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /consents | Create consent request |
| GET | /consents | List user's consents |
| GET | /consents/{consent_id} | Get consent details |
| PUT | /consents/{consent_id}/authorize | Authorize/reject consent |
| DELETE | /consents/{consent_id} | Revoke consent |

### Account Information (OBP v5.1.0)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /obp/v5.1.0/banks | List available banks |
| GET | /obp/v5.1.0/banks/{bank_id} | Get bank details |
| GET | /obp/v5.1.0/my/accounts | Get user's accounts |
| GET | /obp/v5.1.0/banks/{bank_id}/accounts/{account_id}/account | Get account details |
| GET | /obp/v5.1.0/banks/{bank_id}/accounts/{account_id}/balances | Get balance |
| GET | /obp/v5.1.0/banks/{bank_id}/accounts/{account_id}/transactions | Get transactions |
| GET | /obp/v5.1.0/banks/{bank_id}/accounts/{account_id}/transactions/{txn_id} | Get transaction |

### Payment Initiation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /payments | Initiate payment |
| GET | /payments/{payment_id} | Get payment status |
| POST | /payments/{payment_id}/authorize | Authorize payment (SCA) |
| POST | /payments/{payment_id}/cancel | Cancel payment |

---

# 10. Error Handling

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid/expired token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |

## OAuth2 Errors

```json
{
    "error": "invalid_grant",
    "error_description": "Authorization code expired"
}
```

| Error | Description |
|-------|-------------|
| invalid_client | Unknown client_id or wrong secret |
| invalid_grant | Code expired or already used |
| invalid_scope | Requested scope not allowed |
| access_denied | User denied consent |
| unauthorized_client | App not approved for this grant type |

## API Errors

```json
{
    "detail": "Consent not found",
    "status_code": 404
}
```

---

# Appendix A: Code Examples

## Python Example

```python
import requests

# Step 1: Exchange code for token
token_response = requests.post(
    "https://kitbank.net/api/openbanking/oauth/token",
    data={
        "grant_type": "authorization_code",
        "code": "AUTH_CODE_HERE",
        "redirect_uri": "https://myapp.com/callback",
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET"
    }
)
access_token = token_response.json()["access_token"]

# Step 2: Get accounts
accounts = requests.get(
    "https://kitbank.net/api/openbanking/obp/v5.1.0/my/accounts",
    headers={"Authorization": f"Bearer {access_token}"}
)
print(accounts.json())
```

## JavaScript Example

```javascript
// Step 1: Exchange code for token
const tokenResponse = await fetch(
    'https://kitbank.net/api/openbanking/oauth/token',
    {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
            grant_type: 'authorization_code',
            code: 'AUTH_CODE_HERE',
            redirect_uri: 'https://myapp.com/callback',
            client_id: 'YOUR_CLIENT_ID',
            client_secret: 'YOUR_CLIENT_SECRET'
        })
    }
);
const { access_token } = await tokenResponse.json();

// Step 2: Get accounts
const accounts = await fetch(
    'https://kitbank.net/api/openbanking/obp/v5.1.0/my/accounts',
    { headers: { 'Authorization': `Bearer ${access_token}` } }
);
console.log(await accounts.json());
```

---

# Appendix B: Sandbox Environment

## Test Credentials

| Username | Password | Description |
|----------|----------|-------------|
| test_user_1 | sandbox_pass_1 | Basic user with 2 accounts |
| test_user_2 | sandbox_pass_2 | Premium user with 5 accounts |
| test_user_3 | sandbox_pass_3 | Business user |

## Sandbox Limitations

- No real money transactions
- Limited to test data
- Refresh every 24 hours
- Same API endpoints with `/sandbox` prefix

---

**Document Version:** 1.0  
**Last Updated:** January 3, 2026  
**Contact:** api-support@kitbank.net

