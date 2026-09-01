// ============================================================
// REVENUE RECOVERY AI
// CUSTOMERS LIST PAGE
// ============================================================

let customers = [];


// ============================================================
// HELPERS
// ============================================================

function esc(value) {
    const div = document.createElement("div");

    div.textContent =
        value === null || value === undefined
            ? ""
            : String(value);

    return div.innerHTML;
}


function money(value) {
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


function numberIN(value) {
    return Number(
        value || 0
    ).toLocaleString(
        "en-IN"
    );
}


function setText(id, value) {
    const element =
        document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


// ============================================================
// SIDEBAR
// ============================================================

function setupSidebar() {

    const app =
        document.getElementById("app");

    const button =
        document.getElementById("sidebar-toggle");

    if (!app || !button) {
        return;
    }


    const saved =
        localStorage.getItem(
            "sidebarCollapsed"
        );


    if (saved === "true") {

        app.classList.add(
            "sidebar-collapsed"
        );

    } else {

        app.classList.remove(
            "sidebar-collapsed"
        );

    }


    updateSidebarButton();


    button.addEventListener(
        "click",
        function (event) {

            event.preventDefault();
            event.stopPropagation();

            app.classList.toggle(
                "sidebar-collapsed"
            );


            localStorage.setItem(
                "sidebarCollapsed",
                app.classList.contains(
                    "sidebar-collapsed"
                )
                    ? "true"
                    : "false"
            );


            updateSidebarButton();
        }
    );
}


function updateSidebarButton() {

    const app =
        document.getElementById("app");

    const button =
        document.getElementById(
            "sidebar-toggle"
        );

    if (!app || !button) {
        return;
    }


    const collapsed =
        app.classList.contains(
            "sidebar-collapsed"
        );


    const icon =
        button.querySelector(
            ".toggle-icon"
        );


    if (icon) {

        icon.textContent =
            collapsed
                ? "›"
                : "‹";
    }


    button.setAttribute(
        "aria-label",
        collapsed
            ? "Expand sidebar"
            : "Collapse sidebar"
    );


    button.setAttribute(
        "title",
        collapsed
            ? "Expand sidebar"
            : "Collapse sidebar"
    );
}


// ============================================================
// CUSTOMER TABLE
// ============================================================

function renderCustomers(
    list
) {

    const body =
        document.getElementById(
            "customer-table-body"
        );


    if (!body) {

        console.error(
            "customer-table-body was not found."
        );

        return;
    }


    if (
        !Array.isArray(list) ||
        list.length === 0
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
        list
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
                                    ${esc(customerId)}
                                </a>
                            </td>

                            <td>
                                ${numberIN(
                                    customer.cases
                                )}
                            </td>

                            <td class="amount">
                                ${money(
                                    customer.amount_at_risk
                                )}
                            </td>

                            <td>
                                ${numberIN(
                                    customer.recovered_cases
                                )}
                            </td>

                            <td>
                                ${Number(
                                    customer.recovery_rate || 0
                                ).toFixed(2)}%
                            </td>

                            <td class="amount">
                                ${money(
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
// LOAD CUSTOMERS
// ============================================================

async function loadCustomerMetrics() {

    const table =
        document.getElementById(
            "customer-table-body"
        );


    try {

        if (table) {

            table.innerHTML = `
                <tr>
                    <td
                        colspan="8"
                        class="loading"
                    >
                        Loading customers...
                    </td>
                </tr>
            `;
        }


        const response =
            await fetch(
                "/customers",
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                `Customers API returned ${response.status}`
            );
        }


        customers =
            Array.isArray(
                data.customers
            )
                ? data.customers
                : [];


        console.log(
            "Customers loaded:",
            customers.length
        );


        // ----------------------------------------------------
        // METRICS
        // ----------------------------------------------------

        setText(
            "total-customers",
            numberIN(
                data.total_customers
            )
        );


        setText(
            "customers-with-cases",
            numberIN(
                data.customers_with_cases
            )
        );


        setText(
            "recovered-customers",
            numberIN(
                data.recovered_customers
            )
        );


        setText(
            "money-recovered",
            money(
                data.money_recovered
            )
        );


        setText(
            "customer-money-recovered",
            money(
                data.money_recovered
            )
        );


        // ----------------------------------------------------
        // CUSTOMER RECOVERY RATE
        // ----------------------------------------------------

        const totalCustomers =
            Number(
                data.total_customers || 0
            );

        const recoveredCustomers =
            Number(
                data.recovered_customers || 0
            );


        const recoveryRate =
            totalCustomers > 0
                ? (
                    recoveredCustomers /
                    totalCustomers
                ) * 100
                : 0;


        setText(
            "customer-recovery-rate",
            recoveryRate.toFixed(2) + "%"
        );


        // ----------------------------------------------------
        // TABLE
        // ----------------------------------------------------

        renderCustomers(
            customers
        );


        // ----------------------------------------------------
        // PROGRESS BAR
        // ----------------------------------------------------

        updateCustomerProgress();


    } catch (error) {

        console.error(
            "Customer loading error:",
            error
        );


        if (table) {

            table.innerHTML = `
                <tr>
                    <td
                        colspan="8"
                        class="loading"
                    >
                        Unable to load customers.
                        <br>
                        ${esc(
                            error.message
                        )}
                    </td>
                </tr>
            `;
        }
    }
}


// ============================================================
// CUSTOMER SEARCH
// ============================================================

function filterCustomers() {

    const input =
        document.getElementById(
            "customer-search"
        );


    if (!input) {
        return;
    }


    const query =
        input.value
            .toLowerCase()
            .trim();


    if (!query) {

        renderCustomers(
            customers
        );

        return;
    }


    const filtered =
        customers.filter(
            customer => {

                const customerId =
                    String(
                        customer.customer_id || ""
                    )
                        .toLowerCase();


                return customerId.includes(
                    query
                );
            }
        );


    renderCustomers(
        filtered
    );
}


// ============================================================
// PROGRESS BAR
// ============================================================

function updateCustomerProgress() {

    const coverage =
        document.getElementById(
            "coverage-progress"
        );


    const recovery =
        document.getElementById(
            "recovery-progress"
        );


    const coverageRate =
        Number(
            document.getElementById(
                "coverage-rate"
            )?.textContent
                ?.replace(
                    "%",
                    ""
                )
        ) || 0;


    const recoveryRate =
        Number(
            document.getElementById(
                "customer-recovery-rate"
            )?.textContent
                ?.replace(
                    "%",
                    ""
                )
        ) || 0;


    if (coverage) {

        coverage.style.width =
            Math.max(
                0,
                Math.min(
                    100,
                    coverageRate
                )
            ) + "%";
    }


    if (recovery) {

        recovery.style.width =
            Math.max(
                0,
                Math.min(
                    100,
                    recoveryRate
                )
            ) + "%";
    }
}


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        console.log(
            "Recovery AI Customers page starting..."
        );


        setupSidebar();


        const refresh =
            document.getElementById(
                "customer-refresh"
            );


        if (refresh) {

            refresh.addEventListener(
                "click",
                loadCustomerMetrics
            );
        }


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


        loadCustomerMetrics();


        setInterval(
            loadCustomerMetrics,
            30000
        );

    }
);