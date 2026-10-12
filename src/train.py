import os
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

# Load cleaned data
df = pd.read_csv("data/cleaned_data.csv")

# Input features
X = df.drop(columns=["label", "target"])
X = X.select_dtypes(include=["number"])

# Correct answers
y = df["target"]

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