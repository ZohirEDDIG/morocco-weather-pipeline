import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

from ingestion.client import fetch_daily
from ingestion.db import get_conn, init_schema, upsert_cities, upsert_weather

CITIES_FILE = Path(__file__).parent / 'cities.csv'


def parse_args():
    today = date.today()
    parser = argparse.ArgumentParser(
        description='Load daily weather into raw.daily_weather'
    )
    parser.add_argument('--start', default=(today - timedelta(days=7)).isoformat())
    parser.add_argument('--end', default=(today - timedelta(days=1)).isoformat())
    return parser.parse_args()


def main():
    args = parse_args()
    print(f'Loading {args.start} -> {args.end}')

    with CITIES_FILE.open(encoding='utf-8') as f:
        cities = list(csv.DictReader(f))

    conn = get_conn()
    try:
        init_schema(conn)
        upsert_cities(conn, cities)
        for city in cities:
            rows = fetch_daily(
                float(city['latitude']), float(city['longitude']), args.start, args.end
            )
            usable = [r for r in rows if r['temperature_2m_max'] is not None]
            upsert_weather(conn, int(city['city_id']), usable)
            skipped = len(rows) - len(usable)
            print(
                f"{city['city_name']}: {len(usable)} rows loaded, {skipped} skipped (no data yet)"
            )
    finally:
        conn.close()


if __name__ == '__main__':
    main()
