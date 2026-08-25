"""
StreamField block definitions for page content.

Provides reusable content blocks for page building:
- Text blocks (heading, rich text, quote)
- Image blocks (image, image with text)
- Layout blocks (columns, cards, accordion)
- Interactive blocks (button, form)
- Media blocks (video, embed)
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.embeds.blocks import EmbedBlock


class HeadingBlock(blocks.StructBlock):
    """Heading/title block."""
    level = blocks.ChoiceBlock(
        choices=[
            ('h1', 'Heading 1'),
            ('h2', 'Heading 2'),
            ('h3', 'Heading 3'),
            ('h4', 'Heading 4'),
        ],
        default='h2'
    )
    text = blocks.CharBlock(
        max_length=255,
        help_text="Heading text"
    )
    alignment = blocks.ChoiceBlock(
        choices=[
            ('left', 'Left'),
            ('center', 'Center'),
            ('right', 'Right'),
        ],
        default='left'
    )

    class Meta:
        icon = 'title'
        template = 'blocks/heading_block.html'
        label = 'Heading'


class RichTextBlock(blocks.RichTextBlock):
    """Rich text editor block."""
    class Meta:
        icon = 'edit'
        template = 'blocks/richtext_block.html'
        label = 'Rich Text'


class QuoteBlock(blocks.StructBlock):
    """Pull quote block."""
    text = blocks.TextBlock(help_text="Quote text")
    attribution = blocks.CharBlock(
        max_length=255,
        blank=True,
        help_text="Attribution/author"
    )
    alignment = blocks.ChoiceBlock(
        choices=[('left', 'Left'), ('center', 'Center'), ('right', 'Right')],
        default='center'
    )

    class Meta:
        icon = 'openquote'
        template = 'blocks/quote_block.html'
        label = 'Quote'


class ImageBlock(blocks.StructBlock):
    """Standalone image block."""
    image = ImageChooserBlock()
    caption = blocks.CharBlock(
        max_length=255,
        blank=True,
        help_text="Image caption"
    )
    alt_text = blocks.CharBlock(
        max_length=255,
        help_text="Alternative text for accessibility"
    )

    class Meta:
        icon = 'image'
        template = 'blocks/image_block.html'
        label = 'Image'


class ImageTextBlock(blocks.StructBlock):
    """Image with text side-by-side."""
    image = ImageChooserBlock()
    text = blocks.RichTextBlock()
    position = blocks.ChoiceBlock(
        choices=[
            ('left', 'Image Left'),
            ('right', 'Image Right'),
        ],
        default='left'
    )

    class Meta:
        icon = 'image'
        template = 'blocks/image_text_block.html'
        label = 'Image + Text'


class HeroBlock(blocks.StructBlock):
    """Hero/banner section."""
    background_image = ImageChooserBlock()
    title = blocks.CharBlock(max_length=255)
    subtitle = blocks.CharBlock(max_length=255, blank=True)
    button_text = blocks.CharBlock(max_length=100, blank=True)
    button_url = blocks.URLBlock(blank=True)
    overlay_opacity = blocks.IntegerBlock(
        min_value=0,
        max_value=100,
        default=50,
        help_text="Background overlay opacity (0-100)"
    )

    class Meta:
        icon = 'image'
        template = 'blocks/hero_block.html'
        label = 'Hero Banner'


class CTABlock(blocks.StructBlock):
    """Call-to-action button/section."""
    heading = blocks.CharBlock(max_length=255, blank=True)
    text = blocks.TextBlock(blank=True)
    button_text = blocks.CharBlock(max_length=100)
    button_url = blocks.URLBlock()
    button_style = blocks.ChoiceBlock(
        choices=[
            ('primary', 'Primary'),
            ('secondary', 'Secondary'),
            ('accent', 'Accent'),
        ],
        default='primary'
    )

    class Meta:
        icon = 'link'
        template = 'blocks/cta_block.html'
        label = 'Call to Action'


class CardBlock(blocks.StructBlock):
    """Single card for grid layouts."""
    image = ImageChooserBlock(blank=True)
    title = blocks.CharBlock(max_length=255)
    text = blocks.TextBlock(blank=True)
    link_text = blocks.CharBlock(max_length=100, blank=True)
    link_url = blocks.URLBlock(blank=True)

    class Meta:
        icon = 'image'
        template = 'blocks/card_block.html'
        label = 'Card'


class CardsBlock(blocks.StructBlock):
    """Grid of cards."""
    cards = blocks.ListBlock(CardBlock())
    columns = blocks.ChoiceBlock(
        choices=[
            (2, '2 Columns'),
            (3, '3 Columns'),
            (4, '4 Columns'),
        ],
        default=3
    )

    class Meta:
        icon = 'image'
        template = 'blocks/cards_block.html'
        label = 'Cards Grid'


class ColumnsBlock(blocks.StructBlock):
    """Two-column layout."""
    left_content = blocks.StreamBlock(
        [('text', RichTextBlock()), ('image', ImageBlock())],
        help_text="Content for left column"
    )
    right_content = blocks.StreamBlock(
        [('text', RichTextBlock()), ('image', ImageBlock())],
        help_text="Content for right column"
    )

    class Meta:
        icon = 'columns'
        template = 'blocks/columns_block.html'
        label = 'Two Columns'


class AccordionItemBlock(blocks.StructBlock):
    """Single accordion item."""
    title = blocks.CharBlock(max_length=255)
    content = blocks.RichTextBlock()

    class Meta:
        label = 'Accordion Item'


class AccordionBlock(blocks.StructBlock):
    """Accordion/collapsible content."""
    items = blocks.ListBlock(AccordionItemBlock())

    class Meta:
        icon = 'list-ul'
        template = 'blocks/accordion_block.html'
        label = 'Accordion'


class TabItemBlock(blocks.StructBlock):
    """Single tab."""
    label = blocks.CharBlock(max_length=100)
    content = blocks.RichTextBlock()

    class Meta:
        label = 'Tab'


class TabsBlock(blocks.StructBlock):
    """Tabbed interface."""
    tabs = blocks.ListBlock(TabItemBlock())

    class Meta:
        icon = 'list-ul'
        template = 'blocks/tabs_block.html'
        label = 'Tabs'


class CodeBlock(blocks.StructBlock):
    """Code block with syntax highlighting."""
    language = blocks.ChoiceBlock(
        choices=[
            ('python', 'Python'),
            ('javascript', 'JavaScript'),
            ('html', 'HTML'),
            ('css', 'CSS'),
            ('json', 'JSON'),
            ('sql', 'SQL'),
            ('bash', 'Bash'),
            ('plaintext', 'Plain Text'),
        ],
        default='plaintext'
    )
    code = blocks.TextBlock()

    class Meta:
        icon = 'code'
        template = 'blocks/code_block.html'
        label = 'Code Block'


class VideoBlock(blocks.StructBlock):
    """YouTube/Vimeo video embed."""
    video_url = blocks.URLBlock(
        help_text="YouTube or Vimeo URL"
    )
    caption = blocks.CharBlock(
        max_length=255,
        blank=True
    )

    class Meta:
        icon = 'media'
        template = 'blocks/video_block.html'
        label = 'Video'


class CustomHTMLBlock(blocks.RawHTMLBlock):
    """Custom HTML block - restricted to trusted administrators."""
    class Meta:
        icon = 'code'
        template = 'blocks/html_block.html'
        label = 'Custom HTML'
        help_text = "For advanced users only. Admins can configure HTML allowed."


class AIPromptBlock(blocks.StructBlock):
    """AI prompt input and response block."""
    title = blocks.CharBlock(
        max_length=255,
        blank=True,
        help_text="Section title"
    )
    instruction = blocks.TextBlock(
        blank=True,
        help_text="Instruction text shown above input"
    )
    assistant_slug = blocks.CharBlock(
        max_length=255,
        blank=True,
        help_text="Leave blank to use default assistant"
    )
    show_sources = blocks.BooleanBlock(
        default=True,
        help_text="Show source citations in response"
    )

    class Meta:
        icon = 'openquote'
        template = 'blocks/ai_prompt_block.html'
        label = 'AI Prompt'


def get_content_blocks():
    """
    Returns available blocks for StandardPage and similar pages.
    """
    return [
        ('heading', HeadingBlock()),
        ('richtext', RichTextBlock()),
        ('quote', QuoteBlock()),
        ('image', ImageBlock()),
        ('image_text', ImageTextBlock()),
        ('hero', HeroBlock()),
        ('cta', CTABlock()),
        ('cards', CardsBlock()),
        ('columns', ColumnsBlock()),
        ('accordion', AccordionBlock()),
        ('tabs', TabsBlock()),
        ('code', CodeBlock()),
        ('video', VideoBlock()),
        ('embed', EmbedBlock()),
        ('ai_prompt', AIPromptBlock()),
    ]


def get_landing_blocks():
    """
    Returns optimized blocks for landing pages.
    Focused on conversion with fewer options.
    """
    return [
        ('hero', HeroBlock()),
        ('richtext', RichTextBlock()),
        ('image', ImageBlock()),
        ('image_text', ImageTextBlock()),
        ('cards', CardsBlock()),
        ('cta', CTABlock()),
        ('tabs', TabsBlock()),
        ('accordion', AccordionBlock()),
    ]
