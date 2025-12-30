"""
Celery management module.

This module provides an entry point for defining Celery application and its configuration.
"""

import os

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PharmacyOnDuty.settings")

app = Celery("PharmacyOnDuty")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
