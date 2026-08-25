#!/bin/bash
# Start AI CMS Phase 2 - Complete Setup & Launch

set -e

echo "======================================================="
echo "🚀 AI CMS Phase 2 - Starting Server"
echo "======================================================="
echo ""

# Navigate to project
cd ~/Downloads/ai-cms
echo "📁 Project directory: $(pwd)"

# Activate virtual environment
echo "🐍 Activating Python virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"

# Run system checks
echo ""
echo "🔍 Running Django system checks..."
python manage.py check
echo "✅ System checks passed (0 issues)"

# Ensure admin user exists
echo ""
echo "👤 Checking admin user..."
python manage.py shell << 'PYEOF'
from django.contrib.auth.models import User
admin_exists = User.objects.filter(username='admin').exists()
if admin_exists:
    print("✅ Admin user 'admin' already exists")
else:
    print("⚠️  Creating admin user 'admin'...")
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ Admin user created: admin / admin123")
PYEOF

# Display branding settings
echo ""
echo "🎨 Checking branding configuration..."
python manage.py shell << 'PYEOF'
from apps.branding.models import BrandingSettings
from wagtail.models import Site
try:
    site = Site.objects.get_default()
    print(f"✅ Site: {site.name} ({site.domain})")
except:
    print("⚠️  Using default site")
PYEOF

# Display menu status
echo ""
echo "📋 Checking navigation menus..."
python manage.py shell << 'PYEOF'
from apps.navigation.models import Menu
menus = Menu.objects.all()
if menus.exists():
    print(f"✅ Found {menus.count()} menu(s): {', '.join([m.name for m in menus])}")
else:
    print("⚠️  No menus created yet")
PYEOF

# Display pages
echo ""
echo "📄 Checking pages..."
python manage.py shell << 'PYEOF'
from home.models import HomePage, StandardPage, LandingPage
home_count = HomePage.objects.count()
standard_count = StandardPage.objects.count()
landing_count = LandingPage.objects.count()
print(f"✅ Pages: {home_count} home, {standard_count} standard, {landing_count} landing")
PYEOF

# Final instructions
echo ""
echo "======================================================="
echo "✨ Server is ready to start!"
echo "======================================================="
echo ""
echo "📍 Access URLs:"
echo "   Admin:      http://localhost:8000/admin/"
echo "   Home:       http://localhost:8000/"
echo "   Wagtail:    http://localhost:8000/cms/"
echo ""
echo "🔐 Login Credentials:"
echo "   Username:   admin"
echo "   Password:   admin123"
echo ""
echo "⏸️  Starting development server..."
echo "   Press Ctrl+C to stop the server"
echo ""
echo "======================================================="
echo ""

# Start server
python manage.py runserver localhost:8000
