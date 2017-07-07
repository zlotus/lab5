# lab5
backend for my antd-admin

if you want to play this repo, you may need to install redis.
then run `sudo redis-server` in your host to start a redis server with default configuration.

after that, you need to run `celery worker -A app.celery --loglevel=debug` to start a celery worker.

oh, you also have to install tensorflow in your python running environment.

GG, GL. T_T.