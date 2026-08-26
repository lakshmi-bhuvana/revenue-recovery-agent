1\. Core Entities

These are the entities that exist across the entire Revenue Recovery system.

merchants

Column	Type	Purpose

merchant\_id	string	Unique merchant

merchant\_name	string	Merchant name

industry	string	Merchant industry

onboarding\_date	date	Merchant start date

active	boolean	Whether merchant is active

customers

Column	Type	Purpose

customer\_id	string	Unique customer

merchant\_id	string	Merchant they belong to

name	string	Customer name

email	string	Email if available

phone	string	Phone if available

customer\_segment	string	New / returning / loyal

created\_at	timestamp	Customer creation time

orders

Column	Type	Purpose

order\_id	string	Unique order

merchant\_id	string	Merchant

customer\_id	string	Customer

amount	float	Order value

currency	string	Currency

product\_id	string	Product involved

created\_at	timestamp	Order creation

payments

This is the central table.

Column	Type	Purpose

payment\_id	string	Unique payment

order\_id	string	Associated order

merchant\_id	string	Merchant

customer\_id	string	Customer

amount	float	Payment amount

payment\_method	string	UPI / card / netbanking / wallet

payment\_status	string	success / failed / pending

failure\_code	string	Failure reason

failure\_stage	string	Authentication / processing etc.

failure\_source	string	Customer / bank / payment system etc.

created\_at	timestamp	Payment timestamp

This table is where your clean successful payments AND failed payments belong.

That matters because ML needs to learn:

"What does a successful payment look like compared with a payment likely to fail?"

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

2\. Customer \& Payment Intelligence

This is where your earlier idea comes in:

Check customer's previous transactions + current payment method + payment-method success rate + customer/product interest.

customer\_payment\_profile

Column	Type	Purpose

customer\_id	string	Customer

total\_transactions	int	Historical transactions

successful\_transactions	int	Successful payments

failed\_transactions	int	Failed payments

historical\_success\_rate	float	Customer's payment success rate

avg\_transaction\_value	float	Average amount

preferred\_payment\_method	string	Most successful/preferred method

last\_successful\_payment	timestamp	Last success

last\_failed\_payment	timestamp	Last failure

payment\_method\_metrics

This captures the traffic and performance of each payment method.

Column	Type	Purpose

merchant\_id	string	Merchant

payment\_method	string	UPI/card/etc.

time\_window	string	Hour/day/week

total\_attempts	int	Number of attempts

successful\_attempts	int	Successful

failed\_attempts	int	Failed

success\_rate	float	Success percentage

avg\_amount	float	Average transaction amount

This lets the system reason:

"UPI success rate for this merchant is currently 94%, but this customer's card has historically failed 4/5 times."

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

customer\_product\_interest

This captures your other important idea.

Column	Type	Purpose

customer\_id	string	Customer

product\_id	string	Product

views	int	Product views

cart\_additions	int	Added to cart

checkout\_attempts	int	Checkout attempts

purchases	int	Completed purchases

last\_interaction	timestamp	Latest interaction

interest\_score	float	Calculated interest

Now the system can distinguish:

Payment failure + high product interest + historically legitimate customer

from

Payment failure + low interest + suspicious/unknown customer.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

3\. Scenario Tables

This is where the six scenarios live.

Don't force everything into one giant table.

A. Checkout Drop-off

checkout\_sessions

Column	Type

checkout\_id	string

customer\_id	string

merchant\_id	string

order\_id	string

amount	float

payment\_method	string

checkout\_started\_at	timestamp

payment\_attempted	boolean

payment\_completed	boolean

abandoned	boolean

abandonment\_stage	string

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

B. Failed Subscription Recovery

subscription\_events

Column	Type

subscription\_id	string

customer\_id	string

merchant\_id	string

plan\_id	string

amount	float

billing\_cycle	string

event\_type	string

payment\_status	string

failure\_reason	string

retry\_count	int

event\_time	timestamp

Possible event\_type:

subscription\_created

payment\_attempt

payment\_failed

payment\_success

subscription\_halted

subscription\_cancelled

subscription\_resumed

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

C. B2B Receivables Chaser

invoices

Column	Type

invoice\_id	string

merchant\_id	string

customer\_id	string

amount	float

