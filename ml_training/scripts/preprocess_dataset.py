
"""
CyberAgent AI - Step 4
Dataset preparation for binary intrusion detection.

Operations:
1. Read the CSV in chunks.
2. Sample records across the source file.
3. Normalize column names and labels.
4. Parse timestamps.
5. Split chronologically.
6. Convert features to numeric values.
7. Fit missing-value replacements on training data only.
8. Save datasets and preprocessing metadata.

This is an experimental, single-day split.
Not a final cross-day model evaluation.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

PRIMARY_RAW_FILE = (
    ROOT / "data/raw"
    / "Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv"
)

# Use primary 2018 file if available, otherwise fallback to existing CSVs in data/raw
if PRIMARY_RAW_FILE.is_file():
    RAW_FILE = PRIMARY_RAW_FILE
else:
    wednesday_fallback = ROOT / "data/raw" / "Wednesday-workingHours.pcap_ISCX.csv"
    if wednesday_fallback.is_file():
        RAW_FILE = wednesday_fallback
    else:
        raw_files = sorted((ROOT / "data/raw").glob("*.csv"))
        RAW_FILE = raw_files[0] if raw_files else PRIMARY_RAW_FILE


OUTPUT_DIR = ROOT / "data/processed"
REPORT_FILE = ROOT / "reports/preprocessing_report.json"

CHUNK_SIZE = 100_000
SAMPLE_EVERY = 10

# Identifiers and timing fields must not be ML inputs.
EXCLUDED_FEATURES = {
    "label",
    "binary_label",
    "timestamp",
    "flow id",
    "src ip",
    "dst ip",
    "source ip",
    "destination ip",
    "src port",
    "source port",
}


def load_sample():
    """Read rows across the full source CSV in chunks."""

    parts = []
    total_rows = 0

    for chunk in pd.read_csv(
        RAW_FILE,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ):
        chunk.columns = chunk.columns.str.strip()

        # Reject duplicate column names.
        if not chunk.columns.is_unique:
            raise ValueError(
                "Duplicate column names found after trimming."
            )

        # Select every tenth row using global positions.
        positions = np.arange(
            total_rows,
            total_rows + len(chunk)
        )

        selected = chunk.loc[
            positions % SAMPLE_EVERY == 0
        ]

        parts.append(selected.copy())
        total_rows += len(chunk)

        print(f"Read {total_rows:,} original rows")

    if not parts:
        raise ValueError("The source CSV contains no rows.")

    df = pd.concat(parts, ignore_index=True)

    print(f"\nSampled rows: {len(df):,}")
    return df, total_rows


def prepare_labels(df):
    """Preserve original labels and create binary labels."""

    if "Label" not in df.columns:
        raise ValueError("Missing required Label column.")

    df = df.copy()

    labels = df["Label"].astype("string").str.strip()

    valid = labels.notna() & labels.ne("")
    df = df.loc[valid].copy()

    labels = labels.loc[valid]

    df["Label"] = labels

    df["binary_label"] = (
        labels.str.upper().ne("BENIGN")
    ).astype(int)

    return df


def prepare_timestamps(df):
    """Parse timestamps and sort chronologically."""

    if "Timestamp" not in df.columns:
        raise ValueError(
            "Timestamp column is required for time splitting."
        )

    df = df.copy()

    # Day-first date interpretation for this dataset.
    df["_time"] = pd.to_datetime(
        df["Timestamp"].astype("string").str.strip(),
        dayfirst=True,
        errors="coerce",
    )

    invalid = int(df["_time"].isna().sum())

    if invalid:
        raise ValueError(
            f"{invalid} timestamps could not be parsed. "
            "Inspect their original format before continuing."
        )

    df = df.sort_values(
        "_time",
        kind="stable"
    ).reset_index(drop=True)

    return df


def split_chronologically(df):
    """Create train, validation and test partitions."""

    n = len(df)

    if n < 100:
        raise ValueError("Not enough records to split.")

    train_end = int(n * 0.60)
    val_end = int(n * 0.80)

    train = df.iloc[:train_end].copy()
    validation = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:].copy()

    # Prevent records with identical timestamps
    # appearing on both sides of a split.
    if (
        train["_time"].max() >= validation["_time"].min()
        or validation["_time"].max() >= test["_time"].min()
    ):
        raise ValueError(
            "A split boundary crosses identical timestamps. "
            "Use a timestamp-group-aware split."
        )

    return train, validation, test


def split_stratified(df):
    """Create train, validation and test partitions using stratified sampling."""
    from sklearn.model_selection import train_test_split

    n = len(df)
    if n < 100:
        raise ValueError("Not enough records to split.")

    train, temp = train_test_split(
        df,
        test_size=0.40,
        random_state=42,
        stratify=df["binary_label"],
    )
    validation, test = train_test_split(
        temp,
        test_size=0.50,
        random_state=42,
        stratify=temp["binary_label"],
    )

    return (
        train.reset_index(drop=True),
        validation.reset_index(drop=True),
        test.reset_index(drop=True),
    )



def get_features(df):
    """Choose numeric candidate features by column name."""

    feature_columns = [
        col
        for col in df.columns
        if col.lower() not in EXCLUDED_FEATURES
        and col != "_time"
        and not col.lower().startswith("unnamed:")
    ]

    if not feature_columns:
        raise ValueError("No candidate features found.")

    return feature_columns


def convert_features(df, columns):
    """Convert features to numerical format."""

    result = df[columns].copy()

    for column in columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce"
        )

    # Infinity is not a valid ML input.
    result = result.replace(
        [np.inf, -np.inf],
        np.nan
    )

    return result


def check_labels(name, df):
    """Ensure that both classes exist in every split."""

    counts = df["binary_label"].value_counts()

    print(f"\n{name} label distribution:")
    print(counts.to_string())

    if set(counts.index.tolist()) != {0, 1}:
        raise ValueError(
            f"{name} does not contain both classes. "
            "A single capture day may not support a "
            "representative chronological evaluation. "
            "Additional capture days or an explicitly "
            "grouped evaluation design are needed."
        )

    return {
        str(label): int(count)
        for label, count in counts.items()
    }


def main():
    if not RAW_FILE.is_file():
        raise FileNotFoundError(RAW_FILE)

    print("CYBERAGENT AI - PREPROCESSING\n")

    df, original_count = load_sample()

    df = prepare_labels(df)
    has_timestamp = "Timestamp" in df.columns

    if has_timestamp:
        df = prepare_timestamps(df)
        train, validation, test = split_chronologically(df)
        split_method = "chronological_60_20_20"
    else:
        print("\n'Timestamp' column not present in dataset. Performing stratified 60/20/20 train/validation/test split.")
        train, validation, test = split_stratified(df)
        split_method = "stratified_random_60_20_20"

    print("\nOriginal label counts:")
    print(df["Label"].value_counts().to_string())


    train_counts = check_labels("Train", train)
    val_counts = check_labels("Validation", validation)
    test_counts = check_labels("Test", test)

    feature_columns = get_features(df)

    x_train = convert_features(train, feature_columns)
    x_val = convert_features(validation, feature_columns)
    x_test = convert_features(test, feature_columns)

    # Fit missing-value replacements only on train.
    train_medians = x_train.median(axis=0)

    # Training columns that are entirely missing
    # cannot provide a usable median.
    usable = train_medians.notna()

    feature_columns = train_medians.index[
        usable
    ].tolist()

    if not feature_columns:
        raise ValueError("No usable numeric features.")

    medians = train_medians.loc[feature_columns]

    x_train = x_train[feature_columns].fillna(medians)
    x_val = x_val[feature_columns].fillna(medians)
    x_test = x_test[feature_columns].fillna(medians)

    partitions = {
        "train": (train, x_train),
        "validation": (validation, x_val),
        "test": (test, x_test),
    }

    # Build outputs in memory first.
    prepared = {}

    for name, (original, features) in partitions.items():
        output = features.copy()
        output["binary_label"] = (
            original["binary_label"].to_numpy()
        )
        prepared[name] = output

    report = {
        "source_file": RAW_FILE.name,
        "original_rows_read": original_count,
        "sampled_rows_after_label_cleaning": len(df),
        "sample_every": SAMPLE_EVERY,
        "split_method": split_method,
        "important_limitations": [
            "Single capture day",
            "Deterministic every-nth-row sampling",
            "Possible correlation across attack sessions",
            "Not an independent cross-day test",
        ],
        "rows": {
            name: len(data)
            for name, data in prepared.items()
        },
        "class_distribution": {
            "train": train_counts,
            "validation": val_counts,
            "test": test_counts,
        },
        "features": feature_columns,
        "imputation_medians": {
            name: float(value)
            for name, value in medians.items()
        },
        "timestamp_ranges": (
            {
                name: {
                    "first": original["_time"].min().isoformat(),
                    "last": original["_time"].max().isoformat(),
                }
                for name, (original, _) in partitions.items()
            }
            if has_timestamp
            else "Not applicable (no Timestamp column; stratified split used)"
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    for name, data in prepared.items():
        output_path = OUTPUT_DIR / f"{name}.csv"
        data.to_csv(output_path, index=False)

        print(f"\nSaved: {output_path}")
        print(f"Rows: {len(data):,}")

    REPORT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print(f"\nFeatures retained: {len(feature_columns)}")
    print(f"Report saved: {REPORT_FILE}")
    print("\nSTEP 4 PREPROCESSING COMPLETED!")


if __name__ == "__main__":
    main()
