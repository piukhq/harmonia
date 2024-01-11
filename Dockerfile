FROM ghcr.io/binkhq/python:3.11 AS build

WORKDIR /src

RUN pip install poetry

COPY . .

RUN poetry build

FROM ghcr.io/binkhq/python:3.11

ARG PIP_INDEX_URL

WORKDIR /app

COPY --from=build /src/dist/*.whl .

RUN pip install *.whl && rm *.whl

COPY --from=build /src/alembic.ini alembic.ini
COPY --from=build /src/alembic/ alembic/

ENV PROMETHEUS_MULTIPROC_DIR=/dev/shm
ENTRYPOINT [ "linkerd-await", "--" ]
CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
    "--access-logfile=-", "--bind=0.0.0.0:9000", "app.api.app:app" ]
