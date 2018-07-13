from python:3.6
workdir /app
add . .
run pip install uwsgi pipenv && pipenv install --deploy --system
cmd ["uwsgi","--http",":5000","--wsgi-file","app/api.py","--callable","app","--master"]
