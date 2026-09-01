// ============================================================
// REVENUE RECOVERY AI
// CUSTOMERS PAGE
// ============================================================

let allCustomers = [];


// ============================================================
// HELPERS
// ============================================================

function escapeCustomerHtml(value) {
    if (value === null || value === undefined) {
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
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2
    }).format(Number(value || 0));
}


function formatCustomerPercent(value) {
    return Number(value || 0).toFixed(2) + "%";
}


function setCustomerText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


// ============================================================
// METRICS
// ============================================================

function updateCustomerMetrics(data) {

    setCustomerText(
        "total-customers",
        Number(data.total_customers || 0)
            .toLocaleString("en-IN")
    );

    setCustomerText(
        "customers-with-cases",
        Number(data.customers_with_cases || 0)
            .toLocaleString("en-IN")
    );

    setCustomerText(
        "recovered-customers",
        Number(data.recovered_customers || 0)
            .toLocaleString("en-IN")
    );

    setCustomerText(
        "customer-money-recovered",
        formatCustomerCurrency(data.money_recovered)
    );
}


// ============================================================
// LOAD CUSTOMERS
// ============================================================

async function loadCustomerMetrics() {

    try {

        const response = await fetch(
            "/customers",
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                `Customers API returned ${response.status}`
            );
        }

        const data = await response.json();

        console.log("Customers API:", data);

        allCustomers = Array.isArray(data.customers)
            ? data.customers
            : [];

        updateCustomerMetrics(data);
        renderCustomers(allCustomers);
        updateCustomerOverview(data);

    } catch (error) {

        console.error(
            "Failed to load customers:",
            error
        );

        const body = document.getElementById(
            "customer-table-body"
        );

        if (body) {
            body.innerHTML = `
                <tr>
                    <td colspan="7" class="loading">
                        Unable to load customer data.
                    </td>
                </tr>
            `;
        }
    }
}


// ============================================================
// RENDER
// ============================================================

function renderCustomers(customers) {

    const body = document.getElementById(
        "customer-table-body"
    );

    if (!body) {
        return;
    }

    if (!Array.isArray(customers) || customers.length === 0) {

        body.innerHTML = `
            <tr>
                <td colspan="7" class="loading">
                    No customers found.
                </td>
            </tr>
        `;

        return;
    }

    body.innerHTML = customers.map(customer => {

        const customerId =
            customer.customer_id || "";

        const averageProbability =
            Number(
                customer.average_recovery_probability || 0
            ) * 100;

        return `
            <tr>
                <td>
                    <span class="customer-id">
                        ${escapeCustomerHtml(customerId)}
                    </span>
                </td>

                <td>
                    ${Number(customer.cases || 0)
                        .toLocaleString("en-IN")}
                </td>

                <td>
                    ${formatCustomerCurrency(
                        customer.amount_at_risk
                    )}
                </td>

                <td>
                    ${Number(customer.recovered_cases || 0)
                        .toLocaleString("en-IN")}
                </td>

                <td>
                    ${formatCustomerPercent(
                        customer.recovery_rate
                    )}
                </td>

                <td>
                    ${formatCustomerCurrency(
                        customer.money_recovered
                    )}
                </td>

                <td>
                    ${formatCustomerPercent(
                        averageProbability
                    )}
                </td>
            </tr>
        `;
    }).join("");
}


// ============================================================
// SEARCH
// ============================================================

function filterCustomers() {

    const input = document.getElementById(
        "customer-search"
    );

    const search = input
        ? input.value.toLowerCase().trim()
        : "";

    if (!search) {
        renderCustomers(allCustomers);
        return;
    }

    const filtered = allCustomers.filter(customer =>
        String(customer.customer_id || "")
            .toLowerCase()
            .includes(search)
    );

    renderCustomers(filtered);
}


// ============================================================
// OVERVIEW
// ============================================================

function updateCustomerOverview(data) {

    const customers = Number(
        data.total_customers || 0
    );

    const recovered = Number(
        data.recovered_customers || 0
    );

    const rate = customers > 0
        ? (recovered / customers) * 100
        : 0;

    setCustomerText(
        "customer-recovery-rate",
        rate.toFixed(2) + "%"
    );
}


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        loadCustomerMetrics();

        const search = document.getElementById(
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
