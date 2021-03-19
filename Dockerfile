FROM binkhq/python:3.8

WORKDIR /app
ADD . .

ADD https://github.com/olix0r/linkerd-await/releases/download/release/v0.2.2/linkerd-await-v0.2.2-amd64 \
    /usr/local/bin/linkerd-await

RUN pip install --no-cache-dir pipenv gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv && chmod +x /usr/local/bin/linkerd-await

ENTRYPOINT ["/usr/local/bin/linkerd-await"]
CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "app.api.app:app" ]
