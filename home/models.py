"""
Page type models for AI CMS.

Defines different page types:
- HomePage: Site landing page
- StandardPage: General content page  
- LandingPage: Marketing/campaign pages
- AIAssistantPage: Chat interface
- KnowledgeBasePage: Knowledge base listing and detail
"""

from django.db import models
from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.search import index

from .blocks import get_content_blocks, get_landing_blocks


class BasePage(Page):
    """
    Abstract base page with common SEO and configuration fields.
    """
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Page description for search engines"
    )
    og_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Open Graph Title",
        help_text="Title for social media sharing"
    )
    og_description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Open Graph Description",
        help_text="Description for social media sharing"
    )
    og_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Open Graph Image",
        help_text="Image for social media sharing"
    )
    canonical_url = models.URLField(
        blank=True,
        help_text="Canonical URL for duplicate page management"
    )

    class Meta:
        abstract = True

    promote_panels = Page.promote_panels + [
        MultiFieldPanel([
            FieldPanel('description'),
            FieldPanel('og_title'),
            FieldPanel('og_description'),
            FieldPanel('og_image'),
            FieldPanel('canonical_url'),
        ], heading="SEO & Social Media")
    ]

    search_fields = Page.search_fields + [
        index.SearchField('description'),
        index.SearchField('og_description'),
    ]


class HomePage(BasePage):
    """
    Homepage with hero section and featured content.
    """
    hero_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Large hero title at page top"
    )
    hero_subtitle = models.CharField(
        max_length=255,
        blank=True,
        help_text="Subtitle under hero title"
    )
    hero_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Background image for hero section"
    )
    hero_cta_text = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Hero CTA Text",
        help_text="Call-to-action button text"
    )
    hero_cta_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Hero CTA URL",
        help_text="URL for CTA button"
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('hero_title'),
            FieldPanel('hero_subtitle'),
            FieldPanel('hero_image'),
            FieldPanel('hero_cta_text'),
            FieldPanel('hero_cta_url'),
        ], heading="Hero Section")
    ]

    subpage_types = ['StandardPage', 'LandingPage', 'AIAssistantPage', 'KnowledgeBasePage']

    class Meta:
        verbose_name = "Home Page"
        verbose_name_plural = "Home Pages"


class StandardPage(BasePage):
    """
    Standard content page with StreamField blocks.
    Flexible page for various content types.
    """
    body = StreamField(
        get_content_blocks(),
        blank=True,
        help_text="Add content blocks using the editor"
    )

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    subpage_types = ['StandardPage', 'LandingPage']
    parent_page_types = ['HomePage', 'StandardPage']

    search_fields = BasePage.search_fields + [
        index.SearchField('body'),
    ]

    class Meta:
        verbose_name = "Standard Page"
        verbose_name_plural = "Standard Pages"


class LandingPage(BasePage):
    """
    Marketing/campaign landing page.
    Optimized for conversions with focused content.
    """
    headline = models.CharField(
        max_length=255,
        help_text="Main headline for landing page"
    )
    subheadline = models.CharField(
        max_length=255,
        blank=True,
        help_text="Supporting headline"
    )
    body = StreamField(
        get_landing_blocks(),
        blank=True,
        help_text="Landing page content blocks"
    )
    cta_text = models.CharField(
        max_length=100,
        verbose_name="CTA Text",
        help_text="Primary call-to-action button text"
    )
    cta_url = models.CharField(
        max_length=500,
        verbose_name="CTA URL",
        help_text="Target URL for CTA"
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('headline'),
            FieldPanel('subheadline'),
            FieldPanel('cta_text'),
            FieldPanel('cta_url'),
        ], heading="Landing Page Config"),
        FieldPanel('body'),
    ]

    parent_page_types = ['HomePage', 'StandardPage']
    subpage_types = []

    search_fields = BasePage.search_fields + [
        index.SearchField('headline'),
        index.SearchField('subheadline'),
        index.SearchField('body'),
    ]

    class Meta:
        verbose_name = "Landing Page"
        verbose_name_plural = "Landing Pages"


class AIAssistantPage(BasePage):
    """
    Public-facing AI assistant/chat page.
    Displays chat interface and assistant configuration.
    """
    assistant_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of AI assistant"
    )
    assistant_description = RichTextField(
        blank=True,
        help_text="Description shown above chat"
    )
    welcome_message = models.TextField(
        blank=True,
        help_text="Initial message shown to user"
    )
    show_knowledge_selector = models.BooleanField(
        default=False,
        help_text="Allow user to select knowledge bases"
    )
    allow_anonymous = models.BooleanField(
        default=True,
        help_text="Allow anonymous users to chat"
    )
    require_login = models.BooleanField(
        default=False,
        help_text="Require login to use chat"
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('assistant_name'),
            FieldPanel('assistant_description'),
            FieldPanel('welcome_message'),
        ], heading="Assistant Config"),
        MultiFieldPanel([
            FieldPanel('show_knowledge_selector'),
            FieldPanel('allow_anonymous'),
            FieldPanel('require_login'),
        ], heading="Access Control"),
    ]

    parent_page_types = ['HomePage', 'StandardPage']
    subpage_types = []

    class Meta:
        verbose_name = "AI Assistant Page"
        verbose_name_plural = "AI Assistant Pages"


class KnowledgeBasePage(BasePage):
    """
    Knowledge base listing and detail pages.
    """
    is_listing = models.BooleanField(
        default=True,
        help_text="Is this a listing page (vs detail page)?"
    )
    knowledge_base = models.ForeignKey(
        'knowledge.KnowledgeBase',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="For detail pages: select knowledge base"
    )

    content_panels = Page.content_panels + [
        FieldPanel('is_listing'),
        FieldPanel('knowledge_base'),
    ]

    parent_page_types = ['HomePage', 'StandardPage']
    subpage_types = []

    class Meta:
        verbose_name = "Knowledge Base Page"
        verbose_name_plural = "Knowledge Base Pages"
