from fastapi import APIRouter, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import User  # adjust if your models.py defines this
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["Users"])

class UserBase(BaseModel):
    username: str
    role: str

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: str | None = None

@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    user = USERS.get(username)

    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {"username": username, "role": user["role"], "name": user["name"]}

@router.get("/")
def get_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    return {"users": users, "total": total}

@router.get("/stats")
def get_user_stats(db: Session = Depends(get_db)):
    total = db.query(User).count()
    admin = db.query(User).filter(User.role == "Admin").count()
    editor = db.query(User).filter(User.role == "Editor").count()
    return {"total": total, "admin": admin, "editor": editor}

@router.post("/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    new_user = User(username=user.username, role=user.role, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/{user_id}")
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = user.username
    db_user.role = user.role
    if user.password:
        db_user.password = user.password
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted"}
