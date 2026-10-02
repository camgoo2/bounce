#!/bin/bash

API_BASE="http://localhost:8000"

echo "🧪 Testing Bounce API v1"
echo "========================"
echo ""

echo "1️⃣  Registering new user..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "secure123",
    "full_name": "Test User"
  }')

echo "$REGISTER_RESPONSE" | python3 -m json.tool
TOKEN=$(echo "$REGISTER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Registration failed or user already exists"
  echo ""
  echo "2️⃣  Logging in instead..."
  LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{
      "username": "testuser",
      "password": "secure123"
    }')

  echo "$LOGIN_RESPONSE" | python3 -m json.tool
  TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
fi

echo ""
echo "🔑 JWT Token obtained: ${TOKEN:0:50}..."
echo ""

echo "3️⃣  Getting current user info..."
curl -s -X GET "$API_BASE/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "4️⃣  Creating event (authenticated)..."
curl -s -X POST "$API_BASE/api/v1/events" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Coffee tomorrow 10am at Starbucks, who is in?",
    "timeout_minutes": 15,
    "invitees": [
      {"user_name": "paul", "priority": 1},
      {"user_name": "sarah", "priority": 2}
    ]
  }' | python3 -m json.tool
echo ""

echo "5️⃣  Getting my events..."
curl -s -X GET "$API_BASE/api/v1/events/my-events" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "✅ API test complete!"
echo ""
echo "📝 Note: To test invitation endpoints, you'd need to:"
echo "   - Register as 'paul' or 'sarah'"
echo "   - Login to get their token"
echo "   - Use GET /api/v1/invitations/pending to see invitations"
echo "   - Use POST /api/v1/invitations/{id}/accept or /decline to respond"
