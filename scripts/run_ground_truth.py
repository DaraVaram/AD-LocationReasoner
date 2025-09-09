
import argparse, os, glob
import pandas as pd
from src.rules_engine import load_spec, evaluate

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--queries_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    feats = pd.read_parquet(args.features)

    # Helpful index
    if "zone_id" not in feats.columns:
        raise ValueError("features file must contain 'zone_id'")

    # Run all *.json queries
    for qpath in sorted(glob.glob(os.path.join(args.queries_dir, "*.json"))):
        spec = load_spec(qpath)
        matched = evaluate(feats, spec)[["zone_id","center_lat","center_lng"]]
        out_csv = os.path.join(args.out_dir, os.path.basename(qpath).replace(".json", ".csv"))
        matched.to_csv(out_csv, index=False)
        print(f"✔ {os.path.basename(qpath)} → {len(matched)} zones → {out_csv}")

if __name__ == "__main__":
    main()
