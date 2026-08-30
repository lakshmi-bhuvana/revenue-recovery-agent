def execute_action(transaction, action, channel):
    """
    Simulated execution layer.

    This does not charge customers or send real messages.
    It simulates whether the recovery action succeeds so that
    the complete agent workflow can be evaluated.
    """

    amount = float(
        transaction.get("transaction_amount", 0) or 0
    )

    already_recovered = int(
        transaction.get("recovered", 0) or 0
    )

    if already_recovered == 1:
        return {
            "execution_status": "skipped",
            "action": action,
            "channel": channel,
            "attempt_increment": 0,
            "message_sent": False,
            "recovered": True,
            "money_recovered": float(
                transaction.get("money_recovered", 0) or 0
            ),
            "execution_detail": "Payment was already recovered."
        }

    # -----------------------------------------
    # SIMULATED RECOVERY PROBABILITY
    # -----------------------------------------

    recovery_probability = float(
        transaction.get(
            "_recovery_probability",
            0
        )
    )

    # Deterministic simulation:
    # recovery occurs when the model probability
    # crosses the threshold.
    recovered = recovery_probability >= 0.70

    if recovered:
        money_recovered = amount
        detail = (
            f"Recovery succeeded through {action} "
            f"using {channel}."
        )
    else:
        money_recovered = 0.0
        detail = (
            f"Recovery action {action} was executed "
            f"through {channel}, but payment remains pending."
        )

    return {
        "execution_status": "simulated",
        "action": action,
        "channel": channel,
        "attempt_increment": 1,
        "message_sent": channel != "none",
        "recovered": recovered,
        "money_recovered": money_recovered,
        "execution_detail": detail
    }