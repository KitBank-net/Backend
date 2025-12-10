from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.modules.users.models import User
from app.modules.loans.schemas import LoanCreate, LoanResponse, LoanRepayment, LoanUpdate
from app.modules.loans.services import LoanService

router = APIRouter(prefix="/loans", tags=["loans"])

@router.post("/apply", response_model=LoanResponse)
def apply_loan(
    loan: LoanCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = LoanService(db)
    return service.apply_loan(loan)

@router.get("/", response_model=List[LoanResponse])
def read_loans(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = LoanService(db)
    return service.get_loans(skip=skip, limit=limit)

@router.get("/{loan_id}", response_model=LoanResponse)
def read_loan(
    loan_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = LoanService(db)
    db_loan = service.get_loan(loan_id)
    if db_loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    return db_loan

@router.get("/user/{user_id}", response_model=List[LoanResponse])
def read_user_loans(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = LoanService(db)
    return service.get_user_loans(user_id)

@router.put("/{loan_id}", response_model=LoanResponse)
def update_loan(
    loan_id: int, 
    loan_in: LoanUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = LoanService(db)
    db_loan = service.update_loan(loan_id, loan_in)
    if db_loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    return db_loan

@router.post("/{loan_id}/repay", response_model=LoanResponse)
def repay_loan(
    loan_id: int, 
    repayment: LoanRepayment, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = LoanService(db)
    db_loan = service.repay_loan(loan_id, repayment)
    if db_loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    return db_loan

@router.delete("/{loan_id}", response_model=LoanResponse)
def delete_loan(
    loan_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = LoanService(db)
    db_loan = service.delete_loan(loan_id)
    if db_loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    return db_loan
