web: bash -c "python manage.py collectstatic --noinput && gunicorn PharmacyOnDuty.wsgi:application"
release: python manage.py migrate
