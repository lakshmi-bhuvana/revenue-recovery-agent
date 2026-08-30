from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.agent.recovery_agent import RecoveryAgent
from src.ml.recovery_scorer import RecoveryScorer


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

FRONTEND_DIR = BASE_DIR / "frontend"
CSS_DIR = FRONTEND_DIR / "css"
JS_DIR = FRONTEND_DIR / "js"
DATA_FILE = BASE_DIR / "data" / "raw" / "revenue_recovery.csv"


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Revenue Recovery AI",
    version="1.0.0",
)


# ============================================================
# LIVE EVENTS
# ============================================================

PROCESSED_RECOVERY_EVENTS: dict[str, dict[str, Any]] = {}
LIVE_RECOVERY_STATE: dict[str, dict[str, Any]] = {}
LIVE_EVENTS_FILE = BASE_DIR / "data" / "raw" / "recovery_live_events.json"


def load_live_events() -> None:
    """Load processed recovery events so metrics survive API restarts."""
    global PROCESSED_RECOVERY_EVENTS, LIVE_RECOVERY_STATE

    if not LIVE_EVENTS_FILE.exists():
        return

    try:
        import json

        payload = json.loads(LIVE_EVENTS_FILE.read_text(encoding="utf-8"))
        events = payload.get("events", {}) if isinstance(payload, dict) else {}

        if not isinstance(events, dict):
            return

        PROCESSED_RECOVERY_EVENTS = {
            str(key): value
            for key, value in events.items()
            if isinstance(value, dict)
        }

        for transaction_id, row in PROCESSED_RECOVERY_EVENTS.items():
            LIVE_RECOVERY_STATE[transaction_id] = {
                "recovery_attempts": safe_int(row.get("recovery_attempts")),
                "recovered": normalize_bool(row.get("recovered")),
                "payment_status": safe_string(
                    row.get("payment_status", "failed"),
                    "failed",
                ),
                "money_recovered": safe_float(
                    row.get("money_recovered", 0.0)
                ),
            }
    except Exception:
        # A corrupt optional live-state file must never prevent the API from
        # starting; the base dataset remains available.
        PROCESSED_RECOVERY_EVENTS = {}
        LIVE_RECOVERY_STATE = {}


def save_live_events() -> None:
    """Atomically persist processed recovery events to disk."""
    import json

    LIVE_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "events": PROCESSED_RECOVERY_EVENTS,
    }
    temp_file = LIVE_EVENTS_FILE.with_suffix(".tmp")
    temp_file.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    temp_file.replace(LIVE_EVENTS_FILE)


# ============================================================
# RECOVERY SCENARIOS
# ============================================================

SUPPORTED_SCENARIOS = {
    "payment_failure",
    "checkout_abandonment",
    "failed_subscription",
    "b2b_receivable",
    "mandate_failure",
    "promise_to_pay",
}

SCENARIO_DEFAULTS = {
    "payment_failure": {
        "diagnosis": "payment_failure",
        "action": "retry_payment",
        "strategy": "aggressive_recovery",
        "channel": "whatsapp",
    },
    "checkout_abandonment": {
        "diagnosis": "checkout_abandonment",
        "action": "checkout_reminder",
        "strategy": "assisted_recovery",
        "channel": "whatsapp",
    },
    "failed_subscription": {
        "diagnosis": "subscription_payment_failed",
        "action": "retry_subscription_payment",
        "strategy": "assisted_recovery",
        "channel": "email",
    },
    "b2b_receivable": {
        "diagnosis": "invoice_overdue",
        "action": "send_invoice_reminder",
        "strategy": "standard_recovery",
        "channel": "email",
    },
    "mandate_failure": {
        "diagnosis": "mandate_failed",
        "action": "retry_mandate",
        "strategy": "standard_recovery",
        "channel": "whatsapp",
    },
    "promise_to_pay": {
        "diagnosis": "promise_to_pay_followup",
        "action": "follow_up_promise_to_pay",
        "strategy": "assisted_recovery",
        "channel": "whatsapp",
    },
}

SCENARIO_DIAGNOSIS_REASONS = {
    "checkout_abandonment": (
        "Customer showed purchase intent but did not complete checkout."
    ),
    "failed_subscription": (
        "A recurring subscription payment failed."
    ),
    "b2b_receivable": (
        "A B2B receivable is overdue and requires collection follow-up."
    ),
    "mandate_failure": (
        "The recurring payment mandate failed and requires recovery."
    ),
    "promise_to_pay": (
        "A customer promise to pay requires follow-up."
    ),
    "payment_failure": (
        "The payment transaction failed and requires recovery."
    ),
}


# ============================================================
# REQUEST MODELS
# ============================================================

class RecoveryEvent(BaseModel):
    transaction_id: str
    customer_id: str
    transaction_amount: float = Field(ge=0)

    payment_method: str
    failure_reason: str

    retry_count: int = Field(default=0, ge=0)

    customer_transaction_count: int = Field(default=1, ge=1)
    customer_success_rate: float = Field(default=0.8, ge=0, le=1)
    payment_method_success_rate: float = Field(default=0.8, ge=0, le=1)

    channel: str = "payment_link"
    preferred_channel: str | None = None

    product_interest_score: float = Field(default=0.5, ge=0, le=1)
    checkout_progress: float = Field(default=0.5, ge=0, le=1)

    customer_email_available: int = Field(default=1, ge=0, le=1)
    customer_phone_available: int = Field(default=1, ge=0, le=1)

    scenario: str = "payment_failure"
    payment_status: str = "failed"

    revenue_at_risk: int = Field(default=1, ge=0, le=1)
    recovery_attempts: int = Field(default=0, ge=0)

    promise_to_pay: int = Field(default=0, ge=0, le=1)
    recovered: int = Field(default=0, ge=0, le=1)
    money_recovered: float = Field(default=0.0, ge=0)


class AIMessage(BaseModel):
    role: str
    content: str


class AIQuestion(BaseModel):
    question: str
    conversation: list[AIMessage] = Field(default_factory=list)


# ============================================================
# STATIC FILES
# ============================================================

if CSS_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(CSS_DIR)), name="css")

if JS_DIR.exists():
    app.mount("/js", StaticFiles(directory=str(JS_DIR)), name="js")


# ============================================================
# DATA HELPERS
# ============================================================

def load_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

    return pd.read_csv(DATA_FILE)


def normalize_bool(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)

    if value is None:
        return 0

    if isinstance(value, str):
        return int(
            value.strip().lower()
            in {"true", "1", "yes", "paid", "recovered"}
        )

    try:
        return int(float(value) != 0)
    except (TypeError, ValueError):
        return 0


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    return str(value)


def format_inr(value: float) -> str:
    value = safe_float(value)

    integer_part, decimal_part = f"{value:.2f}".split(".")

    if len(integer_part) <= 3:
        return f"₹{integer_part}.{decimal_part}"

    last_three = integer_part[-3:]
    remaining = integer_part[:-3]

    groups = []

    while len(remaining) > 2:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]

    if remaining:
        groups.insert(0, remaining)

    return f"₹{','.join(groups)},{last_three}.{decimal_part}"


