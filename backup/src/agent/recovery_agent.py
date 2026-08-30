from src.agent.diagnosis import diagnose
from src.agent.action_policy import choose_action
from src.agent.policy_engine import check_policy
from src.agent.actions import execute_action
from src.agent.stopping_rules import check_stopping_rule
from src.agent.audit import create_audit_event
from src.agent.escalation import check_escalation


class RecoveryAgent:

    def __init__(self, scorer):
        self.scorer = scorer

    def process(self, transaction):

        # -----------------------------------------
        # 1. CHECK STOPPING RULE BEFORE ACTION
        # -----------------------------------------

        stopping = check_stopping_rule(transaction)

        if stopping["stop"]:

            # -----------------------------------------
            # ESCALATION FOR EARLY STOP
            # -----------------------------------------

            if stopping["reason"] == (
                "maximum_recovery_attempts_reached"
            ):
                escalation = {
                    "escalate": True,
                    "escalation_level": "HIGH",
                    "reason": (
                        "maximum_recovery_attempts_reached"
                    ),
                    "recommended_team": "revenue_operations",
                }

            elif stopping["reason"] in (
                "payment_already_recovered",
                "invoice_already_paid",
            ):
                escalation = {
                    "escalate": False,
                    "escalation_level": "NONE",
                    "reason": stopping["reason"],
                    "recommended_team": None,
                }

            else:
                escalation = {
                    "escalate": True,
                    "escalation_level": "HIGH",
                    "reason": stopping["reason"],
                    "recommended_team": "revenue_operations",
                }

            return {
                "status": "stopped",
                "transaction_id": transaction.get(
                    "transaction_id"
                ),
                "customer_id": transaction.get(
                    "customer_id"
                ),
                "stopping": stopping,
                "escalation": escalation,
                "audit": {
                    "transaction_id": transaction.get(
                        "transaction_id"
                    ),
                    "customer_id": transaction.get(
                        "customer_id"
                    ),
                    "stopped": True,
                    "stopping_reason": stopping["reason"],
                    "escalate": escalation["escalate"],
                    "escalation_level": (
                        escalation["escalation_level"]
                    ),
                    "escalation_reason": (
                        escalation["reason"]
                    ),
                    "recommended_team": (
                        escalation["recommended_team"]
                    ),
                },
            }

        # -----------------------------------------
        # 2. DIAGNOSE
        # -----------------------------------------

        diagnosis = diagnose(transaction)

        # -----------------------------------------
        # 3. ML PREDICTION
        # -----------------------------------------

        score = self.scorer.score(transaction)

        # -----------------------------------------
        # 4. SELECT ACTION
        # -----------------------------------------

        action = choose_action(
            transaction,
            score,
            diagnosis,
        )

        # -----------------------------------------
        # 5. POLICY CHECK
        # -----------------------------------------

        policy = check_policy(
            transaction,
            score,
            action["recovery_action"],
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
                "execution_detail": (
                    "Action blocked by recovery policy."
                ),
            }

            stopping_result = {
                "stop": True,
                "reason": policy["reason"],
            }

        else:

            # -----------------------------------------
            # 6. EXECUTE SIMULATED RECOVERY ACTION
            # -----------------------------------------

            transaction["_recovery_probability"] = (
                score["recovery_probability"]
            )

            execution = execute_action(
                transaction,
                action["recovery_action"],
                action["channel"],
            )

            # -----------------------------------------
            # 7. UPDATE TRANSACTION STATE
            # -----------------------------------------

            current_attempts = int(
                transaction.get(
                    "recovery_attempts",
                    0,
                )
                or 0
            )

            transaction["recovery_attempts"] = (
                current_attempts
                + execution.get(
                    "attempt_increment",
                    0,
                )
            )

            if execution.get("recovered"):

                transaction["recovered"] = 1

                transaction["money_recovered"] = (
                    execution.get(
                        "money_recovered",
                        0.0,
                    )
                )

                transaction["payment_status"] = "paid"

                # -----------------------------------------
                # SUCCESSFUL RECOVERY = STOP
                # -----------------------------------------

                stopping_result = {
                    "stop": True,
                    "reason": "PAYMENT_SUCCESS",
                }

            else:

                # -----------------------------------------
                # 8. CHECK STOPPING RULE AFTER FAILED ACTION
                # -----------------------------------------

                stopping_result = check_stopping_rule(
                    transaction
                )

        # -----------------------------------------
        # 9. ESCALATION
        # -----------------------------------------

        escalation = check_escalation(
            transaction,
            score,
            policy,
            execution,
            stopping_result,
        )

        # -----------------------------------------
        # 10. AUDIT
        # -----------------------------------------

        audit = create_audit_event(
            transaction,
            diagnosis,
            score,
            action,
            policy,
            execution,
            stopping_result,
            escalation,
        )

        # -----------------------------------------
        # 11. FINAL STATUS
        # -----------------------------------------

        if execution.get("recovered"):

            final_status = "recovered"

        elif stopping_result["stop"]:

            final_status = "stopped"

        else:

            final_status = execution[
                "execution_status"
            ]

        # -----------------------------------------
        # 12. RETURN COMPLETE AGENT RESULT
        # -----------------------------------------

        return {
            "status": final_status,
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
            "escalation": escalation,
            "audit": audit,
        }