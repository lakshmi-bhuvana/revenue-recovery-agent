import pandas as pd

from src.ml.recovery_scorer import RecoveryScorer
from src.agent.action_policy import choose_action
from src.agent.message_generator import generate_message


def create_recovery_decision(transaction, scorer):
    """
    Convert a transaction into a complete recovery decision.
    """

    # 1. Score transaction
    score = scorer.score(transaction)

    # 2. Choose recovery strategy/action
    action = choose_action(
        transaction,
        score
    )

    # 3. Expected monetary recovery
    probability = score["recovery_probability"]
    amount = score["transaction_amount"]

    expected_recovery = amount * probability

    # 4. Explain decision
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

    # 5. Generate customer message
    message = generate_message(
        transaction,
        {
            "recommended_channel":
                score["recommended_channel"],
            "recovery_action":
                action["recovery_action"]
        }
    )

    # 6. Complete decision
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


if __name__ == "__main__":

    # Load dataset
    df = pd.read_csv(
        "data/raw/revenue_recovery.csv"
    )

    # Only process revenue-at-risk cases
    df = df[
        df["revenue_at_risk"] == 1
    ]

    # Initialize scorer
    scorer = RecoveryScorer()

    # Test first at-risk transaction
    transaction = df.iloc[0].to_dict()

    # Generate complete decision
    decision = create_recovery_decision(
        transaction,
        scorer
    )

    print("\n======================================")
    print("RECOVERY AGENT DECISION")
    print("======================================")

    for key, value in decision.items():
        print(f"{key}: {value}")