from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.modules.users.models import User
from app.modules.transactions.schemas import TransactionCreate, TransactionResponse, TransactionUpdate
from app.modules.transactions.services import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("/", response_model=TransactionResponse)
def create_transaction(
    txn: TransactionCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = TransactionService(db)
    try:
        return service.create_transaction(txn)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[TransactionResponse])
def read_transactions(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = TransactionService(db)
    return service.get_transactions(skip=skip, limit=limit)

@router.get("/{txn_id}", response_model=TransactionResponse)
def read_transaction(
    txn_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = TransactionService(db)
    db_txn = service.get_transaction(txn_id)
    if db_txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_txn

@router.get("/account/{account_id}", response_model=List[TransactionResponse])
def read_account_transactions(
    account_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = TransactionService(db)
    return service.get_account_transactions(account_id)

@router.put("/{txn_id}", response_model=TransactionResponse)
def update_transaction(
    txn_id: int, 
    txn_in: TransactionUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = TransactionService(db)
    db_txn = service.update_transaction(txn_id, txn_in)
    if db_txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_txn

@router.delete("/{txn_id}", response_model=TransactionResponse)
def delete_transaction(
    txn_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = TransactionService(db)
    db_txn = service.delete_transaction(txn_id)
    if db_txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_txn
