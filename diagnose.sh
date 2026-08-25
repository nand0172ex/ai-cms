#!/bin/bash
# AI CMS Phase 2 - Complete Error Diagnostic Tool

echo ""
echo "=========================================================="
echo "🔍 AI CMS Phase 2 - Error Diagnostic Report"
echo "=========================================================="
echo ""
echo "Generated: $(date)"
echo "Location: $(pwd)"
echo ""

# Function to print section header
print_section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# 1. Python & Virtual Environment
print_section "1. Python & Virtual Environment"
echo "Python version:"
python --version 2>&1
echo ""
echo "Virtual environment:"
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Active: $VIRTUAL_ENV"
else
    echo "❌ Not activated - activating now..."
    source .venv/bin/activate
    echo "✅ Activated: $VIRTUAL_ENV"
fi
echo ""
echo "Python executable:"
which python
echo ""
echo "pip version:"
pip --version

# 2. Django
print_section "2. Django Configuration"
python manage.py --version 2>&1
echo ""
echo "Settings module: $(python -c 'import os; print(os.environ.get(\"DJANGO_SETTINGS_MODULE\", \"Not set\"))')"
echo ""
echo "Python path:"
python -c "import sys; print('\n'.join(sys.path[:3]))"

# 3. System Checks
print_section "3. Django System Checks"
python manage.py check 2>&1

# 4. Database
print_section "4. Database Status"
echo "Database file:"
ls -lh db.sqlite3 2>&1 || echo "⚠️  No database found"
echo ""
echo "Database type:"
python manage.py shell << 'PYEOF' 2>&1
import django
from django.db import connection
print(f"Engine: {connection.settings_dict['ENGINE']}")
print(f"Name: {connection.settings_dict['NAME']}")
PYEOF

# 5. Migrations
print_section "5. Migration Status"
python manage.py showmigrations --plan 2>&1 | head -30
echo ""
echo "Unapplied migrations:"
python manage.py showmigrations --list 2>&1 | grep '\[ \]' | head -10 || echo "✅ All migrations applied"

# 6. Apps Configuration
print_section "6. Installed Apps"
python manage.py shell << 'PYEOF' 2>&1
from django.apps import apps
installed = [app.name for app in apps.get_app_configs()]
print("Total apps:", len(installed))
print("\nLocal apps (ai-cms):")
for app in sorted(installed):
    if 'apps.' in app or app in ['home', 'search']:
        print(f"  ✅ {app}")
PYEOF

# 7. Admin User
print_section "7. Admin User Status"
python manage.py shell << 'PYEOF' 2>&1
from django.contrib.auth.models import User
users = User.objects.filter(is_staff=True)
if users.exists():
    print("✅ Admin users found:")
    for user in users:
        print(f"   - {user.username} ({user.email})")
else:
    print("❌ No admin users found")
    print("Creating admin user...")
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ Admin user created: admin/admin123")
PYEOF

# 8. Models
print_section "8. CMS Models Status"
python manage.py shell << 'PYEOF' 2>&1
# Check page models
from home.models import HomePage, StandardPage, LandingPage, AIAssistantPage, KnowledgeBasePage

models = [
    ('HomePage', HomePage),
    ('StandardPage', StandardPage),
    ('LandingPage', LandingPage),
    ('AIAssistantPage', AIAssistantPage),
    ('KnowledgeBasePage', KnowledgeBasePage),
]

print("Page Models:")
for name, model in models:
    try:
        count = model.objects.count()
        print(f"  ✅ {name}: {count} records")
    except Exception as e:
        print(f"  ❌ {name}: {str(e)[:50]}")

# Check navigation
from apps.navigation.models import Menu, MenuItem
try:
    menu_count = Menu.objects.count()
    item_count = MenuItem.objects.count()
    print(f"\nNavigation Models:")
    print(f"  ✅ Menu: {menu_count} records")
    print(f"  ✅ MenuItem: {item_count} records")
except Exception as e:
    print(f"  ❌ Navigation error: {str(e)[:50]}")

