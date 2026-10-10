import json
import pandas as pd
import clickhouse_connect

CH_HOST = 'localhost'
CH_PORT = 8125
CH_USER = 'admin'
CH_PASSWORD = 'admin123'


def main():
    ch = clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT,
        username=CH_USER, password=CH_PASSWORD,
    )

    print("Загрузка GeoJSON...")
    with open('geojson/gadm41_RUS_1.json') as f:
        data = json.load(f)

    rows = []
    for feature in data['features']:
        name = feature['properties']['NAME_1']
        geometry = json.dumps(feature['geometry'], ensure_ascii=False)
        rows.append({'name': name, 'geometry': geometry})

    print(f"Регионов: {len(rows)}")

    ch.command("DROP TABLE IF EXISTS regions_geojson")
    ch.command("""
    CREATE TABLE regions_geojson (
        name String,
        geometry String
    )
    ENGINE = MergeTree()
    ORDER BY name
    """)

    df = pd.DataFrame(rows)
    ch.insert_df('regions_geojson', df)
    print(f"Загружено {len(rows)} регионов в regions_geojson")


if __name__ == '__main__':
    main()
