#!/usr/bin/env bash
# exit on error

# set -o errexit

# pip install -r requirements.txt
# python manage.py collectstatic --noinput
# python manage.py migrate


#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); u, _ = User.objects.get_or_create(username='alamin'); u.set_password('alamin1234'); u.is_staff=True; u.is_superuser=True; u.is_active=True; u.save()"

