import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
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
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)
from feature_engineering import create_features
# ============================================================
# PATHS
# ============================================================
DATA_PATH = Path(
    "data/raw/revenue_recovery.csv"
)
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)
METRICS_PATH = (
    MODEL_DIR /
    "recovery_model_metrics.json"
)
MODEL_PATH = (
    MODEL_DIR /
    "recovery_model.pkl"
)
# ============================================================
# CONFIGURATION
# ============================================================
RANDOM_STATE = 42
TEST_SIZE = 0.20
TARGET = "recovered"
# Threshold is selected using validation data only.
# The model probability itself is never modified.
THRESHOLD_MIN = 0.20
THRESHOLD_MAX = 0.80
THRESHOLD_STEP = 0.01
# ============================================================
# LOAD DATA
# ============================================================
df = pd.read_csv(
    DATA_PATH
)
# The Recovery Agent is concerned with cases already
# identified as revenue risk.
if "revenue_at_risk" not in df.columns:
    raise ValueError(
        "Column 'revenue_at_risk' is required."
    )
df = df[
    df["revenue_at_risk"] == 1
].copy()
print(
    "At-risk dataset shape:",
    df.shape
)
if TARGET not in df.columns:
    raise ValueError(
        f"Target column '{TARGET}' not found."
    )
# ============================================================
# FEATURE ENGINEERING
# ============================================================
df = create_features(
    df
)
print(
    "\nEngineered features created:"
)
print(
    [
        "customer_reliability",
        "payment_reliability",
        "customer_intent",
        "contactability",
        "recovery_friction",
    ]
)
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
y = (
    pd.to_numeric(
        df[TARGET],
        errors="coerce",
    )
    .fillna(0)
    .astype(int)
    .clip(
        0,
        1,
    )
)
if y.nunique() < 2:
    raise ValueError(
        "Target must contain both recovered and unrecovered cases."
    )
# ============================================================
# FEATURE TYPES
# ============================================================
categorical_features = (
    X.select_dtypes(
        include=[
            "object",
            "string",
            "category",
        ]
    )
    .columns
    .tolist()
)
numeric_features = (
    X.select_dtypes(
        include=[
            "number",
            "bool",
        ]
    )
    .columns
    .tolist()
)
print(
    "\nCategorical features:"
)
print(
    categorical_features
)
print(
    "\nNumeric features:"
)
print(
    numeric_features
)
# ============================================================
# PREPROCESSOR FACTORY
# ============================================================
def make_preprocessor():
    numeric_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                ),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ]
    )
    return ColumnTransformer(
        [
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
        ],
        remainder="drop",
    )