load_live_events()


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_base_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    numeric_defaults = {
        "transaction_amount": 0.0,
        "customer_success_rate": 0.0,
        "payment_method_success_rate": 0.0,
        "product_interest_score": 0.0,
        "checkout_progress": 0.0,
        "customer_transaction_count": 1,
        "customer_email_available": 0,
        "customer_phone_available": 0,
        "recovery_attempts": 0,
        "recovered": 0,
        "money_recovered": 0.0,
        "revenue_at_risk": 1,
        "promise_to_pay": 0,
    }

    for column, default in numeric_defaults.items():
        if column not in df.columns:
            df[column] = default

        df[column] = (
            pd.to_numeric(df[column], errors="coerce")
            .fillna(default)
        )

    string_defaults = {
        "transaction_id": "",
        "customer_id": "",
        "payment_method": "",
        "failure_reason": "",
        "preferred_channel": "",
        "channel": "payment_link",
        "scenario": "payment_failure",
        "payment_status": "failed",
    }

    for column, default in string_defaults.items():
        if column not in df.columns:
            df[column] = default

        df[column] = df[column].fillna(default).astype(str)

    return df


# ============================================================
# SCORING
# ============================================================

def calculate_recovery_probability(df: pd.DataFrame) -> pd.Series:
    probability = (
        0.25
        + 0.30 * df["customer_success_rate"]
        + 0.20 * df["product_interest_score"]
        + 0.15 * df["payment_method_success_rate"]
        + 0.10 * df["checkout_progress"]
    )

    return probability.clip(0, 1)


def calculate_customer_intent(df: pd.DataFrame) -> pd.Series:
    intent = (
        0.60 * df["product_interest_score"]
        + 0.40 * df["checkout_progress"]
    )

    return intent.clip(0, 1)


def calculate_value_score(df: pd.DataFrame) -> pd.Series:
    return (df["transaction_amount"] / 50000).clip(0, 1)


def calculate_priority_score(df: pd.DataFrame) -> pd.Series:
    priority = (
        0.50 * df["recovery_probability"]
        + 0.20 * df["value_score"]
        + 0.20 * df["customer_intent"]
        + 0.10 * df["customer_success_rate"]
    )

    return priority.clip(0, 1)


def assign_priority(score: pd.Series) -> pd.Series:
    priority = pd.Series("LOW", index=score.index)
    priority.loc[score >= 0.55] = "MEDIUM"
    priority.loc[score >= 0.75] = "HIGH"
    return priority


def assign_strategy(score: pd.Series) -> pd.Series:
    strategy = pd.Series("low_cost_recovery", index=score.index)
    strategy.loc[score >= 0.45] = "standard_recovery"
    strategy.loc[score >= 0.60] = "assisted_recovery"
    strategy.loc[score >= 0.75] = "aggressive_recovery"
    return strategy


# ============================================================
# AT-RISK DATA
# ============================================================

