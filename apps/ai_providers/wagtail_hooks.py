from django.shortcuts import redirect
from django.urls import path
from django.urls import reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.models import Site
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from apps.ai_providers.models import AIProviderSettings
from apps.ai_providers.models import ReasoningProviderProfile


class ReasoningProviderProfileViewSet(SnippetViewSet):
    model = ReasoningProviderProfile
    icon = "snippet"
    menu_label = "Reasoning Provider Profiles"
    menu_name = "reasoning_provider_profiles"
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


register_snippet(ReasoningProviderProfileViewSet)


def _settings_edit_url_for_request(request, app_label, model_name):
    site = Site.find_for_request(request) or Site.objects.order_by("id").first()
    if not site:
        return reverse("wagtailadmin_home")
    return reverse("wagtailsettings:edit", args=[app_label, model_name, site.pk])


@hooks.register("register_admin_urls")
def register_ai_provider_settings_redirect_url():
    return [
        path(
            "ai-provider-settings/",
            lambda request: redirect(
                _settings_edit_url_for_request(request, "ai_providers", "aiprovidersettings")
            ),
            name="ai_provider_settings_shortcut",
        ),
    ]


@hooks.register("construct_settings_menu")
def hide_ai_and_qdrant_from_settings_menu(request, menu_items):
    target_labels = {"AI Provider Settings", "Qdrant Dashboard"}
    targets = (
        "/admin/settings/ai_providers/aiprovidersettings",
        "/admin/settings/knowledge/vectordbsettings",
    )
    kept = []
    for item in menu_items:
        item_url = getattr(item, "url", "") or ""
        item_label = str(getattr(item, "label", "") or "")
        if item_label in target_labels or any(target in item_url for target in targets):
            continue
        kept.append(item)
    menu_items[:] = kept


@hooks.register("register_admin_menu_item")
def register_ai_provider_sidebar_menu_item():
    return MenuItem(
        "AI Provider Settings",
        "/admin/ai-provider-settings/",
        icon_name="cog",
        order=550,
    )
