"""Admin registration for navigation models."""

from django.contrib import admin
from .models import Menu, MenuItem


class MenuItemInline(admin.TabularInline):
    """Inline admin for menu items."""
    model = MenuItem
    extra = 1
    fields = ['title', 'link_type', 'page', 'url', 'enabled', 'sort_order']
    ordering = ['sort_order']


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    """Admin interface for Menu model."""
    list_display = ('name', 'slug', 'enabled', 'created_at')
    list_filter = ('enabled', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin interface for MenuItem model."""
    list_display = ('title', 'menu', 'link_type', 'enabled')
    list_filter = ('menu', 'link_type', 'enabled')
    search_fields = ('title',)
    readonly_fields = ('sort_order',)
