
"""
CyberAgent AI - Step 8 API Integration Test

Loads one preprocessed validation row and sends
its features to the local FastAPI prediction API.

This is an inference smoke test, not an accuracy
benchmark.
"""

import json
from pathlib import Path

import httpx
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

SELECTION_FILE = ROOT / "models/selected_model.json"
VALIDATION_FILE = ROOT / "data/processed/validation.csv"

API_URL = "http://127.0.0.1:8001/api/v1/predict"


def main():
    if not SELECTION_FILE.exists():
        raise FileNotFoundError(SELECTION_FILE)

    if not VALIDATION_FILE.exists():
        raise FileNotFoundError(VALIDATION_FILE)

    # Read the first validation record.
    df = pd.read_csv(VALIDATION_FILE, nrows=1)

    features = df.drop(columns=["binary_label"])

    # Convert to standard JSON-compatible values.
    payload = {
        "features": features.iloc[0].to_dict()
    }

    print("Sending validation record to CyberAgent API...")

    response = httpx.post(
        API_URL,
        json=payload,
        timeout=30.0,
    )

    response.raise_for_status()

    result = response.json()

    actual = int(df["binary_label"].iloc[0])

    print("\nAPI Response:")
    print(json.dumps(result, indent=2))

    print("\nActual Label:", actual)
    print("Predicted Label:", result["prediction"])

    print(
        "Single-record match:",
        result["prediction"] == actual
    )

    print("\nAPI inference test completed!")


if __name__ == "__main__":
    main()
