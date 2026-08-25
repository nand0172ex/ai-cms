"""
Navigation and menu management models.

Allows admins to create and manage site menus:
- Menu collections
- Menu items with hierarchical structure
- Links to pages, external URLs, or custom URLs
- Visibility and ordering controls
"""

from django.db import models
from django.utils.text import slugify
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page


class Menu(models.Model):
    """
    A collection of menu items.
    Example: "Main Menu", "Footer Menu", "Mobile Menu"
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Menu identifier (e.g., 'Main Menu', 'Footer')"
    )
    slug = models.SlugField(
        unique=True,
        help_text="URL-friendly identifier"
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Enable/disable this menu"
    )
    max_depth = models.IntegerField(
        default=3,
        help_text="Maximum nesting depth for menu items"
    )
    description = models.TextField(
        blank=True,
        help_text="Internal notes about this menu"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel('name'),
        FieldPanel('slug'),
        FieldPanel('enabled'),
        FieldPanel('max_depth'),
        FieldPanel('description'),
        InlinePanel('items', label='Menu Items'),
    ]

    class Meta:
        ordering = ['name']
        verbose_name = "Menu"
        verbose_name_plural = "Menus"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class MenuItem(Orderable):
    """
    Individual menu item that can link to pages or external URLs.
    Supports hierarchical nesting.
    """
    LINK_TYPE_CHOICES = [
        ('page', 'Wagtail Page'),
        ('external', 'External URL'),
        ('custom', 'Custom URL'),
    ]

    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name='items'
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        help_text="Leave blank for top-level items"
    )

    title = models.CharField(
        max_length=255,
        help_text="Display text for menu item"
    )
    link_type = models.CharField(
        max_length=20,
        choices=LINK_TYPE_CHOICES,
        default='page',
        help_text="Type of link this menu item points to"
    )

    # Page link
    page = models.ForeignKey(
        Page,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Select a page (for 'Wagtail Page' link type)"
    )

    # External/Custom URL
    url = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL (for 'External URL' or 'Custom URL' link types)"
    )

    # Display options
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="Icon class (e.g., 'fas fa-home' for Font Awesome)"
    )
    open_in_new_tab = models.BooleanField(
        default=False,
        help_text="Open link in new tab/window"
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Show/hide this menu item"
    )
    custom_css_class = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional CSS classes for styling"
    )

    panels = [
        MultiFieldPanel([
            FieldPanel('title'),
            FieldPanel('link_type'),
        ], heading="Item Details"),
        MultiFieldPanel([
            FieldPanel('page'),
            FieldPanel('url'),
        ], heading="Link Target"),
        MultiFieldPanel([
            FieldPanel('icon'),
            FieldPanel('open_in_new_tab'),
            FieldPanel('enabled'),
            FieldPanel('custom_css_class'),
        ], heading="Display Options"),
    ]

    class Meta:
        ordering = ['sort_order']
        verbose_name = "Menu Item"
        verbose_name_plural = "Menu Items"

    def __str__(self):
        return f"{self.title} ({self.menu.name})"

    def get_url(self):
        """
        Get the actual URL this menu item points to.
        """
        if self.link_type == 'page' and self.page:
            return self.page.url
        elif self.link_type in ['external', 'custom']:
            return self.url
        return '#'

    def get_absolute_url(self):
        """Alias for get_url() for template compatibility."""
        return self.get_url()

    def is_active(self, current_path):
        """
        Check if this menu item is active for the given path.
        Used for highlighting current menu item.
        """
        item_url = self.get_url()
        if item_url == '#':
            return False
        return current_path.startswith(item_url)

    def has_children(self):
        """Check if this item has child items."""
        return self.children.filter(enabled=True).exists()

    def get_children(self):
        """Get enabled child items."""
        return self.children.filter(enabled=True).order_by('sort_order')
