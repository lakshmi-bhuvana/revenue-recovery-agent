import pandas as pd
import numpy as np

np.random.seed(42)

N = 3000

payment_methods = ["UPI", "CARD", "NETBANKING", "WALLET"]
channels = ["web", "mobile", "payment_link", "subscription", "invoice"]

scenarios = [
    "clean_payment",
    "payment_failure",
    "checkout_dropoff",
    "failed_subscription",
    "overdue_receivable",
    "mandate_failure"
]

failure_reasons = [
    "none",
    "insufficient_funds",
    "bank_decline",
    "timeout",
    "authentication_failed",
    "mandate_failed",
    "customer_abandoned",
    "invoice_overdue"
]

preferred_channels = ["sms", "email", "whatsapp"]

data = []

for i in range(N):

    scenario = np.random.choice(
        scenarios,
        p=[0.45, 0.18, 0.12, 0.10, 0.08, 0.07]
    )

    customer_transactions = np.random.randint(1, 30)

    customer_success_rate = round(
        np.random.beta(8, 2), 3
    )

    payment_method = np.random.choice(payment_methods)

    payment_method_success_rate = round(
        np.random.uniform(0.70, 0.99), 3
    )

    product_interest_score = round(
        np.random.uniform(0, 1), 3
    )

    checkout_progress = round(
        np.random.uniform(0, 1), 3
    )

    transaction_amount = round(
        np.random.uniform(200, 50000), 2
    )

    channel = np.random.choice(channels)

    preferred_channel = np.random.choice(preferred_channels)

    customer_email_available = np.random.choice(
        [0, 1], p=[0.15, 0.85]
    )

    customer_phone_available = np.random.choice(
        [0, 1], p=[0.10, 0.90]
    )

    failure_reason = "none"

    if scenario == "payment_failure":
        failure_reason = np.random.choice(
            failure_reasons[1:6]
        )

    elif scenario == "checkout_dropoff":
        failure_reason = "customer_abandoned"

    elif scenario == "failed_subscription":
        failure_reason = np.random.choice(
            ["insufficient_funds", "bank_decline", "timeout"]
        )

    elif scenario == "overdue_receivable":
        failure_reason = "invoice_overdue"

    elif scenario == "mandate_failure":
        failure_reason = "mandate_failed"

    # Revenue at risk
    if scenario == "clean_payment":
        revenue_at_risk = 0
    else:
        revenue_at_risk = 1

    # Current payment status
    if scenario == "clean_payment":
        payment_status = "captured"
    elif scenario == "checkout_dropoff":
        payment_status = "abandoned"
    elif scenario == "overdue_receivable":
        payment_status = "overdue"
    elif scenario in ["failed_subscription", "mandate_failure"]:
        payment_status = "failed"
    else:
        payment_status = "failed"

    # Whether customer eventually paid
    recovery_probability = (
        0.25
        + 0.30 * customer_success_rate
        + 0.20 * product_interest_score
        + 0.15 * payment_method_success_rate
        + 0.10 * checkout_progress
    )

    if scenario == "clean_payment":
        recovered = 1
    else:
        recovered = int(
            np.random.random() < recovery_probability
        )

    money_recovered = (
        transaction_amount
        if recovered == 1 and revenue_at_risk == 1
        else 0
    )

    recovery_attempts = (
        np.random.randint(0, 4)
        if revenue_at_risk
        else 0
    )

    promise_to_pay = 0

    if recovered and revenue_at_risk:
        promise_to_pay = np.random.choice([0, 1], p=[0.7, 0.3])

    data.append({
        "transaction_id": f"txn_{i+1:06d}",
        "customer_id": f"cust_{np.random.randint(1, 800):04d}",
        "transaction_amount": transaction_amount,

        "customer_transaction_count": customer_transactions,
        "customer_success_rate": customer_success_rate,

        "payment_method": payment_method,
        "payment_method_success_rate": payment_method_success_rate,

        "channel": channel,
        "preferred_channel": preferred_channel,

        "product_interest_score": product_interest_score,
        "checkout_progress": checkout_progress,

        "customer_email_available": customer_email_available,
        "customer_phone_available": customer_phone_available,

        "scenario": scenario,
        "payment_status": payment_status,
        "failure_reason": failure_reason,

        "revenue_at_risk": revenue_at_risk,

        "recovery_attempts": recovery_attempts,
        "promise_to_pay": promise_to_pay,

        "recovered": recovered,
        "money_recovered": money_recovered
    })


df = pd.DataFrame(data)

df.to_csv(
    "data/raw/revenue_recovery.csv",
    index=False
)

print("Dataset generated successfully.")
print("Shape:", df.shape)
print("\nScenario distribution:")
print(df["scenario"].value_counts())

print("\nRevenue at risk:")
print(df["revenue_at_risk"].value_counts())

print("\nTotal revenue at risk: ₹",
      df.loc[df["revenue_at_risk"] == 1,
             "transaction_amount"].sum())

print("\nTotal money recovered: ₹",
      df["money_recovered"].sum())