issue\_date	date

due\_date	date

paid\_date	date

status	string

days\_overdue	int

payment\_link	string

Possible status:

issued

partially\_paid

paid

overdue

cancelled

expired

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

D. Mandate Retry Sequencer

mandate\_events

Column	Type

mandate\_id	string

customer\_id	string

subscription\_id	string

payment\_method	string

attempt\_number	int

attempt\_time	timestamp

status	string

failure\_reason	string

next\_retry\_at	timestamp

This becomes important for your agent because it can learn:

retry now / retry later / change payment method / stop retrying.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

E. Hinglish Voice Recovery

recovery\_conversations

Column	Type

conversation\_id	string

customer\_id	string

recovery\_event\_id	string

channel	string

language	string

intent	string

sentiment	string

transcript	text

customer\_response	string

promised\_payment\_date	date

outcome	string

For example:

language = Hinglish

intent = promise\_to\_pay

outcome = promised

You don't necessarily need actual voice calls in your first implementation.

You can simulate the conversation and show how the agent would handle it.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

F. Promise-to-Pay

promise\_to\_pay

Column	Type

ptp\_id	string

customer\_id	string

invoice\_id	string

amount\_promised	float

promised\_date	date

created\_at	timestamp

status	string

reminder\_count	int

fulfilled\_at	timestamp

broken\_reason	string

Possible status:

promised

fulfilled

broken

expired

cancelled

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

4\. Common Revenue Event

This is very important for your architecture.

Instead of building six completely independent systems, normalize everything into a common event.

revenue\_events

Column	Type	Purpose

event\_id	string	Unique event

merchant\_id	string	Merchant

customer\_id	string	Customer

event\_type	string	Type of revenue risk

source\_entity\_id	string	Payment/order/invoice/subscription ID

amount\_at\_risk	float	Revenue potentially lost

event\_time	timestamp	Event time

risk\_status	string	detected/recovered/lost

recovery\_status	string	pending/success/failed

created\_at	timestamp	Event creation

Example:

event\_type = PAYMENT\_FAILURE

amount\_at\_risk = 1499

risk\_status = detected

or:

event\_type = CHECKOUT\_ABANDONMENT

amount\_at\_risk = 2499

or:

event\_type = OVERDUE\_INVOICE

amount\_at\_risk = 85000

This is what lets one recovery engine handle all six scenarios.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

5\. ML Tables

Now we explicitly satisfy the requirement:

The project must contain a meaningful ML component.

recovery\_predictions

Column	Type

prediction\_id	string

event\_id	string

model\_version	string

recovery\_probability	float

predicted\_outcome	string

confidence	float

top\_factors	json

prediction\_time	timestamp

Example:

recovery\_probability = 0.82

predicted\_outcome = likely\_recoverable

confidence = 0.91

top\_factors =

&#x20;   historical\_success\_rate

&#x20;   payment\_method\_failure\_rate

&#x20;   customer\_interest\_score

customer\_risk\_features

This is the feature store-like layer.

Feature	Example

historical\_success\_rate	0.92

payment\_method\_success\_rate	0.71

customer\_transaction\_count	18

failed\_attempts\_recent	2

product\_interest\_score	0.87

avg\_transaction\_value	1299

days\_since\_last\_success	12

invoice\_days\_overdue	8

This is where your ML model gets its input.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

6\. Recovery Orchestration

This is the agent layer.

recovery\_cases

Column	Type

case\_id	string

event\_id	string

customer\_id	string

amount\_at\_risk	float

risk\_score	float

recommended\_action	string

priority	string

status	string

created\_at	timestamp

recovery\_actions

Column	Type

action\_id	string

case\_id	string

action\_type	string

channel	string

scheduled\_at	timestamp

executed\_at	timestamp

result	string

next\_action	string

Possible actions:

RETRY\_PAYMENT

SUGGEST\_PAYMENT\_METHOD

SEND\_PAYMENT\_LINK

SEND\_EMAIL

SEND\_SMS

SEND\_REMINDER

CREATE\_PROMISE\_TO\_PAY

RETRY\_MANDATE

ESCALATE\_TO\_MERCHANT

STOP\_RECOVERY

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

7\. Measurement

This answers the problem statement's biggest requirement:

