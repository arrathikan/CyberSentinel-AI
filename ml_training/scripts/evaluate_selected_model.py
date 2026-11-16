
"""
CyberAgent AI - Step 7

Two commands:

1. audit
   Check dataset integrity and cross-split feature duplicates.

2. evaluate
   Evaluate the previously selected model on test.csv.

IMPORTANT:
- Do not train or tune models here.
- Do not use test results to select a model.
- This test comes from one capture day.
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)


ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data/processed"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"

TARGET = "binary_label"

ALLOWED_MODELS = {
    "models/random_forest_model.joblib",
    "models/xgboost_model.joblib",
}


def load_metadata():
    """Load the selection and preprocessing settings."""

    selection = json.loads(
        (MODEL_DIR / "selected_model.json").read_text()
    )

    preprocessing = json.loads(
        (REPORT_DIR / "preprocessing_report.json").read_text()
    )

    return selection, preprocessing


def load_split(name, features):
    """Load a prepared dataset and check its schema."""

    path = DATA_DIR / f"{name}.csv"
    df = pd.read_csv(path)

    expected = features + [TARGET]

    if df.columns.tolist() != expected:
        raise ValueError(
            f"{name}: feature columns do not match."
        )

    if df[features].isna().any().any():
        raise ValueError(
            f"{name}: missing feature values detected."
        )

    numeric = df[features].to_numpy(
        dtype=np.float64
    )

    if not np.isfinite(numeric).all():
        raise ValueError(
            f"{name}: non-finite feature values detected."
        )

    if not set(df[TARGET].unique()).issubset({0, 1}):
        raise ValueError(
            f"{name}: unexpected label values."
        )

    return df


def hash_features(df, features):
    """
    Calculate hashes from feature values only.

    These hashes help detect exact feature matches
    between datasets without comparing labels.
    """

    return set(
        pd.util.hash_pandas_object(
            df[features],
            index=False
        ).to_numpy()
    )


def audit():
    """Inspect dataset consistency and overlap."""

    print("\n[1] RUNNING DATA LEAKAGE AUDIT")

    _, preprocessing = load_metadata()
    features = preprocessing["features"]

    train = load_split("train", features)
    validation = load_split("validation", features)
    test = load_split("test", features)

    train_hashes = hash_features(train, features)
    val_hashes = hash_features(validation, features)
    test_hashes = hash_features(test, features)

    overlaps = {
        "train_validation": len(
            train_hashes & val_hashes
        ),
        "train_test": len(
            train_hashes & test_hashes
        ),
        "validation_test": len(
            val_hashes & test_hashes
        ),
    }

    excluded = {
        "label", "binary_label", "timestamp",
        "flow id", "src ip", "dst ip",
        "source ip", "destination ip",
    }

    suspicious = [
        feature for feature in features
        if feature.lower().strip() in excluded
    ]

    # Count records, not just unique hashes.
    report = {
        "method": "feature_hash_overlap_audit",
        "feature_count": len(features),
        "rows": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
        },
        "unique_feature_hash_overlaps": overlaps,
        "suspicious_feature_names": suspicious,
        "limitations": [
            "Hashes can theoretically collide.",
            "Identical features can represent different flows.",
            "Non-identical correlated sessions are not detected.",
            "All partitions originate from one capture day.",
        ],
    }

    # Gate the simple experiment on overlap detection.
    passed = (
        all(count == 0 for count in overlaps.values())
        and len(suspicious) == 0
    )

    report["basic_audit_passed"] = passed

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output = REPORT_DIR / "leakage_audit.json"

    output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("\nRows:")
    print(report["rows"])

    print("\nFeature-hash overlaps:")
    print(overlaps)

    print("\nSuspicious feature names:")
    print(suspicious)

    print("\nBasic audit passed:", passed)
    print("Audit report:", output)

    if not passed:
        print(
            "\nSTOP: Do not run final evaluation yet."
            "\nInspect the overlapping records and "
            "review your data-splitting strategy."
        )

    return passed


def evaluate():
    """Evaluate the selected model on untouched test data."""

    # An audit is required before this evaluation.
    audit_file = REPORT_DIR / "leakage_audit.json"

    if not audit_file.exists():
        raise RuntimeError(
            "Run the audit command first."
        )

    audit_result = json.loads(
        audit_file.read_text()
    )

    if not audit_result["basic_audit_passed"]:
        raise RuntimeError(
            "The leakage audit did not pass."
        )

    selection, preprocessing = load_metadata()

    if selection.get("test_set_evaluated") is not False:
        raise RuntimeError(
            "Expected a validation-only model selection."
        )

    relative_path = selection["artifact_path"]

    if relative_path not in ALLOWED_MODELS:
        raise ValueError(
            "Unrecognized model artifact path."
        )

    model_path = ROOT / relative_path

    # Only load model artifacts created by you.
    artifact = joblib.load(model_path)

    features = preprocessing["features"]

    if artifact["feature_columns"] != features:
        raise ValueError(
            "Model features differ from preprocessing metadata."
        )

    model = artifact["model"]
    threshold = float(
        selection["decision_threshold"]
    )

    if not 0 <= threshold <= 1:
        raise ValueError("Invalid decision threshold.")

    if list(model.classes_) != [0, 1]:
        raise ValueError(
            "Expected binary model classes [0, 1]."
        )

    print("\n[2] RUNNING TEST EVALUATION")

    test = load_split("test", features)

    X_test = test[features]
    y_test = test[TARGET]

    scores = model.predict_proba(X_test)[:, 1]

    predictions = (
        scores >= threshold
    ).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1]
    ).ravel()

    # Ranking metrics require both classes.
    both_classes = set(y_test.unique()) == {0, 1}

    metrics = {
        "accuracy": float(
            accuracy_score(y_test, predictions)
        ),
        "precision": float(
            precision_score(
                y_test, predictions, zero_division=0
            )
        ),
        "recall": float(
            recall_score(
                y_test, predictions, zero_division=0
            )
        ),
        "f1_score": float(
            f1_score(
                y_test, predictions, zero_division=0
            )
        ),
        "average_precision": (
            float(average_precision_score(y_test, scores))
            if both_classes else None
        ),
        "roc_auc": (
            float(roc_auc_score(y_test, scores))
            if both_classes else None
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

    report = {
        "model": selection["selected_model"],
        "model_artifact": relative_path,
        "threshold": threshold,
        "test_rows": int(len(test)),
        "label_counts": {
            str(k): int(v)
            for k, v in y_test.value_counts().items()
        },
        "metrics": metrics,
        "evaluation_scope": (
            "Held-out subset of same capture day"
        ),
        "generalization_to_new_days_verified": False,
    }

    output = REPORT_DIR / "final_test_evaluation.json"

    # Prevent accidental repeated evaluation.
    if output.exists():
        raise RuntimeError(
            "Test report already exists. "
            "Do not repeatedly tune against the test set."
        )

    output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("\nMODEL:", selection["selected_model"])

    for metric, value in metrics.items():
        print(f"{metric}: {value}")

    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=[0, 1],
            target_names=["Benign", "Attack"],
            zero_division=0
        )
    )

    print("\nSaved:", output)
    print("STEP 7 EVALUATION COMPLETED!")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=["audit", "evaluate"]
    )

    args = parser.parse_args()

    if args.command == "audit":
        audit()

    elif args.command == "evaluate":
        evaluate()


if __name__ == "__main__":
    main()
