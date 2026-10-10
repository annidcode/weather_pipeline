import os
import boto3
import pandas as pd
import clickhouse_connect
from io import BytesIO

S3_ENDPOINT = os.environ.get('S3_ENDPOINT', 'http://localhost:8333')
S3_BUCKET = 'weather-raw'
CH_HOST = os.environ.get('CH_HOST', 'localhost')
CH_PORT = int(os.environ.get('CH_PORT', 8125))
CH_USER = 'admin'
CH_PASSWORD = 'admin123'


def get_s3():
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id='any',
        aws_secret_access_key='any',
        region_name='us-east-1',
    )


def get_ch():
    return clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT,
        username=CH_USER, password=CH_PASSWORD,
    )


def read_parquet_from_s3(s3, prefix):
    r = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
    keys = [obj['Key'] for obj in r.get('Contents', [])]
    if not keys:
        raise RuntimeError(f"Нет файлов по префиксу {prefix}")
    latest = sorted(keys)[-1]
    print(f"Читаем {latest}...")
    obj = s3.get_object(Bucket=S3_BUCKET, Key=latest)
    return pd.read_parquet(BytesIO(obj['Body'].read()))


def load_current(s3, ch):
    print("=== Yandex current ===")
    df = read_parquet_from_s3(s3, 'yandex/current/')
    print(f"Строк: {len(df)}")

    # Приводим типы
    df['population'] = df['population'].fillna(0).astype('uint64')
    df['humidity'] = df['humidity'].fillna(0).astype('uint8')
    df['pressure_mm'] = df['pressure_mm'].fillna(0).astype('uint16')
    df['uv_index'] = df['uv_index'].fillna(0).astype('uint8')
    df['prec_type'] = df['prec_type'].fillna(0).astype('uint8')
    df['temp'] = df['temp'].fillna(0).astype('int32')
    df['feels_like'] = df['feels_like'].fillna(0).astype('int32')
    df['wind_speed'] = df['wind_speed'].fillna(0).astype('float32')
    df['wind_gust'] = df['wind_gust'].fillna(0).astype('float32')
    df['prec_strength'] = df['prec_strength'].fillna(0).astype('float32')
    df['cloudness'] = df['cloudness'].fillna(0).astype('float32')
    df['magnetic_field'] = df['magnetic_field'].astype('Int32')

    ch.command("DROP TABLE IF EXISTS raw_weather_current")
    ch.command("""
    CREATE TABLE raw_weather_current (
        city String,
        region String,
        latitude Float64,
        longitude Float64,
        population UInt64,
        timestamp String,
        temp Int32,
        feels_like Int32,
        condition String,
        humidity UInt8,
        pressure_mm UInt16,
        wind_speed Float32,
        wind_dir String,
        wind_gust Float32,
        uv_index UInt8,
        prec_strength Float32,
        prec_type UInt8,
        cloudness Float32,
        magnetic_field Nullable(Int32)
    )
    ENGINE = MergeTree()
    ORDER BY (region, city, timestamp) 	 
    """)
    ch.insert_df('raw_weather_current', df)
    print(f"Загружено {len(df)} строк в raw_weather_current")


def load_history(s3, ch):
    print("\n=== Open-Meteo history ===")
    df = read_parquet_from_s3(s3, 'openmeteo/history/')
    print(f"Строк: {len(df)}")

    # Приводим дату
    df['date'] = pd.to_datetime(df['date']).dt.date

    # Приводим типы
    for col in ['temp_max', 'temp_min', 'temp_mean',
                'precipitation', 'wind_speed_max', 'wind_gusts_max']:
        df[col] = df[col].fillna(0).astype('float32')

    ch.command("DROP TABLE IF EXISTS raw_weather_history")
    ch.command("""
    CREATE TABLE raw_weather_history (
        city String,
	region String,
        latitude Float64,
        longitude Float64,
        date Date,
        temp_max Float32,
        temp_min Float32,
        temp_mean Float32,
        precipitation Float32,
        wind_speed_max Float32,
        wind_gusts_max Float32
    )
    ENGINE = MergeTree()
    ORDER BY (region, city, date)
    """)
    ch.insert_df('raw_weather_history', df)
    print(f"Загружено {len(df)} строк в raw_weather_history")


def main():
    s3 = get_s3()
    ch = get_ch()

    load_current(s3, ch)
    load_history(s3, ch)

    print("\n=== Проверка ===")
    for table in ['raw_weather_current', 'raw_weather_history']:
        count = ch.query(f"SELECT count() FROM {table}").result_rows[0][0]
        print(f"{table}: {count} строк")


if __name__ == '__main__':
    main()
