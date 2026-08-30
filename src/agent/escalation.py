
MAX_RECOVERY_ATTEMPTS = 3


def check_escalation(
    transaction,
    score,
    policy,
    execution,
    stopping,
    action=None,
):
    """
    Determines whether a revenue-recovery case
    should be escalated to a human/team.

    Escalation rules:

    HIGH priority:
        Escalate after the first failed attempt.

    MEDIUM priority:
        Allow up to 3 recovery attempts.
        Escalate after the third failed attempt.

    LOW priority:
        Allow up to 3 recovery attempts.
        Escalate after the third failed attempt.

    Other safety conditions such as policy blocks,
    unavailable communication channels, and successful
    recovery are handled separately.
    """

    attempts = int(
        transaction.get(
            "recovery_attempts",
            0
        ) or 0
    )

    priority = str(
        (action or {}).get(
            "priority",
            "MEDIUM"
        )
    ).upper()

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
    # 2. POLICY BLOCK
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
    # 3. NO COMMUNICATION CHANNEL
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
    # 4. HIGH PRIORITY
    #
    # HIGH priority gets only ONE attempt.
    # If that attempt fails, escalate.
    # -----------------------------------------

    if priority == "HIGH":

        if attempts >= 1:

            return {
                "escalate": True,
                "escalation_level": "HIGH",
                "reason": "high_priority_recovery_attempt_failed",
                "recommended_team": "revenue_operations"
            }

        return {
            "escalate": False,
            "escalation_level": "NONE",
            "reason": "high_priority_recovery_can_continue",
            "recommended_team": None
        }

    # -----------------------------------------
    # 5. MEDIUM / LOW PRIORITY
    #
    # Allow 3 attempts.
    # Escalate only after attempt 3 fails.
    # -----------------------------------------

    if priority in ("MEDIUM", "LOW"):

        if attempts >= MAX_RECOVERY_ATTEMPTS:

            return {
                "escalate": True,
                "escalation_level": priority,
                "reason": (
                    "maximum_recovery_attempts_reached"
                ),
                "recommended_team": "revenue_operations"
            }

        return {
            "escalate": False,
            "escalation_level": "NONE",
            "reason": "recovery_attempt_failed_automation_can_continue",
            "recommended_team": None
        }

    # -----------------------------------------
    # 6. UNKNOWN PRIORITY
    #
    # Safe fallback: use the 3-attempt rule.
    # -----------------------------------------

    if attempts >= MAX_RECOVERY_ATTEMPTS:

        return {
            "escalate": True,
            "escalation_level": "MEDIUM",
            "reason": "maximum_recovery_attempts_reached",
            "recommended_team": "revenue_operations"
        }

    return {
        "escalate": False,
        "escalation_level": "NONE",
        "reason": "automation_can_continue",
        "recommended_team": None
    }
