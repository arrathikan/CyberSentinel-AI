import glob
import numpy as np
import pandas as pd

# 1. Locate all CSV files
files = glob.glob("archive-2/*.csv")

if not files:
    raise FileNotFoundError("No CSV files found in 'archive-2/' directory.")

print(f"Found {len(files)} CSV files. Loading...")

# 2. Read and combine
df_list = [pd.read_csv(file) for file in files]
df = pd.concat(df_list, ignore_index=True)

# 3. Standardize column names (strip whitespace, lowercase, snake_case)
df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

# 4. Handle infinite values and missing data
df = df.replace([np.inf, -np.inf], np.nan)
df = df.dropna()

# 5. Remove duplicates
df = df.drop_duplicates()

print("\n--- Dataset Summary ---")
print("Shape after cleaning:", df.shape)
print("\nClass Distribution:")
print(df['label'].value_counts())
