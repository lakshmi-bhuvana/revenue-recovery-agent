Revenue Recovery Agent



Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery



Find revenue that's slipping away and win it back.



Revenue Recovery Agent is an AI-powered revenue recovery system that identifies revenue at risk, diagnoses the reason for the risk, predicts recovery potential, selects an appropriate recovery action, and executes a bounded recovery workflow.



The system follows an end-to-end recovery loop:



DETECT → DIAGNOSE → PREDICT → DECIDE → ACT → MEASURE → STOP / ESCALATE → AUDIT



1\. Problem



Revenue can be lost after:



Payment failures



Checkout abandonment



Mandate failures



Overdue B2B receivables



Promise-to-pay situations



Simply detecting a failed transaction is not enough. Different recovery situations require different interventions, and repeatedly retrying every case can lead to inefficient recovery and poor customer experience.



Revenue Recovery Agent addresses this by determining:



Which revenue is at risk



Why the revenue is at risk



How likely the case is to recover



Which recovery strategy and action should be used



Which communication channel is appropriate



When automated recovery should stop



When a case should be escalated to a human



How much revenue was actually recovered



2\. Objectives



The system is designed to:



Detect revenue at risk.



Diagnose the underlying recovery situation.



Predict recovery probability.



Prioritize recovery opportunities.



Select an appropriate recovery strategy and action.



Execute recovery actions within deterministic policy boundaries.



Adapt recovery based on customer responses.



Stop automated recovery when recovery succeeds or the recovery boundary is reached.



Escalate cases to human intervention when required.



Persist recovery decisions, execution outcomes, stopping reasons, and escalation information.



Measure recovered revenue across recovery cases and batches.



3\. Solution



Revenue Recovery Agent combines machine learning, deterministic policy controls, workflow logic, and an LLM for language-oriented tasks.



End-to-End Recovery Workflow



Transaction / Customer Data

&#x20;         |

&#x20;         v

&#x20;     DETECT

&#x20;         |

&#x20;         v

&#x20;    DIAGNOSE

&#x20;         |

&#x20;         v

&#x20;     PREDICT

&#x20;         |

&#x20;         v

&#x20;      DECIDE

&#x20;         |

&#x20;         v

&#x20; POLICY / CONTROL

&#x20;         |

&#x20;         v

&#x20;       ACT

&#x20;         |

&#x20;         v

&#x20;     MEASURE

&#x20;         |

&#x20;    +----+----+

&#x20;    |         |

&#x20; SUCCESS    FAILURE

&#x20;    |         |

&#x20;    v         v

&#x20;   STOP   Retry / Follow-up

&#x20;              |

&#x20;              v

&#x20;       Attempt Limit?

&#x20;         /       \\

&#x20;       No         Yes

&#x20;       |           |

&#x20;       v           v

&#x20;    Continue    ESCALATE

&#x20;                   |

&#x20;                   v

&#x20;            Human Intervention

&#x20;                   |

&#x20;                   v

&#x20;                 AUDIT



The key design principle is that prediction and language intelligence are separated from deterministic operational controls.



4\. AI Architecture



Machine Learning



A Logistic Regression model is used to predict recovery probability.



The prediction helps the system:



Estimate the likelihood of successful recovery.



Prioritize recovery opportunities.



Support recovery decision-making.



The ML model does not directly control operational safety boundaries.



Model Evaluation



Metric



Logistic Regression



Precision



76.60%



Recall



100.00%



F1 Score



86.75%



ROC-AUC



0.5833



PR-AUC



0.8013



Brier Score



0.1793



The ML model is one component of the overall recovery system. The project focuses on connecting prediction with controlled decision-making, execution, measurement, and escalation.



5\. LLM Integration



The project uses OpenRouter for language-oriented tasks.



The LLM is used for:



Recovery decision explanations



Recovery-message generation



Customer-response interpretation



The LLM is intentionally not responsible for:



Recovery probability scoring



Priority scoring



Retry limits



Safety policies



Stopping rules



Escalation thresholds



Unrestricted operational actions



This separation allows language intelligence to add value while keeping operational safety boundaries deterministic.



The LLM is used where language adds value, while operational safety boundaries remain deterministic.



6\. Recovery Decisioning



Recovery decisions use transaction and customer context such as:



Transaction amount



Failure reason



Payment method



Customer transaction history



Customer success rate



Payment method success rate



Customer intent



Customer reliability



Contactability



Checkout progress



Product interest



Previous recovery attempts



