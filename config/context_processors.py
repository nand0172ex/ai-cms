"""Context processors for making branding settings available in templates."""

from django.core.cache import cache


def branding(request):
    """
    Add branding settings to template context.
    Results are cached to avoid repeated database queries.
    """
    cache_key = 'branding_settings'
    branding_settings = cache.get(cache_key)
    
    if branding_settings is None:
        try:
            from apps.branding.models import BrandingSettings
            branding_settings = BrandingSettings.for_request(request)
            cache.set(cache_key, branding_settings, 3600)  # Cache for 1 hour
        except Exception:
            # Return empty dict if settings don't exist yet
            branding_settings = {}
    
    return {
        'branding': branding_settings,
    }


def navigation(request):
    """
    Add navigation menus to template context.
    Results are cached to avoid repeated database queries.
    """
    cache_key = 'navigation_menus'
    menus = cache.get(cache_key)
    
    if menus is None:
        try:
            from apps.navigation.models import Menu
            menus = {
                menu.slug: menu.items.filter(enabled=True, parent__isnull=True).order_by('sort_order')
                for menu in Menu.objects.filter(enabled=True)
            }
            cache.set(cache_key, menus, 3600)  # Cache for 1 hour
        except Exception:
            menus = {}
    
    return {
        'menus': menus,
    }
