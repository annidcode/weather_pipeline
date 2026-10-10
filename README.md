# Weather Pipeline: ETL + dbt + Grafana

End-to-end пайплайн для сбора, обработки и визуализации погоды по **419 городам России**.

## Бизнес-задача

Метеосервис хотел:
- Видеть **погоду по всей России** на интерактивной карте.
- Анализировать **историю за год** (тренды, аномалии).
- Показывать **прогноз на неделю** для выбранного города.
- Получать **текущую погоду** с УФ, влажностью, давлением, ветром.

## Архитектура
Яндекс.Погода API Open-Meteo API
↓ ↓
Текущая + прогноз 5д История за год
↓ ↓
SeaweedFS (S3)
↓
ClickHouse (raw)
↓
dbt (staging → marts)
↓
Grafana


## Стек

- **Источники:** Яндекс.Погода API, Open-Meteo API
- **Хранилище:** SeaweedFS (S3), ClickHouse 24.3
- **Трансформации:** dbt (dbt-clickhouse)
- **Оркестрация:** Airflow 2.9
- **BI:** Grafana 10.4
- **Инфраструктура:** Docker Compose
- **Язык:** Python (pandas, requests, boto3, clickhouse-connect, shapely)

## Что сделано

### 1. Данные
- **419 городов России** (GeoNames, население >50k).
- **Текущая погода** + **прогноз 5 дней** (Яндекс.Погода).
- **История за год** (152 988 строк, Open-Meteo).
- **83 региона России** (GeoJSON GADM).
- **Привязка городов к регионам** через shapely.

### 2. ETL-пайплайн
- `prepare_cities.py` — фильтр GeoNames.
- `assign_regions.py` — привязка городов к регионам.
- `fetch_yandex.py` — текущая + прогноз → S3.
- `fetch_openmeteo.py` — история → S3.
- `load_to_clickhouse.py` — S3 → ClickHouse.
- `load_forecast_to_clickhouse.py` — прогноз → ClickHouse.
- `load_geojson.py` — GeoJSON регионов → ClickHouse.

### 3. dbt-модели
**Staging:**
- `stg_yandex_current` — текущая погода.
- `stg_openmeteo_history` — история за год.
- `stg_yandex_forecast` — прогноз.

**Marts:**
- `city_summary`, `region_summary`, `current_by_region`, `daily_weather`, `weather_anomalies`.

### 4. Grafana-дашборд

**Визуализация 1: «Погода в регионах России»**
- Choropleth-карта 83 регионов.
- 3 метрики: температура / ветер / осадки.
- Динамическая легенда и авто-диапазон.

**Визуализация 2: «Мой город»**
- Search bar (419 городов).
- Stat-панель: температура, ощущается, УФ, влажность, давление, ветер, порывы, магнитное поле.
- Прогноз на неделю с переключением метрики.

**Визуализация 3: «История за год»**
- График температуры за период (год/месяц/неделя/день).

## Ключевые концепции

- **ETL:** API → S3 → dbt → DWH.
- **dbt:** staging → marts, тесты данных.
- **Choropleth:** карта с покраской регионов по метрике.
- **GeoJSON:** границы регионов России.
- **Привязка данных:** города → регионы через shapely.

## Ограничения

- **Яндекс.Погода:** тестовый тариф (10 000 запросов). Прогноз только 5 дней.
- **Open-Meteo:** лимиты API (429 при частых запросах).
- **Choropleth в Superset:** не поддерживается, использована Grafana.
- **История за год:** фиксированная (загружена один раз).

## Как запустить

### 1. Инфраструктура
```bash
docker compose up -d
```
Grafana: http://localhost:3000 (admin/admin)

Airflow: http://localhost:8082

ClickHouse: http://localhost:8125 (admin/admin123)

SeaweedFS: http://localhost:8333

### 2. Данные
```bash
source .venv/bin/activate
export YANDEX_WEATHER_KEY="<ключ>"
export S3_ENDPOINT="http://localhost:8333"
export CH_HOST="localhost"
export CH_PORT="8125"

python3 scripts/fetch_yandex.py
python3 scripts/fetch_openmeteo.py
python3 scripts/load_to_clickhouse.py
python3 scripts/load_forecast_to_clickhouse.py
python3 scripts/load_geojson.py
```
### 3. dbt
```bash
cd dbt
export CH_HOST="localhost"
export CH_PORT="9002"
dbt run
dbt test
```

### Что можно улучшить
- Оркестрация через Airflow — ежедневный запуск в 6:00.

- Прогноз на 16 дней — через Open-Meteo Forecast.

- Алерты — аномальная температура → Telegram.

- 1000+ городов — расширить список.

- История за 5 лет — климатические тренды.
