"""
App configuration for the Pharmacies application.
"""

from django.apps import AppConfig


class PharmaciesConfig(AppConfig):
    """
    Configuration for the pharmacies application.

    This class handles the initialization of the pharmacies app, including
    signal registration (if any) and default field types.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "pharmacies"
