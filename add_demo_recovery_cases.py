import pandas as pd
from pathlib import Path
csv_path = Path("data/raw/revenue_recovery.csv")
df = pd.read_csv(csv_path)
# ------------------------------------------------------------
# Controlled synthetic demo cases
# These are NEW unrecovered opportunities only.
# Existing dataset rows are not modified.
# ------------------------------------------------------------
cases = [
    # --------------------------------------------------------
    # PAYMENT FAILURE
    # --------------------------------------------------------
    {
        "scenario": "payment_failure",
        "failure_reason": "bank_decline",
        "payment_method": "card",
        "transaction_amount": 42000,
        "customer_success_rate": 0.96,
        "payment_method_success_rate": 0.90,
        "product_interest_score": 0.94,
        "checkout_progress": 0.92,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "payment_failure",
        "failure_reason": "insufficient_funds",
        "payment_method": "card",
        "transaction_amount": 38000,
        "customer_success_rate": 0.93,
        "payment_method_success_rate": 0.88,
        "product_interest_score": 0.91,
        "checkout_progress": 0.89,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "payment_failure",
        "failure_reason": "payment_method_failed",
        "payment_method": "card",
        "transaction_amount": 47000,
        "customer_success_rate": 0.97,
        "payment_method_success_rate": 0.92,
        "product_interest_score": 0.95,
        "checkout_progress": 0.96,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "payment_failure",
        "failure_reason": "card_expired",
        "payment_method": "card",
        "transaction_amount": 31500,
        "customer_success_rate": 0.91,
        "payment_method_success_rate": 0.86,
        "product_interest_score": 0.90,
        "checkout_progress": 0.88,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "payment_failure",
        "failure_reason": "invalid_card",
        "payment_method": "card",
        "transaction_amount": 28500,
        "customer_success_rate": 0.94,
        "payment_method_success_rate": 0.87,
        "product_interest_score": 0.92,
        "checkout_progress": 0.90,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "payment_failure",
        "failure_reason": "bank_decline",
        "payment_method": "card",
        "transaction_amount": 52000,
        "customer_success_rate": 0.98,
        "payment_method_success_rate": 0.94,
        "product_interest_score": 0.97,
        "checkout_progress": 0.95,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    # --------------------------------------------------------
    # CHECKOUT ABANDONMENT
    # --------------------------------------------------------
    {
        "scenario": "checkout_abandonment",
        "failure_reason": "customer_abandoned",
        "payment_method": "card",
        "transaction_amount": 36000,
        "customer_success_rate": 0.94,
        "payment_method_success_rate": 0.91,
        "product_interest_score": 0.97,
        "checkout_progress": 0.96,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "checkout_abandonment",
        "failure_reason": "customer_abandoned",
        "payment_method": "upi",
        "transaction_amount": 29500,
        "customer_success_rate": 0.92,
        "payment_method_success_rate": 0.93,
        "product_interest_score": 0.95,
        "checkout_progress": 0.91,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "checkout_abandonment",
        "failure_reason": "customer_abandoned",
        "payment_method": "card",
        "transaction_amount": 44000,
        "customer_success_rate": 0.96,
        "payment_method_success_rate": 0.90,
        "product_interest_score": 0.96,
        "checkout_progress": 0.94,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "checkout_abandonment",
        "failure_reason": "customer_abandoned",
        "payment_method": "upi",
        "transaction_amount": 25500,
        "customer_success_rate": 0.91,
        "payment_method_success_rate": 0.92,
        "product_interest_score": 0.93,
        "checkout_progress": 0.90,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "checkout_abandonment",
        "failure_reason": "customer_abandoned",
        "payment_method": "card",
        "transaction_amount": 49000,
        "customer_success_rate": 0.97,
        "payment_method_success_rate": 0.91,
        "product_interest_score": 0.98,
        "checkout_progress": 0.97,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "checkout_abandonment",
        "failure_reason": "customer_abandoned",
        "payment_method": "card",
        "transaction_amount": 33000,
        "customer_success_rate": 0.93,
        "payment_method_success_rate": 0.89,
        "product_interest_score": 0.94,
        "checkout_progress": 0.93,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    # --------------------------------------------------------
    # FAILED SUBSCRIPTION
    # --------------------------------------------------------
    {
        "scenario": "failed_subscription",
        "failure_reason": "subscription_payment_failed",
        "payment_method": "card",
        "transaction_amount": 22000,
        "customer_success_rate": 0.95,
        "payment_method_success_rate": 0.91,
        "product_interest_score": 0.90,
        "checkout_progress": 0.90,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    {
        "scenario": "failed_subscription",
        "failure_reason": "subscription_payment_failed",
        "payment_method": "card",
        "transaction_amount": 27500,
        "customer_success_rate": 0.94,
        "payment_method_success_rate": 0.90,
        "product_interest_score": 0.92,
        "checkout_progress": 0.88,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    {
        "scenario": "failed_subscription",
        "failure_reason": "subscription_payment_failed",
        "payment_method": "upi",
        "transaction_amount": 18500,
        "customer_success_rate": 0.93,
        "payment_method_success_rate": 0.92,
        "product_interest_score": 0.91,
        "checkout_progress": 0.86,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    {
        "scenario": "failed_subscription",
        "failure_reason": "subscription_payment_failed",
        "payment_method": "card",
        "transaction_amount": 31000,
        "customer_success_rate": 0.97,
        "payment_method_success_rate": 0.93,
        "product_interest_score": 0.94,
        "checkout_progress": 0.92,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    {
        "scenario": "failed_subscription",
        "failure_reason": "subscription_payment_failed",
        "payment_method": "card",
        "transaction_amount": 24500,
        "customer_success_rate": 0.92,
        "payment_method_success_rate": 0.89,
        "product_interest_score": 0.93,
        "checkout_progress": 0.87,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    {
        "scenario": "failed_subscription",
        "failure_reason": "subscription_payment_failed",
        "payment_method": "upi",
        "transaction_amount": 33500,
        "customer_success_rate": 0.96,
        "payment_method_success_rate": 0.94,
        "product_interest_score": 0.95,
        "checkout_progress": 0.93,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    # --------------------------------------------------------
    # B2B RECEIVABLE
    # --------------------------------------------------------
    {
        "scenario": "b2b_receivable",
        "failure_reason": "invoice_overdue",
        "payment_method": "bank_transfer",
        "transaction_amount": 68000,
        "customer_success_rate": 0.95,
        "payment_method_success_rate": 0.90,
        "product_interest_score": 0.88,
        "checkout_progress": 0.82,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    {
        "scenario": "b2b_receivable",
        "failure_reason": "invoice_overdue",
        "payment_method": "bank_transfer",
        "transaction_amount": 54000,
        "customer_success_rate": 0.93,
        "payment_method_success_rate": 0.89,
        "product_interest_score": 0.91,
        "checkout_progress": 0.84,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    {
        "scenario": "b2b_receivable",
        "failure_reason": "invoice_overdue",
        "payment_method": "bank_transfer",
        "transaction_amount": 72000,
        "customer_success_rate": 0.97,
        "payment_method_success_rate": 0.92,
        "product_interest_score": 0.90,
        "checkout_progress": 0.86,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    {
        "scenario": "b2b_receivable",
        "failure_reason": "invoice_overdue",
        "payment_method": "bank_transfer",
        "transaction_amount": 45500,
        "customer_success_rate": 0.92,
        "payment_method_success_rate": 0.88,
        "product_interest_score": 0.89,
        "checkout_progress": 0.80,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    {
        "scenario": "b2b_receivable",
        "failure_reason": "invoice_overdue",
        "payment_method": "bank_transfer",
        "transaction_amount": 61000,
        "customer_success_rate": 0.96,
        "payment_method_success_rate": 0.91,
        "product_interest_score": 0.93,
        "checkout_progress": 0.85,
        "preferred_channel": "email",
        "channel": "payment_link",
    },
    # --------------------------------------------------------
    # MANDATE FAILURE
    # --------------------------------------------------------
    {
        "scenario": "mandate_failure",
        "failure_reason": "mandate_failed",
        "payment_method": "bank_mandate",
        "transaction_amount": 26500,
        "customer_success_rate": 0.95,
        "payment_method_success_rate": 0.91,
        "product_interest_score": 0.89,
        "checkout_progress": 0.88,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "mandate_failure",
        "failure_reason": "mandate_failed",
        "payment_method": "bank_mandate",
        "transaction_amount": 39500,
        "customer_success_rate": 0.96,
        "payment_method_success_rate": 0.92,
        "product_interest_score": 0.93,
        "checkout_progress": 0.90,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "mandate_failure",
        "failure_reason": "mandate_failed",
        "payment_method": "bank_mandate",
        "transaction_amount": 31500,
        "customer_success_rate": 0.92,
        "payment_method_success_rate": 0.90,
        "product_interest_score": 0.91,
        "checkout_progress": 0.87,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "mandate_failure",
        "failure_reason": "mandate_failed",
        "payment_method": "bank_mandate",
        "transaction_amount": 47500,
        "customer_success_rate": 0.97,
        "payment_method_success_rate": 0.93,
        "product_interest_score": 0.94,
        "checkout_progress": 0.91,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "mandate_failure",
        "failure_reason": "mandate_failed",
        "payment_method": "bank_mandate",
        "transaction_amount": 28500,
        "customer_success_rate": 0.94,
        "payment_method_success_rate": 0.89,
        "product_interest_score": 0.92,
        "checkout_progress": 0.89,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    # --------------------------------------------------------
    # PROMISE TO PAY
    # --------------------------------------------------------
    {
        "scenario": "promise_to_pay",
        "failure_reason": "promise_to_pay_followup",
        "payment_method": "bank_transfer",
        "transaction_amount": 34000,
        "customer_success_rate": 0.96,
        "payment_method_success_rate": 0.91,
        "product_interest_score": 0.94,
        "checkout_progress": 0.90,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "promise_to_pay",
        "failure_reason": "promise_to_pay_followup",
        "payment_method": "upi",
        "transaction_amount": 28000,
        "customer_success_rate": 0.94,
        "payment_method_success_rate": 0.92,
        "product_interest_score": 0.93,
        "checkout_progress": 0.88,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "promise_to_pay",
        "failure_reason": "promise_to_pay_followup",
        "payment_method": "bank_transfer",
        "transaction_amount": 46000,
        "customer_success_rate": 0.97,
        "payment_method_success_rate": 0.93,
        "product_interest_score": 0.95,
        "checkout_progress": 0.92,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "promise_to_pay",
        "failure_reason": "promise_to_pay_followup",
        "payment_method": "upi",
        "transaction_amount": 22500,
        "customer_success_rate": 0.93,
        "payment_method_success_rate": 0.90,
        "product_interest_score": 0.91,
        "checkout_progress": 0.87,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "promise_to_pay",
        "failure_reason": "promise_to_pay_followup",
        "payment_method": "bank_transfer",
        "transaction_amount": 52000,
        "customer_success_rate": 0.98,
        "payment_method_success_rate": 0.94,
        "product_interest_score": 0.96,
        "checkout_progress": 0.95,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "promise_to_pay",
        "failure_reason": "promise_to_pay_followup",
        "payment_method": "card",
        "transaction_amount": 36500,
        "customer_success_rate": 0.95,
        "payment_method_success_rate": 0.91,
        "product_interest_score": 0.92,
        "checkout_progress": 0.91,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "promise_to_pay",
        "failure_reason": "promise_to_pay_followup",
        "payment_method": "bank_transfer",
        "transaction_amount": 41500,
        "customer_success_rate": 0.96,
        "payment_method_success_rate": 0.92,
        "product_interest_score": 0.94,
        "checkout_progress": 0.93,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
    {
        "scenario": "promise_to_pay",
        "failure_reason": "promise_to_pay_followup",
        "payment_method": "upi",
        "transaction_amount": 30500,
        "customer_success_rate": 0.94,
        "payment_method_success_rate": 0.90,
        "product_interest_score": 0.93,
        "checkout_progress": 0.89,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
    },
]
# ------------------------------------------------------------
# Existing IDs
# ------------------------------------------------------------
existing_ids = set(
    df["transaction_id"].astype(str)
    if "transaction_id" in df.columns
    else []
)
new_rows = []
for index, case in enumerate(cases, start=1):
    transaction_id = f"demo_high_{index:03d}"
    if transaction_id in existing_ids:
        raise RuntimeError(
            f"Demo transaction already exists: {transaction_id}"
        )
    row = {}
    # Start with safe defaults for whatever columns already
    # exist in the user's CSV.
    for column in df.columns:
        row[column] = None
    row["transaction_id"] = transaction_id
    row["customer_id"] = f"demo_customer_high_{index:03d}"
    row["transaction_amount"] = case["transaction_amount"]
    row["payment_method"] = case["payment_method"]
    row["failure_reason"] = case["failure_reason"]
    row["retry_count"] = 0
    row["customer_transaction_count"] = 10
    row["customer_success_rate"] = case["customer_success_rate"]
    row["payment_method_success_rate"] = case["payment_method_success_rate"]
    row["channel"] = case["channel"]
    row["preferred_channel"] = case["preferred_channel"]
    row["product_interest_score"] = case["product_interest_score"]
    row["checkout_progress"] = case["checkout_progress"]
    row["customer_email_available"] = 1
    row["customer_phone_available"] = 1
    row["scenario"] = case["scenario"]
    row["payment_status"] = "failed"
    row["revenue_at_risk"] = 1
    row["recovery_attempts"] = 0
    row["promise_to_pay"] = (
        1 if case["scenario"] == "promise_to_pay" else 0
    )
    row["recovered"] = 0
    row["money_recovered"] = 0.0
    new_rows.append(row)
new_df = pd.DataFrame(new_rows)
# Keep EXACTLY the original CSV column structure.
new_df = new_df.reindex(columns=df.columns)
combined = pd.concat(
    [df, new_df],
    ignore_index=True
)
combined.to_csv(
    csv_path,
    index=False
)
print()
print("=" * 60)
print("DEMO CASES ADDED")
print("=" * 60)
print(f"Original rows : {len(df):,}")
print(f"Added rows    : {len(new_df):,}")
print(f"New total     : {len(combined):,}")
print()
print("Scenario distribution:")
print(
    new_df["scenario"]
    .value_counts()
    .to_string()
)
print()
print("Promise-to-Pay cases:")
print(
    int(
        (
            new_df["scenario"]
            == "promise_to_pay"
        ).sum()
    )
)
print()
print("All new cases are:")
print("  recovered = 0")
print("  revenue_at_risk = 1")
print("  recovery_attempts = 0")
print()
print("Backup:")
print(
    "data/raw/revenue_recovery_backup_before_demo_cases.csv"
)
print("=" * 60)
