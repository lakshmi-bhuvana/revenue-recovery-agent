# Revenue Recovery Agent

### Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery

An AI-powered revenue recovery system that identifies revenue at risk, diagnoses the reason, predicts recovery potential, selects the right recovery action, and executes within controlled boundaries.

## How It Works

**Detect → Diagnose → Predict → Decide → Act → Measure → Stop / Escalate → Audit**

The system combines machine learning, deterministic recovery policies, workflow logic, and an LLM for language-based tasks.

## Key Features

- Revenue-at-risk detection
- Recovery probability prediction
- Recovery strategy and action selection
- Adaptive recovery based on customer responses
- Retry and stopping controls
- Human escalation
- Recovery audit trail
- Batch recovery
- Customer analysis
- Recovery analytics

## AI Architecture

### Machine Learning
A Logistic Regression model predicts recovery probability and supports recovery prioritization.

### LLM
OpenRouter is used for:
- Decision explanations
- Recovery-message generation
- Customer-response interpretation

The LLM does **not** control recovery probability, priority scoring, retry limits, safety policies, stopping rules, escalation thresholds, or unrestricted operational actions.

## Recovery Workflow

```text
Transaction / Customer Data
          ↓
       Detect
          ↓
      Diagnose
          ↓
       Predict
          ↓
        Decide
          ↓
   Policy / Control
          ↓
         Act
          ↓
       Measure
       ↙      ↘
   Success    Failure
      ↓          ↓
    Stop    Retry / Follow-up
                  ↓
            Attempt Limit?
             ↙        ↘
           No          Yes
           ↓            ↓
       Continue     Escalate
                         ↓
                 Human Intervention
                         ↓
                       Audit
