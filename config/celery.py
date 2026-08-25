"""Celery configuration for AI CMS."""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("config")

# Load configuration from Django settings with CELERY namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Define periodic tasks
app.conf.beat_schedule = {
    "cleanup-expired-sessions": {
        "task": "apps.core.tasks.cleanup_expired_sessions",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight UTC
    },
    "connector-sync-hourly": {
        "task": "apps.connectors.tasks.sync_all_active_connectors",
        "schedule": crontab(minute=0),
    },
}


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f"Request: {self.request!r}")
