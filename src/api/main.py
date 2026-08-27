from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

FRONTEND_DIR = BASE_DIR / "frontend"
CSS_DIR = FRONTEND_DIR / "css"
JS_DIR = FRONTEND_DIR / "js"
DATA_FILE = BASE_DIR / "data" / "raw" / "revenue_recovery.csv"


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(title="Revenue Recovery AI")


# =========================================================
# STATIC FILES
# =========================================================

app.mount("/css", StaticFiles(directory=str(CSS_DIR)), name="css")
app.mount("/js", StaticFiles(directory=str(JS_DIR)), name="js")


# =========================================================
# DATA + CANONICAL SCORING PIPELINE
# =========================================================

def load_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")
    return pd.read_csv(DATA_FILE)


def get_at_risk_data() -> pd.DataFrame:
    """Return every revenue-at-risk case with all derived decision fields."""
    df = load_data()
    at_risk = df[df["revenue_at_risk"] == 1].copy()

    # Canonical recovery probability
    at_risk["recovery_probability"] = (
        0.25
        + 0.30 * at_risk["customer_success_rate"]
        + 0.20 * at_risk["product_interest_score"]
        + 0.15 * at_risk["payment_method_success_rate"]
        + 0.10 * at_risk["checkout_progress"]
    ).clip(0, 1)

    # Expected recovery
    at_risk["expected_recovery_value"] = (
        at_risk["transaction_amount"]
        * at_risk["recovery_probability"]
    )

    # Customer intent
    at_risk["customer_intent"] = (
        0.60 * at_risk["product_interest_score"]
        + 0.40 * at_risk["checkout_progress"]
    ).clip(0, 1)

    # Value score
    at_risk["value_score"] = (
        at_risk["transaction_amount"] / 50000
    ).clip(0, 1)

    # Canonical priority score
    at_risk["priority_score"] = (
        0.50 * at_risk["recovery_probability"]
        + 0.20 * at_risk["value_score"]
        + 0.20 * at_risk["customer_intent"]
        + 0.10 * at_risk["customer_success_rate"]
    ).clip(0, 1)

    # Canonical priority
    at_risk["priority"] = "LOW"
    at_risk.loc[at_risk["priority_score"] >= 0.55, "priority"] = "MEDIUM"
    at_risk.loc[at_risk["priority_score"] >= 0.75, "priority"] = "HIGH"

    # Canonical recovery strategy
    at_risk["strategy"] = "low_cost_recovery"
    at_risk.loc[at_risk["priority_score"] >= 0.45, "strategy"] = "standard_recovery"
    at_risk.loc[at_risk["priority_score"] >= 0.60, "strategy"] = "assisted_recovery"
    at_risk.loc[at_risk["priority_score"] >= 0.75, "strategy"] = "aggressive_recovery"

    # Recommended communication channel
    at_risk["recommended_channel"] = at_risk["preferred_channel"]

    # Display action
    if "recovery_action" in at_risk.columns:
        at_risk["recovery_action_display"] = at_risk["recovery_action"].fillna(
            at_risk["preferred_channel"]
        )
    else:
        at_risk["recovery_action_display"] = at_risk["preferred_channel"]

    return at_risk


def dashboard_summary(at_risk: pd.DataFrame) -> dict:
    """Single source of truth for global dashboard numbers."""

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
        else 0
    )

    # Total customers in the original/raw dataset
    raw_data = load_data()

    total_dataset_customers = int(
        raw_data["customer_id"].nunique()
    )

    # Customers that actually entered the recovery system
    recovery_customers = int(
        at_risk["customer_id"].nunique()
    )

    # Percentage of all customers covered by recovery
    recovery_coverage = (
        recovery_customers / total_dataset_customers * 100
        if total_dataset_customers
        else 0
    )

    return {
        "total_transaction_value": round(
            total_risk, 2
        ),

        "expected_recovery_value": round(
            expected_recovery, 2
        ),

        "actual_recovered_value": round(
            actual_recovered, 2
        ),

        "recovery_rate": round(
            recovery_rate, 2
        ),

        "at_risk_cases": total_cases,

        "recovered_cases": recovered_cases,

        "unrecovered_cases": (
            total_cases - recovered_cases
        ),

        # Customers participating in recovery
        "total_customers": recovery_customers,

        # All customers from raw dataset
        "total_dataset_customers": total_dataset_customers,

        # % of all customers that entered recovery
        "recovery_coverage": round(
            recovery_coverage, 2
        ),
    }

