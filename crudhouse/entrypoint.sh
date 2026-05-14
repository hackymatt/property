#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! python -c "import socket, sys; s=socket.socket(); s.settimeout(1); r=s.connect_ex(('$DB_HOST', int('$DB_PORT'))); s.close(); sys.exit(r)" 2>/dev/null; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

touch /var/log/cron.log
printenv | grep -Ev 'BASHOPTS|BASH_VERSINFO|EUID|PPID|SHELLOPTS|UID|LANG|PWD|GPG_KEY|_=' >> /etc/environment

cd /app/crudhouse

python manage.py migrate

python manage.py collectstatic --no-input

python manage.py init_superuser

gunicorn -c gunicorn_conf.py
