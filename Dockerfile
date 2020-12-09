FROM binkhq/python:3.8

WORKDIR /app
ADD . .

RUN apt-get update && apt-get -y install gnupg1 && \
    pip install --no-cache-dir pipenv==2018.11.26 gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv && \
    apt-get clean && rm -rf /var/lib/apt/lists

CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "app.api.app:app" ]
