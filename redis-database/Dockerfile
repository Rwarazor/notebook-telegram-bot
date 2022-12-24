FROM redis

EXPOSE 6379

COPY redis.conf /usr/local/etc/redis/redis.conf
CMD [ "redis-server", "/usr/local/etc/redis/redis.conf", "--save 60 1" ,"--loglevel warning" ]
