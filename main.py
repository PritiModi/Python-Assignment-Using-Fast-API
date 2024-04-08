from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import List, Optional
import uuid

# FastAPI app
app = FastAPI()

# SQLAlchemy setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Pydantic models
class UserBase(BaseModel):
    name: str
    email: str
    password: str
    referral_code: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: str
    timestamp: Optional[datetime]

    class Config:
        orm_mode = True

class ReferralBase(BaseModel):
    user_id: str
    referred_user_id: str

class ReferralCreate(ReferralBase):
    pass

class Referral(ReferralBase):
    id: str

    class Config:
        orm_mode = True

# SQLAlchemy models
class UserModel(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    referral_code = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

class ReferralModel(Base):
    __tablename__ = "referrals"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    referred_user_id = Column(String, ForeignKey("users.id"))

    user = relationship("UserModel", foreign_keys=[user_id])
    referred_user = relationship("UserModel", foreign_keys=[referred_user_id])

# Create the tables in the database
Base.metadata.create_all(bind=engine)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API :: /users/  
# PURPOSE :: Register User
# Payload :: {
#   "name": "Adaaaama",
#   "email": "Priti@gmail.com",
#   "password": "1234545",
#   "referral_code": "priti123"
# }
@app.post("/users/", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    db_user = UserModel(**user.dict(), id=str(uuid.uuid4()), timestamp=datetime.now())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# API :: /getall_users/
# PURPOSE :: get all users
@app.get("/getall_users/", response_model=List[User])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(UserModel).all()
    return users


# API :: /users/{user_id}
# PURPOSE :: get user data user id wise
@app.get("/users/{user_id}", response_model=User)
def read_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# API :: /referrals/{user_id}
# PURSOSE :: get referral data from user table
@app.get("/referrals/{user_id}", response_model=List[User])
def read_referral(user_id: str, db: Session = Depends(get_db), page: int = 1, per_page: int = 20):
    check_current_user_refrel = db.query(UserModel.referral_code).filter(UserModel.id == user_id).first()
    referral_code = check_current_user_refrel[0]

    referral = db.query(UserModel).filter(UserModel.referral_code == referral_code).all()
    if referral is None:
        raise HTTPException(status_code=404, detail="Referral not found")

    total_records = len(referral)
    total_pages = (total_records + per_page - 1) // per_page

    if page < 1 or page > total_pages:
        raise HTTPException(status_code=404, detail="Invalid page number")

    start_index = (page - 1) * per_page
    end_index = min(start_index + per_page, total_records)
    return referral[start_index:end_index]




