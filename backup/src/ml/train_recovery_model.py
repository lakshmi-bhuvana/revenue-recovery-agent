import pandas as pd
import joblib
import json

from feature_engineering import create_features
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix
)
# --------------------------------------------------
# 1. LOAD DATA
# --------------------------------------------------

df = pd.read_csv("data/raw/revenue_recovery.csv")

# Only cases where revenue is actually at risk
df = df[df["revenue_at_risk"] == 1].copy()

print("At-risk dataset shape:", df.shape)

# --------------------------------------------------
# 2. FEATURE ENGINEERING
# --------------------------------------------------

df = create_features(df)

print("\nEngineered features created:")
print([
    "customer_reliability",
    "payment_reliability",
    "customer_intent",
    "contactability",
    "recovery_friction"
])

# --------------------------------------------------
# 3. REMOVE DATA LEAKAGE
# --------------------------------------------------

drop_columns = [
    "transaction_id",
    "customer_id",
    "revenue_at_risk",
    "recovered",
    "money_recovered",
    "promise_to_pay"
]

X = df.drop(columns=drop_columns)
y = df["recovered"]

# --------------------------------------------------
# 4. IDENTIFY FEATURE TYPES
# --------------------------------------------------

categorical_features = X.select_dtypes(
    include=["object", "string"]
).columns.tolist()

numeric_features = X.select_dtypes(
    include=["int64", "float64"]
).columns.tolist()

print("\nCategorical features:")
print(categorical_features)

print("\nNumeric features:")
print(numeric_features)

# --------------------------------------------------
# 5. PREPROCESSING
# --------------------------------------------------

numeric_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

categorical_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer([
    ("num", numeric_pipeline, numeric_features),
    ("cat", categorical_pipeline, categorical_features)
])

# --------------------------------------------------
# 6. TRAIN / TEST SPLIT
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))

# --------------------------------------------------
# 7. LOGISTIC REGRESSION
# --------------------------------------------------

logistic_model = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", LogisticRegression(
        max_iter=1000,
        random_state=42
    ))
])

logistic_model.fit(X_train, y_train)

logistic_pred = logistic_model.predict(X_test)
logistic_prob = logistic_model.predict_proba(X_test)[:, 1]

# --------------------------------------------------
# 8. RANDOM FOREST
# --------------------------------------------------

random_forest_model = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1
    ))
])

random_forest_model.fit(X_train, y_train)

rf_pred = random_forest_model.predict(X_test)
rf_prob = random_forest_model.predict_proba(X_test)[:, 1]

# --------------------------------------------------
# 9. EVALUATION FUNCTION
# --------------------------------------------------

def evaluate_model(name, y_true, predictions, probabilities):

    accuracy = accuracy_score(y_true, predictions)
    precision = precision_score(
        y_true,
        predictions,
        zero_division=0
    )
    recall = recall_score(
        y_true,
        predictions,
        zero_division=0
    )
    f1 = f1_score(
        y_true,
        predictions,
        zero_division=0
    )
    auc = roc_auc_score(
        y_true,
        probabilities
    )
    pr_auc = average_precision_score(
        y_true,
        probabilities
    )
    balanced_accuracy = balanced_accuracy_score(
        y_true,
        predictions
    )

    cm = confusion_matrix(
        y_true,
        predictions
    )

    print("\n======================================")
    print(name)
    print("======================================")

    print(f"Accuracy:           {accuracy:.4f}")
    print(f"Balanced Accuracy:  {balanced_accuracy:.4f}")
    print(f"Precision:          {precision:.4f}")
    print(f"Recall:             {recall:.4f}")
    print(f"F1 Score:           {f1:.4f}")
    print(f"ROC-AUC:            {auc:.4f}")
    print(f"PR-AUC:             {pr_auc:.4f}")

    print("\nConfusion Matrix:")
    print(cm)

    print("\nTN:", cm[0][0])
    print("FP:", cm[0][1])
    print("FN:", cm[1][0])
    print("TP:", cm[1][1])

    return {
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": auc,
        "pr_auc": pr_auc,
        "confusion_matrix": cm.tolist(),
    }
# --------------------------------------------------
# 10. EVALUATE MODELS
# --------------------------------------------------

logistic_metrics = evaluate_model(
    "LOGISTIC REGRESSION",
    y_test,
    logistic_pred,
    logistic_prob
)

rf_metrics = evaluate_model(
    "RANDOM FOREST",
    y_test,
    rf_pred,
    rf_prob
)

# --------------------------------------------------
# 11. SELECT BEST MODEL
# --------------------------------------------------

# ROC-AUC measures ranking quality across thresholds.
if rf_metrics["roc_auc"] >= logistic_metrics["roc_auc"]:
    best_model = random_forest_model
    best_name = "Random Forest"
    best_metrics = rf_metrics
else:
    best_model = logistic_model
    best_name = "Logistic Regression"
    best_metrics = logistic_metrics

print("\n======================================")
print("BEST MODEL:", best_name)
print("======================================")
# --------------------------------------------------
# 12. SAVE EVALUATION METRICS
# --------------------------------------------------

evaluation = {
    "dataset": {
        "total_at_risk_cases": int(len(df)),
        "training_samples": int(len(X_train)),
        "testing_samples": int(len(X_test)),
    },
    "models": {
        "logistic_regression": logistic_metrics,
        "random_forest": rf_metrics,
    },
    "selected_model": best_name,
}

with open("models/recovery_model_metrics.json", "w") as f:
    json.dump(evaluation, f, indent=2)

print("Evaluation metrics saved to:")
print("models/recovery_model_metrics.json")

# 13. SAVE MODEL
# --------------------------------------------------

joblib.dump(
    best_model,
    "models/recovery_model.pkl"
)

print("\nModel saved to:")
print("models/recovery_model.pkl")
