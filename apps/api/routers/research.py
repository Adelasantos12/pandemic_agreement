from pathlib import Path
from typing import Optional

import json

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

router = APIRouter()


def _resolve_output_dir(output_dir: str) -> Path:
    path = Path(output_dir)
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=404, detail=f"Output directory not found: {output_dir}")
    return path


@router.get("/overview")
def overview(output_dir: str = Query("research/output")):
    base = _resolve_output_dir(output_dir)
    summary_path = base / "model_summary.json"
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="model_summary.json not found")
    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/countries")
def countries(output_dir: str = Query("research/output"), latest_year_only: bool = Query(True)):
    base = _resolve_output_dir(output_dir)
    scores_path = base / "country_scores.csv"
    if not scores_path.exists():
        raise HTTPException(status_code=404, detail="country_scores.csv not found")

    df = pd.read_csv(scores_path)
    if latest_year_only and "year" in df.columns:
        latest = int(df["year"].max())
        df = df[df["year"] == latest]

    cols = [c for c in ["country", "year", "y_prob", "y_pred", "implementation_tier"] if c in df.columns]
    return {"rows": df[cols].sort_values(["country", "year"]).to_dict(orient="records")}


@router.get("/country/{country}")
def country_detail(country: str, output_dir: str = Query("research/output")):
    base = _resolve_output_dir(output_dir)
    scores_path = base / "country_scores.csv"
    fi_path = base / "feature_importance.csv"

    if not scores_path.exists():
        raise HTTPException(status_code=404, detail="country_scores.csv not found")

    scores = pd.read_csv(scores_path)
    subset = scores[scores["country"].str.lower() == country.lower()].copy()
    if subset.empty:
        raise HTTPException(status_code=404, detail=f"Country not found: {country}")

    response = {
        "country": country,
        "trajectory": subset.sort_values("year").to_dict(orient="records"),
    }

    if fi_path.exists():
        fi = pd.read_csv(fi_path).head(10)
        response["top_features"] = fi.to_dict(orient="records")

    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(output_dir: Optional[str] = Query("research/output")):
    html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset='utf-8'/>
      <title>LATAM Treaty Capacity Dashboard</title>
      <script src='https://cdn.plot.ly/plotly-2.35.2.min.js'></script>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 24px; }}
        .row {{ display: flex; gap: 20px; align-items: center; }}
        select {{ padding: 6px; }}
      </style>
    </head>
    <body>
      <h2>LATAM Pandemic Treaty Implementation Capacity</h2>
      <p>Output directory: <code>{output_dir}</code></p>
      <div class='row'>
        <label>Country: <select id='countrySelect'></select></label>
      </div>
      <div id='bar' style='width:100%;height:420px;'></div>
      <div id='line' style='width:100%;height:420px;'></div>

      <script>
        const outputDir = encodeURIComponent('{output_dir}');

        async function loadCountries() {{
          const res = await fetch(`/research/countries?output_dir=${{outputDir}}&latest_year_only=true`);
          const data = await res.json();
          const rows = data.rows || [];

          const x = rows.map(r => r.country);
          const y = rows.map(r => r.y_prob);
          Plotly.newPlot('bar', [{{x, y, type:'bar'}}], {{title:'Latest year predicted implementation capacity by country'}});

          const select = document.getElementById('countrySelect');
          select.innerHTML = x.map(c => `<option value="${{c}}">${{c}}</option>`).join('');
          if (x.length > 0) loadCountryDetail(x[0]);
          select.onchange = (e) => loadCountryDetail(e.target.value);
        }}

        async function loadCountryDetail(country) {{
          const res = await fetch(`/research/country/${{country}}?output_dir=${{outputDir}}`);
          const data = await res.json();
          const t = data.trajectory || [];
          const x = t.map(r => r.year);
          const y = t.map(r => r.y_prob);
          Plotly.newPlot('line', [{{x, y, type:'scatter', mode:'lines+markers'}}], {{title: `Trajectory: ${{country}}`}});
        }}

        loadCountries();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
