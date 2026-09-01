document.addEventListener("DOMContentLoaded", () => {
    loadCustomers();
});


async function loadCustomers() {

    const status =
        document.getElementById("customer-status");


    try {

        console.log("Customer page loaded");


        if (status) {
            status.style.display = "none";
        }


        /*
         * -----------------------------------------
         * LOAD CUSTOMER DATA
         * -----------------------------------------
         *
         * IMPORTANT:
         * Do NOT use /recovery-cases?limit=500 here.
         *
         * The /customers endpoint already performs
         * the complete customer aggregation on the
         * backend using the full at-risk dataset.
         */

        const response =
            await fetch("/customers");


        console.log(
            "Customers API HTTP:",
            response.status
        );


        if (!response.ok) {

            throw new Error(
                `Customers API failed: HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        console.log(
            "Customers API response:",
            data
        );


        /*
         * -----------------------------------------
         * VALIDATE RESPONSE
         * -----------------------------------------
         */

        if (!data || typeof data !== "object") {

            throw new Error(
                "Customers API returned an invalid response"
            );

        }


        if (!Array.isArray(data.customers)) {

            throw new Error(
                "Customers API did not return a customers array"
            );

        }


        /*
         * -----------------------------------------
         * BACKEND CUSTOMER METRICS
         * -----------------------------------------
         *
         * These values come directly from the
         * backend /customers endpoint.
         */

        const totalCustomers =
            Number(
                data.total_customers || 0
            );


        const customersWithCases =
            Number(
                data.customers_with_cases || 0
            );


        const recoveredCustomers =
            Number(
                data.recovered_customers || 0
            );


        const totalCases =
            Number(
                data.total_cases || 0
            );


        const moneyRecovered =
            Number(
                data.money_recovered || 0
            );


        /*
         * -----------------------------------------
         * CUSTOMER RATES
         * -----------------------------------------
         */

        const coverageRate =
            totalCustomers > 0
                ? (
                    customersWithCases /
                    totalCustomers
                ) * 100
                : 0;


        const recoveryRate =
            totalCustomers > 0
                ? (
                    recoveredCustomers /
                    totalCustomers
                ) * 100
                : 0;


        const averageRecovery =
            recoveredCustomers > 0
                ? (
                    moneyRecovered /
                    recoveredCustomers
                )
                : 0;


        /*
         * -----------------------------------------
         * LOG FINAL METRICS
         * -----------------------------------------
         */

        console.log(
            "Customer metrics:",
            {
                totalCustomers,
                customersWithCases,
                recoveredCustomers,
                totalCases,
                moneyRecovered,
                coverageRate,
                recoveryRate,
                averageRecovery
            }
        );


        /*
         * -----------------------------------------
         * UPDATE KPI CARDS
         * -----------------------------------------
         */

        setText(
            "total-customers",
            formatNumber(totalCustomers)
        );


        setText(
            "customers-with-cases",
            formatNumber(customersWithCases)
        );


        setText(
            "recovered-customers",
            formatNumber(recoveredCustomers)
        );


        setText(
            "money-recovered",
            formatCurrency(moneyRecovered)
        );


        /*
         * -----------------------------------------
         * UPDATE OVERVIEW
         * -----------------------------------------
         */

        setText(
            "coverage-rate",
            `${coverageRate.toFixed(2)}%`
        );


        setText(
            "customer-recovery-rate",
            `${recoveryRate.toFixed(2)}%`
        );


        setText(
            "average-recovery",
            formatCurrency(averageRecovery)
        );


        /*
         * -----------------------------------------
         * PROGRESS BARS
         * -----------------------------------------
         */

        const coverageProgress =
            document.getElementById(
                "coverage-progress"
            );


        if (coverageProgress) {

            coverageProgress.style.width =
                `${Math.min(
                    coverageRate,
                    100
                )}%`;

        }


        const recoveryProgress =
            document.getElementById(
                "recovery-progress"
            );


        if (recoveryProgress) {

            recoveryProgress.style.width =
                `${Math.min(
                    recoveryRate,
                    100
                )}%`;

        }


        /*
         * -----------------------------------------
         * CUSTOMER STATUS
         * -----------------------------------------
         */

        if (status) {

            status.innerHTML = `

                <div class="status-row">

                    <div class="status-left">

                        <div class="status-title">
                            Customer data
                        </div>

                        <div class="status-description">
                            Customer intelligence loaded from the complete recovery dataset
                        </div>

                    </div>

                    <div class="status-value">
                        ${formatNumber(totalCustomers)} customers
                    </div>

                </div>


                <div class="status-row">

                    <div class="status-left">

                        <div class="status-title">
                            Recovery cases
                        </div>

                        <div class="status-description">
                            Total revenue-at-risk cases currently tracked
                        </div>

                    </div>

                    <div class="status-value">
                        ${formatNumber(totalCases)}
                    </div>

                </div>


                <div class="status-row">

                    <div class="status-left">

                        <div class="status-title">
                            Recovered customers
                        </div>

                        <div class="status-description">
                            Customers with at least one recovered case
                        </div>

                    </div>

                    <div class="status-value">
                        ${formatNumber(recoveredCustomers)}
                    </div>

                </div>

            `;

            status.style.display = "block";

        }


        /*
         * -----------------------------------------
         * SUCCESS
         * -----------------------------------------
         */

        console.log(
            "Customer page successfully loaded."
        );


    } catch (error) {

        console.error(
            "Customer data error:",
            error
        );


        /*
         * -----------------------------------------
         * ERROR UI
         * -----------------------------------------
         */

        if (status) {

            status.innerHTML = `

                <div class="status-row">

                    <div class="status-left">

                        <div class="status-title">
                            API Error
                        </div>

                        <div class="status-description">
                            ${escapeHtml(error.message)}
                        </div>

                    </div>

                    <div class="status-value">
                        Error
                    </div>

                </div>

            `;

            status.style.display = "block";

        }

    }

}


/*
 * -----------------------------------------
 * SET TEXT
 * -----------------------------------------
 */

function setText(id, value) {

    const element =
        document.getElementById(id);


    if (element) {

        element.textContent =
            value;

    }

}


/*
 * -----------------------------------------
 * NUMBER FORMAT
 * -----------------------------------------
 */

function formatNumber(value) {

    return Number(
        value || 0
    ).toLocaleString("en-IN");

}


/*
 * -----------------------------------------
 * CURRENCY FORMAT
 * -----------------------------------------
 */

function formatCurrency(value) {

    return `₹${Number(
        value || 0
    ).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;

}


/*
 * -----------------------------------------
 * HTML ESCAPE
 * -----------------------------------------
 */

function escapeHtml(value) {

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}