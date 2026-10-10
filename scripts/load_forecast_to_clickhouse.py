import os
import boto3
import pandas as pd
import clickhouse_connect
from io import BytesIO

S3_ENDPOINT = os.environ.get('S3_ENDPOINT', 'http://localhost:8333')
S3_BUCKET = 'weather-raw'
CH_HOST = os.environ.get('CH_HOST', 'localhost')
CH_PORT = int(os.environ.get('CH_PORT', 8125))


def main():
    s3 = boto3.client('s3', endpoint_url=S3_ENDPOINT,
                      aws_access_key_id='any', aws_secret_access_key='any',
                      region_name='us-east-1')
    ch = clickhouse_connect.get_client(host=CH_HOST, port=CH_PORT,
                                        username='admin', password='admin123')

    r = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix='yandex/forecast/')
    keys = sorted([obj['Key'] for obj in r.get('Contents', [])])
    if not keys:
        raise RuntimeError("Нет файлов прогноза в S3")

    latest = keys[-1]
    print(f"Читаем {latest}")
    obj = s3.get_object(Bucket=S3_BUCKET, Key=latest)
    df = pd.read_parquet(BytesIO(obj['Body'].read()))

    df['date'] = pd.to_datetime(df['date']).dt.date

    for col in ['temp_max', 'temp_min', 'temp_avg', 'precipitation',
                'wind_speed', 'wind_gust', 'uv_index', 'humidity']:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype('float32')

    df['condition'] = df['condition'].fillna('')

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
        temp_avg Float32,
        precipitation Float32,
        wind_speed Float32,
        wind_gust Float32,
        condition String,
        uv_index Float32,
        humidity Float32
    )
    ENGINE = MergeTree()
    ORDER BY (region, city, date)
    """)
    ch.insert_df('raw_weather_forecast', df)
    print(f"Загружено {len(df)} строк в raw_weather_forecast")


if __name__ == '__main__':
    main()
