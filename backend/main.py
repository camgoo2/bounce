from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager
from enum import Enum
import os

# Database setup (always save next to main.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bounces.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Enum definitions
class InviteStatus(str, Enum):
    pending = "pending"
    invited = "invited"
    accepted = "accepted"
    declined = "declined"
    cancelled = "cancelled"

class BounceStatus(str, Enum):
    pending = "pending"
    active = "active"
    accepted = "accepted"
    cancelled = "cancelled"
    completed = "completed"

# SQLAlchemy Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    full_name = Column(String, nullable=True)

class Bounce(Base):
    __tablename__ = "bounces"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    date = Column(DateTime)
    creator_id = Column(Integer, ForeignKey("users.id"))
    status = Column(SAEnum(BounceStatus, native_enum=False), default=BounceStatus.pending)
    current_invitee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    invitees = relationship("BounceInvitee", back_populates="bounce", cascade="all, delete-orphan")

class BounceInvitee(Base):
    __tablename__ = "bounce_invitees"
    id = Column(Integer, primary_key=True)
    bounce_id = Column(Integer, ForeignKey("bounces.id"))
    invitee_id = Column(Integer, ForeignKey("users.id"))
    priority = Column(Integer)
    status = Column(SAEnum(InviteStatus, native_enum=False), default=InviteStatus.pending)
    invited_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    bounce = relationship("Bounce", back_populates="invitees")

# Pydantic Models
class InviteeCreate(BaseModel):
    user_id: int
    priority: int

class BounceInviteeResponse(BaseModel):
    invitee_id: int
    priority: int
    status: InviteStatus
    invited_at: Optional[datetime]
    responded_at: Optional[datetime]

    class Config:
        orm_mode = True

class BounceCreate(BaseModel):
    title: str
    date: datetime
    invitees: List[InviteeCreate]

class BounceResponse(BaseModel):
    id: int
    title: str
    date: datetime
    creator_id: int
    status: BounceStatus
    current_invitee_id: Optional[int]
    invitees: List[BounceInviteeResponse]

    class Config:
        orm_mode = True

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Pre-populate users
    if not db.query(User).all():
        users = [
            User(username="cam", full_name="Cam Goodhue"),
            User(username="paul", full_name="Paul Smith"),
            User(username="tom", full_name="Tom Jones")
        ]
        db.add_all(users)
        db.commit()
    db.close()
    yield

app = FastAPI(lifespan=lifespan)

# Endpoints
@app.post("/bounces", response_model=BounceResponse, status_code=201)
async def create_bounce(bounce: BounceCreate, db: Session = Depends(get_db)):
    creator = db.query(User).filter(User.username == "cam").first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    db_bounce = Bounce(
        title=bounce.title,
        date=bounce.date,
        creator_id=creator.id,
        status=BounceStatus.pending
    )
    db.add(db_bounce)
    db.commit()
    db.refresh(db_bounce)
    
    # Add invitees
    for invitee in bounce.invitees:
        user = db.query(User).filter(User.id == invitee.user_id).first()
        if not user:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Invitee ID {invitee.user_id} not found")
        db_invitee = BounceInvitee(
            bounce_id=db_bounce.id,
            invitee_id=user.id,
            priority=invitee.priority
        )
        db.add(db_invitee)
    
    db.commit()
    
    # Activate first priority
    first_invitee = db.query(BounceInvitee).filter(
        BounceInvitee.bounce_id == db_bounce.id
    ).order_by(BounceInvitee.priority.asc()).first()
    if first_invitee:
        first_invitee.status = InviteStatus.invited
        first_invitee.invited_at = datetime.utcnow()
        db_bounce.current_invitee_id = first_invitee.invitee_id
        db_bounce.status = BounceStatus.active
        db.commit()
    
    db.refresh(db_bounce)
    return db_bounce

@app.post("/bounces/{bounce_id}/respond")
async def respond_to_bounce(
    bounce_id: int,
    response: dict,  # e.g., {"status": "declined"} or {"status": "accepted"}
    db: Session = Depends(get_db)
):
    bounce = db.query(Bounce).filter(Bounce.id == bounce_id).first()
    if not bounce:
        raise HTTPException(status_code=404, detail="Bounce not found")
    
    current_invitee = db.query(BounceInvitee).filter(
        BounceInvitee.bounce_id == bounce_id,
        BounceInvitee.invitee_id == bounce.current_invitee_id
    ).first()
    
    if not current_invitee:
        raise HTTPException(status_code=400, detail="No active invitee")
    
    current_invitee.status = InviteStatus(response["status"])
    current_invitee.responded_at = datetime.utcnow()
    db.commit()
    
    if response["status"] == "accepted":
        bounce.status = BounceStatus.accepted
        db.commit()
        return {"message": "Bounce accepted!"}
    
    elif response["status"] == "declined":
        next_invitee = db.query(BounceInvitee).filter(
            BounceInvitee.bounce_id == bounce_id,
            BounceInvitee.status == InviteStatus.pending
        ).order_by(BounceInvitee.priority.asc()).first()
        
        if next_invitee:
            next_invitee.status = InviteStatus.invited
            next_invitee.invited_at = datetime.utcnow()
            bounce.current_invitee_id = next_invitee.invitee_id
            bounce.status = BounceStatus.active
            db.commit()
            return {"message": "Declined—invitation forwarded to next priority"}
        else:
            bounce.status = BounceStatus.cancelled
            bounce.current_invitee_id = None
            db.commit()
            return {"message": "Declined—no more priorities available"}
    
    db.commit()
    return {"message": "Response recorded"}

@app.get("/bounces/{bounce_id}", response_model=BounceResponse)
async def get_bounce(bounce_id: int, db: Session = Depends(get_db)):
    bounce = db.query(Bounce).filter(Bounce.id == bounce_id).first()
    if not bounce:
        raise HTTPException(status_code=404, detail="Bounce not found")
    return bounce
