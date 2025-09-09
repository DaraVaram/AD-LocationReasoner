#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
General H3 query visualizer (Folium)
- Visualizes one or more ground-truth query CSVs on top of the zones.geojson
- Each query gets its own colored overlay + layer toggle
- Works with CSVs produced by scripts/run_ground_truth.py
  (columns: zone_id, center_lat, center_lng)

Usage (single query):
  PYTHONPATH=. python scripts/viz_queries.py \
    --zones_geojson ./out/zones.geojson \
    --winners_csv ./out/gt/q05_ge_2_pharmacies.csv \
    --out ./out/q05_map.html

Usage (multiple queries; each becomes a layer):
  PYTHONPATH=. python scripts/viz_queries.py \
    --zones_geojson ./out/zones.geojson \
    --winners_csv ./out/gt/q01_ge_3_coffee_shops.csv ./out/gt/q07_within_800m_mall.csv \
    --out ./out/multi_map.html
"""

import os, json, argparse
import pandas as pd
import folium

# A few nice distinct colors (cycled if you pass > len colors)
PALETTE = [
    "#3778C2", "#E07A5F", "#3DA35D", "#B56576",
    "#6D597A", "#F2CC8F", "#1D7874", "#8E7DBE",
    "#FF9F1C", "#2A9D8F", "#A26769", "#4361EE",
]

def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def base_layer(zones_gj):
    # Light grey base layer of ALL zones
    return folium.GeoJson(
        zones_gj,
        name="All H3 zones",
        style_function=lambda feat: {
            "weight": 0.5,
            "color": "#B3B3B3",
            "fillOpacity": 0.05,
        },
        tooltip=folium.GeoJsonTooltip(fields=["zone_id"]),
        control=True,
        show=True,
    )

def filtered_layer(zones_gj, zone_ids, color, layer_name):
    # Keep only features whose properties.zone_id is in zone_ids
    feats = []
    for feat in zones_gj.get("features", []):
        zid = feat.get("properties", {}).get("zone_id")
        if zid in zone_ids:
            feats.append(feat)
    gj = {"type": "FeatureCollection", "features": feats}

    return folium.GeoJson(
        gj,
        name=layer_name,
        style_function=lambda _feat, c=color: {
            "weight": 1,
            "color": c,
            "fillColor": c,
            "fillOpacity": 0.6,
        },
        tooltip=folium.GeoJsonTooltip(fields=["zone_id"]),
        control=True,
        show=True,
    )

def pick_center_from_winners(dfs):
    # Use the first non-empty winners CSV to center the map
    for df in dfs:
        if not df.empty and {"center_lat","center_lng"}.issubset(df.columns):
            return [df["center_lat"].mean(), df["center_lng"].mean()]
    return None

def pick_center_from_geojson(zones_gj):
    # Fallback: average centers from geojson properties
    lats, lngs = [], []
    for f in zones_gj.get("features", []):
        p = f.get("properties", {})
        if "center_lat" in p and "center_lng" in p:
            lats.append(float(p["center_lat"]))
            lngs.append(float(p["center_lng"]))
    if lats and lngs:
        return [sum(lats)/len(lats), sum(lngs)/len(lngs)]
    return [24.4539, 54.3773]  # Abu Dhabi fallback

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zones_geojson", required=True, help="Path to out/zones.geojson")
    ap.add_argument("--winners_csv", nargs="+", required=True,
                    help="One or more winners CSVs (from run_ground_truth.py)")
    ap.add_argument("--out", required=True, help="Output HTML map path")
    ap.add_argument("--zoom", type=int, default=12)
    ap.add_argument("--tiles", default="cartodbpositron")
    args = ap.parse_args()

    # Load base layers
    zones_gj = load_geojson(args.zones_geojson)

    # Load winners (one or many CSVs)
    winner_dfs = []
    for csv_path in args.winners_csv:
        df = pd.read_csv(csv_path)
        if "zone_id" not in df.columns:
            raise ValueError(f"{csv_path} missing 'zone_id'")
        winner_dfs.append(df)

    # Map center
    center = pick_center_from_winners(winner_dfs) or pick_center_from_geojson(zones_gj)
    m = folium.Map(location=center, zoom_start=args.zoom, tiles=args.tiles)

    # Add base grey grid of all zones
    base = base_layer(zones_gj)
    base.add_to(m)

    # Add an overlay per query (colored)
    for i, (csv_path, df) in enumerate(zip(args.winners_csv, winner_dfs)):
        color = PALETTE[i % len(PALETTE)]
        layer_name = os.path.basename(csv_path)
        zone_ids = set(df["zone_id"].astype(str))
        layer = filtered_layer(zones_gj, zone_ids, color, layer_name)
        layer.add_to(m)

    # Layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Save
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    m.save(args.out)
    print(f"✔ Saved {args.out}")

if __name__ == "__main__":
    main()
