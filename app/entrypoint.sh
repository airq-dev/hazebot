#!/bin/sh

while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
    sleep 0.1
done

echo "Applying pending migrations..."
flask db upgrade

exec "$@"