1. Core Entities
These are the entities that exist across the entire Revenue Recovery system.
merchants
Column	Type	Purpose
merchant_id	string	Unique merchant
merchant_name	string	Merchant name
industry	string	Merchant industry
onboarding_date	date	Merchant start date
active	boolean	Whether merchant is active
customers
Column	Type	Purpose
customer_id	string	Unique customer
merchant_id	string	Merchant they belong to
name	string	Customer name
email	string	Email if available
phone	string	Phone if available
customer_segment	string	New / returning / loyal
created_at	timestamp	Customer creation time
orders
Column	Type	Purpose
order_id	string	Unique order
merchant_id	string	Merchant
customer_id	string	Customer
amount	float	Order value
currency	string	Currency
product_id	string	Product involved
created_at	timestamp	Order creation
payments
This is the central table.
Column	Type	Purpose
payment_id	string	Unique payment
order_id	string	Associated order
merchant_id	string	Merchant
customer_id	string	Customer
amount	float	Payment amount
payment_method	string	UPI / card / netbanking / wallet
payment_status	string	success / failed / pending
failure_code	string	Failure reason
failure_stage	string	Authentication / processing etc.
failure_source	string	Customer / bank / payment system etc.
created_at	timestamp	Payment timestamp
This table is where your clean successful payments AND failed payments belong.
That matters because ML needs to learn:
"What does a successful payment look like compared with a payment likely to fail?"
________________________________________
2. Customer & Payment Intelligence
This is where your earlier idea comes in:
Check customer's previous transactions + current payment method + payment-method success rate + customer/product interest.
customer_payment_profile
Column	Type	Purpose
customer_id	string	Customer
total_transactions	int	Historical transactions
successful_transactions	int	Successful payments
failed_transactions	int	Failed payments
historical_success_rate	float	Customer's payment success rate
avg_transaction_value	float	Average amount
preferred_payment_method	string	Most successful/preferred method
last_successful_payment	timestamp	Last success
last_failed_payment	timestamp	Last failure
payment_method_metrics
This captures the traffic and performance of each payment method.
Column	Type	Purpose
merchant_id	string	Merchant
payment_method	string	UPI/card/etc.
time_window	string	Hour/day/week
total_attempts	int	Number of attempts
successful_attempts	int	Successful
failed_attempts	int	Failed
success_rate	float	Success percentage
avg_amount	float	Average transaction amount
This lets the system reason:
"UPI success rate for this merchant is currently 94%, but this customer's card has historically failed 4/5 times."
________________________________________
customer_product_interest
This captures your other important idea.
Column	Type	Purpose
customer_id	string	Customer
product_id	string	Product
views	int	Product views
cart_additions	int	Added to cart
checkout_attempts	int	Checkout attempts
purchases	int	Completed purchases
last_interaction	timestamp	Latest interaction
interest_score	float	Calculated interest
Now the system can distinguish:
Payment failure + high product interest + historically legitimate customer
from
Payment failure + low interest + suspicious/unknown customer.
________________________________________
3. Scenario Tables
This is where the six scenarios live.
Don't force everything into one giant table.
A. Checkout Drop-off
checkout_sessions
Column	Type
checkout_id	string
customer_id	string
merchant_id	string
order_id	string
amount	float
payment_method	string
checkout_started_at	timestamp
payment_attempted	boolean
payment_completed	boolean
abandoned	boolean
abandonment_stage	string
________________________________________
B. Failed Subscription Recovery
subscription_events
Column	Type
subscription_id	string
customer_id	string
merchant_id	string
plan_id	string
amount	float
billing_cycle	string
event_type	string
payment_status	string
failure_reason	string
retry_count	int
event_time	timestamp
Possible event_type:
subscription_created
payment_attempt
payment_failed
payment_success
subscription_halted
subscription_cancelled
subscription_resumed
________________________________________
C. B2B Receivables Chaser
invoices
Column	Type
invoice_id	string
merchant_id	string
customer_id	string
amount	float
issue_date	date
due_date	date
paid_date	date
status	string
days_overdue	int
payment_link	string
Possible status:
issued
partially_paid
paid
overdue
cancelled
expired
________________________________________
D. Mandate Retry Sequencer
mandate_events
Column	Type
mandate_id	string
customer_id	string
subscription_id	string
payment_method	string
attempt_number	int
attempt_time	timestamp
status	string
failure_reason	string
next_retry_at	timestamp
This becomes important for your agent because it can learn:
retry now / retry later / change payment method / stop retrying.
________________________________________
E. Hinglish Voice Recovery
recovery_conversations
Column	Type
conversation_id	string
customer_id	string
recovery_event_id	string
channel	string
language	string
intent	string
sentiment	string
transcript	text
customer_response	string
promised_payment_date	date
outcome	string
For example:
language = Hinglish
intent = promise_to_pay
outcome = promised
You don't necessarily need actual voice calls in your first implementation.
You can simulate the conversation and show how the agent would handle it.
________________________________________
F. Promise-to-Pay
promise_to_pay
Column	Type
ptp_id	string
customer_id	string
invoice_id	string
amount_promised	float
promised_date	date
created_at	timestamp
status	string
reminder_count	int
fulfilled_at	timestamp
broken_reason	string
Possible status:
promised
fulfilled
broken
expired
cancelled
________________________________________
4. Common Revenue Event
This is very important for your architecture.
Instead of building six completely independent systems, normalize everything into a common event.
revenue_events
Column	Type	Purpose
event_id	string	Unique event
merchant_id	string	Merchant
customer_id	string	Customer
event_type	string	Type of revenue risk
source_entity_id	string	Payment/order/invoice/subscription ID
amount_at_risk	float	Revenue potentially lost
event_time	timestamp	Event time
risk_status	string	detected/recovered/lost
recovery_status	string	pending/success/failed
created_at	timestamp	Event creation
Example:
event_type = PAYMENT_FAILURE
amount_at_risk = 1499
risk_status = detected
or:
event_type = CHECKOUT_ABANDONMENT
amount_at_risk = 2499
or:
event_type = OVERDUE_INVOICE
amount_at_risk = 85000
This is what lets one recovery engine handle all six scenarios.
________________________________________
5. ML Tables
Now we explicitly satisfy the requirement:
The project must contain a meaningful ML component.
recovery_predictions
Column	Type
prediction_id	string
event_id	string
model_version	string
recovery_probability	float
predicted_outcome	string
confidence	float
top_factors	json
prediction_time	timestamp
Example:
recovery_probability = 0.82
predicted_outcome = likely_recoverable
confidence = 0.91
top_factors =
    historical_success_rate
    payment_method_failure_rate
    customer_interest_score
