from pathlib import Path
from typing import Any
import os
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.agent.recovery_agent import RecoveryAgent
from src.ml.recovery_scorer import RecoveryScorer


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


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
            in {"true", "1", "yes", "paid", "recovered"}
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

    return (
        f"₹{','.join(groups)},{last_three}.{decimal_part}"
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

    priority.loc[score >= 0.55] = "MEDIUM"
    priority.loc[score >= 0.75] = "HIGH"

    return priority


def assign_strategy(
    score: pd.Series,
) -> pd.Series:

    strategy = pd.Series(
        "low_cost_recovery",
        index=score.index,
    )

    strategy.loc[score >= 0.45] = "standard_recovery"
    strategy.loc[score >= 0.60] = "assisted_recovery"
    strategy.loc[score >= 0.75] = "aggressive_recovery"

    return strategy


# ============================================================
# AT-RISK DATA
# ============================================================

def get_at_risk_data() -> pd.DataFrame:
    """
    Return all revenue-at-risk transactions with scoring.

    Performance behavior:
    - Historical CSV rows are ML-scored once and cached in memory.
    - Repeated dashboard / analytics / recovery-cases requests reuse
      the cached historical scores.
    - Live recovery events always use the score already produced by
      RecoveryAgent, so live-event behavior remains intact.
    - Cache is invalidated automatically when the CSV file changes.
    """

    # --------------------------------------------------------
    # LOAD BASE DATA
    # --------------------------------------------------------

    df = prepare_base_dataframe(load_data())

    # --------------------------------------------------------
    # ADD LIVE RECOVERY EVENTS
    # --------------------------------------------------------

    if PROCESSED_RECOVERY_EVENTS:

        live_df = prepare_base_dataframe(
            pd.DataFrame(
                PROCESSED_RECOVERY_EVENTS.values()
            )
        )

        live_ids = set(
            live_df["transaction_id"].astype(str)
        )

        # Remove the historical copy of any transaction that
        # has subsequently been processed live.
        df = df[
            ~df["transaction_id"]
            .astype(str)
            .isin(live_ids)
        ]

        df = pd.concat(
            [df, live_df],
            ignore_index=True,
        )

    # --------------------------------------------------------
    # NORMALIZE REVENUE-AT-RISK
    # --------------------------------------------------------

    df["revenue_at_risk"] = (
        df["revenue_at_risk"]
        .apply(normalize_bool)
    )

    at_risk = df[
        df["revenue_at_risk"] == 1
    ].copy()

    if at_risk.empty:
        return at_risk

    # --------------------------------------------------------
    # HISTORICAL ML SCORE CACHE
    # --------------------------------------------------------
    #
    # The cache lives on the function itself.
    #
    # Historical rows are identified by transaction_id.
    # This prevents 1,643 model predictions from happening
    # every time the dashboard is opened.
    # --------------------------------------------------------

    if not hasattr(
        get_at_risk_data,
        "_historical_score_cache",
    ):
        get_at_risk_data._historical_score_cache = {}

    score_cache = (
        get_at_risk_data._historical_score_cache
    )

    # --------------------------------------------------------
    # DETECT CSV CHANGES
    # --------------------------------------------------------
    #
    # If the source CSV changes, clear the historical cache.
    # This prevents stale scores after dataset updates.
    # --------------------------------------------------------

    try:

        dataset_path = DATA_FILE

        dataset_mtime = (
            os.path.getmtime(dataset_path)
        )

    except Exception:

        dataset_mtime = None

    cached_mtime = getattr(
        get_at_risk_data,
        "_dataset_mtime",
        None,
    )

    if dataset_mtime != cached_mtime:

        score_cache.clear()

        get_at_risk_data._dataset_mtime = (
            dataset_mtime
        )

    # --------------------------------------------------------
    # ML SCORER
    # --------------------------------------------------------

    scorer = None

    scored_rows = []

    for _, row in at_risk.iterrows():

        transaction_id = safe_string(
            row.get("transaction_id")
        )

        # ----------------------------------------------------
        # LIVE EVENT
        # ----------------------------------------------------

        live_event = (
            PROCESSED_RECOVERY_EVENTS.get(
                transaction_id
            )
        )

        if live_event:

            agent_result = (
                live_event.get(
                    "_agent_result",
                    {},
                )
            )

            live_score = (
                agent_result.get(
                    "score",
                    {},
                )
                if isinstance(
                    agent_result,
                    dict,
                )
                else {}
            )

            if (
                isinstance(
                    live_score,
                    dict,
                )
                and live_score
            ):

                result = live_score

            else:

                # Very unusual fallback:
                # if the live event does not contain its
                # score, calculate it normally.
                if scorer is None:
                    scorer = RecoveryScorer()

                result = scorer.score(
                    row.to_dict()
                )

        # ----------------------------------------------------
        # HISTORICAL ROW
        # ----------------------------------------------------

        else:

            cached_result = score_cache.get(
                transaction_id
            )

            if cached_result is not None:

                result = cached_result

            else:

                if scorer is None:
                    scorer = RecoveryScorer()

                result = scorer.score(
                    row.to_dict()
                )

                score_cache[
                    transaction_id
                ] = result

        scored_rows.append(result)

    # --------------------------------------------------------
    # BUILD SCORE DATAFRAME
    # --------------------------------------------------------

    scored_df = pd.DataFrame(
        scored_rows,
        index=at_risk.index,
    )

    # --------------------------------------------------------
    # SCORE COLUMNS
    # --------------------------------------------------------

    at_risk["recovery_probability"] = (
        pd.to_numeric(
            scored_df[
                "recovery_probability"
            ],
            errors="coerce",
        )
        .clip(0, 1)
    )

    at_risk["expected_recovery_value"] = (
        at_risk["transaction_amount"]
        * at_risk[
            "recovery_probability"
        ]
    )

    at_risk["customer_intent"] = (
        pd.to_numeric(
            scored_df[
                "customer_intent"
            ],
            errors="coerce",
        )
        .clip(0, 1)
    )

    at_risk["customer_reliability"] = (
        pd.to_numeric(
            scored_df[
                "customer_reliability"
            ],
            errors="coerce",
        )
        .clip(0, 1)
    )

    at_risk["contactability"] = (
        pd.to_numeric(
            scored_df[
                "contactability"
            ],
            errors="coerce",
        )
        .clip(0, 1)
    )

    at_risk["recovery_friction"] = (
        pd.to_numeric(
            scored_df[
                "recovery_friction"
            ],
            errors="coerce",
        )
        .clip(0, 1)
    )

    at_risk["priority_score"] = (
        pd.to_numeric(
            scored_df[
                "priority_score"
            ],
            errors="coerce",
        )
        .clip(0, 1)
    )

    at_risk["priority"] = (
        scored_df[
            "priority"
        ]
        .fillna("LOW")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # STRATEGY
    # --------------------------------------------------------

    calculated_strategy = (
        assign_strategy(
            at_risk[
                "priority_score"
            ]
        )
    )

    if "strategy" not in at_risk.columns:

        at_risk["strategy"] = (
            calculated_strategy
        )

    else:

        strategy = (
            at_risk[
                "strategy"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        missing = strategy == ""

        at_risk.loc[
            missing,
            "strategy",
        ] = calculated_strategy[
            missing
        ]

    # --------------------------------------------------------
    # RECOVERY ACTION
    # --------------------------------------------------------

    if "recovery_action" not in at_risk.columns:

        at_risk["recovery_action"] = ""

    else:

        at_risk[
            "recovery_action"
        ] = (
            at_risk[
                "recovery_action"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # --------------------------------------------------------
    # RECOMMENDED CHANNEL
    # --------------------------------------------------------

    if (
        "recommended_channel"
        not in at_risk.columns
    ):

        at_risk[
            "recommended_channel"
        ] = ""

    else:

        at_risk[
            "recommended_channel"
        ] = (
            at_risk[
                "recommended_channel"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # ========================================================
    # DISPLAY / API-SAFE FIELDS
    # ========================================================

    if "recovery_action_display" not in at_risk.columns:
        at_risk["recovery_action_display"] = ""

    at_risk["recovery_action_display"] = (
        at_risk["recovery_action_display"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # Populate display action from recovery_action when needed.
    if "recovery_action" in at_risk.columns:
        missing_display = (
            at_risk["recovery_action_display"] == ""
        )

        at_risk.loc[missing_display, "recovery_action_display"] = (
            at_risk.loc[missing_display, "recovery_action"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # --------------------------------------------------------
    # RECOVERY STATUS
    # --------------------------------------------------------

    at_risk["recovered"] = (
        at_risk[
            "recovered"
        ]
        .apply(normalize_bool)
    )

    at_risk["money_recovered"] = (
        pd.to_numeric(
            at_risk[
                "money_recovered"
            ],
            errors="coerce",
        )
        .fillna(0.0)
    )

        # --------------------------------------------------------
    # FINAL EXPECTED RECOVERY VALUE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # FINAL RECOMMENDED CHANNEL
    # --------------------------------------------------------
    #
    # The source dataset uses:
    #   preferred_channel
    #   channel
    #
    # The AI uses:
    #   recommended_channel
    #
    # Always build the API field here, at the very end,
    # so scoring cannot accidentally remove or overwrite it.
    # --------------------------------------------------------

    if "preferred_channel" in at_risk.columns:

        preferred_channel = (
            at_risk["preferred_channel"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

    else:

        preferred_channel = pd.Series(
            "",
            index=at_risk.index,
            dtype="object",
        )

    if "channel" in at_risk.columns:

        transaction_channel = (
            at_risk["channel"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

    else:

        transaction_channel = pd.Series(
            "",
            index=at_risk.index,
            dtype="object",
        )

    at_risk["recommended_channel"] = (
        preferred_channel.where(
            preferred_channel != "",
            transaction_channel,
        )
    )

    return at_risk


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

def dashboard_summary(
    at_risk: pd.DataFrame,
) -> dict[str, Any]:

    total_cases = len(at_risk)

    recovered_cases = int(
        at_risk["recovered"].sum()
    )

    total_risk = float(
        at_risk["transaction_amount"].sum()
    )

    actual_recovered = float(
        at_risk["money_recovered"].sum()
    )

    expected_recovery = float(
        at_risk["expected_recovery_value"].sum()
    )

    recovery_rate = (
        recovered_cases / total_cases * 100
        if total_cases
        else 0.0
    )

    recovery_customers = int(
        at_risk["customer_id"].nunique()
    )

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
        "unrecovered_cases": (
            total_cases - recovered_cases
        ),
        "total_customers": recovery_customers,
        "total_dataset_customers": (
            total_dataset_customers
        ),
        "recovery_coverage": round(
            recovery_coverage,
            2,
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

    result = agent.process(transaction)

    if not isinstance(result, dict):
        raise ValueError(
            "RecoveryAgent returned an invalid result."
        )

    return result


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
        if isinstance(score, dict)
        else {}
    )

    action = (
        action
        if isinstance(action, dict)
        else {}
    )

    execution = (
        execution
        if isinstance(execution, dict)
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
            transaction.get("transaction_id")
        ),
        "customer_id": safe_string(
            transaction.get("customer_id")
        ),
        "transaction_amount": amount,
        "payment_method": safe_string(
            transaction.get("payment_method")
        ),
        "failure_reason": safe_string(
            transaction.get("failure_reason")
        ),
        "retry_count": safe_int(
            transaction.get("retry_count")
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
        "recovery_probability": recovery_probability,
        "expected_recovery_value": (
            amount * recovery_probability
        ),
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

        role = message.role.lower().strip()

        if role in {"user", "assistant"}:
            lines.append(
                f"{role.upper()}: "
                f"{message.content}"
            )

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

        if (
            message.role.lower().strip()
            == "user"
        ):
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
    q = q.rstrip("?!.'\"")

    previous_user = last_user_question(
        conversation
    )

    previous_user = previous_user.rstrip(
        "?!.'\""
    )

    history = get_last_conversation_text(
        conversation
    )

    # ========================================================
    # GREETING
    # ========================================================

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
            "I analyze failed-payment recovery opportunities "
            "and help you understand where revenue is at risk, "
            "which cases should be prioritized, and why the "
            "recovery agent selected a particular action.\n\n"
            "You can ask:\n"
            "• What does this dashboard help me understand?\n"
            "• Why is revenue at risk?\n"
            "• Why are recovery cases failing?\n"
            "• What should I prioritize first?\n"
            "• Which strategy performs best?\n"
            "• Tell me the reasoning behind the decision."
        )

    # ========================================================
    # KEYWORDS
    # ========================================================

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

    # ========================================================
    # FOLLOW-UP DETECTION
    # ========================================================

    followup_phrases = {
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
        "tell me the reasoning",
        "tell me why",
        "explain the reasoning",
        "explain why",
        "why was this selected",
        "why was this prioritized",
        "why this transaction",
    }

    is_short_followup = (
        bool(conversation)
        and (
            q in followup_phrases
            or q.startswith("explain ")
            or q.startswith("tell me ")
            or q.startswith("why ")
            or q.startswith("how ")
        )
    )

    # ========================================================
    # FOLLOW-UP REASONING
    # ========================================================

    reasoning_requested = (
        "reasoning" in q
        or "why was this selected" in q
        or "why was this prioritized" in q
        or "explain why" in q
        or "tell me why" in q
    )

    if reasoning_requested and conversation:

        # ----------------------------------------------------
        # PRIORITIZATION REASONING
        # ----------------------------------------------------

        if (
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
                    "There are currently no recovery cases "
                    "available to explain."
                )

            row = top.iloc[0]

            return (
                f"Here is why transaction "
                f"{row['transaction_id']} was prioritized:\n\n"

                f"1. Amount at risk: "
                f"{format_inr(row['transaction_amount'])}\n"

                f"2. Recovery probability: "
                f"{row['recovery_probability'] * 100:.2f}%\n"

                f"3. Expected recovery value: "
                f"{format_inr(row['expected_recovery_value'])}\n"

                f"4. Customer intent: "
                f"{row['customer_intent'] * 100:.2f}%\n"

                f"5. Customer success rate: "
                f"{row['customer_success_rate'] * 100:.2f}%\n"

                f"6. Priority score: "
                f"{row['priority_score'] * 100:.2f}%\n\n"

                "The important metric is expected recovery value. "
                "It combines the amount that could be recovered "
                "with the probability of successfully recovering it.\n\n"

                f"For this case, "
                f"{format_inr(row['transaction_amount'])} is at risk "
                f"and the estimated recovery probability is "
                f"{row['recovery_probability'] * 100:.2f}%. "
                f"That produces an expected recovery of "
                f"{format_inr(row['expected_recovery_value'])}.\n\n"

                "Because the case also has strong customer intent "
                "and customer payment history, the system considers "
                "it a strong recovery opportunity.\n\n"

                f"The recommended strategy is "
                f"'{row['strategy']}' using "
                f"'{row['recommended_channel']}' as the channel."
            )

        # ----------------------------------------------------
        # FAILURE REASONING
        # ----------------------------------------------------

        if (
            "failure" in previous_user
            or "failed" in previous_user
            or "transaction fail" in previous_user
            or "payment fail" in previous_user
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
                return (
                    "There isn't enough failure-reason data "
                    "to explain the recovery failures."
                )

            failure_stats["recovery_rate"] = (
                failure_stats["recovered"]
                / failure_stats["cases"]
                * 100
            )

            worst_name = str(
                failure_stats["recovery_rate"].idxmin()
            )

            worst = failure_stats.loc[
                worst_name
            ]

            return (
                "Some recovery cases fail because the underlying "
                "payment problem is difficult to recover from.\n\n"

                f"The weakest failure category is "
                f"'{worst_name}'.\n\n"

                f"• Cases: {int(worst['cases']):,}\n"
                f"• Amount involved: "
                f"{format_inr(worst['amount'])}\n"
                f"• Recovery rate: "
                f"{worst['recovery_rate']:.2f}%\n\n"

                "A low recovery rate means that many cases in this "
                "failure category remain unrecovered even after "
                "recovery attempts.\n\n"

                "To improve these cases, the next things to examine "
                "are customer intent, contactability, retry count, "
                "payment-method success rate, and the recovery "
                "channel used."
            )

        # ----------------------------------------------------
        # STRATEGY REASONING
        # ----------------------------------------------------

        if "strategy" in previous_user:

            strategy_stats = (
                at_risk
                .groupby("strategy")
                .agg(
                    cases=("transaction_id", "count"),
                    recovered=("recovered", "sum"),
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

            strategy_stats["recovery_rate"] = (
                strategy_stats["recovered"]
                / strategy_stats["cases"]
                * 100
            )

            best_name = str(
                strategy_stats["recovery_rate"].idxmax()
            )

            best = strategy_stats.loc[
                best_name
            ]

            return (
                f"The strongest-performing strategy is "
                f"'{best_name}'.\n\n"

                f"• Recovery rate: "
                f"{best['recovery_rate']:.2f}%\n"
                f"• Cases: {int(best['cases']):,}\n"
                f"• Money recovered: "
                f"{format_inr(best['money_recovered'])}\n\n"

                "This strategy ranks first because it has the "
                "highest observed recovery rate in the current "
                "dataset."
            )

    # ========================================================
    # UNRELATED QUESTION
    # ========================================================

    if has_unrelated_topic and not has_recovery_topic:

        return (
            "That question isn't related to Revenue Recovery AI.\n\n"
            "This AI is designed to analyze failed payments, "
            "revenue risk, recovery opportunities, customer behavior, "
            "prioritization, recovery strategies, agent decisions, "
            "and recovery performance."
        )

    # ========================================================
    # DASHBOARD EXPLANATION
    # ========================================================

    if (
        "what does this help" in q
        or "what is this for" in q
        or "what does this do" in q
        or "what can this do" in q
        or "what does recovery ai do" in q
        or "what does this help me know" in q
        or "what can i know" in q
    ):

        return (
            "Revenue Recovery AI helps you understand where failed "
            "payments could turn into lost revenue and what you "
            "should do about them.\n\n"

            "In simple terms, it answers four important questions:\n\n"

            "1. WHERE is money at risk?\n"
            f"   There are {summary['at_risk_cases']:,} recovery cases "
            f"with {format_inr(summary['total_transaction_value'])} "
            "in transaction value at risk.\n\n"

            "2. HOW MUCH can potentially be recovered?\n"
            f"   The estimated recovery opportunity is "
            f"{format_inr(summary['expected_recovery_value'])}.\n\n"

            "3. WHICH cases should we handle first?\n"
            "   The system ranks cases using recovery probability, "
            "transaction value, customer intent, and customer "
            "success history.\n\n"

            "4. WHY did the agent choose a particular action?\n"
            "   The recovery score and recommended strategy explain "
            "which cases deserve more attention and which recovery "
            "channel should be used.\n\n"

            "So the main purpose is to turn failed payments into "
            "prioritized recovery opportunities instead of treating "
            "every failed transaction the same way."
        )

    # ========================================================
    # WHY RECOVERY CASES FAIL
    # ========================================================

    if (
        "why are some recovery cases failing" in q
        or "why are recovery cases failing" in q
        or "why do recovery cases fail" in q
        or "why are some cases failing" in q
        or "why do some cases fail" in q
        or "recovery cases fail" in q
        or "recovery case fail" in q
    ):

        failure_stats = (
            at_risk
            .groupby("failure_reason")
            .agg(
                cases=("transaction_id", "count"),
                recovered=("recovered", "sum"),
                amount=("transaction_amount", "sum"),
            )
            .sort_values(
                "cases",
                ascending=False,
            )
        )

        if failure_stats.empty:
            return (
                "There isn't enough failure-reason data "
                "to explain why recovery cases are failing."
            )

        failure_stats["unrecovered"] = (
            failure_stats["cases"]
            - failure_stats["recovered"]
        )

        failure_stats["recovery_rate"] = (
            failure_stats["recovered"]
            / failure_stats["cases"]
            * 100
        )

        top_failures = failure_stats.head(5)

        lines = []

        for failure_name, row in top_failures.iterrows():

            lines.append(
                f"• {failure_name}: "
                f"{int(row['cases']):,} cases, "
                f"{int(row['unrecovered']):,} unrecovered, "
                f"{row['recovery_rate']:.2f}% recovery rate"
            )

        worst_name = str(
            failure_stats["recovery_rate"].idxmin()
        )

        worst = failure_stats.loc[
            worst_name
        ]

        return (
            "Some recovery cases remain unsuccessful because "
            "different payment failures have different levels "
            "of recovery difficulty.\n\n"

            "The most common failure categories are:\n\n"
            + "\n".join(lines)
            + "\n\n"

            f"The weakest recovery category is "
            f"'{worst_name}', with a recovery rate of "
            f"{worst['recovery_rate']:.2f}%.\n\n"

            "This means the recovery problem is not only about "
            "the amount of money involved. The type of payment "
            "failure, customer behavior, previous payment success, "
            "retry history, and available communication channels "
            "also affect whether a case can be recovered.\n\n"

            "In practice, these cases should be investigated by "
            "failure reason and then matched with the most suitable "
            "recovery strategy and communication channel."
        )

    # ========================================================
    # REVENUE AT RISK
    # ========================================================

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

            top_failure = failure_stats.iloc[0]
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

            f"{summary['recovered_cases']:,} cases have been recovered, "
            f"while {summary['unrecovered_cases']:,} remain unrecovered.\n\n"

            f"{explanation}\n\n"

            "The most valuable opportunities are cases where the "
            "potential recovery amount is high and the probability "
            "of successful recovery is also strong."
        )

    # ========================================================
    # PRIORITIZATION
    # ========================================================

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
                "There are currently no recovery cases available."
            )

        row = top.iloc[0]

        return (
            "Start with the case that has the highest expected "
            "recovery value.\n\n"

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

            "The reason this case comes first is that it combines "
            "a meaningful amount at risk with a strong probability "
            "of successful recovery.\n\n"

            "Ask 'tell me the reasoning' if you want the detailed "
            "explanation."
        )

    # ========================================================
    # HIGH PRIORITY
    # ========================================================

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
            return (
                "There are currently no HIGH-priority "
                "recovery cases."
            )

        top = high.iloc[0]

        total_high_value = float(
            high["transaction_amount"].sum()
        )

        expected_high_value = float(
            high["expected_recovery_value"].sum()
        )

        return (
            f"There are "
            f"{int((at_risk['priority'] == 'HIGH').sum()):,} "
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
            f"{format_inr(expected_high_value)} is expected "
            "to be recovered."
        )

    # ========================================================
    # STRATEGY
    # ========================================================

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
                money_recovered=(
                    "money_recovered",
                    "sum",
                ),
                amount_at_risk=(
                    "transaction_amount",
                    "sum",
                ),
            )
        )

        if strategy_stats.empty:
            return (
                "There isn't enough strategy data "
                "to determine which strategy performs best."
            )

        strategy_stats["recovery_rate"] = (
            strategy_stats["recovered"]
            / strategy_stats["cases"]
            * 100
        )

        strategy_stats["unrecovered"] = (
            strategy_stats["cases"]
            - strategy_stats["recovered"]
        )

        strategy_stats = strategy_stats.sort_values(
            [
                "recovery_rate",
                "money_recovered",
            ],
            ascending=False,
        )

        best_name = str(
            strategy_stats.index[0]
        )

        best = strategy_stats.iloc[0]

        return (
            f"The best-performing recovery strategy is "
            f"'{best_name}'.\n\n"

            f"Why it performs best:\n"
            f"• Recovery rate: "
            f"{best['recovery_rate']:.2f}%\n"
            f"• Cases handled: "
            f"{int(best['cases']):,}\n"
            f"• Cases recovered: "
            f"{int(best['recovered']):,}\n"
            f"• Cases not recovered: "
            f"{int(best['unrecovered']):,}\n"
            f"• Money recovered: "
            f"{format_inr(best['money_recovered'])}\n"
            f"• Transaction value at risk: "
            f"{format_inr(best['amount_at_risk'])}\n\n"

            f"This means {best_name} successfully recovered "
            f"{best['recovery_rate']:.2f}% of the cases assigned "
            "to it in the current dataset.\n\n"

            "From a business perspective, this strategy is currently "
            "the strongest option when the goal is to maximize the "
            "percentage of recovery cases successfully recovered.\n\n"

            "Note: a high recovery rate does not automatically mean "
            "the strategy recovered the most money. For a complete "
            "comparison, you should also consider total money "
            "recovered and the value of transactions assigned to "
            "each strategy."
        )

    # ========================================================
    # TRANSACTION / PAYMENT FAILURE
    # ========================================================

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

        top_failures = failure_stats.head(5)

        lines = []

        for failure_name, row in top_failures.iterrows():

            lines.append(
                f"• {failure_name}: "
                f"{int(row['cases']):,} cases, "
                f"{format_inr(row['amount'])} at risk"
            )

        return (
            "Transactions are failing for several reasons.\n\n"
            "The most common failure categories are:\n\n"
            + "\n".join(lines)
            + "\n\n"
            "Different failure types can require different "
            "recovery actions, so they should be analyzed separately."
        )

    # ========================================================
    # RECOVERY PERFORMANCE
    # ========================================================

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

            f"{summary['unrecovered_cases']:,} cases still "
            "require recovery action.\n\n"

            f"Expected recovery is "
            f"{format_inr(summary['expected_recovery_value'])} "
            f"against "
            f"{format_inr(summary['total_transaction_value'])} "
            "at risk."
        )

    # ========================================================
    # GENERIC RECOVERY QUESTION
    # ========================================================

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

            "You can ask me:\n"
            "• Why is revenue at risk?\n"
            "• Why are recovery cases failing?\n"
            "• What should I prioritize first?\n"
            "• Which strategy performs best?\n"
            "• Tell me the reasoning."
        )

    # ========================================================
    # DEFAULT
    # ========================================================

    return (
        "I can help you analyze Revenue Recovery AI.\n\n"
        "Try asking:\n"
        "• What does this help me know?\n"
        "• Why is revenue at risk?\n"
        "• Why are recovery cases failing?\n"
        "• What should I prioritize first?\n"
        "• Which strategy performs best?\n"
        "• Tell me the reasoning."
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
        "dataset_exists": DATA_FILE.exists(),
        "dataset": str(DATA_FILE),
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

    transaction["recovery_attempts"] = (
        transaction["retry_count"]
    )

    transaction["revenue_at_risk"] = 1

    try:

        result = run_recovery_agent(
            transaction
        )

        transaction_id = safe_string(
            transaction.get("transaction_id")
        )

        if not transaction_id:
            raise ValueError(
                "transaction_id cannot be empty."
            )

        live_row = processed_event_to_row(
            transaction,
            result,
        )

        live_row["_agent_result"] = result

        PROCESSED_RECOVERY_EVENTS[
            transaction_id
        ] = live_row

        return {
            "success": True,
            "event": transaction,
            "agent_result": result,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Recovery event processing failed: "
                f"{exc}"
            ),
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
        .reindex(
            ["HIGH", "MEDIUM", "LOW"],
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
        at_risk["strategy"]
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
                    priority_counts[priority]
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
                    strategy_counts[strategy]
                ),
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
        (
            at_risk["priority"] == "HIGH"
        ).sum()
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
        .reindex(
            ["HIGH", "MEDIUM", "LOW"],
            fill_value=0,
        )
    )

    return {
        "priority_distribution": [
            {
                "priority": priority,
                "cases": int(
                    counts[priority]
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
        at_risk["strategy"]
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
                    counts[strategy]
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
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
):

    at_risk = get_at_risk_data()

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
                    row["transaction_id"]
                ),
                "customer_id": safe_string(
                    row["customer_id"]
                ),
                "transaction_amount": round(
                    safe_float(
                        row["transaction_amount"]
                    ),
                    2,
                ),
                "recovery_probability": round(
                    safe_float(
                        row["recovery_probability"]
                    ),
                    4,
                ),
                "priority_score": round(
                    safe_float(
                        row["priority_score"]
                    ),
                    4,
                ),
                "priority": safe_string(
                    row["priority"]
                ),
                "strategy": safe_string(
                    row["strategy"]
                ),
                "recommended_channel": safe_string(
                    row["recommended_channel"]
                ),
                "expected_recovery_value": round(
                    safe_float(
                        row["expected_recovery_value"]
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

    at_risk = get_at_risk_data()

    # Filter by priority
    if priority:

        at_risk = at_risk[
            at_risk["priority"]
            .astype(str)
            .str.upper()
            == priority.upper()
        ]

    # Filter by strategy
    if strategy:

        at_risk = at_risk[
            at_risk["strategy"]
            .astype(str)
            .str.lower()
            == strategy.lower()
        ]

    # Search transaction/customer ID
    if search:

        term = search.lower().strip()

        transaction_match = (
            at_risk["transaction_id"]
            .astype(str)
            .str.lower()
            .str.contains(
                term,
                regex=False,
            )
        )

        customer_match = (
            at_risk["customer_id"]
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

    total = len(at_risk)

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
        offset:offset + limit
    ]

    results = []

    for _, row in page.iterrows():

        results.append(
            {
                "transaction_id": safe_string(
                    row["transaction_id"]
                ),
                "customer_id": safe_string(
                    row["customer_id"]
                ),
                "transaction_amount": round(
                    safe_float(
                        row["transaction_amount"]
                    ),
                    2,
                ),
                "priority": safe_string(
                    row["priority"]
                ),
                "priority_score": round(
                    safe_float(
                        row["priority_score"]
                    ),
                    4,
                ),
                "recovery_probability": round(
                    safe_float(
                        row["recovery_probability"]
                    ),
                    4,
                ),
                "strategy": safe_string(
                    row["strategy"]
                ),
                "recovery_action": safe_string(
                    row["recovery_action_display"]
                ),
                "recommended_channel": safe_string(
                    row["recommended_channel"]
                ),
                "recovered": bool(
                    normalize_bool(
                        row["recovered"]
                    )
                ),
                "money_recovered": round(
                    safe_float(
                        row["money_recovered"]
                    ),
                    2,
                ),
                "expected_recovery_value": round(
                    safe_float(
                        row["expected_recovery_value"]
                    ),
                    2,
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
        .groupby(
            "customer_id",
            as_index=False,
        )
        .agg(
            cases=("transaction_id", "count"),
            amount_at_risk=(
                "transaction_amount",
                "sum",
            ),
            recovered_cases=(
                "recovered",
                "sum",
            ),
            money_recovered=(
                "money_recovered",
                "sum",
            ),
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
        [
            "money_recovered",
            "amount_at_risk",
        ],
        ascending=False,
    )

    return {
        "total_customers": int(
            len(grouped)
        ),
        "customers_with_cases": int(
            len(grouped)
        ),
        "recovered_customers": int(
            (
                grouped["recovered_cases"] > 0
            ).sum()
        ),
        "total_cases": int(
            len(at_risk)
        ),
        "money_recovered": round(
            safe_float(
                at_risk["money_recovered"].sum()
            ),
            2,
        ),
        "customers": [
            {
                "customer_id": safe_string(
                    row["customer_id"]
                ),
                "cases": safe_int(
                    row["cases"]
                ),
                "amount_at_risk": round(
                    safe_float(
                        row["amount_at_risk"]
                    ),
                    2,
                ),
                "recovered_cases": safe_int(
                    row["recovered_cases"]
                ),
                "recovery_rate": round(
                    safe_float(
                        row["recovery_rate"]
                    ),
                    2,
                ),
                "money_recovered": round(
                    safe_float(
                        row["money_recovered"]
                    ),
                    2,
                ),
                "average_recovery_probability": round(
                    safe_float(
                        row[
                            "average_recovery_probability"
                        ]
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

        grouped["recovery_rate"] = (
            grouped["recovered"]
            / grouped["cases"]
            * 100
        )

        return [
            {
                column: safe_string(
                    row[column]
                ),
                "cases": safe_int(
                    row["cases"]
                ),
                "recovered": safe_int(
                    row["recovered"]
                ),
                "recovery_rate": round(
                    safe_float(
                        row["recovery_rate"]
                    ),
                    2,
                ),
                "amount_at_risk": round(
                    safe_float(
                        row["amount_at_risk"]
                    ),
                    2,
                ),
                "money_recovered": round(
                    safe_float(
                        row["money_recovered"]
                    ),
                    2,
                ),
            }
            for _, row in grouped.iterrows()
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
