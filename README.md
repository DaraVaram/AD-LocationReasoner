# Abu Dhabi Site-Selection (H3) — End-to-End How-To

This guide shows how to go from a single POI CSV (`abudhabi_osm_all_pois.csv`) to:

1. H3 zones
2. Per-zone features
3. **Query** JSONs (your rules)
4. **Winning tiles** CSVs
5. Interactive **maps**

No external data (spend, population, etc.) is used—**only your OSM POIs**.

---

## 0) Prerequisites

```bash
# From your project root
cd ./auh_site_selection

# Minimal dependencies
pip install -U pandas numpy h3 pyarrow folium
```

> **H3 note:** The provided `src/zones_h3.py` is compatible with both H3 v3 and v4—no action needed.

**Project layout**

```
auh_site_selection/
  src/
    loader_auh.py            # load POIs
    zones_h3.py              # H3 cells + hex GeoJSON
    features_basic.py        # counts + nearest-distance features
    rules_engine.py          # JSON rule evaluator (AND/OR/NOT)
  scripts/
    build_zones.py           # -> out/zones.parquet, out/pois_with_zone.parquet, out/zones.geojson
    build_features.py        # -> out/zone_features.parquet
    run_ground_truth.py      # -> out/gt/*.csv ("winners")
    viz_queries.py           # -> out/*.html (map for one/many queries)
  demo_queries/              # example rule files (*.json)
  out/                       # all outputs go here
```

When running any script, either run **from the project root** with `PYTHONPATH=.` or ensure the scripts include the `sys.path` snippet (already done).

---

## 1) Input data

Place your combined POI CSV here (or pass an absolute path):

```
./auh_site_selection/abudhabi_osm_all_pois.csv
```

**Required columns:** `category, lat, lon`
(Optional columns like `osm_uid, name, _raw_tags` are fine.)

**Typical categories** (from the Overpass extract):

```
coffee_shops, supermarkets, convenience, bakeries, pharmacies, department_stores,
clothes, electronics, sports, furniture, malls, restaurants, fast_food,
mosques, parks, tourist_landmarks, bus_stops, bus_stations, bus_routes, parking
```

---

## 2) Build H3 zones (hex grid)

```bash
cd ./auh_site_selection
PYTHONPATH=. python scripts/build_zones.py \
  --pois_csv "./abudhabi_osm_all_pois.csv" \
  --out_dir "./out" \
  --h3_res 8 \
  --write_geojson
```

**Outputs**

* `out/pois_with_zone.parquet` — each POI with `zone_id`
* `out/zones.parquet` — one row per zone (`zone_id, center_lat, center_lng`)
* `out/zones.geojson` — hex polygons for mapping

> **Tip:** Adjust spatial granularity with `--h3_res` (7 = coarser, 9 = finer).

---

## 3) Build per-zone features

```bash
PYTHONPATH=. python scripts/build_features.py \
  --zones ./out/zones.parquet \
  --pois_with_zone ./out/pois_with_zone.parquet \
  --out ./out/zone_features.parquet
```

**What gets computed**

* **Counts** for **every** category present in your CSV
  Columns: `cnt_<category>` (e.g., `cnt_pharmacies`, `cnt_parking`, `cnt_restaurants`, …)

* **Nearest distances** (meters) from **zone centroid** to selected categories
  Defaults: `malls`, `bus_stations`, `tourist_landmarks`
  Columns: `dist_to_<category>_m` (e.g., `dist_to_malls_m`, `dist_to_bus_stations_m`, …)

**Customize distance categories (optional)**

```bash
PYTHONPATH=. python scripts/build_features.py \
  --zones ./out/zones.parquet \
  --pois_with_zone ./out/pois_with_zone.parquet \
  --out ./out/zone_features.parquet \
  --distance_categories malls bus_stations tourist_landmarks coffee_shops
```

---

## 4) Write your queries (rule JSON)

A **query** is a JSON file that expresses constraints over columns in `out/zone_features.parquet`.

### 4.1 Grammar

* **Leaf clause**

```json
{"metric": "<column_name>", "op": "<operator>", "value": <number_or_list>}
```

* **Combinators**

```json
{"all_of": [ ... ]}   // logical AND of clauses
{"any_of":  [ ... ]}  // logical OR
{"not":     [ ... ]}  // logical NOT (applies to the enclosed clause/list)
```

* **Supported operators**
  `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not_in`
  For `in`/`not_in`, `value` must be a JSON array.