customer_risk_features
This is the feature store-like layer.
Feature	Example
historical_success_rate	0.92
payment_method_success_rate	0.71
customer_transaction_count	18
failed_attempts_recent	2
product_interest_score	0.87
avg_transaction_value	1299
days_since_last_success	12
invoice_days_overdue	8
This is where your ML model gets its input.
________________________________________
6. Recovery Orchestration
This is the agent layer.
recovery_cases
Column	Type
case_id	string
event_id	string
customer_id	string
amount_at_risk	float
risk_score	float
recommended_action	string
priority	string
status	string
created_at	timestamp
recovery_actions
Column	Type
action_id	string
case_id	string
action_type	string
channel	string
scheduled_at	timestamp
executed_at	timestamp
result	string
next_action	string
Possible actions:
RETRY_PAYMENT
SUGGEST_PAYMENT_METHOD
SEND_PAYMENT_LINK
SEND_EMAIL
SEND_SMS
SEND_REMINDER
CREATE_PROMISE_TO_PAY
RETRY_MANDATE
ESCALATE_TO_MERCHANT
STOP_RECOVERY
________________________________________
7. Measurement
This answers the problem statement's biggest requirement:
Show measured money recovered across a batch.
recovery_outcomes
Column	Type
outcome_id	string
case_id	string
amount_at_risk	float
amount_recovered	float
recovery_status	string
recovery_time	timestamp
recovery_attempts	int
Then calculate:
Revenue at risk
SUM(amount_at_risk)
Revenue recovered
SUM(amount_recovered)
Recovery rate
recovered / revenue_at_risk
Recovery uplift
Compare:
recovered with agent
vs
baseline recovery
This is how you demonstrate that the system isn't just "AI-looking."
It actually made money come back.
________________________________________
8. Audit
Because your agent is allowed to execute bounded recovery workflows, we need an audit trail.
audit_logs
Column	Type
audit_id	string
case_id	string
agent_action	string
reason	text
model_score	float
policy_check	string
executed	boolean
timestamp	timestamp
Example:
Agent detected payment failure.

ML recovery probability: 0.86

Reason:
Customer has 17 previous successful transactions.
Current card success rate is low.
UPI success rate is 94%.

Action:
Suggest UPI.

Policy:
Allowed.

Executed:
Yes.
This is much stronger than simply saying "our AI agent decided this."
________________________________________
9. Entity Relationships
Put this at the bottom of dataset_schema.md.
You can represent the architecture like this:
MERCHANT
   |
   +---- CUSTOMER
   |        |
   |        +---- CUSTOMER PAYMENT PROFILE
   |        |
   |        +---- PRODUCT INTEREST
   |        |
   |        +---- PAYMENTS
   |        |
   |        +---- SUBSCRIPTIONS
   |        |
   |        +---- INVOICES
   |
   +---- ORDERS
            |
            +---- PAYMENTS
            |
            +---- CHECKOUT SESSIONS


PAYMENTS
   |
   +---- REVENUE EVENTS
   |
   +---- ML PREDICTION
   |
   +---- RECOVERY CASE
             |
             +---- RECOVERY ACTION
             |
             +---- RECOVERY OUTCOME
             |
             +---- AUDIT LOG


SUBSCRIPTIONS
   |
   +---- SUBSCRIPTION EVENTS
   |
   +---- MANDATE EVENTS
   |
   +---- PROMISE TO PAY


INVOICES
   |
   +---- PROMISE TO PAY
   |
   +---- RECOVERY EVENTS
________________________________________
The architecture we're actually building
Keep this mental model. This is the important part.
                    RAZORPAY / MERCHANT DATA
                              │
          ┌───────────────────┼───────────────────┐
          ↓                   ↓                   ↓
      Payments            Customers          Business Events
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ↓
                    ┌───────────────────┐
                    │ Intelligence Layer│
                    │                   │
                    │ Customer history  │
                    │ Payment behavior  │
                    │ Method success    │
                    │ Product interest  │
                    └─────────┬─────────┘
                              ↓
                         ML MODEL
                              ↓
                  "How recoverable is this?"
                              ↓
                    REVENUE EVENT ENGINE
                              ↓
                  RECOVERY ORCHESTRATOR
                              ↓
        ┌─────────────┬─────────────┬──────────────┐
        ↓             ↓             ↓              ↓
      Retry       Payment       Reminder       Promise-to-
      payment     switch        SMS/Email        Pay
        │             │             │              │
        └─────────────┴─────────────┴──────────────┘
                              ↓
                       STOPPING RULES
                              ↓
                     RECOVERY OUTCOME
                              ↓
                    ₹ MONEY RECOVERED
                              ↓
                         AUDIT LOG

