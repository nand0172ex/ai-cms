# 🚀 Phase 2 - Localhost Configuration & Access Guide

**Date:** August 24, 2026  
**Status:** ✅ READY FOR BROWSER ACCESS

---

## 🌐 Access URLs

### Admin Interface
**URL:** http://localhost:8000/admin/

**Login Credentials:**
- **Username:** `admin`
- **Password:** `admin123`

### Wagtail CMS Dashboard
After login: http://localhost:8000/cms/

---

## ✅ Server Configuration

### Current Settings
```
✅ Server: Running on http://127.0.0.1:8000
✅ Django Settings Module: config.settings.dev
✅ DEBUG Mode: True
✅ ALLOWED_HOSTS: localhost, 127.0.0.1, 0.0.0.0
✅ Database: SQLite (db.sqlite3)
✅ System Checks: 0 errors
✅ Superuser: admin/admin123
```

### Environment File
Updated `.env` file with:
- Correct DJANGO_SETTINGS_MODULE (config.settings.dev)
- ALLOWED_HOSTS configured for localhost
- DEBUG enabled for development
- SQLite database enabled

---

## 📋 Phase 2 Features to Test

### 1. ✅ Page Types (6 Available)
After login, go to **Pages** section:

- **HomePage**: Site landing page with hero section
- **StandardPage**: General content with all 16 blocks
- **LandingPage**: Marketing pages with conversion focus
- **AIAssistantPage**: Chat interface placeholder
- **KnowledgeBasePage**: Knowledge base display
- **Search Page**: Default Wagtail search

### 2. ✅ StreamField Blocks (16 Types)
Available when editing StandardPage or LandingPage:

**Text Blocks:**
- Heading Block (h1-h4 with alignment)
- Rich Text Block (WYSIWYG editor)
- Quote Block (with attribution)

**Image Blocks:**
- Image Block (with caption)
- Image + Text Block (side-by-side)
- Hero Block (full-width banner)

**Interactive Blocks:**
- CTA Block (call-to-action button)
- Cards Block (grid layout)
- Accordion Block (collapsible)
- Tabs Block (tabbed interface)

**Code & Media:**
- Code Block (syntax highlighting)
- Video Block (YouTube/Vimeo)
- Custom HTML Block
- AI Prompt Block (Phase 8)

### 3. ✅ Branding Settings
Go to: **Settings ⚙️** → **Branding Settings**

Configure:
- Site name and tagline
- Logo and favicon
- Color scheme (primary, secondary, accent)
- Typography (fonts for headings, body, code)
- Social media links
- Contact information
- Footer copyright text

### 4. ✅ Navigation Management
Go to: **Django Admin** → **Navigation** → **Menus**

Create menus with:
- Hierarchical menu items
- Link to Wagtail pages
- External URLs
- Custom URLs
- Icons and styling

---

## 🧪 Step-by-Step Testing

### Test 1: Create a Test Page

1. Login: http://localhost:8000/admin/
2. Click **Pages** in left sidebar
3. Click **Add page** → Select **HomePage**
4. Fill in:
   - **Title:** "AI CMS Demo"
   - **Hero Title:** "Welcome to Phase 2"
   - **Hero Subtitle:** "Sophisticated Page Building System"
   - **Hero Image:** Upload an image
5. Click **Save Draft**
6. Click **Publish**

### Test 2: Add StreamField Blocks

1. Create new **StandardPage** under HomePage
   - **Title:** "Features & Blocks Demo"
2. In **Body** field, add blocks:

```
Block 1: Heading Block
- Level: h2
- Text: "Our Features"
- Alignment: center

Block 2: Rich Text Block
- Text: "This page demonstrates all Phase 2 StreamField blocks"

Block 3: Image Block
- Upload image
- Caption: "Example feature image"
- Alt text: "Feature demo"

Block 4: Cards Block
- Add 3 cards with titles and descriptions
- Columns: 3

Block 5: Accordion Block
- Add 2 items with questions and answers

Block 6: CTA Block
- Heading: "Ready to get started?"
- Button text: "Start Free Trial"
- Button URL: https://example.com
- Style: primary
```

3. Click **Publish**
4. Click **View Live** to see rendered page

### Test 3: Update Branding Settings

