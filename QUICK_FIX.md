# 🚀 QUICK FIX - Open Phase 2 in Browser NOW

## ⚡ IMMEDIATE ACTION

### Step 1: Open New Terminal in VS Code

Press: **`Ctrl + ~`** (backtick/tilde key)

Or: **View → Terminal**

### Step 2: Run This Command

Copy-paste this entire command and press Enter:

```bash
cd ~/Downloads/ai-cms && source .venv/bin/activate && python manage.py runserver localhost:8000
```

**You should see output like:**
```
Django version 5.2.17, using settings 'config.settings.dev'
Starting development server at http://127.0.0.1:8000/
```

### Step 3: Open Browser

**Open a new browser tab and go to:**

```
http://localhost:8000/admin/
```

---

## 🔐 Login

| Field | Value |
|-------|-------|
| **Username** | `admin` |
| **Password** | `admin123` |

---

## ✅ What You'll See

1. **Login page** → Enter credentials above
2. **Dashboard** → Wagtail admin interface
3. **Left sidebar** → Pages, Settings, Images, etc.
4. **Pages section** → HomePage, Features Demo, Free Trial

---

## 🆘 If Still Not Working

**Try these URLs in order:**

1. `http://localhost:8000/admin/` ← Try this FIRST
2. `http://127.0.0.1:8000/admin/` ← Try this second
3. `http://localhost:8001/admin/` ← If port 8000 blocked, use:

For URL #3, also run server on port 8001:
```bash
python manage.py runserver localhost:8001
```

---

## 🔄 Server Already Running?

**Close it first:**

Press **`Ctrl + C`** in the terminal running the server

**Then start fresh:**
```bash
cd ~/Downloads/ai-cms && source .venv/bin/activate && python manage.py runserver localhost:8000
```

---

## 📍 Server Must Be Running

- ✅ Server terminal should show: `Starting development server at...`
- ✅ Should NOT show errors
- ✅ Keep terminal open while using the app
- ✅ If you close terminal, the server stops

---

## 💡 Pro Tips

- **Don't close the terminal** running the server
- **Use `localhost`, not `127.0.0.1`** in browser URL
- **Include `/admin/`** at the end of URL
- **If stuck, try port 8001** instead

---

## 🎯 Expected Result

### When Server is Running:
```
Performing system checks...
System check identified no issues (0 silenced).
August 24, 2026 - XX:XX:XX
Django version 5.2.17, using settings 'config.settings.dev'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### When You Visit URL:
1. ✅ Wagtail login page loads
2. ✅ You can see username/password input fields
3. ✅ Login button is visible
4. ✅ No error messages

### After Login:
1. ✅ Dashboard loads
2. ✅ Left sidebar visible with "Pages"
3. ✅ Can see page tree with Home, Features Demo
4. ✅ Can edit pages and add blocks

---

## 🆔 Admin Credentials (Confirmed)

These are definitely set up:
```
Username: admin
Password: admin123
Email: admin@example.com
```

If login fails, create new one:
```bash
python manage.py createsuperuser
```

---

**That's it! Try now:** 👉 http://localhost:8000/admin/

If you're still having issues after trying all these steps, share what error message you see in the browser.
