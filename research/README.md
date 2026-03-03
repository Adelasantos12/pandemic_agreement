# LATAM Pandemic Treaty Implementation Capacity Model (CAS)

This module operationalizes your research design into a reproducible machine-learning workflow for 18 LATAM countries (2005-2023), under a Complex Adaptive Systems (CAS) framing.

## 1) Outcome definition

Binary target (`implementation_capacity`):
- `1`: country-year shows strong domestic internalization and implementation readiness for Pandemic Treaty obligations.
- `0`: limited or weak internalization/implementation readiness.

You can create this outcome from a composite index (e.g., legal transposition, institutional setup, budget alignment, compliance behavior) and threshold it.

## 2) Recommended variable architecture

Use one row per `country-year` and include features from these blocks:

### A. Executive priorities and influence
- Executive ideology position (Manifesto Project)
- Health salience in executive agenda
- V-Dem executive dominance / constraints indicators
- WGI Voice & Accountability (optional control)

### B. Legislative capacities
- Legislative independence from executive (V-Dem)
- Opposition strength (V-Dem)
- Government majority size in lower/upper chambers
- Legislative approval timeline (days from proposal to approval)

### C. Governance quality and political stability
- Democratic quality indices (V-Dem)
- Regime stability / turnover frequency
- Degree of centralization/decentralization
- WGI Government Effectiveness
- WGI Control of Corruption

### D. International engagement and compliance
- Historical treaty compliance score
- Participation intensity in WHO and global health forums
- Number of relevant reservations/non-compliance episodes

## 3) Modeling approach

Implemented in `latam_treaty_capacity_model.py`:
- 70/30 train-test split (stratified)
- 5-fold stratified cross-validation
- Supervised algorithms:
  - Random Forest
  - Gradient Boosting Machine (GBM)
- Hyperparameter tuning via `GridSearchCV`
- Metrics: Accuracy, Precision, Recall, F1, ROC-AUC
- Interpretability:
  - Tree feature importance (always)
  - SHAP values (optional; if `shap` is installed)

PCA is optional via `--use-pca` to reduce dimensionality on numeric inputs.

## 4) Data template

Minimum columns:
- `country`
- `year`
- `implementation_capacity` (0/1)
- Predictor columns for each conceptual block above

## 5) Run

```bash
pip install -r research/requirements-ml.txt
python research/latam_treaty_capacity_model.py \
  --data data/latam_treaty_panel.csv \
  --target implementation_capacity \
  --output-dir research/output
```

Optional PCA:

```bash
python research/latam_treaty_capacity_model.py \
  --data data/latam_treaty_panel.csv \
  --use-pca \
  --pca-components 0.95
```

## 6) Outputs

Generated in `research/output/`:
- `model_summary.json`: best model, CV score, test metrics, selected hyperparameters.
- `feature_importance.csv`: ranked variable importance from best tree model.
- `country_scores.csv`: country-year probabilities (`y_prob`) and tier labels (`High/Medium/Low`) for train/test splits.
- `country_benchmarks_latest.csv`: latest-year country benchmark ranking.
- `shap_values.npy`: local attribution values if SHAP execution succeeds.

## 7) Visualización en Railway (dashboard por país)

Sí, se puede desplegar en Railway y visualizar resultados tipo data science.

Después de generar `research/output/*`, levanta la API (Railway usa esto en el servicio `web`):

```bash
uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT
```

Endpoints de visualización/consulta:
- `GET /research/dashboard` → dashboard interactivo (Plotly) con:
  - barra por país (último año)
  - trayectoria temporal por país
- `GET /research/overview?output_dir=research/output`
- `GET /research/countries?output_dir=research/output&latest_year_only=true`
- `GET /research/country/{country}?output_dir=research/output`

Si guardas outputs en otra ruta/persistencia, ajusta `output_dir` en query params.

## 8) Interpretation guidance for objectives

### Objective 1: Build predictive model integrating legislative, governance, and political stability indicators
- Compare RF vs GBM by **test ROC-AUC** first, then F1.
- Validate generalization by consistency between CV ROC-AUC and test ROC-AUC.
- If class imbalance is high, prioritize Recall/F1 and consider threshold tuning.

### Objective 2: Identify critical factors influencing norm internalization
- Use top-ranked features from `feature_importance.csv`.
- If SHAP is available, compute average absolute SHAP values by feature and by country clusters.
- Conduct robustness checks: retrain excluding one variable block at a time (ablation) to quantify block-level contributions in CAS terms.

## 9) Suggested benchmark outputs (country-level)

Create benchmark profiles for each country using:
- Predicted probability of high implementation capacity.
- Top 3 constraining factors (negative SHAP contributions or low-score features).
- Top 3 enabling factors.
- Policy action tags (legislative reform, anti-corruption, coalition management, treaty engagement).

This supports comparative governance diagnostics across LATAM and can be extended specifically for Mexico as a dedicated medium-term line.
