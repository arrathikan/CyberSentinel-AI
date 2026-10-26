
"""
CyberAgent AI - Step 6

Train XGBoost and compare it with Random Forest.

Uses:
    train.csv
    validation.csv

Does NOT use:
    test.csv

Selection:
    Highest validation Average Precision
    F1-score as tie-breaker
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost

from xgboost import XGBClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    classification_report,
)


# -----------------------------------------
# 1. Project paths
# -----------------------------------------

ROOT = Path(__file__).resolve().parents[2]

TRAIN_FILE = ROOT / "data/processed/train.csv"
VAL_FILE = ROOT / "data/processed/validation.csv"

RF_FILE = ROOT / "models/random_forest_model.joblib"
XGB_FILE = ROOT / "models/xgboost_model.joblib"

SELECTION_FILE = ROOT / "models/selected_model.json"

PREPROCESSING_FILE = (
    ROOT / "reports/preprocessing_report.json"
)

COMPARISON_FILE = (
    ROOT / "reports/model_comparison.json"
)

RANDOM_STATE = 42
THRESHOLD = 0.50


# -----------------------------------------
# 2. Load datasets and feature metadata
# -----------------------------------------

def load_data():
    print("\n[1] Loading datasets...")

    with open(PREPROCESSING_FILE, encoding="utf-8") as f:
        metadata = json.load(f)

    features = metadata["features"]

    train = pd.read_csv(TRAIN_FILE)
    val = pd.read_csv(VAL_FILE)

    expected = features + ["binary_label"]

    for name, data in [("Train", train), ("Validation", val)]:
        if data.columns.tolist() != expected:
            raise ValueError(
                f"{name} columns differ from preprocessing metadata."
            )

        if data[features].isna().any().any():
            raise ValueError(f"{name} contains missing features.")

        if not all(
            pd.api.types.is_numeric_dtype(t)
            for t in data[features].dtypes
        ):
            raise ValueError(f"{name} contains nonnumeric features.")

        if not np.isfinite(
            data[features].to_numpy(dtype=np.float64)
        ).all():
            raise ValueError(f"{name} has infinite feature values.")

        if set(data["binary_label"].unique()) != {0, 1}:
            raise ValueError(f"{name} requires both classes.")

    X_train = train[features]
    y_train = train["binary_label"]

    X_val = val[features]
    y_val = val["binary_label"]

    print("Training rows:", len(train))
    print("Validation rows:", len(val))
    print("Features:", len(features))

    return X_train, y_train, X_val, y_val, metadata


# -----------------------------------------
# 3. Train XGBoost
# -----------------------------------------

def train_xgboost(X_train, y_train):
    print("\n[2] Training XGBoost...")

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        device="cpu",
        n_jobs=2,
        random_state=RANDOM_STATE,
    )

    model.fit(X_train, y_train)

    print("XGBoost training completed!")
    return model


# -----------------------------------------
# 4. Calculate consistent model metrics
# -----------------------------------------

def evaluate(name, model, X_val, y_val):
    print(f"\nEvaluating {name}...")

    classes = list(model.classes_)

    if classes != [0, 1]:
        raise ValueError(
            f"Unexpected model class order: {classes}"
        )

    scores = model.predict_proba(X_val)[:, 1]
    predictions = (scores >= THRESHOLD).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_val,
        predictions,
        labels=[0, 1]
    ).ravel()

    result = {
        "accuracy": float(
            accuracy_score(y_val, predictions)
        ),
        "precision": float(
            precision_score(
                y_val, predictions, zero_division=0
            )
        ),
        "recall": float(
            recall_score(
                y_val, predictions, zero_division=0
            )
        ),
        "f1_score": float(
            f1_score(y_val, predictions, zero_division=0)
        ),
        "roc_auc": float(
            roc_auc_score(y_val, scores)
        ),
        "average_precision": float(
            average_precision_score(y_val, scores)
        ),
        "false_positive_rate": (
            float(fp / (fp + tn))
            if (fp + tn) else None
        ),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }

    print("\nClassification Report:")
    print(
        classification_report(
            y_val, predictions,
            labels=[0, 1],
            target_names=["Benign", "Attack"],
            zero_division=0,
        )
    )

    return result


# -----------------------------------------
# 5. Compare both models
# -----------------------------------------

def compare_models(results):
    print("\n[4] MODEL COMPARISON")
    print("-" * 60)

    comparison = pd.DataFrame(results).T

    columns = [
        "accuracy",
        "precision",
        "recall",
        "f1_score",
        "average_precision",
        "roc_auc",
        "false_positive_rate",
    ]

    print(comparison[columns].round(4).to_string())

    # Select by average precision.
    # Break exact ties using F1-score.
    # Break any remaining tie using model name
    # to make selection deterministic.
    winner = max(
        results.keys(),
        key=lambda name: (
            results[name]["average_precision"],
            results[name]["f1_score"],
            name,
        )
    )

    print(f"\nSelected model: {winner}")

    return winner


# -----------------------------------------
# 6. Save model and selection metadata
# -----------------------------------------

def save_results(
    xgb_model,
    rf_artifact,
    metadata,
    results,
    winner,
):
    print("\n[5] Saving results...")

    XGB_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    COMPARISON_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    features = metadata["features"]

    xgb_artifact = {
        "model": xgb_model,
        "feature_columns": features,
        "imputation_medians": metadata[
            "imputation_medians"
        ],
        "decision_threshold": THRESHOLD,
        "sklearn_version": sklearn.__version__,
        "xgboost_version": xgboost.__version__,
    }

    joblib.dump(xgb_artifact, XGB_FILE)

    model_paths = {
        "Random Forest": "models/random_forest_model.joblib",
        "XGBoost": "models/xgboost_model.joblib",
    }

    selection = {
        "selected_model": winner,
        "artifact_path": model_paths[winner],
        "selection_metric": "validation_average_precision",
        "tie_breaker": "validation_f1_score",
        "decision_threshold": THRESHOLD,
        "test_set_evaluated": False,
    }

    report = {
        "dataset": "CSE-CIC-IDS2018",
        "evaluation_split": "single_day_validation",
        "test_set_evaluated": False,
        "selection": selection,
        "results": results,
        "limitations": [
            "Only one capture day was evaluated",
            "Chronological sampling may retain correlated sessions",
            "Independent cross-day performance is unknown",
            "Scores are not necessarily calibrated probabilities",
        ],
    }

    with open(SELECTION_FILE, "w", encoding="utf-8") as f:
        json.dump(selection, f, indent=2)

    with open(COMPARISON_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("XGBoost model:", XGB_FILE)
    print("Comparison report:", COMPARISON_FILE)
    print("Model selection:", SELECTION_FILE)


# -----------------------------------------
# 7. Main workflow
# -----------------------------------------

def main():
    print("=" * 50)
    print("CYBERAGENT AI - XGBOOST MODEL COMPARISON")
    print("=" * 50)

    X_train, y_train, X_val, y_val, metadata = load_data()

    print("\n[2] Loading existing Random Forest model...")

    # Only load locally trained, trusted model files.
    rf_artifact = joblib.load(RF_FILE)

    if rf_artifact["feature_columns"] != metadata["features"]:
        raise ValueError(
            "Random Forest features do not match "
            "the current preprocessing metadata."
        )

    if rf_artifact["decision_threshold"] != THRESHOLD:
        raise ValueError(
            "Random Forest threshold differs from XGBoost."
        )

    rf_model = rf_artifact["model"]

    if list(rf_model.classes_) != [0, 1]:
        raise ValueError("Unexpected Random Forest classes.")

    # Train the new model.
    xgb_model = train_xgboost(X_train, y_train)

    # Re-evaluate both on exactly the same rows.
    results = {
        "Random Forest": evaluate(
            "Random Forest", rf_model, X_val, y_val
        ),
        "XGBoost": evaluate(
            "XGBoost", xgb_model, X_val, y_val
        ),
    }

    winner = compare_models(results)

    save_results(
        xgb_model,
        rf_artifact,
        metadata,
        results,
        winner,
    )

    print("\nSTEP 6 COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
