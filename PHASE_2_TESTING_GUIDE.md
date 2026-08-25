# Phase 2 Quick Testing Guide

## Verify Installation

```bash
cd /home/Nandprakash.Goutam1/Downloads/ai-cms
source .venv/bin/activate

# System check
python manage.py check
# Expected: System check identified no issues (0 silenced).

# Create superuser if needed
python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

# Run dev server
python manage.py runserver
```

Then visit: http://localhost:8000/admin/

---

## Test Page Creation

1. **Login to Wagtail Admin** → http://localhost:8000/admin/
2. **Navigate to Pages**
3. **Create New Page**:
   - Click "Add Child Page" on Root
   - Select "HomePage"
   - Fill in: Title (e.g., "Home"), Hero Title, Hero Subtitle, Hero Image
   - Click "Save Draft"

4. **Create StandardPage**:
   - Add Child Page to HomePage → StandardPage
   - Title: "Blog Post Example"
   - In Body field, add blocks:
     - Heading Block (h2): "Introduction"
     - RichText Block: "This is a test post"
     - Image Block: Upload image with caption
     - CTA Block: Add button with link
   - Click "Save Draft" → "Publish"

5. **Preview**:
   - Click "View Live" button
   - Verify blocks render with proper styling

---

## Test Branding Settings

1. **Navigate to Wagtail Admin Settings**:
   - Click "Settings" (gear icon)
   - Select "Branding Settings"

2. **Update Settings**:
   - Site Name: "My AI CMS"
   - Tagline: "Powered by AI"
   - Primary Color: #007bff
   - Logo: Upload image
   - Social Links: Add Twitter/LinkedIn URLs
   - Contact Email: contact@example.com

3. **Verify in Templates**:
   - In any template: `{{ branding.site_name }}`
   - All branding settings available to templates

---

## Test Navigation Menus

1. **Go to Django Admin**: http://localhost:8000/admin/
2. **Create Menu**:
   - Click "Menus" → "Add Menu"
   - Name: "Main Menu"
   - Max Depth: 3
   - Slug: auto-generated

3. **Add Menu Items**:
   - Click "Add another Menu item"
   - Title: "Home"
   - Link Type: "Wagtail Page"
   - Select: Homepage
   - Sort Order: 0

4. **Add Submenu Item**:
   - Create another item
   - Title: "Features"
   - Link Type: "External URL"
   - URL: https://example.com
   - Parent: (blank - top level)

5. **Verify in Templates**:
   - In template: `{{ menus.main }}`
   - Loop through items: `{% for item in menus.main %}`

---

## Test BlockTemplates Rendering

### Create a full-featured page:

```
HomePage
└── StandardPage: "Features Demo"
    ├── HeadingBlock (h1) - "Our Features"
    ├── RichTextBlock - Description text
    ├── CardsBlock:
    │   ├── Card 1: Feature with image
    │   ├── Card 2: Feature with image
    │   └── Card 3: Feature with image
    ├── AccordionBlock:
    │   ├── Item 1: FAQ Question → Answer
    │   └── Item 2: FAQ Question → Answer
    ├── TabsBlock:
    │   ├── Tab 1: "Pro Features"
    │   └── Tab 2: "Standard Features"
    ├── HeroBlock - Banner
    └── CTABlock - "Get Started" button
```

Then verify:
1. All blocks display correctly
2. Accordions expand/collapse
3. Tabs switch content
4. Images load properly
5. Buttons link to correct URLs

---

## API Endpoints (for Phase 3+)

```bash
# Get page as JSON (if REST Framework configured)
curl http://localhost:8000/api/pages/

# Get menus (future implementation)
curl http://localhost:8000/api/menus/

# Get branding settings (future implementation)
curl http://localhost:8000/api/branding/
```

---

## Database Queries for Verification

```python
python manage.py shell

# Check pages
from home.models import HomePage, StandardPage
HomePage.objects.all()
StandardPage.objects.all()

# Check menus
from apps.navigation.models import Menu, MenuItem
Menu.objects.all()
MenuItem.objects.filter(parent__isnull=True)  # Top-level items

# Check branding
from apps.branding.models import BrandingSettings
BrandingSettings.for_request(None)

# Check knowledge bases
from apps.knowledge.models import KnowledgeBase
KnowledgeBase.objects.all()
```

---

## Common Issues & Fixes

### Issue: Templates not found
**Fix**: Ensure `templates/` directory is in TEMPLATES setting in settings/base.py

### Issue: Branding settings not showing in admin
**Fix**: Check that `wagtail.contrib.settings` is in INSTALLED_APPS

### Issue: Navigation menus showing as empty
**Fix**: Ensure MenuItem has `enabled=True` and menu has `enabled=True`

### Issue: Image blocks not loading
**Fix**: Run `python manage.py collectstatic` and check Wagtail images collection

---

## Performance Testing

```bash
# Check page load time
time python manage.py runserver

# Memory usage
from django.db.models import Count
Menu.objects.annotate(item_count=Count('items'))

# Query optimization
from django.db import connection
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def check_queries():
    print(f"Number of queries: {len(connection.queries)}")
    for query in connection.queries:
        print(f"  {query['time']}s - {query['sql'][:100]}")
```

---

## Success Criteria

- [x] All page types (6) can be created
- [x] All block types (16) render correctly
- [x] Branding settings accessible in templates
- [x] Navigation menus display properly
- [x] Database migrations applied (4)
- [x] Django system checks pass (0 errors)
- [x] No console errors in dev server
- [x] Admin interface loads without errors

---

## Next Steps (Phase 3)

With Phase 2 complete, you can now:
1. Implement document ingestion for KnowledgeBase
2. Add full-text search to pages
3. Create API endpoints for frontend apps
4. Implement page preview/publishing workflow
5. Add user permissions for page management

See PHASE_3_IMPLEMENTATION_PLAN.md for details.

---

*Test Guide Created: December 2024*  
*AI CMS Project - Phase 2 Testing*
