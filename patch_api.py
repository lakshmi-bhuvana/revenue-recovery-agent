from pathlib import Path

path = Path("src/api/main.py")

text = path.read_text(encoding="utf-8")

old = '''    calculated_probability = (
        calculate_recovery_probability(at_risk)
    )

    if "recovery_probability" not in at_risk.columns:
        at_risk["recovery_probability"] = (
            calculated_probability
        )
    else:
        existing = pd.to_numeric(
            at_risk["recovery_probability"],
            errors="coerce",
        )

        at_risk["recovery_probability"] = (
            existing.fillna(
                calculated_probability
            )
        )

    at_risk["recovery_probability"] = (
        at_risk["recovery_probability"]
        .clip(0, 1)
    )

    at_risk["expected_recovery_value"] = (
        at_risk["transaction_amount"]
        * at_risk["recovery_probability"]
    )

    calculated_intent = (
        calculate_customer_intent(at_risk)
    )

    if "customer_intent" not in at_risk.columns:
        at_risk["customer_intent"] = calculated_intent
    else:
        existing = pd.to_numeric(
            at_risk["customer_intent"],
            errors="coerce",
        )

        at_risk["customer_intent"] = (
            existing.fillna(calculated_intent)
        )

    at_risk["customer_intent"] = (
        at_risk["customer_intent"]
        .clip(0, 1)
    )

    at_risk["value_score"] = (
        calculate_value_score(at_risk)
    )

    calculated_priority = (
        calculate_priority_score(at_risk)
    )

    if "priority_score" not in at_risk.columns:
        at_risk["priority_score"] = calculated_priority
    else:
        existing = pd.to_numeric(
            at_risk["priority_score"],
            errors="coerce",
        )

        at_risk["priority_score"] = (
            existing.fillna(calculated_priority)
        )

    at_risk["priority_score"] = (
        at_risk["priority_score"]
        .clip(0, 1)
    )

    calculated_priority_label = assign_priority(
        at_risk["priority_score"]
    )

    if "priority" not in at_risk.columns:
        at_risk["priority"] = calculated_priority_label
    else:
        priority = (
            at_risk["priority"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        missing = priority == ""

        priority.loc[missing] = (
            calculated_priority_label.loc[missing]
        )

        at_risk["priority"] = priority
'''

new = '''    # --------------------------------------------------------
    # ML SCORING
    # --------------------------------------------------------
    # The trained RecoveryScorer is now the source of truth
    # for recovery probability and business priority.
    # --------------------------------------------------------

    scorer = RecoveryScorer()

    scored_rows = []

    for _, row in at_risk.iterrows():
        result = scorer.score(row.to_dict())
        scored_rows.append(result)

    scored_df = pd.DataFrame(scored_rows)

    at_risk["recovery_probability"] = (
        pd.to_numeric(
            scored_df["recovery_probability"],
            errors="coerce",
        ).clip(0, 1)
    )

    at_risk["expected_recovery_value"] = (
        at_risk["transaction_amount"]
        * at_risk["recovery_probability"]
    )

    at_risk["customer_intent"] = (
        pd.to_numeric(
            scored_df["customer_intent"],
            errors="coerce",
        ).clip(0, 1)
    )

    at_risk["customer_reliability"] = (
        pd.to_numeric(
            scored_df["customer_reliability"],
            errors="coerce",
        ).clip(0, 1)
    )

    at_risk["contactability"] = (
        pd.to_numeric(
            scored_df["contactability"],
            errors="coerce",
        ).clip(0, 1)
    )

    at_risk["recovery_friction"] = (
        pd.to_numeric(
            scored_df["recovery_friction"],
            errors="coerce",
        ).clip(0, 1)
    )

    at_risk["priority_score"] = (
        pd.to_numeric(
            scored_df["priority_score"],
            errors="coerce",
        ).clip(0, 1)
    )

    at_risk["priority"] = (
        scored_df["priority"]
        .fillna("LOW")
        .astype(str)
        .str.strip()
        .str.upper()
    )
'''

if old not in text:
    raise RuntimeError(
        "TARGET SCORING BLOCK NOT FOUND. "
        "No changes were made."
    )

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("API ML scoring integration completed.")