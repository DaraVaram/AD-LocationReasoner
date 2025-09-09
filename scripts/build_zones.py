
import argparse, os
import pandas as pd
from src.loader_auh import load_pois
from src.zones_h3 import assign_h3_zones, build_zone_df, zones_to_geojson

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pois_csv", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--h3_res", type=int, default=8)
    ap.add_argument("--write_geojson", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    pois = load_pois(args.pois_csv)
    pois_z = assign_h3_zones(pois, h3_res=args.h3_res)
    zones = build_zone_df(pois_z)

    pois_z.to_parquet(os.path.join(args.out_dir, "pois_with_zone.parquet"), index=False)
    zones.to_parquet(os.path.join(args.out_dir, "zones.parquet"), index=False)

    if args.write_geojson:
        zones_to_geojson(zones, os.path.join(args.out_dir, "zones.geojson"))

    print(f"✔ Saved zones to {args.out_dir}")

if __name__ == "__main__":
    main()
