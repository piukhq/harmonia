FROM ghcr.io/binkhq/python:3.10 AS build

WORKDIR /src

RUN pip install poetry==1.2.0b3
RUN poetry config virtualenvs.create false

COPY . .

RUN poetry build

FROM ghcr.io/binkhq/python:3.10 AS base

ARG wheel=harmonia-*-py3-none-any.whl

WORKDIR /app

COPY --from=build /src/dist/$wheel .

ENV PIP_INDEX_URL=https://269fdc63-af3d-4eca-8101-8bddc22d6f14:b694b5b1-f97e-49e4-959e-f3c202e3ab91@pypi.uksouth.bink.sh/simple
RUN pip install $wheel && rm $wheel

ENV PROMETHEUS_MULTIPROC_DIR=/dev/shm
ENTRYPOINT [ "linkerd-await", "--" ]
CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
    "--access-logfile=-", "--bind=0.0.0.0:9000", "app.api.app:app" ]

FROM base AS harness

RUN apt-get update && apt-get -y install tmux nano vim && \
    apt-get clean && rm -rf /var/lib/apt/lists && \
    pip install --no-cache-dir harmonia-fixtures
ADD data_generation /app/data_generation

ENTRYPOINT [ "linkerd-await", "--" ]
CMD ["tail", "-f", "/dev/null"]
