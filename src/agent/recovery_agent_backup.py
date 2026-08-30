from src.agent.diagnosis import diagnose
from src.agent.action_policy import choose_action
from src.agent.policy_engine import check_policy
from src.agent.actions import execute_action
from src.agent.stopping_rules import check_stopping_rule
from src.agent.audit import create_audit_event


class RecoveryAgent:

    def __init__(self, scorer):
        self.scorer = scorer

    def process(self, transaction):

        # -----------------------------------------
        # 1. CHECK STOPPING RULE
        # -----------------------------------------

        stopping = check_stopping_rule(
            transaction
        )

        if stopping["stop"]:

            return {
                "status": "stopped",
                "stopping_reason": stopping["reason"],
                "audit": {
                    "transaction_id": transaction.get(
                        "transaction_id"
                    ),
                    "stopped": True,
                    "stopping_reason": stopping["reason"]
                }
            }

        # -----------------------------------------
        # 2. DIAGNOSE
        # -----------------------------------------

        diagnosis = diagnose(
            transaction
        )

        # -----------------------------------------
        # 3. ML PREDICTION
        # -----------------------------------------

        score = self.scorer.score(
            transaction
        )

        # -----------------------------------------
        # 4. SELECT ACTION
        # -----------------------------------------

        action = choose_action(
            transaction,
            score,
            diagnosis
        )

        # -----------------------------------------
        # 5. POLICY CHECK
        # -----------------------------------------

        policy = check_policy(
            transaction,
            score,
            action["recovery_action"]
        )

        if not policy["allowed"]:

            execution = {
                "execution_status": "blocked",
                "action": action["recovery_action"],
                "channel": action["channel"],
                "attempt_increment": 0,
                "message_sent": False,
                "recovered": False,
                "money_recovered": 0.0,
                "execution_detail": "Action blocked by recovery policy."
            }

            stopping_result = {
                "stop": True,
                "reason": policy["reason"]
            }

        else:

            # -----------------------------------------
            # 6. EXECUTE
            # -----------------------------------------

            transaction["_recovery_probability"] = (
                score["recovery_probability"]
            )

            execution = execute_action(
                transaction,
                action["recovery_action"],
                action["channel"]
            )

            # -----------------------------------------
            # 7. CHECK STOPPING RULE AGAIN
            # -----------------------------------------

            stopping_result = {
                "stop": False,
                "reason": "action_executed"
            }

        # -----------------------------------------
        # 8. AUDIT
        # -----------------------------------------

        audit = create_audit_event(
            transaction,
            diagnosis,
            score,
            action,
            policy,
            execution,
            stopping_result
        )

        # -----------------------------------------
        # 9. RETURN COMPLETE RESULT
        # -----------------------------------------

        return {
            "status": execution["execution_status"],
            "transaction_id": transaction.get(
                "transaction_id"
            ),
            "customer_id": transaction.get(
                "customer_id"
            ),
            "diagnosis": diagnosis,
            "score": score,
            "action": action,
            "policy": policy,
            "execution": execution,
            "stopping": stopping_result,
            "audit": audit
        }