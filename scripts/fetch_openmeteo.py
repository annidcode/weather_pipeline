import os
import time
import requests
import pandas as pd
import boto3
from datetime import datetime, timezone, timedelta
from io import BytesIO

S3_ENDPOINT = os.environ.get('S3_ENDPOINT', 'http://localhost:8333')
S3_BUCKET = 'weather-raw'
CITIES_FILE = os.environ.get('CITIES_FILE', '/opt/airflow/data/cities_with_regions.csv')
LOCAL_OUTPUT = os.environ.get('LOCAL_OUTPUT', '/opt/airflow/data/weather_history.csv')

HISTORY_DAYS = 365
BATCH_SIZE = 50
BATCH_PAUSE = 30  # секунд между батчами
REQUEST_PAUSE = 1.0  # секунд между запросами
MAX_RETRIES = 5


def get_s3():
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id='any',
        aws_secret_access_key='any',
        region_name='us-east-1',
    )


def fetch_history(lat, lon, tz, start_date, end_date, max_retries=MAX_RETRIES):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
                 "precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max",
        "timezone": tz or "Europe/Moscow",
    }

    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 429:
                wait = 10 * (2 ** attempt)
                print(f"   429, ждём {wait} сек (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            wait = 5 * (2 ** attempt)
            print(f"   timeout, ждём {wait} сек")
            time.sleep(wait)
        except requests.exceptions.RequestException as e:
            print(f"   request error: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(5)

    raise RuntimeError(f"Failed after {max_retries} retries")


def main():
    df_cities = pd.read_csv(CITIES_FILE)
    print(f"Городов: {len(df_cities)}")

    now = datetime.now(timezone.utc)
    end_date = (now - timedelta(days=2)).strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=HISTORY_DAYS + 2)).strftime("%Y-%m-%d")
    print(f"Период: {start_date} → {end_date}")

    s3 = get_s3()
    all_rows = []
    errors = []
    success = 0

    for i, row in df_cities.iterrows():
        try:
            data = fetch_history(
                row['latitude'], row['longitude'],
                row.get('timezone', 'Europe/Moscow'),
                start_date, end_date,
            )
            daily = data.get('daily', {})
            dates = daily.get('time', [])
            for j, d in enumerate(dates):
                all_rows.append({
                    'city': row['name'],
		    'region': row['region'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'date': d,
                    'temp_max': daily['temperature_2m_max'][j],
                    'temp_min': daily['temperature_2m_min'][j],
                    'temp_mean': daily['temperature_2m_mean'][j],
                    'precipitation': daily['precipitation_sum'][j],
                    'wind_speed_max': daily['wind_speed_10m_max'][j],
                    'wind_gusts_max': daily['wind_gusts_10m_max'][j],
                })
            success += 1
        except Exception as e:
            errors.append((row['name'], str(e)))
            print(f"Error for {row['name']}: {e}")

        if (i + 1) % 25 == 0:
            print(f"Обработано {i+1}/{len(df_cities)} (успешно: {success}, ошибок: {len(errors)})")

        # Пауза между батчами
        if (i + 1) % BATCH_SIZE == 0 and i + 1 < len(df_cities):
            print(f"--- Батч {(i+1)//BATCH_SIZE} готов, пауза {BATCH_PAUSE} сек ---")
            time.sleep(BATCH_PAUSE)
        else:
            time.sleep(REQUEST_PAUSE)

    print(f"\nИтог: успешно {success}/{len(df_cities)} городов, ошибок: {len(errors)}")
    if errors:
        print("Города с ошибками:")
        for name, err in errors[:20]:
            print(f"  - {name}: {err[:100]}")

    df_result = pd.DataFrame(all_rows)
    print(f"Строк в датасете: {len(df_result)}")

    if len(df_result) == 0:
        raise RuntimeError("Нет данных для сохранения")

    # Сохраняем в S3
    date_str = now.strftime("%Y-%m-%d")
    key = f"openmeteo/history/dt={date_str}/history_{date_str}.parquet"
    buffer = BytesIO()
    df_result.to_parquet(buffer, index=False)
    buffer.seek(0)

    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=buffer.getvalue())
    print(f"Загружено в s3://{S3_BUCKET}/{key}")

    # Локально
    os.makedirs(os.path.dirname(LOCAL_OUTPUT), exist_ok=True)
    df_result.to_csv(LOCAL_OUTPUT, index=False)
    print(f"Локально: {LOCAL_OUTPUT}")


if __name__ == '__main__':
    main()
