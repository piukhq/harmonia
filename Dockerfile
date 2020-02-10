FROM python:3.8-alpine
ENV TZ=UTC
WORKDIR /app
ADD . .
ARG DEPLOY_KEY
RUN apk --no-cache add --virtual build-deps \
      build-base \
      postgresql-dev \
      libffi-dev \
      openssh \
      git && \
    apk --no-cache add \
      libpq \
      gnupg && \
    mkdir -p /root/.ssh && \
    echo $DEPLOY_KEY | base64 -d > /root/.ssh/id_rsa && \
    chmod 0600 /root/.ssh/id_rsa && \
    ssh-keyscan git.bink.com > /root/.ssh/known_hosts && \
    pip install pipenv gunicorn alembic && \
    pipenv install --deploy --system --ignore-pipfile && \
    pip uninstall --yes pipenv && \
    apk --no-cache del build-deps && \
    rm -rf /root/.cache
