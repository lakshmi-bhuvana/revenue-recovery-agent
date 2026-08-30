MAX_RECOVERY_ATTEMPTS = 3


def check_stopping_rule(transaction):
    """
    Determines whether recovery should stop before
    another intervention is attempted.
    """

    if int(transaction.get("recovered", 0) or 0) == 1:
        return {
            "stop": True,
            "reason": "payment_already_recovered"
        }

    attempts = int(
        transaction.get("recovery_attempts", 0) or 0
    )

    if attempts >= MAX_RECOVERY_ATTEMPTS:
        return {
            "stop": True,
            "reason": "maximum_recovery_attempts_reached"
        }

    scenario = str(
        transaction.get("scenario", "")
    ).lower()

    if scenario == "overdue_receivable":

        if str(
            transaction.get("payment_status", "")
        ).lower() == "paid":

            return {
                "stop": True,
                "reason": "invoice_already_paid"
            }

    return {
        "stop": False,
        "reason": "recovery_workflow_can_continue"
    }