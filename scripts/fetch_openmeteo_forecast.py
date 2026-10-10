import os
import time
import requests
import pandas as pd
import clickhouse_connect

CH_HOST = os.environ.get('CH_HOST', 'localhost')
CH_PORT = int(os.environ.get('CH_PORT', 8125))
CH_USER = 'admin'
CH_PASSWORD = 'admin123'
CITIES_FILE = os.environ.get('CITIES_FILE', 'data/cities_with_regions.csv')
FORECAST_DAYS = 7
BATCH_PAUSE = 30
REQUEST_PAUSE = 1.0


def get_ch():
    return clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT,
        username=CH_USER, password=CH_PASSWORD,
    )


def fetch_forecast(lat, lon, tz):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "wind_speed_10m_max,wind_gusts_10m_max",
        "timezone": tz or "Europe/Moscow",
        "forecast_days": FORECAST_DAYS,
    }
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 429:
                wait = 10 * (2 ** attempt)
                print(f"   429, ждём {wait} сек")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"   error: {e}")
            time.sleep(5)
    return None


def main():
    df_cities = pd.read_csv(CITIES_FILE)
    print(f"Городов: {len(df_cities)}")

    ch = get_ch()
    all_rows = []
    success = 0
    errors = 0

    for i, row in df_cities.iterrows():
        data = fetch_forecast(row['latitude'], row['longitude'], row.get('timezone', 'Europe/Moscow'))
        if not data:
            errors += 1
            continue

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
                'precipitation': daily['precipitation_sum'][j],
                'wind_speed_max': daily['wind_speed_10m_max'][j],
                'wind_gusts_max': daily['wind_gusts_10m_max'][j],
            })
        success += 1

        if (i + 1) % 25 == 0:
            print(f"Обработано {i+1}/{len(df_cities)} (успешно: {success}, ошибок: {errors})")

        if (i + 1) % 50 == 0 and i + 1 < len(df_cities):
            time.sleep(BATCH_PAUSE)
        else:
            time.sleep(REQUEST_PAUSE)

    print(f"\nИтог: {success}/{len(df_cities)}, ошибок: {errors}")
    df = pd.DataFrame(all_rows)
    print(f"Строк: {len(df)}")

    if len(df) == 0:
        raise RuntimeError("Нет данных")

    df['date'] = pd.to_datetime(df['date']).dt.date
    for col in ['temp_max', 'temp_min', 'precipitation', 'wind_speed_max', 'wind_gusts_max']:
        df[col] = df[col].fillna(0).astype('float32')

    ch.command("DROP TABLE IF EXISTS raw_weather_forecast")
    ch.command("""
    CREATE TABLE raw_weather_forecast (
        city String,
        region String,
        latitude Float64,
        longitude Float64,
        date Date,
        temp_max Float32,
        temp_min Float32,
        precipitation Float32,
        wind_speed_max Float32,
        wind_gusts_max Float32
    )
    ENGINE = MergeTree()
    ORDER BY (region, city, date)
    """)
    ch.insert_df('raw_weather_forecast', df)
    print(f"Загружено {len(df)} строк в raw_weather_forecast")


if __name__ == '__main__':
    main()
