
def execute_action(transaction, action, channel):
    """
    Simulated execution layer.

    This does not charge customers or send real messages.
    It simulates whether the recovery action succeeds so that
    the complete agent workflow can be evaluated.

    Optional test override:
        transaction["_force_recovery_failure"] = True

    When enabled, the recovery attempt intentionally fails.
    This is useful for testing escalation behavior without
    changing the normal recovery simulation logic.
    """

    amount = float(
        transaction.get(
            "transaction_amount",
            0
        ) or 0
    )

    already_recovered = int(
        transaction.get(
            "recovered",
            0
        ) or 0
    )

    # -----------------------------------------
    # ALREADY RECOVERED
    # -----------------------------------------

    if already_recovered == 1:
        return {
            "execution_status": "skipped",
            "action": action,
            "channel": channel,
            "attempt_increment": 0,
            "message_sent": False,
            "recovered": True,
            "money_recovered": float(
                transaction.get(
                    "money_recovered",
                    0
                ) or 0
            ),
            "execution_detail": (
                "Payment was already recovered."
            )
        }

    # -----------------------------------------
    # SIMULATED RECOVERY PROBABILITY
    # -----------------------------------------

    recovery_probability = float(
        transaction.get(
            "_recovery_probability",
            0
        ) or 0
    )

    # -----------------------------------------
    # TEST OVERRIDE
    # -----------------------------------------

    force_failure = bool(
        transaction.get(
            "_force_recovery_failure",
            False
        )
    )

    if force_failure:
        recovered = False
    else:
        # Normal deterministic simulation:
        # recovery occurs when model probability
        # crosses the threshold.
        recovered = recovery_probability >= 0.70

    # -----------------------------------------
    # RECOVERY RESULT
    # -----------------------------------------

    if recovered:

        money_recovered = amount

        detail = (
            f"Recovery succeeded through {action} "
            f"using {channel}."
        )

    else:

        money_recovered = 0.0

        if force_failure:
            detail = (
                f"Recovery action {action} was executed "
                f"through {channel}, but recovery was "
                f"intentionally failed for escalation testing."
            )
        else:
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