1. Click **Settings** ⚙️ (top right)
2. Select **Branding Settings**
3. Update:
   - Site Name: "My AI CMS"
   - Primary Color: #007bff (Blue)
   - Secondary Color: #6c757d (Gray)
4. Upload a logo
5. Add social links
6. Click **Save**

### Test 4: Create Navigation Menu

1. Go to Django Admin: http://localhost:8000/admin/
2. Click **Navigation** → **Menus**
3. Click **Add Menu**
4. Fill in:
   - **Name:** Main Menu
   - **Max Depth:** 3
5. In menu items section, add:
   - Home (link to HomePage)
   - Features (link to StandardPage)
   - About (External URL)
6. Click **Save**

---

## 📺 What You Should See

### Admin Dashboard
```
✅ Pages Tree with all 6 page types
✅ Wagtail admin interface with sidebar
✅ Edit page with StreamField blocks
✅ Image library and media management
✅ Settings and configuration options
```

### Page Editing
```
✅ Block selector showing 16 blocks
✅ WYSIWYG editor for text blocks
✅ Image upload and selection
✅ Block ordering and nesting
✅ Preview button to see live page
```

### Branding Settings
```
✅ Color picker for brand colors
✅ Logo upload with preview
✅ Font selection dropdowns
✅ Social link input fields
✅ All settings persistent in database
```

### Navigation Management
```
✅ Menu creation and editing
✅ Menu item hierarchy (parent/child)
✅ Link type selector (page/external/custom)
✅ Drag-and-drop ordering
✅ Status toggles (enabled/disabled)
```

---

## 🔧 Troubleshooting

### Issue: "Connection Refused"
**Solution:** Ensure server is running:
```bash
cd ~/Downloads/ai-cms
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000
```

### Issue: "Page Not Found" (404)
**Solution:** Make sure you're using correct URL:
- Admin: http://localhost:8000/admin/
- Home: http://localhost:8000/

### Issue: "ALLOWED_HOSTS" error
**Solution:** Already fixed in `.env` file. Server should be running correctly.

### Issue: Login not working
**Solution:** Create superuser again:
```bash
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: admin123
```

### Issue: Images not loading
**Solution:** Run collectstatic:
```bash
python manage.py collectstatic --noinput
```

---

## 📝 Database Status

```bash
# Check migrations
python manage.py showmigrations

# Verify page types exist
python manage.py shell
>>> from home.models import HomePage, StandardPage
>>> HomePage.objects.all()
```

**Current Database:**
- ✅ SQLite: `db.sqlite3`
- ✅ All Phase 2 migrations applied
- ✅ Superuser created
- ✅ Ready for page creation

---

## 🎯 Next Steps

### After Testing Phase 2:
1. ✅ Create sample pages with all block types
2. ✅ Test branding configuration
3. ✅ Create multiple menus
4. ✅ Verify block rendering on live pages
5. ✅ Test admin interface usability

### Prepare for Phase 3:
- Knowledge base ingestion
- Document processing
- RAG integration
- Full-text search

---

## 📞 Quick Command Reference

```bash
# Start server
python manage.py runserver 127.0.0.1:8000

# Create superuser
python manage.py createsuperuser

# Check system
python manage.py check

# View logs
tail -f logs/django.log

# Access shell
python manage.py shell

# Collect static files
python manage.py collectstatic --noinput
```

---

## ✨ Summary

| Component | Status | URL |
|-----------|--------|-----|
| Django Server | ✅ Running | http://localhost:8000 |
| Admin Interface | ✅ Ready | http://localhost:8000/admin/ |
| Wagtail CMS | ✅ Configured | After login |
| Page Types | ✅ 6 Available | Pages section |
| Block System | ✅ 16 Blocks | In page editor |
| Branding | ✅ Configured | Settings menu |
| Navigation | ✅ Ready | Django Admin |
| Database | ✅ SQLite | db.sqlite3 |
| Superuser | ✅ admin/admin123 | Ready |

---

**Phase 2 is now fully accessible at:** 🎉

### 👉 **http://localhost:8000/admin/**

**Login with:**
- Username: `admin`
- Password: `admin123`

---

*Configuration completed: August 24, 2026*  
*Ready for browser testing and Phase 3 implementation*
