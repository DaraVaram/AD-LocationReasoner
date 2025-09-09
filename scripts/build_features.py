
import argparse, os
import pandas as pd
from src.features_basic import category_counts, add_nearest_distance_features

DIST_CATS_DEFAULT = ["malls", "bus_stations", "tourist_landmarks"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zones", required=True)
    ap.add_argument("--pois_with_zone", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--distance_categories", nargs="*", default=DIST_CATS_DEFAULT)
    args = ap.parse_args()

    zones = pd.read_parquet(args.zones)
    pois_z = pd.read_parquet(args.pois_with_zone)

    # per-zone counts for all categories present
    counts = category_counts(pois_z)

    # nearest distance to selected categories
    dist = add_nearest_distance_features(zones, pois_z, args.distance_categories)

    # merge
    feats = dist.merge(counts, on="zone_id", how="left")
    feats = feats.fillna(0)

    # Save
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    feats.to_parquet(args.out, index=False)
    print(f"✔ Saved features to {args.out} with {feats.shape[0]} zones and {feats.shape[1]} columns.")

if __name__ == "__main__":
    main()
