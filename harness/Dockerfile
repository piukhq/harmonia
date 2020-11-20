FROM binkhq/python:3.8

WORKDIR /app
ADD . .

RUN apt-get update && apt-get -y install gnupg1 tmux nano && \
    pip install --no-cache-dir pipenv==2018.11.26 && \
    pipenv install --dev --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv && \
    apt-get clean && rm -rf /var/lib/apt/lists

CMD ["tail", "-f", "/dev/null"]
