FROM binkhq/python:3.8

WORKDIR /app
ADD . .

ADD https://github.com/olix0r/linkerd-await/releases/download/release/v0.2.2/linkerd-await-v0.2.2-amd64 \
    /usr/local/bin/linkerd-await

# prevents tzdata from asking where you live
ARG DEBIAN_FRONTEND=noninteractive

# libgi* and libcairo* are installed for pygobject.
# https://github.com/AzureAD/microsoft-authentication-extensions-for-python/wiki/Encryption-on-Linux
RUN apt-get update && apt-get install -y libgirepository1.0-dev libcairo2-dev python3-dev gir1.2-secret-1 && \
    pip install --no-cache-dir pipenv gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv && \
    chmod +x /usr/local/bin/linkerd-await && \
    apt-get autoremove -y libgirepository1.0-dev libcairo2-dev python3-dev && rm -rf /var/lib/apt/lists

ENTRYPOINT ["/usr/local/bin/linkerd-await"]
CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "app.api.app:app" ]
