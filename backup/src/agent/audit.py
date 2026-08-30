from datetime import datetime


def create_audit_event(
    transaction,
    diagnosis,
    score,
    action,
    policy,
    execution,
    stopping,
    escalation
):
    """
    Creates a complete audit record for one agent decision.
    """

    return {
        "timestamp": datetime.utcnow().isoformat(),

        "transaction_id": transaction.get(
            "transaction_id"
        ),

        "customer_id": transaction.get(
            "customer_id"
        ),

        "scenario": transaction.get(
            "scenario"
        ),

        "transaction_amount": transaction.get(
            "transaction_amount"
        ),

        "diagnosis": diagnosis.get(
            "diagnosis"
        ),

        "diagnosis_reason": diagnosis.get(
            "reason"
        ),

        "recovery_probability": score.get(
            "recovery_probability"
        ),

        "priority_score": score.get(
            "priority_score"
        ),

        "priority": score.get(
            "priority"
        ),

        "strategy": action.get(
            "strategy"
        ),

        "recovery_action": action.get(
            "recovery_action"
        ),

        "recommended_channel": action.get(
            "channel"
        ),

        "policy_allowed": policy.get(
            "allowed"
        ),

        "policy_reason": policy.get(
            "reason"
        ),

        "execution_status": execution.get(
            "execution_status"
        ),

        "recovered": execution.get(
            "recovered",
            False
        ),

        "money_recovered": execution.get(
            "money_recovered",
            0.0
        ),

        "attempt_increment": execution.get(
            "attempt_increment"
        ),

        "stopped": stopping.get(
            "stop"
        ),

        "stopping_reason": stopping.get(
            "reason"
        ),

        # -----------------------------------------
        # ESCALATION
        # -----------------------------------------

        "escalate": escalation.get(
            "escalate",
            False
        ),

        "escalation_level": escalation.get(
            "escalation_level",
            "NONE"
        ),

        "escalation_reason": escalation.get(
            "reason"
        ),

        "recommended_team": escalation.get(
            "recommended_team"
        )
    }