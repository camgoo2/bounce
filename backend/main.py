from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager
from enum import Enum
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from passlib.context import CryptContext
from jose import JWTError, jwt

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Use argon2 for password hashing (better Python 3.14 support than bcrypt)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer()

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
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    full_name = Column(String, nullable=True)
    device_token = Column(String, nullable=True)  # For push notifications (APNs)
    created_at = Column(DateTime, default=datetime.utcnow)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    creator_id = Column(Integer, ForeignKey("users.id"))
    status = Column(SAEnum(EventStatus, native_enum=False), default=EventStatus.pending)
    current_invitee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timeout_minutes = Column(Integer, default=15)
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

# Pydantic Models - Auth
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: "UserResponse"

class DeviceTokenUpdate(BaseModel):
    device_token: str

# Pydantic Models - Users
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    created_at: datetime

    class Config:
        from_attributes = True

# Pydantic Models - Events
class InviteeCreate(BaseModel):
    user_name: str
    priority: int

class EventCreate(BaseModel):
    title: str
    invitees: List[InviteeCreate]
    timeout_minutes: int = 15

class EventInviteeResponse(BaseModel):
    invitee_id: int
    priority: int
    status: InviteReplyStatus
    invited_at: Optional[datetime]
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True

class EventResponse(BaseModel):
    id: int
    title: str
    creator_id: int
    status: EventStatus
    current_invitee_id: Optional[int]
    timeout_minutes: int
    created_at: datetime
    invitees: List[EventInviteeResponse]

    class Config:
        from_attributes = True

class EventSummary(BaseModel):
    id: int
    title: str
    creator_id: int
    status: EventStatus
    timeout_minutes: int
    created_at: datetime

    class Config:
        from_attributes = True

# Pydantic Models - Invitations
class InvitationResponse(BaseModel):
    id: int
    event: EventSummary
    my_priority: int
    my_status: InviteReplyStatus
    invited_at: Optional[datetime]
    responded_at: Optional[datetime]
    is_current_invitee: bool

    class Config:
        from_attributes = True

class InvitationAction(BaseModel):
    action: str  # "accept" or "decline"

# Auth Utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate JWT token, return current user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)  # Convert string to int
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

# Timeout handler function
def handle_invitation_timeout(event_id: int, invitee_id: int):
    """Called when an invitation times out. Auto-declines and forwards to next priority."""
    db = SessionLocal()
    try:
        print(f"⏰ Timeout triggered for event_id={event_id}, invitee_id={invitee_id}")

        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print(f"❌ Event {event_id} not found")
            return

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

        # TODO: Send push notification to invitee about timeout

        # Find next priority invitee
        next_invitee = db.query(EventInvitee).filter(
            EventInvitee.event_id == event_id,
            EventInvitee.status == InviteReplyStatus.pending
        ).order_by(EventInvitee.priority.asc()).first()

        if next_invitee:
            print(f"📨 Forwarding to next invitee: {next_invitee.invitee_id}")
            next_invitee.status = InviteReplyStatus.invited
            next_invitee.invited_at = datetime.utcnow()
            event.current_invitee_id = next_invitee.invitee_id
            event.status = EventStatus.active
            db.commit()

            # TODO: Send push notification to next invitee

            schedule_invitation_timeout(event_id, next_invitee.invitee_id, event.timeout_minutes)
        else:
            print(f"❌ No more invitees available - cancelling event {event_id}")
            event.status = EventStatus.cancelled
            event.current_invitee_id = None
            db.commit()

            # TODO: Send push notification to creator about cancellation

    except Exception as e:
        print(f"❌ Error in timeout handler: {e}")
        db.rollback()
    finally:
        db.close()