These signals are used together with recovery probability and policy controls to determine an appropriate recovery path.



7\. Recovery Strategies



The system supports multiple recovery strategies:



Aggressive Recovery



Assisted Recovery



Standard Recovery



Low Cost Recovery



Example recovery actions include:



Retry payment



Retry mandate



Checkout reminder



Payment link follow-up



Invoice reminder



Promise-to-pay follow-up



The system can also recommend a communication channel such as:



WhatsApp



Email



SMS



Payment link



8\. Adaptive Recovery Loop



Recovery is not treated as a single prediction-and-action step.



The outcome of an action is evaluated and fed back into the recovery workflow.



Successful Recovery



Action

&#x20; ↓

Payment Success

&#x20; ↓

Measure Recovery

&#x20; ↓

STOP



Promise to Pay



Action

&#x20; ↓

Promise to Pay

&#x20; ↓

Follow-up

&#x20; ↓

Re-evaluate



Failed Recovery



Action

&#x20; ↓

Failure

&#x20; ↓

Check Attempt Limit

&#x20; ↓

Retry / Follow-up



Automation Boundary



Attempt Limit Reached

&#x20; ↓

Stop Automated Recovery

&#x20; ↓

Human Review



This allows the system to adapt rather than repeatedly applying the same recovery action.



9\. Policy and Safety Controls



Recovery actions are controlled by deterministic policies.



The policy layer controls:



Allowed recovery actions



Retry limits



Stopping conditions



Escalation conditions



Recovery attempt state



Human intervention requirements



This prevents the AI layer from having unrestricted control over the recovery workflow.



When the permitted automated recovery boundary is reached, the system stops automated recovery and creates a human-review state.



10\. Human Intervention



Cases that reach the automated recovery boundary are escalated for human review.



The Human Intervention view provides information including:



Transaction ID



Customer



Priority



Revenue at risk



Attempt count



Stopping reason



Escalation reason



Recommended team



Human-review status



This creates a controlled handoff from automated recovery to human intervention.



11\. Audit Trail



Each recovery workflow maintains execution and decision information.



The recovery timeline follows:



DETECT

&#x20;  ↓

DIAGNOSE

&#x20;  ↓

PREDICT

&#x20;  ↓

DECIDE

&#x20;  ↓

ACT

&#x20;  ↓

MEASURE

&#x20;  ↓

STOP / ESCALATE



The audit information records details such as:



Diagnosis



Recovery probability



Selected strategy



Selected action



Communication channel



Attempt count



Execution outcome



Money recovered



Stopping reason



Escalation status



Timestamp



This makes recovery decisions inspectable and traceable.



12\. Batch Recovery



The system supports processing recovery opportunities as a batch.



Batch recovery applies the controlled recovery workflow across eligible cases while retaining individual case outcomes and audit information.



This allows the system to evaluate recovery at scale while maintaining case-level traceability and measurable recovery outcomes.



13\. Dashboard and Analytics



The dashboard provides visibility into:



Revenue at risk



Expected recovery



Recovery rate



Money recovered



High-priority opportunities



Recovery strategies



Recovery cases



Customer-level information



Human escalations



Recovery execution history



The analytics views connect recovery intelligence with measurable business outcomes.



14\. Customer Analysis



Customer-level analysis provides additional context for recovery decisions, including:



Transaction history



Payment behavior



Recovery attempts



Recovery outcomes



Customer reliability



Contactability



Payment methods



Revenue associated with the customer



This allows recovery decisions to consider customer context rather than only the current failed transaction.



15\. Example Recovery Case



A recovery case follows this general flow:



Transaction

&#x20;   |

&#x20;   +-- Revenue at Risk

&#x20;   +-- Failure / Recovery Reason

&#x20;   +-- Customer Context

&#x20;   |

&#x20;   v

Recovery Probability

&#x20;   |

&#x20;   v

Priority

&#x20;   |

&#x20;   v

Recovery Strategy

&#x20;   |

&#x20;   v

Recovery Action

&#x20;   |

&#x20;   v

Execution

&#x20;   |

&#x20;   v

Outcome

&#x20;   |

&#x20;   +-- Recovered → STOP

&#x20;   |

&#x20;   +-- Not Recovered → Retry / Follow-up

&#x20;   |

&#x20;   +-- Limit Reached → HUMAN ESCALATION

&#x20;   |

&#x20;   v

Audit Trail



16\. Technology Stack



Backend



Python



FastAPI



Scikit-learn



