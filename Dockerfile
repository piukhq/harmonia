from python:3.6
workdir /app
run pip install pipenv uwsgi alembic
add Pipfile* ./
run pipenv install --deploy --system
add . .
run pip install .
