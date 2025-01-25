release: python manage.py migrate
release: bash scripts/on_deploy.sh
web: gunicorn PharmacyOnDuty.wsgi:application --log-file -