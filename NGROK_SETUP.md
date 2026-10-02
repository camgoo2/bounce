# 🚇 Ngrok Setup for iOS Development

## What is Ngrok?

Ngrok creates a **secure tunnel** from the internet to your local server, giving you a public URL like `https://abc123.ngrok.io` that you can use to test your iOS app.

**Perfect for:**
- Testing iOS app on your Mac while backend runs on this server
- No need to deploy to production
- Free tier available
- Instant HTTPS

---

## 📋 Setup Instructions

### Step 1: Sign Up for Ngrok

1. Go to https://ngrok.com
2. Click "Sign Up" (free account)
3. Verify your email
4. Go to dashboard: https://dashboard.ngrok.com/get-started/your-authtoken
5. **Copy your authtoken** (looks like: `2abc...xyz123`)

---

### Step 2: Install Ngrok on Server

```bash
# Method 1: Using snap (easiest)
sudo snap install ngrok

# Method 2: Using apt
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update
sudo apt install ngrok

# Method 3: Direct download
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

---

### Step 3: Add Your Authtoken

```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

---

### Step 4: Start Backend & Ngrok

#### Terminal 1: Start Backend
```bash
cd ~/personal_projects/bounce/backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Terminal 2: Start Ngrok Tunnel
```bash
ngrok http 8000
```

You'll see output like:
```
Session Status                online
Account                       Your Name (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok.io -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Your public URL is:** `https://abc123.ngrok.io`

---

## 📱 Use in iOS App

### Swift Code Example

```swift
// In your API service file
class APIService {
    // UPDATE THIS URL when ngrok restarts
    static let baseURL = "https://abc123.ngrok.io"
    
    func register(username: String, email: String, password: String, fullName: String) async throws -> AuthResponse {
        let url = URL(string: "\(APIService.baseURL)/api/v1/auth/register")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "username": username,
            "email": email,
            "password": password,
            "full_name": fullName
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(AuthResponse.self, from: data)
    }
}
```

---

## 🧪 Test the Connection

### From Your Mac Terminal:

```bash
# Test health endpoint
curl https://abc123.ngrok.io/health

# Should return:
# {"status":"ok","message":"Bounce API is running"}

# Test registration
curl -X POST https://abc123.ngrok.io/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "iostest",
    "email": "iostest@example.com",
    "password": "password123",
    "full_name": "iOS Test"
  }'
```

---

## 📊 Ngrok Web Interface

Ngrok provides a **local web interface** to monitor requests:

**Open in browser:** http://127.0.0.1:4040

You'll see:
- All HTTP requests
- Request/response details
- Timing information
- Perfect for debugging!

---

## ⚠️ Free Tier Limitations

| Feature | Free | Paid ($8/month) |
|---------|------|-----------------|
| URL Changes | ✅ Every restart | ❌ Fixed subdomain |
| Session Duration | ⚠️ 2 hours | ✅ Unlimited |
| HTTPS | ✅ Yes | ✅ Yes |
| Request Limits | ⚠️ 40 req/min | ✅ Unlimited |
| Custom Domain | ❌ No | ✅ Yes |

**For development:** Free tier is perfect!

---

## 🔄 Daily Workflow

### Morning (Start Development):

```bash
# Terminal 1: Backend
cd ~/personal_projects/bounce/backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Ngrok
ngrok http 8000

# Copy the https://xxx.ngrok.io URL
# Update in iOS app if it changed
```

### Evening (End Development):

```bash
# Ctrl+C in both terminals to stop
```

---

## 💡 Pro Tips

### 1. Keep Ngrok Running

Use `tmux` or `screen` to keep sessions alive:

```bash
# Install tmux
sudo apt install tmux

# Start tmux session
tmux new -s bounce

# Terminal 1 (Ctrl+B, C to create new pane)
cd ~/personal_projects/bounce/backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 (Ctrl+B, C)
ngrok http 8000

# Detach: Ctrl+B, D
# Reattach: tmux attach -t bounce
```

### 2. Save Ngrok URL

```bash
# Save current ngrok URL to file
curl http://localhost:4040/api/tunnels | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" \
  > current_ngrok_url.txt

# Read it
cat current_ngrok_url.txt
```

### 3. Environment Config in iOS

```swift
// Config.swift
enum Environment {
    static let apiBaseURL: String = {
        #if DEBUG
        // Paste your ngrok URL here when it changes
        return "https://abc123.ngrok.io"
        #else
        return "https://api.yourdomain.com"
        #endif
    }()
}
```

---

## 🆘 Troubleshooting

### "Failed to complete tunnel connection"
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill if needed
kill -9 <PID>
```

### "Invalid authtoken"
```bash
# Re-add your token
ngrok config add-authtoken YOUR_TOKEN_HERE
```

### "Session expired"
- Free tier sessions expire after 2 hours
- Just restart ngrok: `ngrok http 8000`
- URL will change (update in iOS app)

### "Too many connections"
- Free tier: 40 requests/minute
- For testing, this should be plenty
- If needed, upgrade to paid tier

---

## 🎯 Quick Reference

```bash
# Start everything
cd ~/personal_projects/bounce/backend
uvicorn main:app --host 0.0.0.0 --port 8000 &
ngrok http 8000

# Check ngrok URL
curl http://localhost:4040/api/tunnels

# Stop everything
pkill -f uvicorn
pkill -f ngrok
```

---

## 📱 Ready for iOS Development

Once ngrok is running, you can:
1. Use the `https://xxx.ngrok.io` URL in your iOS app
2. Test on your Mac (different computer)
3. Test on real iPhone devices
4. Debug requests in ngrok web interface (http://localhost:4040)

**All your API endpoints work the same:**
- `POST https://xxx.ngrok.io/api/v1/auth/register`
- `POST https://xxx.ngrok.io/api/v1/auth/login`
- `POST https://xxx.ngrok.io/api/v1/events`
- etc.

---

## 🚀 Tomorrow's Plan

1. Install & configure ngrok
2. Get public URL
3. Test from your Mac
4. Start iOS app development!

See you tomorrow! 🎉
