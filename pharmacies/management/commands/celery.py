from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Start celery worker with production settings"

    def handle(self, *args, **options):
        import subprocess

        subprocess.run(["celery", "-A", "PharmacyOnDuty", "worker", "-l", "info"])
