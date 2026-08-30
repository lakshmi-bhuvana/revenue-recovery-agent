def choose_action(transaction, score, diagnosis):
    """
    Select a bounded recovery action using:
    - revenue-loss scenario
    - diagnosed cause
    - ML recovery probability
    - priority
    """

    scenario = str(
        transaction.get("scenario", "")
    ).lower()

    failure_reason = str(
        transaction.get("failure_reason", "")
    ).lower()

    diagnosis_name = str(
        diagnosis.get("diagnosis", "")
    ).lower()

    priority = score["priority"]
    probability = score["recovery_probability"]

    # -----------------------------------------
    # RECOVERY STRATEGY
    # -----------------------------------------

    if priority == "HIGH":

        if probability >= 0.80:
            base_action = "aggressive_recovery"
        else:
            base_action = "assisted_recovery"

    elif priority == "MEDIUM":

        base_action = "standard_recovery"

    else:

        base_action = "low_cost_recovery"

    # -----------------------------------------
    # DIAGNOSIS-DRIVEN ACTION
    # -----------------------------------------

    if diagnosis_name == "payment_method_degradation":

        recovery_action = "alternative_payment_method"

    elif diagnosis_name == "insufficient_funds":

        recovery_action = "payment_reminder"

    elif diagnosis_name == "bank_decline":

        recovery_action = "retry_payment"

    elif diagnosis_name == "payment_timeout":

        recovery_action = "retry_payment"

    elif diagnosis_name == "authentication_failure":

        recovery_action = "authentication_retry"

    elif diagnosis_name == "payment_failure_mandate_issue":

        recovery_action = "mandate_reactivation"

    elif diagnosis_name == "checkout_abandonment":

        recovery_action = "checkout_reminder"

    elif diagnosis_name == "subscription_payment_failure":

        recovery_action = "subscription_reactivation"

    elif diagnosis_name == "mandate_failure":

        recovery_action = "mandate_reactivation"

    elif diagnosis_name == "overdue_receivable":

        recovery_action = "payment_reminder"

    # -----------------------------------------
    # FALLBACK
    # -----------------------------------------

    elif scenario == "payment_failure":

        if failure_reason == "insufficient_funds":
            recovery_action = "payment_reminder"

        elif failure_reason in (
            "bank_decline",
            "timeout"
        ):
            recovery_action = "retry_payment"

        elif failure_reason == "authentication_failed":
            recovery_action = "authentication_retry"

        else:
            recovery_action = "payment_recovery"

    elif scenario == "checkout_dropoff":

        recovery_action = "checkout_reminder"

    elif scenario == "failed_subscription":

        recovery_action = "subscription_reactivation"

    elif scenario == "mandate_failure":

        recovery_action = "mandate_reactivation"

    elif scenario == "overdue_receivable":

        recovery_action = "payment_reminder"

    else:

        recovery_action = "general_recovery"

    return {
        "strategy": base_action,
        "recovery_action": recovery_action,
        "channel": score["recommended_channel"],
        "priority": priority
    }