from sqlalchemy.orm import Session
from app.modules.loans.models import Loan
from app.modules.loans.schemas import LoanCreate, LoanRepayment, LoanUpdate

class LoanService:
    def __init__(self, db: Session):
        self.db = db

    def apply_loan(self, loan: LoanCreate):
        db_loan = Loan(
            user_id=loan.user_id,
            amount=loan.amount,
            term_months=loan.term_months,
            purpose=loan.purpose,
            remaining_balance=loan.amount,
            status="pending"
        )
        self.db.add(db_loan)
        self.db.commit()
        self.db.refresh(db_loan)
        return db_loan

    def get_loan(self, loan_id: int):
        return self.db.query(Loan).filter(Loan.id == loan_id).first()

    def get_loans(self, skip: int = 0, limit: int = 100):
        return self.db.query(Loan).offset(skip).limit(limit).all()

    def get_user_loans(self, user_id: int):
        return self.db.query(Loan).filter(Loan.user_id == user_id).all()

    def update_loan(self, loan_id: int, loan_in: LoanUpdate):
        db_loan = self.get_loan(loan_id)
        if not db_loan:
            return None
        
        if loan_in.status:
            db_loan.status = loan_in.status
        if loan_in.remaining_balance is not None:
            db_loan.remaining_balance = loan_in.remaining_balance
            
        self.db.commit()
        self.db.refresh(db_loan)
        return db_loan

    def repay_loan(self, loan_id: int, repayment: LoanRepayment):
        db_loan = self.get_loan(loan_id)
        if not db_loan:
            return None
        
        db_loan.remaining_balance -= repayment.amount
        if db_loan.remaining_balance <= 0:
            db_loan.remaining_balance = 0
            db_loan.status = "paid"
            
        self.db.commit()
        self.db.refresh(db_loan)
        return db_loan

    def delete_loan(self, loan_id: int):
        db_loan = self.get_loan(loan_id)
        if not db_loan:
            return None
        self.db.delete(db_loan)
        self.db.commit()
        return db_loan