# =========================================================
# PAGES
# =========================================================

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


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "dataset_exists": DATA_FILE.exists(),
        "dataset": str(DATA_FILE),
    }


# =========================================================
# DASHBOARD SUMMARY
# =========================================================

@app.get("/dashboard-summary")
async def dashboard_summary_api():
    at_risk = get_at_risk_data()
    summary = dashboard_summary(at_risk)

    priority_counts = (
        at_risk["priority"]
        .value_counts()
        .reindex(["HIGH", "MEDIUM", "LOW"], fill_value=0)
    )

    strategy_counts = (
        at_risk["strategy"]
        .value_counts()
        .reindex(
            [
                "aggressive_recovery",
                "assisted_recovery",
                "standard_recovery",
                "low_cost_recovery",
            ],
            fill_value=0,
        )
    )

    return {
        **summary,
        "priority_distribution": [
            {"priority": name, "cases": int(priority_counts[name])}
            for name in ["HIGH", "MEDIUM", "LOW"]
        ],
        "strategy_distribution": [
            {"strategy": name, "cases": int(strategy_counts[name])}
            for name in strategy_counts.index
        ],
    }


# =========================================================
# BACKWARD-COMPATIBLE METRICS
# =========================================================

@app.get("/metrics")
async def metrics():
    at_risk = get_at_risk_data()
    summary = dashboard_summary(at_risk)

    high_priority = int((at_risk["priority"] == "HIGH").sum())

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
            {"priority": "HIGH", "cases": int(counts["HIGH"])},
            {"priority": "MEDIUM", "cases": int(counts["MEDIUM"])},
            {"priority": "LOW", "cases": int(counts["LOW"])},
        ]
    }


@app.get("/metrics/strategy")
async def strategy_metrics():
    at_risk = get_at_risk_data()

    counts = (
        at_risk["strategy"]
        .value_counts()
        .reindex(
            [
                "aggressive_recovery",
                "assisted_recovery",
                "standard_recovery",
                "low_cost_recovery",
            ],
            fill_value=0,
        )
    )

    return {
        "strategy_distribution": [
            {
                "strategy": "aggressive_recovery",
                "cases": int(counts["aggressive_recovery"]),
            },
            {
                "strategy": "assisted_recovery",
                "cases": int(counts["assisted_recovery"]),
            },
            {
                "strategy": "standard_recovery",
                "cases": int(counts["standard_recovery"]),
            },
            {
                "strategy": "low_cost_recovery",
                "cases": int(counts["low_cost_recovery"]),
            },
        ]
    }


# =========================================================
# TOP OPPORTUNITIES
# =========================================================

