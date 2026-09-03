import json
import os
import time
from contextvars import ContextVar
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free",
)
LLM_TIMEOUT_SECONDS = float(
    os.getenv(
        "LLM_TIMEOUT_SECONDS",
        "12",
    )
)
_llm_status: ContextVar[dict[str, Any]] = ContextVar(
    "llm_status",
    default={
        "provider": "openrouter",
        "model": OPENROUTER_MODEL,
        "status": "not_called",
        "latency_ms": 0,
        "error": "",
    },
)
def _set_status(
    *,
    status: str,
    latency_ms: float = 0.0,
    model: str | None = None,
    error: str = "",
) -> None:
    _llm_status.set(
        {
            "provider": "openrouter",
            "model": model or OPENROUTER_MODEL,
            "status": status,
            "latency_ms": round(
                latency_ms,
                2,
            ),
            "error": error,
        }
    )
def get_llm_status() -> dict[str, Any]:
    """Return request-local LLM telemetry without exposing secrets."""
    return dict(
        _llm_status.get()
    )
def _client() -> OpenAI | None:
    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )
    if not api_key:
        _set_status(
            status="not_configured",
            error="OPENROUTER_API_KEY is not configured.",
        )
        return None
    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=0,
    )
def _call_llm(
    system_prompt: str,
    user_prompt: str,
) -> str:
    client = _client()
    if client is None:
        return ""
    started = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.2,
        )
        latency_ms = (
            time.perf_counter()
            - started
        ) * 1000
        content = (
            response.choices[0].message.content
            if response.choices
            else ""
        )
        actual_model = getattr(
            response,
            "model",
            None,
        )
        if not content:
            _set_status(
                status="empty_response",
                latency_ms=latency_ms,
                model=actual_model,
            )
            return ""
        _set_status(
            status="success",
            latency_ms=latency_ms,
            model=actual_model,
        )
        return content.strip()
    except Exception as exc:
        latency_ms = (
            time.perf_counter()
            - started
        ) * 1000
        _set_status(
            status="error",
            latency_ms=latency_ms,
            error=(
                f"{type(exc).__name__}: "
                f"{str(exc)[:240]}"
            ),
        )
        return ""
def _deterministic_decision_explanation(
    context: dict[str, Any],
) -> str:
    action = str(
        context.get(
            "selected_action",
            "recovery action",
        )
        or "recovery action"
    ).replace(
        "_",
        " ",
    )
    scenario = str(
        context.get(
            "scenario",
            "revenue risk",
        )
        or "revenue risk"
    ).replace(
        "_",
        " ",
    )
    probability = float(
        context.get(
            "recovery_probability",
            0.0,
        )
        or 0.0
    )
    channel = str(
        context.get(
            "channel",
            "the available channel",
        )
        or "the available channel"
    )
    return (
        f"The Recovery Agent selected {action} for this "
        f"{scenario} case based on a {probability:.2%} "
        f"predicted recovery probability and the available "
        f"{channel} contact path."
    )
def explain_decision(
    context: dict[str, Any],
) -> str:
    """
    Explain an existing deterministic recovery decision.
    The LLM does not choose or authorize the action.
    """
    safe_context = {
        "scenario": context.get(
            "scenario"
        ),
        "recovery_probability": context.get(
            "recovery_probability"
        ),
        "priority": context.get(
            "priority"
        ),
        "customer_reliability": context.get(
            "customer_reliability"
        ),
        "contactability": context.get(
            "contactability"
        ),
        "recovery_friction": context.get(
            "recovery_friction"
        ),
        "selected_action": context.get(
            "selected_action"
        ),
        "channel": context.get(
            "channel"
        ),
        "strategy": context.get(
            "strategy"
        ),
    }
    system_prompt = """
You are the explanation layer for the Revenue Recovery Agent.
Explain an already-made recovery decision clearly and briefly.
Rules:
- Never invent customer facts.
- Never recommend an action different from selected_action.
- Never authorize payments.
- Never change policy, attempts, stopping, or escalation.
- Treat application-provided values as authoritative.
- Return one concise paragraph.
""".strip()
    user_prompt = (
        "Explain this existing decision:\n\n"
        + json.dumps(
            safe_context,
            indent=2,
        )
    )
    result = _call_llm(
        system_prompt,
        user_prompt,
    )
    if result:
        return result
    return _deterministic_decision_explanation(
        context
    )
def _deterministic_recovery_message(
    context: dict[str, Any],
) -> str:
    action = str(
        context.get(
            "selected_action",
            "",
        )
        or ""
    )
    messages = {
        "payment_link_follow_up":
            "Please use the secure payment link to complete your payment.",
        "retry_payment":
            "Your recent payment could not be completed. Please retry using the secure payment option.",
        "checkout_reminder":
            "You started a checkout but did not complete the payment. Please use the secure payment option to continue.",
        "send_invoice_reminder":
            "Your invoice is still outstanding. Please complete the payment using the secure payment option.",
        "retry_mandate":
            "Your recurring payment could not be completed. Please use the secure payment option to update or retry it.",
        "retry_subscription_payment":
            "Your subscription payment could not be completed. Please use the secure payment option to complete it.",
    }
    return messages.get(
        action,
        "A secure payment option is available to complete the recovery process.",
    )
