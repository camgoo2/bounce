from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager
from enum import Enum
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

# Database setup (always save next to main.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "events.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Enum definitions
class InviteReplyStatus(str, Enum):
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
    #just thinking that current_invitee_id - This uses Foreign Key for database integrity and CRUD Update methods.
    current_invitee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timeout_minutes = Column(Integer, default=15)  # How long each person has to respond
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    invitees = relationship("EventInvitee", back_populates="event", cascade="all, delete-orphan")

class EventInvitee(Base):
    __tablename__ = "event_invitees"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    invitee_id = Column(Integer, ForeignKey("users.id"))
    priority = Column(Integer)
    status = Column(SAEnum(InviteReplyStatus, native_enum=False), default=InviteReplyStatus.pending)
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
    status: InviteReplyStatus
    invited_at: Optional[datetime]
    responded_at: Optional[datetime]

    class Config:
        orm_mode = True

class EventCreate(BaseModel):
    title: str
    creator_id: int
    invitees: List[InviteeCreate]
    timeout_minutes: int = 15  # Default 15 minutes

class EventResponse(BaseModel):
    id: int
    title: str
    creator_id: int
    status: EventStatus
    current_invitee_id: Optional[int]
    timeout_minutes: int
    invitees: List[EventInviteeResponse]
    message: str

    class Config:
        orm_mode = True

class InviteReplyRequest(BaseModel):
    status: InviteReplyStatus #Enum

class EventSummary(BaseModel):
    id: int
    title: str
    creator_id: int
    status: EventStatus
    timeout_minutes: int

    class Config:
        orm_mode = True

class MyInvitationResponse(BaseModel):
    event: EventSummary
    my_priority: int
    my_status: InviteReplyStatus
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

# Timeout handler function
def handle_invitation_timeout(event_id: int, invitee_id: int):
    """
    Called when an invitation times out.
    Auto-declines the current invitee and forwards to the next priority person.
    """
    db = SessionLocal()
    try:
        print(f"⏰ Timeout triggered for event_id={event_id}, invitee_id={invitee_id}")

        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print(f"❌ Event {event_id} not found")
            return

        # Check if this invitee is still the current one and hasn't responded
        current_invitee = db.query(EventInvitee).filter(
            EventInvitee.event_id == event_id,
            EventInvitee.invitee_id == invitee_id,
            EventInvitee.status == InviteReplyStatus.invited
        ).first()

        if not current_invitee:
            print(f"✅ Invitee {invitee_id} already responded or is not current invitee")
            return

        # Auto-decline due to timeout
        print(f"⏱️ Auto-declining invitee {invitee_id} due to timeout")
        current_invitee.status = InviteReplyStatus.declined
        current_invitee.responded_at = datetime.utcnow()
        db.commit()

        # Find next priority invitee
        next_invitee = db.query(EventInvitee).filter(
            EventInvitee.event_id == event_id,
            EventInvitee.status == InviteReplyStatus.pending
        ).order_by(EventInvitee.priority.asc()).first()

        if next_invitee:
            # Invite next person
            print(f"📨 Forwarding to next invitee: {next_invitee.invitee_id}")
            next_invitee.status = InviteReplyStatus.invited
            next_invitee.invited_at = datetime.utcnow()
            event.current_invitee_id = next_invitee.invitee_id
            event.status = EventStatus.active
            db.commit()

            # Schedule timeout for this new invitee
            schedule_invitation_timeout(event_id, next_invitee.invitee_id, event.timeout_minutes)
        else:
            # No more invitees - cancel event
            print(f"❌ No more invitees available - cancelling event {event_id}")
            event.status = EventStatus.cancelled
            event.current_invitee_id = None
            db.commit()

    except Exception as e:
        print(f"❌ Error in timeout handler: {e}")
        db.rollback()
    finally:
        db.close()

def schedule_invitation_timeout(event_id: int, invitee_id: int, timeout_minutes: int):
    """
    Schedule a timeout task for the given invitation.
    """
    run_time = datetime.now() + timedelta(minutes=timeout_minutes)
    job_id = f"event_{event_id}_invitee_{invitee_id}"

    print(f"⏰ Scheduling timeout for event {event_id}, invitee {invitee_id} at {run_time}")

    scheduler.add_job(
        func=handle_invitation_timeout,
        trigger=DateTrigger(run_date=run_time),
        args=[event_id, invitee_id],
        id=job_id,
        replace_existing=True  # Replace if job already exists
    )

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
    print("🚀 Scheduler started")
    yield
    scheduler.shutdown()
    print("🛑 Scheduler stopped")

