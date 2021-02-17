FROM binkhq/python:3.8

WORKDIR /app
ADD . .

RUN pip install --no-cache-dir pipenv gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv

CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "app.api.app:app" ]
