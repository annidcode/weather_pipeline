import json
import pandas as pd
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

print("Загрузка GeoJSON регионов...")
with open('geojson/gadm41_RUS_1.json') as f:
    regions = json.load(f)

print(f"Регионов в GeoJSON: {len(regions['features'])}")

# Строим пространственный индекс
geoms = [shape(f['geometry']) for f in regions['features']]
names = [f['properties']['NAME_1'] for f in regions['features']]
tree = STRtree(geoms)

print("Загрузка городов...")
cities = pd.read_csv('data/cities.csv')
print(f"Городов: {len(cities)}")

# Для каждого города находим регион
regions_for_cities = []
for _, row in cities.iterrows():
    point = Point(row['longitude'], row['latitude'])
    idx = tree.query(point)
    if len(idx) > 0:
        region_name = names[idx[0]]
    else:
        region_name = None
    regions_for_cities.append(region_name)

cities['region'] = regions_for_cities

cities.to_csv('data/cities_with_regions.csv', index=False)

print(f"\nНайдено регионов: {cities['region'].notna().sum()} из {len(cities)}")
print(f"Уникальных регионов: {cities['region'].nunique()}")
print()
print(cities.head(15).to_string(index=False))
