#!/usr/bin/env python
"""
Phase 2 Sample Data Generator

Creates demo pages, blocks, and settings for quick testing.
Run: python manage.py shell < create_sample_data.py
"""

from django.contrib.auth.models import User
from wagtail.models import Site
from home.models import HomePage, StandardPage, LandingPage
from apps.branding.models import BrandingSettings
from apps.navigation.models import Menu, MenuItem
from wagtail.images.models import Image
from PIL import Image as PILImage
from io import BytesIO
from django.core.files.images import ImageFile
import os

def create_demo_images():
    """Create simple demo images."""
    images = {}
    
    # Create a simple red square image
    for name, color in [('demo-red', '#ff0000'), ('demo-blue', '#0000ff')]:
        img = PILImage.new('RGB', (600, 400), color=color)
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        try:
            image_obj = Image.objects.create(
                title=f"{name}",
                file=ImageFile(img_io, name=f"{name}.png")
            )
            images[name] = image_obj
            print(f"✅ Created image: {name}")
        except Exception as e:
            print(f"⚠️ Could not create image {name}: {e}")
    
    return images

def create_branding():
    """Create or update branding settings."""
    try:
        site = Site.objects.get_current()
        branding, created = BrandingSettings.objects.get_or_create(site=site)
        
        branding.site_name = "AI CMS Platform"
        branding.tagline = "Intelligent Content Management System"
        branding.primary_color = "#007bff"
        branding.secondary_color = "#6c757d"
        branding.accent_color = "#fd7e14"
        branding.email = "info@aicms.local"
        branding.phone = "+1 (555) 123-4567"
        branding.copyright_text = f"© 2024 AI CMS. All rights reserved."
        branding.save()
        
        action = "updated" if not created else "created"
        print(f"✅ Branding settings {action}")
        return branding
    except Exception as e:
        print(f"⚠️ Error creating branding: {e}")
        return None

def create_menus():
    """Create demo menus."""
    try:
        main_menu, created = Menu.objects.get_or_create(
            name="Main Menu",
            defaults={'slug': 'main', 'enabled': True}
        )
        
        # Create menu items
        MenuItem.objects.filter(menu=main_menu).delete()  # Clear existing
        
        menu_items = [
            {"title": "Home", "link_type": "page", "enabled": True, "parent": None},
            {"title": "Features", "link_type": "external", "url": "#features", "enabled": True, "parent": None},
            {"title": "Blog", "link_type": "external", "url": "#blog", "enabled": True, "parent": None},
            {"title": "Contact", "link_type": "external", "url": "#contact", "enabled": True, "parent": None},
        ]
        
        for idx, item_data in enumerate(menu_items):
            MenuItem.objects.create(
                menu=main_menu,
                title=item_data["title"],
                link_type=item_data["link_type"],
                url=item_data.get("url", ""),
                enabled=item_data["enabled"],
                parent=None,
                sort_order=idx
            )
        
        print(f"✅ Created menu: {main_menu.name} with {len(menu_items)} items")
        return main_menu
    except Exception as e:
        print(f"⚠️ Error creating menus: {e}")
        return None

def create_pages():
    """Create demo pages with blocks."""
    try:
        # Get or create root HomePage
        home_page = HomePage.objects.first()
        if not home_page:
            root = HomePage.add_root(
                title="Home",
                slug="home",
                hero_title="Welcome to AI CMS",
                hero_subtitle="Sophisticated Content Management with AI Integration",
                hero_cta_text="Get Started",
                hero_cta_url="https://example.com/start"
            )
            print(f"✅ Created HomePage")
        else:
            root = home_page
            print(f"✅ HomePage already exists")
        
        # Create demo StandardPage
        try:
            demo_page = StandardPage.objects.get(slug='demo-features')
        except StandardPage.DoesNotExist:
            demo_page = root.add_child(
                instance=StandardPage(
                    title="Features Demo",
                    slug="demo-features",
                    description="Demonstration of all Phase 2 StreamField blocks"
                )
            )
            print(f"✅ Created StandardPage: Features Demo")
        
        # Create demo LandingPage
        try:
            landing_page = LandingPage.objects.get(slug='free-trial')
        except LandingPage.DoesNotExist:
            landing_page = root.add_child(
                instance=LandingPage(
                    title="Free Trial Signup",
                    slug="free-trial",
                    headline="Try AI CMS for Free",
                    subheadline="No credit card required",
                    description="Get 30 days free access to all features"
                )
            )
            print(f"✅ Created LandingPage: Free Trial")
        
        return {"home": root, "features": demo_page, "landing": landing_page}
    
    except Exception as e:
        print(f"⚠️ Error creating pages: {e}")
        return {}

def main():
    """Run all sample data creation."""
    print("\n" + "="*60)
    print("🚀 Creating Phase 2 Sample Data")
    print("="*60 + "\n")
    
    print("📸 Creating demo images...")
    images = create_demo_images()
    
    print("\n🎨 Creating branding settings...")
    branding = create_branding()
    
    print("\n📋 Creating navigation menus...")
    menus = create_menus()
    
    print("\n📄 Creating demo pages...")
    pages = create_pages()
    
    print("\n" + "="*60)
    print("✅ Sample Data Creation Complete!")
    print("="*60)
    print("\n📚 Next Steps:")
    print("1. Login to http://localhost:8000/admin/")
    print("2. Navigate to Pages to see created pages")
    print("3. Go to Settings > Branding Settings to see config")
    print("4. Go to Django Admin > Navigation > Menus to see menus")
    print("\n")

if __name__ == "__main__":
    main()