Logistic Regression



JSON-based runtime persistence



Frontend



React



Vite



Dashboard and recovery-case interfaces



AI



OpenRouter



LLM-based decision explanations



LLM-based recovery-message generation



LLM-based customer-response interpretation



Data



Transaction-level recovery data



Customer-level transaction context



Persisted recovery execution and audit information



17\. Project Structure



revenue-recovery-agent/

│

├── frontend/

│   └── src/

│       ├── pages/

│       ├── components/

│       └── ...

│

├── src/

│   └── api/

│       └── main.py

│

├── data/

│   ├── raw/

│   └── runtime/

│

├── recovery\_cases\_current.json

├── recovery\_cases\_after\_escalation.json

├── README.md

└── ...



18\. Running the Project



Clone the repository



git clone https://github.com/lakshmi-bhuvana/revenue-recovery-agent.git

cd revenue-recovery-agent



Backend Setup



Create a Python virtual environment:



python -m venv .venv



Windows:



.venv\\Scripts\\Activate.ps1



Install dependencies:



pip install -r requirements.txt



Environment Variables



Create a .env file and configure:



OPENROUTER\_API\_KEY=your\_openrouter\_api\_key

OPENROUTER\_MODEL=openrouter/free



Do not commit API keys or other secrets to GitHub.



Start the Backend



Run the FastAPI application using the project's configured entry point.



Start the Frontend



cd frontend

npm install

npm run dev



Open the local URL provided by Vite.



19\. Key Design Principle



The central design decision is the separation between AI intelligence and operational control.



AI / ML

&#x20; |

&#x20; +-- Recovery probability

&#x20; +-- Prioritization

&#x20; +-- Diagnosis support

&#x20; +-- Explanations

&#x20; +-- Customer-response interpretation

&#x20; |

&#x20; v

Deterministic Recovery Policy

&#x20; |

&#x20; +-- Allowed actions

&#x20; +-- Retry limits

&#x20; +-- Stop conditions

&#x20; +-- Escalation

&#x20; |

&#x20; v

Controlled Recovery Workflow

&#x20; |

&#x20; v

Measured Outcome + Audit



This allows the system to use AI where it provides value while maintaining predictable recovery boundaries.



20\. What Makes This Different



Revenue Recovery Agent is not only a prediction model or failed-payment classifier.



It connects:



Prediction → Decision → Action → Outcome → Adaptation → Control



The system answers not only:



"Is this revenue at risk?"



but also:



"What should we do about it, how should we act within defined boundaries, when should we stop, and when should a human take over?"



The goal is measurable revenue recovery through controlled automation and an auditable workflow.



21\. Track 03 Alignment



This project is built for:



Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery



The implementation focuses on:



Detecting revenue at risk



Diagnosing recovery situations



Predicting recovery potential



Selecting appropriate interventions



Executing bounded recovery workflows



Measuring recovered revenue



Applying stopping rules



Escalating to humans



Maintaining an audit trail



Adapting to customer responses



22\. Demo Flow



The project demo showcases:



Recovery dashboard



Recovery cases



Case-level recovery intelligence



Agent decision reasoning



Adaptive recovery loop



Policy and audit information



Batch recovery workflow



Human intervention



Customer analysis



Recovery analytics



Recommended demo flow:



Recovery Agent

&#x20;     ↓

Recovery Cases

&#x20;     ↓

Recovery Case

&#x20;     ↓

Agent Decision

&#x20;     ↓

Adaptive Recovery

&#x20;     ↓

Policy + Audit

&#x20;     ↓

Batch Recovery

&#x20;     ↓

Human Intervention

&#x20;     ↓

Customer Analysis

&#x20;     ↓

Analytics



23\. Execution Note



Recovery execution in the submitted project is implemented as a controlled/simulated workflow for demonstration and evaluation.



The system does not claim unrestricted live payment execution.



Operational recovery boundaries remain deterministic, with human escalation available when automated recovery reaches its defined limits.



24\. Final Summary



Revenue Recovery Agent turns revenue recovery from a simple failure-detection problem into a controlled decision and action workflow:



Detect → Diagnose → Predict → Decide → Act → Measure → Adapt → Stop / Escalate → Audit



The system combines ML for recovery prediction, an LLM for language-oriented intelligence, deterministic policies for operational safety, adaptive recovery logic for customer responses, and persistent audit information for traceability.



The goal is simple:



Recover more revenue while knowing what to do, when to stop, and when to involve a human.

