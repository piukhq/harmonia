FROM binkhq/python:3.8

WORKDIR /app
ADD . .

RUN apt-get update && apt-get -y install gnupg1 && \
    apt-get -y install tmux && \
    apt-get -y install nano && \
    pip install --no-cache-dir pipenv==2018.11.26 gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv && \
    apt-get clean && rm -rf /var/lib/apt/lists

cmd ["tail", "-f", "/dev/null"]
