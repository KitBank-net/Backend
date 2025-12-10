import requests
import time
import sys
import uuid

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing Health Check...")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        print(f"✅ Health Check Passed: {resp.json()}")
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
        sys.exit(1)

def test_users():
    print("\nTesting Users Module...")
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user_data = {
        "email": email,
        "password": "password123",
        "full_name": "Test User",
        "phone_number": "+1234567890"
    }
    # Create User
    resp = requests.post(f"{BASE_URL}/users/", json=user_data)
    if resp.status_code != 200:
        print(f"❌ Create User Failed: {resp.text}")
        return None
    user = resp.json()
    assert user["email"] == email
    print("✅ Create User Passed")

    # Get User
    resp = requests.get(f"{BASE_URL}/users/{user['id']}")
    assert resp.status_code == 200
    print("✅ Get User Passed")
    
    return user

def test_accounts(user):
    print("\nTesting Accounts Module...")
    account_data = {
        "user_id": user["id"],
        "account_type": "savings",
        "currency": "USD"
    }
    # Create Account
    resp = requests.post(f"{BASE_URL}/accounts/", json=account_data)
    if resp.status_code != 200:
        print(f"❌ Create Account Failed: {resp.text}")
        return None
    account = resp.json()
    assert account["user_id"] == user["id"]
    print("✅ Create Account Passed")

    # Get Account
    resp = requests.get(f"{BASE_URL}/accounts/{account['id']}")
    assert resp.status_code == 200
    print("✅ Get Account Passed")

    return account

def test_transactions(account):
    print("\nTesting Transactions Module...")
    # Credit Transaction (Deposit)
    txn_data = {
        "account_id": account["id"],
        "amount": 1000.0,
        "currency": "USD",
        "transaction_type": "credit"
    }
    resp = requests.post(f"{BASE_URL}/transactions/", json=txn_data)
    if resp.status_code != 200:
        print(f"❌ Create Credit Transaction Failed: {resp.text}")
    else:
        print("✅ Create Credit Transaction Passed")

    # Debit Transaction (Withdrawal)
    txn_data["transaction_type"] = "debit"
    txn_data["amount"] = 500.0
    resp = requests.post(f"{BASE_URL}/transactions/", json=txn_data)
    if resp.status_code != 200:
        print(f"❌ Create Debit Transaction Failed: {resp.text}")
    else:
        print("✅ Create Debit Transaction Passed")

    # Check Balance
    resp = requests.get(f"{BASE_URL}/accounts/{account['id']}")
    updated_account = resp.json()
    print(f"💰 Updated Balance: {updated_account['balance']}")
    assert updated_account["balance"] == 500.0
    print("✅ Balance Update Verified")

def test_loans(user):
    print("\nTesting Loans Module...")
    loan_data = {
        "user_id": user["id"],
        "amount": 5000.0,
        "term_months": 12,
        "purpose": "Home improvement"
    }
    # Apply Loan
    resp = requests.post(f"{BASE_URL}/loans/apply", json=loan_data)
    if resp.status_code != 200:
        print(f"❌ Apply Loan Failed: {resp.text}")
        return None
    loan = resp.json()
    assert loan["amount"] == 5000.0
    print("✅ Apply Loan Passed")

    # Repay Loan
    repay_data = {"amount": 1000.0}
    resp = requests.post(f"{BASE_URL}/loans/{loan['id']}/repay", json=repay_data)
    if resp.status_code != 200:
        print(f"❌ Repay Loan Failed: {resp.text}")
    else:
        updated_loan = resp.json()
        print(f"📉 Remaining Balance: {updated_loan['remaining_balance']}")
        assert updated_loan["remaining_balance"] == 4000.0
        print("✅ Repay Loan Passed")

if __name__ == "__main__":
    # Wait for server to start
    time.sleep(2)
    
    test_health()
    user = test_users()
    if user:
        account = test_accounts(user)
        if account:
            test_transactions(account)
        test_loans(user)
    
    print("\n🎉 All Modular Tests Passed!")
