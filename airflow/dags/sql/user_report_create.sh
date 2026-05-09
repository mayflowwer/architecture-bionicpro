#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "airflow" --dbname "postgres" <<-EOSQL
    CREATE DATABASE sample;
    GRANT ALL PRIVILEGES ON DATABASE sample TO airflow;
EOSQL

psql -v ON_ERROR_STOP=1 --username "airflow" --dbname "sample" <<-EOSQL
    CREATE TABLE IF NOT EXISTS user_report (
        user_id      VARCHAR  NOT NULL,
        device_id    VARCHAR  NOT NULL,
        action_count INTEGER  NOT NULL DEFAULT 0
    );
EOSQL