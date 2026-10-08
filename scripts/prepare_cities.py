import pandas as pd

columns = [
    'geonameid', 'name', 'asciiname', 'alternatenames',
    'latitude', 'longitude', 'feature_class', 'feature_code',
    'country_code', 'cc2', 'admin1_code', 'admin2_code',
    'admin3_code', 'admin4_code', 'population', 'elevation',
    'dem', 'timezone', 'modification_date'
]

df = pd.read_csv(
    'data/RU.txt',
    sep='\t',
    names=columns,
    dtype={'population': 'Int64'},
    low_memory=False,
)

print(f"Всего записей: {len(df)}")

cities = df[
    (df['feature_class'] == 'P') &
    (df['population'] > 50_000)
].copy()

print(f"Городов с населением > 50k: {len(cities)}")

cities = cities[['name', 'latitude', 'longitude', 'population', 'timezone']]
cities = cities.dropna(subset=['latitude', 'longitude'])
cities = cities.drop_duplicates(subset=['name', 'latitude', 'longitude'])
cities = cities.sort_values('population', ascending=False).reset_index(drop=True)

cities.to_csv('data/cities.csv', index=False)

print(f"\nТоп-10 городов:")
print(cities.head(10).to_string(index=False))

print(f"\nСохранено в data/cities.csv: {len(cities)} городов")
