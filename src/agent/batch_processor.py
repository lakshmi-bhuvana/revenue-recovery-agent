import pandas as pd

from src.ml.recovery_scorer import RecoveryScorer
from src.agent.action_policy import choose_action
from src.agent.message_generator import generate_message


def create_decision(transaction, scorer):

    # Score transaction
    score = scorer.score(transaction)

    # Select strategy/action
    action = choose_action(
        transaction,
        score
    )

    probability = score["recovery_probability"]
    amount = score["transaction_amount"]

    # Expected monetary value
    expected_recovery = amount * probability

    # Generate explanation
    reasons = []

    if probability >= 0.80:
        reasons.append("high recovery probability")
    elif probability >= 0.60:
        reasons.append("moderate recovery probability")
    else:
        reasons.append("low recovery probability")

    if score["customer_intent"] >= 0.80:
        reasons.append("high customer intent")

    if score["customer_reliability"] >= 0.80:
        reasons.append("high customer reliability")

    if score["contactability"] >= 2:
        reasons.append("strong contactability")

    if score["recovery_friction"] == 0:
        reasons.append("low recovery friction")

    reason = (
        f"{score['priority']} priority because of "
        + ", ".join(reasons)
        + "."
    )

    # Generate customer message
    message = generate_message(
        transaction,
        {
            "recommended_channel":
                score["recommended_channel"],
            "recovery_action":
                action["recovery_action"]
        }
    )

    return {
        "transaction_id":
            transaction["transaction_id"],

        "customer_id":
            transaction["customer_id"],

        "transaction_amount":
            amount,

        "recovery_probability":
            probability,

        "priority_score":
            score["priority_score"],

        "priority":
            score["priority"],

        "recommended_channel":
            score["recommended_channel"],

        "strategy":
            action["strategy"],

        "recovery_action":
            action["recovery_action"],

        "expected_recovery_value":
            round(expected_recovery, 2),

        "reason":
            reason,

        "message":
            message["message"]
    }


def main():

    print("Loading dataset...")

    df = pd.read_csv(
        "data/raw/revenue_recovery.csv"
    )

    # Only revenue-at-risk transactions
    df = df[
        df["revenue_at_risk"] == 1
    ].copy()

    print(
        f"At-risk transactions: {len(df)}"
    )

    # Load model once
    scorer = RecoveryScorer()

    decisions = []

    print("Generating agent decisions...")

    for _, transaction in df.iterrows():

        decision = create_decision(
            transaction.to_dict(),
            scorer
        )

        decisions.append(decision)

    decisions_df = pd.DataFrame(decisions)

    # Create output directory if needed
    import os

    os.makedirs(
        "data/processed",
        exist_ok=True
    )

    output_path = (
        "data/processed/"
        "recovery_decisions.csv"
    )

    decisions_df.to_csv(
        output_path,
        index=False
    )

    print("\n======================================")
    print("BATCH PROCESSING COMPLETE")
    print("======================================")

    print(
        "Decisions generated:",
        len(decisions_df)
    )

    print(
        "\nPriority distribution:"
    )

    print(
        decisions_df[
            "priority"
        ].value_counts()
    )

    print(
        "\nStrategy distribution:"
    )

    print(
        decisions_df[
            "strategy"
        ].value_counts()
    )

    print(
        "\nChannel distribution:"
    )

    print(
        decisions_df[
            "recommended_channel"
        ].value_counts()
    )

    print(
        "\nTotal transaction value: ₹",
        round(
            decisions_df[
                "transaction_amount"
            ].sum(),
            2
        )
    )

    print(
        "Total expected recovery: ₹",
        round(
            decisions_df[
                "expected_recovery_value"
            ].sum(),
            2
        )
    )

    print(
        "\nSaved to:",
        output_path
    )


if __name__ == "__main__":
    main()