import glob
import os
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

# Find CSV files in archive-2 or data/raw
files = glob.glob(str(ROOT / "archive-2/*.csv"))
if not files:
    files = glob.glob(str(ROOT / "data/raw/*.csv"))

if not files:
    raise FileNotFoundError("No raw CSV files found in archive-2/ or data/raw/")

print(f"Loading {len(files)} dataset files for preprocessing...")
df = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)

# Standardize column names (removes leading/trailing spaces and converts to lowercase)
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

# Remove duplicate records
df = df.drop_duplicates()

# Replace infinite values with missing values
df = df.replace([np.inf, -np.inf], np.nan)

# Remove rows with missing values for the first version
df = df.dropna()

# Check available labels
if "label" in df.columns:
    print(df["label"].value_counts())

    # Convert labels into binary classes
    normal_labels = {"benign", "normal"}

    df["target"] = df["label"].astype(str).str.strip().str.lower().apply(
        lambda x: 0 if x in normal_labels else 1
    )

    print(df["target"].value_counts())

# Save cleaned dataset
output_dir = ROOT / "data" / "processed"
output_dir.mkdir(parents=True, exist_ok=True)
df.to_csv(output_dir / "cleaned_data.csv", index=False)
print(f"Cleaned dataset saved to: {output_dir / 'cleaned_data.csv'}")
