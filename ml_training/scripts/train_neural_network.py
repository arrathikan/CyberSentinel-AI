"""
CyberAgent AI - Train Neural Network (MLP) Classifier

Trains a multi-layer perceptron neural network on the preprocessed training dataset.
"""

import os
from pathlib import Path
import joblib
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]

train_split = ROOT / "data/processed/train.csv"
cleaned_path = ROOT / "data/processed/cleaned_data.csv"

default_dataset = train_split if train_split.exists() else cleaned_path
data_path = Path(os.getenv("DATA_FILE", default_dataset))


def main():
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found at {data_path}")

    print(f"Loading data from: {data_path}")
    env_sample = os.getenv("SAMPLE_SIZE")
    nrows = int(env_sample) if env_sample and env_sample.isdigit() else None
    df = pd.read_csv(data_path, nrows=nrows)

    target_col = "binary_label" if "binary_label" in df.columns else "target"
    if target_col not in df.columns:
        raise ValueError(f"Target column not found in {data_path}")

    X = df.drop(columns=["label", "target", "binary_label"], errors="ignore")
    X = X.select_dtypes(include=["number"])
    y = df[target_col]

    if y.nunique() < 2:
        raise ValueError(f"Dataset slice contains only 1 class: {y.unique().tolist()}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"Training Neural Network (MLP) on {len(X_train):,} samples...")
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", MLPClassifier(
            hidden_layer_sizes=(64, 32),
            max_iter=100,
            random_state=42,
            early_stopping=True,
        )),
    ])

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    print("\nEvaluation:")
    print(classification_report(y_test, predictions, target_names=["Benign", "Attack"]))
    print(confusion_matrix(y_test, predictions))

    output_dir = ROOT / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "neural_network_model.pkl")
    print(f"\nModel saved to: {output_dir / 'neural_network_model.pkl'}")


if __name__ == "__main__":
    main()
