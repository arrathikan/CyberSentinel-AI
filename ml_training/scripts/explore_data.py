
"""
CyberAgent AI - Step 3
Explore the CSE-CIC-IDS2018 network-flow dataset.

This script:
1. Loads a sample of the original CSV.
2. Displays rows, columns, and data types.
3. Checks labels and missing values.
4. Detects infinite numeric values.
5. Saves a text exploration report.

No ML model is trained in this script.
"""

from pathlib import Path

import numpy as np
import pandas as pd


# Project root: CyberAgent-AI/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Original downloaded CSV
DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv"
)

# Output report
REPORT_PATH = (
    PROJECT_ROOT
    / "reports"
    / "dataset_exploration.txt"
)

# Load only the first 50,000 rows for exploration.
# This reduces memory usage on macOS.
SAMPLE_ROWS = 50_000


def main():
    print("======================================")
    print("  CYBERAGENT AI - DATASET EXPLORATION")
    print("======================================")

    if not DATA_PATH.is_file():
        print(f"\nDataset not found: {DATA_PATH}")
        print("Please complete the dataset download first.")
        return

    # 1. Read a limited sample of the original CSV
    df = pd.read_csv(
        DATA_PATH,
        nrows=SAMPLE_ROWS,
        low_memory=False
    )

    # 2. Clean whitespace from column names
    df.columns = df.columns.str.strip()

    print("\n[1] FIRST FIVE ROWS")
    print(df.head().to_string())

    print("\n[2] DATASET SAMPLE SHAPE")
    print(f"Rows loaded: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")

    print("\n[3] ALL COLUMN NAMES")
    for index, column in enumerate(df.columns, start=1):
        print(f"{index}. {column}")

    print("\n[4] COLUMN DATA TYPES")
    print(df.dtypes.to_string())

    print("\n[5] LABEL DISTRIBUTION")

    if "Label" not in df.columns:
        raise ValueError(
            "The dataset does not contain a 'Label' column."
        )

    # Normalize label whitespace for reporting only.
    df["Label"] = df["Label"].astype("string").str.strip()

    print(
        df["Label"].value_counts(
            dropna=False
        ).to_string()
    )

    print("\n[6] MISSING VALUES")
    missing = df.isna().sum()
    missing = missing[missing > 0]

    if missing.empty:
        print("No missing values in the loaded sample.")
    else:
        print(missing.to_string())

    print("\n[7] INFINITE NUMERIC VALUES")

    numeric_df = df.select_dtypes(include="number")
    inf_count = np.isinf(
        numeric_df.to_numpy(dtype=np.float64)
    ).sum()

    print(f"Infinite values: {inf_count}")

    print("\n[8] DUPLICATE ROWS")
    duplicates = df.duplicated().sum()
    print(f"Duplicate rows: {duplicates}")

    print("\n[9] NUMERIC FEATURE SUMMARY")
    print(numeric_df.describe().to_string())

    # Save the important findings.
    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(REPORT_PATH, "w", encoding="utf-8") as report:
        report.write("CYBERAGENT AI DATASET REPORT\n")
        report.write("============================\n\n")

        report.write(f"Source: {DATA_PATH.name}\n")
        report.write(
            f"Rows analyzed: {len(df)} (first rows only)\n"
        )
        report.write(f"Columns: {len(df.columns)}\n\n")

        report.write("COLUMN NAMES\n")
        report.write("\n".join(df.columns))
        report.write("\n\n")

        report.write("LABEL DISTRIBUTION\n")
        report.write(
            df["Label"]
            .value_counts(dropna=False)
            .to_string()
        )
        report.write("\n\n")

        report.write("MISSING VALUES\n")
        report.write(missing.to_string())
        report.write("\n\n")

        report.write(
            f"Infinite numeric values: {inf_count}\n"
        )
        report.write(f"Duplicate rows: {duplicates}\n")

    print("\nDataset exploration completed!")
    print(f"Report saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
