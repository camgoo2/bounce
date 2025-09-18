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
DB_PATH = os.path.join(BASE_DIR, "events.db")
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

class EventStatus(str, Enum):
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

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    creator_id = Column(Integer, ForeignKey("users.id"))
    status = Column(SAEnum(EventStatus, native_enum=False), default=EventStatus.pending)
    #just thinking that current_invitee_id should maybe replaced with all invitee_id as only seeing 1 in table
#     [
#   {
#     "status": "active",
#     "title": "Golf tonight",
#     "current_invitee_id": 3,
#     "created_at": "2025-09-18T08:31:28.589627",
#     "creator_id": 1,
#     "id": 1,
#     "updated_at": "2025-09-18T08:31:28.601459"
#   }
# ]
    current_invitee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    invitees = relationship("EventInvitee", back_populates="event", cascade="all, delete-orphan")

class EventInvitee(Base):
    __tablename__ = "event_invitees"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    invitee_id = Column(Integer, ForeignKey("users.id"))
    priority = Column(Integer)
    status = Column(SAEnum(InviteStatus, native_enum=False), default=InviteStatus.pending)
    invited_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    event = relationship("Event", back_populates="invitees")

# Pydantic Models
class InviteeCreate(BaseModel):
    user_name: str
    priority: int

class EventInviteeResponse(BaseModel):
    invitee_id: int
    priority: int
    status: InviteStatus
    invited_at: Optional[datetime]
    responded_at: Optional[datetime]

    class Config:
        orm_mode = True

class EventCreate(BaseModel):
    title: str
    creator_id: int  
    invitees: List[InviteeCreate]

class EventResponse(BaseModel):
    id: int
    title: str
    creator_id: int
    status: EventStatus
    current_invitee_id: Optional[int]
    invitees: List[EventInviteeResponse]

    class Config:
        orm_mode = True

class EventResponseRequest(BaseModel):
    status: str

class EventSummary(BaseModel):
    id: int
    title: str
    creator_id: int
    status: EventStatus
    
    class Config:
        orm_mode = True

class MyInvitationResponse(BaseModel):
    event: EventSummary
    my_priority: int
    my_status: InviteStatus
    invited_at: Optional[datetime]
    responded_at: Optional[datetime]
    is_current_invitee: bool
    
    class Config:
        orm_mode = True

class UserInvitationsResponse(BaseModel):
    user_id: int
    username: str
    pending_invitations: List[MyInvitationResponse]
    invitation_history: List[MyInvitationResponse]

# Add these to your Pydantic Models section
class UserCreate(BaseModel):
    username: str
    full_name: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    
    class Config:
        orm_mode = True

# Add this new Pydantic model for sent invitations
class SentInvitationResponse(BaseModel):
    event: EventSummary
    current_invitee_username: Optional[str]
    current_invitee_full_name: Optional[str]
    invitees_count: int
    
    class Config:
        orm_mode = True

class UserSentInvitationsResponse(BaseModel):
    user_id: int
    username: str
    sent_invitations: List[SentInvitationResponse]

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
    yield

app = FastAPI(lifespan=lifespan)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Hi bounce team, you are healthy"}

