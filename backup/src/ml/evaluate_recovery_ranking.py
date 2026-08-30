import pandas as pd

from sklearn.metrics import roc_auc_score, average_precision_score

from recovery_scorer import RecoveryScorer


DATA_PATH = "data/raw/revenue_recovery.csv"


def main():
    print("Loading at-risk dataset...")

    df = pd.read_csv(DATA_PATH)

    df = df[
        df["revenue_at_risk"] == 1
    ].copy()

    print(f"At-risk cases: {len(df)}")

    scorer = RecoveryScorer()

    print("\nScoring transactions...")

    results = []

    for _, row in df.iterrows():
        result = scorer.score(row.to_dict())

        results.append(
            {
                "transaction_id": row["transaction_id"],
                "recovered": int(row["recovered"]),
                "transaction_amount": float(
                    row["transaction_amount"]
                ),
                "recovery_probability": float(
                    result["recovery_probability"]
                ),
                "priority_score": float(
                    result["priority_score"]
                ),
                "priority": result["priority"],
            }
        )

    scored = pd.DataFrame(results)

    # --------------------------------------------------
    # OVERALL RANKING QUALITY
    # --------------------------------------------------

    roc_auc = roc_auc_score(
        scored["recovered"],
        scored["recovery_probability"],
    )

    pr_auc = average_precision_score(
        scored["recovered"],
        scored["recovery_probability"],
    )

    print("\n======================================")
    print("OVERALL RANKING QUALITY")
    print("======================================")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"PR-AUC:  {pr_auc:.4f}")

    # --------------------------------------------------
    # TOP-PERCENTILE ANALYSIS
    # --------------------------------------------------

    scored = scored.sort_values(
        "recovery_probability",
        ascending=False,
    ).reset_index(drop=True)

    total_cases = len(scored)
    total_recovered = scored["recovered"].sum()

    print("\n======================================")
    print("TOP-SCORE RECOVERY ANALYSIS")
    print("======================================")

    for percentage in [10, 20, 30, 50, 100]:

        n = max(
            1,
            int(total_cases * percentage / 100),
        )

        top = scored.head(n)

        recovery_rate = top["recovered"].mean()

        recovered_cases = top["recovered"].sum()

        revenue = top[
            "transaction_amount"
        ].sum()

        recovered_revenue = top.loc[
            top["recovered"] == 1,
            "transaction_amount",
        ].sum()

        case_capture = (
            recovered_cases / total_recovered
        )

        revenue_capture = (
            recovered_revenue
            / scored.loc[
                scored["recovered"] == 1,
                "transaction_amount",
            ].sum()
        )

        print(
            f"\nTop {percentage}%"
        )

        print(
            f"Cases:              {n}"
        )

        print(
            f"Recovery rate:      {recovery_rate:.4f}"
        )

        print(
            f"Recovered cases:    {recovered_cases}"
        )

        print(
            f"Recovered-case capture: "
            f"{case_capture:.4f}"
        )

        print(
            f"Revenue capture:    "
            f"{revenue_capture:.4f}"
        )

        print(
            f"Revenue worked:     "
            f"{revenue:,.2f}"
        )

        print(
            f"Revenue recovered:  "
            f"{recovered_revenue:,.2f}"
        )

    # --------------------------------------------------
    # PRIORITY GROUP ANALYSIS
    # --------------------------------------------------

    print("\n======================================")
    print("PRIORITY GROUP ANALYSIS")
    print("======================================")

    priority_summary = (
        scored.groupby("priority")
        .agg(
            cases=("recovered", "count"),
            recovery_rate=("recovered", "mean"),
            revenue=("transaction_amount", "sum"),
        )
        .reindex(
            ["HIGH", "MEDIUM", "LOW"]
        )
    )

    print(
        priority_summary.to_string(
            float_format=lambda x: f"{x:.4f}"
        )
    )

    # --------------------------------------------------
    # SAVE RESULTS
    # --------------------------------------------------

    output = (
        "models/recovery_ranking_evaluation.csv"
    )

    scored.to_csv(
        output,
        index=False,
    )

    print(
        f"\nDetailed results saved to:\n{output}"
    )


if __name__ == "__main__":
    main()

