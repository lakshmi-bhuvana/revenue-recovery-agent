def diagnose(transaction):
    """
    Diagnose the likely cause of a revenue-risk event.

    The scenario is the primary source of truth for the
    type of revenue-loss event. Failure details are used
    only to refine the diagnosis.
    """

    scenario = str(
        transaction.get("scenario", "")
    ).lower()

    failure_reason = str(
        transaction.get("failure_reason", "")
    ).lower()

    evidence = []

    evidence_fields = [
        "transaction_amount",
        "customer_success_rate",
        "payment_method_success_rate",
        "customer_transaction_count",
        "recovery_attempts",
        "preferred_channel",
        "customer_email_available",
        "customer_phone_available"
    ]

    for field in evidence_fields:
        if field in transaction:
            evidence.append({
                "field": field,
                "value": transaction[field]
            })

    # -----------------------------------------
    # PAYMENT FAILURE
    # -----------------------------------------

    if scenario == "payment_failure":

        customer_success = float(
            transaction.get(
                "customer_success_rate", 0
            ) or 0
        )

        method_success = float(
            transaction.get(
                "payment_method_success_rate", 0
            ) or 0
        )

        # Payment-method degradation:
        # customer historically succeeds more often
        # than the current payment method.
        if customer_success - method_success >= 0.10:

            return {
                "diagnosis": "payment_method_degradation",
                "reason": (
                    "The customer's historical payment success "
                    "is materially higher than the payment method's "
                    "current success rate."
                ),
                "evidence": evidence
            }

        if failure_reason == "insufficient_funds":

            return {
                "diagnosis": "insufficient_funds",
                "reason": (
                    "The payment failed because the customer "
                    "appears to have insufficient funds."
                ),
                "evidence": evidence
            }

        if failure_reason == "bank_decline":

            return {
                "diagnosis": "bank_decline",
                "reason": (
                    "The payment was declined by the bank."
                ),
                "evidence": evidence
            }

        if failure_reason in (
            "timeout",
            "payment_timeout"
        ):

            return {
                "diagnosis": "payment_timeout",
                "reason": (
                    "The payment attempt timed out."
                ),
                "evidence": evidence
            }

        if failure_reason in (
            "authentication_failed",
            "authentication_failure"
        ):

            return {
                "diagnosis": "authentication_failure",
                "reason": (
                    "The payment requires another "
                    "authentication attempt."
                ),
                "evidence": evidence
            }

        # Important:
        # mandate_failed inside a payment_failure event
        # does NOT change the scenario into mandate_failure.

        if failure_reason == "mandate_failed":

            return {
                "diagnosis": "payment_failure_mandate_issue",
                "reason": (
                    "The payment failed because the recurring "
                    "payment mandate could not be used."
                ),
                "evidence": evidence
            }

        return {
            "diagnosis": "payment_failure",
            "reason": (
                "The transaction failed during the "
                "payment process."
            ),
            "evidence": evidence
        }

    # -----------------------------------------
    # CHECKOUT DROP-OFF
    # -----------------------------------------

    if scenario == "checkout_dropoff":

        return {
            "diagnosis": "checkout_abandonment",
            "reason": (
                "Customer showed purchase intent but did "
                "not complete checkout."
            ),
            "evidence": evidence
        }

    # -----------------------------------------
    # FAILED SUBSCRIPTION
    # -----------------------------------------

    if scenario == "failed_subscription":

        return {
            "diagnosis": "subscription_payment_failure",
            "reason": (
                "A recurring subscription payment failed."
            ),
            "evidence": evidence
        }

    # -----------------------------------------
    # MANDATE FAILURE
    # -----------------------------------------

    if scenario == "mandate_failure":

        return {
            "diagnosis": "mandate_failure",
            "reason": (
                "The recurring payment mandate failed "
                "and requires recovery."
            ),
            "evidence": evidence
        }

    # -----------------------------------------
    # OVERDUE RECEIVABLE
    # -----------------------------------------

    if scenario == "overdue_receivable":

        return {
            "diagnosis": "overdue_receivable",
            "reason": (
                "An invoice remains unpaid after its "
                "due date."
            ),
            "evidence": evidence
        }

    # -----------------------------------------
    # UNKNOWN SCENARIO
    # -----------------------------------------

    return {
        "diagnosis": "unknown_revenue_risk",
        "reason": (
            "The revenue-risk event does not match "
            "a supported recovery scenario."
        ),
        "evidence": evidence
    }