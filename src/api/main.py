from fastapi import FastAPI, HTTPException
import psycopg2
import os


app = FastAPI(
    title="Revenue Recovery Agent API",
    description="API for revenue recovery decisions and business metrics",
    version="1.0.0"
)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "revenue_recovery"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health_check():
    try:
        conn = get_connection()
        conn.close()

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


# --------------------------------------------------
# BASIC API INFO
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "name": "Revenue Recovery Agent API",
        "version": "1.0.0",
        "status": "running"
    }


# --------------------------------------------------
# RECOVERY METRICS
# --------------------------------------------------

@app.get("/metrics")
def get_metrics():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) AS cases,
            COALESCE(SUM(t.transaction_amount), 0),
            COALESCE(SUM(rd.expected_recovery_value), 0)
        FROM transactions t
        JOIN recovery_cases rc
            ON t.transaction_id = rc.transaction_id
        JOIN recovery_decisions rd
            ON rc.recovery_case_id = rd.recovery_case_id
    """)

    cases, total_at_risk, expected_recovery = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "total_cases": cases,
        "total_transaction_value": float(total_at_risk),
        "expected_recovery_value": float(expected_recovery)
    }


# --------------------------------------------------
# PRIORITY DISTRIBUTION
# --------------------------------------------------

@app.get("/metrics/priority")
def priority_metrics():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT priority, COUNT(*)
        FROM recovery_decisions
        GROUP BY priority
        ORDER BY
            CASE priority
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'LOW' THEN 3
            END
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "priority_distribution": [
            {
                "priority": row[0],
                "cases": row[1]
            }
            for row in rows
        ]
    }


# --------------------------------------------------
# GET RECOVERY DECISIONS
# --------------------------------------------------

@app.get("/decisions")
def get_decisions(limit: int = 20):

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100"
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            t.transaction_id,
            c.customer_id,
            t.transaction_amount,
            rd.recovery_probability,
            rd.priority_score,
            rd.priority,
            rd.strategy,
            rd.recovery_action,
            rd.recommended_channel,
            rd.expected_recovery_value,
            rd.reason
        FROM transactions t
        JOIN customers c
            ON t.customer_id = c.customer_id
        JOIN recovery_cases rc
            ON t.transaction_id = rc.transaction_id
        JOIN recovery_decisions rd
            ON rc.recovery_case_id = rd.recovery_case_id
        ORDER BY rd.priority_score DESC
        LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    columns = [
        "transaction_id",
        "customer_id",
        "transaction_amount",
        "recovery_probability",
        "priority_score",
        "priority",
        "strategy",
        "recovery_action",
        "recommended_channel",
        "expected_recovery_value",
        "reason"
    ]

    return [
        dict(zip(columns, row))
        for row in rows
    ]


# --------------------------------------------------
# GET SINGLE TRANSACTION DECISION
# --------------------------------------------------

@app.get("/decisions/{transaction_id}")
def get_decision(transaction_id: str):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            t.transaction_id,
            c.customer_id,
            t.transaction_amount,
            rd.recovery_probability,
            rd.priority_score,
            rd.priority,
            rd.strategy,
            rd.recovery_action,
            rd.recommended_channel,
            rd.expected_recovery_value,
            rd.reason
        FROM transactions t
        JOIN customers c
            ON t.customer_id = c.customer_id
        JOIN recovery_cases rc
            ON t.transaction_id = rc.transaction_id
        JOIN recovery_decisions rd
            ON rc.recovery_case_id = rd.recovery_case_id
        WHERE t.transaction_id = %s
    """, (transaction_id,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found"
        )

    columns = [
        "transaction_id",
        "customer_id",
        "transaction_amount",
        "recovery_probability",
        "priority_score",
        "priority",
        "strategy",
        "recovery_action",
        "recommended_channel",
        "expected_recovery_value",
        "reason"
    ]

    return dict(zip(columns, row))


# --------------------------------------------------
# TOP RECOVERY OPPORTUNITIES
# --------------------------------------------------

@app.get("/top-opportunities")
def top_opportunities(limit: int = 10):

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100"
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            t.transaction_id,
            t.transaction_amount,
            rd.recovery_probability,
            rd.priority,
            rd.strategy,
            rd.recommended_channel,
            rd.expected_recovery_value
        FROM transactions t
        JOIN recovery_cases rc
            ON t.transaction_id = rc.transaction_id
        JOIN recovery_decisions rd
            ON rc.recovery_case_id = rd.recovery_case_id
        ORDER BY rd.expected_recovery_value DESC
        LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    columns = [
        "transaction_id",
        "transaction_amount",
        "recovery_probability",
        "priority",
        "strategy",
        "recommended_channel",
        "expected_recovery_value"
    ]

    return [
        dict(zip(columns, row))
        for row in rows
    ]