# Check branding
from apps.branding.models import BrandingSettings
try:
    branding_count = BrandingSettings.objects.count()
    print(f"\nBranding Models:")
    print(f"  ✅ BrandingSettings: {branding_count} records")
except Exception as e:
    print(f"  ❌ Branding error: {str(e)[:50]}")
PYEOF

# 9. Static Files
print_section "9. Static Files"
echo "Static root configured:"
python -c "from django.conf import settings; print(f'  {settings.STATIC_ROOT}')"
echo ""
echo "Static files collected:"
ls -d static 2>/dev/null && echo "  ✅ static/ directory exists" || echo "  ⚠️  Run: python manage.py collectstatic"

# 10. Environment
print_section "10. Environment Variables"
echo "Key settings from .env:"
if [ -f .env ]; then
    echo "  DJANGO_SETTINGS_MODULE=$(grep DJANGO_SETTINGS_MODULE .env | cut -d= -f2)"
    echo "  DJANGO_DEBUG=$(grep DJANGO_DEBUG .env | cut -d= -f2)"
    echo "  DJANGO_ALLOWED_HOSTS=$(grep DJANGO_ALLOWED_HOSTS .env | cut -d= -f2)"
    echo "  DATABASE_URL=$(grep DATABASE_URL .env | cut -d= -f2)"
else
    echo "  ⚠️  .env file not found"
fi

# 11. Templates
print_section "11. Template Configuration"
python -c "from django.conf import settings; print('TEMPLATES directories:'); [print(f'  {d}') for d in settings.TEMPLATES[0].get('DIRS', [])]" 2>&1 || echo "  ⚠️  Could not read templates"
echo ""
echo "Template files in templates/blocks/:"
ls -1 templates/blocks/ 2>/dev/null | wc -l | xargs echo "  " "block templates found"

# 12. Port Status
print_section "12. Port 8000 Status"
echo "Checking if port 8000 is in use:"
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "  ✅ Port 8000 is LISTENING (server is running)"
    echo "  Access: http://localhost:8000/admin/"
else
    echo "  ⚠️  Port 8000 is NOT listening"
    echo "  Run: python manage.py runserver localhost:8000"
fi

# 13. File Permissions
print_section "13. File Permissions"
echo "Database write permissions:"
touch db.sqlite3 2>/dev/null && echo "  ✅ db.sqlite3 writable" || echo "  ❌ db.sqlite3 NOT writable"
echo ""
echo "Media directory:"
[ -d media ] && echo "  ✅ media/ exists" || (mkdir -p media && echo "  ✅ media/ created")
echo ""
echo "Static directory:"
[ -d static ] && echo "  ✅ static/ exists" || echo "  ⚠️  static/ missing (run collectstatic)"

# 14. URLs
print_section "14. URL Configuration"
python manage.py shell << 'PYEOF' 2>&1
from django.urls import get_resolver
from django.urls.exceptions import Resolver404

try:
    resolver = get_resolver()
    print("✅ URL configuration loaded")
    print("\nKey URL patterns:")
    patterns = [
        ('admin', '/admin/'),
        ('home', '/'),
        ('wagtail', '/cms/'),
    ]
    for name, path in patterns:
        try:
            resolver.resolve(path)
            print(f"  ✅ {name}: {path}")
        except Resolver404:
            print(f"  ⚠️  {name}: {path} - NOT FOUND")
except Exception as e:
    print(f"❌ URL error: {str(e)[:100]}")
PYEOF

# Final Summary
print_section "Summary"
echo "✅ If all items above show ✅, the installation is correct"
echo ""
echo "🌐 To access the application:"
echo "  1. Run server: python manage.py runserver localhost:8000"
echo "  2. Open browser: http://localhost:8000/admin/"
echo "  3. Login: admin / admin123"
echo ""
echo "❌ If you see any ❌ errors above, share the output and we'll fix it!"
echo ""
echo "=========================================================="
echo "✨ Diagnostic complete!"
echo "=========================================================="
echo ""
