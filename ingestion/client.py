import time

import requests

ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive'

DAILY_VARS = [
    'temperature_2m_max',
    'temperature_2m_min',
    'temperature_2m_mean',
    'precipitation_sum',
    'wind_speed_10m_max',
    'weather_code',
]


def fetch_daily(lat, lon, start, end, retries=3):
    params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': start,
        'end_date': end,
        'daily': ','.join(DAILY_VARS),
        'timezone': 'Africa/Casablanca',
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(ARCHIVE_URL, params=params, timeout=30)
            response.raise_for_status()
            daily = response.json()['daily']
            break
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            wait = 2**attempt
            print(
                f'API error ({exc}); retrying in {wait}s (attempt {attempt}/{retries})'
            )
            time.sleep(wait)

    return [
        {'weather_date': day, **{var: daily[var][i] for var in DAILY_VARS}}
        for i, day in enumerate(daily['time'])
    ]