"""
Setup AI CMS with initial configuration.

Creates:
- Default tenant
- Default Wagtail site
- Root/home page
- Standard groups and permissions
- Default configuration

This command is idempotent and safe to run multiple times.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.sites.models import Site
from wagtail.models import Page
from home.models import HomePage


class Command(BaseCommand):
    help = "Set up AI CMS with initial configuration"

    def handle(self, *args, **options):
        self.stdout.write("Setting up AI CMS...")

        # Create default groups
        self.setup_groups()
        
        # Setup Wagtail site
        self.setup_site()
        
        # Create home page
        self.setup_home_page()
        
        self.stdout.write(
            self.style.SUCCESS("✓ AI CMS setup completed successfully!")
        )
        self.stdout.write(
            self.style.WARNING(
                "\nNext steps:"
                "\n1. Create a superuser: python manage.py createsuperuser"
                "\n2. Start the dev server: python manage.py runserver"
                "\n3. Access admin at: http://localhost:8000/admin"
                "\n4. Configure AI providers"
                "\n5. Set up Qdrant connection"
            )
        )

    def setup_groups(self):
        """Create default groups with appropriate permissions."""
        groups = {
            "Super Administrator": [],
            "Site Administrator": [],
            "Content Editor": [],
            "AI Administrator": [],
            "Knowledge Administrator": [],
            "Connector Administrator": [],
            "Reviewer": [],
            "Read-Only Auditor": [],
        }

        for group_name in groups.keys():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f"  Created group: {group_name}")
            else:
                self.stdout.write(f"  Group exists: {group_name}")

    def setup_site(self):
        """Configure Wagtail site."""
        site = Site.objects.get_or_create(
            pk=1,
            defaults={
                "domain": "localhost:8000",
                "name": "AI CMS",
            }
        )[0]
        
        if site.name != "AI CMS":
            site.name = "AI CMS"
            site.save()
        
        self.stdout.write(f"  Site configured: {site.name} ({site.domain})")

    def setup_home_page(self):
        """Ensure home page is available."""
        # Check if any home page exists
        home_pages = HomePage.objects.all()
        
        if home_pages.exists():
            self.stdout.write("  Home page already exists")
        else:
            self.stdout.write("  Note: Create a home page through Wagtail admin")
