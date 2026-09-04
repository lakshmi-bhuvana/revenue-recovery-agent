from pathlib import Path
import pandas as pd
csv_path = Path("data/raw/revenue_recovery.csv")
df = pd.read_csv(csv_path)
cases = [
    ("payment_failure", "bank_decline", "card", 42000, 0.96, 0.90, 0.94, 0.92, "whatsapp", "payment_link", "retry_payment"),
    ("payment_failure", "insufficient_funds", "card", 38000, 0.93, 0.88, 0.91, 0.89, "whatsapp", "payment_link", "retry_payment"),
    ("payment_failure", "payment_method_failed", "card", 47000, 0.97, 0.92, 0.95, 0.96, "whatsapp", "payment_link", "retry_payment"),
    ("payment_failure", "card_expired", "card", 31500, 0.91, 0.86, 0.90, 0.88, "whatsapp", "payment_link", "retry_payment"),
    ("payment_failure", "invalid_card", "card", 28500, 0.94, 0.87, 0.92, 0.90, "whatsapp", "payment_link", "retry_payment"),
    ("payment_failure", "bank_decline", "card", 52000, 0.98, 0.94, 0.97, 0.95, "whatsapp", "payment_link", "retry_payment"),
    ("checkout_abandonment", "customer_abandoned", "card", 36000, 0.94, 0.91, 0.97, 0.96, "whatsapp", "payment_link", "checkout_reminder"),
    ("checkout_abandonment", "customer_abandoned", "upi", 29500, 0.92, 0.93, 0.95, 0.91, "whatsapp", "payment_link", "checkout_reminder"),
    ("checkout_abandonment", "customer_abandoned", "card", 44000, 0.96, 0.90, 0.96, 0.94, "whatsapp", "payment_link", "checkout_reminder"),
    ("checkout_abandonment", "customer_abandoned", "upi", 25500, 0.91, 0.92, 0.93, 0.90, "whatsapp", "payment_link", "checkout_reminder"),
    ("checkout_abandonment", "customer_abandoned", "card", 49000, 0.97, 0.91, 0.98, 0.97, "whatsapp", "payment_link", "checkout_reminder"),
    ("checkout_abandonment", "customer_abandoned", "card", 33000, 0.93, 0.89, 0.94, 0.93, "whatsapp", "payment_link", "checkout_reminder"),
    ("failed_subscription", "subscription_payment_failed", "card", 22000, 0.95, 0.91, 0.90, 0.90, "email", "payment_link", "retry_subscription_payment"),
    ("failed_subscription", "subscription_payment_failed", "card", 27500, 0.94, 0.90, 0.92, 0.88, "email", "payment_link", "retry_subscription_payment"),
    ("failed_subscription", "subscription_payment_failed", "upi", 18500, 0.93, 0.92, 0.91, 0.86, "email", "payment_link", "retry_subscription_payment"),
    ("failed_subscription", "subscription_payment_failed", "card", 31000, 0.97, 0.93, 0.94, 0.92, "email", "payment_link", "retry_subscription_payment"),
    ("failed_subscription", "subscription_payment_failed", "card", 24500, 0.92, 0.89, 0.93, 0.87, "email", "payment_link", "retry_subscription_payment"),
    ("failed_subscription", "subscription_payment_failed", "upi", 33500, 0.96, 0.94, 0.95, 0.93, "email", "payment_link", "retry_subscription_payment"),
    ("b2b_receivable", "invoice_overdue", "bank_transfer", 68000, 0.95, 0.90, 0.88, 0.82, "email", "payment_link", "send_invoice_reminder"),
    ("b2b_receivable", "invoice_overdue", "bank_transfer", 54000, 0.93, 0.89, 0.91, 0.84, "email", "payment_link", "send_invoice_reminder"),
    ("b2b_receivable", "invoice_overdue", "bank_transfer", 72000, 0.97, 0.92, 0.90, 0.86, "email", "payment_link", "send_invoice_reminder"),
    ("b2b_receivable", "invoice_overdue", "bank_transfer", 45500, 0.92, 0.88, 0.89, 0.80, "email", "payment_link", "send_invoice_reminder"),
    ("b2b_receivable", "invoice_overdue", "bank_transfer", 61000, 0.96, 0.91, 0.93, 0.85, "email", "payment_link", "send_invoice_reminder"),
    ("mandate_failure", "mandate_failed", "bank_mandate", 26500, 0.95, 0.91, 0.89, 0.88, "whatsapp", "payment_link", "retry_mandate"),
    ("mandate_failure", "mandate_failed", "bank_mandate", 39500, 0.96, 0.92, 0.93, 0.90, "whatsapp", "payment_link", "retry_mandate"),
    ("mandate_failure", "mandate_failed", "bank_mandate", 31500, 0.92, 0.90, 0.91, 0.87, "whatsapp", "payment_link", "retry_mandate"),
    ("mandate_failure", "mandate_failed", "bank_mandate", 47500, 0.97, 0.93, 0.94, 0.91, "whatsapp", "payment_link", "retry_mandate"),
    ("mandate_failure", "mandate_failed", "bank_mandate", 28500, 0.94, 0.89, 0.92, 0.89, "whatsapp", "payment_link", "retry_mandate"),
    ("promise_to_pay", "promise_to_pay_followup", "bank_transfer", 34000, 0.96, 0.91, 0.94, 0.90, "whatsapp", "payment_link", "follow_up_promise_to_pay"),
    ("promise_to_pay", "promise_to_pay_followup", "upi", 28000, 0.94, 0.92, 0.93, 0.88, "whatsapp", "payment_link", "follow_up_promise_to_pay"),
    ("promise_to_pay", "promise_to_pay_followup", "bank_transfer", 46000, 0.97, 0.93, 0.95, 0.92, "whatsapp", "payment_link", "follow_up_promise_to_pay"),
    ("promise_to_pay", "promise_to_pay_followup", "upi", 22500, 0.93, 0.90, 0.91, 0.87, "whatsapp", "payment_link", "follow_up_promise_to_pay"),
    ("promise_to_pay", "promise_to_pay_followup", "bank_transfer", 52000, 0.98, 0.94, 0.96, 0.95, "whatsapp", "payment_link", "follow_up_promise_to_pay"),
    ("promise_to_pay", "promise_to_pay_followup", "card", 36500, 0.95, 0.91, 0.92, 0.91, "whatsapp", "payment_link", "follow_up_promise_to_pay"),
    ("promise_to_pay", "promise_to_pay_followup", "bank_transfer", 41500, 0.96, 0.92, 0.94, 0.93, "whatsapp", "payment_link", "follow_up_promise_to_pay"),
    ("promise_to_pay", "promise_to_pay_followup", "upi", 30500, 0.94, 0.90, 0.93, 0.89, "whatsapp", "payment_link", "follow_up_promise_to_pay"),
]
# Continue normal transaction sequence.
existing_numbers = []
for value in df["transaction_id"].astype(str):
    if value.startswith("txn_") and value[4:].isdigit():
        existing_numbers.append(int(value[4:]))