* **Available metrics**

  * Counts (for every category): `cnt_<category>`
    e.g., `cnt_pharmacies`, `cnt_parking`, `cnt_restaurants`, `cnt_coffee_shops`, …
  * Distances (for categories provided to `--distance_categories`): `dist_to_<category>_m`
    e.g., `dist_to_malls_m`, `dist_to_bus_stations_m`, `dist_to_tourist_landmarks_m`, …

### 4.2 Examples

**(A) Simple — ≥ 2 pharmacies**

```json
{
  "all_of": [
    {"metric": "cnt_pharmacies", "op": ">=", "value": 2}
  ]
}
```

**(B) Distance + counts — within 800 m of a mall AND ≥ 1 parking**

```json
{
  "all_of": [
    {"metric": "dist_to_malls_m", "op": "<=", "value": 800},
    {"metric": "cnt_parking",     "op": ">=", "value": 1}
  ]
}
```

**(C) Mixed — ≥2 pharmacies, ≤800 m to a mall, ≥1 parking, and **no** coffee shops**

```json
{
  "all_of": [
    {"metric": "cnt_pharmacies",   "op": ">=", "value": 2},
    {"metric": "dist_to_malls_m",  "op": "<=", "value": 800},
    {"metric": "cnt_parking",      "op": ">=", "value": 1},
    {"metric": "cnt_coffee_shops", "op": "==", "value": 0}
  ]
}
```

Save your JSON files in `demo_queries/`, e.g.:

```
demo_queries/q10_pharm2_mall800_parking1_no_coffee.json
```

---

## 5) Generate **winners** (tiles satisfying each query)

This scans **every** `*.json` in `demo_queries/` and writes one CSV per query.

```bash
PYTHONPATH=. python scripts/run_ground_truth.py \
  --features ./out/zone_features.parquet \
  --queries_dir ./demo_queries \
  --out_dir ./out/gt
```

**Outputs** (one per query)

```
out/gt/<query_name>.csv    # columns: zone_id, center_lat, center_lng
```

---

## 6) Visualize results (single or multiple queries)

Use the general visualizer to overlay winners on the H3 hex grid.

**Single query**

```bash
PYTHONPATH=. python scripts/viz_queries.py \
  --zones_geojson ./out/zones.geojson \
  --winners_csv ./out/gt/q10_pharm2_mall800_parking1_no_coffee.csv \
  --out ./out/q10_map.html
```

**Multiple queries on one map (toggleable colored layers)**

```bash
PYTHONPATH=. python scripts/viz_queries.py \
  --zones_geojson ./out/zones.geojson \
  --winners_csv ./out/gt/q05_ge_2_pharmacies.csv ./out/gt/q07_within_800m_mall.csv ./out/gt/q10_pharm2_mall800_parking1_no_coffee.csv \
  --out ./out/multi_map.html
```

Open the resulting HTML in your browser.

> **Quicklook alternative:** Convert a winners CSV to **points GeoJSON** (centroids) and drop into kepler.gl/QGIS.

---

## 7) Troubleshooting & tips

* **Use project-relative paths** if you’re already in the root: `./out/...` (not `auh_site_selection/out/...`).
* **Parquet engine**: If Pandas complains, `pip install pyarrow`.
* **Imports**: If you see `ModuleNotFoundError: src`, run with `PYTHONPATH=.` from the project root.
* **Zero results?** Loosen a constraint (e.g., increase distance threshold, reduce counts).
* **Granularity**: Changing `--h3_res` changes the spatial unit; rebuild zones **and** features after changing it.
* **More distance metrics**: Add categories via `--distance_categories` in `build_features.py`.

---

## 8) Quick checklist (copy/paste)

```bash
# 1) Zones
PYTHONPATH=. python scripts/build_zones.py \
  --pois_csv "./abudhabi_osm_all_pois.csv" \
  --out_dir "./out" \
  --h3_res 8 \
  --write_geojson

# 2) Features
PYTHONPATH=. python scripts/build_features.py \
  --zones ./out/zones.parquet \
  --pois_with_zone ./out/pois_with_zone.parquet \
  --out ./out/zone_features.parquet

# 3) Add queries in ./demo_queries/*.json

# 4) Winners
PYTHONPATH=. python scripts/run_ground_truth.py \
  --features ./out/zone_features.parquet \
  --queries_dir ./demo_queries \
  --out_dir ./out/gt

# 5) Visualize
PYTHONPATH=. python scripts/viz_queries.py \
  --zones_geojson ./out/zones.geojson \
  --winners_csv ./out/gt/<one-or-more-csvs> \
  --out ./out/<map>.html
```

