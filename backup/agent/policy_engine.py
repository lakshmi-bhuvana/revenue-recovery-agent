MAX_RECOVERY_ATTEMPTS = 3

SUPPORTED_SCENARIOS = {
    "payment_failure",
    "checkout_dropoff",
    "failed_subscription",
    "mandate_failure",
    "overdue_receivable"
}


def check_policy(transaction, score, action):
    """
    Determines whether the proposed recovery action is permitted.
    """

    scenario = str(
        transaction.get("scenario", "")
    ).lower()

    attempts = int(
        transaction.get("recovery_attempts", 0) or 0
    )

    channel = score.get(
        "recommended_channel",
        "none"
    )

    if scenario not in SUPPORTED_SCENARIOS:

        return {
            "allowed": False,
            "reason": "unsupported_recovery_scenario"
        }

    if attempts >= MAX_RECOVERY_ATTEMPTS:

        return {
            "allowed": False,
            "reason": "maximum_recovery_attempts_reached"
        }

    if channel == "none":

        return {
            "allowed": False,
            "reason": "no_communication_channel_available"
        }

    if not action:

        return {
            "allowed": False,
            "reason": "no_recovery_action_selected"
        }

    return {
        "allowed": True,
        "reason": "action_within_recovery_policy"
    }