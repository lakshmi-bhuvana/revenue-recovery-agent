import joblib
import pandas as pd

from src.ml.feature_engineering import create_features


MODEL_PATH = "models/recovery_model.pkl"


class RecoveryScorer:

    def __init__(self):
        self.model = joblib.load(MODEL_PATH)

    def score(self, transaction):

        # Convert single transaction into DataFrame
        df = pd.DataFrame([transaction])

        # Create engineered features
        df = create_features(df)

        # Remove fields that the ML model should not see
        drop_columns = [
            "transaction_id",
            "customer_id",
            "revenue_at_risk",
            "recovered",
            "money_recovered",
            "promise_to_pay"
        ]

        X = df.drop(
            columns=drop_columns,
            errors="ignore"
        )

        # ML recovery probability
        recovery_probability = self.model.predict_proba(X)[0][1]

        # --------------------------------------------------
        # BUSINESS PRIORITY
        # --------------------------------------------------

        transaction_amount = float(
            transaction["transaction_amount"]
        )

        customer_intent = float(
            df["customer_intent"].iloc[0]
        )

        customer_reliability = float(
            df["customer_reliability"].iloc[0]
        )

        contactability = float(
            df["contactability"].iloc[0]
        )

        recovery_friction = float(
            df["recovery_friction"].iloc[0]
        )

        # Normalize transaction value.
        # ₹50,000 is treated as the upper reference point.
        value_score = min(
            transaction_amount / 50000,
            1.0
        )

        # Higher friction should reduce priority.
        friction_score = 1 - recovery_friction
        

        # --------------------------------------------------
        # COMBINED PRIORITY SCORE
        # --------------------------------------------------

        priority_score = (
            0.35 * recovery_probability +
            0.15 * value_score +
            0.20 * customer_intent +
            0.15 * customer_reliability +
            0.10 * contactability +
            0.05 * friction_score
        )

        # --------------------------------------------------
        # PRIORITY LEVEL
        # --------------------------------------------------

        if priority_score >= 0.75:
            priority = "HIGH"

        elif priority_score >= 0.55:
            priority = "MEDIUM"

        else:
            priority = "LOW"

        # --------------------------------------------------
        # RECOMMENDED CHANNEL
        # --------------------------------------------------

        preferred_channel = transaction.get(
            "preferred_channel"
        )

        if preferred_channel:
            recommended_channel = preferred_channel

        elif transaction.get("customer_phone_available") == 1:
            recommended_channel = "sms"

        elif transaction.get("customer_email_available") == 1:
            recommended_channel = "email"

        else:
            recommended_channel = "none"

        # --------------------------------------------------
        # RETURN RESULT
        # --------------------------------------------------

        return {
            "recovery_probability": round(
                recovery_probability,
                4
            ),

            "priority_score": round(
                priority_score,
                4
            ),

            "priority": priority,

            "recommended_channel":
                recommended_channel,

            "transaction_amount":
                transaction_amount,

            "customer_intent":
                round(customer_intent, 4),

            "customer_reliability":
                round(customer_reliability, 4),

            "contactability":
                round(contactability, 4),

            "recovery_friction":
                round(recovery_friction, 4)
        }


# --------------------------------------------------
# TEST THE SCORER
# --------------------------------------------------

if __name__ == "__main__":

    scorer = RecoveryScorer()

    test_transaction = {
        "transaction_id": "test_001",
        "customer_id": "cust_test",

        "transaction_amount": 35000,
        "customer_transaction_count": 8,
        "customer_success_rate": 0.88,

        "payment_method": "CARD",
        "payment_method_success_rate": 0.91,

        "channel": "payment_link",
        "preferred_channel": "whatsapp",

        "product_interest_score": 0.91,
        "checkout_progress": 0.82,

        "customer_email_available": 1,
        "customer_phone_available": 1,

        "scenario": "payment_failure",
        "payment_status": "failed",
        "failure_reason": "bank_decline",

        "revenue_at_risk": 1,
        "recovery_attempts": 0,
        "promise_to_pay": 0,
        "recovered": 0,
        "money_recovered": 0
    }

    result = scorer.score(test_transaction)

    print("\n======================================")
    print("RECOVERY SCORER TEST")
    print("======================================")

    for key, value in result.items():
        print(f"{key}: {value}")

