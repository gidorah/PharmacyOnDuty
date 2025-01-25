release: bash scripts/on_deploy.sh
release: python manage.py migrate
web: gunicorn PharmacyOnDuty.wsgi:application --log-file -