def schedule_invitation_timeout(event_id: int, invitee_id: int, timeout_minutes: int):
    """Schedule a timeout task for the given invitation."""
    run_time = datetime.now() + timedelta(minutes=timeout_minutes)
    job_id = f"event_{event_id}_invitee_{invitee_id}"

    print(f"⏰ Scheduling timeout for event {event_id}, invitee {invitee_id} at {run_time}")

    scheduler.add_job(
        func=handle_invitation_timeout,
        trigger=DateTrigger(run_date=run_time),
        args=[event_id, invitee_id],
        id=job_id,
        replace_existing=True
    )

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    print("🚀 Scheduler started")
    yield
    scheduler.shutdown()
    print("🛑 Scheduler stopped")

app = FastAPI(
    title="Bounce API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Bounce API is running"}

# ==================== AUTH ENDPOINTS ====================

@app.post("/api/v1/auth/register", response_model=Token, status_code=201)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account"""

    # Check if username exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )

    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Create user
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Generate token (sub must be string per JWT spec)
    access_token = create_access_token(data={"sub": str(db_user.id)})

    print(f"✅ New user registered: {db_user.username}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": db_user
    }

@app.post("/api/v1/auth/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and get JWT token"""

    # Find user
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )

    # Generate token (sub must be string per JWT spec)
    access_token = create_access_token(data={"sub": str(user.id)})

    print(f"✅ User logged in: {user.username}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.post("/api/v1/auth/device-token")
async def update_device_token(
    device_data: DeviceTokenUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's device token for push notifications (APNs)"""

    current_user.device_token = device_data.device_token
    db.commit()

    print(f"📱 Device token updated for user: {current_user.username}")

    return {"message": "Device token updated successfully"}

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's information"""
    return current_user

# ==================== EVENT ENDPOINTS ====================

@app.post("/api/v1/events", response_model=EventResponse, status_code=201)
async def create_event(
    event: EventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new event (authenticated users only)"""

    # Create event (creator = authenticated user)
    db_event = Event(
        title=event.title,
        creator_id=current_user.id,
        status=EventStatus.pending,
        timeout_minutes=event.timeout_minutes
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Add invitees
    for invitee in event.invitees:
        user = db.query(User).filter(User.username == invitee.user_name).first()
        if not user:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Invitee '{invitee.user_name}' not found"
            )

        db_invitee = EventInvitee(
            event_id=db_event.id,
            invitee_id=user.id,
            priority=invitee.priority
        )
        db.add(db_invitee)

    db.commit()

    # Activate first priority invitee
    first_invitee = db.query(EventInvitee).filter(
        EventInvitee.event_id == db_event.id
    ).order_by(EventInvitee.priority.asc()).first()

    if first_invitee:
        first_invitee.status = InviteReplyStatus.invited
        first_invitee.invited_at = datetime.utcnow()
        db_event.current_invitee_id = first_invitee.invitee_id
        db_event.status = EventStatus.active
        db.commit()

        # Schedule timeout
        schedule_invitation_timeout(db_event.id, first_invitee.invitee_id, db_event.timeout_minutes)

        # TODO: Send push notification to first invitee

    db.refresh(db_event)
    print(f"📅 Event created: {db_event.title} by {current_user.username}")

    return db_event

@app.get("/api/v1/events/my-events", response_model=List[EventResponse])
async def get_my_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all events created by the authenticated user"""

    events = db.query(Event).filter(Event.creator_id == current_user.id).all()
    return events

@app.get("/api/v1/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get event details"""

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check authorization: only creator or invitees can view
    is_creator = event.creator_id == current_user.id
    is_invitee = db.query(EventInvitee).filter(
        EventInvitee.event_id == event_id,
        EventInvitee.invitee_id == current_user.id
    ).first() is not None

    if not (is_creator or is_invitee):
        raise HTTPException(status_code=403, detail="Not authorized to view this event")

    return event

@app.delete("/api/v1/events/{event_id}")
async def cancel_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel an event (creator only)"""

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Only creator can cancel
    if event.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can cancel this event")

    event.status = EventStatus.cancelled
    event.current_invitee_id = None
    db.commit()

    # Cancel scheduled timeout
    try:
        if event.current_invitee_id:
            job_id = f"event_{event_id}_invitee_{event.current_invitee_id}"
            scheduler.remove_job(job_id)
    except:
        pass

    print(f"❌ Event cancelled: {event.title}")

    return {"message": "Event cancelled successfully"}

# ==================== INVITATION ENDPOINTS ====================

@app.get("/api/v1/invitations/pending", response_model=List[InvitationResponse])
async def get_pending_invitations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all pending invitations for the authenticated user"""

    invitations = db.query(EventInvitee).filter(
        EventInvitee.invitee_id == current_user.id
    ).join(Event).filter(
        Event.current_invitee_id == current_user.id,
        Event.status == EventStatus.active
    ).all()

    result = []
    for inv in invitations:
        result.append(InvitationResponse(
            id=inv.id,
            event=inv.event,
            my_priority=inv.priority,
            my_status=inv.status,
            invited_at=inv.invited_at,
            responded_at=inv.responded_at,
            is_current_invitee=True
        ))

    return result

@app.get("/api/v1/invitations/history", response_model=List[InvitationResponse])
async def get_invitation_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get invitation history for the authenticated user"""

    invitations = db.query(EventInvitee).filter(
        EventInvitee.invitee_id == current_user.id,
        EventInvitee.status != InviteReplyStatus.pending
    ).join(Event).all()

    result = []
    for inv in invitations:
        # Skip if still current invitee (that's in pending)
        if inv.event.current_invitee_id == current_user.id and inv.event.status == EventStatus.active:
            continue

        result.append(InvitationResponse(
            id=inv.id,
            event=inv.event,
            my_priority=inv.priority,
            my_status=inv.status,
            invited_at=inv.invited_at,
            responded_at=inv.responded_at,
            is_current_invitee=False
        ))

    return result

@app.post("/api/v1/invitations/{invitation_id}/accept")
async def accept_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept an invitation"""

    invitation = db.query(EventInvitee).filter(EventInvitee.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Check authorization: only the invitee can respond
    if invitation.invitee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only respond to your own invitations")

    # Check if it's their turn
    event = invitation.event
    if event.current_invitee_id != current_user.id:
        raise HTTPException(status_code=400, detail="It's not your turn yet")

    # Accept invitation
    invitation.status = InviteReplyStatus.accepted
    invitation.responded_at = datetime.utcnow()
    event.status = EventStatus.accepted
    db.commit()

    # Cancel timeout
    try:
        job_id = f"event_{event.id}_invitee_{current_user.id}"
        scheduler.remove_job(job_id)
        print(f"✅ Cancelled timeout job {job_id}")
    except:
        pass

    # TODO: Send push notification to creator

    print(f"✅ {current_user.username} accepted invitation to: {event.title}")

    return {"message": "Invitation accepted successfully"}

@app.post("/api/v1/invitations/{invitation_id}/decline")
async def decline_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Decline an invitation"""

    invitation = db.query(EventInvitee).filter(EventInvitee.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Check authorization
    if invitation.invitee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only respond to your own invitations")

    # Check if it's their turn
    event = invitation.event
    if event.current_invitee_id != current_user.id:
        raise HTTPException(status_code=400, detail="It's not your turn yet")

    # Decline invitation
    invitation.status = InviteReplyStatus.declined
    invitation.responded_at = datetime.utcnow()
    db.commit()

    # Cancel timeout
    try:
        job_id = f"event_{event.id}_invitee_{current_user.id}"
        scheduler.remove_job(job_id)
        print(f"✅ Cancelled timeout job {job_id}")
    except:
        pass

    # Find next invitee
    next_invitee = db.query(EventInvitee).filter(
        EventInvitee.event_id == event.id,
        EventInvitee.status == InviteReplyStatus.pending
    ).order_by(EventInvitee.priority.asc()).first()

    if next_invitee:
        next_invitee.status = InviteReplyStatus.invited
        next_invitee.invited_at = datetime.utcnow()
        event.current_invitee_id = next_invitee.invitee_id
        event.status = EventStatus.active
        db.commit()

        schedule_invitation_timeout(event.id, next_invitee.invitee_id, event.timeout_minutes)

        # TODO: Send push notification to next invitee

        print(f"📨 {current_user.username} declined, forwarded to invitee {next_invitee.invitee_id}")
        return {"message": "Declined - invitation forwarded to next priority"}
    else:
        event.status = EventStatus.cancelled
        event.current_invitee_id = None
        db.commit()

        # TODO: Send push notification to creator

        print(f"❌ {current_user.username} declined, no more invitees - event cancelled")
        return {"message": "Declined - no more priorities available, event cancelled"}

# ==================== DEBUG/TESTING ENDPOINTS (Remove in production) ====================

@app.get("/debug/users")
async def debug_users(db: Session = Depends(get_db)):
    """Debug: View all users"""
    users = db.query(User).all()
    return users

@app.get("/debug/events")
async def debug_events(db: Session = Depends(get_db)):
    """Debug: View all events"""
    events = db.query(Event).all()
    return events

@app.get("/debug/event-invitees")
async def debug_event_invitees(db: Session = Depends(get_db)):
    """Debug: View all event invitees"""
    invitees = db.query(EventInvitee).all()
    return invitees

@app.post("/debug/clear-all-data")
async def clear_all_data(db: Session = Depends(get_db)):
    """Debug: Clear all data (DANGEROUS!)"""
    try:
        db.query(EventInvitee).delete()
        db.query(Event).delete()
        db.query(User).delete()
        db.commit()
        return {"message": "All data cleared"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")

# ==================== LEGACY ENDPOINTS (For web testing) ====================

@app.post("/events", response_model=EventResponse, status_code=201)
async def create_event_legacy(event: EventCreate, db: Session = Depends(get_db)):
    """LEGACY: Create event without auth (for web testing only)"""
    # This is a simplified version for web testing - uses first user as creator
    creator = db.query(User).first()
    if not creator:
        raise HTTPException(status_code=400, detail="No users found. Create a user first.")

    db_event = Event(
        title=event.title,
        creator_id=creator.id,
        status=EventStatus.pending,
        timeout_minutes=event.timeout_minutes
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    for invitee in event.invitees:
        user = db.query(User).filter(User.username == invitee.user_name).first()
        if not user:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Invitee '{invitee.user_name}' not found")

        db_invitee = EventInvitee(
            event_id=db_event.id,
            invitee_id=user.id,
            priority=invitee.priority
        )
        db.add(db_invitee)

    db.commit()

    first_invitee = db.query(EventInvitee).filter(
        EventInvitee.event_id == db_event.id
    ).order_by(EventInvitee.priority.asc()).first()

    if first_invitee:
        first_invitee.status = InviteReplyStatus.invited
        first_invitee.invited_at = datetime.utcnow()
        db_event.current_invitee_id = first_invitee.invitee_id
        db_event.status = EventStatus.active
        db.commit()
        schedule_invitation_timeout(db_event.id, first_invitee.invitee_id, db_event.timeout_minutes)

    db.refresh(db_event)
    return db_event

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user_legacy(user: UserRegister, db: Session = Depends(get_db)):
    """LEGACY: Create user without auth (for web testing)"""
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password),
        full_name=user.full_name
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

@app.get("/users")
async def get_users_legacy(db: Session = Depends(get_db)):
    """LEGACY: Get all users (for web testing)"""
    users = db.query(User).all()
    return users

@app.get("/users/{username}")
async def get_user_by_username(username: str, db: Session = Depends(get_db)):
    """LEGACY: Get user by username (for web testing)"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return user
