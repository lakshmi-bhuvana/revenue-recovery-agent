from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.calibration import calibration_curve
from feature_engineering import create_features
warnings.filterwarnings("ignore")
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data/raw/revenue_recovery.csv"
OUTPUT_PATH = BASE_DIR / "models/recovery_model_cv_evaluation.json"
TARGET = "recovered"
RANDOM_STATE = 42
FOLDS = 5
# ============================================================
# LOAD + FILTER
# ============================================================
df = pd.read_csv(DATA_PATH)
df = df[
    df["revenue_at_risk"] == 1
].copy()
df = create_features(df)
# ============================================================
# LEAKAGE CONTROL
# ============================================================
LEAKAGE_COLUMNS = {
    "transaction_id",
    "customer_id",
    "revenue_at_risk",
    "recovered",
    "money_recovered",
    "promise_to_pay",
}
drop_columns = [
    c for c in LEAKAGE_COLUMNS
    if c in df.columns
]
X = df.drop(
    columns=drop_columns,
    errors="ignore",
)
y = (
    pd.to_numeric(
        df[TARGET],
        errors="coerce",
    )
    .fillna(0)
    .astype(int)
)
# ============================================================
# FEATURE TYPES
# ============================================================
categorical = (
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
numeric = (
    X.select_dtypes(
        include=[
            "number",
            "bool",
        ]
    )
    .columns
    .tolist()
)
# ============================================================
# PIPELINE
# ============================================================
preprocessor = ColumnTransformer(
    [
        (
            "numeric",
            Pipeline(
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
            ),
            numeric,
        ),
        (
            "categorical",
            Pipeline(
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
            ),
            categorical,
        ),
    ]
)
model = Pipeline(
    [
        (
            "preprocessor",
            preprocessor,
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=2000,
                random_state=RANDOM_STATE,
            ),
        ),
    ]
)
# ============================================================
# 5-FOLD OUT-OF-FOLD PREDICTIONS
# ============================================================
cv = StratifiedKFold(
    n_splits=FOLDS,
    shuffle=True,
    random_state=RANDOM_STATE,
)
probabilities = cross_val_predict(
    model,
    X,
    y,
    cv=cv,
    method="predict_proba",
)[:, 1]
# ============================================================
# THRESHOLD ANALYSIS
# ============================================================
threshold_rows = []
for threshold in np.arange(
    0.20,
    0.81,
    0.01,
):
    predictions = (
        probabilities >= threshold
    ).astype(int)
    threshold_rows.append(
        {
            "threshold": round(
                float(threshold),
                2,
            ),
            "precision": round(
                float(
                    precision_score(
                        y,
                        predictions,
                        zero_division=0,
                    )
                ),
                6,
            ),
            "recall": round(
                float(
                    recall_score(
                        y,
                        predictions,
                        zero_division=0,
                    )
                ),
                6,
            ),
            "f1": round(
                float(
                    f1_score(
                        y,
                        predictions,
                        zero_division=0,
                    )
                ),
                6,
            ),
            "predicted_positive_rate": round(
                float(
                    predictions.mean()
                ),
                6,
            ),
        }
    )
best_threshold = max(
    threshold_rows,
    key=lambda x: (
        x["f1"],
        x["recall"],
        x["precision"],
    ),
)
# ============================================================
# GLOBAL METRICS
# ============================================================
roc_auc = roc_auc_score(
    y,
    probabilities,
)
pr_auc = average_precision_score(
    y,
    probabilities,
)
brier = brier_score_loss(
    y,
    probabilities,
)
predictions = (
    probabilities >= best_threshold["threshold"]
).astype(int)
precision = precision_score(
    y,
    predictions,
    zero_division=0,
)
recall = recall_score(
    y,
    predictions,
    zero_division=0,
)
f1 = f1_score(
    y,
    predictions,
    zero_division=0,
)
# ============================================================
# CALIBRATION
# ============================================================
fraction_positive, mean_predicted = (
    calibration_curve(
        y,
        probabilities,
        n_bins=10,
        strategy="quantile",
    )
)
calibration_points = []
for predicted, observed in zip(
    mean_predicted,
    fraction_positive,
):
    calibration_points.append(
        {
            "mean_predicted_probability":
                round(
                    float(predicted),
                    6,
                ),
            "observed_recovery_rate":
                round(
                    float(observed),
                    6,
                ),
        }
    )
# ============================================================
# OUTPUT
# ============================================================
result = {
    "evaluation_type": (
        "5_fold_stratified_out_of_fold_evaluation"
    ),
    "dataset": {
        "rows": int(len(df)),
        "features": int(X.shape[1]),
        "positive_rate": round(
            float(y.mean()),
            6,
        ),
    },
    "leakage_controls": {
        "excluded_columns": sorted(
            drop_columns
        ),
    },
    "cross_validation": {
        "folds": FOLDS,
        "shuffle": True,
        "random_state": RANDOM_STATE,
    },
    "metrics": {
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
        "precision_at_selected_threshold":
            round(
                float(precision),
                6,
            ),
        "recall_at_selected_threshold":
            round(
                float(recall),
                6,
            ),
        "f1_at_selected_threshold":
            round(
                float(f1),
                6,
            ),
    },
    "threshold_selection": {
        "method": (
            "maximum validation-style F1 "
            "from out-of-fold predictions"
        ),
        "selected_threshold":
            best_threshold,
        "analysis": threshold_rows,
    },
    "calibration": {
        "bins": calibration_points,
    },
}
OUTPUT_PATH.write_text(
    json.dumps(
        result,
        indent=2,
    ),
    encoding="utf-8",
)
# ============================================================
# PRINT
# ============================================================
print()
print("=" * 72)
print("RECOVERY MODEL 5-FOLD EVALUATION")
print("=" * 72)
print(
    f"Rows       : {len(df)}"
)
print(
    f"Features   : {X.shape[1]}"
)
print(
    f"Folds      : {FOLDS}"
)
print(
    f"ROC-AUC    : {roc_auc:.4f}"
)
print(
    f"PR-AUC     : {pr_auc:.4f}"
)
print(
    f"Brier      : {brier:.4f}"
)
print(
    f"Precision  : {precision:.4f}"
)
print(
    f"Recall     : {recall:.4f}"
)
print(
    f"F1         : {f1:.4f}"
)
print()
print(
    "SELECTED THRESHOLD:"
)
print(
    f"Threshold  : "
    f"{best_threshold['threshold']:.2f}"
)
print(
    f"Precision  : "
    f"{best_threshold['precision']:.4f}"
)
print(
    f"Recall     : "
    f"{best_threshold['recall']:.4f}"
)
print(
    f"F1         : "
    f"{best_threshold['f1']:.4f}"
)
print(
    f"Positive % : "
    f"{best_threshold['predicted_positive_rate'] * 100:.2f}%"
)
print()
print(
    "Saved to:",
    OUTPUT_PATH,
)
print("=" * 72)