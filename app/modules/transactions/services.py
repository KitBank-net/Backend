from sqlalchemy.orm import Session
from app.modules.transactions.models import Transaction
from app.modules.transactions.schemas import TransactionCreate, TransactionUpdate
from app.modules.accounts.models import Account
import uuid

class TransactionService:
    def __init__(self, db: Session):
        self.db = db

    def create_transaction(self, txn: TransactionCreate):
        # 1. Check account existence
        account = self.db.query(Account).filter(Account.id == txn.account_id).first()
        if not account:
            raise ValueError("Account not found")

        # 2. Update balance
        if txn.transaction_type == "debit":
            if account.balance < txn.amount:
                raise ValueError("Insufficient funds")
            account.balance -= txn.amount
        elif txn.transaction_type == "credit":
            account.balance += txn.amount

        # 3. Create transaction record
        db_txn = Transaction(
            account_id=txn.account_id,
            amount=txn.amount,
            transaction_type=txn.transaction_type,
            currency=txn.currency,
            status="completed",
            reference_code=f"TXN-{uuid.uuid4().hex[:8].upper()}"
        )
        self.db.add(db_txn)
        self.db.commit()
        self.db.refresh(db_txn)
        return db_txn

    def get_transaction(self, txn_id: int):
        return self.db.query(Transaction).filter(Transaction.id == txn_id).first()

    def get_transactions(self, skip: int = 0, limit: int = 100):
        return self.db.query(Transaction).offset(skip).limit(limit).all()

    def get_account_transactions(self, account_id: int):
        return self.db.query(Transaction).filter(Transaction.account_id == account_id).all()

    def update_transaction(self, txn_id: int, txn_in: TransactionUpdate):
        db_txn = self.get_transaction(txn_id)
        if not db_txn:
            return None
        
        if txn_in.status:
            db_txn.status = txn_in.status
            
        self.db.commit()
        self.db.refresh(db_txn)
        return db_txn

    def delete_transaction(self, txn_id: int):
        db_txn = self.get_transaction(txn_id)
        if not db_txn:
            return None
        self.db.delete(db_txn)
        self.db.commit()
        return db_txn
