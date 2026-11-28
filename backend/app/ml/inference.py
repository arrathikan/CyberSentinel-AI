
"""
CyberAgent AI - Step 8
Load the selected model and predict network traffic.

Only locally trained, trusted model artifacts are loaded.
"""

import json
from math import isfinite
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = ROOT / "models"

ALLOWED_MODELS = {
    "models/random_forest_model.joblib",
    "models/xgboost_model.joblib",
}


class CyberattackPredictor:

    def __init__(self):
        selection_file = (
            MODEL_DIR / "selected_model.json"
        )

        selection = json.loads(
            selection_file.read_text(encoding="utf-8")
        )

        relative_path = selection["artifact_path"]

        # Never load a model path supplied by API clients.
        if relative_path not in ALLOWED_MODELS:
            raise ValueError("Unapproved model artifact")

        model_path = ROOT / relative_path

        # Joblib files must come from a trusted source.
        artifact = joblib.load(model_path)

        self.model = artifact["model"]
        self.model_name = selection["selected_model"]
        version = selection.get("model_version", artifact.get("model_version"))
        if version is not None and (not isinstance(version, str) or not version.strip()):
            raise ValueError("Model version must be a nonempty string")
        self.model_version = version
        self.features = artifact["feature_columns"]
        self.medians = artifact["imputation_medians"]
        self.threshold = float(
            selection["decision_threshold"]
        )

        if len(self.features) != len(set(self.features)):
            raise ValueError("Duplicate feature names")

        if set(self.medians) != set(self.features):
            raise ValueError("Imputation metadata mismatch")

        if not 0 <= self.threshold <= 1:
            raise ValueError("Invalid decision threshold")

        if list(self.model.classes_) != [0, 1]:
            raise ValueError("Expected classes [0, 1]")

        if hasattr(self.model, "n_features_in_"):
            if self.model.n_features_in_ != len(self.features):
                raise ValueError("Model feature count mismatch")

        print(f"Loaded model: {self.model_name}")
        print(f"Features: {len(self.features)}")

    def predict(self, values: dict):
        """
        Predict one pre-extracted network flow.

        Expected:
        {feature_name: numeric_value_or_null}

        Missing feature keys and unexpected feature names
        are rejected. Null values use training medians.
        """

        expected = set(self.features)
        provided = set(values)

        missing = sorted(expected - provided)
        unexpected = sorted(provided - expected)

        if missing or unexpected:
            raise ValueError(
                f"Missing features: {missing[:10]}; "
                f"Unexpected features: {unexpected[:10]}"
            )

        cleaned = {}

        for feature in self.features:
            value = values[feature]

            if value is None:
                cleaned[feature] = float(
                    self.medians[feature]
                )
                continue

            # Reject strings, booleans and nonnumeric input.
            if isinstance(value, bool) or not isinstance(
                value, (int, float)
            ):
                raise ValueError(
                    f"{feature} must be numeric or null"
                )

            try:
                numeric_value = float(value)
            except OverflowError as exc:
                raise ValueError(f"{feature} must be finite") from exc

            if not isfinite(numeric_value):
                raise ValueError(
                    f"{feature} must be finite"
                )

            cleaned[feature] = numeric_value

        # Preserve exact training feature order.
        X = pd.DataFrame(
            [cleaned],
            columns=self.features
        )

        score = float(
            self.model.predict_proba(X)[0, 1]
        )

        prediction = int(score >= self.threshold)

        return {
            "model": self.model_name,
            "prediction": prediction,
            "label": (
                "Attack" if prediction else "Benign"
            ),
            "attack_score": round(score, 6),
            "threshold": self.threshold,
        }
