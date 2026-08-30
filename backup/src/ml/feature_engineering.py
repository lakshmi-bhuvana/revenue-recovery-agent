import pandas as pd


def create_features(df):
    """
    Create features used by the recovery ML model and agent.

    The calculations are bounded where appropriate so that
    single-event inference produces the same type of feature
    values as historical inference.
    """

    df = df.copy()

    # -----------------------------------------
    # CUSTOMER RELIABILITY
    # -----------------------------------------

    transaction_count = pd.to_numeric(
        df["customer_transaction_count"],
        errors="coerce"
    ).fillna(0)

    # Cap the transaction-count contribution at 1.
    # 10+ historical transactions represents strong history.
    transaction_history_score = (
        transaction_count / 10
    ).clip(0, 1)

    df["customer_reliability"] = (
        0.7 * df["customer_success_rate"]
        + 0.3 * transaction_history_score
    ).clip(0, 1)

    # -----------------------------------------
    # PAYMENT RELIABILITY
    # -----------------------------------------

    df["payment_reliability"] = (
        0.5 * df["customer_success_rate"]
        + 0.5 * df["payment_method_success_rate"]
    ).clip(0, 1)

    # -----------------------------------------
    # CUSTOMER INTENT
    # -----------------------------------------

    df["customer_intent"] = (
        0.6 * df["product_interest_score"]
        + 0.4 * df["checkout_progress"]
    ).clip(0, 1)

    # -----------------------------------------
    # CONTACTABILITY
    # -----------------------------------------

    email_available = (
        pd.to_numeric(
            df["customer_email_available"],
            errors="coerce"
        )
        .fillna(0)
        .clip(0, 1)
    )

    phone_available = (
        pd.to_numeric(
            df["customer_phone_available"],
            errors="coerce"
        )
        .fillna(0)
        .clip(0, 1)
    )

    # 0 = no channel
    # 0.5 = one channel
    # 1 = both channels
    df["contactability"] = (
        (email_available + phone_available) / 2
    ).clip(0, 1)

    # -----------------------------------------
    # RECOVERY FRICTION
    # -----------------------------------------

    recovery_attempts = pd.to_numeric(
        df["recovery_attempts"],
        errors="coerce"
    ).fillna(0)

    # Normalize recovery attempts to 0-1.
    # Three attempts is the maximum allowed by policy.
    df["recovery_friction"] = (
        recovery_attempts / 3
    ).clip(0, 1)

    return df