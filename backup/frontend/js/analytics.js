// ============================================================
// RECOVERY AI
// ANALYTICS PAGE
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
    loadAnalytics();
});


// ============================================================
// LOAD ANALYTICS
// ============================================================

async function loadAnalytics() {

    const errorBox =
        document.getElementById("analytics-error");

    try {

        if (errorBox) {
            errorBox.style.display = "none";
        }


        // ----------------------------------------------------
        // LOAD BACKEND DATA
        // ----------------------------------------------------

        const [
            metricsResponse,
            strategyResponse,
            priorityResponse,
            customersResponse
        ] = await Promise.all([
            fetch("/metrics"),
            fetch("/metrics/strategy"),
            fetch("/metrics/priority"),
            fetch("/customers")
        ]);


        // ----------------------------------------------------
        // VALIDATE RESPONSES
        // ----------------------------------------------------

        if (!metricsResponse.ok) {
            throw new Error(
                `Metrics API failed: HTTP ${metricsResponse.status}`
            );
        }

        if (!strategyResponse.ok) {
            throw new Error(
                `Strategy API failed: HTTP ${strategyResponse.status}`
            );
        }

        if (!priorityResponse.ok) {
            throw new Error(
                `Priority API failed: HTTP ${priorityResponse.status}`
            );
        }

        if (!customersResponse.ok) {
            throw new Error(
                `Customers API failed: HTTP ${customersResponse.status}`
            );
        }


        // ----------------------------------------------------
        // PARSE DATA
        // ----------------------------------------------------

        const metrics =
            await metricsResponse.json();

        const strategyData =
            await strategyResponse.json();

        const priorityData =
            await priorityResponse.json();

        const customersData =
            await customersResponse.json();


        console.log(
            "Analytics metrics:",
            metrics
        );

        console.log(
            "Analytics strategy:",
            strategyData
        );

        console.log(
            "Analytics priority:",
            priorityData
        );

        console.log(
            "Analytics customers:",
            customersData
        );


        // ====================================================
        // BACKEND METRICS
        // ====================================================

        const totalTransactionValue =
            Number(
                metrics.total_transaction_value || 0
            );


        const expectedRecoveryValue =
            Number(
                metrics.expected_recovery_value || 0
            );


        const actualRecoveredValue =
            Number(
                metrics.actual_recovered_value || 0
            );


        const highPriorityCases =
            Number(
                metrics.high_priority_cases || 0
            );


        const atRiskCases =
            Number(
                metrics.at_risk_cases || 0
            );


        // ====================================================
        // CUSTOMER METRICS
        // ====================================================
        //
        // IMPORTANT:
        // Use /customers as the authoritative customer source.
        //
        // Do NOT calculate customers from /recovery-cases?limit=500
        // because that endpoint is paginated.
        //
        // Your dataset has more customers than can fit in one
        // 500-case recovery API response.
        // ====================================================

        const totalCustomers =
            Number(
                customersData.total_customers || 0
            );


        const recoveredCustomers =
            Number(
                customersData.recovered_customers || 0
            );


        const customerCases =
            Number(
                customersData.total_cases || atRiskCases
            );


        const recoveryRate =
            totalCustomers > 0
                ? (
                    recoveredCustomers /
                    totalCustomers
                ) * 100
                : 0;


        // ====================================================
        // CUSTOMER / BUSINESS CARDS
        // ====================================================

        setText(
            "analytics-total-customers",
            formatNumber(totalCustomers)
        );


        setText(
            "analytics-recovered-customers",
            formatNumber(recoveredCustomers)
        );


        setText(
            "analytics-recovery-rate",
            `${recoveryRate.toFixed(2)}%`
        );


        setText(
            "analytics-money-recovered",
            formatCurrency(actualRecoveredValue)
        );


        // ====================================================
        // INSIGHTS
        // ====================================================

        const averageRecovery =
            recoveredCustomers > 0
                ? actualRecoveredValue /
                  recoveredCustomers
                : 0;


        setText(
            "analytics-average-recovery",
            formatCurrency(averageRecovery)
        );


        // Coverage represents how many at-risk cases are
        // represented by the recovery system.

        setText(
            "analytics-coverage",
            atRiskCases > 0
                ? "100%"
                : "0%"
        );


        setText(
            "analytics-cases",
            formatNumber(atRiskCases)
        );


        // Unrecovered CUSTOMERS.

        const unrecoveredCustomers =
            Math.max(
                totalCustomers -
                recoveredCustomers,
                0
            );


        setText(
            "analytics-unrecovered",
            formatNumber(
                unrecoveredCustomers
            )
        );


        // ====================================================
        // STRATEGY DISTRIBUTION
        // ====================================================

        const strategies = {

            aggressive_recovery: 0,

            assisted_recovery: 0,

            standard_recovery: 0,

            low_cost_recovery: 0

        };


        if (
            strategyData &&
            Array.isArray(
                strategyData.strategy_distribution
            )
        ) {

            strategyData.strategy_distribution
                .forEach(item => {

                    const strategy =
                        String(
                            item.strategy || ""
                        ).toLowerCase();


                    if (
                        Object.prototype
                            .hasOwnProperty
                            .call(
                                strategies,
                                strategy
                            )
                    ) {

                        strategies[strategy] =
                            Number(
                                item.cases || 0
                            );

                    }

                });

        }


        // ====================================================
        // STRATEGY TOTAL
        // ====================================================

        const strategyTotal =
            Object.values(strategies)
                .reduce(
                    (sum, value) =>
                        sum + value,
                    0
                );


        setText(
            "analytics-strategy-total",
            formatNumber(strategyTotal)
        );


        // ====================================================
        // STRATEGY BARS
        // ====================================================

        updateStrategy(
            "aggressive",
            strategies.aggressive_recovery,
            strategyTotal
        );


        updateStrategy(
            "assisted",
            strategies.assisted_recovery,
            strategyTotal
        );


        updateStrategy(
            "standard",
            strategies.standard_recovery,
            strategyTotal
        );


        updateStrategy(
            "low-cost",
            strategies.low_cost_recovery,
            strategyTotal
        );


        // ====================================================
        // PERFORMANCE TABLE
        // ====================================================

        const performanceBody =
            document.getElementById(
                "performance-body"
            );


        if (performanceBody) {

            performanceBody.innerHTML = "";


            const strategyRows = [

                {
                    name: "Aggressive Recovery",
                    value:
                        strategies
                            .aggressive_recovery,
                    status: "High-value"
                },

                {
                    name: "Assisted Recovery",
                    value:
                        strategies
                            .assisted_recovery,
                    status: "Agent-assisted"
                },

                {
                    name: "Standard Recovery",
                    value:
                        strategies
                            .standard_recovery,
                    status: "Normal"
                },

                {
                    name: "Low Cost Recovery",
                    value:
                        strategies
                            .low_cost_recovery,
                    status: "Low priority"
                }

            ];


            strategyRows.forEach(row => {

                const share =
                    strategyTotal > 0
                        ? (
                            row.value /
                            strategyTotal
                        ) * 100
                        : 0;


                const tr =
                    document.createElement(
                        "tr"
                    );


                tr.innerHTML = `

                    <td>
                        <strong>
                            ${escapeHtml(
                                row.name
                            )}
                        </strong>
                    </td>

                    <td>
                        ${formatNumber(
                            row.value
                        )}
                    </td>

                    <td>
                        ${share.toFixed(2)}%
                    </td>

                    <td>
                        <span class="strategy-badge">
                            ${escapeHtml(
                                row.status
                            )}
                        </span>
                    </td>

                `;


                performanceBody.appendChild(
                    tr
                );

            });

        }


        // ====================================================
        // LIVE STATUS
        // ====================================================

        const liveText =
            document.getElementById(
                "analytics-live-text"
            );


        if (liveText) {

            liveText.textContent =
                "Live";

        }


        // ====================================================
        // OPTIONAL DEBUG OUTPUT
        // ====================================================

        console.log(
            "Analytics customer totals:",
            {
                totalCustomers,
                recoveredCustomers,
                unrecoveredCustomers,
                recoveryRate,
                customerCases
            }
        );


    } catch (error) {

        console.error(
            "Analytics error:",
            error
        );


        if (errorBox) {

            errorBox.textContent =
                `Unable to load analytics data: ${error.message}`;

            errorBox.style.display =
                "block";

        }


        const liveText =
            document.getElementById(
                "analytics-live-text"
            );


        if (liveText) {

            liveText.textContent =
                "API Error";

        }

    }

}


// ============================================================
// STRATEGY UI
// ============================================================

function updateStrategy(
    name,
    count,
    total
) {

    setText(
        `${name}-count`,
        formatNumber(count)
    );


    const percent =
        total > 0
            ? (
                count /
                total
            ) * 100
            : 0;


    setText(
        `${name}-percent`,
        `${percent.toFixed(2)}% of cases`
    );


    const bar =
        document.getElementById(
            `${name}-bar`
        );


    if (bar) {

        bar.style.width =
            `${Math.min(percent, 100)}%`;

    }

}


// ============================================================
// GENERIC HELPERS
// ============================================================

function setText(
    id,
    value
) {

    const element =
        document.getElementById(id);


    if (element) {

        element.textContent =
            value;

    }

}


// ============================================================
// NUMBER FORMAT
// ============================================================

function formatNumber(value) {

    return Number(
        value || 0
    ).toLocaleString(
        "en-IN"
    );

}


// ============================================================
// CURRENCY FORMAT
// ============================================================

function formatCurrency(value) {

    return `₹${Number(
        value || 0
    ).toLocaleString(
        "en-IN",
        {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }
    )}`;

}


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeHtml(value) {

    return String(
        value ?? ""
    )
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}