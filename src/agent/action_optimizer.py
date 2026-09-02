from typing import Any
MAX_RECOVERY_ATTEMPTS = 3
def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = low
    return max(low, min(high, value))
def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
def _candidate(
    name: str,
    suitability: float,
    channel: str,
    strategy: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "suitability": round(
            _clamp(suitability),
            4,
        ),
        "channel": channel,
        "strategy": strategy,
        "reason": reason,
    }
def optimize_recovery_action(
    transaction: dict[str, Any],
    score: dict[str, Any],
    diagnosis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Rank recovery actions using pre-recovery signals.
    The ML model estimates recoverability.
    This optimizer converts the model assessment into
    an action decision.
    Post-outcome fields such as:
        recovered
        money_recovered
        final payment status
    are intentionally ignored to avoid leakage.
    Human review is treated as an escalation path and
    is never returned as an automated execution action.
    """
    diagnosis = diagnosis or {}
    scenario = str(
        transaction.get("scenario")
        or diagnosis.get("diagnosis")
        or score.get("scenario")
        or "payment_failure"
    ).strip().lower()
    recovery_probability = _clamp(
        score.get(
            "recovery_probability",
            0.0,
        )
    )
    priority_score = _clamp(
        score.get(
            "priority_score",
            0.0,
        )
    )
    customer_reliability = _clamp(
        score.get(
            "customer_reliability",
            0.0,
        )
    )
    contactability = _clamp(
        score.get(
            "contactability",
            0.0,
        )
    )
    recovery_friction = _clamp(
        score.get(
            "recovery_friction",
            0.0,
        )
    )
    customer_intent = _clamp(
        score.get(
            "customer_intent",
            0.0,
        )
    )
    attempts = max(
        0,
        min(
            _safe_int(
                transaction.get(
                    "recovery_attempts",
                    0,
                )
            ),
            MAX_RECOVERY_ATTEMPTS,
        ),
    )
    attempts_remaining = max(
        0,
        MAX_RECOVERY_ATTEMPTS - attempts,
    )
    # ---------------------------------------------------------
    # BASE UTILITY
    # ---------------------------------------------------------
    #
    # The model probability carries the largest weight,
    # while customer quality, reachability, intent and
    # friction influence expected action utility.
    #
    # ---------------------------------------------------------
    base_utility = (
        0.45 * recovery_probability
        + 0.20 * customer_reliability
        + 0.15 * contactability
        + 0.10 * customer_intent
        + 0.10 * (1.0 - recovery_friction)
    )
    candidates: list[dict[str, Any]] = []
    # ---------------------------------------------------------
    # CHECKOUT ABANDONMENT
    # ---------------------------------------------------------
    if scenario == "checkout_abandonment":
        candidates.append(
            _candidate(
                "checkout_reminder",
                (
                    base_utility
                    + 0.08 * customer_intent
                    + 0.04 * contactability
                ),
                "whatsapp",
                "model_guided_recovery",
                (
                    "Strong checkout intent and reachable customer "
                    "support a low-friction checkout reminder."
                ),
            )
        )
        candidates.append(
            _candidate(
                "payment_link_follow_up",
                (
                    base_utility
                    - 0.05
                    + 0.04 * contactability
                ),
                "whatsapp",
                "adaptive_recovery",
                (
                    "A direct payment-link follow-up is a fallback "
                    "when the reminder does not convert."
                ),
            )
        )
    # ---------------------------------------------------------
    # MANDATE FAILURE
    # ---------------------------------------------------------
    elif scenario == "mandate_failure":
        candidates.append(
            _candidate(
                "retry_mandate",
                (
                    base_utility
                    + 0.08 * customer_reliability
                    + 0.03 * (
                        attempts_remaining
                        / MAX_RECOVERY_ATTEMPTS
                    )
                ),
                "whatsapp",
                "model_guided_recovery",
                (
                    "The failure is mandate-specific and customer "
                    "history supports another bounded mandate attempt."
                ),
            )
        )
        candidates.append(
            _candidate(
                "payment_link_follow_up",
                base_utility - 0.06,
                "whatsapp",
                "adaptive_recovery",
                (
                    "A payment link provides an alternative "
                    "completion path after mandate failure."
                ),
            )
        )
    # ---------------------------------------------------------
    # FAILED SUBSCRIPTION
    # ---------------------------------------------------------
    elif scenario == "failed_subscription":
        candidates.append(
            _candidate(
                "retry_subscription_payment",
                (
                    base_utility
                    + 0.06 * customer_reliability
                ),
                "email",
                "model_guided_recovery",
                (
                    "The subscription-specific retry directly "
                    "addresses the recurring payment failure."
                ),
            )
        )
        candidates.append(
            _candidate(
                "payment_link_follow_up",
                base_utility - 0.06,
                "email",
                "adaptive_recovery",
                (
                    "An alternate payment path is available "
                    "after a failed subscription retry."
                ),
            )
        )
    # ---------------------------------------------------------
    # B2B RECEIVABLE
    # ---------------------------------------------------------
    elif scenario == "b2b_receivable":
        candidates.append(
            _candidate(
                "send_invoice_reminder",
                (
                    base_utility
                    + 0.05 * customer_reliability
                    + 0.03 * contactability
                ),
                "email",
                "model_guided_recovery",
                (
                    "An invoice reminder addresses the overdue "
                    "receivable with low execution friction."
                ),
            )
        )
        candidates.append(
            _candidate(
                "payment_link_follow_up",
                base_utility - 0.08,
                "email",
                "adaptive_recovery",
                (
                    "A payment link is a fallback when the "
                    "invoice reminder remains unresolved."
                ),
            )
        )
    # ---------------------------------------------------------
    # PAYMENT FAILURE / DEFAULT
    # ---------------------------------------------------------
    else:
        candidates.append(
            _candidate(
                "retry_payment",
                (
                    base_utility
                    + 0.05 * customer_reliability
                    + 0.04 * contactability
                ),
                "whatsapp",
                "model_guided_recovery",
                (
                    "Predicted recoverability, customer reliability "
                    "and reachability support a direct payment retry."
                ),
            )
        )
        candidates.append(
            _candidate(
                "payment_link_follow_up",
                (
                    base_utility
                    - 0.04
                    + 0.03 * contactability
                ),
                "whatsapp",
                "adaptive_recovery",
                (
                    "A payment link is a lower-friction fallback "
                    "when direct retry is less attractive."
                ),
            )
        )
    # ---------------------------------------------------------
    # HUMAN REVIEW / ESCALATION UTILITY
    # ---------------------------------------------------------
    human_review_score = (
        0.20
        + 0.25 * (1.0 - recovery_probability)
        + 0.20 * recovery_friction
        + 0.20 * (
            attempts
            / MAX_RECOVERY_ATTEMPTS
        )
        + 0.15 * (1.0 - contactability)
    )
    if priority_score >= 0.75:
        human_review_score += 0.03
    candidates.append(
        _candidate(
            "human_review",
            human_review_score,
            "none",
            "controlled_escalation",
            (
                "Human review becomes more appropriate when "
                "recoverability is weak, friction is high, "
                "contactability is limited, or retry capacity "
                "is being exhausted."
            ),
        )
    )
    # ---------------------------------------------------------
    # RANK
    # ---------------------------------------------------------
    candidates.sort(
        key=lambda item: item["suitability"],
        reverse=True,
    )
    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):
        candidate["rank"] = rank
    # ---------------------------------------------------------
    # AUTOMATED SELECTION
    # ---------------------------------------------------------
    #
    # Never execute human_review through execute_action().
    # It represents escalation only.
    #
    # ---------------------------------------------------------
    automated_candidates = [
        candidate
        for candidate in candidates
        if candidate["name"] != "human_review"
    ]
    if automated_candidates:
        selected = automated_candidates[0]
    else:
        selected = next(
            candidate
            for candidate in candidates
            if candidate["name"] == "human_review"
        )
    requires_human_review = (
        selected["name"] == "human_review"
    )
    return {
        "selected_action": selected["name"],
        "channel": selected["channel"],
        "strategy": selected["strategy"],
        "reason": selected["reason"],
        "requires_human_review": requires_human_review,
        "attempts": attempts,
        "attempts_remaining": attempts_remaining,
        "candidates": candidates,
    }
