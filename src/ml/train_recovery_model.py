import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from feature_engineering import create_features
DATA_PATH = Path("data/raw/revenue_recovery.csv")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
METRICS_PATH = MODEL_DIR / "recovery_model_metrics.json"
MODEL_PATH = MODEL_DIR / "recovery_model.pkl"
df = pd.read_csv(DATA_PATH)
df = df[
    df["revenue_at_risk"] == 1
].copy()
print("At-risk dataset shape:", df.shape)
# ============================================================
# FEATURE ENGINEERING
# ============================================================
df = create_features(df)
print("\nEngineered features created:")
print([
    "customer_reliability",
    "payment_reliability",
    "customer_intent",
    "contactability",
    "recovery_friction",
])
# ============================================================
# LEAKAGE CONTROL
# ============================================================
leakage_columns = [
    "transaction_id",
    "customer_id",
    "revenue_at_risk",
    "recovered",
    "money_recovered",
    "promise_to_pay",
]
existing_leakage_columns = [
    column
    for column in leakage_columns
    if column in df.columns
]
X = df.drop(
    columns=existing_leakage_columns
)
y = pd.to_numeric(
    df["recovered"],
    errors="coerce",
).fillna(0).astype(int)
# ============================================================
# FEATURE TYPES
# ============================================================
categorical_features = X.select_dtypes(
    include=["object", "string"]
).columns.tolist()
numeric_features = X.select_dtypes(
    include=["int64", "float64", "int32", "float32"]
).columns.tolist()
print("\nCategorical features:")
print(categorical_features)
print("\nNumeric features:")
print(numeric_features)
# ============================================================
# PREPROCESSING
# ============================================================
numeric_pipeline = Pipeline([
    (
        "imputer",
        SimpleImputer(strategy="median"),
    ),
    (
        "scaler",
        StandardScaler(),
    ),
])
categorical_pipeline = Pipeline([
    (
        "imputer",
        SimpleImputer(strategy="most_frequent"),
    ),
    (
        "encoder",
        OneHotEncoder(handle_unknown="ignore"),
    ),
])
preprocessor = ColumnTransformer([
    (
        "num",
        numeric_pipeline,
        numeric_features,
    ),
    (
        "cat",
        categorical_pipeline,
        categorical_features,
    ),
])
# ============================================================
# HOLDOUT SPLIT
# ============================================================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y,
)
print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))
positive_rate = float(y_test.mean())
print(
    f"Test-set recovery baseline: "
    f"{positive_rate:.4f}"
)
# ============================================================
# MODELS
# ============================================================
logistic_model = Pipeline([
    (
        "preprocessor",
        preprocessor,
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=1000,
            random_state=42,
        ),
    ),
])
random_forest_model = Pipeline([
    (
        "preprocessor",
        preprocessor,
    ),
    (
        "classifier",
        RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1,
        ),
    ),
])
# ============================================================
# EVALUATION
# ============================================================
def evaluate_model(
    name,
    model,
    X_test,
    y_test,
):
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]
    accuracy = accuracy_score(
        y_test,
        predictions,
    )
    balanced_accuracy = balanced_accuracy_score(
        y_test,
        predictions,
    )
    precision = precision_score(
        y_test,
        predictions,
        zero_division=0,
    )
    recall = recall_score(
        y_test,
        predictions,
        zero_division=0,
    )
    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0,
    )
    roc_auc = roc_auc_score(
        y_test,
        probabilities,
    )
    pr_auc = average_precision_score(
        y_test,
        probabilities,
    )
    brier = brier_score_loss(
        y_test,
        probabilities,
    )
    cm = confusion_matrix(
        y_test,
        predictions,
    )
    print("\n======================================")
    print(name)
    print("======================================")
    print(f"Accuracy:           {accuracy:.4f}")
    print(f"Balanced Accuracy:  {balanced_accuracy:.4f}")
    print(f"Precision:          {precision:.4f}")
    print(f"Recall:             {recall:.4f}")
    print(f"F1 Score:           {f1:.4f}")
    print(f"ROC-AUC:            {roc_auc:.4f}")
    print(f"PR-AUC:             {pr_auc:.4f}")
    print(f"Brier Score:        {brier:.4f}")
    print("\nConfusion Matrix:")
    print(cm)
    return {
        "accuracy": round(float(accuracy), 6),
        "balanced_accuracy": round(
            float(balanced_accuracy),
            6,
        ),
        "precision": round(
            float(precision),
            6,
        ),
        "recall": round(
            float(recall),
            6,
        ),
        "f1": round(
            float(f1),
            6,
        ),
        "roc_auc": round(
            float(roc_auc),
            6,
        ),
        "pr_auc": round(
            float(pr_auc),
            6,
        ),
        "brier_score": round(
            float(brier),
            6,
        ),
        "positive_prediction_rate": round(
            float(predictions.mean()),
            6,
        ),
        "confusion_matrix": cm.tolist(),
    }
print("\nFitting Logistic Regression...")
logistic_model.fit(
    X_train,
    y_train,
)
logistic_metrics = evaluate_model(
    "LOGISTIC REGRESSION",
    logistic_model,
    X_test,
    y_test,
)
print("\nFitting Random Forest...")
random_forest_model.fit(
    X_train,
    y_train,
)
rf_metrics = evaluate_model(
    "RANDOM FOREST",
    random_forest_model,
    X_test,
    y_test,
)
# ============================================================
# MODEL SELECTION
# ============================================================
if rf_metrics["roc_auc"] >= logistic_metrics["roc_auc"]:
    best_model = random_forest_model
    best_name = "Random Forest"
    best_metrics = rf_metrics
else:
    best_model = logistic_model
    best_name = "Logistic Regression"
    best_metrics = logistic_metrics
# ============================================================
# SAVE EVALUATION
# ============================================================
evaluation = {
    "evaluation_type": "held_out_test_set",
    "description": (
        "Metrics are calculated on a stratified 20% holdout "
        "that was not used to fit the selected model."
    ),
    "dataset": {
        "total_at_risk_cases": int(len(df)),
        "training_samples": int(len(X_train)),
        "testing_samples": int(len(X_test)),
        "test_positive_rate": round(
            positive_rate,
            6,
        ),
    },
    "leakage_controls": {
        "excluded_from_features": existing_leakage_columns,
        "recovered_excluded": "recovered" in existing_leakage_columns,
        "money_recovered_excluded": "money_recovered" in existing_leakage_columns,
        "identifiers_excluded": (
            "transaction_id" in existing_leakage_columns
            and "customer_id" in existing_leakage_columns
        ),
        "future_outcome_fields_excluded": (
            "recovered" in existing_leakage_columns
            and "money_recovered" in existing_leakage_columns
        ),
    },
    "models": {
        "logistic_regression": logistic_metrics,
        "random_forest": rf_metrics,
    },
    "selected_model": best_name,
    "selected_model_metrics": best_metrics,
}
with open(
    METRICS_PATH,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        evaluation,
        file,
        indent=2,
    )
joblib.dump(
    best_model,
    MODEL_PATH,
)
print("\n======================================")
print("BEST MODEL:", best_name)
print("======================================")
print(
    "Evaluation metrics saved to:",
    METRICS_PATH,
)
print(
    "Model saved to:",
    MODEL_PATH,
)