"""Train and interpret a predictive model of Pandemic Treaty implementation capacity in LATAM.

Expected input: CSV with one row per country-year (2005-2023 recommended) and:
- target column (binary): implementation_capacity (1=high/adequate, 0=low/insufficient)
- optional ID columns: country, year
- explanatory variables aligned with legislative/political/regulatory CAS indicators.

Example:
python research/latam_treaty_capacity_model.py \
  --data data/latam_treaty_panel.csv \
  --target implementation_capacity \
  --output-dir research/output
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def build_preprocessor(
    data: pd.DataFrame,
    feature_cols: List[str],
    use_pca: bool,
    pca_components: float,
) -> ColumnTransformer:
    numeric_features = [c for c in feature_cols if pd.api.types.is_numeric_dtype(data[c])]
    categorical_features = [c for c in feature_cols if c not in numeric_features]

    num_steps = [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
    if use_pca:
        num_steps.append(("pca", PCA(n_components=pca_components, svd_solver="full")))

    numeric_pipeline = Pipeline(steps=num_steps)
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_features),
            ("cat", categorical_pipeline, categorical_features),
        ]
    )


def evaluate(y_true: np.ndarray, y_prob: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
    }


def train_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    preprocessor: ColumnTransformer,
    random_state: int,
    cv_splits: int,
) -> Tuple[GridSearchCV, GridSearchCV]:
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=random_state)

    rf_pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            (
                "model",
                RandomForestClassifier(
                    random_state=random_state,
                    class_weight="balanced",
                ),
            ),
        ]
    )
    rf_grid = {
        "model__n_estimators": [200, 500],
        "model__max_depth": [None, 8, 16],
        "model__min_samples_leaf": [1, 3, 5],
    }

    gbm_pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", GradientBoostingClassifier(random_state=random_state)),
        ]
    )
    gbm_grid = {
        "model__n_estimators": [100, 300],
        "model__learning_rate": [0.03, 0.1],
        "model__max_depth": [2, 3],
        "model__subsample": [0.8, 1.0],
    }

    rf_search = GridSearchCV(
        rf_pipeline,
        rf_grid,
        scoring="roc_auc",
        cv=cv,
        n_jobs=-1,
        verbose=0,
    )
    gbm_search = GridSearchCV(
        gbm_pipeline,
        gbm_grid,
        scoring="roc_auc",
        cv=cv,
        n_jobs=-1,
        verbose=0,
    )

    rf_search.fit(X_train, y_train)
    gbm_search.fit(X_train, y_train)

    return rf_search, gbm_search


def compute_tree_importance(model: Pipeline, feature_names: List[str]) -> pd.DataFrame:
    fitted_model = model.named_steps["model"]
    importance = getattr(fitted_model, "feature_importances_", None)
    if importance is None:
        return pd.DataFrame(columns=["feature", "importance"])

    return (
        pd.DataFrame({"feature": feature_names, "importance": importance})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def try_compute_shap(model: Pipeline, X_train: pd.DataFrame, output_dir: Path) -> str:
    try:
        import shap  # type: ignore

        transformed = model.named_steps["preprocess"].transform(X_train)
        estimator = model.named_steps["model"]

        explainer = shap.TreeExplainer(estimator)
        shap_values = explainer.shap_values(transformed)

        if isinstance(shap_values, list):
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]

        np.save(output_dir / "shap_values.npy", shap_values)
        return "SHAP values saved to shap_values.npy"
    except Exception as exc:
        return f"SHAP not computed ({exc})"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to panel CSV.")
    parser.add_argument("--target", default="implementation_capacity", help="Target column name.")
    parser.add_argument("--output-dir", default="research/output", help="Output directory.")
    parser.add_argument("--test-size", type=float, default=0.3)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--cv-splits", type=int, default=5)
    parser.add_argument("--use-pca", action="store_true", help="Apply PCA to numeric features.")
    parser.add_argument(
        "--pca-components",
        type=float,
        default=0.95,
        help="If PCA is enabled, retained variance fraction.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.data)
    if args.target not in df.columns:
        raise ValueError(f"Target column '{args.target}' not in dataset.")

    excluded = {args.target, "country", "year"}
    feature_cols = [c for c in df.columns if c not in excluded]

    id_cols = [c for c in ["country", "year"] if c in df.columns]
    ids = df[id_cols].copy() if id_cols else pd.DataFrame(index=df.index)

    X = df[feature_cols]
    y = df[args.target].astype(int)

    X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
        X,
        y,
        ids,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=y,
    )

    preprocessor = build_preprocessor(
        data=df,
        feature_cols=feature_cols,
        use_pca=args.use_pca,
        pca_components=args.pca_components,
    )

    rf_search, gbm_search = train_models(
        X_train=X_train,
        y_train=y_train,
        preprocessor=preprocessor,
        random_state=args.random_state,
        cv_splits=args.cv_splits,
    )

    model_results = {}
    for name, search in {"random_forest": rf_search, "gbm": gbm_search}.items():
        best_model = search.best_estimator_
        y_prob = best_model.predict_proba(X_test)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)
        metrics = evaluate(y_test.to_numpy(), y_prob, y_pred)

        model_results[name] = {
            "best_params": search.best_params_,
            "cv_best_roc_auc": float(search.best_score_),
            "test_metrics": metrics,
        }

    # Select the winning model using cross-validated validation performance only.
    best_name = max(model_results.keys(), key=lambda m: model_results[m]["cv_best_roc_auc"])
    best_search = {"random_forest": rf_search, "gbm": gbm_search}[best_name]
    best_model = best_search.best_estimator_

    train_prob = best_model.predict_proba(X_train)[:, 1]
    test_prob = best_model.predict_proba(X_test)[:, 1]

    train_scores = ids_train.reset_index(drop=True)
    train_scores["split"] = "train"
    train_scores["y_true"] = y_train.reset_index(drop=True)
    train_scores["y_prob"] = train_prob
    train_scores["y_pred"] = (train_prob >= 0.5).astype(int)

    test_scores = ids_test.reset_index(drop=True)
    test_scores["split"] = "test"
    test_scores["y_true"] = y_test.reset_index(drop=True)
    test_scores["y_prob"] = test_prob
    test_scores["y_pred"] = (test_prob >= 0.5).astype(int)

    country_scores = pd.concat([train_scores, test_scores], ignore_index=True)

    def tier(prob: float) -> str:
        if prob >= 0.7:
            return "High"
        if prob >= 0.4:
            return "Medium"
        return "Low"

    country_scores["implementation_tier"] = country_scores["y_prob"].apply(tier)
    country_scores.to_csv(output_dir / "country_scores.csv", index=False)

    if {"country", "year"}.issubset(country_scores.columns):
        latest_year = int(country_scores["year"].max())
        latest = country_scores[country_scores["year"] == latest_year].copy()
        latest = latest[["country", "year", "y_prob", "implementation_tier"]]
        latest = latest.sort_values("y_prob", ascending=False)
        latest.to_csv(output_dir / "country_benchmarks_latest.csv", index=False)

    transformed_feature_names = best_model.named_steps["preprocess"].get_feature_names_out()
    importances = compute_tree_importance(best_model, list(transformed_feature_names))
    importances.to_csv(output_dir / "feature_importance.csv", index=False)

    shap_status = try_compute_shap(best_model, X_train, output_dir)

    summary = {
        "n_obs": int(df.shape[0]),
        "n_features": int(len(feature_cols)),
        "train_size": int(X_train.shape[0]),
        "test_size": int(X_test.shape[0]),
        "best_model": best_name,
        "country_scores_file": "country_scores.csv",
        "models": model_results,
        "shap": shap_status,
    }

    with open(output_dir / "model_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
