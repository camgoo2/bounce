## 📂 Project Structure

- `backend/`
  - `main.py` - FastAPI backend with SQLAlchemy ORM
- `frontend/`
  - `index.html` - Simple web interface to create events
  - `README.md` - Frontend setup instructions
- Not touching the ios through git, just in XCode
- `iOS/`
  - `Bounce/`
    - `Models/` # Data models
    - `Preview Content/`
    - `Services/` # Networking & API calls
      - `APIService.swift`
    - `Views/` # UI screens
      - `HomeView.swift` #HomeScreen
      - `CreateBounceView.swift`#CreateBounceScreen
    - `BounceApp.swift` # App entry point
  - `BounceTests/`
  - `BounceUITests/`
- `README`

## Local Development  
1.Make a new environment
```conda env create -f env.yaml```
2.Activate the environment
```conda activate bounce```
3.Run poetry commands - this will create a lock file
`poetry config virtualenvs.create false`
`poetry install`



## Running the App

### Backend Server
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://127.0.0.1:8000/docs

### Web Frontend
Simply open `frontend/index.html` in your browser to create events via a web interface.

See `frontend/README.md` for detailed instructions.

### iOS Development (Remote Access)
Use **Ngrok** to expose your backend to the internet for iOS app testing.

See **[NGROK_SETUP.md](NGROK_SETUP.md)** for complete setup instructions.

## Features

- ✅ **Priority-based invitations**: Invite people in order of preference
- ✅ **Automatic timeout**: If someone doesn't respond in time, automatically forward to next person
- ✅ **Cascading invites**: Keep going down the priority list until someone accepts
- ✅ **Simple message**: Just send a text message (stored in event title)
- ✅ **JWT Authentication**: Secure user accounts and API access
- ✅ **Mobile-ready**: Complete REST API for iOS app
- 🔄 **Web + iOS**: Test via web interface, use via iOS app

---

## 📚 Documentation

- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference
- **[PHASE_1_COMPLETE.md](PHASE_1_COMPLETE.md)** - Backend implementation guide
- **[NGROK_SETUP.md](NGROK_SETUP.md)** - Setup guide for iOS development
- **[SESSION_SUMMARY.md](SESSION_SUMMARY.md)** - Latest session summary

---

## 🚀 Quick Start

### For Testing (Web):
1. Start backend: `cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000`
2. Open `frontend/index.html` in browser
3. Create events and test the flow

### For iOS Development:
1. Follow **[NGROK_SETUP.md](NGROK_SETUP.md)**
2. Get public URL from ngrok
3. Use URL in iOS app to connect to backend

---

## ✅ Current Status

**Phase 1: Backend API** - ✅ Complete  
**Phase 2: iOS App** - 🔄 Next  
**Phase 3: Push Notifications** - ⏳ Planned  
**Phase 4: Production Deploy** - ⏳ Planned





