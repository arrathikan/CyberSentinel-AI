
import json
import joblib

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

from data_loader import load_data, MODELS_DIR, RESULTS_DIR


# 1. Load the dataset
X_train, X_val, X_test, y_train, y_val, y_test = load_data()


# 2. Create Random Forest model
model = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("classifier", RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    ))
])


# 3. Train the model
print("\nTraining Random Forest...")
model.fit(X_train, y_train)

print("Random Forest training completed!")


# 4. Make predictions on validation data
y_pred = model.predict(X_val)


# 5. Evaluate model performance
print("\n========== RANDOM FOREST RESULTS ==========")

accuracy = accuracy_score(y_val, y_pred)
precision = precision_score(y_val, y_pred, zero_division=0)
recall = recall_score(y_val, y_pred, zero_division=0)
f1 = f1_score(y_val, y_pred, zero_division=0)

print(f"Accuracy : {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall   : {recall:.4f}")
print(f"F1 Score : {f1:.4f}")

print("\nClassification Report:")
print(classification_report(
    y_val,
    y_pred,
    target_names=["Normal", "Attack"],
    zero_division=0
))

print("\nConfusion Matrix:")
print(confusion_matrix(y_val, y_pred, labels=[0, 1]))


# 6. Save evaluation metrics
metrics = {
    "model": "Random Forest",
    "accuracy": accuracy,
    "precision": precision,
    "recall": recall,
    "f1": f1
}

with open(RESULTS_DIR / "random_forest_metrics.json", "w") as f:
    json.dump(metrics, f, indent=4)


# 7. Save trained model and feature names
joblib.dump(
    model,
    MODELS_DIR / "random_forest.pkl"
)

joblib.dump(
    list(X_train.columns),
    MODELS_DIR / "feature_columns.pkl"
)


# 8. Check saved model
loaded_model = joblib.load(
    MODELS_DIR / "random_forest.pkl"
)

sample = X_val.iloc[[0]]
prediction = loaded_model.predict(sample)[0]
probability = loaded_model.predict_proba(sample)[0, 1]

print("\nSample Prediction:")
print("Prediction:", "Attack" if prediction == 1 else "Normal")
print(f"Attack Probability: {probability:.4f}")

print("\nRandom Forest model saved successfully!")
