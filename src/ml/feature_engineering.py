import numpy as np
import pandas as pd
def create_features(df):
    """
    Leakage-safe feature engineering for revenue recovery.
    Important:
    - Uses only information available before the recovery action.
    - Does not use recovered, money_recovered, or transaction/customer IDs.
    - Preserves the existing engineered features used by the agent.
    """
    df = df.copy()
    # =========================================================
    # SAFE NUMERIC INPUTS
    # =========================================================
    transaction_count = pd.to_numeric(
        df.get("customer_transaction_count", 0),
        errors="coerce"
    ).fillna(0).clip(lower=0)
    customer_success = pd.to_numeric(
        df.get("customer_success_rate", 0),
        errors="coerce"
    ).fillna(0).clip(0, 1)
    payment_success = pd.to_numeric(
        df.get("payment_method_success_rate", 0),
        errors="coerce"
    ).fillna(0).clip(0, 1)
    interest = pd.to_numeric(
        df.get("product_interest_score", 0),
        errors="coerce"
    ).fillna(0).clip(0, 1)
    checkout = pd.to_numeric(
        df.get("checkout_progress", 0),
        errors="coerce"
    ).fillna(0).clip(0, 1)
    attempts = pd.to_numeric(
        df.get("recovery_attempts", 0),
        errors="coerce"
    ).fillna(0).clip(lower=0)
    email_available = pd.to_numeric(
        df.get("customer_email_available", 0),
        errors="coerce"
    ).fillna(0).clip(0, 1)
    phone_available = pd.to_numeric(
        df.get("customer_phone_available", 0),
        errors="coerce"
    ).fillna(0).clip(0, 1)
    amount = pd.to_numeric(
        df.get("transaction_amount", 0),
        errors="coerce"
    ).fillna(0).clip(lower=0)
    # =========================================================
    # EXISTING FEATURES
    # =========================================================
    transaction_history_score = (
        transaction_count / 10.0
    ).clip(0, 1)
    df["customer_reliability"] = (
        0.7 * customer_success
        + 0.3 * transaction_history_score
    ).clip(0, 1)
    df["payment_reliability"] = (
        0.5 * customer_success
        + 0.5 * payment_success
    ).clip(0, 1)
    df["customer_intent"] = (
        0.6 * interest
        + 0.4 * checkout
    ).clip(0, 1)
    df["contactability"] = (
        (email_available + phone_available) / 2.0
    ).clip(0, 1)
    df["recovery_friction"] = (
        attempts / 3.0
    ).clip(0, 1)
    # =========================================================
    # NEW BEHAVIORAL FEATURES
    # =========================================================
    # Historical success gap:
    # positive means the customer historically performs better
    # than the payment method.
    df["customer_vs_payment_success_gap"] = (
        customer_success - payment_success
    )
    # Combined reliability signal.
    df["reliability_average"] = (
        customer_success + payment_success
    ) / 2.0
    # Product interest minus checkout completion can identify
    # customers who are interested but stalled before completion.
    df["intent_gap"] = (
        interest - checkout
    )
    # Combined intent strength.
    df["engagement_strength"] = (
        0.5 * interest
        + 0.5 * checkout
    ).clip(0, 1)
    # Channel availability count.
    df["available_channel_count"] = (
        email_available + phone_available
    )
    # Whether at least one direct contact route exists.
    df["has_contact_channel"] = (
        (
            email_available
            + phone_available
        ) > 0
    ).astype(int)
    # Whether both channels are available.
    df["multi_channel_contact"] = (
        (
            email_available
            + phone_available
        ) >= 2
    ).astype(int)
    # Attempt pressure.
    df["attempt_pressure"] = (
        attempts / 3.0
    ).clip(0, 1)
    # Remaining policy capacity.
    df["attempts_remaining_ratio"] = (
        1.0 - df["attempt_pressure"]
    ).clip(0, 1)
    # Historical opportunity quality.
    df["customer_history_strength"] = (
        np.log1p(transaction_count)
        / np.log1p(20.0)
    ).clip(0, 1)
    # Amount scale (log reduces domination by very large values).
    df["transaction_amount_log"] = (
        np.log1p(amount)
    )
    # Normalized amount relative to a practical ₹50k reference.
    df["transaction_amount_scaled"] = (
        amount / 50000.0
    ).clip(0, 10)
    # =========================================================
    # INTERACTION FEATURES
    # =========================================================
    # Reliable customer + reliable payment method.
    df["reliability_x_payment"] = (
        df["customer_reliability"]
        * df["payment_reliability"]
    )
    # Intent × contactability.
    # High intent is more actionable when the customer can be reached.
    df["intent_x_contactability"] = (
        df["customer_intent"]
        * df["contactability"]
    )
    # Reliability × contactability.
    df["reliability_x_contactability"] = (
        df["customer_reliability"]
        * df["contactability"]
    )
    # Intent × reliability.
    df["intent_x_reliability"] = (
        df["customer_intent"]
        * df["customer_reliability"]
    )
    # High friction should reduce recovery confidence.
    df["recovery_capacity"] = (
        (
            0.45 * df["customer_reliability"]
            + 0.30 * df["customer_intent"]
            + 0.25 * df["contactability"]
        )
        * (
            1.0 - df["recovery_friction"]
        )
    ).clip(0, 1)
    # Expected-value style features available before execution.
    df["amount_x_reliability"] = (
        amount
        * df["customer_reliability"]
    )
    df["amount_x_intent"] = (
        amount
        * df["customer_intent"]
    )
    df["amount_x_contactability"] = (
        amount
        * df["contactability"]
    )
    # =========================================================
    # SCENARIO-SPECIFIC SIGNALS
    # =========================================================
    scenario = (
        df.get(
            "scenario",
            ""
        )
        .astype(str)
        .str.lower()
    )
    df["is_payment_failure"] = (
        scenario == "payment_failure"
    ).astype(int)
    df["is_checkout_abandonment"] = (
        scenario == "checkout_abandonment"
    ).astype(int)
    df["is_failed_subscription"] = (
        scenario == "failed_subscription"
    ).astype(int)
    df["is_b2b_receivable"] = (
        scenario == "b2b_receivable"
    ).astype(int)
    df["is_mandate_failure"] = (
        scenario == "mandate_failure"
    ).astype(int)
    # =========================================================
    # CHANNEL / PREFERENCE SIGNALS
    # =========================================================
    preferred = (
        df.get(
            "preferred_channel",
            ""
        )
        .astype(str)
        .str.lower()
        .str.strip()
    )
    channel = (
        df.get(
            "channel",
            ""
        )
        .astype(str)
        .str.lower()
        .str.strip()
    )
    df["channel_matches_preference"] = (
        (
            channel != ""
        )
        & (
            preferred != ""
        )
        & (
            channel == preferred
        )
    ).astype(int)
    # =========================================================
    # STABLE CLEANUP
    # =========================================================
    # Replace infinities produced by unusual source values.
    numeric_columns = df.select_dtypes(
        include=["number"]
    ).columns
    df[numeric_columns] = (
        df[numeric_columns]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
    )
    return df