FROM mysql:8.0

ADD ./00_schema.sql /docker-entrypoint-initdb.d/
ADD ./01_data_dump.sql /docker-entrypoint-initdb.d/