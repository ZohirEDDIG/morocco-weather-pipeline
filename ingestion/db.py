import os

import psycopg2
from psycopg2.extras import execute_values

from ingestion.client import DAILY_VARS

DDL = '''
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.cities (
    city_id INT PRIMARY KEY,
    city_name TEXT NOT NULL,
    region TEXT,
    latitude NUMERIC NOT NULL,
    longitude NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.daily_weather (
    city_id              INT  NOT NULL REFERENCES raw.cities (city_id),
    weather_date         DATE NOT NULL,
    temperature_2m_max   NUMERIC,
    temperature_2m_min   NUMERIC,
    temperature_2m_mean  NUMERIC,
    precipitation_sum    NUMERIC,
    wind_speed_10m_max   NUMERIC,
    weather_code         INT,
    _ingested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (city_id, weather_date)
);
'''


def get_conn():
    return psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        port=os.environ.get('POSTGRES_PORT', '5432'),
        dbname=os.environ['WAREHOUSE_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD'],
    )


def init_schema(conn):
    with conn, conn.cursor() as cur:
        cur.execute(DDL)


def upsert_cities(conn, cities):
    sql = '''
        INSERT INTO raw.cities (city_id, city_name, region, latitude, longitude)
        VALUES %s
        ON CONFLICT (city_id) DO UPDATE SET
            city_name = EXCLUDED.city_name,
            region = EXCLUDED.region,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude
    '''

    values = [
        (
            int(city['city_id']),
            city['city_name'],
            city['region'],
            float(city['latitude']),
            float(city['longitude']),
        )
        for city in cities
    ]

    with conn, conn.cursor() as cur:
        execute_values(cur, sql, values)


def upsert_weather(conn, city_id, rows):
    if not rows:
        return

    columns = ['city_id', 'weather_date'] + DAILY_VARS
    updates = ', '.join(f'{column} = EXCLUDED.{column}' for column in DAILY_VARS)

    sql = f'''
        INSERT INTO raw.daily_weather ({', '.join(columns)})
        VALUES %s
        ON CONFLICT (city_id, weather_date) DO UPDATE SET
            {updates},
            _ingested_at = now()
    '''

    values = [
        (city_id, row['weather_date'], *[row[variable] for variable in DAILY_VARS])
        for row in rows
    ]

    with conn, conn.cursor() as cur:
        execute_values(cur, sql, values)
