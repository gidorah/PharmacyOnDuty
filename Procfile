web: gunicorn PharmacyOnDuty.wsgi:application --log-file -
release: python manage.py migrate
release: python manage.py collectstatic --noinput