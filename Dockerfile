FROM python:3.6-alpine
ENV TZ=UTC
WORKDIR /app
ADD . .
RUN apk --no-cache add libpq gnupg && \
    apk --no-cache add --virtual build-deps build-base postgresql-dev libffi-dev && \
    pip install pipenv gunicorn alembic && \
    pipenv install --deploy --system --ignore-pipfile && \
    pip uninstall --yes pipenv && \
    apk --no-cache del build-deps && \
    rm -rf /root/.cache
