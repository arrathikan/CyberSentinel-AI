import os
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

# Directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"

# Ensure output directories exist
MODELS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_data(
    data_path=None,
    test_size=0.15,
    val_size=0.15,
    sample_size=None,
    random_state=42
):
    """
    Loads and splits dataset into Train, Validation, and Test sets.

    Parameters:
    - data_path: Path to the cleaned CSV file (default: data/cleaned_data.csv).
    - test_size: Proportion of dataset to include in the test split (default: 0.15).
    - val_size: Proportion of dataset to include in the validation split (default: 0.15).
    - sample_size: Optional integer to subsample the dataset (useful for faster training).
    - random_state: Seed for reproducible random splits (default: 42).

    Returns:
    - X_train, X_val, X_test, y_train, y_val, y_test
    """
    if data_path is None:
        data_path = DATA_DIR / "cleaned_data.csv"
    else:
        data_path = Path(data_path)

    # Optional sample size override via environment variable SAMPLE_SIZE
    env_sample = os.getenv("SAMPLE_SIZE")
    if env_sample and sample_size is None:
        try:
            sample_size = int(env_sample)
        except ValueError:
            pass

    print(f"Loading dataset from: {data_path}...")
    df = pd.read_csv(data_path)

    if sample_size and sample_size < len(df):
        print(f"Sampling {sample_size:,} records for training/evaluation...")
        df = df.sample(n=sample_size, random_state=random_state)

    X = df.drop(columns=["label", "target"], errors="ignore")
    X = X.select_dtypes(include=["number"])
    y = df["target"]

    # First split: train + validation vs test
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y
    )

    # Second split: train vs validation
    relative_val_size = val_size / (1.0 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp,
        test_size=relative_val_size,
        random_state=random_state,
        stratify=y_temp
    )

    print(f"Data successfully split:")
    print(f"  Training set   : {X_train.shape[0]:,} samples ({X_train.shape[1]} features)")
    print(f"  Validation set : {X_val.shape[0]:,} samples")
    print(f"  Test set       : {X_test.shape[0]:,} samples")

    return X_train, X_val, X_test, y_train, y_val, y_test
