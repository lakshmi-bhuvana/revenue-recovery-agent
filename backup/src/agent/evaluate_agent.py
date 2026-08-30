import pandas as pd


DATA_PATH = "data/raw/revenue_recovery.csv"
DECISIONS_PATH = "data/processed/recovery_decisions.csv"


def main():

    # -----------------------------------------
    # Load original outcomes
    # -----------------------------------------

    original = pd.read_csv(DATA_PATH)

    original = original[
        original["revenue_at_risk"] == 1
    ].copy()

    # -----------------------------------------
    # Load agent decisions
    # -----------------------------------------

    decisions = pd.read_csv(
        DECISIONS_PATH
    )

    # -----------------------------------------
    # Combine agent decisions with actual outcome
    # -----------------------------------------

    df = decisions.merge(
        original[
            [
                "transaction_id",
                "recovered",
                "money_recovered"
            ]
        ],
        on="transaction_id",
        how="left"
    )

    print("\n======================================")
    print("RECOVERY AGENT EVALUATION")
    print("======================================")

    # -----------------------------------------
    # Overall performance
    # -----------------------------------------

    print("\nOverall recovery rate:")

    print(
        round(
            df["recovered"].mean(),
            4
        )
    )

    print("\nActual money recovered:")

    print(
        "₹",
        round(
            df["money_recovered"].sum(),
            2
        )
    )

    print("\nExpected recovery:")

    print(
        "₹",
        round(
            df["expected_recovery_value"].sum(),
            2
        )
    )

    # -----------------------------------------
    # Priority performance
    # -----------------------------------------

    print("\n======================================")
    print("PERFORMANCE BY PRIORITY")
    print("======================================")

    priority_results = (
        df.groupby("priority")
        .agg(
            cases=(
                "transaction_id",
                "count"
            ),

            recovery_rate=(
                "recovered",
                "mean"
            ),

            actual_recovered=(
                "money_recovered",
                "sum"
            ),

            expected_recovery=(
                "expected_recovery_value",
                "sum"
            )
        )
        .sort_values(
            "recovery_rate",
            ascending=False
        )
    )

    print(priority_results)

    # -----------------------------------------
    # Strategy performance
    # -----------------------------------------

    print("\n======================================")
    print("PERFORMANCE BY STRATEGY")
    print("======================================")

    strategy_results = (
        df.groupby("strategy")
        .agg(
            cases=(
                "transaction_id",
                "count"
            ),

            recovery_rate=(
                "recovered",
                "mean"
            ),

            actual_recovered=(
                "money_recovered",
                "sum"
            ),

            expected_recovery=(
                "expected_recovery_value",
                "sum"
            )
        )
        .sort_values(
            "recovery_rate",
            ascending=False
        )
    )

    print(strategy_results)

    # -----------------------------------------
    # Probability buckets
    # -----------------------------------------

    df["probability_bucket"] = pd.cut(
        df["recovery_probability"],
        bins=[
            0,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0
        ],
        labels=[
            "<50%",
            "50-60%",
            "60-70%",
            "70-80%",
            "80-90%",
            "90-100%"
        ],
        include_lowest=True
    )

    print("\n======================================")
    print("PERFORMANCE BY RECOVERY PROBABILITY")
    print("======================================")

    probability_results = (
        df.groupby(
            "probability_bucket",
            observed=True
        )
        .agg(
            cases=(
                "transaction_id",
                "count"
            ),

            actual_recovery_rate=(
                "recovered",
                "mean"
            ),

            expected_recovery=(
                "expected_recovery_value",
                "sum"
            ),

            actual_recovered=(
                "money_recovered",
                "sum"
            )
        )
    )

    print(probability_results)

    # -----------------------------------------
    # Top-value opportunities
    # -----------------------------------------

    print("\n======================================")
    print("TOP 10 RECOVERY OPPORTUNITIES")
    print("======================================")

    top = (
        df.sort_values(
            "expected_recovery_value",
            ascending=False
        )
        [
            [
                "transaction_id",
                "transaction_amount",
                "recovery_probability",
                "priority",
                "strategy",
                "recommended_channel",
                "expected_recovery_value"
            ]
        ]
        .head(10)
    )

    print(top.to_string(index=False))

    # -----------------------------------------
    # Save evaluation dataset
    # -----------------------------------------

    output_path = (
        "data/processed/"
        "evaluated_decisions.csv"
    )

    df.to_csv(
        output_path,
        index=False
    )

    print("\nEvaluation dataset saved to:")
    print(output_path)


if __name__ == "__main__":
    main()