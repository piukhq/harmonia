FROM binkhq/python:3.8

WORKDIR /app
ADD . .

RUN apt-get update && apt-get -y install gnupg1 && \
    pip install --no-cache-dir pipenv==2018.11.26 gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv && \
    apt-get clean && rm -rf /var/lib/apt/lists

# In theory this should then reuse the harmonia layer cache
RUN apt-get update && apt-get -y install tmux && \
    apt-get -y install nano && \
    apt-get clean && rm -rf /var/lib/apt/lists

CMD ["tail", "-f", "/dev/null"]