# ============================================================
# HOLDOUT SPLIT
# ============================================================
X_train, X_test, y_train, y_test = (
    train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )
)
print(
    "\nTraining samples:",
    len(X_train)
)
print(
    "Testing samples:",
    len(X_test)
)
positive_rate = float(
    y_test.mean()
)
print(
    f"Test-set recovery baseline: "
    f"{positive_rate:.4f}"
)
# ============================================================
# THRESHOLD SPLIT
#
# Test remains untouched until final evaluation.
# Threshold selection uses a validation split carved from
# the training population.
# ============================================================
X_fit, X_validation, y_fit, y_validation = (
    train_test_split(
        X_train,
        y_train,
        test_size=0.25,
        random_state=RANDOM_STATE,
        stratify=y_train,
    )
)
# ============================================================
# MODEL FACTORY
# ============================================================
def build_models():
    return {
        "Logistic Regression": Pipeline(
            [
                (
                    "preprocessor",
                    make_preprocessor(),
                ),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=2000,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "Random Forest": Pipeline(
            [
                (
                    "preprocessor",
                    make_preprocessor(),
                ),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=400,
                        max_depth=10,
                        min_samples_leaf=2,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "HistGradientBoosting": Pipeline(
            [
                (
                    "preprocessor",
                    make_preprocessor(),
                ),
                (
                    "classifier",
                    HistGradientBoostingClassifier(
                        max_iter=300,
                        learning_rate=0.05,
                        max_leaf_nodes=15,
                        l2_regularization=1.0,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }
# ============================================================
# METRIC EVALUATION
# ============================================================
def calculate_metrics(
    y_true,
    probabilities,
    threshold,
):
    predictions = (
        probabilities >= threshold
    ).astype(int)
    accuracy = accuracy_score(
        y_true,
        predictions,
    )
    balanced_accuracy = (
        balanced_accuracy_score(
            y_true,
            predictions,
        )
    )
    precision = precision_score(
        y_true,
        predictions,
        zero_division=0,
    )
    recall = recall_score(
        y_true,
        predictions,
        zero_division=0,
    )
    f1 = f1_score(
        y_true,
        predictions,
        zero_division=0,
    )
    roc_auc = roc_auc_score(
        y_true,
        probabilities,
    )
    pr_auc = average_precision_score(
        y_true,
        probabilities,
    )
    brier = brier_score_loss(
        y_true,
        probabilities,
    )
    cm = confusion_matrix(
        y_true,
        predictions,
    )
    return {
        "accuracy": round(
            float(accuracy),
            6,
        ),
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
        "threshold": round(
            float(threshold),
            4,
        ),
    }
# ============================================================
# THRESHOLD SEARCH
#
# Optimize F1 on validation data. This changes the binary
# action decision, NOT the probability generated by the model.
# ============================================================
def find_best_threshold(
    y_validation,
    probabilities,
):
    thresholds = np.arange(
        THRESHOLD_MIN,
        THRESHOLD_MAX + 0.0001,
        THRESHOLD_STEP,
    )
    best_threshold = 0.50
    best_score = -1.0
    for threshold in thresholds:
        predictions = (
            probabilities >= threshold
        ).astype(int)
        score = f1_score(
            y_validation,
            predictions,
            zero_division=0,
        )
        if score > best_score:
            best_score = score
            best_threshold = float(
                threshold
            )
    return (
        round(
            best_threshold,
            4,
        ),
        round(
            float(best_score),
            6,
        ),
    )
# ============================================================
# TRAIN + VALIDATE MODELS
# ============================================================
models = build_models()
validation_results = {}
test_results = {}
fitted_models = {}
print(
    "\n============================================================"
)
print(
    "MODEL BENCHMARK"
)
print(
    "============================================================"
)
for name, model in models.items():
    print(
        f"\nFitting {name}..."
    )
    model.fit(
        X_fit,
        y_fit,
    )
    validation_probabilities = (
        model.predict_proba(
            X_validation
        )[:, 1]
    )
    threshold, validation_f1 = (
        find_best_threshold(
            y_validation,
            validation_probabilities,
        )
    )
    validation_results[name] = {
        "best_threshold": threshold,
        "validation_f1": validation_f1,
    }
    # Refit on the FULL training set before touching test data.
    model.fit(
        X_train,
        y_train,
    )
    test_probabilities = (
        model.predict_proba(
            X_test
        )[:, 1]
    )
    test_metrics = calculate_metrics(
        y_test,
        test_probabilities,
        threshold,
    )
    test_results[name] = test_metrics
    fitted_models[name] = model
    print(
        f"  Threshold : {threshold:.2f}"
    )
    print(
        f"  Precision : {test_metrics['precision']:.4f}"
    )
    print(
        f"  Recall    : {test_metrics['recall']:.4f}"
    )
    print(
        f"  F1        : {test_metrics['f1']:.4f}"
    )
    print(
        f"  ROC-AUC   : {test_metrics['roc_auc']:.4f}"
    )
    print(
        f"  PR-AUC    : {test_metrics['pr_auc']:.4f}"
    )
    print(
        f"  Brier     : {test_metrics['brier_score']:.4f}"
    )
# ============================================================
# MODEL SELECTION
#
# Ranking:
# 1. ROC-AUC
# 2. PR-AUC
# 3. Brier Score (lower is better)
#
# We don't optimize solely for F1 because the Recovery Agent
# needs useful probability ranking for prioritization.
# ============================================================
ranking = []
for name, metrics in test_results.items():
    ranking.append(
        (
            name,
            metrics,
        )
    )
ranking.sort(
    key=lambda item: (
        item[1]["roc_auc"],
        item[1]["pr_auc"],
        -item[1]["brier_score"],
    ),
    reverse=True,
)
best_name = ranking[0][0]
best_model = fitted_models[
    best_name
]
best_metrics = test_results[
    best_name
]
best_threshold = validation_results[
    best_name
]["best_threshold"]
# ============================================================
# FINAL OUTPUT
# ============================================================
evaluation = {
    "evaluation_type": (
        "held_out_test_set_with_validation_threshold_selection"
    ),
    "description": (
        "Models were evaluated on the same stratified 20% "
        "holdout. Classification thresholds were selected "
        "using a validation split from the training population."
    ),
    "dataset": {
        "total_at_risk_cases": int(
            len(df)
        ),
        "training_samples": int(
            len(X_train)
        ),
        "validation_samples": int(
            len(X_validation)
        ),
        "testing_samples": int(
            len(X_test)
        ),
        "test_positive_rate": round(
            positive_rate,
            6,
        ),
    },
    "leakage_controls": {
        "excluded_from_features":
            existing_leakage_columns,
        "recovered_excluded":
            "recovered"
            in existing_leakage_columns,
        "money_recovered_excluded":
            "money_recovered"
            in existing_leakage_columns,
        "identifiers_excluded": (
            "transaction_id"
            in existing_leakage_columns
            and
            "customer_id"
            in existing_leakage_columns
        ),
        "future_outcome_fields_excluded": (
            "recovered"
            in existing_leakage_columns
            and
            "money_recovered"
            in existing_leakage_columns
        ),
    },
    "threshold_selection": {
        "method": "validation_f1",
        "min_threshold": THRESHOLD_MIN,
        "max_threshold": THRESHOLD_MAX,
        "step": THRESHOLD_STEP,
    },
    "models": {},
    "selected_model": best_name,
    "selected_model_metrics": best_metrics,
    "selected_decision_threshold": best_threshold,
}
for name in test_results:
    key = name.lower().replace(
        " ",
        "_",
    )
    evaluation["models"][key] = {
        "validation": validation_results[
            name
        ],
        "held_out_test": test_results[
            name
        ],
    }
# ============================================================
# SAVE
# ============================================================
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
# ============================================================
# DISPLAY FINAL RANKING
# ============================================================
print(
    "\n============================================================"
)
print(
    "FINAL MODEL RANKING"
)
print(
    "============================================================"
)
for index, (name, metrics) in enumerate(
    ranking,
    start=1,
):
    print(
        f"{index}. "
        f"{name:<24} "
        f"ROC-AUC={metrics['roc_auc']:.4f} "
        f"PR-AUC={metrics['pr_auc']:.4f} "
        f"Brier={metrics['brier_score']:.4f} "
        f"F1={metrics['f1']:.4f} "
        f"Threshold={metrics['threshold']:.2f}"
    )
print(
    "\n============================================================"
)
print(
    "SELECTED MODEL:",
    best_name,
)
print(
    "DECISION THRESHOLD:",
    best_threshold,
)
print(
    "============================================================"
)
print(
    "\nEvaluation metrics saved to:",
    METRICS_PATH,
)
print(
    "Production model saved to:",
    MODEL_PATH,
)