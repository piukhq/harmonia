FROM ghcr.io/binkhq/python:3.8

WORKDIR /app
ADD . .

RUN apt-get update && apt-get -y install tmux nano vim && \
    pipenv install --dev --system --ignore-pipfile && \
    apt-get clean && rm -rf /var/lib/apt/lists

ENTRYPOINT [ "linkerd-await", "--" ]
CMD ["tail", "-f", "/dev/null"]
