#!/usr/bin/env python
"""Bootstrap script to create Django app structures in apps directory."""

import os
from pathlib import Path

# Define the apps to create
APPS = [
    "accounts",
    "tenants",
    "branding",
    "navigation",
    "ai_providers",
    "prompts",
    "knowledge",
    "ingestion",
    "connectors",
    "retrieval",
    "workflows",
    "conversations",
    "audit",
    "observability",
    "api",
]

APPS_DIR = Path(__file__).parent / "apps"

# Template files
INIT_PY = """"""

APPS_PY = '''from django.apps import AppConfig


class {ClassNameConfig}(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.{app_name}"
'''

MODELS_PY = """from django.db import models


class AbstractBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
"""

ADMIN_PY = """from django.contrib import admin


# Register your models here.
"""

VIEWS_PY = """from django.shortcuts import render


# Create your views here.
"""

TESTS_PY = """from django.test import TestCase


# Create your tests here.
"""

MIGRATIONS_INIT = """"""


def get_class_name(app_name):
    """Convert app_name to Django AppConfig class name."""
    parts = app_name.split('_')
    return ''.join(part.capitalize() for part in parts) + 'Config'


def create_app(app_name):
    """Create a Django app structure."""
    app_dir = APPS_DIR / app_name
    
    if not app_dir.exists():
        app_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {app_dir}")
    
    # Create __init__.py
    init_file = app_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text(INIT_PY)
        print(f"Created: {init_file}")
    
    # Create apps.py
    apps_file = app_dir / "apps.py"
    if not apps_file.exists():
        content = APPS_PY.format(
            ClassNameConfig=get_class_name(app_name),
            app_name=app_name
        )
        apps_file.write_text(content)
        print(f"Created: {apps_file}")
    
    # Create models.py
    models_file = app_dir / "models.py"
    if not models_file.exists():
        models_file.write_text(MODELS_PY)
        print(f"Created: {models_file}")
    
    # Create admin.py
    admin_file = app_dir / "admin.py"
    if not admin_file.exists():
        admin_file.write_text(ADMIN_PY)
        print(f"Created: {admin_file}")
    
    # Create views.py
    views_file = app_dir / "views.py"
    if not views_file.exists():
        views_file.write_text(VIEWS_PY)
        print(f"Created: {views_file}")
    
    # Create tests.py
    tests_file = app_dir / "tests.py"
    if not tests_file.exists():
        tests_file.write_text(TESTS_PY)
        print(f"Created: {tests_file}")
    
    # Create migrations directory
    migrations_dir = app_dir / "migrations"
    if not migrations_dir.exists():
        migrations_dir.mkdir(exist_ok=True)
        print(f"Created directory: {migrations_dir}")
    
    # Create migrations/__init__.py
    migrations_init = migrations_dir / "__init__.py"
    if not migrations_init.exists():
        migrations_init.write_text(MIGRATIONS_INIT)
        print(f"Created: {migrations_init}")


if __name__ == "__main__":
    print(f"Creating Django apps in {APPS_DIR}")
    for app_name in APPS:
        create_app(app_name)
    print("\nAll apps created successfully!")
