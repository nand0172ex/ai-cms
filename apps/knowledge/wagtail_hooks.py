from django.shortcuts import redirect
from django.urls import path
from django.urls import reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.models import Site
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.knowledge.models import EmbeddingProfile


class EmbeddingProfileViewSet(SnippetViewSet):
    model = EmbeddingProfile
    icon = "snippet"
    menu_label = "Embedding Profiles"
    menu_name = "embedding_profiles"
    list_display = [
        "name",
        "provider_type",
        "model_name",
        "active_status",
        "enabled_status",
        "is_default",
        "sort_order",
        "updated_at",
    ]
    list_filter = {
        "provider_type": ["exact"],
        "is_active": ["exact"],
        "is_default": ["exact"],
    }
    search_fields = ["name", "slug", "model_name", "provider_type"]


register_snippet(EmbeddingProfileViewSet)


def _settings_edit_url_for_request(request, app_label, model_name):
    site = Site.find_for_request(request) or Site.objects.order_by("id").first()
    if not site:
        return reverse("wagtailadmin_home")
    return reverse("wagtailsettings:edit", args=[app_label, model_name, site.pk])


@hooks.register("register_admin_urls")
def register_qdrant_settings_redirect_url():
    return [
        path(
            "qdrant-dashboard-settings/",
            lambda request: redirect(
                _settings_edit_url_for_request(request, "knowledge", "vectordbsettings")
            ),
            name="qdrant_dashboard_settings_shortcut",
        ),
    ]


@hooks.register("register_admin_menu_item")
def register_qdrant_sidebar_menu_item():
    return MenuItem(
        "Vector DB",
        "/admin/qdrant-dashboard-settings/",
        icon_name="site",
        order=551,
    )
