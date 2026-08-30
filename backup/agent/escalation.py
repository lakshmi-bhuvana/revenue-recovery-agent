MAX_RECOVERY_ATTEMPTS = 3

HIGH_VALUE_THRESHOLD = 25000


def check_escalation(
    transaction,
    score,
    policy,
    execution,
    stopping
):
    """
    Determines whether a revenue-recovery case
    should be escalated to a human/team.
    """

    attempts = int(
        transaction.get(
            "recovery_attempts",
            0
        ) or 0
    )

    transaction_amount = float(
        transaction.get(
            "transaction_amount",
            0
        ) or 0
    )

    # -----------------------------------------
    # 1. ALREADY RECOVERED
    # -----------------------------------------

    if execution.get("recovered"):

        return {
            "escalate": False,
            "escalation_level": "NONE",
            "reason": "payment_recovered",
            "recommended_team": None
        }

    # -----------------------------------------
    # 2. MAXIMUM RECOVERY ATTEMPTS
    # -----------------------------------------

    if attempts >= MAX_RECOVERY_ATTEMPTS:

        return {
            "escalate": True,
            "escalation_level": "HIGH",
            "reason": "maximum_recovery_attempts_reached",
            "recommended_team": "revenue_operations"
        }

    # -----------------------------------------
    # 3. POLICY BLOCK
    # -----------------------------------------

    if not policy.get("allowed", True):

        return {
            "escalate": True,
            "escalation_level": "HIGH",
            "reason": policy.get(
                "reason",
                "recovery_action_blocked"
            ),
            "recommended_team": "revenue_operations"
        }

    # -----------------------------------------
    # 4. NO COMMUNICATION CHANNEL
    # -----------------------------------------

    if (
        score.get("recommended_channel")
        == "none"
    ):

        return {
            "escalate": True,
            "escalation_level": "MEDIUM",
            "reason": "no_communication_channel_available",
            "recommended_team": "customer_support"
        }

    # -----------------------------------------
    # 5. HIGH-VALUE CASE WITH LOW
    #    RECOVERY PROBABILITY
    # -----------------------------------------

    recovery_probability = float(
        score.get(
            "recovery_probability",
            0
        ) or 0
    )

    if (
        transaction_amount >= HIGH_VALUE_THRESHOLD
        and recovery_probability < 0.40
    ):

        return {
            "escalate": True,
            "escalation_level": "HIGH",
            "reason": (
                "high_value_case_with_low_recovery_probability"
            ),
            "recommended_team": "revenue_operations"
        }

    # -----------------------------------------
    # 6. FAILED RECOVERY ACTION
    # -----------------------------------------

    if (
        execution.get("recovered") is False
        and attempts > 0
    ):

        return {
            "escalate": True,
            "escalation_level": "MEDIUM",
            "reason": "recovery_attempt_failed",
            "recommended_team": "revenue_operations"
        }

    # -----------------------------------------
    # 7. NO ESCALATION
    # -----------------------------------------

    return {
        "escalate": False,
        "escalation_level": "NONE",
        "reason": "automated_recovery_can_continue",
        "recommended_team": None
    }