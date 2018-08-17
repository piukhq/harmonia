#! /bin/sh
docker run -d --name postgres -p5432:5432 postgres:latest
docker run -d --name redis -p6379:6379 redis:latest
docker run -d --name rabbitmq -p5672:5672 -p15672:15672 rabbitmq:management
