# Bounce Web App

Simple web interface to create events with priority-based invitations.

## How to Use

### 1. Start the Backend Server

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Open the Web App

Simply open `index.html` in your web browser:
- **Option A**: Double-click `index.html`
- **Option B**: Right-click → Open with → Chrome/Firefox/Safari
- **Option C**: Drag and drop into your browser

### 3. Create Users First

Before creating events, you need to create users via the API:

```bash
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{"username": "cameron", "full_name": "Cameron Goodhue"}'

curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{"username": "paul", "full_name": "Paul Smith"}'

curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{"username": "sarah", "full_name": "Sarah Johnson"}'
```

### 4. Create an Event

1. Fill in your username (e.g., "cameron")
2. Add the event message (e.g., "Golf Saturday 3:00pm, Beverley Park Golf course, whose keen")
3. Set timeout in minutes (default: 15)
4. Add invitees with their usernames and priorities
5. Click "Create Event"

## Features

- **Simple Form**: Easy-to-use interface for creating events
- **Priority Management**: Add multiple invitees with priority order
- **Timeout Configuration**: Set how long each person has to respond
- **Real-time Feedback**: See success/error messages instantly

## API Endpoints

The backend runs on `http://localhost:8000`

View API docs at: http://localhost:8000/docs
