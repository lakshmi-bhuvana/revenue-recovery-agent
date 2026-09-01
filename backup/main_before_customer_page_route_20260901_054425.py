
from datetime import datetime
import json
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
LIVE_EVENTS_FILE = BASE_DIR / "data" / "runtime" / "recovery_events.json"


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

MAX_RECOVERY_ATTEMPTS = 3
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

PAYMENT_FAILURE_DIAGNOSES = {
    "bank_decline": {
        "diagnosis": "bank_decline",
        "reason": "The payment was declined by the bank.",
    },
    "insufficient_funds": {
        "diagnosis": "insufficient_funds",
        "reason": "The payment failed because sufficient funds were not available.",
    },
    "card_expired": {
        "diagnosis": "card_expired",
        "reason": "The payment failed because the card has expired.",
    },
    "invalid_card": {
        "diagnosis": "invalid_card",
        "reason": "The payment failed because the card details were invalid.",
    },
    "payment_method_failed": {
        "diagnosis": "payment_method_failed",
        "reason": "The selected payment method failed.",
    },
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

    # API field used to force a failed recovery in demos/tests.
    force_recovery_failure: bool = False


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
    app.mount(
        "/css",
        StaticFiles(directory=str(CSS_DIR)),
        name="css",
    )

if JS_DIR.exists():
    app.mount(
        "/js",
        StaticFiles(directory=str(JS_DIR)),
        name="js",
    )


# ============================================================
# DATA HELPERS
# ============================================================

def load_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    return pd.read_csv(DATA_FILE)


def normalize_bool(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)

    if value is None:
        return 0

    if isinstance(value, str):
        return int(
            value.strip().lower()
            in {
                "true",
                "1",
                "yes",
                "paid",
                "recovered",
            }
        )

    try:
        return int(float(value) != 0)
    except (TypeError, ValueError):
        return 0


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        if pd.isna(value):
            return default

        return int(float(value))

    except (TypeError, ValueError):
        return default


def safe_string(
    value: Any,
    default: str = "",
) -> str:
    if value is None:
        return default

    try:
        if pd.isna(value):
            return default

    except (TypeError, ValueError):
        pass

    return str(value)


def persist_recovery_events() -> None:
    """Persist live recovery events so recovery state survives restarts."""

    try:
        LIVE_EVENTS_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with LIVE_EVENTS_FILE.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                PROCESSED_RECOVERY_EVENTS,
                handle,
                ensure_ascii=False,
                indent=2,
            )

    except (OSError, TypeError, ValueError):
        # Persistence is supplementary. A filesystem error must not
        # turn an otherwise successful recovery into a failed request.
        pass


def load_persisted_recovery_events() -> None:
    """Restore processed recovery events when the API starts."""

    if not LIVE_EVENTS_FILE.exists():
        return

    try:
        with LIVE_EVENTS_FILE.open(
            "r",
            encoding="utf-8",
        ) as handle:
            payload = json.load(handle)

        if not isinstance(payload, dict):
            return

        for raw_transaction_id, row in payload.items():
            if not isinstance(row, dict):
                continue

            transaction_id = safe_string(
                raw_transaction_id
            )

            if not transaction_id:
                continue

            PROCESSED_RECOVERY_EVENTS[
                transaction_id
            ] = row

            LIVE_RECOVERY_STATE[
                transaction_id
            ] = {
                "recovery_attempts": max(
                    0,
                    min(
                        safe_int(
                            row.get(
                                "recovery_attempts",
                                0,
                            )
                        ),
                        MAX_RECOVERY_ATTEMPTS,
                    ),
                ),
                "recovered": normalize_bool(
                    row.get(
                        "recovered",
                        0,
                    )
                ),
                "payment_status": safe_string(
                    row.get(
                        "payment_status",
                        "failed",
                    ),
                    "failed",
                ),
                "money_recovered": safe_float(
                    row.get(
                        "money_recovered",
                        0.0,
                    )
                ),
            }

    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        # Ignore an unavailable/corrupt runtime file and use the CSV.
        return


def format_inr(value: float) -> str:
    value = safe_float(value)

    integer_part, decimal_part = (
        f"{value:.2f}".split(".")
    )

    if len(integer_part) <= 3:
        return f"â‚¹{integer_part}.{decimal_part}"

    last_three = integer_part[-3:]
    remaining = integer_part[:-3]

    groups = []

    while len(remaining) > 2:
        groups.insert(
            0,
            remaining[-2:],
        )

        remaining = remaining[:-2]

    if remaining:
        groups.insert(
            0,
            remaining,
        )

    return (
        f"â‚¹{','.join(groups)},"
        f"{last_three}.{decimal_part}"
    )


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_base_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:

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
            pd.to_numeric(
                df[column],
                errors="coerce",
            )
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

        df[column] = (
            df[column]
            .fillna(default)
            .astype(str)
        )

    return df


# ============================================================
# SCORING
# ============================================================

def calculate_recovery_probability(
    df: pd.DataFrame,
) -> pd.Series:

    probability = (
        0.25
        + 0.30 * df["customer_success_rate"]
        + 0.20 * df["product_interest_score"]
        + 0.15 * df["payment_method_success_rate"]
        + 0.10 * df["checkout_progress"]
    )

    return probability.clip(0, 1)


def calculate_customer_intent(
    df: pd.DataFrame,
) -> pd.Series:

    intent = (
        0.60 * df["product_interest_score"]
        + 0.40 * df["checkout_progress"]
    )

    return intent.clip(0, 1)


def calculate_value_score(
    df: pd.DataFrame,
) -> pd.Series:

    return (
        df["transaction_amount"] / 50000
    ).clip(0, 1)


def calculate_priority_score(
    df: pd.DataFrame,
) -> pd.Series:

    priority = (
        0.50 * df["recovery_probability"]
        + 0.20 * df["value_score"]
        + 0.20 * df["customer_intent"]
        + 0.10 * df["customer_success_rate"]
    )

    return priority.clip(0, 1)


def assign_priority(
    score: pd.Series,
) -> pd.Series:

    priority = pd.Series(
        "LOW",
        index=score.index,
    )

    priority.loc[
        score >= 0.55
    ] = "MEDIUM"

    priority.loc[
        score >= 0.75
    ] = "HIGH"

    return priority


def assign_strategy(
    score: pd.Series,
) -> pd.Series:

    strategy = pd.Series(
        "low_cost_recovery",
        index=score.index,
    )

    strategy.loc[
        score >= 0.45
    ] = "standard_recovery"

    strategy.loc[
        score >= 0.60
    ] = "assisted_recovery"

    strategy.loc[
        score >= 0.75
    ] = "aggressive_recovery"

    return strategy


# ============================================================
# AT-RISK DATA
# ============================================================

