// ============================================================
// REVENUE RECOVERY AI
// CUSTOMERS PAGE
// ============================================================

const CUSTOMER_API = "/customers";

let allCustomers = [];


// ============================================================
// HELPERS
// ============================================================

function escapeCustomerHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatCustomerCurrency(value) {

    return new Intl.NumberFormat(
        "en-IN",
        {
            style: "currency",
            currency: "INR",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }
    ).format(
        Number(value || 0)
    );
}


function formatNumber(value) {

    return Number(
        value || 0
    ).toLocaleString(
        "en-IN"
    );
}


function formatPercent(value) {

    return Number(
        value || 0
    ).toFixed(2) + "%";
}


function setCustomerText(
    id,
    value
) {

    const element =
        document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


// ============================================================
// LOAD CUSTOMER DATA
// ============================================================

async function loadCustomerMetrics() {

    try {

        const response =
            await fetch(
                CUSTOMER_API,
                {
                    cache: "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                `Customers API returned ${response.status}`
            );
        }


        const data =
            await response.json();


        console.log(
            "Customer data loaded:",
            data
        );


        allCustomers =
            Array.isArray(
                data.customers
            )
                ? data.customers
                : [];


        // ----------------------------------------------------
        // TOP METRICS
        // ----------------------------------------------------

        setCustomerText(
            "total-customers",
            formatNumber(
                data.total_customers
            )
        );


        setCustomerText(
            "customers-with-cases",
            formatNumber(
                data.customers_with_cases
            )
        );


        setCustomerText(
            "recovered-customers",
            formatNumber(
                data.recovered_customers
            )
        );


        // Your page uses this existing ID if present.
        setCustomerText(
            "money-recovered",
            formatCustomerCurrency(
                data.money_recovered
            )
        );


        setCustomerText(
            "customer-money-recovered",
            formatCustomerCurrency(
                data.money_recovered
            )
        );


        // ----------------------------------------------------
        // OVERVIEW
        // ----------------------------------------------------

        const totalCustomers =
            Number(
                data.total_customers || 0
            );

        const recoveredCustomers =
            Number(
                data.recovered_customers || 0
            );

        const customerRecoveryRate =
            totalCustomers > 0
                ? (
                    recoveredCustomers /
                    totalCustomers *
                    100
                )
                : 0;


        setCustomerText(
            "customer-recovery-rate",
            customerRecoveryRate.toFixed(2) + "%"
        );


        // ----------------------------------------------------
        // STATUS
        // ----------------------------------------------------

        updateCustomerStatus(
            data
        );


        // ----------------------------------------------------
        // TABLE
        // ----------------------------------------------------

        renderCustomers(
            allCustomers
        );


    } catch (error) {

        console.error(
            "Failed to load customer data:",
            error
        );


        const table =
            document.getElementById(
                "customer-table-body"
            );


        if (table) {

            table.innerHTML = `
                <tr>
                    <td
                        colspan="8"
                        class="loading"
                    >
                        Unable to load customer data.
                        ${escapeCustomerHtml(
                            error.message
                        )}
                    </td>
                </tr>
            `;
        }
    }
}


// ============================================================
// CUSTOMER STATUS
// ============================================================

function updateCustomerStatus(
    data
) {

    const status =
        document.getElementById(
            "customer-status"
        );


    if (!status) {
        return;
    }


    status.innerHTML = `
        <div class="status-row">

            <div class="status-left">

                <div class="status-title">
                    Customer data
                </div>

                <div class="status-description">
                    Complete customer population
                </div>

            </div>

            <div class="status-value">
                ${formatNumber(
                    data.total_customers
                )} customers
            </div>

        </div>


        <div class="status-row">

            <div class="status-left">

                <div class="status-title">
                    Recovery cases
                </div>

                <div class="status-description">
                    All transactions in the dataset
                </div>

            </div>

            <div class="status-value">
                ${formatNumber(
                    data.total_cases
                )}
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
                ${formatNumber(
                    data.recovered_customers
                )}
            </div>

        </div>
    `;
}


// ============================================================
// RENDER CUSTOMER TABLE
// ============================================================

function renderCustomers(
    customers
) {

    const body =
        document.getElementById(
            "customer-table-body"
        );


    if (!body) {

        console.error(
            "customer-table-body not found in customers.html"
        );

        return;
    }


    if (
        !Array.isArray(customers) ||
        customers.length === 0
    ) {

        body.innerHTML = `
            <tr>
                <td
                    colspan="8"
                    class="loading"
                >
                    No customers found.
                </td>
            </tr>
        `;

        return;
    }


    body.innerHTML =
        customers
            .map(
                customer => {

                    const customerId =
                        String(
                            customer.customer_id || ""
                        );


                    return `
                        <tr>

                            <td>

                                <a
                                    class="customer-id-link"
                                    href="/customer.html?customer_id=${encodeURIComponent(customerId)}"
                                >
                                    ${escapeCustomerHtml(
                                        customerId
                                    )}
                                </a>

                            </td>


                            <td>
                                ${formatNumber(
                                    customer.cases
                                )}
                            </td>


                            <td>
                                ${formatCustomerCurrency(
                                    customer.amount_at_risk
                                )}
                            </td>


                            <td>
                                ${formatNumber(
                                    customer.recovered_cases
                                )}
                            </td>


                            <td>
                                ${formatPercent(
                                    customer.recovery_rate
                                )}
                            </td>


                            <td>
                                ${formatCustomerCurrency(
                                    customer.money_recovered
                                )}
                            </td>


                            <td>
                                ${(
                                    Number(
                                        customer.average_recovery_probability || 0
                                    ) * 100
                                ).toFixed(2)}%
                            </td>


                            <td>

                                <a
                                    class="customer-action"
                                    href="/customer.html?customer_id=${encodeURIComponent(customerId)}"
                                >
                                    View Customer
                                </a>

                            </td>

                        </tr>
                    `;
                }
            )
            .join("");
}


// ============================================================
// SEARCH
// ============================================================

function filterCustomers() {

    const input =
        document.getElementById(
            "customer-search"
        );


    if (!input) {
        return;
    }


    const search =
        input.value
            .toLowerCase()
            .trim();


    if (!search) {

        renderCustomers(
            allCustomers
        );

        return;
    }


    const filtered =
        allCustomers.filter(
            customer => {

                const id =
                    String(
                        customer.customer_id || ""
                    )
                        .toLowerCase();


                return id.includes(
                    search
                );
            }
        );


    renderCustomers(
        filtered
    );
}


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        loadCustomerMetrics();


        const search =
            document.getElementById(
                "customer-search"
            );


        if (search) {

            search.addEventListener(
                "input",
                filterCustomers
            );
        }


        setInterval(
            loadCustomerMetrics,
            30000
        );
    }
);