next_tx = max(existing_numbers) + 1 if existing_numbers else 1
# Continue normal customer sequence where possible.
customer_numbers = []
for value in df["customer_id"].astype(str):
    digits = "".join(ch for ch in reversed(value) if ch.isdigit())
    if digits:
        customer_numbers.append(int(digits[::-1]))
next_customer = max(customer_numbers) + 1 if customer_numbers else next_tx
new_rows = []
for i, case in enumerate(cases):
    (
        scenario,
        failure_reason,
        payment_method,
        amount,
        customer_success,
        payment_success,
        interest,
        checkout,
        preferred_channel,
        channel,
        recovery_action,
    ) = case
    row = {column: None for column in df.columns}
    row["transaction_id"] = f"txn_{next_tx + i:06d}"
    row["customer_id"] = f"customer_{next_customer + i:06d}"
    row["transaction_amount"] = amount
    row["payment_method"] = payment_method
    row["failure_reason"] = failure_reason
    row["retry_count"] = 0
    row["customer_transaction_count"] = 10
    row["customer_success_rate"] = customer_success
    row["payment_method_success_rate"] = payment_success
    row["channel"] = channel
    row["preferred_channel"] = preferred_channel
    row["product_interest_score"] = interest
    row["checkout_progress"] = checkout
    row["customer_email_available"] = 1
    row["customer_phone_available"] = 1
    row["scenario"] = scenario
    row["payment_status"] = "failed"
    row["revenue_at_risk"] = 1
    row["recovery_attempts"] = 0
    row["promise_to_pay"] = 1 if scenario == "promise_to_pay" else 0
    row["recovered"] = 0
    row["money_recovered"] = 0.0
    # Populate display/action columns when they exist.
    if "recovery_action" in df.columns:
        row["recovery_action"] = recovery_action
    if "strategy" in df.columns:
        if scenario == "payment_failure":
            row["strategy"] = "aggressive_recovery"
        elif scenario in {"checkout_abandonment", "failed_subscription", "promise_to_pay"}:
            row["strategy"] = "assisted_recovery"
        else:
            row["strategy"] = "standard_recovery"
    if "recommended_channel" in df.columns:
        row["recommended_channel"] = preferred_channel
    new_rows.append(row)
new_df = pd.DataFrame(new_rows).reindex(columns=df.columns)
combined = pd.concat([df, new_df], ignore_index=True)
combined.to_csv(csv_path, index=False)
print("=" * 60)
print("NORMAL MIXED RECOVERY CASES ADDED")
print("=" * 60)
print("Original rows:", len(df))
print("Added rows   :", len(new_df))
print("Final rows   :", len(combined))
print()
print("ID range:")
print(new_df["transaction_id"].iloc[0], "->", new_df["transaction_id"].iloc[-1])
print()
print("Scenarios:")
print(new_df["scenario"].value_counts().to_string())
print()
print("Promise-to-Pay:", int((new_df["promise_to_pay"] == 1).sum()))
print("Recovered:", int(new_df["recovered"].sum()))
print("=" * 60)
