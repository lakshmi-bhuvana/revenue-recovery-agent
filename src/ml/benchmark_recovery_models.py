from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier,
    HistGradientBoostingClassifier,
)
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
warnings.filterwarnings("ignore")
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "revenue_recovery.csv"
)
OUTPUT_PATH = (
    BASE_DIR
    / "models"
    / "recovery_model_benchmark.json"
)
TARGET = "recovered"
LEAKAGE_COLUMNS = {
    "recovered",
    "money_recovered",
    "transaction_id",
    "customer_id",
    "recovery_probability",
    "expected_recovery_value",
}
TEST_SIZE = 0.20
RANDOM_STATE = 42
def clean_target(series):
    return (
        pd.to_numeric(series, errors="coerce")
        .fillna(0)
        .astype(int)
        .clip(0, 1)
    )
def prepare_data(df):
    df = df.copy()
    if TARGET not in df.columns:
        raise ValueError(
            f"Target column '{TARGET}' was not found. "
            f"Available columns: {list(df.columns)}"
        )
    y = clean_target(df[TARGET])
    drop_columns = [
        c
        for c in LEAKAGE_COLUMNS
        if c in df.columns
    ]
    X = df.drop(
        columns=drop_columns,
        errors="ignore",
    )
    # Remove completely empty columns.
    X = X.dropna(
        axis=1,
        how="all",
    )
    # Treat booleans as numeric.
    for column in X.columns:
        if X[column].dtype == bool:
            X[column] = (
                X[column]
                .astype(int)
            )
    return X, y
def make_preprocessor(X):
    numeric_columns = (
        X.select_dtypes(
            include=[
                "number",
                "bool",
            ]
        )
        .columns
        .tolist()
    )
    categorical_columns = (
        X.select_dtypes(
            exclude=[
                "number",
                "bool",
            ]
        )
        .columns
        .tolist()
    )
    numeric_pipeline = Pipeline(
        steps=[
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
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                ),
            ),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ]
    )
    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                numeric_columns,
            ),
            (
                "categorical",
                categorical_pipeline,
                categorical_columns,
            ),
        ],
        remainder="drop",
    )
def evaluate_model(
    name,
    model,
    X_train,
    X_test,
    y_train,
    y_test,
):
    pipeline = Pipeline(
        steps=[
            (
                "preprocess",
                make_preprocessor(X_train),
            ),
            (
                "model",
                model,
            ),
        ]
    )
    pipeline.fit(
        X_train,
        y_train,
    )
    predictions = pipeline.predict(
        X_test
    )
    probabilities = pipeline.predict_proba(
        X_test
    )[:, 1]
    result = {
        "model": name,
        "precision": round(
            precision_score(
                y_test,
                predictions,
                zero_division=0,
            ),
            6,
        ),
        "recall": round(
            recall_score(
                y_test,
                predictions,
                zero_division=0,
            ),
            6,
        ),
        "f1": round(
            f1_score(
                y_test,
                predictions,
                zero_division=0,
            ),
            6,
        ),
        "roc_auc": round(
            roc_auc_score(
                y_test,
                probabilities,
            ),
            6,
        ),
        "pr_auc": round(
            average_precision_score(
                y_test,
                probabilities,
            ),
            6,
        ),
        "brier_score": round(
            brier_score_loss(
                y_test,
                probabilities,
            ),
            6,
        ),
    }
    return result, pipeline
def try_xgboost():
    try:
        from xgboost import XGBClassifier
        return XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=RANDOM_STATE,
        )
    except Exception:
        return None
def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )
    df = pd.read_csv(DATA_PATH)
    X, y = prepare_data(df)
    if y.nunique() < 2:
        raise ValueError(
            "The target contains fewer than two classes."
        )
    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=TEST_SIZE,
            stratify=y,
            random_state=RANDOM_STATE,
        )
    )
    models = {
        "Logistic Regression": LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=400,
            max_depth=None,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.05,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=RANDOM_STATE,
        ),
    }
    xgb_model = try_xgboost()
    if xgb_model is not None:
        models["XGBoost"] = xgb_model
    results = []
    fitted_models = {}
    print()
    print("=" * 78)
    print("RECOVERY MODEL BENCHMARK")
    print("=" * 78)
    print(f"Dataset rows: {len(df)}")
    print(f"Features used: {X.shape[1]}")
    print(f"Training rows: {len(X_train)}")
    print(f"Test rows: {len(X_test)}")
    print(
        "Excluded leakage:",
        ", ".join(
            sorted(
                LEAKAGE_COLUMNS.intersection(
                    df.columns
                )
            )
        ),
    )
    print("=" * 78)
    for name, model in models.items():
        print()
        print(f"Evaluating {name}...")
        metrics, pipeline = evaluate_model(
            name,
            model,
            X_train,
            X_test,
            y_train,
            y_test,
        )
        results.append(metrics)
        fitted_models[name] = pipeline
        print(
            f"  Precision : {metrics['precision']:.4f}"
        )
        print(
            f"  Recall    : {metrics['recall']:.4f}"
        )
        print(
            f"  F1        : {metrics['f1']:.4f}"
        )
        print(
            f"  ROC-AUC   : {metrics['roc_auc']:.4f}"
        )
        print(
            f"  PR-AUC    : {metrics['pr_auc']:.4f}"
        )
        print(
            f"  Brier     : {metrics['brier_score']:.4f}"
        )
    results_sorted = sorted(
        results,
        key=lambda x: (
            x["roc_auc"],
            x["pr_auc"],
            -x["brier_score"],
        ),
        reverse=True,
    )
    best = results_sorted[0]
    payload = {
        "dataset_rows": int(len(df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "feature_count": int(X.shape[1]),
        "target": TARGET,
        "excluded_leakage_columns": sorted(
            LEAKAGE_COLUMNS.intersection(
                df.columns
            )
        ),
        "selection_rule": (
            "Primary: ROC-AUC; "
            "secondary: PR-AUC; "
            "tertiary: lower Brier Score."
        ),
        "models": results_sorted,
        "best_model": best["model"],
    }
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    OUTPUT_PATH.write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )
    print()
    print("=" * 78)
    print("RANKING")
    print("=" * 78)
    for index, item in enumerate(
        results_sorted,
        start=1,
    ):
        print(
            f"{index}. "
            f"{item['model']:<24} "
            f"ROC-AUC={item['roc_auc']:.4f} "
            f"PR-AUC={item['pr_auc']:.4f} "
            f"Brier={item['brier_score']:.4f}"
        )
    print("=" * 78)
    print(
        f"BEST MODEL: {best['model']}"
    )
    print(
        f"Benchmark saved to: {OUTPUT_PATH}"
    )
if __name__ == "__main__":
    main()