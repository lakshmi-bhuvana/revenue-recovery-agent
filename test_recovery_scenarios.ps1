$base = "http://127.0.0.1:8000"

$scenarios = @(
    @{ scenario="payment_failure"; failure_reason="bank_decline"; transaction_id="demo_payment_001" },
    @{ scenario="checkout_abandonment"; failure_reason="customer_abandoned"; transaction_id="demo_checkout_001" },
    @{ scenario="failed_subscription"; failure_reason="subscription_payment_failed"; transaction_id="demo_subscription_001" },
    @{ scenario="b2b_receivable"; failure_reason="invoice_overdue"; transaction_id="demo_b2b_001" },
    @{ scenario="mandate_failure"; failure_reason="mandate_failed"; transaction_id="demo_mandate_001" },
    @{ scenario="promise_to_pay"; failure_reason="promise_to_pay_due"; transaction_id="demo_ptp_001" }
)

foreach ($s in $scenarios) {

    $body = @{
        transaction_id = $s.transaction_id
        customer_id = "demo_customer_$($s.scenario)"
        transaction_amount = 35000
        payment_method = "CARD"
        failure_reason = $s.failure_reason
        retry_count = 0
        customer_transaction_count = 8
        customer_success_rate = 0.88
        payment_method_success_rate = 0.91
        channel = "payment_link"
        preferred_channel = "whatsapp"
        product_interest_score = 0.91
        checkout_progress = if ($s.scenario -eq "checkout_abandonment") { 0.82 } else { 0.65 }
        customer_email_available = 1
        customer_phone_available = 1
        scenario = $s.scenario
        payment_status = "failed"
        revenue_at_risk = 1
        recovery_attempts = 0
        promise_to_pay = if ($s.scenario -eq "promise_to_pay") { 1 } else { 0 }
        recovered = 0
        money_recovered = 0
    } | ConvertTo-Json

    Write-Host "`n=== $($s.scenario) ===" -ForegroundColor Cyan

    try {
        $result = Invoke-RestMethod `
            -Uri "$base/recovery-events" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body

        $result.agent_result |
            Select-Object `
                status,
                diagnosis,
                score,
                action,
                policy,
                execution,
                stopping,
                escalation |
            ConvertTo-Json -Depth 10
    }
    catch {
        Write-Host $_ -ForegroundColor Red
    }
}

Write-Host "`n=== Scenario registry ===" -ForegroundColor Cyan

Invoke-RestMethod "$base/recovery-scenarios" |
    ConvertTo-Json -Depth 10