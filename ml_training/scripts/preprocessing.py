import glob
import os
import pandas as pd
import numpy as np

files = glob.glob("archive-2/*.csv")
df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

# Standardize column names (removes leading/trailing spaces and converts to lowercase)
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

# Remove duplicate records
df = df.drop_duplicates()

# Replace infinite values with missing values
df = df.replace([np.inf, -np.inf], np.nan)

# Remove rows with missing values for the first version
df = df.dropna()

# Check available labels
print(df["label"].value_counts())

# Convert labels into binary classes
normal_labels = {"benign", "normal"}

df["target"] = df["label"].astype(str).str.strip().str.lower().apply(
    lambda x: 0 if x in normal_labels else 1
)

print(df["target"].value_counts())

# Save cleaned dataset
os.makedirs("data", exist_ok=True)
df.to_csv("data/cleaned_data.csv", index=False)