@app.get("/top-opportunities")
async def top_opportunities(
    limit: int = Query(10, ge=1, le=50)
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

    return [
        {
            "transaction_id": str(row["transaction_id"]),
            "customer_id": str(row["customer_id"]),
            "transaction_amount": round(float(row["transaction_amount"]), 2),
            "recovery_probability": round(float(row["recovery_probability"]), 4),
            "priority_score": round(float(row["priority_score"]), 4),
            "priority": str(row["priority"]),
            "strategy": str(row["strategy"]),
            "recommended_channel": str(row["recommended_channel"]),
            "expected_recovery_value": round(
                float(row["expected_recovery_value"]), 2
            ),
        }
        for _, row in top.iterrows()
    ]


# =========================================================
# RECOVERY CASES
# =========================================================

@app.get("/recovery-cases")
async def recovery_cases_api(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    priority: str | None = None,
    strategy: str | None = None,
    search: str | None = None,
):
    at_risk = get_at_risk_data()

    if priority:
        at_risk = at_risk[
            at_risk["priority"].str.upper() == priority.upper()
        ]

    if strategy:
        at_risk = at_risk[
            at_risk["strategy"].str.lower() == strategy.lower()
        ]

    if search:
        term = search.lower().strip()
        at_risk = at_risk[
            at_risk["transaction_id"].astype(str).str.lower().str.contains(term)
            | at_risk["customer_id"].astype(str).str.lower().str.contains(term)
        ]

    total = len(at_risk)

    at_risk = at_risk.sort_values(
        ["priority_score", "expected_recovery_value"],
        ascending=False,
    )

    page = at_risk.iloc[offset: offset + limit]

    results = [
        {
            "transaction_id": str(row["transaction_id"]),
            "customer_id": str(row["customer_id"]),
            "transaction_amount": round(float(row["transaction_amount"]), 2),
            "priority": str(row["priority"]),
            "priority_score": round(float(row["priority_score"]), 4),
            "recovery_probability": round(float(row["recovery_probability"]), 4),
            "strategy": str(row["strategy"]),
            "recovery_action": str(row["recovery_action_display"]),
            "recommended_channel": str(row["recommended_channel"]),
            "recovered": bool(row["recovered"]),
            "money_recovered": round(float(row["money_recovered"]), 2),
            "expected_recovery_value": round(
                float(row["expected_recovery_value"]), 2
            ),
        }
        for _, row in page.iterrows()
    ]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "returned": len(results),
        "cases": results,
    }


# =========================================================
# CUSTOMER INTELLIGENCE
# =========================================================

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
            average_recovery_probability=("recovery_probability", "mean"),
        )
    )

    grouped["recovery_rate"] = (
        grouped["recovered_cases"] / grouped["cases"] * 100
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
            float(at_risk["money_recovered"].sum()), 2
        ),
        "customers": [
            {
                "customer_id": str(row["customer_id"]),
                "cases": int(row["cases"]),
                "amount_at_risk": round(float(row["amount_at_risk"]), 2),
                "recovered_cases": int(row["recovered_cases"]),
                "recovery_rate": round(float(row["recovery_rate"]), 2),
                "money_recovered": round(float(row["money_recovered"]), 2),
                "average_recovery_probability": round(
                    float(row["average_recovery_probability"]), 4
                ),
            }
            for _, row in grouped.iterrows()
        ],
    }


# =========================================================
# ANALYTICS
# =========================================================

@app.get("/analytics")
async def analytics_api():
    at_risk = get_at_risk_data()

    def group_recovery(column: str) -> list[dict]:
        grouped = (
            at_risk.groupby(column)
            .agg(
                cases=("transaction_id", "count"),
                recovered=("recovered", "sum"),
                money_recovered=("money_recovered", "sum"),
                amount_at_risk=("transaction_amount", "sum"),
            )
            .reset_index()
        )

        grouped["recovery_rate"] = (
            grouped["recovered"] / grouped["cases"] * 100
        )

        return [
            {
                column: str(row[column]),
                "cases": int(row["cases"]),
                "recovered": int(row["recovered"]),
                "recovery_rate": round(float(row["recovery_rate"]), 2),
                "amount_at_risk": round(float(row["amount_at_risk"]), 2),
                "money_recovered": round(float(row["money_recovered"]), 2),
            }
            for _, row in grouped.iterrows()
        ]

    summary = dashboard_summary(at_risk)

    return {
        "summary": summary,
        "scenario": group_recovery("scenario"),
        "payment_method": group_recovery("payment_method"),
        "channel": group_recovery("channel"),
        "failure_reason": group_recovery("failure_reason"),
        "priority": group_recovery("priority"),
        "strategy": group_recovery("strategy"),
    }