def get_at_risk_data() -> pd.DataFrame:
    df = prepare_base_dataframe(load_data())

    if PROCESSED_RECOVERY_EVENTS:
        # Recovery events are an event stream, so they are appended to the
        # dataset rather than replacing a historical row with the same
        # transaction_id.  This is important for demo/test events: a newly
        # processed recovery event must contribute its full recovered amount
        # to aggregate metrics even when its transaction_id happens to match
        # an existing dataset row.
        live_df = prepare_base_dataframe(
            pd.DataFrame(PROCESSED_RECOVERY_EVENTS.values())
        )
        df = pd.concat([df, live_df], ignore_index=True)

    # Re-apply authoritative values from the live agent result.  This is
    # important because pandas normalization can otherwise leave the API
    # with placeholder zeros/empty labels for a freshly processed event.
    if "_agent_result" in df.columns:
        for idx, raw_result in df["_agent_result"].items():
            if not isinstance(raw_result, dict):
                continue
            score = raw_result.get("score") or {}
            action = raw_result.get("action") or {}
            execution = raw_result.get("execution") or {}
            if isinstance(score, dict):
                if score.get("recovery_probability") is not None:
                    df.at[idx, "recovery_probability"] = safe_float(score.get("recovery_probability"))
                if score.get("priority_score") is not None:
                    df.at[idx, "priority_score"] = safe_float(score.get("priority_score"))
                if score.get("priority") is not None:
                    df.at[idx, "priority"] = safe_string(score.get("priority"))
                if score.get("recommended_channel") is not None:
                    df.at[idx, "recommended_channel"] = safe_string(score.get("recommended_channel"))
            if isinstance(action, dict):
                if action.get("strategy") is not None:
                    df.at[idx, "strategy"] = safe_string(action.get("strategy"))
                if action.get("recovery_action") is not None:
                    df.at[idx, "recovery_action"] = safe_string(action.get("recovery_action"))
                if action.get("channel") is not None:
                    df.at[idx, "recommended_channel"] = safe_string(action.get("channel"))
            if isinstance(execution, dict):
                if execution.get("recovered") is not None:
                    df.at[idx, "recovered"] = normalize_bool(execution.get("recovered"))
                if execution.get("money_recovered") is not None:
                    df.at[idx, "money_recovered"] = safe_float(execution.get("money_recovered"))

    df["revenue_at_risk"] = df["revenue_at_risk"].apply(normalize_bool)

    at_risk = df[df["revenue_at_risk"] == 1].copy()

    if at_risk.empty:
        return at_risk

    calculated_probability = calculate_recovery_probability(at_risk)

    if "recovery_probability" not in at_risk.columns:
        at_risk["recovery_probability"] = calculated_probability
    else:
        existing = pd.to_numeric(
            at_risk["recovery_probability"],
            errors="coerce",
        )
        at_risk["recovery_probability"] = existing.fillna(
            calculated_probability
        )

    at_risk["recovery_probability"] = at_risk[
        "recovery_probability"
    ].clip(0, 1)

    at_risk["expected_recovery_value"] = (
        at_risk["transaction_amount"]
        * at_risk["recovery_probability"]
    )

    calculated_intent = calculate_customer_intent(at_risk)

    if "customer_intent" not in at_risk.columns:
        at_risk["customer_intent"] = calculated_intent
    else:
        existing = pd.to_numeric(
            at_risk["customer_intent"],
            errors="coerce",
        )
        at_risk["customer_intent"] = existing.fillna(
            calculated_intent
        )

    at_risk["customer_intent"] = at_risk["customer_intent"].clip(0, 1)

    at_risk["value_score"] = calculate_value_score(at_risk)

    calculated_priority = calculate_priority_score(at_risk)

    if "priority_score" not in at_risk.columns:
        at_risk["priority_score"] = calculated_priority
    else:
        existing = pd.to_numeric(
            at_risk["priority_score"],
            errors="coerce",
        )
        at_risk["priority_score"] = existing.fillna(
            calculated_priority
        )

    at_risk["priority_score"] = at_risk["priority_score"].clip(0, 1)

    calculated_priority_label = assign_priority(
        at_risk["priority_score"]
    )

    if "priority" not in at_risk.columns:
        at_risk["priority"] = calculated_priority_label
    else:
        priority = (
            at_risk["priority"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        missing = priority == ""
        priority.loc[missing] = calculated_priority_label.loc[missing]
        at_risk["priority"] = priority

    calculated_strategy = assign_strategy(at_risk["priority_score"])

    if "strategy" not in at_risk.columns:
        at_risk["strategy"] = calculated_strategy
    else:
        strategy = (
            at_risk["strategy"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        missing = strategy == ""
        strategy.loc[missing] = calculated_strategy.loc[missing]
        at_risk["strategy"] = strategy

    if "recommended_channel" not in at_risk.columns:
        at_risk["recommended_channel"] = at_risk["preferred_channel"]
    else:
        channel = (
            at_risk["recommended_channel"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        missing = channel == ""
        channel.loc[missing] = at_risk.loc[
            missing, "preferred_channel"
        ]
        at_risk["recommended_channel"] = channel

    if "recovery_action" not in at_risk.columns:
        at_risk["recovery_action"] = at_risk["recommended_channel"]

    at_risk["recovery_action_display"] = (
        at_risk["recovery_action"]
        .fillna("")
        .astype(str)
    )

    at_risk["recovered"] = at_risk["recovered"].apply(normalize_bool)

    at_risk["money_recovered"] = (
        pd.to_numeric(
            at_risk["money_recovered"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    return at_risk


# ============================================================
# SCENARIOS
# ============================================================

@app.get("/recovery-scenarios")
async def recovery_scenarios_api():
    return {
        "supported": sorted(SUPPORTED_SCENARIOS),
        "scenarios": [
            {"scenario": name, **defaults}
            for name, defaults in SCENARIO_DEFAULTS.items()
        ],
    }


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

def dashboard_summary(at_risk: pd.DataFrame) -> dict[str, Any]:
    total_cases = len(at_risk)
    recovered_cases = int(at_risk["recovered"].sum())
    total_risk = float(at_risk["transaction_amount"].sum())
    actual_recovered = float(at_risk["money_recovered"].sum())
    expected_recovery = float(at_risk["expected_recovery_value"].sum())
    recovery_rate = recovered_cases / total_cases * 100 if total_cases else 0.0
    recovery_customers = int(at_risk["customer_id"].nunique())
    raw_data = load_data()
    total_dataset_customers = int(raw_data["customer_id"].nunique()) if "customer_id" in raw_data.columns else 0
    recovery_coverage = recovery_customers / total_dataset_customers * 100 if total_dataset_customers else 0.0

    if "recovery_attempts" in at_risk.columns:
        retry_series = pd.to_numeric(at_risk["recovery_attempts"], errors="coerce").fillna(0.0)
    elif "attempt_count" in at_risk.columns:
        retry_series = pd.to_numeric(at_risk["attempt_count"], errors="coerce").fillna(0.0)
    else:
        retry_series = pd.Series(0.0, index=at_risk.index)

    total_retries = int(retry_series.sum())
    intervention_cases = int((retry_series > 0).sum())
    recovery_amount_per_intervention = actual_recovered / intervention_cases if intervention_cases > 0 else 0.0

    scenario_recovery: dict[str, dict[str, Any]] = {}
    if "scenario" in at_risk.columns:
        scenario_values = at_risk["scenario"].fillna("unknown").astype(str).str.strip().str.lower()
        for scenario_name in sorted(scenario_values.unique()):
            scenario_df = at_risk[scenario_values == scenario_name]
            scenario_cases = len(scenario_df)
            scenario_recovered_cases = int(scenario_df["recovered"].sum())
            scenario_money_recovered = float(scenario_df["money_recovered"].sum())
            scenario_recovery_rate = scenario_recovered_cases / scenario_cases * 100 if scenario_cases else 0.0
            scenario_recovery[scenario_name] = {
                "cases": scenario_cases,
                "recovered_cases": scenario_recovered_cases,
                "unrecovered_cases": scenario_cases - scenario_recovered_cases,
                "recovery_rate": round(scenario_recovery_rate, 2),
                "money_recovered": round(scenario_money_recovered, 2),
            }

    return {
        "total_transaction_value": round(total_risk, 2),
        "expected_recovery_value": round(expected_recovery, 2),
        "actual_recovered_value": round(actual_recovered, 2),
        "recovery_rate": round(recovery_rate, 2),
        "at_risk_cases": total_cases,
        "recovered_cases": recovered_cases,
        "unrecovered_cases": total_cases - recovered_cases,
        "total_customers": recovery_customers,
        "total_dataset_customers": total_dataset_customers,
        "recovery_coverage": round(recovery_coverage, 2),
        "total_retries": total_retries,
        "intervention_cases": intervention_cases,
        "recovery_amount_per_intervention": round(recovery_amount_per_intervention, 2),
        "scenario_recovery": scenario_recovery,
    }


# ============================================================
# SCENARIO NORMALIZATION / EXECUTION
# ============================================================

def normalize_scenario(scenario: Any) -> str:
    value = safe_string(scenario, "payment_failure").strip().lower()
    aliases = {
        "checkout_abandoned": "checkout_abandonment",
        "checkout_dropoff": "checkout_abandonment",
        "checkout_dropout": "checkout_abandonment",
        "checkout_drop_off": "checkout_abandonment",
        "subscription_failure": "failed_subscription",
        "subscription_payment_failed": "failed_subscription",
        "b2b_receivables": "b2b_receivable",
        "invoice_overdue": "b2b_receivable",
        "mandate": "mandate_failure",
        "recurring_payment_failure": "mandate_failure",
        "ptp": "promise_to_pay",
        "promise-to-pay": "promise_to_pay",
    }
    value = aliases.get(value, value)
    if value not in SUPPORTED_SCENARIOS:
        raise ValueError(
            f"Unsupported scenario '{value}'. Supported scenarios: "
            f"{', '.join(sorted(SUPPORTED_SCENARIOS))}"
        )
    return value


def apply_scenario_recovery_policy(
    transaction: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Make every supported scenario produce an explicit, demoable workflow."""
    scenario = normalize_scenario(transaction.get("scenario"))
    defaults = SCENARIO_DEFAULTS[scenario]

    result = dict(result)
    diagnosis = dict(result.get("diagnosis") or {})
    score = dict(result.get("score") or {})
    action = dict(result.get("action") or {})
    policy = dict(result.get("policy") or {})
    execution = dict(result.get("execution") or {})
    stopping = dict(result.get("stopping") or {})

    # ------------------------------------------------------------
    # AUTHORITATIVE SCENARIO DIAGNOSIS
    # ------------------------------------------------------------
    if scenario in SUPPORTED_SCENARIOS:
        diagnosis["diagnosis"] = defaults["diagnosis"]
        diagnosis["reason"] = SCENARIO_DIAGNOSIS_REASONS[scenario]
    else:
        diagnosis.setdefault("diagnosis", defaults["diagnosis"])
        diagnosis.setdefault(
            "reason",
            f"Recovery workflow selected for {scenario.replace('_', ' ')}.",
        )
    diagnosis.setdefault("evidence", [])

    score.setdefault("recovery_probability", 0.0)
    score.setdefault("priority_score", 0.0)
    score.setdefault("priority", "LOW")
    score.setdefault("recommended_channel", defaults["channel"])

    # Scenario-specific action is authoritative when the base agent returns
    # a generic payment action. This keeps one common bounded agent loop.
    generic_actions = {"", "general_recovery", "retry_payment"}
    if scenario != "payment_failure" and action.get("recovery_action") in generic_actions:
        action["recovery_action"] = defaults["action"]
    action.setdefault("recovery_action", defaults["action"])
    action.setdefault("strategy", defaults["strategy"])
    action.setdefault("channel", defaults["channel"])
    action["scenario"] = scenario

    # ------------------------------------------------------------
    # SUPPORTED SCENARIOS ARE POLICY-ALLOWED
    # ------------------------------------------------------------
    # The common agent may return "unsupported_recovery_scenario"
    # because its older policy engine does not know about the
    # expanded scenario registry. The API-level scenario registry
    # is authoritative for these supported demo workflows.
    if scenario in SUPPORTED_SCENARIOS:
        policy["allowed"] = True
        policy["reason"] = "action_within_recovery_policy"
    else:
        policy["allowed"] = False
        policy["reason"] = "unsupported_recovery_scenario"

    recovered = bool(execution.get("recovered", False))
    money_recovered = safe_float(execution.get("money_recovered", 0.0))

    # For the demo environment, all six workflows execute as simulated actions.
    # Recovery is intentionally bounded: the stopping state is always explicit.
    if not policy.get("allowed", False):
        execution.update({
            "execution_status": "blocked",
            "action": action["recovery_action"],
            "channel": action["channel"],
            "attempt_increment": 0,
            "message_sent": False,
            "recovered": False,
            "money_recovered": 0.0,
            "execution_detail": "Action blocked by recovery policy.",
        })
        stopping.update({"stop": True, "reason": "POLICY_BLOCKED"})
    else:
        execution.setdefault("execution_status", "simulated")
        execution["action"] = action["recovery_action"]
        execution["channel"] = action["channel"]
        execution.setdefault("attempt_increment", 1)
        execution.setdefault("message_sent", True)
        execution.setdefault("recovered", recovered)
        execution.setdefault("money_recovered", money_recovered)
        execution["execution_detail"] = (
            f"Recovery succeeded through "
            f"{action['recovery_action']} "
            f"using {action['channel']} "
            f"for {scenario}."
        )
        execution["scenario"] = scenario
        stopping.setdefault(
            "stop", bool(execution.get("recovered")),
        )
        stopping.setdefault(
            "reason",
            "PAYMENT_SUCCESS" if execution.get("recovered") else "MAX_ATTEMPTS_OR_FOLLOWUP",
        )

    result.update({
        "status": "recovered" if execution.get("recovered") else "processed",
        "scenario": scenario,
        "diagnosis": diagnosis,
        "score": score,
        "action": action,
        "policy": policy,
        "execution": execution,
        "stopping": stopping,
    })
    return result


# ============================================================
# RECOVERY AGENT
# ============================================================

def run_recovery_agent(transaction: dict[str, Any]) -> dict[str, Any]:
    scorer = RecoveryScorer()
    agent = RecoveryAgent(scorer=scorer)

    result = agent.process(transaction)

    if not isinstance(result, dict):
        raise ValueError("RecoveryAgent returned an invalid result.")

    return apply_scenario_recovery_policy(transaction, result)


def processed_event_to_row(
    transaction: dict[str, Any],
    agent_result: dict[str, Any],
) -> dict[str, Any]:

    score = agent_result.get("score", {})
    action = agent_result.get("action", {})
    execution = agent_result.get("execution", {})

    score = score if isinstance(score, dict) else {}
    action = action if isinstance(action, dict) else {}
    execution = execution if isinstance(execution, dict) else {}

    amount = safe_float(transaction.get("transaction_amount"))

    recovery_probability = safe_float(
        score.get("recovery_probability")
    )

    recovered = normalize_bool(
        transaction.get(
            "recovered",
            execution.get("recovered", 0),
        )
    )

    money_recovered = safe_float(
        transaction.get(
            "money_recovered",
            execution.get("money_recovered", 0.0),
        )
    )

    return {
        "transaction_id": safe_string(transaction.get("transaction_id")),
        "customer_id": safe_string(transaction.get("customer_id")),
        "transaction_amount": amount,
        "payment_method": safe_string(transaction.get("payment_method")),
        "failure_reason": safe_string(transaction.get("failure_reason")),
        "retry_count": safe_int(transaction.get("retry_count")),
        "customer_transaction_count": safe_int(
            transaction.get("customer_transaction_count", 1), 1
        ),
        "customer_success_rate": safe_float(
            transaction.get("customer_success_rate")
        ),
        "payment_method_success_rate": safe_float(
            transaction.get("payment_method_success_rate")
        ),
        "channel": safe_string(
            transaction.get("channel", "payment_link"),
            "payment_link",
        ),
        "preferred_channel": safe_string(
            transaction.get("preferred_channel", "")
        ),
        "product_interest_score": safe_float(
            transaction.get("product_interest_score")
        ),
        "checkout_progress": safe_float(
            transaction.get("checkout_progress")
        ),
        "customer_email_available": normalize_bool(
            transaction.get("customer_email_available")
        ),
        "customer_phone_available": normalize_bool(
            transaction.get("customer_phone_available")
        ),
        "scenario": safe_string(
            transaction.get("scenario", "payment_failure"),
            "payment_failure",
        ),
        "payment_status": safe_string(
            transaction.get("payment_status", "failed"),
            "failed",
        ),
        "revenue_at_risk": 1,
        "recovery_attempts": safe_int(
            transaction.get("recovery_attempts")
        ),
        "promise_to_pay": normalize_bool(
            transaction.get("promise_to_pay")
        ),
        "recovered": recovered,
        "money_recovered": money_recovered,
        "recovery_probability": recovery_probability,
        "expected_recovery_value": amount * recovery_probability,
        "customer_intent": safe_float(
            score.get("customer_intent")
        ),
        "customer_reliability": safe_float(
            score.get("customer_reliability")
        ),
        "contactability": safe_float(
            score.get("contactability")
        ),
        "recovery_friction": safe_float(
            score.get("recovery_friction")
        ),
        "priority_score": safe_float(
            score.get("priority_score")
        ),
        "priority": safe_string(
            score.get("priority", "LOW"),
            "LOW",
        ).upper(),
        "strategy": safe_string(
            action.get("strategy", "low_cost_recovery"),
            "low_cost_recovery",
        ),
        "recovery_action": safe_string(
            action.get("recovery_action", "general_recovery"),
            "general_recovery",
        ),
        "recommended_channel": safe_string(
            action.get(
                "channel",
                score.get("recommended_channel", "none"),
            ),
            "none",
        ),
    }


# ============================================================
# CONVERSATION HELPERS
# ============================================================

def build_conversation_context(
    conversation: list[AIMessage],
) -> str:
    if not conversation:
        return ""

    lines = []

    for message in conversation[-8:]:
        role = message.role.lower().strip()

        if role in {"user", "assistant"}:
            lines.append(f"{role.upper()}: {message.content}")

    return "\n".join(lines)


def get_last_conversation_text(
    conversation: list[AIMessage],
) -> str:
    if not conversation:
        return ""

    return " ".join(
        message.content.lower().strip()
        for message in conversation[-8:]
        if message.content.strip()
    )


def last_user_question(
    conversation: list[AIMessage],
) -> str:
    for message in reversed(conversation):
        if message.role.lower().strip() == "user":
            return message.content.lower().strip()

    return ""


# ============================================================
# AI ANSWER
# ============================================================

def get_ai_answer(
    question: str,
    conversation: list[AIMessage],
    at_risk: pd.DataFrame,
    summary: dict[str, Any],
) -> str:

    q = question.lower().strip()
    previous_user = last_user_question(conversation)
    history = get_last_conversation_text(conversation)

    # --------------------------------------------------------
    # GREETING
    # --------------------------------------------------------

    if q in {
        "hi",
        "hello",
        "hey",
        "hi ai",
        "hello ai",
        "hey ai",
    }:
        return (
            "Hi! I'm your Recovery AI. 👋\n\n"
            "I can help you understand revenue risk, "
            "payment failures, recovery performance, "
            "prioritization, strategies, and agent decisions.\n\n"
            "Try asking:\n"
            "• Why is revenue at risk?\n"
            "• Why do transactions fail?\n"
            "• What should I prioritize first?\n"
            "• Which strategy performs best?\n"
            "• Explain the reasoning behind the decision."
        )

    # --------------------------------------------------------
    # UNRELATED TOPIC DETECTION
    # --------------------------------------------------------

    recovery_keywords = {
        "revenue",
        "recovery",
        "recover",
        "recovered",
        "risk",
        "at risk",
        "transaction",
        "transactions",
        "payment",
        "payments",
        "failed payment",
        "failure",
        "failure reason",
        "customer",
        "customers",
        "case",
        "cases",
        "priority",
        "prioritize",
        "high priority",
        "medium priority",
        "low priority",
        "strategy",
        "strategies",
        "agent",
        "agents",
        "action",
        "actions",
        "channel",
        "channels",
        "expected recovery",
        "recovery probability",
        "recovery rate",
        "money recovered",
        "amount at risk",
        "transaction value",
        "checkout",
        "retry",
        "retries",
        "contactability",
        "customer intent",
        "customer reliability",
        "payment method",
        "analytics",
        "performance",
        "opportunity",
        "opportunities",
        "unrecovered",
        "revenue recovery",
        "recovery ai",
    }

    unrelated_keywords = {
        "school",
        "schools",
        "homework",
        "math",
        "mathematics",
        "science",
        "history",
        "geography",
        "recipe",
        "recipes",
        "maggie",
        "movie",
        "movies",
        "song",
        "songs",
        "game",
        "games",
        "weather",
        "politics",
        "football",
        "cricket",
        "joke",
        "jokes",
        "poem",
        "poetry",
        "travel",
        "cooking",
        "water bottle",
        "waterbottle",
        "buy",
        "shopping",
        "amazon",
        "flipkart",
        "purchase",
    }

    has_recovery_topic = any(
        keyword in q for keyword in recovery_keywords
    )

    has_unrelated_topic = any(
        keyword in q for keyword in unrelated_keywords
    )

    # Short conversational words such as "ok", "yes", "sure"
    # should only be treated as follow-ups when there is history.
    followup_words = {
        "ok",
        "okay",
        "yes",
        "sure",
        "continue",
        "go on",
        "more",
        "explain",
        "explain more",
        "tell me more",
        "explain further",
        "more about it",
        "more about this",
        "why",
        "how",
        "what about it",
        "what about this",
        "which one",
        "which ones",
        "reasoning",
        "explain reasoning",
        "why this",
        "why this one",
        "why this case",
    }

    is_short_followup = (
        bool(conversation)
        and (
            q in followup_words
            or q.startswith("explain ")
            or q.startswith("tell me ")
            or q.startswith("why ")
        )
    )

    # If user asks something clearly unrelated and it is not
    # a follow-up to Recovery AI, reject it.
    if has_unrelated_topic and not has_recovery_topic:
        return (
            "That question isn't related to Revenue Recovery AI.\n\n"
            "I can help with revenue risk, payment failures, "
            "recovery cases, customer behavior, prioritization, "
            "recovery strategies, agent decisions, and recovery "
            "performance."
        )

    # --------------------------------------------------------
    # FOLLOW-UP: REASONING BEHIND PRIORITIZATION
    # --------------------------------------------------------

    if is_short_followup and (
        "priorit" in previous_user
        or "recover first" in previous_user
        or "which cases" in previous_user
        or "opportunity" in previous_user
    ):
        top = (
            at_risk
            .sort_values(
                ["expected_recovery_value", "priority_score"],
                ascending=False,
            )
            .head(1)
        )

        if top.empty:
            return "There are no recovery cases available to explain."

        row = top.iloc[0]

        return (
            f"The reasoning behind prioritizing transaction "
            f"{row['transaction_id']} is based on expected recovery value.\n\n"
            f"• Amount at risk: "
            f"{format_inr(row['transaction_amount'])}\n"
            f"• Recovery probability: "
            f"{row['recovery_probability'] * 100:.2f}%\n"
            f"• Expected recovery: "
            f"{format_inr(row['expected_recovery_value'])}\n"
            f"• Customer intent: "
            f"{row['customer_intent'] * 100:.2f}%\n"
            f"• Customer success rate: "
            f"{row['customer_success_rate'] * 100:.2f}%\n"
            f"• Priority score: "
            f"{row['priority_score'] * 100:.2f}%\n\n"
            "The system combines recovery probability, transaction "
            "value, customer intent, and customer success rate. "
            "This means the case is prioritized because it has a "
            "strong chance of recovering meaningful revenue, not "
            "simply because its transaction amount is large."
        )

    # --------------------------------------------------------
    # FOLLOW-UP: FAILURE REASONING
    # --------------------------------------------------------

    if is_short_followup and (
        "failure" in previous_user
        or "failed" in previous_user
        or "bank_decline" in history
        or "decline" in history
    ):
        failure_stats = (
            at_risk
            .groupby("failure_reason")
            .agg(
                cases=("transaction_id", "count"),
                recovered=("recovered", "sum"),
                amount=("transaction_amount", "sum"),
            )
        )

        if failure_stats.empty:
            return "There isn't enough failure data to explain the issue."

        failure_stats["recovery_rate"] = (
            failure_stats["recovered"]
            / failure_stats["cases"]
            * 100
        )

        worst_name = str(
            failure_stats["recovery_rate"].idxmin()
        )

        worst = failure_stats.loc[worst_name]

        return (
            f"The weakest recovery category is "
            f"'{worst_name}'.\n\n"
            f"• Cases: {int(worst['cases']):,}\n"
            f"• Transaction value: "
            f"{format_inr(worst['amount'])}\n"
            f"• Recovery rate: "
            f"{worst['recovery_rate']:.2f}%\n\n"
            "This suggests that the failure type is creating "
            "additional recovery friction. The next investigation "
            "should compare customer intent, contactability, retry "
            "count, payment-method performance, and the recovery "
            "action assigned to these cases."
        )

    # --------------------------------------------------------
    # FOLLOW-UP: STRATEGY REASONING
    # --------------------------------------------------------

    if is_short_followup and "strategy" in previous_user:
        strategy_stats = (
            at_risk
            .groupby("strategy")
            .agg(
                cases=("transaction_id", "count"),
                recovered=("recovered", "sum"),
                money_recovered=("money_recovered", "sum"),
            )
        )

        if strategy_stats.empty:
            return "There isn't enough strategy data to explain the result."

        strategy_stats["recovery_rate"] = (
            strategy_stats["recovered"]
            / strategy_stats["cases"]
            * 100
        )

        best_name = str(
            strategy_stats["recovery_rate"].idxmax()
        )

        best = strategy_stats.loc[best_name]

        return (
            f"The reasoning for the strongest strategy, "
            f"'{best_name}', is its observed recovery performance "
            "in the current dataset.\n\n"
            f"• Recovery rate: "
            f"{best['recovery_rate']:.2f}%\n"
            f"• Cases: {int(best['cases']):,}\n"
            f"• Money recovered: "
            f"{format_inr(best['money_recovered'])}\n\n"
            "The comparison is based on actual recovered cases "
            "and money recovered in the available data."
        )

    # --------------------------------------------------------
    # FOLLOW-UP: RISK REASONING
    # --------------------------------------------------------

    if is_short_followup and (
        "risk" in previous_user
        or "revenue" in previous_user
    ):
        return (
            "The revenue risk is driven by failed transactions "
            "that are still marked as recoverable opportunities.\n\n"
            f"• Revenue at risk: "
            f"{format_inr(summary['total_transaction_value'])}\n"
            f"• Expected recovery: "
            f"{format_inr(summary['expected_recovery_value'])}\n"
            f"• Unrecovered cases: "
            f"{summary['unrecovered_cases']:,}\n\n"
            "The highest-impact cases should be reviewed first "
            "using expected recovery value, because it combines "
            "transaction value with the estimated probability of "
            "successful recovery."
        )

    # --------------------------------------------------------
    # HIGH PRIORITY
    # --------------------------------------------------------

    if (
        "high priority" in q
        or "high-priority" in q
        or "high priority cases" in q
    ):
        high = (
            at_risk[
                at_risk["priority"] == "HIGH"
            ]
            .sort_values(
                "expected_recovery_value",
                ascending=False,
            )
            .head(5)
        )

        if high.empty:
            return "There are currently no HIGH-priority recovery cases."

        top = high.iloc[0]

        total_high_value = float(high["transaction_amount"].sum())
        expected_high_value = float(
            high["expected_recovery_value"].sum()
        )

        return (
            f"There are {int((at_risk['priority'] == 'HIGH').sum()):,} "
            "HIGH-priority cases.\n\n"
            f"The top opportunity is transaction "
            f"{top['transaction_id']}.\n\n"
            f"• Amount at risk: "
            f"{format_inr(top['transaction_amount'])}\n"
            f"• Recovery probability: "
            f"{top['recovery_probability'] * 100:.2f}%\n"
            f"• Expected recovery: "
            f"{format_inr(top['expected_recovery_value'])}\n"
            f"• Strategy: {top['strategy']}\n"
            f"• Channel: {top['recommended_channel']}\n\n"
            f"Among the top five opportunities, "
            f"{format_inr(total_high_value)} is at risk and "
            f"{format_inr(expected_high_value)} is expected to be recovered."
        )

    # --------------------------------------------------------
    # PRIORITIZATION
    # --------------------------------------------------------

    if (
        "prioritize" in q
        or "recover first" in q
        or "what should we do" in q
        or "what should i do" in q
        or "where should we start" in q
        or "which cases" in q
    ):
        top = (
            at_risk
            .sort_values(
                ["expected_recovery_value", "priority_score"],
                ascending=False,
            )
            .head(1)
        )

        if top.empty:
            return "There are currently no recovery cases available."

        row = top.iloc[0]

        return (
            "I would prioritize cases using expected recovery value "
            "rather than transaction amount alone.\n\n"
            f"Top opportunity: {row['transaction_id']}\n\n"
            f"• Amount at risk: "
            f"{format_inr(row['transaction_amount'])}\n"
            f"• Recovery probability: "
            f"{row['recovery_probability'] * 100:.2f}%\n"
            f"• Expected recovery: "
            f"{format_inr(row['expected_recovery_value'])}\n"
            f"• Priority: {row['priority']}\n"
            f"• Strategy: {row['strategy']}\n"
            f"• Channel: {row['recommended_channel']}\n\n"
            "Ask 'tell me the reasoning' to see exactly why this "
            "case was selected."
        )

    # --------------------------------------------------------
    # REVENUE AT RISK
    # --------------------------------------------------------

    if (
        "revenue at risk" in q
        or ("why" in q and "risk" in q)
        or ("why" in q and "revenue" in q)
    ):
        failure_stats = (
            at_risk
            .groupby("failure_reason")
            .agg(
                cases=("transaction_id", "count"),
                amount=("transaction_amount", "sum"),
                recovered=("recovered", "sum"),
            )
            .sort_values("amount", ascending=False)
        )

        if failure_stats.empty:
            explanation = "Failure-reason data is not available."
        else:
            top_failure = failure_stats.iloc[0]
            failure_name = str(failure_stats.index[0])

            explanation = (
                f"The largest failure category is "
                f"'{failure_name}', representing "
                f"{int(top_failure['cases']):,} cases and "
                f"{format_inr(top_failure['amount'])} in transaction value."
            )

        return (
            f"Revenue at risk is currently "
            f"{format_inr(summary['total_transaction_value'])} "
            f"across {summary['at_risk_cases']:,} cases.\n\n"
            f"The recovery rate is "
            f"{summary['recovery_rate']:.2f}%, leaving "
            f"{summary['unrecovered_cases']:,} cases unrecovered.\n\n"
            f"{explanation}\n\n"
            "The biggest opportunities are cases with high recovery "
            "probability, meaningful transaction value, and strong "
            "customer intent."
        )

    # --------------------------------------------------------
    # STRATEGY
    # --------------------------------------------------------

    if (
        "strategy" in q
        or "performing best" in q
        or "best strategy" in q
        or "which strategy" in q
    ):
        strategy_stats = (
            at_risk
            .groupby("strategy")
            .agg(
                cases=("transaction_id", "count"),
                recovered=("recovered", "sum"),
                money_recovered=("money_recovered", "sum"),
            )
        )

        if strategy_stats.empty:
            return "There isn't enough strategy data to determine a best performer."

        strategy_stats["recovery_rate"] = (
            strategy_stats["recovered"]
            / strategy_stats["cases"]
            * 100
        )

        strategy_stats = strategy_stats.sort_values(
            ["recovery_rate", "money_recovered"],
            ascending=False,
        )

        best_name = str(strategy_stats.index[0])
        best = strategy_stats.iloc[0]

        return (
            f"The strongest-performing strategy in the current "
            f"data is '{best_name}'.\n\n"
            f"• Recovery rate: {best['recovery_rate']:.2f}%\n"
            f"• Cases: {int(best['cases']):,}\n"
            f"• Money recovered: {format_inr(best['money_recovered'])}\n\n"
            "Ask 'tell me the reasoning' if you want to understand "
            "why this strategy ranks first."
        )

    # --------------------------------------------------------
    # TRANSACTION / PAYMENT FAILURE
    # --------------------------------------------------------

    if (
        "why do transactions fail" in q
        or "why does transactions fail" in q
        or "why does transaction fail" in q
        or "why do payments fail" in q
        or "why does payment fail" in q
        or "transaction failure" in q
        or "payment failure" in q
        or "failure reasons" in q
        or "failure reason" in q
    ):
        failure_stats = (
            at_risk
            .groupby("failure_reason")
            .agg(
                cases=("transaction_id", "count"),
                amount=("transaction_amount", "sum"),
                recovered=("recovered", "sum"),
            )
            .sort_values("cases", ascending=False)
        )

        if failure_stats.empty:
            return (
                "There isn't enough failure-reason data "
                "to explain transaction failures."
            )

        top_failures = failure_stats.head(5)

        lines = []

        for failure_name, row in top_failures.iterrows():
            lines.append(
                f"• {failure_name}: "
                f"{int(row['cases']):,} cases, "
                f"{format_inr(row['amount'])} at risk"
            )

        return (
            "Transactions are failing for several reasons. "
            "The most common failure categories in the current "
            "data are:\n\n"
            + "\n".join(lines)
            + "\n\n"
            "These categories should be analyzed separately because "
            "different payment problems may require different "
            "recovery actions."
        )

    # --------------------------------------------------------
    # RECOVERY RATE / PERFORMANCE
    # --------------------------------------------------------

    if (
        "recovery rate" in q
        or "how are we doing" in q
        or "performance" in q
    ):
        return (
            f"The current recovery rate is "
            f"{summary['recovery_rate']:.2f}%.\n\n"
            f"We have recovered "
            f"{summary['recovered_cases']:,} of "
            f"{summary['at_risk_cases']:,} cases.\n\n"
            f"{summary['unrecovered_cases']:,} cases still require "
            "recovery action.\n\n"
            f"Expected recovery is "
            f"{format_inr(summary['expected_recovery_value'])} "
            f"against {format_inr(summary['total_transaction_value'])} "
            "at risk."
        )

    # --------------------------------------------------------
    # GENERIC RECOVERY QUESTION
    # --------------------------------------------------------

    if has_recovery_topic:
        return (
            "Here's the current recovery picture:\n\n"
            f"• Revenue at risk: "
            f"{format_inr(summary['total_transaction_value'])}\n"
            f"• Expected recovery: "
            f"{format_inr(summary['expected_recovery_value'])}\n"
            f"• Recovery rate: "
            f"{summary['recovery_rate']:.2f}%\n"
            f"• Recovery cases: "
            f"{summary['at_risk_cases']:,}\n"
            f"• Recovered cases: "
            f"{summary['recovered_cases']:,}\n"
            f"• Unrecovered cases: "
            f"{summary['unrecovered_cases']:,}\n\n"
            "Try asking:\n"
            "• Why is revenue at risk?\n"
            "• Why do transactions fail?\n"
            "• What should I prioritize first?\n"
            "• Which strategy performs best?\n"
            "• Tell me the reasoning behind the decision."
        )

    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------

    return (
        "That question isn't related to Revenue Recovery AI.\n\n"
        "I can help with revenue risk, payment failures, recovery "
        "cases, customer behavior, prioritization, recovery strategies, "
        "agent decisions, and recovery performance."
    )


# ============================================================
# PAGES
# ============================================================

@app.get("/")
async def dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/recovery-cases.html")
async def recovery_cases_page():
    return FileResponse(FRONTEND_DIR / "recovery-cases.html")


@app.get("/customers.html")
async def customers_page():
    return FileResponse(FRONTEND_DIR / "customers.html")


@app.get("/analytics.html")
async def analytics_page():
    return FileResponse(FRONTEND_DIR / "analytics.html")


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "dataset_exists": DATA_FILE.exists(),
        "dataset": str(DATA_FILE),
        "live_recovery_events": len(PROCESSED_RECOVERY_EVENTS),
        "live_events_persisted": LIVE_EVENTS_FILE.exists(),
        "live_events_file": str(LIVE_EVENTS_FILE),
    }


# ============================================================
# CREATE / PROCESS RECOVERY EVENT
# ============================================================

@app.post("/recovery-events")
async def process_recovery_event(event: RecoveryEvent):
    transaction = event.model_dump()
    transaction["scenario"] = normalize_scenario(transaction.get("scenario"))
    transaction["revenue_at_risk"] = 1

    transaction_id = safe_string(transaction.get("transaction_id"))
    if not transaction_id:
        raise HTTPException(
            status_code=400,
            detail="transaction_id cannot be empty.",
        )

    # ------------------------------------------------------------
    # SERVER OWNS RECOVERY ATTEMPTS
    # ------------------------------------------------------------
    previous_state = LIVE_RECOVERY_STATE.get(transaction_id)

    if previous_state:
        transaction["recovery_attempts"] = int(
            previous_state.get("recovery_attempts", 0) or 0
        )
    else:
        transaction["recovery_attempts"] = 0

    try:
        # --------------------------------------------------------
        # RUN RECOVERY AGENT
        # --------------------------------------------------------
        result = run_recovery_agent(transaction)

        execution = result.get("execution", {})
        if not isinstance(execution, dict):
            execution = {}

        # --------------------------------------------------------
        # SERVER UPDATES THE ATTEMPT COUNTER
        # --------------------------------------------------------
        attempt_increment = safe_int(
            execution.get("attempt_increment", 0)
        )
        transaction["recovery_attempts"] += attempt_increment

        # Keep the server-owned counter in the result as well.
        execution["attempt_count"] = transaction["recovery_attempts"]
        result["execution"] = execution

        # --------------------------------------------------------
        # RECOVERY STATE
        # --------------------------------------------------------
        recovered = bool(execution.get("recovered", False))
        money_recovered = safe_float(
            execution.get("money_recovered", 0.0)
        )

        transaction["recovered"] = int(recovered)
        transaction["money_recovered"] = money_recovered
        transaction["payment_status"] = (
            "paid" if recovered else "failed"
        )

        # --------------------------------------------------------
        # PERSIST SERVER-OWNED LIVE STATE
        # --------------------------------------------------------
        LIVE_RECOVERY_STATE[transaction_id] = {
            "recovery_attempts": transaction["recovery_attempts"],
            "recovered": int(recovered),
            "payment_status": transaction["payment_status"],
            "money_recovered": money_recovered,
        }

        # --------------------------------------------------------
        # STORE PROCESSED EVENT
        # --------------------------------------------------------
        live_row = processed_event_to_row(transaction, result)
        live_row["_agent_result"] = result
        live_row["recovery_attempts"] = transaction["recovery_attempts"]

        PROCESSED_RECOVERY_EVENTS[transaction_id] = live_row
        save_live_events()

        return {
            "success": True,
            "event": transaction,
            "agent_result": result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Recovery event processing failed: {exc}",
        ) from exc


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

@app.get("/dashboard-summary")
async def dashboard_summary_api():
    at_risk = get_at_risk_data()
    summary = dashboard_summary(at_risk)

    priority_counts = (
        at_risk["priority"]
        .value_counts()
        .reindex(["HIGH", "MEDIUM", "LOW"], fill_value=0)
    )

    strategy_order = [
        "aggressive_recovery",
        "assisted_recovery",
        "standard_recovery",
        "low_cost_recovery",
    ]

    strategy_counts = (
        at_risk["strategy"]
        .value_counts()
        .reindex(strategy_order, fill_value=0)
    )

    return {
        **summary,
        "priority_distribution": [
            {
                "priority": priority,
                "cases": int(priority_counts[priority]),
            }
            for priority in ["HIGH", "MEDIUM", "LOW"]
        ],
        "strategy_distribution": [
            {
                "strategy": strategy,
                "cases": int(strategy_counts[strategy]),
            }
            for strategy in strategy_order
        ],
    }


# ============================================================
# METRICS
# ============================================================

@app.get("/metrics")
async def metrics():
    at_risk = get_at_risk_data()
    summary = dashboard_summary(at_risk)

    high_priority = int(
        (at_risk["priority"] == "HIGH").sum()
    )

    return {
        **summary,
        "high_priority_cases": high_priority,
    }


@app.get("/metrics/priority")
async def priority_metrics():
    at_risk = get_at_risk_data()

    counts = (
        at_risk["priority"]
        .value_counts()
        .reindex(["HIGH", "MEDIUM", "LOW"], fill_value=0)
    )

    return {
        "priority_distribution": [
            {
                "priority": priority,
                "cases": int(counts[priority]),
            }
            for priority in ["HIGH", "MEDIUM", "LOW"]
        ]
    }


@app.get("/metrics/strategy")
async def strategy_metrics():
    at_risk = get_at_risk_data()

    strategies = [
        "aggressive_recovery",
        "assisted_recovery",
        "standard_recovery",
        "low_cost_recovery",
    ]

    counts = (
        at_risk["strategy"]
        .value_counts()
        .reindex(strategies, fill_value=0)
    )

    return {
        "strategy_distribution": [
            {
                "strategy": strategy,
                "cases": int(counts[strategy]),
            }
            for strategy in strategies
        ]
    }


# ============================================================
# AI ANALYSIS
# ============================================================

@app.post("/ai/analyze")
async def analyze_recovery_ai(request: AIQuestion):
    question = request.question.strip()

    if not question:
        return {
            "success": False,
            "answer": "Please enter a question.",
            "conversation": [
                message.model_dump()
                for message in request.conversation
            ],
        }

    at_risk = get_at_risk_data()
    summary = dashboard_summary(at_risk)

    answer = get_ai_answer(
        question=question,
        conversation=request.conversation,
        at_risk=at_risk,
        summary=summary,
    )

    conversation = [
        message.model_dump()
        for message in request.conversation
    ]

    conversation.extend(
        [
            {
                "role": "user",
                "content": question,
            },
            {
                "role": "assistant",
                "content": answer,
            },
        ]
    )

    conversation = conversation[-20:]

    return {
        "success": True,
        "question": question,
        "answer": answer,
        "conversation": conversation,
        "summary": summary,
    }


# ============================================================
# TOP OPPORTUNITIES
# ============================================================

@app.get("/top-opportunities")
async def top_opportunities(
    limit: int = Query(default=10, ge=1, le=50),
):
    at_risk = get_at_risk_data()

    top = (
        at_risk
        .sort_values(
            ["expected_recovery_value", "priority_score"],
            ascending=False,
        )
        .head(limit)
    )

    results = []

    for _, row in top.iterrows():
        results.append(
            {
                "transaction_id": safe_string(row["transaction_id"]),
                "customer_id": safe_string(row["customer_id"]),
                "transaction_amount": round(
                    safe_float(row["transaction_amount"]), 2
                ),
                "recovery_probability": round(
                    safe_float(row["recovery_probability"]), 4
                ),
                "priority_score": round(
                    safe_float(row["priority_score"]), 4
                ),
                "priority": safe_string(row["priority"]),
                "strategy": safe_string(row["strategy"]),
                "recommended_channel": safe_string(
                    row["recommended_channel"]
                ),
                "expected_recovery_value": round(
                    safe_float(row["expected_recovery_value"]), 2
                ),
            }
        )

    return results


# ============================================================
# RECOVERY CASES
# ============================================================

@app.get("/recovery-cases")
async def recovery_cases_api(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    priority: str | None = None,
    strategy: str | None = None,
    search: str | None = None,
):
    at_risk = get_at_risk_data()

    if priority:
        at_risk = at_risk[
            at_risk["priority"].astype(str).str.upper()
            == priority.upper()
        ]

    if strategy:
        at_risk = at_risk[
            at_risk["strategy"].astype(str).str.lower()
            == strategy.lower()
        ]

    if search:
        term = search.lower().strip()

        transaction_match = (
            at_risk["transaction_id"]
            .astype(str)
            .str.lower()
            .str.contains(term, regex=False)
        )

        customer_match = (
            at_risk["customer_id"]
            .astype(str)
            .str.lower()
            .str.contains(term, regex=False)
        )

        at_risk = at_risk[
            transaction_match | customer_match
        ]

    total = len(at_risk)

    at_risk = (
        at_risk
        .sort_values(
            ["priority_score", "expected_recovery_value"],
            ascending=False,
        )
    )

    page = at_risk.iloc[offset: offset + limit]

    results = []

    for _, row in page.iterrows():
        results.append(
            {
                "transaction_id": safe_string(row["transaction_id"]),
                "customer_id": safe_string(row["customer_id"]),
                "transaction_amount": round(
                    safe_float(row["transaction_amount"]), 2
                ),
                "priority": safe_string(row["priority"]),
                "priority_score": round(
                    safe_float(row["priority_score"]), 4
                ),
                "recovery_probability": round(
                    safe_float(row["recovery_probability"]), 4
                ),
                "strategy": safe_string(row["strategy"]),
                "recovery_action": safe_string(
                    row["recovery_action_display"]
                ),
                "recommended_channel": safe_string(
                    row["recommended_channel"]
                ),
                "recovered": bool(
                    normalize_bool(row["recovered"])
                ),
                "money_recovered": round(
                    safe_float(row["money_recovered"]), 2
                ),
                "expected_recovery_value": round(
                    safe_float(row["expected_recovery_value"]), 2
                ),
            }
        )

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "returned": len(results),
        "cases": results,
    }


# ============================================================
# CUSTOMERS
# ============================================================

@app.get("/customers")
async def customers_api():
    at_risk = get_at_risk_data()

    grouped = (
        at_risk
        .groupby("customer_id", as_index=False)
        .agg(
            cases=("transaction_id", "count"),
            amount_at_risk=("transaction_amount", "sum"),
            recovered_cases=("recovered", "sum"),
            money_recovered=("money_recovered", "sum"),
            average_recovery_probability=(
                "recovery_probability",
                "mean",
            ),
        )
    )

    if grouped.empty:
        return {
            "total_customers": 0,
            "customers_with_cases": 0,
            "recovered_customers": 0,
            "total_cases": 0,
            "money_recovered": 0.0,
            "customers": [],
        }

    grouped["recovery_rate"] = (
        grouped["recovered_cases"]
        / grouped["cases"]
        * 100
    )

    grouped = grouped.sort_values(
        ["money_recovered", "amount_at_risk"],
        ascending=False,
    )

    return {
        "total_customers": int(len(grouped)),
        "customers_with_cases": int(len(grouped)),
        "recovered_customers": int(
            (grouped["recovered_cases"] > 0).sum()
        ),
        "total_cases": int(len(at_risk)),
        "money_recovered": round(
            safe_float(at_risk["money_recovered"].sum()),
            2,
        ),
        "customers": [
            {
                "customer_id": safe_string(row["customer_id"]),
                "cases": safe_int(row["cases"]),
                "amount_at_risk": round(
                    safe_float(row["amount_at_risk"]), 2
                ),
                "recovered_cases": safe_int(
                    row["recovered_cases"]
                ),
                "recovery_rate": round(
                    safe_float(row["recovery_rate"]), 2
                ),
                "money_recovered": round(
                    safe_float(row["money_recovered"]), 2
                ),
                "average_recovery_probability": round(
                    safe_float(
                        row["average_recovery_probability"]
                    ),
                    4,
                ),
            }
            for _, row in grouped.iterrows()
        ],
    }


# ============================================================
# ANALYTICS
# ============================================================

@app.get("/analytics")
async def analytics_api():
    at_risk = get_at_risk_data()

    def group_recovery(
        column: str,
    ) -> list[dict[str, Any]]:

        if at_risk.empty:
            return []

        grouped = (
            at_risk
            .groupby(column)
            .agg(
                cases=("transaction_id", "count"),
                recovered=("recovered", "sum"),
                money_recovered=("money_recovered", "sum"),
                amount_at_risk=("transaction_amount", "sum"),
            )
            .reset_index()
        )

        grouped["recovery_rate"] = (
            grouped["recovered"]
            / grouped["cases"]
            * 100
        )

        return [
            {
                column: safe_string(row[column]),
                "cases": safe_int(row["cases"]),
                "recovered": safe_int(row["recovered"]),
                "recovery_rate": round(
                    safe_float(row["recovery_rate"]), 2
                ),
                "amount_at_risk": round(
                    safe_float(row["amount_at_risk"]), 2
                ),
                "money_recovered": round(
                    safe_float(row["money_recovered"]), 2
                ),
            }
            for _, row in grouped.iterrows()
        ]

    return {
        "summary": dashboard_summary(at_risk),
        "scenario": group_recovery("scenario"),
        "payment_method": group_recovery("payment_method"),
        "channel": group_recovery("channel"),
        "failure_reason": group_recovery("failure_reason"),
        "priority": group_recovery("priority"),
        "strategy": group_recovery("strategy"),
    }