def get_at_risk_data() -> pd.DataFrame:

    df = prepare_base_dataframe(
        load_data()
    )

    if PROCESSED_RECOVERY_EVENTS:

        live_df = prepare_base_dataframe(
            pd.DataFrame(
                PROCESSED_RECOVERY_EVENTS.values()
            )
        )

        live_ids = set(
            live_df[
                "transaction_id"
            ].astype(str)
        )

        df = df[
            ~df[
                "transaction_id"
            ]
            .astype(str)
            .isin(live_ids)
        ]

        df = pd.concat(
            [
                df,
                live_df,
            ],
            ignore_index=True,
        )

    if "_agent_result" in df.columns:

        for idx, raw_result in df[
            "_agent_result"
        ].items():

            if not isinstance(
                raw_result,
                dict,
            ):
                continue

            score = (
                raw_result.get(
                    "score"
                )
                or {}
            )

            action = (
                raw_result.get(
                    "action"
                )
                or {}
            )

            execution = (
                raw_result.get(
                    "execution"
                )
                or {}
            )

            if isinstance(
                score,
                dict,
            ):

                if score.get(
                    "recovery_probability"
                ) is not None:

                    df.at[
                        idx,
                        "recovery_probability",
                    ] = safe_float(
                        score.get(
                            "recovery_probability"
                        )
                    )

                if score.get(
                    "priority_score"
                ) is not None:

                    df.at[
                        idx,
                        "priority_score",
                    ] = safe_float(
                        score.get(
                            "priority_score"
                        )
                    )

                if score.get(
                    "priority"
                ) is not None:

                    df.at[
                        idx,
                        "priority",
                    ] = safe_string(
                        score.get(
                            "priority"
                        )
                    )

                if score.get(
                    "recommended_channel"
                ) is not None:

                    df.at[
                        idx,
                        "recommended_channel",
                    ] = safe_string(
                        score.get(
                            "recommended_channel"
                        )
                    )

            if isinstance(
                action,
                dict,
            ):

                if action.get(
                    "strategy"
                ) is not None:

                    df.at[
                        idx,
                        "strategy",
                    ] = safe_string(
                        action.get(
                            "strategy"
                        )
                    )

                if action.get(
                    "recovery_action"
                ) is not None:

                    df.at[
                        idx,
                        "recovery_action",
                    ] = safe_string(
                        action.get(
                            "recovery_action"
                        )
                    )

                if action.get(
                    "channel"
                ) is not None:

                    df.at[
                        idx,
                        "recommended_channel",
                    ] = safe_string(
                        action.get(
                            "channel"
                        )
                    )

            if isinstance(
                execution,
                dict,
            ):

                if execution.get(
                    "recovered"
                ) is not None:

                    df.at[
                        idx,
                        "recovered",
                    ] = normalize_bool(
                        execution.get(
                            "recovered"
                        )
                    )

                if execution.get(
                    "money_recovered"
                ) is not None:

                    df.at[
                        idx,
                        "money_recovered",
                    ] = safe_float(
                        execution.get(
                            "money_recovered"
                        )
                    )

    df["revenue_at_risk"] = (
        df[
            "revenue_at_risk"
        ]
        .apply(normalize_bool)
    )

    at_risk = df[
        df[
            "revenue_at_risk"
        ] == 1
    ].copy()

    if at_risk.empty:
        return at_risk

    calculated_probability = (
        calculate_recovery_probability(
            at_risk
        )
    )

    if (
        "recovery_probability"
        not in at_risk.columns
    ):

        at_risk[
            "recovery_probability"
        ] = calculated_probability

    else:

        existing = pd.to_numeric(
            at_risk[
                "recovery_probability"
            ],
            errors="coerce",
        )

        at_risk[
            "recovery_probability"
        ] = existing.fillna(
            calculated_probability
        )

    at_risk[
        "recovery_probability"
    ] = (
        at_risk[
            "recovery_probability"
        ]
        .clip(0, 1)
    )

    at_risk[
        "expected_recovery_value"
    ] = (
        at_risk[
            "transaction_amount"
        ]
        * at_risk[
            "recovery_probability"
        ]
    )

    calculated_intent = (
        calculate_customer_intent(
            at_risk
        )
    )

    if (
        "customer_intent"
        not in at_risk.columns
    ):

        at_risk[
            "customer_intent"
        ] = calculated_intent

    else:

        existing = pd.to_numeric(
            at_risk[
                "customer_intent"
            ],
            errors="coerce",
        )

        at_risk[
            "customer_intent"
        ] = existing.fillna(
            calculated_intent
        )

    at_risk[
        "customer_intent"
    ] = (
        at_risk[
            "customer_intent"
        ]
        .clip(0, 1)
    )

    at_risk[
        "value_score"
    ] = calculate_value_score(
        at_risk
    )

    calculated_priority = (
        calculate_priority_score(
            at_risk
        )
    )

    if (
        "priority_score"
        not in at_risk.columns
    ):

        at_risk[
            "priority_score"
        ] = calculated_priority

    else:

        existing = pd.to_numeric(
            at_risk[
                "priority_score"
            ],
            errors="coerce",
        )

        at_risk[
            "priority_score"
        ] = existing.fillna(
            calculated_priority
        )

    at_risk[
        "priority_score"
    ] = (
        at_risk[
            "priority_score"
        ]
        .clip(0, 1)
    )

    calculated_priority_label = (
        assign_priority(
            at_risk[
                "priority_score"
            ]
        )
    )

    at_risk[
        "priority"
    ] = calculated_priority_label


    calculated_strategy = (
        assign_strategy(
            at_risk[
                "priority_score"
            ]
        )
    )

    if (
        "strategy"
        not in at_risk.columns
    ):

        at_risk[
            "strategy"
        ] = calculated_strategy

    else:

        strategy = (
            at_risk[
                "strategy"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        missing = (
            strategy == ""
        )

        strategy.loc[
            missing
        ] = calculated_strategy.loc[
            missing
        ]

        at_risk[
            "strategy"
        ] = strategy

    if (
        "recommended_channel"
        not in at_risk.columns
    ):

        at_risk[
            "recommended_channel"
        ] = at_risk[
            "preferred_channel"
        ]

    else:

        channel = (
            at_risk[
                "recommended_channel"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        missing = (
            channel == ""
        )

        channel.loc[
            missing
        ] = at_risk.loc[
            missing,
            "preferred_channel",
        ]

        at_risk[
            "recommended_channel"
        ] = channel

    if (
        "recovery_action"
        not in at_risk.columns
    ):

        at_risk[
            "recovery_action"
        ] = at_risk[
            "recommended_channel"
        ]

    at_risk[
        "recovery_action_display"
    ] = (
        at_risk[
            "recovery_action"
        ]
        .fillna("")
        .astype(str)
    )

    at_risk[
        "recovered"
    ] = (
        at_risk[
            "recovered"
        ]
        .apply(normalize_bool)
    )

    at_risk[
        "money_recovered"
    ] = (
        pd.to_numeric(
            at_risk[
                "money_recovered"
            ],
            errors="coerce",
        )
        .fillna(0.0)
    )

    return at_risk


def get_unrecovered_data(
    at_risk: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return only recovery opportunities that are not yet recovered."""

    if at_risk is None:
        at_risk = get_at_risk_data()

    if at_risk.empty:
        return at_risk.copy()

    return at_risk[
        at_risk["recovered"].apply(normalize_bool) == 0
    ].copy()


# ============================================================
# SCENARIOS
# ============================================================

@app.get("/recovery-scenarios")
async def recovery_scenarios_api():

    return {
        "supported": sorted(
            SUPPORTED_SCENARIOS
        ),
        "scenarios": [
            {
                "scenario": name,
                **defaults,
            }
            for name, defaults
            in SCENARIO_DEFAULTS.items()
        ],
    }


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

def dashboard_summary(
    at_risk: pd.DataFrame,
) -> dict[str, Any]:

    # Current risk/opportunity values must exclude transactions that
    # have already been recovered. Historical recovery metrics still
    # use the complete dataframe.
    active = get_unrecovered_data(
        at_risk
    )

    total_cases = len(
        active
    )

    recovered_cases = int(
        at_risk["recovered"].apply(normalize_bool).sum()
    )

    total_dataset_cases = len(
        at_risk
    )

    total_risk = float(
        active["transaction_amount"].sum()
    ) if not active.empty else 0.0

    actual_recovered = float(
        at_risk["money_recovered"].sum()
    ) if not at_risk.empty else 0.0

    expected_recovery = float(
        active["expected_recovery_value"].sum()
    ) if not active.empty else 0.0

    recovery_rate = (
        recovered_cases
        / total_dataset_cases
        * 100
        if total_dataset_cases
        else 0.0
    )

    recovery_customers = int(
        active["customer_id"].nunique()
    ) if not active.empty else 0

    raw_data = load_data()

    total_dataset_customers = (
        int(
            raw_data["customer_id"].nunique()
        )
        if "customer_id" in raw_data.columns
        else 0
    )

    recovery_coverage = (
        recovery_customers
        / total_dataset_customers
        * 100
        if total_dataset_customers
        else 0.0
    )

    return {
        "total_transaction_value": round(
            total_risk,
            2,
        ),
        "expected_recovery_value": round(
            expected_recovery,
            2,
        ),
        "actual_recovered_value": round(
            actual_recovered,
            2,
        ),
        "recovery_rate": round(
            recovery_rate,
            2,
        ),
        "at_risk_cases": total_cases,
        "recovered_cases": recovered_cases,
        "unrecovered_cases": total_cases,
        "total_customers": recovery_customers,
        "total_dataset_customers": total_dataset_customers,
        "recovery_coverage": round(
            recovery_coverage,
            2,
        ),
    }


# ============================================================
# SCENARIO NORMALIZATION
# ============================================================

def normalize_scenario(
    scenario: Any,
) -> str:

    value = safe_string(
        scenario,
        "payment_failure",
    ).strip().lower()

    aliases = {
        "checkout_abandoned":
            "checkout_abandonment",

        "checkout_dropoff":
            "checkout_abandonment",

        "checkout_dropout":
            "checkout_abandonment",

        "checkout_drop_off":
            "checkout_abandonment",

        "subscription_failure":
            "failed_subscription",

        "subscription_payment_failed":
            "failed_subscription",

        "b2b_receivables":
            "b2b_receivable",
        "invoice_overdue":
            "b2b_receivable",
        "overdue_receivable":
            "b2b_receivable",
        "overdue_invoice":
            "b2b_receivable",
        "receivable_overdue":
            "b2b_receivable",
        "b2b_invoice_overdue":
            "b2b_receivable",

        "mandate":
            "mandate_failure",

        "recurring_payment_failure":
            "mandate_failure",

        "ptp":
            "promise_to_pay",

        "promise-to-pay":
            "promise_to_pay",
    }

    value = aliases.get(
        value,
        value,
    )

    if value not in SUPPORTED_SCENARIOS:

        raise ValueError(
            f"Unsupported scenario '{value}'. "
            f"Supported scenarios: "
            f"{', '.join(sorted(SUPPORTED_SCENARIOS))}"
        )

    return value


# ============================================================
# SCENARIO RECOVERY POLICY
# ============================================================

def apply_scenario_recovery_policy(
    transaction: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:

    scenario = normalize_scenario(
        transaction.get(
            "scenario"
        )
    )

    defaults = SCENARIO_DEFAULTS[
        scenario
    ]

    result = dict(
        result
    )

    diagnosis = dict(
        result.get(
            "diagnosis"
        )
        or {}
    )

    score = dict(
        result.get(
            "score"
        )
        or {}
    )

    action = dict(
        result.get(
            "action"
        )
        or {}
    )

    policy = dict(
        result.get(
            "policy"
        )
        or {}
    )

    execution = dict(
        result.get(
            "execution"
        )
        or {}
    )

    stopping = dict(
        result.get(
            "stopping"
        )
        or {}
    )

    escalation = dict(
        result.get(
            "escalation"
        )
        or {}
    )

    # ========================================================
    # AUTHORITATIVE DIAGNOSIS
    # Preserve a specific payment-failure diagnosis such as
    # bank_decline instead of overwriting it with payment_failure.

    diagnosis_name = defaults[
        "diagnosis"
    ]
    diagnosis_reason = SCENARIO_DIAGNOSIS_REASONS[
        scenario
    ]

    if scenario == "payment_failure":
        failure_reason = safe_string(
            transaction.get(
                "failure_reason"
            )
        ).strip().lower()

        specific_diagnosis = PAYMENT_FAILURE_DIAGNOSES.get(
            failure_reason
        )

        if specific_diagnosis:
            diagnosis_name = specific_diagnosis[
                "diagnosis"
            ]
            diagnosis_reason = specific_diagnosis[
                "reason"
            ]

    diagnosis[
        "diagnosis"
    ] = diagnosis_name

    diagnosis[
        "reason"
    ] = diagnosis_reason

    diagnosis.setdefault(
        "evidence",
        [],
    )

    # ========================================================
    # SCORE DEFAULTS
    # ========================================================

    score.setdefault(
        "recovery_probability",
        0.0,
    )

    score.setdefault(
        "priority_score",
        0.0,
    )

    score.setdefault(
        "priority",
        "LOW",
    )

    # IMPORTANT:
    #
    # This is deliberately NOT setdefault().
    #
    # The scenario policy is authoritative for
    # the final recommended channel.
    #
    score[
        "recommended_channel"
    ] = defaults[
        "channel"
    ]

    # ========================================================
    # AUTHORITATIVE ACTION
    # ========================================================

    action[
        "recovery_action"
    ] = defaults[
        "action"
    ]

    action[
        "strategy"
    ] = defaults[
        "strategy"
    ]

    action[
        "channel"
    ] = defaults[
        "channel"
    ]

    action[
        "scenario"
    ] = scenario

    # ========================================================
    # POLICY
    # ========================================================

    policy[
        "allowed"
    ] = True

    policy[
        "reason"
    ] = (
        "action_within_recovery_policy"
    )

    # ========================================================
    # EXECUTION
    # ========================================================

    transaction_amount = safe_float(
        transaction.get(
            "transaction_amount",
            0.0,
        )
    )

    recovery_probability = float(
        transaction.get(
            "_recovery_probability",
            score.get(
                "recovery_probability",
                0,
            ),
        )
    )

    force_failure = bool(
        transaction.get(
            "_force_recovery_failure",
            False,
        )
    )

    if force_failure:

        recovered = False

    else:

        recovered = (
            recovery_probability
            >= 0.70
        )

    execution[
        "execution_status"
    ] = "simulated"

    execution[
        "action"
    ] = action[
        "recovery_action"
    ]

    execution[
        "channel"
    ] = action[
        "channel"
    ]

    execution[
        "attempt_increment"
    ] = 1

    execution[
        "message_sent"
    ] = True

    execution[
        "recovered"
    ] = recovered

    execution[
        "money_recovered"
    ] = (
        transaction_amount
        if recovered
        else 0.0
    )

    if recovered:

        execution[
            "execution_detail"
        ] = (
            f"Recovery succeeded through "
            f"{action['recovery_action']} "
            f"using {action['channel']} "
            f"for {scenario}."
        )

        stopping[
            "stop"
        ] = True

        stopping[
            "reason"
        ] = "PAYMENT_SUCCESS"

    else:

        execution[
            "execution_detail"
        ] = (
            f"Recovery attempt executed through "
            f"{action['recovery_action']} "
            f"using {action['channel']}, "
            f"but payment was not recovered."
        )

        stopping[
            "stop"
        ] = True

        stopping[
            "reason"
        ] = "RECOVERY_FAILED"

    execution[
        "scenario"
    ] = scenario

    # ========================================================
    # SCENARIO RECOVERY OVERRIDES ESCALATION
    # ========================================================

    if (
        scenario in SUPPORTED_SCENARIOS
        and execution.get(
            "recovered",
            False,
        )
    ):

        escalation[
            "escalate"
        ] = False

        escalation[
            "escalation_level"
        ] = "NONE"

        escalation[
            "reason"
        ] = "payment_recovered"

        escalation[
            "recommended_team"
        ] = None

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result.update(
        {
            "status": (
                "recovered"
                if execution.get(
                    "recovered"
                )
                else "processed"
            ),

            "scenario": scenario,

            "diagnosis": diagnosis,

            "score": score,

            "action": action,

            "policy": policy,

            "execution": execution,

            "stopping": stopping,

            "escalation": escalation,
        }
    )

    return result


# ============================================================
# AUDIT BUILDER
# ============================================================

def build_audit(
    transaction: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:

    diagnosis = (
        result.get(
            "diagnosis"
        )
        or {}
    )

    score = (
        result.get(
            "score"
        )
        or {}
    )

    action = (
        result.get(
            "action"
        )
        or {}
    )

    policy = (
        result.get(
            "policy"
        )
        or {}
    )

    execution = (
        result.get(
            "execution"
        )
        or {}
    )

    stopping = (
        result.get(
            "stopping"
        )
        or {}
    )

    escalation = (
        result.get(
            "escalation"
        )
        or {}
    )

    # ========================================================
    # IMPORTANT:
    #
    # Every audit field below comes from the FINAL result.
    #
    # That means the audit reflects scenario-policy overrides,
    # rather than stale scorer recommendations.
    # ========================================================

    return {
        "timestamp": datetime.utcnow().isoformat(),

        "transaction_id": safe_string(
            transaction.get(
                "transaction_id"
            )
        ),

        "customer_id": safe_string(
            transaction.get(
                "customer_id"
            )
        ),

        "scenario": safe_string(
            result.get(
                "scenario",
                transaction.get(
                    "scenario"
                ),
            )
        ),

        "transaction_amount": safe_float(
            transaction.get(
                "transaction_amount"
            )
        ),

        # ----------------------------------------------------
        # FINAL DIAGNOSIS
        # ----------------------------------------------------

        "diagnosis": safe_string(
            diagnosis.get(
                "diagnosis"
            )
        ),

        "diagnosis_reason": safe_string(
            diagnosis.get(
                "reason"
            )
        ),

        # ----------------------------------------------------
        # FINAL SCORE
        # ----------------------------------------------------

        "recovery_probability": safe_float(
            score.get(
                "recovery_probability"
            )
        ),

        "priority_score": safe_float(
            score.get(
                "priority_score"
            )
        ),

        "priority": safe_string(
            score.get(
                "priority"
            )
        ),

        # ----------------------------------------------------
        # FINAL ACTION
        # ----------------------------------------------------

        "strategy": safe_string(
            action.get(
                "strategy"
            )
        ),

        "recovery_action": safe_string(
            action.get(
                "recovery_action"
            )
        ),

        "recommended_channel": safe_string(
            action.get(
                "channel"
            )
        ),

        # ----------------------------------------------------
        # FINAL POLICY
        # ----------------------------------------------------

        "policy_allowed": bool(
            policy.get(
                "allowed",
                False,
            )
        ),

        "policy_reason": safe_string(
            policy.get(
                "reason"
            )
        ),

        # ----------------------------------------------------
        # FINAL EXECUTION
        # ----------------------------------------------------

        "execution_status": safe_string(
            execution.get(
                "execution_status"
            )
        ),

        "recovered": bool(
            execution.get(
                "recovered",
                False,
            )
        ),

        "money_recovered": safe_float(
            execution.get(
                "money_recovered"
            )
        ),

        "attempt_increment": safe_int(
            execution.get(
                "attempt_increment"
            )
        ),

        "attempt_count": safe_int(
            execution.get(
                "attempt_count"
            )
        ),

        # ----------------------------------------------------
        # FINAL STOPPING
        # ----------------------------------------------------

        "stopped": bool(
            stopping.get(
                "stop",
                False,
            )
        ),

        "stopping_reason": safe_string(
            stopping.get(
                "reason"
            )
        ),

        # ----------------------------------------------------
        # FINAL ESCALATION
        # ----------------------------------------------------

        "escalate": bool(
            escalation.get(
                "escalate",
                False,
            )
        ),

        "escalation_level": safe_string(
            escalation.get(
                "escalation_level"
            )
        ),

        "escalation_reason": safe_string(
            escalation.get(
                "reason"
            )
        ),

        "recommended_team": (
            escalation.get(
                "recommended_team"
            )
        ),
    }


# ============================================================
# RECOVERY AGENT
# ============================================================

def run_recovery_agent(
    transaction: dict[str, Any],
) -> dict[str, Any]:

    scorer = RecoveryScorer()

    agent = RecoveryAgent(
        scorer=scorer
    )

    # If the server-owned attempt counter is already at the bound,
    # the underlying agent may return early before calculating
    # diagnosis/score. Run the explanatory pass on an isolated copy
    # with attempts reset, while forcing the simulated execution to
    # fail. The API keeps ownership of the real attempt counter and
    # applies escalation after this result is returned.
    agent_transaction = dict(
        transaction
    )

    if safe_int(
        transaction.get(
            "recovery_attempts",
            0,
        )
    ) >= MAX_RECOVERY_ATTEMPTS:
        agent_transaction[
            "recovery_attempts"
        ] = 0
        agent_transaction[
            "force_recovery_failure"
        ] = True
        agent_transaction[
            "_force_recovery_failure"
        ] = True

    result = agent.process(
        agent_transaction
    )

    if not isinstance(
        result,
        dict,
    ):

        raise ValueError(
            "RecoveryAgent returned an invalid result."
        )

    # ========================================================
    # STEP 1
    # Apply the authoritative scenario policy.
    # ========================================================

    result = apply_scenario_recovery_policy(
        transaction,
        result,
    )

    # ========================================================
    # STEP 2
    # Build audit AFTER the policy.
    #
    # This is the important fix.
    # ========================================================

    result[
        "audit"
    ] = build_audit(
        transaction,
        result,
    )

    return result


# ============================================================
# PROCESSED EVENT â†’ DATAFRAME ROW
# ============================================================

def processed_event_to_row(
    transaction: dict[str, Any],
    agent_result: dict[str, Any],
) -> dict[str, Any]:

    score = agent_result.get(
        "score",
        {},
    )

    action = agent_result.get(
        "action",
        {},
    )

    execution = agent_result.get(
        "execution",
        {},
    )

    score = (
        score
        if isinstance(
            score,
            dict,
        )
        else {}
    )

    action = (
        action
        if isinstance(
            action,
            dict,
        )
        else {}
    )

    execution = (
        execution
        if isinstance(
            execution,
            dict,
        )
        else {}
    )

    amount = safe_float(
        transaction.get(
            "transaction_amount"
        )
    )

    recovery_probability = safe_float(
        score.get(
            "recovery_probability"
        )
    )

    recovered = normalize_bool(
        transaction.get(
            "recovered",
            execution.get(
                "recovered",
                0,
            ),
        )
    )

    money_recovered = safe_float(
        transaction.get(
            "money_recovered",
            execution.get(
                "money_recovered",
                0.0,
            ),
        )
    )

    return {
        "transaction_id": safe_string(
            transaction.get(
                "transaction_id"
            )
        ),

        "customer_id": safe_string(
            transaction.get(
                "customer_id"
            )
        ),

        "transaction_amount": amount,

        "payment_method": safe_string(
            transaction.get(
                "payment_method"
            )
        ),

        "failure_reason": safe_string(
            transaction.get(
                "failure_reason"
            )
        ),

        "retry_count": safe_int(
            transaction.get(
                "retry_count"
            )
        ),

        "customer_transaction_count": safe_int(
            transaction.get(
                "customer_transaction_count",
                1,
            ),
            1,
        ),

        "customer_success_rate": safe_float(
            transaction.get(
                "customer_success_rate"
            )
        ),

        "payment_method_success_rate": safe_float(
            transaction.get(
                "payment_method_success_rate"
            )
        ),

        "channel": safe_string(
            transaction.get(
                "channel",
                "payment_link",
            ),
            "payment_link",
        ),

        "preferred_channel": safe_string(
            transaction.get(
                "preferred_channel",
                "",
            )
        ),

        "product_interest_score": safe_float(
            transaction.get(
                "product_interest_score"
            )
        ),

        "checkout_progress": safe_float(
            transaction.get(
                "checkout_progress"
            )
        ),

        "customer_email_available": normalize_bool(
            transaction.get(
                "customer_email_available"
            )
        ),

        "customer_phone_available": normalize_bool(
            transaction.get(
                "customer_phone_available"
            )
        ),

        "scenario": safe_string(
            transaction.get(
                "scenario",
                "payment_failure",
            ),
            "payment_failure",
        ),

        "payment_status": safe_string(
            transaction.get(
                "payment_status",
                "failed",
            ),
            "failed",
        ),

        "revenue_at_risk": 1,

        "recovery_attempts": safe_int(
            transaction.get(
                "recovery_attempts"
            )
        ),

        "promise_to_pay": normalize_bool(
            transaction.get(
                "promise_to_pay"
            )
        ),

        "recovered": recovered,

        "money_recovered": money_recovered,

        "recovery_probability": (
            recovery_probability
        ),

        "expected_recovery_value": (
            amount
            * recovery_probability
        ),

        "customer_intent": safe_float(
            score.get(
                "customer_intent"
            )
        ),

        "customer_reliability": safe_float(
            score.get(
                "customer_reliability"
            )
        ),

        "contactability": safe_float(
            score.get(
                "contactability"
            )
        ),

        "recovery_friction": safe_float(
            score.get(
                "recovery_friction"
            )
        ),

        "priority_score": safe_float(
            score.get(
                "priority_score"
            )
        ),

        "priority": safe_string(
            score.get(
                "priority",
                "LOW",
            ),
            "LOW",
        ).upper(),

        "strategy": safe_string(
            action.get(
                "strategy",
                "low_cost_recovery",
            ),
            "low_cost_recovery",
        ),

        "recovery_action": safe_string(
            action.get(
                "recovery_action",
                "general_recovery",
            ),
            "general_recovery",
        ),

        "recommended_channel": safe_string(
            action.get(
                "channel",
                score.get(
                    "recommended_channel",
                    "none",
                ),
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

        role = (
            message.role
            .lower()
            .strip()
        )

        if role in {
            "user",
            "assistant",
        }:

            lines.append(
                f"{role.upper()}: "
                f"{message.content}"
            )

    return "\n".join(
        lines
    )


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

    for message in reversed(
        conversation
    ):

        if (
            message.role
            .lower()
            .strip()
            == "user"
        ):

            return (
                message.content
                .lower()
                .strip()
            )

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

    q = (
        question
        .lower()
        .strip()
    )

    previous_user = (
        last_user_question(
            conversation
        )
    )

    history = (
        get_last_conversation_text(
            conversation
        )
    )

    if q in {
        "hi",
        "hello",
        "hey",
        "hi ai",
        "hello ai",
        "hey ai",
    }:

        return (
            "Hi! I'm your Recovery AI. ðŸ‘‹\n\n"
            "I can help you understand revenue risk, "
            "payment failures, recovery performance, "
            "prioritization, strategies, and agent decisions.\n\n"
            "Try asking:\n"
            "â€¢ Why is revenue at risk?\n"
            "â€¢ Why do transactions fail?\n"
            "â€¢ What should I prioritize first?\n"
            "â€¢ Which strategy performs best?\n"
            "â€¢ Explain the reasoning behind the decision."
        )

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
        keyword in q
        for keyword in recovery_keywords
    )

    has_unrelated_topic = any(
        keyword in q
        for keyword in unrelated_keywords
    )

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
            or q.startswith(
                "explain "
            )
            or q.startswith(
                "tell me "
            )
            or q.startswith(
                "why "
            )
        )
    )

    if (
        has_unrelated_topic
        and not has_recovery_topic
    ):

        return (
            "That question isn't related to Revenue Recovery AI.\n\n"
            "I can help with revenue risk, payment failures, "
            "recovery cases, customer behavior, prioritization, "
            "recovery strategies, agent decisions, and recovery "
            "performance."
        )

    if is_short_followup and (
        "priorit" in previous_user
        or "recover first" in previous_user
        or "which cases" in previous_user
        or "opportunity" in previous_user
    ):

        top = (
            at_risk
            .sort_values(
                [
                    "expected_recovery_value",
                    "priority_score",
                ],
                ascending=False,
            )
            .head(1)
        )

        if top.empty:
            return (
                "There are no recovery cases "
                "available to explain."
            )

        row = top.iloc[0]

        return (
            f"The reasoning behind prioritizing transaction "
            f"{row['transaction_id']} is based on expected recovery value.\n\n"
            f"â€¢ Amount at risk: "
            f"{format_inr(row['transaction_amount'])}\n"
            f"â€¢ Recovery probability: "
            f"{row['recovery_probability'] * 100:.2f}%\n"
            f"â€¢ Expected recovery: "
            f"{format_inr(row['expected_recovery_value'])}\n"
            f"â€¢ Customer intent: "
            f"{row['customer_intent'] * 100:.2f}%\n"
            f"â€¢ Customer success rate: "
            f"{row['customer_success_rate'] * 100:.2f}%\n"
            f"â€¢ Priority score: "
            f"{row['priority_score'] * 100:.2f}%\n\n"
            "The system combines recovery probability, transaction "
            "value, customer intent, and customer success rate."
        )

    if is_short_followup and (
        "failure" in previous_user
        or "failed" in previous_user
        or "bank_decline" in history
        or "decline" in history
    ):

        failure_stats = (
            at_risk
            .groupby(
                "failure_reason"
            )
            .agg(
                cases=(
                    "transaction_id",
                    "count",
                ),
                recovered=(
                    "recovered",
                    "sum",
                ),
                amount=(
                    "transaction_amount",
                    "sum",
                ),
            )
        )

        if failure_stats.empty:
            return (
                "There isn't enough failure data "
                "to explain the issue."
            )

        failure_stats[
            "recovery_rate"
        ] = (
            failure_stats[
                "recovered"
            ]
            / failure_stats[
                "cases"
            ]
            * 100
        )

        worst_name = str(
            failure_stats[
                "recovery_rate"
            ].idxmin()
        )

        worst = failure_stats.loc[
            worst_name
        ]

        return (
            f"The weakest recovery category is "
            f"'{worst_name}'.\n\n"
            f"â€¢ Cases: {int(worst['cases']):,}\n"
            f"â€¢ Transaction value: "
            f"{format_inr(worst['amount'])}\n"
            f"â€¢ Recovery rate: "
            f"{worst['recovery_rate']:.2f}%\n\n"
            "This suggests that the failure type is creating "
            "additional recovery friction."
        )

    if is_short_followup and (
        "strategy" in previous_user
    ):

        strategy_stats = (
            at_risk
            .groupby(
                "strategy"
            )
            .agg(
                cases=(
                    "transaction_id",
                    "count",
                ),
                recovered=(
                    "recovered",
                    "sum",
                ),
                money_recovered=(
                    "money_recovered",
                    "sum",
                ),
            )
        )

        if strategy_stats.empty:
            return (
                "There isn't enough strategy data "
                "to explain the result."
            )

        strategy_stats[
            "recovery_rate"
        ] = (
            strategy_stats[
                "recovered"
            ]
            / strategy_stats[
                "cases"
            ]
            * 100
        )

        best_name = str(
            strategy_stats[
                "recovery_rate"
            ].idxmax()
        )

        best = strategy_stats.loc[
            best_name
        ]

        return (
            f"The reasoning for the strongest strategy, "
            f"'{best_name}', is its observed recovery performance "
            "in the current dataset.\n\n"
            f"â€¢ Recovery rate: "
            f"{best['recovery_rate']:.2f}%\n"
            f"â€¢ Cases: {int(best['cases']):,}\n"
            f"â€¢ Money recovered: "
            f"{format_inr(best['money_recovered'])}"
        )

    if is_short_followup and (
        "risk" in previous_user
        or "revenue" in previous_user
    ):

        return (
            "The revenue risk is driven by failed transactions "
            "that are still marked as recoverable opportunities.\n\n"
            f"â€¢ Revenue at risk: "
            f"{format_inr(summary['total_transaction_value'])}\n"
            f"â€¢ Expected recovery: "
            f"{format_inr(summary['expected_recovery_value'])}\n"
            f"â€¢ Unrecovered cases: "
            f"{summary['unrecovered_cases']:,}"
        )

    if (
        "high priority" in q
        or "high-priority" in q
        or "high priority cases" in q
    ):

        high = (
            at_risk[
                at_risk[
                    "priority"
                ] == "HIGH"
            ]
            .sort_values(
                "expected_recovery_value",
                ascending=False,
            )
            .head(5)
        )

        if high.empty:
            return (
                "There are currently no HIGH-priority "
                "recovery cases."
            )

        top = high.iloc[0]

        total_high_value = float(
            high[
                "transaction_amount"
            ].sum()
        )

        expected_high_value = float(
            high[
                "expected_recovery_value"
            ].sum()
        )

        return (
            f"There are "
            f"{int((at_risk['priority'] == 'HIGH').sum()):,} "
            "HIGH-priority cases.\n\n"
            f"The top opportunity is transaction "
            f"{top['transaction_id']}.\n\n"
            f"â€¢ Amount at risk: "
            f"{format_inr(top['transaction_amount'])}\n"
            f"â€¢ Recovery probability: "
            f"{top['recovery_probability'] * 100:.2f}%\n"
            f"â€¢ Expected recovery: "
            f"{format_inr(top['expected_recovery_value'])}\n"
            f"â€¢ Strategy: {top['strategy']}\n"
            f"â€¢ Channel: {top['recommended_channel']}\n\n"
            f"Among the top five opportunities, "
            f"{format_inr(total_high_value)} is at risk and "
            f"{format_inr(expected_high_value)} is expected to be recovered."
        )

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
                [
                    "expected_recovery_value",
                    "priority_score",
                ],
                ascending=False,
            )
            .head(1)
        )

        if top.empty:
            return (
                "There are currently no recovery "
                "cases available."
            )

        row = top.iloc[0]

        return (
            "I would prioritize cases using expected recovery value "
            "rather than transaction amount alone.\n\n"
            f"Top opportunity: {row['transaction_id']}\n\n"
            f"â€¢ Amount at risk: "
            f"{format_inr(row['transaction_amount'])}\n"
            f"â€¢ Recovery probability: "
            f"{row['recovery_probability'] * 100:.2f}%\n"
            f"â€¢ Expected recovery: "
            f"{format_inr(row['expected_recovery_value'])}\n"
            f"â€¢ Priority: {row['priority']}\n"
            f"â€¢ Strategy: {row['strategy']}\n"
            f"â€¢ Channel: {row['recommended_channel']}"
        )

    if (
        "revenue at risk" in q
        or (
            "why" in q
            and "risk" in q
        )
        or (
            "why" in q
            and "revenue" in q
        )
    ):

        failure_stats = (
            at_risk
            .groupby(
                "failure_reason"
            )
            .agg(
                cases=(
                    "transaction_id",
                    "count",
                ),
                amount=(
                    "transaction_amount",
                    "sum",
                ),
                recovered=(
                    "recovered",
                    "sum",
                ),
            )
            .sort_values(
                "amount",
                ascending=False,
            )
        )

        if failure_stats.empty:

            explanation = (
                "Failure-reason data is not available."
            )

        else:

            top_failure = (
                failure_stats.iloc[0]
            )

            failure_name = str(
                failure_stats.index[0]
            )

            explanation = (
                f"The largest failure category is "
                f"'{failure_name}', representing "
                f"{int(top_failure['cases']):,} cases and "
                f"{format_inr(top_failure['amount'])} "
                "in transaction value."
            )

        return (
            f"Revenue at risk is currently "
            f"{format_inr(summary['total_transaction_value'])} "
            f"across {summary['at_risk_cases']:,} cases.\n\n"
            f"The recovery rate is "
            f"{summary['recovery_rate']:.2f}%, leaving "
            f"{summary['unrecovered_cases']:,} cases unrecovered.\n\n"
            f"{explanation}"
        )

    if (
        "strategy" in q
        or "performing best" in q
        or "best strategy" in q
        or "which strategy" in q
    ):

        strategy_stats = (
            at_risk
            .groupby(
                "strategy"
            )
            .agg(
                cases=(
                    "transaction_id",
                    "count",
                ),
                recovered=(
                    "recovered",
                    "sum",
                ),
                money_recovered=(
                    "money_recovered",
                    "sum",
                ),
            )
        )

        if strategy_stats.empty:
            return (
                "There isn't enough strategy data "
                "to determine a best performer."
            )

        strategy_stats[
            "recovery_rate"
        ] = (
            strategy_stats[
                "recovered"
            ]
            / strategy_stats[
                "cases"
            ]
            * 100
        )

        strategy_stats = (
            strategy_stats
            .sort_values(
                [
                    "recovery_rate",
                    "money_recovered",
                ],
                ascending=False,
            )
        )

        best_name = str(
            strategy_stats.index[0]
        )

        best = strategy_stats.iloc[0]

        return (
            f"The strongest-performing strategy in the current "
            f"data is '{best_name}'.\n\n"
            f"â€¢ Recovery rate: "
            f"{best['recovery_rate']:.2f}%\n"
            f"â€¢ Cases: {int(best['cases']):,}\n"
            f"â€¢ Money recovered: "
            f"{format_inr(best['money_recovered'])}"
        )

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
            .groupby(
                "failure_reason"
            )
            .agg(
                cases=(
                    "transaction_id",
                    "count",
                ),
                amount=(
                    "transaction_amount",
                    "sum",
                ),
                recovered=(
                    "recovered",
                    "sum",
                ),
            )
            .sort_values(
                "cases",
                ascending=False,
            )
        )

        if failure_stats.empty:
            return (
                "There isn't enough failure-reason data "
                "to explain transaction failures."
            )

        top_failures = (
            failure_stats.head(5)
        )

        lines = []

        for failure_name, row in (
            top_failures.iterrows()
        ):

            lines.append(
                f"â€¢ {failure_name}: "
                f"{int(row['cases']):,} cases, "
                f"{format_inr(row['amount'])} at risk"
            )

        return (
            "Transactions are failing for several reasons. "
            "The most common failure categories in the current "
            "data are:\n\n"
            + "\n".join(lines)
        )

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
            "against "
            f"{format_inr(summary['total_transaction_value'])} "
            "at risk."
        )

    if has_recovery_topic:

        return (
            "Here's the current recovery picture:\n\n"
            f"â€¢ Revenue at risk: "
            f"{format_inr(summary['total_transaction_value'])}\n"
            f"â€¢ Expected recovery: "
            f"{format_inr(summary['expected_recovery_value'])}\n"
            f"â€¢ Recovery rate: "
            f"{summary['recovery_rate']:.2f}%\n"
            f"â€¢ Recovery cases: "
            f"{summary['at_risk_cases']:,}\n"
            f"â€¢ Recovered cases: "
            f"{summary['recovered_cases']:,}\n"
            f"â€¢ Unrecovered cases: "
            f"{summary['unrecovered_cases']:,}"
        )

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

    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


@app.get("/recovery-cases.html")
async def recovery_cases_page():

    return FileResponse(
        FRONTEND_DIR / "recovery-cases.html"
    )


@app.get("/customers.html")
async def customers_page():

    return FileResponse(
        FRONTEND_DIR / "customers.html"
    )


@app.get("/analytics.html")
async def analytics_page():

    return FileResponse(
        FRONTEND_DIR / "analytics.html"
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",

        "dataset_exists": (
            DATA_FILE.exists()
        ),

        "dataset": str(
            DATA_FILE
        ),

        "live_recovery_events": len(
            PROCESSED_RECOVERY_EVENTS
        ),
    }


# ============================================================
# CREATE / PROCESS RECOVERY EVENT
# ============================================================

@app.post("/recovery-events")
async def process_recovery_event(
    event: RecoveryEvent,
):

    transaction = event.model_dump()

    # ========================================================
    # Copy public API field into internal key.
    # ========================================================

    transaction[
        "_force_recovery_failure"
    ] = transaction.get(
        "force_recovery_failure",
        False,
    )

    transaction[
        "scenario"
    ] = normalize_scenario(
        transaction.get(
            "scenario"
        )
    )

    transaction[
        "revenue_at_risk"
    ] = 1

    transaction_id = safe_string(
        transaction.get(
            "transaction_id"
        )
    )

    if not transaction_id:

        raise HTTPException(
            status_code=400,
            detail=(
                "transaction_id cannot be empty."
            ),
        )

    # ========================================================
    # SERVER OWNS RECOVERY ATTEMPTS
    # ========================================================

    previous_state = (
        LIVE_RECOVERY_STATE.get(
            transaction_id
        )
    )

    if previous_state:
        transaction[
            "recovery_attempts"
        ] = max(
            0,
            min(
                safe_int(
                    previous_state.get(
                        "recovery_attempts",
                        0,
                    )
                ),
                MAX_RECOVERY_ATTEMPTS,
            ),
        )
    else:
        transaction[
            "recovery_attempts"
        ] = max(
            0,
            min(
                safe_int(
                    transaction.get(
                        "recovery_attempts",
                        0,
                    )
                ),
                MAX_RECOVERY_ATTEMPTS,
            ),
        )

    try:

        # ====================================================
        # RUN RECOVERY AGENT
        # ====================================================

        result = run_recovery_agent(
            transaction
        )

        execution = result.get(
            "execution",
            {},
        )

        if not isinstance(
            execution,
            dict,
        ):

            execution = {}

        # ====================================================
        # SERVER UPDATES ATTEMPT COUNTER
        # ====================================================

        attempt_increment = safe_int(
            execution.get(
                "attempt_increment",
                0,
            )
        )

        previous_attempts = safe_int(
            transaction.get(
                "recovery_attempts",
                0,
            )
        )

        attempt_increment = max(
            0,
            min(
                safe_int(
                    execution.get(
                        "attempt_increment",
                        0,
                    )
                ),
                1,
            ),
        )

        transaction[
            "recovery_attempts"
        ] = min(
            previous_attempts + attempt_increment,
            MAX_RECOVERY_ATTEMPTS,
        )

        execution[
            "attempt_increment"
        ] = attempt_increment
        execution[
            "attempt_count"
        ] = transaction[
            "recovery_attempts"
        ]
        result[
            "execution"
        ] = execution

        # Finalize escalation using the server-owned count and priority rule.
        # HIGH: escalate after the first automated attempt.
        # MEDIUM/LOW: escalate after the third automated attempt.
        if not bool(execution.get("recovered", False)):
            priority = safe_string(
                (result.get("score") or {}).get("priority", "LOW"),
                "LOW",
            ).strip().upper()
            escalation_threshold = 1 if priority == "HIGH" else 3

            if transaction["recovery_attempts"] >= escalation_threshold:
                result["stopping"] = {
                    "stop": True,
                    "reason": "RECOVERY_ESCALATION_REQUIRED",
                }
                result["escalation"] = {
                    "escalate": True,
                    "escalation_level": "HUMAN_REVIEW",
                    "reason": "recovery_attempt_limit_reached",
                    "recommended_team": "payments_recovery",
                }
            else:
                result["escalation"] = {
                    "escalate": False,
                    "escalation_level": "NONE",
                    "reason": "recovery_attempt_failed_automation_can_continue",
                    "recommended_team": None,
                }

        

        # ====================================================
        # IMPORTANT:
        #
        # Execution attempt_count was added by the server.
        # Rebuild the audit one more time so the audit also
        # contains the final attempt_count.
        # ====================================================

        result[
            "audit"
        ] = build_audit(
            transaction,
            result,
        )

        # ====================================================
        # RECOVERY STATE
        # ====================================================

        recovered = bool(
            execution.get(
                "recovered",
                False,
            )
        )

        money_recovered = safe_float(
            execution.get(
                "money_recovered",
                0.0,
            )
        )

        transaction[
            "recovered"
        ] = int(
            recovered
        )

        transaction[
            "money_recovered"
        ] = money_recovered

        transaction[
            "payment_status"
        ] = (
            "paid"
            if recovered
            else "failed"
        )

        # ====================================================
        # PERSIST LIVE STATE
        # ====================================================

        LIVE_RECOVERY_STATE[
            transaction_id
        ] = {

            "recovery_attempts": (
                transaction[
                    "recovery_attempts"
                ]
            ),

            "recovered": int(
                recovered
            ),

            "payment_status": (
                transaction[
                    "payment_status"
                ]
            ),

            "money_recovered": (
                money_recovered
            ),
        }

        # ====================================================
        # STORE PROCESSED EVENT
        # ====================================================

        live_row = processed_event_to_row(
            transaction,
            result,
        )

        live_row[
            "_agent_result"
        ] = result

        live_row[
            "recovery_attempts"
        ] = transaction[
            "recovery_attempts"
        ]

        PROCESSED_RECOVERY_EVENTS[
            transaction_id
        ] = live_row

        persist_recovery_events()

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
            detail=(
                "Recovery event processing failed: "
                f"{exc}"
            ),
        ) from exc



# ============================================================
# RUN RECOVERY
# ============================================================

@app.post("/recovery/run")
async def run_recovery():
    """
    Run recovery processing for the highest-value unrecovered
    recovery opportunity currently available.

    This endpoint reuses the same recovery-event processing path
    used by POST /recovery-events, so attempt counting, scenario
    policy, audit generation, and escalation remain consistent.
    """

    try:
        at_risk = get_at_risk_data()

        if at_risk.empty:
            return {
                "success": False,
                "status": "no_cases",
                "message": "No recovery cases are currently available.",
            }

        # Only run automation against cases that have not already
        # been recovered. This prevents repeatedly processing the
        # same successful recovery.
        unrecovered = at_risk[
            at_risk["recovered"].apply(normalize_bool) == 0
        ].copy()

        if unrecovered.empty:
            return {
                "success": False,
                "status": "no_unrecovered_cases",
                "message": "All currently available recovery cases are recovered.",
            }

        # Highest expected recovery value is the primary opportunity
        # selection criterion, with priority score as a tie-breaker.
        top = (
            unrecovered
            .sort_values(
                [
                    "expected_recovery_value",
                    "priority_score",
                ],
                ascending=False,
            )
            .iloc[0]
        )

        transaction_id = safe_string(
            top.get("transaction_id")
        )

        if not transaction_id:
            raise HTTPException(
                status_code=400,
                detail="Selected recovery case has no transaction_id.",
            )

        # Build the same RecoveryEvent model accepted by
        # POST /recovery-events. Values are normalized so the
        # endpoint remains compatible with the current dataset.
        event = RecoveryEvent(
            transaction_id=transaction_id,
            customer_id=safe_string(
                top.get("customer_id")
            ),
            transaction_amount=safe_float(
                top.get("transaction_amount")
            ),
            payment_method=safe_string(
                top.get(
                    "payment_method",
                    "unknown",
                ),
                "unknown",
            ),
            failure_reason=safe_string(
                top.get(
                    "failure_reason",
                    "unknown",
                ),
                "unknown",
            ),
            retry_count=max(
                0,
                safe_int(
                    top.get(
                        "retry_count",
                        0,
                    )
                ),
            ),
            customer_transaction_count=max(
                1,
                safe_int(
                    top.get(
                        "customer_transaction_count",
                        1,
                    ),
                    1,
                ),
            ),
            customer_success_rate=min(
                1.0,
                max(
                    0.0,
                    safe_float(
                        top.get(
                            "customer_success_rate",
                            0.8,
                        ),
                        0.8,
                    ),
                ),
            ),
            payment_method_success_rate=min(
                1.0,
                max(
                    0.0,
                    safe_float(
                        top.get(
                            "payment_method_success_rate",
                            0.8,
                        ),
                        0.8,
                    ),
                ),
            ),
            channel=safe_string(
                top.get(
                    "channel",
                    "payment_link",
                ),
                "payment_link",
            ),
            preferred_channel=(
                safe_string(
                    top.get(
                        "preferred_channel",
                        "",
                    )
                )
                or None
            ),
            product_interest_score=min(
                1.0,
                max(
                    0.0,
                    safe_float(
                        top.get(
                            "product_interest_score",
                            0.5,
                        ),
                        0.5,
                    ),
                ),
            ),
            checkout_progress=min(
                1.0,
                max(
                    0.0,
                    safe_float(
                        top.get(
                            "checkout_progress",
                            0.5,
                        ),
                        0.5,
                    ),
                ),
            ),
            customer_email_available=normalize_bool(
                top.get(
                    "customer_email_available",
                    1,
                )
            ),
            customer_phone_available=normalize_bool(
                top.get(
                    "customer_phone_available",
                    1,
                )
            ),
            scenario=normalize_scenario(
                top.get(
                    "scenario",
                    "payment_failure",
                )
            ),
            payment_status=safe_string(
                top.get(
                    "payment_status",
                    "failed",
                ),
                "failed",
            ),
            revenue_at_risk=1,
            recovery_attempts=max(
                0,
                safe_int(
                    top.get(
                        "recovery_attempts",
                        0,
                    )
                ),
            ),
            promise_to_pay=normalize_bool(
                top.get(
                    "promise_to_pay",
                    0,
                )
            ),
            recovered=0,
            money_recovered=0.0,
        )

        # Reuse the authoritative recovery-event endpoint logic.
        result = await process_recovery_event(event)

        return {
            "success": True,
            "status": "processed",
            "transaction_id": transaction_id,
            "result": result,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Recovery run failed: "
                f"{exc}"
            ),
        ) from exc

# ============================================================
# DASHBOARD SUMMARY
# ============================================================

@app.get("/dashboard-summary")
async def dashboard_summary_api():

    at_risk = get_at_risk_data()
    active = get_unrecovered_data(at_risk)

    summary = dashboard_summary(
        at_risk
    )

    priority_counts = (
        active[
            "priority"
        ]
        .value_counts()
        .reindex(
            [
                "HIGH",
                "MEDIUM",
                "LOW",
            ],
            fill_value=0,
        )
    )

    strategy_order = [
        "aggressive_recovery",
        "assisted_recovery",
        "standard_recovery",
        "low_cost_recovery",
    ]

    strategy_counts = (
        active[
            "strategy"
        ]
        .value_counts()
        .reindex(
            strategy_order,
            fill_value=0,
        )
    )

    return {
        **summary,

        "priority_distribution": [
            {
                "priority": priority,
                "cases": int(
                    priority_counts[
                        priority
                    ]
                ),
            }
            for priority in [
                "HIGH",
                "MEDIUM",
                "LOW",
            ]
        ],

        "strategy_distribution": [
            {
                "strategy": strategy,
                "cases": int(
                    strategy_counts[
                        strategy
                    ]
                ),
            }
            for strategy in strategy_order
        ],
    }


# ============================================================
# OVERALL RECOVERY METRICS
# ============================================================

@app.get("/overall-metrics")
async def overall_metrics():
    """Return dataset-wide recovery performance, including live updates."""

    df = get_at_risk_data()

    if df.empty:
        return {
            "success": True,
            "total_cases": 0,
            "total_transaction_value": 0.0,
            "recovered_cases": 0,
            "unrecovered_cases": 0,
            "money_recovered": 0.0,
            "overall_recovery_rate": 0.0,
            "recovery_value_rate": 0.0,
            "total_customers": 0,
            "average_transaction_value": 0.0,
        }

    total_cases = int(len(df))
    total_value = float(df["transaction_amount"].sum())
    recovered_cases = int(
        df["recovered"].apply(normalize_bool).sum()
    )
    unrecovered_cases = max(
        0,
        total_cases - recovered_cases,
    )
    money_recovered = float(df["money_recovered"].sum())

    overall_recovery_rate = (
        recovered_cases / total_cases * 100
        if total_cases
        else 0.0
    )

    recovery_value_rate = (
        money_recovered / total_value * 100
        if total_value
        else 0.0
    )

    total_customers = int(
        df["customer_id"].astype(str).nunique()
    ) if "customer_id" in df.columns else 0

    average_transaction_value = (
        total_value / total_cases
        if total_cases
        else 0.0
    )

    return {
        "success": True,
        "total_cases": total_cases,
        "total_transaction_value": round(total_value, 2),
        "recovered_cases": recovered_cases,
        "unrecovered_cases": unrecovered_cases,
        "money_recovered": round(money_recovered, 2),
        "overall_recovery_rate": round(
            overall_recovery_rate, 2
        ),
        "recovery_value_rate": round(
            recovery_value_rate, 2
        ),
        "total_customers": total_customers,
        "average_transaction_value": round(
            average_transaction_value, 2
        ),
    }


# ============================================================
# METRICS
# ============================================================

@app.get("/metrics")
async def metrics():

    at_risk = get_at_risk_data()

    summary = dashboard_summary(
        at_risk
    )

    high_priority = int(
        (
            at_risk[
                "priority"
            ]
            == "HIGH"
        ).sum()
    )

    return {
        **summary,

        "high_priority_cases": (
            high_priority
        ),
    }


@app.get("/metrics/priority")
async def priority_metrics():

    at_risk = get_at_risk_data()

    counts = (
        at_risk[
            "priority"
        ]
        .value_counts()
        .reindex(
            [
                "HIGH",
                "MEDIUM",
                "LOW",
            ],
            fill_value=0,
        )
    )

    return {
        "priority_distribution": [
            {
                "priority": priority,
                "cases": int(
                    counts[
                        priority
                    ]
                ),
            }
            for priority in [
                "HIGH",
                "MEDIUM",
                "LOW",
            ]
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
        at_risk[
            "strategy"
        ]
        .value_counts()
        .reindex(
            strategies,
            fill_value=0,
        )
    )

    return {
        "strategy_distribution": [
            {
                "strategy": strategy,
                "cases": int(
                    counts[
                        strategy
                    ]
                ),
            }
            for strategy in strategies
        ]
    }


# ============================================================
# AI ANALYSIS
# ============================================================

@app.post("/ai/analyze")
async def analyze_recovery_ai(
    request: AIQuestion,
):

    question = (
        request.question
        .strip()
    )

    if not question:

        return {
            "success": False,

            "answer": (
                "Please enter a question."
            ),

            "conversation": [
                message.model_dump()
                for message
                in request.conversation
            ],
        }

    at_risk = get_at_risk_data()

    summary = dashboard_summary(
        at_risk
    )

    answer = get_ai_answer(
        question=question,
        conversation=request.conversation,
        at_risk=at_risk,
        summary=summary,
    )

    conversation = [
        message.model_dump()
        for message
        in request.conversation
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

    conversation = conversation[
        -20:
    ]

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

# Restore persisted live recovery state at API startup.
load_persisted_recovery_events()


@app.get("/top-opportunities")
async def top_opportunities(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
):

    at_risk = get_unrecovered_data()

    top = (
        at_risk
        .sort_values(
            [
                "expected_recovery_value",
                "priority_score",
            ],
            ascending=False,
        )
        .head(limit)
    )

    results = []

    for _, row in top.iterrows():

        results.append(
            {
                "transaction_id": safe_string(
                    row[
                        "transaction_id"
                    ]
                ),

                "customer_id": safe_string(
                    row[
                        "customer_id"
                    ]
                ),

                "transaction_amount": round(
                    safe_float(
                        row[
                            "transaction_amount"
                        ]
                    ),
                    2,
                ),

                "recovery_probability": round(
                    safe_float(
                        row[
                            "recovery_probability"
                        ]
                    ),
                    4,
                ),

                "priority_score": round(
                    safe_float(
                        row[
                            "priority_score"
                        ]
                    ),
                    4,
                ),

                "priority": safe_string(
                    row[
                        "priority"
                    ]
                ),

                "strategy": safe_string(
                    row[
                        "strategy"
                    ]
                ),

                "recommended_channel": safe_string(
                    row[
                        "recommended_channel"
                    ]
                ),

                "expected_recovery_value": round(
                    safe_float(
                        row[
                            "expected_recovery_value"
                        ]
                    ),
                    2,
                ),
            }
        )

    return results


# ============================================================
# RECOVERY CASES
# ============================================================

@app.get("/recovery-cases")
async def recovery_cases_api(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),

    offset: int = Query(
        default=0,
        ge=0,
    ),

    priority: str | None = None,

    strategy: str | None = None,

    search: str | None = None,
):

    at_risk = get_unrecovered_data()

    if priority:

        at_risk = at_risk[
            at_risk[
                "priority"
            ]
            .astype(str)
            .str.upper()
            == priority.upper()
        ]

    if strategy:

        at_risk = at_risk[
            at_risk[
                "strategy"
            ]
            .astype(str)
            .str.lower()
            == strategy.lower()
        ]

    if search:

        term = (
            search
            .lower()
            .strip()
        )

        transaction_match = (
            at_risk[
                "transaction_id"
            ]
            .astype(str)
            .str.lower()
            .str.contains(
                term,
                regex=False,
            )
        )

        customer_match = (
            at_risk[
                "customer_id"
            ]
            .astype(str)
            .str.lower()
            .str.contains(
                term,
                regex=False,
            )
        )

        at_risk = at_risk[
            transaction_match
            | customer_match
        ]

    total = len(
        at_risk
    )

    at_risk = (
        at_risk
        .sort_values(
            [
                "priority_score",
                "expected_recovery_value",
            ],
            ascending=False,
        )
    )

    page = at_risk.iloc[
        offset:
        offset + limit
    ]

    results = []

    for _, row in page.iterrows():

        results.append(
            {
                "transaction_id": safe_string(
                    row[
                        "transaction_id"
                    ]
                ),

                "customer_id": safe_string(
                    row[
                        "customer_id"
                    ]
                ),

                "transaction_amount": round(
                    safe_float(
                        row[
                            "transaction_amount"
                        ]
                    ),
                    2,
                ),

                "priority": safe_string(
                    row[
                        "priority"
                    ]
                ),

                "priority_score": round(
                    safe_float(
                        row[
                            "priority_score"
                        ]
                    ),
                    4,
                ),

                "recovery_probability": round(
                    safe_float(
                        row[
                            "recovery_probability"
                        ]
                    ),
                    4,
                ),

                "strategy": safe_string(
                    row[
                        "strategy"
                    ]
                ),

                "recovery_action": safe_string(
                    row[
                        "recovery_action_display"
                    ]
                ),

                "recommended_channel": safe_string(
                    row[
                        "recommended_channel"
                    ]
                ),

                "recovered": bool(
                    normalize_bool(
                        row[
                            "recovered"
                        ]
                    )
                ),

                "money_recovered": round(
                    safe_float(
                        row[
                            "money_recovered"
                        ]
                    ),
                    2,
                ),

                "expected_recovery_value": round(
                    safe_float(
                        row[
                            "expected_recovery_value"
                        ]
                    ),
                    2,
                ),
            }
        )

    return {
        "total": total,

        "offset": offset,

        "limit": limit,

        "returned": len(
            results
        ),

        "cases": results,
    }


# ============================================================
# CUSTOMERS
# ============================================================

@app.get("/customers")
async def customers_api():
    # --------------------------------------------------------
    # COMPLETE DATASET
    # --------------------------------------------------------
    df = prepare_base_dataframe(
        load_data()
    )
    if df.empty:
        return {
            "total_customers": 0,
            "customers_with_cases": 0,
            "recovered_customers": 0,
            "total_cases": 0,
            "money_recovered": 0.0,
            "customers": [],
        }
    # --------------------------------------------------------
    # APPLY PERSISTED RECOVERY AGENT STATE
    # --------------------------------------------------------
    if PROCESSED_RECOVERY_EVENTS:
        event_df = pd.DataFrame(
            PROCESSED_RECOVERY_EVENTS.values()
        )
        if not event_df.empty and "transaction_id" in event_df.columns:
            event_df = prepare_base_dataframe(
                event_df
            )
            event_df = event_df.set_index(
                "transaction_id"
            )
            df = df.set_index(
                "transaction_id"
            )
            common_ids = df.index.intersection(
                event_df.index
            )
            for column in [
                "recovered",
                "money_recovered",
                "payment_status",
                "recovery_attempts",
                "recovery_probability",
                "customer_intent",
                "customer_reliability",
                "contactability",
                "recovery_friction",
                "priority",
                "priority_score",
                "strategy",
                "recovery_action",
                "recommended_channel",
                "expected_recovery_value",
            ]:
                if column in event_df.columns:
                    df.loc[
                        common_ids,
                        column
                    ] = event_df.loc[
                        common_ids,
                        column
                    ]
            df = df.reset_index()
    # --------------------------------------------------------
    # NORMALIZE CUSTOMER IDS
    # --------------------------------------------------------
    df["customer_id"] = (
        df["customer_id"]
        .astype(str)
        .str.strip()
    )
    df = df[
        df["customer_id"] != ""
    ].copy()
    # --------------------------------------------------------
    # ENSURE TRANSACTION-LEVEL MODEL METRICS EXIST
    #
    # Existing persisted values are preserved.
    # Missing values are calculated using the project's
    # existing scoring formulas.
    # --------------------------------------------------------
    calculated_probability = (
        calculate_recovery_probability(
            df
        )
    )
    if "recovery_probability" not in df.columns:
        df[
            "recovery_probability"
        ] = calculated_probability
    else:
        existing_probability = pd.to_numeric(
            df[
                "recovery_probability"
            ],
            errors="coerce"
        )
        df[
            "recovery_probability"
        ] = existing_probability.fillna(
            calculated_probability
        )
    df[
        "recovery_probability"
    ] = (
        df[
            "recovery_probability"
        ]
        .clip(0, 1)
    )
    # --------------------------------------------------------
    # EXPECTED RECOVERY
    # --------------------------------------------------------
    calculated_expected_recovery = (
        df[
            "transaction_amount"
        ]
        * df[
            "recovery_probability"
        ]
    )
    if "expected_recovery_value" not in df.columns:
        df[
            "expected_recovery_value"
        ] = calculated_expected_recovery
    else:
        existing_expected = pd.to_numeric(
            df[
                "expected_recovery_value"
            ],
            errors="coerce"
        )
        df[
            "expected_recovery_value"
        ] = existing_expected.fillna(
            calculated_expected_recovery
        )
    # --------------------------------------------------------
    # CUSTOMER INTENT
    # --------------------------------------------------------
    calculated_intent = (
        calculate_customer_intent(
            df
        )
    )
    if "customer_intent" not in df.columns:
        df[
            "customer_intent"
        ] = calculated_intent
    else:
        existing_intent = pd.to_numeric(
            df[
                "customer_intent"
            ],
            errors="coerce"
        )
        df[
            "customer_intent"
        ] = existing_intent.fillna(
            calculated_intent
        )
    df[
        "customer_intent"
    ] = (
        df[
            "customer_intent"
        ]
        .clip(0, 1)
    )
    # --------------------------------------------------------
    # VALUE SCORE
    # --------------------------------------------------------
    df[
        "value_score"
    ] = calculate_value_score(
        df
    )
    # --------------------------------------------------------
    # PRIORITY SCORE
    # --------------------------------------------------------
    calculated_priority_score = (
        calculate_priority_score(
            df
        )
    )
    if "priority_score" not in df.columns:
        df[
            "priority_score"
        ] = calculated_priority_score
    else:
        existing_priority_score = pd.to_numeric(
            df[
                "priority_score"
            ],
            errors="coerce"
        )
        df[
            "priority_score"
        ] = existing_priority_score.fillna(
            calculated_priority_score
        )
    df[
        "priority_score"
    ] = (
        df[
            "priority_score"
        ]
        .clip(0, 1)
    )
    # --------------------------------------------------------
    # PRIORITY LABEL
    #
    # Priority is always derived from the actual score so that
    # customer directory and recovery cases stay consistent.
    # --------------------------------------------------------
    df[
        "priority"
    ] = assign_priority(
        df[
            "priority_score"
        ]
    )
    # --------------------------------------------------------
    # STRATEGY
    # --------------------------------------------------------
    calculated_strategy = (
        assign_strategy(
            df[
                "priority_score"
            ]
        )
    )
    if "strategy" not in df.columns:
        df[
            "strategy"
        ] = calculated_strategy
    else:
        strategy = (
            df[
                "strategy"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        missing_strategy = (
            strategy == ""
        )
        strategy.loc[
            missing_strategy
        ] = calculated_strategy.loc[
            missing_strategy
        ]
        df[
            "strategy"
        ] = strategy
    # --------------------------------------------------------
    # RECOVERY STATE
    # --------------------------------------------------------
    df[
        "recovered"
    ] = (
        df[
            "recovered"
        ]
        .apply(
            normalize_bool
        )
    )
    df[
        "money_recovered"
    ] = pd.to_numeric(
        df[
            "money_recovered"
        ],
        errors="coerce"
    ).fillna(0.0)
    # --------------------------------------------------------
    # CUSTOMER AGGREGATION
    # --------------------------------------------------------
    grouped = (
        df
        .groupby(
            "customer_id",
            as_index=False
        )
        .agg(
            cases=(
                "transaction_id",
                "count"
            ),
            amount_at_risk=(
                "transaction_amount",
                "sum"
            ),
            recovered_cases=(
                "recovered",
                "sum"
            ),
            money_recovered=(
                "money_recovered",
                "sum"
            ),
            average_recovery_probability=(
                "recovery_probability",
                "mean"
            ),
            average_priority_score=(
                "priority_score",
                "mean"
            ),
            high_priority_cases=(
                "priority",
                lambda values:
                    int(
                        (
                            values
                            .astype(str)
                            .str.upper()
                            == "HIGH"
                        ).sum()
                    )
            ),
            medium_priority_cases=(
                "priority",
                lambda values:
                    int(
                        (
                            values
                            .astype(str)
                            .str.upper()
                            == "MEDIUM"
                        ).sum()
                    )
            ),
            low_priority_cases=(
                "priority",
                lambda values:
                    int(
                        (
                            values
                            .astype(str)
                            .str.upper()
                            == "LOW"
                        ).sum()
                    )
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
    # --------------------------------------------------------
    # RECOVERY RATE
    # --------------------------------------------------------
    grouped[
        "recovery_rate"
    ] = (
        grouped[
            "recovered_cases"
        ]
        / grouped[
            "cases"
        ].replace(
            0,
            1
        )
        * 100
    )
    # --------------------------------------------------------
    # SORT CUSTOMERS BY RECOVERED VALUE
    # --------------------------------------------------------
    grouped = grouped.sort_values(
        [
            "money_recovered",
            "amount_at_risk"
        ],
        ascending=False
    )
    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------
    customers = []
    for _, row in grouped.iterrows():
        customers.append(
            {
                "customer_id":
                    safe_string(
                        row[
                            "customer_id"
                        ]
                    ),
                "cases":
                    safe_int(
                        row[
                            "cases"
                        ]
                    ),
                "amount_at_risk":
                    round(
                        safe_float(
                            row[
                                "amount_at_risk"
                            ]
                        ),
                        2
                    ),
                "recovered_cases":
                    safe_int(
                        row[
                            "recovered_cases"
                        ]
                    ),
                "recovery_rate":
                    round(
                        safe_float(
                            row[
                                "recovery_rate"
                            ]
                        ),
                        2
                    ),
                "money_recovered":
                    round(
                        safe_float(
                            row[
                                "money_recovered"
                            ]
                        ),
                        2
                    ),
                "average_recovery_probability":
                    round(
                        safe_float(
                            row[
                                "average_recovery_probability"
                            ]
                        ),
                        4
                    ),
                "average_priority_score":
                    round(
                        safe_float(
                            row[
                                "average_priority_score"
                            ]
                        ),
                        4
                    ),
                "high_priority_cases":
                    safe_int(
                        row[
                            "high_priority_cases"
                        ]
                    ),
                "medium_priority_cases":
                    safe_int(
                        row[
                            "medium_priority_cases"
                        ]
                    ),
                "low_priority_cases":
                    safe_int(
                        row[
                            "low_priority_cases"
                        ]
                    ),
            }
        )
    return {
        "total_customers":
            int(
                len(
                    grouped
                )
            ),
        "customers_with_cases":
            int(
                (
                    grouped[
                        "cases"
                    ] > 0
                ).sum()
            ),
        "recovered_customers":
            int(
                (
                    grouped[
                        "recovered_cases"
                    ] > 0
                ).sum()
            ),
        "total_cases":
            int(
                len(df)
            ),
        "money_recovered":
            round(
                safe_float(
                    df[
                        "money_recovered"
                    ].sum()
                ),
                2
            ),
        "customers":
            customers,
    }
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
                cases=(
                    "transaction_id",
                    "count",
                ),

                recovered=(
                    "recovered",
                    "sum",
                ),

                money_recovered=(
                    "money_recovered",
                    "sum",
                ),

                amount_at_risk=(
                    "transaction_amount",
                    "sum",
                ),
            )
            .reset_index()
        )

        grouped[
            "recovery_rate"
        ] = (
            grouped[
                "recovered"
            ]
            / grouped[
                "cases"
            ]
            * 100
        )

        return [
            {
                column: safe_string(
                    row[
                        column
                    ]
                ),

                "cases": safe_int(
                    row[
                        "cases"
                    ]
                ),

                "recovered": safe_int(
                    row[
                        "recovered"
                    ]
                ),

                "recovery_rate": round(
                    safe_float(
                        row[
                            "recovery_rate"
                        ]
                    ),
                    2,
                ),

                "amount_at_risk": round(
                    safe_float(
                        row[
                            "amount_at_risk"
                        ]
                    ),
                    2,
                ),

                "money_recovered": round(
                    safe_float(
                        row[
                            "money_recovered"
                        ]
                    ),
                    2,
                ),
            }

            for _, row
            in grouped.iterrows()
        ]

    return {
        "summary": dashboard_summary(
            at_risk
        ),

        "scenario": group_recovery(
            "scenario"
        ),

        "payment_method": group_recovery(
            "payment_method"
        ),

        "channel": group_recovery(
            "channel"
        ),

        "failure_reason": group_recovery(
            "failure_reason"
        ),

        "priority": group_recovery(
            "priority"
        ),

        "strategy": group_recovery(
            "strategy"
        ),
    }


# CASE WORKFLOW EXTENSIONS
# Add these routes to src/api/main.py.
# They reuse the existing RecoveryEvent + process_recovery_event path.
# They do NOT change ML scoring or escalation rules.


@app.get("/recovery-case.html")
async def recovery_case_page():
    return FileResponse(
        FRONTEND_DIR / "recovery-case.html"
    )

class RecoveryBatchRequest(BaseModel):
    transaction_ids: list[str] = Field(..., min_length=1, max_length=50)


def _recovery_case_row(transaction_id: str):
    """
    Return a transaction from the COMPLETE dataset.
    Active recovery cases are a subset of the dataset, so this
    function must not use get_at_risk_data() exclusively. A case
    remains viewable after recovery, with the latest live/processed
    state overlaid onto the original dataset row.
    """
    txid = safe_string(transaction_id)
    if not txid:
        return None
    # --------------------------------------------------------
    # START WITH THE COMPLETE DATASET
    # --------------------------------------------------------
    df = prepare_base_dataframe(
        load_data()
    )
    if df.empty:
        return None
    if "transaction_id" not in df.columns:
        return None
    matches = df[
        df["transaction_id"]
        .astype(str)
        .str.strip()
        == txid
    ]
    if matches.empty:
        return None
    row = matches.iloc[0].copy()
    # --------------------------------------------------------
    # OVERLAY THE LATEST PROCESSED RECOVERY EVENT
    # --------------------------------------------------------
    processed = (
        PROCESSED_RECOVERY_EVENTS.get(
            txid,
            {}
        )
    )
    if isinstance(processed, dict) and processed:
        for key, value in processed.items():
            if value is not None:
                row[key] = value
    # --------------------------------------------------------
    # OVERLAY CURRENT LIVE RECOVERY STATE
    #
    # Only state values that actually exist are applied.
    # --------------------------------------------------------
    live = (
        LIVE_RECOVERY_STATE.get(
            txid,
            {}
        )
    )
    if isinstance(live, dict) and live:
        for key, value in live.items():
            if value is not None:
                row[key] = value
    return row
def _event_from_recovery_row(top) -> RecoveryEvent:
    return RecoveryEvent(
        transaction_id=safe_string(top.get("transaction_id")),
        customer_id=safe_string(top.get("customer_id")),
        transaction_amount=safe_float(top.get("transaction_amount")),
        payment_method=safe_string(top.get("payment_method", "unknown"), "unknown"),
        failure_reason=safe_string(top.get("failure_reason", "unknown"), "unknown"),
        retry_count=max(0, safe_int(top.get("retry_count", 0))),
        customer_transaction_count=max(1, safe_int(top.get("customer_transaction_count", 1), 1)),
        customer_success_rate=min(1.0, max(0.0, safe_float(top.get("customer_success_rate", 0.8), 0.8))),
        payment_method_success_rate=min(1.0, max(0.0, safe_float(top.get("payment_method_success_rate", 0.8), 0.8))),
        channel=safe_string(top.get("channel", "payment_link"), "payment_link"),
        preferred_channel=(safe_string(top.get("preferred_channel", "")) or None),
        product_interest_score=min(1.0, max(0.0, safe_float(top.get("product_interest_score", 0.5), 0.5))),
        checkout_progress=min(1.0, max(0.0, safe_float(top.get("checkout_progress", 0.5), 0.5))),
        customer_email_available=normalize_bool(top.get("customer_email_available", 1)),
        customer_phone_available=normalize_bool(top.get("customer_phone_available", 1)),
        scenario=normalize_scenario(top.get("scenario", "payment_failure")),
        payment_status=safe_string(top.get("payment_status", "failed"), "failed"),
        revenue_at_risk=1,
        recovery_attempts=max(0, safe_int(top.get("recovery_attempts", 0))),
        promise_to_pay=normalize_bool(top.get("promise_to_pay", 0)),
        recovered=0,
        money_recovered=0.0,
    )


@app.get("/recovery-case/{transaction_id}")
async def recovery_case_detail(transaction_id: str):
    row = _recovery_case_row(transaction_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found."
        )
    txid = safe_string(
        row.get("transaction_id")
    )
    live = (
        LIVE_RECOVERY_STATE.get(
            txid,
            {}
        )
    )
    processed = (
        PROCESSED_RECOVERY_EVENTS.get(
            txid,
            {}
        )
    )
    # --------------------------------------------------------
    # Determine whether a real Recovery Agent execution exists.
    # --------------------------------------------------------
    has_historical_agent_execution = (
        isinstance(processed, dict)
        and bool(processed.get("_agent_result"))
    )
    # --------------------------------------------------------
    # For transactions without historical agent execution,
    # calculate a CURRENT model assessment from the actual
    # dataset features using the project's existing formulas.
    # --------------------------------------------------------
    assessment_probability = None
    assessment_intent = None
    assessment_value_score = None
    assessment_priority_score = None
    assessment_priority = None
    assessment_expected_recovery = None
    assessment_strategy = None
    try:
        if not has_historical_agent_execution:
            assessment_df = pd.DataFrame(
                [row.to_dict()]
            )
            assessment_df = prepare_base_dataframe(
                assessment_df
            )
            assessment_probability = (
                calculate_recovery_probability(
                    assessment_df
                ).iloc[0]
            )
            assessment_intent = (
                calculate_customer_intent(
                    assessment_df
                ).iloc[0]
            )
            assessment_value_score = (
                calculate_value_score(
                    assessment_df
                ).iloc[0]
            )
            assessment_df[
                "recovery_probability"
            ] = assessment_probability
            assessment_df[
                "customer_intent"
            ] = assessment_intent
            assessment_df[
                "value_score"
            ] = assessment_value_score
            assessment_priority_score = (
                calculate_priority_score(
                    assessment_df
                ).iloc[0]
            )
            assessment_priority = (
                assign_priority(
                    pd.Series(
                        [assessment_priority_score]
                    )
                ).iloc[0]
            )
            assessment_strategy = (
                assign_strategy(
                    pd.Series(
                        [assessment_priority_score]
                    )
                ).iloc[0]
            )
            assessment_expected_recovery = (
                safe_float(
                    row.get(
                        "transaction_amount"
                    )
                )
                * safe_float(
                    assessment_probability
                )
            )
    except Exception:
        assessment_probability = None
        assessment_intent = None
        assessment_value_score = None
        assessment_priority_score = None
        assessment_priority = None
        assessment_expected_recovery = None
        assessment_strategy = None
    # --------------------------------------------------------
    # Historical agent values take precedence.
    # Otherwise expose the current model assessment.
    # --------------------------------------------------------
    historical_result = (
        processed.get(
            "_agent_result",
            {}
        )
        if isinstance(processed, dict)
        else {}
    )
    historical_score = (
        historical_result.get(
            "score",
            {}
        )
        if isinstance(historical_result, dict)
        else {}
    )
    historical_action = (
        historical_result.get(
            "action",
            {}
        )
        if isinstance(historical_result, dict)
        else {}
    )
    historical_execution = (
        historical_result.get(
            "execution",
            {}
        )
        if isinstance(historical_result, dict)
        else {}
    )
    historical_stopping = (
        historical_result.get(
            "stopping",
            {}
        )
        if isinstance(historical_result, dict)
        else {}
    )
    historical_escalation = (
        historical_result.get(
            "escalation",
            {}
        )
        if isinstance(historical_result, dict)
        else {}
    )
    historical_policy = (
        historical_result.get(
            "policy",
            {}
        )
        if isinstance(historical_result, dict)
        else {}
    )
    historical_audit = (
        historical_result.get(
            "audit",
            {}
        )
        if isinstance(historical_result, dict)
        else {}
    )
    # --------------------------------------------------------
    # Final values shown by the case page.
    # --------------------------------------------------------
    if has_historical_agent_execution:
        display_probability = safe_float(
            historical_score.get(
                "recovery_probability"
            )
        )
        display_priority_score = safe_float(
            historical_score.get(
                "priority_score"
            )
        )
        display_priority = safe_string(
            historical_score.get(
                "priority"
            )
        )
        display_expected_recovery = (
            safe_float(
                processed.get(
                    "expected_recovery_value",
                    safe_float(
                        row.get(
                            "transaction_amount"
                        )
                    )
                    * display_probability,
                )
            )
        )
        display_strategy = safe_string(
            historical_action.get(
                "strategy"
            )
        )
        display_action = safe_string(
            historical_action.get(
                "recovery_action"
            )
        )
        display_channel = safe_string(
            historical_action.get(
                "channel"
            )
        )
        display_intent = safe_float(
            historical_score.get(
                "customer_intent"
            )
        )
        display_reliability = safe_float(
            historical_score.get(
                "customer_reliability"
            )
        )
        display_contactability = safe_float(
            historical_score.get(
                "contactability"
            )
        )
        display_friction = safe_float(
            historical_score.get(
                "recovery_friction"
            )
        )
        display_attempts = max(
            0,
            safe_int(
                historical_execution.get(
                    "attempt_count",
                    processed.get(
                        "recovery_attempts",
                        row.get(
                            "recovery_attempts",
                            0
                        )
                    )
                )
            )
        )
        execution = historical_execution
        stopping = historical_stopping
        escalation = historical_escalation
        policy = historical_policy
        audit = historical_audit
        assessment_source = (
            "historical_agent_execution"
        )
    else:
        display_probability = (
            safe_float(
                assessment_probability
            )
        )
        display_priority_score = (
            safe_float(
                assessment_priority_score
            )
        )
        display_priority = (
            safe_string(
                assessment_priority
            )
        )
        display_expected_recovery = (
            safe_float(
                assessment_expected_recovery
            )
        )
        display_strategy = (
            safe_string(
                assessment_strategy
            )
        )
        display_action = ""
        display_channel = ""
        display_intent = (
            safe_float(
                assessment_intent
            )
        )
        display_reliability = 0.0
        display_contactability = 0.0
        display_friction = 0.0
        display_attempts = max(
            0,
            safe_int(
                row.get(
                    "recovery_attempts",
                    0
                )
            )
        )
        execution = {}
        stopping = {}
        escalation = {}
        policy = {}
        audit = {}
        assessment_source = (
            "current_model_assessment"
        )
    # --------------------------------------------------------
    # Return a stable case-detail payload.
    # --------------------------------------------------------
    return {
        "success": True,
        "case": {
            "transaction_id":
                txid,
            "customer_id":
                safe_string(
                    row.get(
                        "customer_id"
                    )
                ),
            "transaction_amount":
                round(
                    safe_float(
                        row.get(
                            "transaction_amount"
                        )
                    ),
                    2
                ),
            "payment_method":
                safe_string(
                    row.get(
                        "payment_method"
                    )
                ),
            "failure_reason":
                safe_string(
                    row.get(
                        "failure_reason"
                    )
                ),
            "scenario":
                normalize_scenario(
                    row.get(
                        "scenario",
                        "payment_failure"
                    )
                ),
            "payment_status":
                safe_string(
                    row.get(
                        "payment_status"
                    )
                ),
            "recovery_probability":
                round(
                    display_probability,
                    4
                ),
            "priority_score":
                round(
                    display_priority_score,
                    4
                ),
            "priority":
                display_priority,
            "strategy":
                display_strategy,
            "recovery_action":
                display_action,
            "recommended_channel":
                display_channel,
            "expected_recovery_value":
                round(
                    display_expected_recovery,
                    2
                ),
            "customer_intent":
                round(
                    display_intent,
                    4
                ),
            "customer_reliability":
                round(
                    display_reliability,
                    4
                ),
            "contactability":
                round(
                    display_contactability,
                    4
                ),
            "recovery_friction":
                round(
                    display_friction,
                    4
                ),
            "recovery_attempts":
                display_attempts,
            "max_recovery_attempts":
                MAX_RECOVERY_ATTEMPTS,
            "recovered":
                bool(
                    normalize_bool(
                        row.get(
                            "recovered"
                        )
                    )
                ),
            "money_recovered":
                round(
                    safe_float(
                        row.get(
                            "money_recovered"
                        )
                    ),
                    2
                ),
            "assessment_source":
                assessment_source,
            "historical_agent_execution_available":
                has_historical_agent_execution,
            "live_recovery_state":
                live,
            "latest_processed_event":
                processed,
            "execution":
                execution,
            "stopping":
                stopping,
            "escalation":
                escalation,
            "policy":
                policy,
            "audit":
                audit,
        }
    }
@app.post("/recovery/run/{transaction_id}")
async def run_recovery_for_transaction(transaction_id: str):
    row = _recovery_case_row(transaction_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Active recovery case not found.")

    if normalize_bool(row.get("recovered")):
        return {
            "success": False,
            "status": "already_recovered",
            "transaction_id": transaction_id,
            "message": "This case is already recovered.",
        }

    event = _event_from_recovery_row(row)
    result = await process_recovery_event(event)
    return {
        "success": True,
        "status": "processed",
        "transaction_id": transaction_id,
        "result": result,
    }


@app.post("/recovery/run-batch")
async def run_recovery_batch(request: RecoveryBatchRequest):
    results = []
    processed_count = 0

    for raw_id in request.transaction_ids:
        transaction_id = safe_string(raw_id)
        if not transaction_id:
            continue

        row = _recovery_case_row(transaction_id)
        if row is None:
            results.append({
                "transaction_id": transaction_id,
                "success": False,
                "status": "not_found",
                "message": "Active recovery case not found.",
            })
            continue

        if normalize_bool(row.get("recovered")):
            results.append({
                "transaction_id": transaction_id,
                "success": False,
                "status": "already_recovered",
            })
            continue

        try:
            event = _event_from_recovery_row(row)
            result = await process_recovery_event(event)
            processed_count += 1
            results.append({
                "transaction_id": transaction_id,
                "success": True,
                "status": "processed",
                "result": result,
            })
        except Exception as exc:
            results.append({
                "transaction_id": transaction_id,
                "success": False,
                "status": "error",
                "message": str(exc),
            })

    return {
        "success": True,
        "status": "completed",
        "requested": len(request.transaction_ids),
        "processed": processed_count,
        "results": results,
    }




# ============================================================
# COMPLETE CUSTOMER DETAIL API
# Added by final UI workflow installer.
# ============================================================

@app.get("/customers/{customer_id}")
async def customer_detail_api(customer_id: str):
    customer_id = safe_string(
        customer_id
    )
    if not customer_id:
        raise HTTPException(
            status_code=400,
            detail="customer_id is required."
        )
    # --------------------------------------------------------
    # COMPLETE DATASET
    # --------------------------------------------------------
    raw = load_data()
    df = prepare_base_dataframe(
        raw
    )
    if (
        df.empty
        or "customer_id" not in df.columns
    ):
        raise HTTPException(
            status_code=404,
            detail="Customer not found."
        )
    df["customer_id"] = (
        df["customer_id"]
        .astype(str)
        .str.strip()
    )
    matches = df[
        df["customer_id"] == customer_id
    ].copy()
    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {customer_id} not found."
        )
    transactions = []
    # --------------------------------------------------------
    # PROCESS EVERY CUSTOMER TRANSACTION
    # --------------------------------------------------------
    for _, original_row in matches.iterrows():
        transaction_id = safe_string(
            original_row.get(
                "transaction_id"
            )
        )
        if not transaction_id:
            continue
        # Start from the original dataset row.
        row = original_row.copy()
        # ----------------------------------------------------
        # APPLY PERSISTED AGENT STATE
        # ----------------------------------------------------
        processed = (
            PROCESSED_RECOVERY_EVENTS.get(
                transaction_id,
                {}
            )
        )
        live = (
            LIVE_RECOVERY_STATE.get(
                transaction_id,
                {}
            )
        )
        if (
            isinstance(processed, dict)
            and processed
        ):
            for key, value in processed.items():
                if value is not None:
                    row[key] = value
        if (
            isinstance(live, dict)
            and live
        ):
            for key, value in live.items():
                if value is not None:
                    row[key] = value
        # ----------------------------------------------------
        # CHECK FOR REAL HISTORICAL AGENT EXECUTION
        # ----------------------------------------------------
        has_historical_agent_execution = (
            isinstance(processed, dict)
            and bool(
                processed.get(
                    "_agent_result"
                )
            )
        )
        historical_result = (
            processed.get(
                "_agent_result",
                {}
            )
            if isinstance(processed, dict)
            else {}
        )
        historical_score = (
            historical_result.get(
                "score",
                {}
            )
            if isinstance(
                historical_result,
                dict
            )
            else {}
        )
        historical_action = (
            historical_result.get(
                "action",
                {}
            )
            if isinstance(
                historical_result,
                dict
            )
            else {}
        )
        # ----------------------------------------------------
        # CURRENT MODEL ASSESSMENT
        #
        # Used only when this transaction does not have a
        # persisted Recovery Agent execution.
        # ----------------------------------------------------
        current_probability = 0.0
        current_intent = 0.0
        current_value_score = 0.0
        current_priority_score = 0.0
        current_priority = "LOW"
        current_strategy = "low_cost_recovery"
        current_expected_recovery = 0.0
        try:
            assessment_df = pd.DataFrame(
                [row.to_dict()]
            )
            assessment_df = (
                prepare_base_dataframe(
                    assessment_df
                )
            )
            current_probability = safe_float(
                calculate_recovery_probability(
                    assessment_df
                ).iloc[0]
            )
            current_intent = safe_float(
                calculate_customer_intent(
                    assessment_df
                ).iloc[0]
            )
            current_value_score = safe_float(
                calculate_value_score(
                    assessment_df
                ).iloc[0]
            )
            assessment_df[
                "recovery_probability"
            ] = current_probability
            assessment_df[
                "customer_intent"
            ] = current_intent
            assessment_df[
                "value_score"
            ] = current_value_score
            current_priority_score = safe_float(
                calculate_priority_score(
                    assessment_df
                ).iloc[0]
            )
            current_priority = safe_string(
                assign_priority(
                    pd.Series(
                        [current_priority_score]
                    )
                ).iloc[0],
                "LOW"
            )
            current_strategy = safe_string(
                assign_strategy(
                    pd.Series(
                        [current_priority_score]
                    )
                ).iloc[0],
                "low_cost_recovery"
            )
            current_expected_recovery = (
                safe_float(
                    row.get(
                        "transaction_amount"
                    )
                )
                * current_probability
            )
        except Exception:
            # Keep the transaction visible even if assessment
            # calculation fails for an unusual source row.
            pass
        # ----------------------------------------------------
        # HISTORICAL AGENT RESULT WINS WHEN AVAILABLE
        # ----------------------------------------------------
        if has_historical_agent_execution:
            recovery_probability = safe_float(
                historical_score.get(
                    "recovery_probability",
                    0.0
                )
            )
            priority_score = safe_float(
                historical_score.get(
                    "priority_score",
                    0.0
                )
            )
            priority = safe_string(
                historical_score.get(
                    "priority",
                    ""
                )
            )
            strategy = safe_string(
                historical_action.get(
                    "strategy",
                    ""
                )
            )
            expected_recovery_value = (
                safe_float(
                    processed.get(
                        "expected_recovery_value",
                        safe_float(
                            row.get(
                                "transaction_amount"
                            )
                        )
                        * recovery_probability
                    )
                )
            )
            recovery_action = safe_string(
                historical_action.get(
                    "recovery_action",
                    ""
                )
            )
            recommended_channel = safe_string(
                historical_action.get(
                    "channel",
                    ""
                )
            )
            assessment_source = (
                "historical_agent_execution"
            )
        else:
            recovery_probability = (
                current_probability
            )
            priority_score = (
                current_priority_score
            )
            priority = (
                current_priority
            )
            strategy = (
                current_strategy
            )
            expected_recovery_value = (
                current_expected_recovery
            )
            recovery_action = ""
            recommended_channel = ""
            assessment_source = (
                "current_model_assessment"
            )
        # ----------------------------------------------------
        # TRANSACTION
        # ----------------------------------------------------
        transactions.append(
            {
                "transaction_id":
                    transaction_id,
                "customer_id":
                    safe_string(
                        row.get(
                            "customer_id"
                        )
                    ),
                "transaction_amount":
                    round(
                        safe_float(
                            row.get(
                                "transaction_amount"
                            )
                        ),
                        2
                    ),
                "payment_method":
                    safe_string(
                        row.get(
                            "payment_method"
                        )
                    ),
                "failure_reason":
                    safe_string(
                        row.get(
                            "failure_reason"
                        )
                    ),
                "scenario":
                    safe_string(
                        row.get(
                            "scenario"
                        )
                    ),
                "payment_status":
                    safe_string(
                        row.get(
                            "payment_status"
                        )
                    ),
                "recovered":
                    bool(
                        normalize_bool(
                            row.get(
                                "recovered"
                            )
                        )
                    ),
                "money_recovered":
                    round(
                        safe_float(
                            row.get(
                                "money_recovered"
                            )
                        ),
                        2
                    ),
                "recovery_attempts":
                    max(
                        0,
                        safe_int(
                            live.get(
                                "recovery_attempts",
                                row.get(
                                    "recovery_attempts",
                                    0
                                )
                            )
                        )
                    ),
                "recovery_probability":
                    round(
                        recovery_probability,
                        4
                    ),
                "priority_score":
                    round(
                        priority_score,
                        4
                    ),
                "priority":
                    priority,
                "strategy":
                    strategy,
                "expected_recovery_value":
                    round(
                        expected_recovery_value,
                        2
                    ),
                "assessment_source":
                    assessment_source,
                "historical_agent_execution_available":
                    has_historical_agent_execution,
                "recovery_action":
                    recovery_action,
                "recommended_channel":
                    recommended_channel,
            }
        )
    # --------------------------------------------------------
    # CUSTOMER TOTALS
    # --------------------------------------------------------
    total_value = sum(
        safe_float(
            transaction[
                "transaction_amount"
            ]
        )
        for transaction in transactions
    )
    recovered_cases = sum(
        1
        for transaction in transactions
        if transaction["recovered"]
    )
    money_recovered = sum(
        safe_float(
            transaction[
                "money_recovered"
            ]
        )
        for transaction in transactions
    )
    return {
        "success": True,
        "customer": {
            "customer_id":
                customer_id,
            "transactions":
                transactions,
            "transaction_count":
                len(transactions),
            "total_value":
                round(
                    total_value,
                    2
                ),
            "recovered_cases":
                recovered_cases,
            "unrecovered_cases":
                max(
                    0,
                    len(transactions)
                    - recovered_cases
                ),
            "money_recovered":
                round(
                    money_recovered,
                    2
                ),
        }
    }
