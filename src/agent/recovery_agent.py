from src.agent.diagnosis import diagnose
from src.agent.action_policy import choose_action
from src.agent.policy_engine import check_policy
from src.agent.actions import execute_action
from src.agent.stopping_rules import check_stopping_rule
from src.agent.audit import create_audit_event
from src.agent.escalation import check_escalation
from src.agent.action_optimizer import optimize_recovery_action


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
            # EARLY STOP ESCALATION
            # -----------------------------------------

            if stopping["reason"] == (
                "maximum_recovery_attempts_reached"
            ):

                escalation = {
                    "escalate": True,
                    "escalation_level": "MEDIUM",
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

            # -----------------------------------------
            # EARLY STOP AUDIT
            # -----------------------------------------

            audit = {
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
                "audit": audit,
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
        # ACTION UTILITY OPTIMIZER
        # -----------------------------------------
        #
        # ML predicts recoverability.
        # The optimizer ranks the available recovery
        # actions using pre-recovery signals.
        #
        # Human review is escalation only and is never
        # passed to execute_action().
        # -----------------------------------------
        optimizer_result = optimize_recovery_action(
            transaction,
            score,
            diagnosis,
        )
        optimizer_selected_action = (
            optimizer_result.get(
                "selected_action",
                "",
            )
            if isinstance(
                optimizer_result,
                dict,
            )
            else ""
        )
        optimizer_selected_channel = (
            optimizer_result.get(
                "channel",
                "",
            )
            if isinstance(
                optimizer_result,
                dict,
            )
            else ""
        )
        optimizer_selected_strategy = (
            optimizer_result.get(
                "strategy",
                "",
            )
            if isinstance(
                optimizer_result,
                dict,
            )
            else ""
        )
        optimizer_requires_human_review = (
            bool(
                optimizer_result.get(
                    "requires_human_review",
                    False,
                )
            )
            if isinstance(
                optimizer_result,
                dict,
            )
            else False
        )
        optimizer_reason = (
            optimizer_result.get(
                "reason",
                "",
            )
            if isinstance(
                optimizer_result,
                dict,
            )
            else ""
        )
        optimizer_candidates = (
            optimizer_result.get(
                "candidates",
                [],
            )
            if isinstance(
                optimizer_result,
                dict,
            )
            else []
        )
        # Keep the existing action-policy result as the
        # fallback, but allow the optimizer to select the
        # automated execution path.
        action = dict(
            action
        )
        if (
            optimizer_selected_action
            and not optimizer_requires_human_review
        ):
            action[
                "recovery_action"
            ] = optimizer_selected_action
            if optimizer_selected_channel:
                action[
                    "channel"
                ] = optimizer_selected_channel
            if optimizer_selected_strategy:
                action[
                    "strategy"
                ] = optimizer_selected_strategy
        optimizer_evidence = {
            "selected_action":
                optimizer_selected_action,
            "selected_channel":
                optimizer_selected_channel,
            "selected_strategy":
                optimizer_selected_strategy,
            "requires_human_review":
                optimizer_requires_human_review,
            "reason":
                optimizer_reason,
            "candidates":
                optimizer_candidates,
        }
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
            # 6. EXECUTE RECOVERY ACTION
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
            # 7. UPDATE ATTEMPT COUNT
            #
            # This MUST happen immediately after
            # the action so escalation sees the
            # current attempt number.
            # -----------------------------------------

            current_attempts = int(
                transaction.get(
                    "recovery_attempts",
                    0,
                )
                or 0
            )

            attempt_increment = execution.get(
                "attempt_increment",
                0,
            )

            transaction["recovery_attempts"] = (
                current_attempts
                + attempt_increment
            )

            # -----------------------------------------
            # 8. SUCCESSFUL RECOVERY
            # -----------------------------------------

            if execution.get("recovered"):

                transaction["recovered"] = 1

                transaction["money_recovered"] = (
                    execution.get(
                        "money_recovered",
                        0.0,
                    )
                )

                transaction["payment_status"] = "paid"

                stopping_result = {
                    "stop": True,
                    "reason": "PAYMENT_SUCCESS",
                }

            else:

                # -----------------------------------------
                # 9. CHECK STOPPING RULE AFTER FAILED
                #    RECOVERY ACTION
                # -----------------------------------------

                stopping_result = check_stopping_rule(
                    transaction
                )

        # -----------------------------------------
        # 10. ESCALATION
        #
        # IMPORTANT:
        #
        # The escalation function sees the updated
        # recovery_attempts value.
        #
        # Attempt 1:
        #   HIGH     -> escalate
        #   MEDIUM   -> continue
        #
        # Attempt 2:
        #   MEDIUM   -> continue
        #
        # Attempt 3:
        #   MEDIUM   -> escalate
        # -----------------------------------------

        escalation = check_escalation(
            transaction,
            score,
            policy,
            execution,
            stopping_result,
		action
        )

        # -----------------------------------------
        # 11. AUDIT
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
        # 12. FINAL STATUS
        # -----------------------------------------

        if execution.get("recovered"):

            final_status = "recovered"

        elif escalation.get("escalate"):

            # Human/team escalation means automated
            # recovery stops.
            final_status = "stopped"

        elif stopping_result["stop"]:

            final_status = "stopped"

        else:

            final_status = execution[
                "execution_status"
            ]

        # -----------------------------------------
        # 13. RETURN COMPLETE AGENT RESULT
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
            "optimizer": optimizer_evidence,
            "policy": policy,
            "execution": execution,
            "stopping": stopping_result,
            "escalation": escalation,
            "audit": audit,
        }