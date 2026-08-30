from copy import deepcopy

from src.agent.recovery_agent import RecoveryAgent
from src.ml.recovery_scorer import RecoveryScorer


BASE_TRANSACTION = {
    "transaction_id": "agent_test_001",
    "customer_id": "customer_001",
    "transaction_amount": 35000,
    "payment_method": "CARD",
    "failure_reason": "bank_decline",
    "retry_count": 0,
    "customer_transaction_count": 8,
    "customer_success_rate": 0.88,
    "payment_method_success_rate": 0.91,
    "channel": "payment_link",
    "preferred_channel": "whatsapp",
    "product_interest_score": 0.91,
    "checkout_progress": 0.65,
    "customer_email_available": 1,
    "customer_phone_available": 1,
    "scenario": "payment_failure",
    "payment_status": "failed",
    "revenue_at_risk": 1,
    "recovery_attempts": 0,
    "promise_to_pay": 0,
    "recovered": 0,
    "money_recovered": 0,
}


def run_test(name, transaction):
    print(f"\n{'=' * 70}")
    print(name)
    print("=" * 70)

    agent = RecoveryAgent(RecoveryScorer())

    result = agent.process(deepcopy(transaction))

    print("\nSTATUS:")
    print(result["status"])

    print("\nDIAGNOSIS:")
    print(result["diagnosis"])

    print("\nSCORE:")
    print(result["score"])

    print("\nACTION:")
    print(result["action"])

    print("\nPOLICY:")
    print(result["policy"])

    print("\nEXECUTION:")
    print(result["execution"])

    print("\nSTOPPING:")
    print(result["stopping"])

    print("\nESCALATION:")
    print(result["escalation"])

    print("\nAUDIT:")
    print(result["audit"])

    return result


if __name__ == "__main__":

    # --------------------------------------------------
    # 1. PAYMENT FAILURE
    # --------------------------------------------------

    run_test(
        "PAYMENT FAILURE",
        BASE_TRANSACTION,
    )

    # --------------------------------------------------
    # 2. CHECKOUT ABANDONMENT
    # --------------------------------------------------

    checkout = deepcopy(BASE_TRANSACTION)
    checkout["transaction_id"] = "agent_test_checkout"
    checkout["scenario"] = "checkout_abandonment"
    checkout["failure_reason"] = "customer_abandoned"
    checkout["checkout_progress"] = 0.82

    run_test(
        "CHECKOUT ABANDONMENT",
        checkout,
    )

    # --------------------------------------------------
    # 3. FAILED SUBSCRIPTION
    # --------------------------------------------------

    subscription = deepcopy(BASE_TRANSACTION)
    subscription["transaction_id"] = "agent_test_subscription"
    subscription["scenario"] = "failed_subscription"
    subscription["failure_reason"] = "subscription_payment_failed"

    run_test(
        "FAILED SUBSCRIPTION",
        subscription,
    )

    # --------------------------------------------------
    # 4. B2B RECEIVABLE
    # --------------------------------------------------

    b2b = deepcopy(BASE_TRANSACTION)
    b2b["transaction_id"] = "agent_test_b2b"
    b2b["scenario"] = "b2b_receivable"
    b2b["failure_reason"] = "invoice_overdue"

    run_test(
        "B2B RECEIVABLE",
        b2b,
    )

    # --------------------------------------------------
    # 5. MANDATE FAILURE
    # --------------------------------------------------

    mandate = deepcopy(BASE_TRANSACTION)
    mandate["transaction_id"] = "agent_test_mandate"
    mandate["scenario"] = "mandate_failure"
    mandate["failure_reason"] = "mandate_failed"

    run_test(
        "MANDATE FAILURE",
        mandate,
    )

    # --------------------------------------------------
    # 6. PROMISE TO PAY
    # --------------------------------------------------

    ptp = deepcopy(BASE_TRANSACTION)
    ptp["transaction_id"] = "agent_test_ptp"
    ptp["scenario"] = "promise_to_pay"
    ptp["failure_reason"] = "promise_to_pay_due"
    ptp["promise_to_pay"] = 1

    run_test(
        "PROMISE TO PAY",
        ptp,
    )