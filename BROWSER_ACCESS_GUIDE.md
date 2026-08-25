# 🔧 Phase 2 Troubleshooting Guide

**Issue:** Application not opening in browser (frontend and admin)

---

## ✅ Current Server Status

**Server Process:** RUNNING ✅
```
PID: Multiple Python processes running manage.py runserver
Port: 127.0.0.1:8000
Status: Listening on http://127.0.0.1:8000
```

---

## 🔍 Troubleshooting Steps

### Step 1: Verify Server is Running

```bash
# Check if server process is active
ps aux | grep "manage.py runserver"

# Expected output:
# python manage.py runserver 127.0.0.1:8000
# (Running in background)
```

✅ **Status:** Server IS running

---

### Step 2: Correct URLs to Access

**IMPORTANT:** Your browser needs to use the correct hostname and port.

| Component | URL | Status |
|-----------|-----|--------|
| **Admin Login** | http://localhost:8000/admin/ | 🟢 Ready |
| **Home Page** | http://localhost:8000/ | 🟢 Ready |
| **Wagtail CMS** | http://localhost:8000/cms/ | 🟢 Ready |
| **DO NOT USE** | http://127.0.0.1:8000 | ❌ May fail in browser |

---

### Step 3: Browser Access Instructions

#### **For Chrome/Firefox/Edge:**

1. **Open new tab** in your browser
2. **Type this URL** in address bar:
   ```
   http://localhost:8000/admin/
   ```
   
3. **Press Enter**

4. **You should see:** Wagtail admin login page

5. **Login with:**
   - Username: `admin`
   - Password: `admin123`

---

### Step 4: If Still Not Working

#### **Option A: Restart Server (Clean)**

```bash
# Kill any running server processes
pkill -f "manage.py runserver"

# Wait 2 seconds
sleep 2

# Start fresh server
cd ~/Downloads/ai-cms
source .venv/bin/activate
python manage.py runserver localhost:8000
```

Then try: http://localhost:8000/admin/

---

#### **Option B: Use Different Port**

If port 8000 is blocked, try port 8001:

```bash
cd ~/Downloads/ai-cms
source .venv/bin/activate
python manage.py runserver localhost:8001
```

Then access: http://localhost:8001/admin/

---

#### **Option C: Full Diagnostic Check**

Run this complete verification:

```bash
cd ~/Downloads/ai-cms
source .venv/bin/activate

# 1. System check
echo "1️⃣ Checking Django..."
python manage.py check

# 2. Database check
echo "2️⃣ Checking Database..."
python manage.py showmigrations | head -20

# 3. Verify admin user exists
echo "3️⃣ Checking admin user..."
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
admin = User.objects.filter(username='admin').first()
if admin:
    print(f"✅ Admin user exists: {admin.email}")
else:
    print("❌ Admin user not found - creating...")
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ Admin user created")
EOF

# 4. Start server
echo "4️⃣ Starting server..."
python manage.py runserver localhost:8000
```

---

## 🌐 Browser Compatibility

✅ **Works on:**
- Google Chrome/Chromium
- Mozilla Firefox
- Microsoft Edge
- Safari
- Any modern browser

✅ **Required:**
- JavaScript enabled
- Cookies enabled
- Localhost must be trusted

---

## 🔐 If You See "Connection Refused"

This means the browser can't reach the server. Try:

1. **Check server is running:**
   ```bash
   ps aux | grep runserver
   ```
   Should show Python process with `manage.py runserver`

2. **Check correct URL format:**
   ```
   ✅ CORRECT: http://localhost:8000/admin/
   ✅ ALSO OK: http://127.0.0.1:8000/admin/
   ❌ WRONG: http://0.0.0.0:8000/admin/ (this won't work in browser)
   ```

3. **Verify port 8000 is available:**
   ```bash
   # Kill anything using port 8000
   lsof -ti:8000 | xargs kill -9 2>/dev/null || true
   
   # Restart server
   python manage.py runserver localhost:8000
   ```

---

## 🔑 Login Credentials

**If you get to the login page:**

```
Username: admin
Password: admin123
Email: admin@example.com
```

