import os
import json
import time
import requests
import pandas as pd
import boto3
from datetime import datetime, timezone
from io import BytesIO

YANDEX_KEY = os.environ.get('YANDEX_WEATHER_KEY')
S3_ENDPOINT = os.environ.get('S3_ENDPOINT', 'http://localhost:8333')
S3_BUCKET = 'weather-raw'
CITIES_FILE = os.environ.get('CITIES_FILE', '/opt/airflow/data/cities.csv')

if not YANDEX_KEY:
    raise RuntimeError("YANDEX_WEATHER_KEY не задан")


def get_s3():
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id='any',
        aws_secret_access_key='any',
        region_name='us-east-1',
    )


def fetch_weather(lat, lon):
    url = f"https://api.weather.yandex.ru/v2/forecast"
    headers = {"X-Yandex-API-Key": YANDEX_KEY}
    params = {"lat": lat, "lon": lon, "lang": "ru_RU"}
    r = requests.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def main():
    df = pd.read_csv(CITIES_FILE)
    print(f"Городов: {len(df)}")

    s3 = get_s3()
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")

    rows = []
    errors = 0

    for i, row in df.iterrows():
        try:
            data = fetch_weather(row['latitude'], row['longitude'])
            fact = data.get('fact', {})
            rows.append({
                'city': row['name'],
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'population': int(row['population']),
                'timestamp': now.isoformat(),
                'temp': fact.get('temp'),
                'feels_like': fact.get('feels_like'),
                'condition': fact.get('condition'),
                'humidity': fact.get('humidity'),
                'pressure_mm': fact.get('pressure_mm'),
                'wind_speed': fact.get('wind_speed'),
                'wind_dir': fact.get('wind_dir'),
                'wind_gust': fact.get('wind_gust'),
                'uv_index': fact.get('uv_index'),
                'prec_strength': fact.get('prec_strength'),
                'prec_type': fact.get('prec_type'),
                'cloudness': fact.get('cloudness'),
                'magnetic_field': data.get('forecasts', [{}])[0].get('biomet', {}).get('index'),
            })
        except Exception as e:
            errors += 1
            print(f"Error for {row['name']}: {e}")

        if (i + 1) % 50 == 0:
            print(f"Обработано {i+1}/{len(df)}")

        time.sleep(0.15)  # rate limit

    df_result = pd.DataFrame(rows)
    print(f"Успешно: {len(df_result)}, ошибок: {errors}")

    # Сохраняем в S3
    key = f"yandex/current/dt={date_str}/weather_{date_str}_{time_str}.parquet"
    buffer = BytesIO()
    df_result.to_parquet(buffer, index=False)
    buffer.seek(0)

    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=buffer.getvalue())
    print(f"Загружено в s3://{S3_BUCKET}/{key}")

    # Также локально — для отладки
    local_path = os.environ.get('LOCAL_OUTPUT', '/opt/airflow/data/weather_current.csv') 
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    df_result.to_csv(local_path, index=False)	  

if __name__ == '__main__':
    main()
