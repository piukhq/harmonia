from python:3.6-alpine
workdir /app
run apk add build-base postgresql-dev && \
    pip install pipenv gunicorn alembic
add . .
run pipenv install --deploy --system --ignore-pipfile
