FROM mysql:8.0

ADD ./schema.sql /docker-entrypoint-initdb.d/

# https://stackoverflow.com/a/46801962/975271
COPY ./data_dump.placeholder.sql ./data_dump.sql* /docker-entrypoint-initdb.d/