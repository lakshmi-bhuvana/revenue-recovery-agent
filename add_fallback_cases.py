from pathlib import Path
import pandas as pd
csv_path = Path("data/raw/revenue_recovery.csv")
df = pd.read_csv(csv_path)
# ------------------------------------------------------------
# FALLBACK / ESCALATION CASES
#
# 4 HIGH cases:
#   forced automated failure
#   -> escalation after 1 attempt
#
# 4 MEDIUM cases:
#   forced automated failure
#   -> escalation after 3 attempts
# ------------------------------------------------------------
cases = [
    # HIGH escalation cases
    {
        "scenario": "payment_failure",
        "failure_reason": "bank_decline",
        "payment_method": "card",
        "transaction_amount": 59000,
        "customer_success_rate": 0.92,
        "payment_method_success_rate": 0.78,
        "product_interest_score": 0.90,
        "checkout_progress": 0.90,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
        "recovery_attempts": 0,
    },
    {
        "scenario": "checkout_abandonment",
        "failure_reason": "customer_abandoned",
        "payment_method": "card",
        "transaction_amount": 56000,
        "customer_success_rate": 0.91,
        "payment_method_success_rate": 0.76,
        "product_interest_score": 0.93,
        "checkout_progress": 0.95,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
        "recovery_attempts": 0,
    },
    {
        "scenario": "mandate_failure",
        "failure_reason": "mandate_failed",
        "payment_method": "bank_mandate",
        "transaction_amount": 51000,
        "customer_success_rate": 0.93,
        "payment_method_success_rate": 0.79,
        "product_interest_score": 0.89,
        "checkout_progress": 0.88,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
        "recovery_attempts": 0,
    },
    {
        "scenario": "promise_to_pay",
        "failure_reason": "promise_to_pay_followup",
        "payment_method": "bank_transfer",
        "transaction_amount": 62000,
        "customer_success_rate": 0.94,
        "payment_method_success_rate": 0.80,
        "product_interest_score": 0.91,
        "checkout_progress": 0.90,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
        "recovery_attempts": 0,
    },
    # MEDIUM escalation cases
    {
        "scenario": "payment_failure",
        "failure_reason": "insufficient_funds",
        "payment_method": "card",
        "transaction_amount": 18000,
        "customer_success_rate": 0.55,
        "payment_method_success_rate": 0.52,
        "product_interest_score": 0.58,
        "checkout_progress": 0.55,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
        "recovery_attempts": 0,
    },
    {
        "scenario": "failed_subscription",
        "failure_reason": "subscription_payment_failed",
        "payment_method": "card",
        "transaction_amount": 16000,
        "customer_success_rate": 0.60,
        "payment_method_success_rate": 0.55,
        "product_interest_score": 0.62,
        "checkout_progress": 0.58,
        "preferred_channel": "email",
        "channel": "payment_link",
        "recovery_attempts": 0,
    },
    {
        "scenario": "checkout_abandonment",
        "failure_reason": "customer_abandoned",
        "payment_method": "upi",
        "transaction_amount": 21000,
        "customer_success_rate": 0.62,
        "payment_method_success_rate": 0.58,
        "product_interest_score": 0.63,
        "checkout_progress": 0.60,
        "preferred_channel": "whatsapp",
        "channel": "payment_link",
        "recovery_attempts": 0,
    },
    {
        "scenario": "b2b_receivable",
        "failure_reason": "invoice_overdue",
        "payment_method": "bank_transfer",
        "transaction_amount": 24000,
        "customer_success_rate": 0.61,
        "payment_method_success_rate": 0.57,
        "product_interest_score": 0.60,
        "checkout_progress": 0.55,
        "preferred_channel": "email",
        "channel": "payment_link",
        "recovery_attempts": 0,
    },
]
existing_ids = set(
    df["transaction_id"].astype(str)
)
numeric_ids = []
for value in existing_ids:
    if value.startswith("txn_") and value[4:].isdigit():
        numeric_ids.append(int(value[4:]))
next_tx = max(numeric_ids) + 1 if numeric_ids else 1
new_rows = []
for index, case in enumerate(cases):
    row = {
        column: None
        for column in df.columns
    }
    row["transaction_id"] = (
        f"txn_{next_tx + index:06d}"
    )
    row["customer_id"] = (
        f"cust_{next_tx + index:04d}"
    )
    row["transaction_amount"] = (
        case["transaction_amount"]
    )
    row["payment_method"] = (
        case["payment_method"]
    )
    row["failure_reason"] = (
        case["failure_reason"]
    )
    row["retry_count"] = 0
    row["customer_transaction_count"] = 5
    row["customer_success_rate"] = (
        case["customer_success_rate"]
    )
    row["payment_method_success_rate"] = (
        case["payment_method_success_rate"]
    )
    row["channel"] = case["channel"]
    row["preferred_channel"] = (
        case["preferred_channel"]
    )
    row["product_interest_score"] = (
        case["product_interest_score"]
    )
    row["checkout_progress"] = (
        case["checkout_progress"]
    )
    row["customer_email_available"] = 1
    row["customer_phone_available"] = 1
    row["scenario"] = case["scenario"]
    row["payment_status"] = "failed"
    row["revenue_at_risk"] = 1
    row["recovery_attempts"] = (
        case["recovery_attempts"]
    )
    row["promise_to_pay"] = (
        1
        if case["scenario"] == "promise_to_pay"
        else 0
    )
    row["recovered"] = 0
    row["money_recovered"] = 0.0
    # This column is used by the Recovery Agent to
    # deterministically demonstrate a failed recovery.
    row["force_recovery_failure"] = 1
    new_rows.append(row)
new_df = pd.DataFrame(
    new_rows
).reindex(
    columns=df.columns.tolist()
    + (
        ["force_recovery_failure"]
        if "force_recovery_failure" not in df.columns
        else []
    )
)
# Ensure original dataframe gets the new column too.
if "force_recovery_failure" not in df.columns:
    df["force_recovery_failure"] = 0
new_df = new_df.reindex(
    columns=df.columns
)
combined = pd.concat(
    [df, new_df],
    ignore_index=True
)
combined.to_csv(
    csv_path,
    index=False
)
print("=" * 60)
print("FALLBACK / ESCALATION CASES ADDED")
print("=" * 60)
print("Original rows:", len(df))
print("Added rows   :", len(new_df))
print("Final rows   :", len(combined))
print()
print(
    "IDs:",
    new_df["transaction_id"].iloc[0],
    "->",
    new_df["transaction_id"].iloc[-1],
)
print()
print("Scenarios:")
print(
    new_df["scenario"]
    .value_counts()
    .to_string()
)
print()
print(
    "Force failure:",
    int(
        new_df["force_recovery_failure"].sum()
    ),
)
print("=" * 60)