**If login fails:** Create new superuser
```bash
python manage.py createsuperuser
# Follow prompts to create admin account
```

---

## 📋 Expected Pages After Login

### Dashboard View
```
✅ Left Sidebar:
   - Pages (with page tree)
   - Images
   - Documents
   - Settings ⚙️
   - Users
   - Groups
   - Search

✅ Main Area:
   - Welcome message
   - Recent pages
   - Quick actions
```

### Pages Section
```
✅ Should see:
   - Home (HomePage)
   - Features & Blocks Demo (StandardPage)
   - Free Trial (LandingPage) [if created]
   
✅ Can:
   - Click to edit pages
   - Add new pages
   - View in different languages
   - Publish/unpublish
```

---

## 🆘 Common Issues & Fixes

### Issue 1: "Hmm, can't reach this page"
**Cause:** Server not running or wrong URL  
**Fix:**
```bash
# Verify server is running
ps aux | grep runserver

# If not running, start it:
python manage.py runserver localhost:8000

# Then try: http://localhost:8000/admin/
```

### Issue 2: "This site can't be reached - Connection refused"
**Cause:** Port 8000 might be in use  
**Fix:**
```bash
# Try different port
python manage.py runserver localhost:8001

# Access: http://localhost:8001/admin/
```

### Issue 3: "Bad Request (400) - Invalid HTTP_HOST header"
**Cause:** ALLOWED_HOSTS not configured correctly  
**Fix:** Already fixed in `.env` file. Make sure you're using:
- ✅ http://localhost:8000
- NOT http://0.0.0.0:8000
- NOT http://[your-ip]:8000

### Issue 4: Login page appears but login fails
**Cause:** Superuser doesn't exist or password is wrong  
**Fix:**
```bash
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com  
# Password: admin123
```

### Issue 5: Page loads but styling is broken
**Cause:** Static files not collected  
**Fix:**
```bash
python manage.py collectstatic --noinput
```

---

## ✨ Quick Start Command

**Copy and run this entire command to get everything working:**

```bash
cd ~/Downloads/ai-cms && \
source .venv/bin/activate && \
echo "Checking system..." && \
python manage.py check && \
echo "Creating admin user if needed..." && \
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ Admin created")
else:
    print("✅ Admin exists")
EOF
echo "Starting server..." && \
python manage.py runserver localhost:8000
```

Then open your browser to: **http://localhost:8000/admin/**

---

## 📞 Server Information

| Setting | Value |
|---------|-------|
| **Host** | localhost or 127.0.0.1 |
| **Port** | 8000 (or try 8001 if blocked) |
| **URL Format** | http://hostname:port/admin/ |
| **Database** | SQLite (db.sqlite3) |
| **Settings Module** | config.settings.dev |
| **Debug Mode** | True (development only) |
| **Static Files** | /static/ |
| **Media Files** | /media/ |

---

## 🎯 Final Checklist

Before giving up, make sure you've:

- [ ] ✅ Server is running (`ps aux | grep runserver`)
- [ ] ✅ Using correct URL: `http://localhost:8000/admin/`
- [ ] ✅ Correct credentials: `admin` / `admin123`
- [ ] ✅ Browser allows localhost connections
- [ ] ✅ JavaScript is enabled in browser
- [ ] ✅ Port 8000 is not blocked by firewall
- [ ] ✅ Django system checks pass: `python manage.py check`

---

## 🚀 Once Everything Works

After you see the Wagtail login page:

1. Login with: admin / admin123
2. Go to **Pages** in sidebar
3. Click **Home** to see the HomePage
4. Click **"Features & Blocks Demo"** to edit page content
5. In **Body** field, click **"Add block"** to add content blocks
6. Try adding: Heading, Image, Cards, Accordion blocks
7. Click **Save** then **Publish**
8. Click **View Live** to see the published page

---

**Still having issues?**

Get more details:
```bash
# View server logs in real-time
tail -f ~/Downloads/ai-cms/logs/django.log

# Or run with full verbose output:
python manage.py runserver localhost:8000 --verbosity=3
```

---

*Last Updated: August 24, 2026*  
*AI CMS Phase 2 - Browser Access Troubleshooting*
