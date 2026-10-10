import os
import time
import requests
import pandas as pd
import boto3
from datetime import datetime, timezone
from io import BytesIO

YANDEX_KEY = os.environ.get('YANDEX_WEATHER_KEY')
S3_ENDPOINT = os.environ.get('S3_ENDPOINT', 'http://localhost:8333')
S3_BUCKET = 'weather-raw'
CITIES_FILE = os.environ.get('CITIES_FILE', '/opt/airflow/data/cities_with_regions.csv')

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
    url = "https://api.weather.yandex.ru/v2/forecast"
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

    rows_current = []
    rows_forecast = []
    errors = 0

    for i, row in df.iterrows():
        try:
            data = fetch_weather(row['latitude'], row['longitude'])
            fact = data.get('fact', {})

            # Текущая погода
            rows_current.append({
                'city': row['name'],
                'region': row['region'],
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

            # Прогноз на 5 дней
            for forecast in data.get('forecasts', []):
                parts = forecast.get('parts', {})
                day = parts.get('day', {})
                rows_forecast.append({
                    'city': row['name'],
                    'region': row['region'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'date': forecast.get('date'),
                    'temp_max': day.get('temp_max'),
                    'temp_min': day.get('temp_min'),
                    'temp_avg': day.get('temp_avg'),
                    'precipitation': day.get('prec_mm', 0),
                    'wind_speed': day.get('wind_speed'),
                    'wind_gust': day.get('wind_gust'),
                    'condition': day.get('condition'),
                    'uv_index': day.get('uv_index'),
                    'humidity': day.get('humidity'),
                })
        except Exception as e:
            errors += 1
            print(f"Error for {row['name']}: {e}")

        if (i + 1) % 50 == 0:
            print(f"Обработано {i+1}/{len(df)}")

        time.sleep(0.15)

    df_current = pd.DataFrame(rows_current)
    df_forecast = pd.DataFrame(rows_forecast)

    print(f"\nТекущая погода: {len(df_current)} строк")
    print(f"Прогноз: {len(df_forecast)} строк")
    print(f"Ошибок: {errors}")

    # Текущая погода → S3
    key_current = f"yandex/current/dt={date_str}/weather_{date_str}_{time_str}.parquet"
    buffer = BytesIO()
    df_current.to_parquet(buffer, index=False)
    buffer.seek(0)
    s3.put_object(Bucket=S3_BUCKET, Key=key_current, Body=buffer.getvalue())
    print(f"Текущая погода: s3://{S3_BUCKET}/{key_current}")

    # Прогноз → S3
    key_forecast = f"yandex/forecast/dt={date_str}/forecast_{date_str}_{time_str}.parquet"
    buffer = BytesIO()
    df_forecast.to_parquet(buffer, index=False)
    buffer.seek(0)
    s3.put_object(Bucket=S3_BUCKET, Key=key_forecast, Body=buffer.getvalue())
    print(f"Прогноз: s3://{S3_BUCKET}/{key_forecast}")

    # Локально
    local_current = os.environ.get('LOCAL_OUTPUT', '/opt/airflow/data/weather_current.csv')
    local_forecast = os.environ.get('LOCAL_FORECAST', '/opt/airflow/data/weather_forecast.csv')
    os.makedirs(os.path.dirname(local_current), exist_ok=True)
    df_current.to_csv(local_current, index=False)
    df_forecast.to_csv(local_forecast, index=False)
    print(f"Локально: {local_current}, {local_forecast}")


if __name__ == '__main__':
    main()
