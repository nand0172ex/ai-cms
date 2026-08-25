"""
Branding configuration models.

Manages site-wide branding settings including:
- Site name and tagline
- Logo and favicon
- Color scheme
- Typography
- Social links
- Contact information
"""

from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.images.models import Image
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting


@register_setting
class BrandingSettings(BaseSiteSetting):
    """
    Global branding settings managed through Wagtail admin.
    """
    site_name = models.CharField(
        max_length=255,
        default="AI CMS",
        help_text="Official site name"
    )
    tagline = models.CharField(
        max_length=255,
        blank=True,
        help_text="Site tagline or slogan"
    )

    # Logo & Icons
    logo = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Site logo (PNG/SVG recommended)"
    )
    logo_white = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="White version of logo (for dark backgrounds)"
    )
    favicon = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Favicon (ICO or PNG, 32x32px)"
    )

    # Color Scheme
    primary_color = models.CharField(
        max_length=7,
        default="#007bff",
        help_text="Primary brand color (hex format)"
    )
    secondary_color = models.CharField(
        max_length=7,
        default="#6c757d",
        help_text="Secondary brand color (hex format)"
    )
    accent_color = models.CharField(
        max_length=7,
        default="#fd7e14",
        help_text="Accent brand color (hex format)"
    )
    background_color = models.CharField(
        max_length=7,
        default="#ffffff",
        help_text="Page background color"
    )
    text_color = models.CharField(
        max_length=7,
        default="#212529",
        help_text="Primary text color"
    )

    # Typography
    heading_font = models.CharField(
        max_length=100,
        default="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        help_text="Font family for headings (CSS font-family value)"
    )
    body_font = models.CharField(
        max_length=100,
        default="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        help_text="Font family for body text"
    )
    monospace_font = models.CharField(
        max_length=100,
        default="'Monaco', 'Courier New', monospace",
        help_text="Font family for code/monospace text"
    )

    # Social Links
    twitter_url = models.URLField(blank=True, help_text="Twitter profile URL")
    linkedin_url = models.URLField(blank=True, help_text="LinkedIn profile URL")
    github_url = models.URLField(blank=True, help_text="GitHub profile URL")
    facebook_url = models.URLField(blank=True, help_text="Facebook page URL")
    instagram_url = models.URLField(blank=True, help_text="Instagram profile URL")

    # Contact
    email = models.EmailField(blank=True, help_text="Contact email address")
    phone = models.CharField(max_length=20, blank=True, help_text="Phone number")
    address = models.TextField(blank=True, help_text="Physical address")

    # Footer
    copyright_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Copyright notice in footer"
    )

    panels = [
        MultiFieldPanel([
            FieldPanel('site_name'),
            FieldPanel('tagline'),
        ], heading="Site Identity"),
        MultiFieldPanel([
            FieldPanel('logo'),
            FieldPanel('logo_white'),
            FieldPanel('favicon'),
        ], heading="Assets"),
        MultiFieldPanel([
            FieldPanel('primary_color'),
            FieldPanel('secondary_color'),
            FieldPanel('accent_color'),
            FieldPanel('background_color'),
            FieldPanel('text_color'),
        ], heading="Colors"),
        MultiFieldPanel([
            FieldPanel('heading_font'),
            FieldPanel('body_font'),
            FieldPanel('monospace_font'),
        ], heading="Fonts"),
        MultiFieldPanel([
            FieldPanel('twitter_url'),
            FieldPanel('linkedin_url'),
            FieldPanel('github_url'),
            FieldPanel('facebook_url'),
            FieldPanel('instagram_url'),
        ], heading="Social Links"),
        MultiFieldPanel([
            FieldPanel('email'),
            FieldPanel('phone'),
            FieldPanel('address'),
        ], heading="Contact Info"),
        MultiFieldPanel([
            FieldPanel('copyright_text'),
        ], heading="Footer"),
    ]

    class Meta:
        verbose_name = "Branding Settings"
        verbose_name_plural = "Branding Settings"

    def __str__(self):
        return "Branding Settings"
