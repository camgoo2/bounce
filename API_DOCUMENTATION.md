# Bounce API Documentation v1.0

## Base URL
```
http://localhost:8000
```

## Authentication

The API uses **JWT (JSON Web Token)** authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

---

## 📌 Auth Endpoints

### Register New User
Create a new user account and receive a JWT token.

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "john",
  "email": "john@example.com",
  "password": "secure123",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "john",
    "email": "john@example.com",
    "full_name": "John Doe",
    "created_at": "2026-10-02T12:00:00"
  }
}
```

---

### Login
Login with username and password to get a JWT token.

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "john",
  "password": "secure123"
}
```

**Response:** Same as register

---

### Get Current User
Get information about the authenticated user.

```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "full_name": "John Doe",
  "created_at": "2026-10-02T12:00:00"
}
```

---

### Update Device Token (for Push Notifications)
Register device token for iOS push notifications (APNs).

```http
POST /api/v1/auth/device-token
Authorization: Bearer <token>
Content-Type: application/json

{
  "device_token": "<apns_device_token>"
}
```

**Response:**
```json
{
  "message": "Device token updated successfully"
}
```

---

## 📅 Event Endpoints

### Create Event
Create a new event with priority-based invitations. **Requires authentication.**

```http
POST /api/v1/events
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Golf Saturday 3:00pm, Beverley Park Golf course, whose keen",
  "timeout_minutes": 15,
  "invitees": [
    {"user_name": "paul", "priority": 1},
    {"user_name": "sarah", "priority": 2},
    {"user_name": "mike", "priority": 3}
  ]
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Golf Saturday 3:00pm...",
  "creator_id": 1,
  "status": "active",
  "current_invitee_id": 2,
  "timeout_minutes": 15,
  "created_at": "2026-10-02T12:00:00",
  "invitees": [
    {
      "invitee_id": 2,
      "priority": 1,
      "status": "invited",
      "invited_at": "2026-10-02T12:00:00",
      "responded_at": null
    },
    {
      "invitee_id": 3,
      "priority": 2,
      "status": "pending",
      "invited_at": null,
      "responded_at": null
    }
  ]
}
```

**Notes:**
- Creator is automatically set to authenticated user
- First priority invitee is automatically invited
- Timeout is scheduled for first invitee

---

### Get My Events
Get all events created by the authenticated user.

```http
GET /api/v1/events/my-events
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": 1,
    "title": "Golf Saturday...",
    "creator_id": 1,
    "status": "active",
    ...
  }
]
```

---

### Get Event Details
Get details of a specific event. Only creator or invitees can view.

```http
GET /api/v1/events/{event_id}
Authorization: Bearer <token>
```

**Response:** Same as create event response

---

### Cancel Event
Cancel an event. **Only the creator can cancel.**

```http
DELETE /api/v1/events/{event_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Event cancelled successfully"
}
```

---

## 📨 Invitation Endpoints

### Get Pending Invitations
Get all pending invitations for the authenticated user (invitations where it's their turn).

```http
GET /api/v1/invitations/pending
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": 1,
    "event": {
      "id": 1,
      "title": "Golf Saturday...",
      "creator_id": 1,
      "status": "active",
      "timeout_minutes": 15,
      "created_at": "2026-10-02T12:00:00"
    },
    "my_priority": 1,
    "my_status": "invited",
    "invited_at": "2026-10-02T12:00:00",
    "responded_at": null,
    "is_current_invitee": true
  }
]
```

---

### Get Invitation History
Get past invitations (accepted, declined, or timed out).

```http
GET /api/v1/invitations/history
Authorization: Bearer <token>
```

**Response:** Same format as pending invitations

---

### Accept Invitation
Accept an invitation. Must be the current invitee.

```http
POST /api/v1/invitations/{invitation_id}/accept
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Invitation accepted successfully"
}
```

**Side Effects:**
- Event status changes to "accepted"
- Timeout is cancelled
- Creator receives push notification (TODO)

---

### Decline Invitation
Decline an invitation. Automatically forwards to next priority person.

```http
POST /api/v1/invitations/{invitation_id}/decline
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Declined - invitation forwarded to next priority"
}
```

**OR** (if no more invitees):
```json
{
  "message": "Declined - no more priorities available, event cancelled"
}
```

**Side Effects:**
- Timeout is cancelled
- Next priority person is invited
- New timeout is scheduled
- Next invitee receives push notification (TODO)

---

## 🔧 Debug Endpoints (Remove in Production)

### View All Users
```http
GET /debug/users
```

### View All Events
```http
GET /debug/events
```

### View All Event Invitees
```http
GET /debug/event-invitees
```

### Clear All Data (DANGEROUS!)
```http
POST /debug/clear-all-data
```

---

## 🔄 Legacy Endpoints (For Web Testing)

These endpoints don't require authentication and are kept for web frontend testing only.

### Create Event (No Auth)
```http
POST /events
Content-Type: application/json

{
  "title": "Event title",
  "timeout_minutes": 15,
  "invitees": [...]
}
```

### Create User (No Auth)
```http
POST /users
Content-Type: application/json

{
  "username": "john",
  "email": "john@example.com",
  "password": "secure123",
  "full_name": "John Doe"
}
```

### Get All Users (No Auth)
```http
GET /users
```

---

## 📱 iOS App Integration

### Registration/Login Flow
1. User signs up or logs in
2. Store `access_token` in Keychain
3. Store `user` data locally if needed
4. Include token in all API requests

### Swift Example
```swift
// Store token
KeychainWrapper.standard.set(token, forKey: "authToken")

// Make authenticated request
var request = URLRequest(url: url)
request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
```

### Push Notifications
1. Get APNs device token from iOS
2. Send to `/api/v1/auth/device-token`
3. Backend will send push notifications when:
   - User is invited
   - Timeout is approaching
   - Event is accepted/cancelled

---

## 🔐 Security Notes

### Production Checklist
- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS only
- [ ] Remove debug endpoints
- [ ] Add rate limiting
- [ ] Implement refresh tokens
- [ ] Add account verification (email)

### Current Security (Development)
- ✅ Password hashing with bcrypt
- ✅ JWT tokens (7-day expiry)
- ✅ Authorization checks on all protected endpoints
- ⚠️ CORS allows all origins (change in production)
- ⚠️ Default SECRET_KEY (change in production)

---

## 📊 Event Status Flow

```
pending → active → accepted ✅
                → cancelled ❌

Transitions:
- pending → active: When first invitee is invited
- active → accepted: When someone accepts
- active → cancelled: When all invitees decline/timeout
```

## 📊 Invitation Status Flow

```
pending → invited → accepted ✅
                  → declined (manual)
                  → declined (timeout)
```

---

## 🐛 Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

Common HTTP Status Codes:
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (not authorized for this action)
- `404` - Not Found
- `422` - Validation Error

---

## 🧪 Testing

See `test_api.sh` for a complete test script.

Run:
```bash
chmod +x test_api.sh
./test_api.sh
```

---

## 📚 API Docs (Swagger)

Interactive API documentation available at:
```
http://localhost:8000/docs
```
