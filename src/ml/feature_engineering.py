import pandas as pd


def create_features(df):

    df = df.copy()

    # -----------------------------------------
    # CUSTOMER RELIABILITY
    # -----------------------------------------

    df["customer_reliability"] = (
        0.7 * df["customer_success_rate"]
        + 0.3 * (df["customer_transaction_count"] /
                 df["customer_transaction_count"].max())
    )

    # -----------------------------------------
    # PAYMENT RELIABILITY
    # -----------------------------------------

    df["payment_reliability"] = (
        0.5 * df["customer_success_rate"]
        + 0.5 * df["payment_method_success_rate"]
    )

    # -----------------------------------------
    # CUSTOMER INTENT
    # -----------------------------------------

    df["customer_intent"] = (
        0.6 * df["product_interest_score"]
        + 0.4 * df["checkout_progress"]
    )

    # -----------------------------------------
    # CONTACTABILITY
    # -----------------------------------------

    df["contactability"] = (
        df["customer_email_available"]
        + df["customer_phone_available"]
    )

    # -----------------------------------------
    # RECOVERY FRICTION
    # -----------------------------------------

    df["recovery_friction"] = (
        df["recovery_attempts"]
    )

    return df