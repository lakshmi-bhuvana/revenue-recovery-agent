def choose_action(transaction, score):

    scenario = transaction.get("scenario")
    failure_reason = transaction.get("failure_reason")

    priority = score["priority"]
    probability = score["recovery_probability"]

    # -----------------------------------------
    # HIGH PRIORITY
    # -----------------------------------------

    if priority == "HIGH":

        if probability >= 0.80:
            base_action = "aggressive_recovery"
        else:
            base_action = "assisted_recovery"

    # -----------------------------------------
    # MEDIUM PRIORITY
    # -----------------------------------------

    elif priority == "MEDIUM":

        base_action = "standard_recovery"

    # -----------------------------------------
    # LOW PRIORITY
    # -----------------------------------------

    else:

        base_action = "low_cost_recovery"

    # -----------------------------------------
    # SCENARIO-SPECIFIC ACTION
    # -----------------------------------------

    if scenario == "payment_failure":

        if failure_reason == "insufficient_funds":
            recovery_action = "payment_reminder"

        elif failure_reason == "bank_decline":
            recovery_action = "retry_payment"

        elif failure_reason == "authentication_failed":
            recovery_action = "authentication_retry"

        elif failure_reason == "timeout":
            recovery_action = "retry_payment"

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