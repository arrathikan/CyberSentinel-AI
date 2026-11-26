import os
from pathlib import Path
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parents[2]

# Determine dataset path (prefer train.csv for speed & balance, or full cleaned dataset)
train_split = ROOT / "data/processed/train.csv"
cleaned_path = ROOT / "data/processed/cleaned_data.csv"
if not cleaned_path.exists():
    cleaned_path = ROOT / "data/cleaned_data.csv"

default_dataset = train_split if train_split.exists() else cleaned_path
data_path = Path(os.getenv("DATA_FILE", default_dataset))

if not data_path.exists():
    raise FileNotFoundError(f"Dataset not found at {data_path}")

print(f"Loading data from: {data_path}")

# Optional sample size override via environment variable SAMPLE_SIZE
env_sample = os.getenv("SAMPLE_SIZE")
nrows = int(env_sample) if env_sample and env_sample.isdigit() else None
if nrows:
    print(f"Subsampling {nrows:,} records for quick training...")
df = pd.read_csv(data_path, nrows=nrows)

# Determine target column
target_col = "binary_label" if "binary_label" in df.columns else "target"
if target_col not in df.columns:
    raise ValueError(f"Neither 'binary_label' nor 'target' found in {data_path}")

# Input features
X = df.drop(columns=["label", "target", "binary_label"], errors="ignore")
X = X.select_dtypes(include=["number"])

# Correct answers
y = df[target_col]

if y.nunique() < 2:
    raise ValueError(
        f"Dataset contains only 1 class ({y.unique().tolist()}). "
        "Ensure training data includes both benign and attack records."
    )

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

# Create ML pipeline
model = Pipeline([
    ("scaler", StandardScaler()),
    ("classifier", LogisticRegression(
        max_iter=2000,
        class_weight="balanced"
    ))
])

# Train model
model.fit(X_train, y_train)

# Predict using test data
predictions = model.predict(X_test)

# Evaluate
print(classification_report(y_test, predictions))
print(confusion_matrix(y_test, predictions))

# Save model
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/cyberattack_model.pkl")
joblib.dump(list(X.columns), "models/feature_columns.pkl")

print("Model trained and saved!")