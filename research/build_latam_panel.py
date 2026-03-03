"""Build LATAM country-year panel (2005-2023) from external governance datasets.

This script merges standardized extracts from:
- V-Dem (country-year indicators)
- WGI (governance indicators)
- Manifesto Project (executive ideology / salience proxies)
- Optional treaty engagement dataset

Input files can be local CSV files downloaded from official providers.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd

LATAM_ISO3 = [
    "ARG", "BOL", "BRA", "CHL", "COL", "CRI", "CUB", "DOM", "ECU",
    "SLV", "GTM", "HND", "MEX", "NIC", "PAN", "PRY", "PER", "URY",
]


def read_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return pd.read_csv(p)


def prep_vdem(df: pd.DataFrame) -> pd.DataFrame:
    colmap: Dict[str, str] = {
        "country_text_id": "iso3",
        "year": "year",
        "v2xlg_legcon": "legislative_constraints_exec",
        "v2lginvstp": "legislative_investigative_capacity",
        "v2xcl_rol": "rule_of_law_vdem",
        "v2x_polyarchy": "democratic_quality",
    }
    existing = [c for c in colmap if c in df.columns]
    out = df[existing].rename(columns=colmap)
    return out


def prep_wgi(df: pd.DataFrame) -> pd.DataFrame:
    colmap: Dict[str, str] = {
        "Country Code": "iso3",
        "Year": "year",
        "GE.EST": "government_effectiveness",
        "CC.EST": "control_corruption",
        "PV.EST": "political_stability",
        "RL.EST": "rule_of_law_wgi",
    }
    existing = [c for c in colmap if c in df.columns]
    out = df[existing].rename(columns=colmap)
    return out


def prep_manifesto(df: pd.DataFrame) -> pd.DataFrame:
    colmap: Dict[str, str] = {
        "countryname": "country",
        "country": "iso3",
        "edate": "election_date",
        "per503": "welfare_state_expansion",
        "rile": "ideology_rile",
        "year": "year",
    }
    existing = [c for c in colmap if c in df.columns]
    out = df[existing].rename(columns=colmap)
    if "year" not in out.columns and "election_date" in out.columns:
        out["year"] = pd.to_datetime(out["election_date"], errors="coerce").dt.year
    keep = [c for c in ["iso3", "year", "ideology_rile", "welfare_state_expansion"] if c in out.columns]
    out = out[keep]
    if set(["iso3", "year"]).issubset(out.columns):
        out = out.sort_values(["iso3", "year"]).groupby(["iso3", "year"], as_index=False).mean(numeric_only=True)
    return out


def prep_treaty(df: pd.DataFrame) -> pd.DataFrame:
    required = {"iso3", "year"}
    if not required.issubset(df.columns):
        raise ValueError("Treaty dataset must include columns: iso3, year")
    keep = [c for c in ["iso3", "year", "treaty_compliance_score", "global_health_forum_participation"] if c in df.columns]
    return df[keep]


def base_panel(start_year: int, end_year: int) -> pd.DataFrame:
    years = list(range(start_year, end_year + 1))
    return pd.MultiIndex.from_product([LATAM_ISO3, years], names=["iso3", "year"]).to_frame(index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vdem", required=True, help="Path to V-Dem CSV extract")
    parser.add_argument("--wgi", required=True, help="Path to WGI CSV extract")
    parser.add_argument("--manifesto", required=True, help="Path to Manifesto CSV extract")
    parser.add_argument("--treaty", default=None, help="Optional treaty engagement/compliance CSV")
    parser.add_argument("--start-year", type=int, default=2005)
    parser.add_argument("--end-year", type=int, default=2023)
    parser.add_argument("--output", default="data/latam_treaty_panel.csv")
    args = parser.parse_args()

    panel = base_panel(args.start_year, args.end_year)

    vdem = prep_vdem(read_csv(args.vdem))
    wgi = prep_wgi(read_csv(args.wgi))
    mp = prep_manifesto(read_csv(args.manifesto))

    merged = panel.merge(vdem, on=["iso3", "year"], how="left")
    merged = merged.merge(wgi, on=["iso3", "year"], how="left")
    merged = merged.merge(mp, on=["iso3", "year"], how="left")

    if args.treaty:
        treaty = prep_treaty(read_csv(args.treaty))
        merged = merged.merge(treaty, on=["iso3", "year"], how="left")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out, index=False)
    print(f"Saved panel to {out} with shape {merged.shape}")


if __name__ == "__main__":
    main()