app = FastAPI(lifespan=lifespan)

# Add CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Hi bounce team, you are healthy"}

# Endpoints
@app.post("/events", response_model=EventResponse, status_code=201)
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    # creator = db.query(User).filter(User.id == event.creator_id).first()
    # if not creator:
    #     raise HTTPException(status_code=404, detail="Creator not found")

    db_event = Event(
        title=event.title,
        creator_id=event.creator_id,
        status=EventStatus.pending,
        timeout_minutes=event.timeout_minutes
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
        print(f"  invitee_id aka friend : {user.id}")
        print(f"  priority: {invitee.priority}")

        # Adding the friends  to the event
        db_invitee = EventInvitee(
            event_id=db_event.id,
            invitee_id=user.id,
            priority=invitee.priority
        )
         
        db.add(db_invitee)
    
    db.commit()

    # Activate first priority
    first_invitee = db.query(EventInvitee).filter(EventInvitee.event_id == db_event.id).order_by(EventInvitee.priority.asc()).first()
    if first_invitee:
        first_invitee.status = InviteReplyStatus.invited
        first_invitee.invited_at = datetime.utcnow()
        db_event.current_invitee_id = first_invitee.invitee_id
        db_event.status = EventStatus.active
        db.commit()

        # Schedule timeout for first invitee
        schedule_invitation_timeout(db_event.id, first_invitee.invitee_id, db_event.timeout_minutes)

    db.refresh(db_event)
    db_event.message = "Event create successfully"
    print(db_event)
    return db_event

@app.post("/events/{event_id}/respond")
# Just sending the event status string only
async def respond_to_event( event_id: int, invite_reply: InviteReplyRequest, db: Session = Depends(get_db)):
    print("event_id = ", event_id)
    print('invite_reply= ',invite_reply.status)
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
    
    current_invitee.status = InviteReplyStatus(invite_reply.status) #invited->accepted or declined
    current_invitee.responded_at = datetime.utcnow()
    db.commit()
    
    if invite_reply.status == "accepted":
        event.status = EventStatus.accepted #updates the event to accepted, which is what we want
        db.commit()
        print("this is the event.status",event.status)

        # Cancel the scheduled timeout since they responded
        try:
            job_id = f"event_{event_id}_invitee_{current_invitee.invitee_id}"
            scheduler.remove_job(job_id)
            print(f"✅ Cancelled timeout job {job_id}")
        except Exception as e:
            print(f"⚠️ Could not cancel timeout job: {e}")

        return {"message": "Event accepted!"}
    
    elif invite_reply.status == "declined":
        # Cancel the scheduled timeout since they responded
        try:
            job_id = f"event_{event_id}_invitee_{current_invitee.invitee_id}"
            scheduler.remove_job(job_id)
            print(f"✅ Cancelled timeout job {job_id}")
        except Exception as e:
            print(f"⚠️ Could not cancel timeout job: {e}")

        next_invitee = db.query(EventInvitee).filter(
            EventInvitee.event_id == event_id,
            EventInvitee.status == InviteReplyStatus.pending
        ).order_by(EventInvitee.priority.asc()).first()

        if next_invitee:
            next_invitee.status = InviteReplyStatus.invited
            next_invitee.invited_at = datetime.utcnow()
            event.current_invitee_id = next_invitee.invitee_id
            event.status = EventStatus.active
            db.commit()

            # Schedule timeout for next invitee
            schedule_invitation_timeout(event.id, next_invitee.invitee_id, event.timeout_minutes)

            return {"message": "Declined—invitation forwarded to next priority"}
        else:
            event.status = EventStatus.cancelled
            event.current_invitee_id = None
            db.commit()
            return {"message": "Declined—no more priorities available"}
    
    db.commit()
    return {"message": "Response recorded"}


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
        # Skip invitations where user was never actually invited
        # (pending status AND not their turn AND event is in any non-pending state)
        if (invitation.status == InviteReplyStatus.pending and 
            invitation.event.current_invitee_id != user_id):
            # with continue is activated we get taken back to the start of the loop for the next invitation.
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