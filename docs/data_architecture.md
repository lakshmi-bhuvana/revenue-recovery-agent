\# Revenue Recovery Agent — Data Architecture



\## 1. Data Sources



The system uses three categories of data.



\### A. Razorpay-side data



These represent information available through Razorpay payment/product APIs.



Examples:



\- Payment ID

\- Order ID

\- Customer ID

\- Payment amount

\- Currency

\- Payment method

\- Payment status

\- Payment failure code

\- Payment failure reason

\- Failure source

\- Failure step

\- Payment timestamps

\- Retry/attempt information

\- Subscription ID

\- Plan ID

\- Subscription status

\- Authentication attempts

\- Paid billing cycles

\- Remaining billing cycles

\- Mandate/subscription state

\- Invoice ID

\- Invoice amount

\- Invoice status

\- Invoice due date

\- Amount paid

\- Payment Link information

\- Notification availability

\- Communication status



\---



\### B. Merchant-side data



Some information belongs to the merchant's business system rather than the payment gateway.



Examples:



\- Product ID

\- Product category

\- Product value

\- Customer product interest

\- Customer browsing/activity signals

\- Traffic source

\- Device type

\- Checkout stage

\- Customer segment

\- Merchant-defined customer value

\- Merchant-defined priority

\- CRM information



These fields should NOT be represented as Razorpay API fields.



\---



\### C. Derived / ML features



These are calculated by our system.



Examples:



\- Historical payment success rate

\- Historical failure rate

\- Payment-method success rate

\- Recent payment-method degradation

\- Customer recovery rate

\- Customer response rate

\- Average transaction value

\- Failure frequency

\- Retry effectiveness

\- Revenue at risk

\- Recovery probability

\- Risk score

\- Recommended intervention



\---



\## 2. Core Relationship



The main relationship is:



Merchant

&#x20;   |

&#x20;   +--- Customers

&#x20;   |       |

&#x20;   |       +--- Payments

&#x20;   |       |

&#x20;   |       +--- Checkouts

&#x20;   |       |

&#x20;   |       +--- Subscriptions

&#x20;   |       |

&#x20;   |       +--- Invoices

&#x20;   |

&#x20;   +--- Recovery Cases

&#x20;           |

&#x20;           +--- Recovery Actions

&#x20;           |

&#x20;           +--- Communications

&#x20;           |

&#x20;           +--- Promise-to-Pay

&#x20;           |

&#x20;           +--- Audit Events



\---



\## 3. Event-Centered Model



The system treats revenue loss as an event that can trigger a recovery case.



Examples:



Payment failure

&#x20;   ↓

Recovery Case



Checkout abandonment

&#x20;   ↓

Recovery Case



Subscription charge failure

&#x20;   ↓

Recovery Case



Invoice becomes overdue

&#x20;   ↓

Recovery Case



Promise-to-pay is broken

&#x20;   ↓

Recovery Case / Follow-up



\---



\## 4. Unified Recovery Case



Every recovery scenario eventually becomes a common Recovery Case.



A Recovery Case contains:



\- customer

\- merchant

\- source event

\- revenue at risk

\- ML risk score

\- predicted recovery probability

\- root cause

\- recommended intervention

\- workflow state

\- recovery outcome



This allows different revenue-loss scenarios to use the same recovery engine.



\---



\## 5. ML Data Flow



Raw data

&#x20;   ↓

Data validation

&#x20;   ↓

Feature engineering

&#x20;   ↓

Historical/customer/payment aggregates

&#x20;   ↓

ML model

&#x20;   ↓

Risk score

&#x20;   ↓

Recovery probability

&#x20;   ↓

Intervention decision



The model must not directly execute a recovery action.



The model provides predictions.



The policy/agent layer decides whether an action is permitted.



\---



\## 6. Recovery Data Flow



Revenue-risk event

&#x20;   ↓

Create Recovery Case

&#x20;   ↓

Calculate features

&#x20;   ↓

Predict recovery probability

&#x20;   ↓

Determine root cause

&#x20;   ↓

Check available channels

&#x20;   ↓

Select permitted intervention

&#x20;   ↓

Execute action

&#x20;   ↓

Observe result

&#x20;   ↓

Update recovery case

&#x20;   ↓

Record audit event



\---



\## 7. Clean Payments



Successful payments must be included.



They provide the baseline for:



\- normal customer behavior

\- normal payment-method behavior

\- payment success rates

\- customer history

\- ML training

\- comparison between successful and failed transactions



The dataset must therefore contain both successful and unsuccessful payment events.



\---



\## 8. Six Recovery Scenarios



The system supports:



1\. Payment degradation / failure recovery

2\. Checkout drop-off recovery

3\. Failed-subscription recovery

4\. B2B receivables recovery

5\. Mandate/retry sequencing

6\. Promise-to-pay tracking



These are not six separate applications.



They are different event sources feeding the same recovery architecture.



\---



\## 9. Separation of Responsibilities



\### Data layer



Stores raw and processed information.



\### Feature layer



Transforms historical events into ML features.



\### ML layer



Predicts risk and recovery probability.



\### Agent layer



Interprets the prediction and determines the next allowed step.



\### Recovery layer



Executes bounded recovery actions.



\### Audit layer



Records decisions, actions and outcomes.



\---



\## 10. Important Constraint



The system must never assume that information exists simply because it would be useful.



Every feature must be classified as:



\- Razorpay-provided

\- Merchant-provided

\- Derived by the system



This prevents leakage between gateway data and merchant business data.

