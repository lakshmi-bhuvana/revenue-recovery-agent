\# ML Problem Definition



\## Objective



Predict the probability that an at-risk revenue event can be successfully recovered after intervention.



\## Target



`recovered`



\- 1 = revenue successfully recovered

\- 0 = revenue not recovered



\## ML Population



Only transactions where:



`revenue\_at\_risk = 1`



Clean successful payments are retained in the overall dataset but are excluded from the recovery prediction training population.



\## Candidate Features



\- transaction\_amount

\- customer\_transaction\_count

\- customer\_success\_rate

\- payment\_method

\- payment\_method\_success\_rate

\- channel

\- preferred\_channel

\- product\_interest\_score

\- checkout\_progress

\- customer\_email\_available

\- customer\_phone\_available

\- scenario

\- payment\_status

\- failure\_reason



\## Excluded Features



The following are post-intervention variables and must not be used as model inputs:



\- recovery\_attempts

\- promise\_to\_pay

\- recovered

\- money\_recovered



\## Model Output



The model produces:



`P(recovery)`



This represents the estimated probability that intervention will recover the at-risk revenue.



\## Business Metric



Expected Recovery Value:



`ERV = transaction\_amount × P(recovery)`



ERV is used by the recovery decision engine to prioritize interventions.



\## System Role



The ML model does not independently execute recovery actions.



It provides recoverability intelligence to the Revenue Recovery Agent.



The agent combines:



\- ML prediction

\- transaction value

\- customer history

\- payment-method performance

\- scenario

\- communication availability

\- intervention history

\- stopping rules



to select an appropriate recovery action.



\## Overall Flow



Event

→ Revenue-at-Risk Detection

→ ML Recoverability Prediction

→ Root Cause Analysis

→ Intervention Selection

→ Bounded Recovery Workflow

→ Recovery Outcome

→ Money Recovered

→ Audit Trail

