CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_transaction_count INTEGER NOT NULL,
    customer_success_rate DECIMAL(5,4) NOT NULL,
    preferred_channel VARCHAR(20),
    customer_email_available BOOLEAN NOT NULL,
    customer_phone_available BOOLEAN NOT NULL
);

CREATE TABLE transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    transaction_amount DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(30),
    payment_method_success_rate DECIMAL(5,4),
    channel VARCHAR(30),
    product_interest_score DECIMAL(5,4),
    checkout_progress DECIMAL(5,4),
    scenario VARCHAR(50),
    payment_status VARCHAR(30),
    failure_reason VARCHAR(50),
    revenue_at_risk BOOLEAN NOT NULL,

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

CREATE TABLE recovery_cases (
    recovery_case_id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL UNIQUE,
    recovery_attempts INTEGER DEFAULT 0,
    promise_to_pay BOOLEAN DEFAULT FALSE,
    recovered BOOLEAN DEFAULT FALSE,
    money_recovered DECIMAL(12,2) DEFAULT 0,

    FOREIGN KEY (transaction_id)
        REFERENCES transactions(transaction_id)
);

CREATE TABLE recovery_decisions (
    decision_id SERIAL PRIMARY KEY,
    recovery_case_id INTEGER NOT NULL,
    recovery_probability DECIMAL(6,4),
    priority_score DECIMAL(6,4),
    priority VARCHAR(20),
    strategy VARCHAR(50),
    recovery_action VARCHAR(50),
    recommended_channel VARCHAR(30),
    expected_recovery_value DECIMAL(12,2),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (recovery_case_id)
        REFERENCES recovery_cases(recovery_case_id)
);

CREATE TABLE recovery_actions (
    action_id SERIAL PRIMARY KEY,
    decision_id INTEGER NOT NULL,
    channel VARCHAR(30),
    action_type VARCHAR(50),
    message TEXT,
    action_status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (decision_id)
        REFERENCES recovery_decisions(decision_id)
);

CREATE INDEX idx_transactions_customer
ON transactions(customer_id);

CREATE INDEX idx_transactions_status
ON transactions(payment_status);

CREATE INDEX idx_recovery_decisions_priority
ON recovery_decisions(priority);

CREATE INDEX idx_recovery_decisions_score
ON recovery_decisions(priority_score);