# Endpoints
@app.post("/events", response_model=EventResponse, status_code=201)
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    creator = db.query(User).filter(User.id == event.creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    db_event = Event(
        title=event.title,
        creator_id=creator.id,
        status=EventStatus.pending
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # Add invitees
    for invitee in event.invitees:
        user = db.query(User).filter(User.username == invitee.user_name).first()
        print("I am the invited friend, this is my user id >",user.id)
        if not user:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Invitee  {invitee.user_name} not found")
        
        print(f"  event_id: {db_event.id}")
        print(f"  invitee_id: {user.id}")
        print(f"  priority: {invitee.priority}")

        db_invitee = EventInvitee(
            event_id=db_event.id,
            invitee_id=user.id,
            priority=invitee.priority
        )
        db.add(db_invitee)
    
    db.commit()
    
    # Activate first priority
    first_invitee = db.query(EventInvitee).filter(
        EventInvitee.event_id == db_event.id
    ).order_by(EventInvitee.priority.asc()).first()
    if first_invitee:
        first_invitee.status = InviteStatus.invited
        first_invitee.invited_at = datetime.utcnow()
        db_event.current_invitee_id = first_invitee.invitee_id
        db_event.status = EventStatus.active
        db.commit()
    
    db.refresh(db_event)
    
    return db_event

@app.post("/events/{event_id}/respond")
async def respond_to_event(
    event_id: int,
    response: EventResponseRequest,
    db: Session = Depends(get_db)
):
    print("event_id = ", event_id)
    print('respone status= ',response.status)
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    current_invitee = db.query(EventInvitee).filter(
        EventInvitee.event_id == event_id,
        EventInvitee.invitee_id == event.current_invitee_id
    ).first()
    print("current invitee= ",current_invitee.invitee_id)
    if not current_invitee:
        raise HTTPException(status_code=400, detail="No active invitee")
    
    current_invitee.status = InviteStatus(response.status)
    current_invitee.responded_at = datetime.utcnow()
    db.commit()
    
    if response.status == "accepted":
        event.status = EventStatus.accepted
        db.commit()
        print("this is the event.status",event.status)
        return {"message": "Event accepted!"}
    
    # elif response.status == "declined":
    #     next_invitee = db.query(EventInvitee).filter(
    #         EventInvitee.event_id == event_id,
    #         EventInvitee.status == InviteStatus.pending
    #     ).order_by(EventInvitee.priority.asc()).first()
        
    #     if next_invitee:
    #         next_invitee.status = InviteStatus.invited
    #         next_invitee.invited_at = datetime.utcnow()
    #         event.current_invitee_id = next_invitee.invitee_id
    #         event.status = EventStatus.active
    #         db.commit()
    #         return {"message": "Declined—invitation forwarded to next priority"}
    #     else:
    #         event.status = EventStatus.cancelled
    #         event.current_invitee_id = None
    #         db.commit()
    #         return {"message": "Declined—no more priorities available"}
    
    db.commit()
    return {"message": "Response recorded"}

@app.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    print("this is the event id",event.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail=f"Username '{user.username}' already exists"
        )
    
    # Create new user
    db_user = User(
        username=user.username,
        full_name=user.full_name
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    print(f"Created new user: {db_user}")
    return db_user

@app.get("/users")
async def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@app.get("/users/{user_id}/invitations", response_model=UserInvitationsResponse)
async def get_user_invitations(user_id: int, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all invitations for this user
    invitations = db.query(EventInvitee).filter(
        EventInvitee.invitee_id == user_id
    ).join(Event).all()
    
    pending_invitations = []
    invitation_history = []
    
    for invitation in invitations:
        # Skip invitations where:
        # - User hasn't been invited yet (status is still "pending")
        # - AND they're not the current invitee
        # - AND the event is still active
        if (invitation.status == InviteStatus.pending and 
            invitation.event.current_invitee_id != user_id and
            invitation.event.status == EventStatus.active):
            continue  # Don't show this invitation at all
        
        invitation_data = MyInvitationResponse(
            event=EventSummary(
                id=invitation.event.id,
                title=invitation.event.title,
                creator_id=invitation.event.creator_id,
                status=invitation.event.status
            ),
            my_priority=invitation.priority,
            my_status=invitation.status,
            invited_at=invitation.invited_at,
            responded_at=invitation.responded_at,
            is_current_invitee=(invitation.event.current_invitee_id == user_id)
        )
        
        # If they're the current invitee and event is active, it's pending
        if (invitation.event.current_invitee_id == user_id and 
            invitation.event.status == EventStatus.active):
            pending_invitations.append(invitation_data)
        else:
            invitation_history.append(invitation_data)
    
    return UserInvitationsResponse(
        user_id=user.id,
        username=user.username,
        pending_invitations=pending_invitations,
        invitation_history=invitation_history
    )

@app.get("/users/{username}")
async def get_users_login(username: str, db: Session = Depends(get_db)):
    username = db.query(User).filter(User.username == username).first()
    print(username)
    return username


@app.get("/users/{user_id}/sent-invitations", response_model=UserSentInvitationsResponse)
async def get_user_sent_invitations(user_id: int, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all events created by this user
    events = db.query(Event).filter(Event.creator_id == user_id).all()
    
    sent_invitations = []
    
    for event in events:
        current_invitee_username = None
        current_invitee_full_name = None
        
        # Get current invitee details if there is one
        if event.current_invitee_id:
            current_invitee = db.query(User).filter(User.id == event.current_invitee_id).first()
            if current_invitee:
                current_invitee_username = current_invitee.username
                current_invitee_full_name = current_invitee.full_name
        
        # Count total invitees for this event
        invitees_count = db.query(EventInvitee).filter(EventInvitee.event_id == event.id).count()
        
        sent_invitation = SentInvitationResponse(
            event=EventSummary(
                id=event.id,
                title=event.title,
                creator_id=event.creator_id,
                status=event.status
            ),
            current_invitee_username=current_invitee_username,
            current_invitee_full_name=current_invitee_full_name,
            invitees_count=invitees_count
        )
        
        sent_invitations.append(sent_invitation)
    
    return UserSentInvitationsResponse(
        user_id=user.id,
        username=user.username,
        sent_invitations=sent_invitations
    )

#DEBUG Tables
@app.get("/debug/users")
async def debug_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@app.get("/debug/events")
async def debug_events(db: Session = Depends(get_db)):
    events = db.query(Event).all()
    return events

@app.get("/debug/event-invitees")
async def debug_event_invitees(db: Session = Depends(get_db)):
    invitees = db.query(EventInvitee).all()
    return invitees

@app.post("/debug/clear-all-data")
async def clear_all_data(db: Session = Depends(get_db)):
    """
    DANGER: This will delete ALL data from the database!
    Use only in development.
    """
    try:
        # Delete in order to respect foreign key constraints
        db.query(EventInvitee).delete()
        db.query(Event).delete()
        db.query(User).delete()
        db.commit()
        
        return {"message": "All data cleared"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")