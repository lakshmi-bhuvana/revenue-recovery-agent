from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from feature_engineering import create_features
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data/raw/revenue_recovery.csv"
OUTPUT_PATH = BASE_DIR / "models/recovery_signal_audit.json"
df = pd.read_csv(DATA_PATH)
df = df[
    df["revenue_at_risk"] == 1
].copy()
df = create_features(df)
target = (
    pd.to_numeric(
        df["recovered"],
        errors="coerce"
    )
    .fillna(0)
    .astype(int)
)
leakage = [
    "transaction_id",
    "customer_id",
    "revenue_at_risk",
    "recovered",
    "money_recovered",
    "promise_to_pay",
]
features = [
    c for c in df.columns
    if c not in leakage
]
X = df[features]
numeric = (
    X.select_dtypes(include=["number", "bool"])
    .columns
    .tolist()
)
categorical = (
    X.select_dtypes(
        include=["object", "string", "category"]
    )
    .columns
    .tolist()
)
preprocessor = ColumnTransformer(
    [
        (
            "num",
            Pipeline(
                [
                    (
                        "imputer",
                        SimpleImputer(strategy="median"),
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
            "cat",
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
                random_state=42,
            ),
        ),
    ]
)
cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42,
)
model_scores = cross_val_score(
    model,
    X,
    target,
    cv=cv,
    scoring="roc_auc",
)
dummy = Pipeline(
    [
        (
            "preprocessor",
            preprocessor,
        ),
        (
            "classifier",
            DummyClassifier(
                strategy="prior"
            ),
        ),
    ]
)
dummy_scores = cross_val_score(
    dummy,
    X,
    target,
    cv=cv,
    scoring="roc_auc",
)
numeric_signal = []
for column in numeric:
    values = pd.to_numeric(
        X[column],
        errors="coerce"
    )
    if values.nunique(dropna=True) < 2:
        continue
    values = values.fillna(
        values.median()
    )
    try:
        auc = roc_auc_score(
            target,
            values
        )
        auc = max(
            auc,
            1.0 - auc
        )
        numeric_signal.append(
            {
                "feature": column,
                "absolute_univariate_auc":
                    round(float(auc), 6),
                "unique_values":
                    int(values.nunique()),
            }
        )
    except Exception:
        pass
numeric_signal.sort(
    key=lambda x:
        x["absolute_univariate_auc"],
    reverse=True,
)
class_counts = (
    target.value_counts()
    .sort_index()
    .to_dict()
)
missingness = {}
for column in features:
    missingness[column] = round(
        float(
            X[column].isna().mean()
        ),
        6,
    )
result = {
    "dataset": {
        "rows": int(len(df)),
        "features": int(len(features)),
        "positive_count": int(
            class_counts.get(1, 0)
        ),
        "negative_count": int(
            class_counts.get(0, 0)
        ),
        "positive_rate": round(
            float(target.mean()),
            6,
        ),
    },
    "cross_validation": {
        "folds": 5,
        "roc_auc_mean": round(
            float(model_scores.mean()),
            6,
        ),
        "roc_auc_std": round(
            float(model_scores.std()),
            6,
        ),
        "roc_auc_min": round(
            float(model_scores.min()),
            6,
        ),
        "roc_auc_max": round(
            float(model_scores.max()),
            6,
        ),
    },
    "dummy_baseline": {
        "roc_auc_mean": round(
            float(dummy_scores.mean()),
            6,
        ),
        "roc_auc_std": round(
            float(dummy_scores.std()),
            6,
        ),
    },
    "top_numeric_univariate_signal":
        numeric_signal[:15],
    "missingness":
        dict(
            sorted(
                missingness.items(),
                key=lambda x: -x[1],
            )
        ),
    "leakage_excluded":
        leakage,
}
OUTPUT_PATH.write_text(
    json.dumps(
        result,
        indent=2,
    ),
    encoding="utf-8",
)
print("=" * 72)
print("RECOVERY DATA SIGNAL AUDIT")
print("=" * 72)
print(
    f"Rows          : {len(df)}"
)
print(
    f"Features      : {len(features)}"
)
print(
    f"Recovered     : {class_counts.get(1, 0)}"
)
print(
    f"Unrecovered   : {class_counts.get(0, 0)}"
)
print(
    f"Positive rate : {target.mean():.4f}"
)
print()
print("5-FOLD LOGISTIC ROC-AUC")
print(
    f"Mean          : {model_scores.mean():.4f}"
)
print(
    f"Std           : {model_scores.std():.4f}"
)
print(
    f"Min           : {model_scores.min():.4f}"
)
print(
    f"Max           : {model_scores.max():.4f}"
)
print()
print("DUMMY BASELINE ROC-AUC")
print(
    f"Mean          : {dummy_scores.mean():.4f}"
)
print()
print("TOP NUMERIC SIGNAL")
print("-" * 72)
for item in numeric_signal[:15]:
    print(
        f"{item['feature']:<40} "
        f"AUC={item['absolute_univariate_auc']:.4f}"
    )
print()
print(
    "Saved to:",
    OUTPUT_PATH,
)
print("=" * 72)