Show measured money recovered across a batch.

recovery\_outcomes

Column	Type

outcome\_id	string

case\_id	string

amount\_at\_risk	float

amount\_recovered	float

recovery\_status	string

recovery\_time	timestamp

recovery\_attempts	int

Then calculate:

Revenue at risk

SUM(amount\_at\_risk)

Revenue recovered

SUM(amount\_recovered)

Recovery rate

recovered / revenue\_at\_risk

Recovery uplift

Compare:

recovered with agent

vs

baseline recovery

This is how you demonstrate that the system isn't just "AI-looking."

It actually made money come back.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

8\. Audit

Because your agent is allowed to execute bounded recovery workflows, we need an audit trail.

audit\_logs

Column	Type

audit\_id	string

case\_id	string

agent\_action	string

reason	text

model\_score	float

policy\_check	string

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

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

9\. Entity Relationships

Put this at the bottom of dataset\_schema.md.

You can represent the architecture like this:

MERCHANT

&#x20;  |

&#x20;  +---- CUSTOMER

&#x20;  |        |

&#x20;  |        +---- CUSTOMER PAYMENT PROFILE

&#x20;  |        |

&#x20;  |        +---- PRODUCT INTEREST

&#x20;  |        |

&#x20;  |        +---- PAYMENTS

&#x20;  |        |

&#x20;  |        +---- SUBSCRIPTIONS

&#x20;  |        |

&#x20;  |        +---- INVOICES

&#x20;  |

&#x20;  +---- ORDERS

&#x20;           |

&#x20;           +---- PAYMENTS

&#x20;           |

&#x20;           +---- CHECKOUT SESSIONS





PAYMENTS

&#x20;  |

&#x20;  +---- REVENUE EVENTS

&#x20;  |

&#x20;  +---- ML PREDICTION

&#x20;  |

&#x20;  +---- RECOVERY CASE

&#x20;            |

&#x20;            +---- RECOVERY ACTION

&#x20;            |

&#x20;            +---- RECOVERY OUTCOME

&#x20;            |

&#x20;            +---- AUDIT LOG





SUBSCRIPTIONS

&#x20;  |

&#x20;  +---- SUBSCRIPTION EVENTS

&#x20;  |

&#x20;  +---- MANDATE EVENTS

&#x20;  |

&#x20;  +---- PROMISE TO PAY





INVOICES

&#x20;  |

&#x20;  +---- PROMISE TO PAY

&#x20;  |

&#x20;  +---- RECOVERY EVENTS

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

The architecture we're actually building

Keep this mental model. This is the important part.

&#x20;                   RAZORPAY / MERCHANT DATA

&#x20;                             │

&#x20;         ┌───────────────────┼───────────────────┐

&#x20;         ↓                   ↓                   ↓

&#x20;     Payments            Customers          Business Events

&#x20;         │                   │                   │

&#x20;         └───────────────────┼───────────────────┘

&#x20;                             ↓

&#x20;                   ┌───────────────────┐

&#x20;                   │ Intelligence Layer│

&#x20;                   │                   │

&#x20;                   │ Customer history  │

&#x20;                   │ Payment behavior  │

&#x20;                   │ Method success    │

&#x20;                   │ Product interest  │

&#x20;                   └─────────┬─────────┘

&#x20;                             ↓

&#x20;                        ML MODEL

&#x20;                             ↓

&#x20;                 "How recoverable is this?"

&#x20;                             ↓

&#x20;                   REVENUE EVENT ENGINE

&#x20;                             ↓

&#x20;                 RECOVERY ORCHESTRATOR

&#x20;                             ↓

&#x20;       ┌─────────────┬─────────────┬──────────────┐

&#x20;       ↓             ↓             ↓              ↓

&#x20;     Retry       Payment       Reminder       Promise-to-

&#x20;     payment     switch        SMS/Email        Pay

&#x20;       │             │             │              │

&#x20;       └─────────────┴─────────────┴──────────────┘

&#x20;                             ↓

&#x20;                      STOPPING RULES

&#x20;                             ↓

&#x20;                    RECOVERY OUTCOME

&#x20;                             ↓

&#x20;                   ₹ MONEY RECOVERED

&#x20;                             ↓

&#x20;                        AUDIT LOG





