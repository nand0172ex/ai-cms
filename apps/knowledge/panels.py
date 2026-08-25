from django.utils.html import format_html
from wagtail.admin.panels import Panel


class ReadOnlyPanel(Panel):
    """Custom panel that displays readonly content from a model property."""

    def __init__(self, attr, heading=None, **kwargs):
        self.attr = attr
        self.heading = heading or attr.replace("_", " ").title()
        super().__init__(**kwargs)
        
    def clone_kwargs(self):
        kwargs = super().clone_kwargs()
        kwargs["attr"] = self.attr
        kwargs["heading"] = self.heading
        return kwargs

    class BoundPanel(Panel.BoundPanel):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.heading = self.panel.heading
            
        def get_comparison(self):
            return []

        def render_html(self, parent_context=None):
            value = getattr(self.instance, self.panel.attr, "")
            
            if callable(value):
                value = value()
                
            return format_html(
                '<div class="w-field__wrapper" data-field-wrapper style="margin-top: 15px;">'
                '<div class="w-field__content">{}</div>'
                '</div>',
                value
            )

        def is_shown(self):
            return True