def generate_recovery_message(
    context: dict[str, Any],
) -> str:
    """
    Generate a customer-facing message for an already-authorized action.
    """
    safe_context = {
        "scenario": context.get(
            "scenario"
        ),
        "selected_action": context.get(
            "selected_action"
        ),
        "channel": context.get(
            "channel"
        ),
        "language": context.get(
            "language",
            "English",
        ),
    }
    system_prompt = """
You generate a concise customer-facing recovery message
for an already-authorized action.
Rules:
- Never invent amounts, dates, links, discounts, deadlines,
  account details, or transaction facts.
- Never claim payment succeeded.
- Never threaten or pressure the customer.
- Never introduce a different recovery action.
- Return only the message.
""".strip()
    user_prompt = (
        "Generate the message for:\n\n"
        + json.dumps(
            safe_context,
            indent=2,
        )
    )
    result = _call_llm(
        system_prompt,
        user_prompt,
    )
    if result:
        return result
    return _deterministic_recovery_message(
        context
    )
def _deterministic_response_interpretation(
    response_text: str,
) -> dict[str, Any]:
    text = response_text.strip().lower()
    if not text:
        return {
            "interpretation": "NO_RESPONSE",
            "confidence": 1.0,
            "source": "deterministic_fallback",
        }
    payment_success_terms = (
        "paid",
        "payment completed",
        "payment successful",
        "payment succeeded",
        "done with payment",
    )
    promise_terms = (
        "pay tomorrow",
        "pay later",
        "will pay",
        "i'll pay",
        "i will pay",
        "pay by tomorrow",
    )
    difficulty_terms = (
        "cannot pay",
        "can't pay",
        "unable to pay",
        "not able to pay",
        "insufficient funds",
        "no money",
        "cash problem",
    )
    channel_terms = (
        "call me",
        "email me",
        "whatsapp me",
        "contact me on",
        "use email",
        "use whatsapp",
        "call instead",
    )
    if any(
        term in text
        for term in payment_success_terms
    ):
        return {
            "interpretation": "PAYMENT_SUCCESS",
            "confidence": 0.95,
            "source": "deterministic_fallback",
        }
    if any(
        term in text
        for term in promise_terms
    ):
        return {
            "interpretation": "PROMISE_TO_PAY",
            "confidence": 0.90,
            "source": "deterministic_fallback",
        }
    if any(
        term in text
        for term in difficulty_terms
    ):
        return {
            "interpretation": "PAYMENT_DIFFICULTY",
            "confidence": 0.90,
            "source": "deterministic_fallback",
        }
    if any(
        term in text
        for term in channel_terms
    ):
        return {
            "interpretation": "CHANNEL_CHANGE_REQUEST",
            "confidence": 0.85,
            "source": "deterministic_fallback",
        }
    return {
        "interpretation": "UNCLEAR",
        "confidence": 0.0,
        "source": "deterministic_fallback",
    }
def interpret_customer_response(
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    Classify a customer response into a constrained set of labels.
    The deterministic Recovery Agent remains responsible for deciding
    what happens next.
    """
    response_text = str(
        context.get(
            "customer_response",
            "",
        )
        or ""
    ).strip()
    allowed_interpretations = {
        "PAYMENT_SUCCESS",
        "PROMISE_TO_PAY",
        "PAYMENT_DIFFICULTY",
        "NO_RESPONSE",
        "CHANNEL_CHANGE_REQUEST",
        "UNCLEAR",
    }
    if not response_text:
        return {
            "interpretation": "NO_RESPONSE",
            "confidence": 1.0,
            "source": "deterministic_fallback",
        }
    system_prompt = """
You classify customer responses for the Revenue Recovery Agent.
Return exactly one label:
PAYMENT_SUCCESS
PROMISE_TO_PAY
PAYMENT_DIFFICULTY
NO_RESPONSE
CHANNEL_CHANGE_REQUEST
UNCLEAR
Rules:
- PAYMENT_SUCCESS requires a clear statement that payment was completed.
- PROMISE_TO_PAY means the customer intends to pay later.
- PAYMENT_DIFFICULTY means they cannot currently pay or describe inability.
- CHANNEL_CHANGE_REQUEST means they request another contact channel.
- UNCLEAR means ambiguous.
- Never infer payment success from vague language.
Return ONLY valid JSON:
{
  "interpretation": "LABEL",
  "confidence": 0.0
}
""".strip()
    raw = _call_llm(
        system_prompt,
        "Customer response:\n" + response_text,
    )
    if not raw:
        return _deterministic_response_interpretation(
            response_text
        )
    try:
        parsed = json.loads(raw)
        interpretation = str(
            parsed.get(
                "interpretation",
                "UNCLEAR",
            )
        ).strip().upper()
        confidence = float(
            parsed.get(
                "confidence",
                0.0,
            )
        )
        if interpretation not in allowed_interpretations:
            interpretation = "UNCLEAR"
        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )
        return {
            "interpretation": interpretation,
            "confidence": round(
                confidence,
                4,
            ),
            "source": "openrouter",
        }
    except Exception:
        return _deterministic_response_interpretation(
            response_text
        )
