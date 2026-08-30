import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from feature_engineering import create_features


DATA_PATH = "data/raw/revenue_recovery.csv"


def build_preprocessor(X):
    categorical = X.select_dtypes(
        include=["object", "string", "category"]
    ).columns.tolist()

    numeric = X.select_dtypes(
        include=["int64", "float64", "int32", "float32"]
    ).columns.tolist()

    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(strategy="most_frequent"),
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
            ("num", numeric_pipeline, numeric),
            ("cat", categorical_pipeline, categorical),
        ],
        remainder="drop",
    )


def evaluate(name, model, X_train, X_test, y_train, y_test):
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    metrics = {
        "model": name,
        "accuracy": accuracy_score(y_test, predictions),
        "balanced_accuracy": balanced_accuracy_score(
            y_test, predictions
        ),
        "precision": precision_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "recall": recall_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "f1": f1_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "roc_auc": roc_auc_score(
            y_test,
            probabilities,
        ),
        "pr_auc": average_precision_score(
            y_test,
            probabilities,
        ),
    }

    print("\n======================================")
    print(name)
    print("======================================")

    for key, value in metrics.items():
        if key != "model":
            print(f"{key}: {value:.4f}")

    return metrics


def main():
    print("Loading dataset...")

    df = pd.read_csv(DATA_PATH)

    df = df[
        df["revenue_at_risk"] == 1
    ].copy()

    print(
        f"At-risk dataset shape: {df.shape}"
    )

    target = df["recovered"]

    drop_columns = [
        "transaction_id",
        "customer_id",
        "revenue_at_risk",
        "recovered",
        "money_recovered",
        "promise_to_pay",
    ]

    X_raw = df.drop(
        columns=drop_columns,
        errors="ignore",
    )

    print("\nCreating engineered features...")

    X_engineered = create_features(
        X_raw.copy()
    )

    print(
        "Engineered features:",
        [
            "customer_reliability",
            "payment_reliability",
            "customer_intent",
            "contactability",
            "recovery_friction",
        ],
    )

    (
        X_raw_train,
        X_raw_test,
        y_train,
        y_test,
    ) = train_test_split(
        X_raw,
        target,
        test_size=0.20,
        random_state=42,
        stratify=target,
    )

    (
        X_eng_train,
        X_eng_test,
        _,
        _,
    ) = train_test_split(
        X_engineered,
        target,
        test_size=0.20,
        random_state=42,
        stratify=target,
    )

    results = []

    # --------------------------------------------------
    # 1. RAW LOGISTIC REGRESSION
    # --------------------------------------------------

    raw_preprocessor = build_preprocessor(
        X_raw_train
    )

    raw_logistic = Pipeline(
        [
            ("preprocessor", raw_preprocessor),
            (
                "classifier",
                LogisticRegression(
                    max_iter=5000,
                    C=0.5,
                    class_weight=None,
                ),
            ),
        ]
    )

    results.append(
        evaluate(
            "RAW LOGISTIC REGRESSION",
            raw_logistic,
            X_raw_train,
            X_raw_test,
            y_train,
            y_test,
        )
    )

    # --------------------------------------------------
    # 2. ENGINEERED LOGISTIC REGRESSION
    # --------------------------------------------------

    engineered_preprocessor = build_preprocessor(
        X_eng_train
    )

    engineered_logistic = Pipeline(
        [
            (
                "preprocessor",
                engineered_preprocessor,
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=5000,
                    C=0.5,
                    class_weight=None,
                ),
            ),
        ]
    )

    results.append(
        evaluate(
            "ENGINEERED LOGISTIC REGRESSION",
            engineered_logistic,
            X_eng_train,
            X_eng_test,
            y_train,
            y_test,
        )
    )

    # --------------------------------------------------
    # 3. RANDOM FOREST
    # --------------------------------------------------

    rf_preprocessor = build_preprocessor(
        X_engineered
    )

    random_forest = Pipeline(
        [
            (
                "preprocessor",
                rf_preprocessor,
            ),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=400,
                    max_depth=8,
                    min_samples_leaf=5,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    results.append(
        evaluate(
            "RANDOM FOREST",
            random_forest,
            X_eng_train,
            X_eng_test,
            y_train,
            y_test,
        )
    )

    # --------------------------------------------------
    # 4. HISTOGRAM GRADIENT BOOSTING
    # --------------------------------------------------

    hgb_preprocessor = build_preprocessor(
        X_engineered
    )

    hist_gradient_boosting = Pipeline(
        [
            (
                "preprocessor",
                hgb_preprocessor,
            ),
            (
                "classifier",
                HistGradientBoostingClassifier(
                    max_iter=250,
                    learning_rate=0.05,
                    max_leaf_nodes=15,
                    min_samples_leaf=15,
                    l2_regularization=1.0,
                    random_state=42,
                ),
            ),
        ]
    )

    results.append(
        evaluate(
            "HISTOGRAM GRADIENT BOOSTING",
            hist_gradient_boosting,
            X_eng_train,
            X_eng_test,
            y_train,
            y_test,
        )
    )

    # --------------------------------------------------
    # COMPARISON
    # --------------------------------------------------

    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
        by=["roc_auc", "pr_auc"],
        ascending=False,
    )

    print("\n\n======================================")
    print("MODEL COMPARISON")
    print("======================================")

    print(
        results_df[
            [
                "model",
                "balanced_accuracy",
                "f1",
                "roc_auc",
                "pr_auc",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )

    output_path = (
        "models/recovery_model_comparison.csv"
    )

    results_df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"\nComparison saved to:\n{output_path}"
    )

    best = results_df.iloc[0]

    print("\n======================================")
    print("BEST EXPERIMENTAL MODEL")
    print("======================================")
    print(f"Model: {best['model']}")
    print(f"ROC-AUC: {best['roc_auc']:.4f}")
    print(f"PR-AUC: {best['pr_auc']:.4f}")
    print(
        f"Balanced Accuracy: "
        f"{best['balanced_accuracy']:.4f}"
    )


if __name__ == "__main__":
    main()
