import pandas as pd
import psycopg2


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "revenue_recovery",
    "user": "postgres",
    "password": "sql123"
}

RAW_DATA_PATH = "data/raw/revenue_recovery.csv"
DECISIONS_PATH = "data/processed/recovery_decisions.csv"


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def main():

    print("Loading source data...")

    raw_df = pd.read_csv(RAW_DATA_PATH)
    decisions_df = pd.read_csv(DECISIONS_PATH)

    print("Raw transactions:", len(raw_df))
    print("Agent decisions:", len(decisions_df))

    # --------------------------------------------------
    # KEEP ONLY AT-RISK TRANSACTIONS
    # --------------------------------------------------

    raw_df = raw_df[
        raw_df["revenue_at_risk"] == 1
    ].copy()

    print("At-risk transactions:", len(raw_df))

    # --------------------------------------------------
    # JOIN RAW DATA + AGENT DECISIONS
    # --------------------------------------------------

    df = raw_df.merge(
        decisions_df,
        on=[
            "transaction_id",
            "customer_id"
        ],
        how="inner",
        suffixes=("", "_decision")
    )

    print("Joined records:", len(df))

    if len(df) != len(decisions_df):
        raise ValueError(
            "Some agent decisions could not be matched "
            "to the raw transaction data."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # --------------------------------------------------
        # CUSTOMERS
        # --------------------------------------------------

        print("\nLoading customers...")

        for _, row in df.drop_duplicates(
            "customer_id"
        ).iterrows():

            cursor.execute(
                """
                INSERT INTO customers (
                    customer_id,
                    customer_transaction_count,
                    customer_success_rate,
                    preferred_channel,
                    customer_email_available,
                    customer_phone_available
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (customer_id)
                DO NOTHING
                """,
                (
                    row["customer_id"],
                    int(row["customer_transaction_count"]),
                    float(row["customer_success_rate"]),
                    row["preferred_channel"],
                    bool(row["customer_email_available"]),
                    bool(row["customer_phone_available"])
                )
            )

        # --------------------------------------------------
        # TRANSACTIONS
        # --------------------------------------------------

        print("Loading transactions...")

        for _, row in df.iterrows():

            cursor.execute(
                """
                INSERT INTO transactions (
                    transaction_id,
                    customer_id,
                    transaction_amount,
                    payment_method,
                    payment_method_success_rate,
                    channel,
                    product_interest_score,
                    checkout_progress,
                    scenario,
                    payment_status,
                    failure_reason,
                    revenue_at_risk
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (transaction_id)
                DO NOTHING
                """,
                (
                    row["transaction_id"],
                    row["customer_id"],
                    float(row["transaction_amount"]),
                    row["payment_method"],
                    float(row["payment_method_success_rate"]),
                    row["channel"],
                    float(row["product_interest_score"]),
                    float(row["checkout_progress"]),
                    row["scenario"],
                    row["payment_status"],
                    row["failure_reason"],
                    bool(row["revenue_at_risk"])
                )
            )

        # --------------------------------------------------
        # RECOVERY CASES
        # --------------------------------------------------

        print("Loading recovery cases...")

        for _, row in df.iterrows():

            cursor.execute(
                """
                INSERT INTO recovery_cases (
                    transaction_id,
                    recovery_attempts,
                    promise_to_pay,
                    recovered,
                    money_recovered
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (transaction_id)
                DO NOTHING
                """,
                (
                    row["transaction_id"],
                    int(row["recovery_attempts"]),
                    bool(row["promise_to_pay"]),
                    bool(row["recovered"]),
                    float(row["money_recovered"])
                )
            )

        # --------------------------------------------------
        # RECOVERY DECISIONS
        # --------------------------------------------------

        print("Loading recovery decisions...")

        for _, row in df.iterrows():

            cursor.execute(
                """
                SELECT recovery_case_id
                FROM recovery_cases
                WHERE transaction_id = %s
                """,
                (row["transaction_id"],)
            )

            result = cursor.fetchone()

            if result is None:
                raise ValueError(
                    f"Recovery case not found: "
                    f"{row['transaction_id']}"
                )

            recovery_case_id = result[0]

            cursor.execute(
                """
                INSERT INTO recovery_decisions (
                    recovery_case_id,
                    recovery_probability,
                    priority_score,
                    priority,
                    strategy,
                    recovery_action,
                    recommended_channel,
                    expected_recovery_value,
                    reason
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    recovery_case_id,
                    float(row["recovery_probability"]),
                    float(row["priority_score"]),
                    row["priority"],
                    row["strategy"],
                    row["recovery_action"],
                    row["recommended_channel"],
                    float(row["expected_recovery_value"]),
                    row["reason"]
                )
            )

        # --------------------------------------------------
        # COMMIT
        # --------------------------------------------------

        connection.commit()

        print("\n======================================")
        print("DATABASE LOAD COMPLETE")
        print("======================================")

        print(
            "Customers:",
            df["customer_id"].nunique()
        )

        print(
            "Transactions:",
            len(df)
        )

        print(
            "Recovery cases:",
            len(df)
        )

        print(
            "Recovery decisions:",
            len(df)
        )

    except Exception as e:

        connection.rollback()

        print("\nDATABASE ERROR:")
        print(e)

        raise

    finally:

        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()