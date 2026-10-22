
"""
CyberAgent AI - Step 5

Train and validate the first intrusion-detection model.

Model: Random Forest Classifier
Problem: Binary classification (Benign vs Attack)

Training data: data/processed/train.csv
Validation data: data/processed/validation.csv

The test dataset is NOT used in this step.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
    average_precision_score,
)


# ---------------------------------------------
# 1. Project paths
# ---------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

TRAIN_FILE = ROOT / "data/processed/train.csv"
VALIDATION_FILE = ROOT / "data/processed/validation.csv"

PREPROCESSING_REPORT = (
    ROOT / "reports/preprocessing_report.json"
)

MODEL_FILE = ROOT / "models/random_forest_model.joblib"

METRICS_FILE = (
    ROOT / "reports/random_forest_metrics.json"
)

RANDOM_STATE = 42

# Initial baseline configuration
N_ESTIMATORS = 100
MAX_DEPTH = 15
MIN_SAMPLES_LEAF = 2
DECISION_THRESHOLD = 0.50


# ---------------------------------------------
# 2. Load datasets
# ---------------------------------------------

def load_data():
    print("\n[1] Loading datasets...")

    train = pd.read_csv("/Users/aravinthanarrathikasarma/Documents/my_projects/ai _cyber_attack dedoctor/data/processed/test.csv")
    validation = pd.read_csv("/Users/aravinthanarrathikasarma/Documents/my_projects/ai _cyber_attack dedoctor/data/processed/validation.csv")

    if "binary_label" not in train.columns:
        raise ValueError("Training target column is missing.")

    if "binary_label" not in validation.columns:
        raise ValueError("Validation target column is missing.")

    feature_columns = [
        col for col in train.columns
        if col != "binary_label"
    ]

    expected_columns = feature_columns + ["binary_label"]

    if list(validation.columns) != expected_columns:
        raise ValueError(
            "Training and validation columns do not match."
        )

    X_train = train[feature_columns]
    y_train = train["binary_label"]

    X_val = validation[feature_columns]
    y_val = validation["binary_label"]

    # Verify numeric features
    if not all(pd.api.types.is_numeric_dtype(dtype)
               for dtype in X_train.dtypes):
        raise ValueError("Non-numeric training features found.")

    if X_train.isna().any().any() or X_val.isna().any().any():
        raise ValueError("Missing feature values found.")

    if not np.isfinite(X_train.to_numpy()).all():
        raise ValueError("Infinite training values found.")

    if not np.isfinite(X_val.to_numpy()).all():
        raise ValueError("Infinite validation values found.")

    if set(y_train.unique()) != {0, 1}:
        raise ValueError("Training data must have both classes.")

    if set(y_val.unique()) != {0, 1}:
        raise ValueError("Validation data must have both classes.")

    print("Training shape:", X_train.shape)
    print("Validation shape:", X_val.shape)
    print("Features:", len(feature_columns))

    print("\nTraining labels:")
    print(y_train.value_counts().sort_index())

    print("\nValidation labels:")
    print(y_val.value_counts().sort_index())

    return (
        X_train, y_train,
        X_val, y_val,
        feature_columns
    )


# ---------------------------------------------
# 3. Train Random Forest
# ---------------------------------------------

def train_model(X_train, y_train):
    print("\n[2] Training Random Forest...")

    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        random_state=RANDOM_STATE,
        n_jobs=2,
        class_weight="balanced_subsample",
    )

    model.fit(X_train, y_train)

    print("Model training completed!")

    return model


# ---------------------------------------------
# 4. Evaluate on validation data
# ---------------------------------------------

def evaluate_model(model, X_val, y_val):
    print("\n[3] Evaluating on validation data...")

    # Probability estimate for attack class (1)
    probabilities = model.predict_proba(X_val)[:, 1]

    # Convert scores into class predictions
    predictions = (
        probabilities >= DECISION_THRESHOLD
    ).astype(int)

    accuracy = accuracy_score(y_val, predictions)

    precision = precision_score(
        y_val, predictions, zero_division=0
    )

    recall = recall_score(
        y_val, predictions, zero_division=0
    )

    f1 = f1_score(
        y_val, predictions, zero_division=0
    )

    roc_auc = roc_auc_score(y_val, probabilities)

    pr_auc = average_precision_score(
        y_val, probabilities
    )

    cm = confusion_matrix(
        y_val, predictions, labels=[0, 1]
    )

    tn, fp, fn, tp = cm.ravel()

    false_positive_rate = (
        fp / (fp + tn)
        if (fp + tn) > 0 else None
    )

    print("\nVALIDATION RESULTS")
    print("-----------------------------")

    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-score:  {f1:.4f}")
    print(f"ROC-AUC:   {roc_auc:.4f}")
    print(f"AP Score:  {pr_auc:.4f}")

    print("\nConfusion Matrix:")
    print(cm)

    print("\nClassification Report:")
    print(
        classification_report(
            y_val,
            predictions,
            labels=[0, 1],
            target_names=["Benign", "Attack"],
            zero_division=0,
        )
    )

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "roc_auc": float(roc_auc),
        "average_precision": float(pr_auc),
        "false_positive_rate": (
            float(false_positive_rate)
            if false_positive_rate is not None else None
        ),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
        "decision_threshold": DECISION_THRESHOLD,
        "validation_rows": int(len(y_val)),
        "validation_attack_fraction": float(y_val.mean()),
    }


# ---------------------------------------------
# 5. Save model and reports
# ---------------------------------------------

def save_results(model, metrics, features):
    print("\n[4] Saving model and reports...")

    MODEL_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    METRICS_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    with open(
        PREPROCESSING_REPORT, encoding="utf-8"
    ) as file:
        preprocessing = json.load(file)

    if preprocessing["features"] != features:
        raise ValueError(
            "Preprocessing and training feature lists differ."
        )

    # Keep feature metadata and fitted training
    # medians with the model for future inference.
    artifact = {
        "model": model,
        "feature_columns": features,
        "imputation_medians": preprocessing[
            "imputation_medians"
        ],
        "decision_threshold": DECISION_THRESHOLD,
        "python_sklearn_version": sklearn.__version__,
    }

    joblib.dump(artifact, MODEL_FILE)

    report = {
        "model_name": "RandomForestClassifier",
        "created_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "model_parameters": model.get_params(),
        "feature_count": len(features),
        "evaluation_dataset": "validation.csv",
        "test_set_evaluated": False,
        "limitations": [
            "Single-day chronological validation",
            "Sampled traffic records",
            "Possible correlated network sessions",
            "No cross-day generalization demonstrated",
        ],
        "metrics": metrics,
    }

    with open(
        METRICS_FILE, "w", encoding="utf-8"
    ) as file:
        json.dump(report, file, indent=2)

    print("Model saved:", MODEL_FILE)
    print("Metrics saved:", METRICS_FILE)


# ---------------------------------------------
# 6. Main training workflow
# ---------------------------------------------

def main():
    print("=" * 45)
    print("CYBERAGENT AI - RANDOM FOREST TRAINING")
    print("=" * 45)

    (
        X_train, y_train,
        X_val, y_val,
        features
    ) = load_data()

    model = train_model(X_train, y_train)

    metrics = evaluate_model(
        model, X_val, y_val
    )

    save_results(model, metrics, features)

    print("\nSTEP 5 TRAINING COMPLETED!")


if __name__ == "__main__":
    main()
