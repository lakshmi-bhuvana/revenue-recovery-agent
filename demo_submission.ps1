$base = "http://127.0.0.1:8000"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       REVENUE RECOVERY AGENT - SUBMISSION DEMO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ------------------------------------------------------------
# 1. BATCH BUSINESS IMPACT
# ------------------------------------------------------------

Write-Host ""
Write-Host "BATCH RECOVERY RESULTS" -ForegroundColor Green
Write-Host "-----------------------"

$m = Invoke-RestMethod "$base/metrics"

$atRisk = [double]$m.at_risk_cases
$recoveredCases = [double]$m.recovered_cases
$unrecoveredCases = [double]$m.unrecovered_cases
$totalValue = [double]$m.total_transaction_value
$actualRecovered = [double]$m.actual_recovered_value
$recoveryRate = [double]$m.recovery_rate

function Format-Cr($value) {
    return ("₹{0:N2} Cr" -f ($value / 10000000))
}

Write-Host ("Transactions at risk: {0:N0}" -f $atRisk)
Write-Host ("Recovered cases:      {0:N0}" -f $recoveredCases)
Write-Host ("Unrecovered cases:    {0:N0}" -f $unrecoveredCases)
Write-Host ""
Write-Host ("Total value at risk:  {0}" -f (Format-Cr $totalValue))
Write-Host ("Actual recovered:     {0}" -f (Format-Cr $actualRecovered))
Write-Host ("Recovery rate:        {0:N2}%" -f $recoveryRate)

# ------------------------------------------------------------
# 2. ML + DECISION DEMO
# ------------------------------------------------------------

Write-Host ""
Write-Host "------------------------------------------------------------"
Write-Host "ML-DRIVEN RECOVERY DECISION" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------"

$body = @{
    transaction_id = "submission_demo_ml_001"
    customer_id = "submission_demo_customer_001"
    transaction_amount = 25000
    payment_method = "card"
    failure_reason = "payment_method_degradation"
    scenario = "payment_failure"
    customer_transaction_count = 10
    customer_success_rate = 0.95
    payment_method_success_rate = 0.30
    customer_email_available = 1
    customer_phone_available = 1
    preferred_channel = "payment_link"
    product_interest_score = 0.90
    checkout_progress = 0.95
    recovery_attempts = 0
} | ConvertTo-Json

$r = Invoke-RestMethod `
    -Method Post `
    -Uri "$base/recovery-events" `
    -ContentType "application/json" `
    -Body $body

Write-Host ""
Write-Host "INPUT / SIGNALS" -ForegroundColor Cyan
Write-Host ("Transaction amount:       ₹{0:N2}" -f $r.agent_result.score.transaction_amount)
Write-Host ("Customer intent:          {0:N3}" -f $r.agent_result.score.customer_intent)
Write-Host ("Customer reliability:     {0:N3}" -f $r.agent_result.score.customer_reliability)
Write-Host ("Contactability:           {0:N3}" -f $r.agent_result.score.contactability)
Write-Host ("Recovery friction:        {0:N3}" -f $r.agent_result.score.recovery_friction)

Write-Host ""
Write-Host "MODEL DECISION" -ForegroundColor Cyan
Write-Host ("Recovery probability:     {0:N3}" -f $r.agent_result.score.recovery_probability)
Write-Host ("Priority score:           {0:N3}" -f $r.agent_result.score.priority_score)
Write-Host ("Priority:                 {0}" -f $r.agent_result.score.priority)
Write-Host ("Recommended channel:      {0}" -f $r.agent_result.score.recommended_channel)

Write-Host ""
Write-Host "AGENT ACTION" -ForegroundColor Cyan
Write-Host ("Strategy:                 {0}" -f $r.agent_result.action.strategy)
Write-Host ("Recovery action:          {0}" -f $r.agent_result.action.recovery_action)
Write-Host ("Channel:                  {0}" -f $r.agent_result.action.channel)

Write-Host ""
Write-Host "EXECUTION RESULT" -ForegroundColor Cyan
Write-Host ("Status:                   {0}" -f $r.agent_result.execution.execution_status)
Write-Host ("Recovered:                {0}" -f $r.agent_result.execution.recovered)
Write-Host ("Money recovered:          ₹{0:N2}" -f $r.agent_result.execution.money_recovered)
Write-Host ("Message sent:             {0}" -f $r.agent_result.execution.message_sent)

# ------------------------------------------------------------
# 3. AUDIT / STOPPING SUMMARY
# ------------------------------------------------------------

Write-Host ""
Write-Host "AUDIT / CONTROL SUMMARY" -ForegroundColor Magenta
Write-Host "------------------------"

Write-Host ("Policy allowed:           {0}" -f $r.agent_result.policy.allowed)
Write-Host ("Policy reason:            {0}" -f $r.agent_result.policy.reason)
Write-Host ("Stopping rule:            {0}" -f $r.agent_result.stopping.stop)
Write-Host ("Stopping reason:          {0}" -f $r.agent_result.stopping.reason)
Write-Host ("Escalation:               {0}" -f $r.agent_result.escalation.escalate)

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "DEMO COMPLETE" -ForegroundColor Green
Write-Host "============================================================"