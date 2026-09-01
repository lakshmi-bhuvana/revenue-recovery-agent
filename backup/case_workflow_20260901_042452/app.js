// ============================================================
// REVENUE RECOVERY AI
// MAIN DASHBOARD JAVASCRIPT
// ============================================================

// FastAPI is served from the same host
const API_BASE = "";


// ============================================================
// SIDEBAR
// ============================================================

function toggleSidebar() {

    const app =
        document.getElementById("app");

    if (!app) return;

    const collapsed =
        app.classList.toggle(
            "sidebar-collapsed"
        );

    localStorage.setItem(
        "sidebarCollapsed",
        collapsed ? "true" : "false"
    );

    updateSidebarToggle();
}


function updateSidebarToggle() {

    const button =
        document.getElementById(
            "sidebar-toggle"
        );

    const app =
        document.getElementById("app");

    if (!button || !app) return;

    const collapsed =
        app.classList.contains(
            "sidebar-collapsed"
        );

    /*
     * The HTML contains a toggle icon span.
     * Updating the whole button text is safe because
     * the current dashboard uses a simple text icon.
     */
    button.textContent =
        collapsed
            ? "›"
            : "‹";

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


function setupSidebar() {

    const app =
        document.getElementById("app");

    const button =
        document.getElementById(
            "sidebar-toggle"
        );

    if (!app || !button) {

        console.error(
            "Sidebar elements not found."
        );

        return;
    }

    // Restore previous sidebar state
    const savedState =
        localStorage.getItem(
            "sidebarCollapsed"
        );

    if (savedState === "true") {

        app.classList.add(
            "sidebar-collapsed"
        );

    } else {

        app.classList.remove(
            "sidebar-collapsed"
        );

    }

    // Prevent duplicate listeners if setupSidebar
    // is ever called more than once.
    button.onclick = function (event) {

        event.preventDefault();
        event.stopPropagation();

        toggleSidebar();
    };

    updateSidebarToggle();
}


// ============================================================
// LOAD DASHBOARD
// ============================================================

async function loadDashboard() {

    const liveText =
        document.getElementById(
            "live-text"
        );

    try {

        if (liveText) {
            liveText.textContent =
                "Updating...";
        }


        // ----------------------------------------------------
        // MAIN DASHBOARD SUMMARY
        // ----------------------------------------------------

        const summaryResponse =
            await fetch(
                `${API_BASE}/dashboard-summary`,
                {
                    cache: "no-store"
                }
            );


        if (!summaryResponse.ok) {

            throw new Error(
                `Dashboard API returned ${summaryResponse.status}`
            );

        }


        const summary =
            await summaryResponse.json();


        console.log(
            "Dashboard summary:",
            summary
        );


        // ----------------------------------------------------
        // UPDATE MAIN DASHBOARD
        // ----------------------------------------------------

        updateMetrics(
            summary
        );

        updatePriority(
            summary
        );

        updateStrategies(
            summary
        );


        // ----------------------------------------------------
        // TOP RECOVERY OPPORTUNITIES
        // ----------------------------------------------------

        try {

            const opportunitiesResponse =
                await fetch(
                    `${API_BASE}/top-opportunities?limit=10`,
                    {
                        cache: "no-store"
                    }
                );


            if (opportunitiesResponse.ok) {

                const opportunities =
                    await opportunitiesResponse.json();

                updateOpportunities(
                    opportunities
                );

            } else {

                console.warn(
                    "Top opportunities API returned:",
                    opportunitiesResponse.status
                );

            }

        } catch (error) {

            console.warn(
                "Could not load top opportunities:",
                error
            );

        }


        // ----------------------------------------------------
        // LIVE STATUS
        // ----------------------------------------------------

        if (liveText) {
            liveText.textContent =
                "Live";
        }


    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );

        if (liveText) {

            liveText.textContent =
                "API Error";
        }

    }
}


// ============================================================
// UPDATE MAIN METRICS
// ============================================================

function updateMetrics(
    metrics
) {

    // --------------------------------------------------------
    // REVENUE AT RISK
    // --------------------------------------------------------

    setElementText(
        "total-risk",
        formatCurrency(
            metrics.total_transaction_value
        )
    );


    // --------------------------------------------------------
    // EXPECTED RECOVERY
    // --------------------------------------------------------

    setElementText(
        "expected-recovery",
        formatCurrency(
            metrics.expected_recovery_value
        )
    );


    // --------------------------------------------------------
    // RECOVERY RATE
    // --------------------------------------------------------

    setElementText(
        "recovery-rate",
        `${Number(
            metrics.recovery_rate || 0
        ).toFixed(2)}%`
    );


    // --------------------------------------------------------
    // HIGH PRIORITY CASES
    // --------------------------------------------------------

    const highPriority =
        (
            metrics.priority_distribution ||
            []
        ).find(
            item =>
                String(
                    item.priority || ""
                ).toUpperCase() === "HIGH"
        );


    setElementText(
        "high-priority",
        Number(
            highPriority
                ? highPriority.cases
                : 0
        ).toLocaleString(
            "en-IN"
        )
    );
}


// ============================================================
// PRIORITY DISTRIBUTION
// ============================================================

function updatePriority(
    data
) {

    const distribution =
        data.priority_distribution ||
        [];

    let high = 0;
    let medium = 0;
    let low = 0;


    distribution.forEach(
        item => {

            const priority =
                String(
                    item.priority || ""
                ).toUpperCase();

            const cases =
                Number(
                    item.cases || 0
                );


            if (priority === "HIGH") {

                high = cases;

            } else if (
                priority === "MEDIUM"
            ) {

                medium = cases;

            } else if (
                priority === "LOW"
            ) {

                low = cases;
            }

        }
    );


    // --------------------------------------------------------
    // UPDATE LEGEND
    // --------------------------------------------------------

    updateLegend(
        ".legend-dot.high",
        `High Priority (${high.toLocaleString("en-IN")})`
    );


    updateLegend(
        ".legend-dot.medium",
        `Medium Priority (${medium.toLocaleString("en-IN")})`
    );


    updateLegend(
        ".legend-dot.low",
        `Low Priority (${low.toLocaleString("en-IN")})`
    );


    // --------------------------------------------------------
    // UPDATE DONUT
    // --------------------------------------------------------

    updatePriorityChart(
        high,
        medium,
        low
    );
}


// ============================================================
// PRIORITY DONUT CHART
// ============================================================

function updatePriorityChart(
    high,
    medium,
    low
) {

    const circle =
        document.getElementById(
            "priority-chart"
        );

    if (!circle) return;


    const safeHigh =
        Math.max(
            0,
            Number(high) || 0
        );

    const safeMedium =
        Math.max(
            0,
            Number(medium) || 0
        );

    const safeLow =
        Math.max(
            0,
            Number(low) || 0
        );


    const total =
        safeHigh +
        safeMedium +
        safeLow;


    // --------------------------------------------------------
    // CENTER TOTAL
    // --------------------------------------------------------

    const totalLabel =
        document.getElementById(
            "priority-total"
        );


    if (totalLabel) {

        totalLabel.textContent =
            total.toLocaleString(
                "en-IN"
            );
    }


    // --------------------------------------------------------
    // EMPTY STATE
    // --------------------------------------------------------

    if (total <= 0) {

        circle.style.background =
            "#e2e8f0";

        return;
    }


    // --------------------------------------------------------
    // CALCULATE PERCENTAGES
    // --------------------------------------------------------

    const highPercent =
        (
            safeHigh /
            total
        ) * 100;


    const mediumPercent =
        (
            safeMedium /
            total
        ) * 100;


    const mediumEnd =
        highPercent +
        mediumPercent;


    // --------------------------------------------------------
    // DATA-DRIVEN DONUT
    // --------------------------------------------------------

    circle.style.background =
        `conic-gradient(
            #2563eb 0% ${highPercent}%,
            #f59e0b ${highPercent}% ${mediumEnd}%,
            #d1d5db ${mediumEnd}% 100%
        )`;

}


// ============================================================
// LEGEND
// ============================================================

function updateLegend(
    selector,
    text
) {

    const dot =
        document.querySelector(
            selector
        );

    if (!dot) return;


    const parent =
        dot.parentElement;

    if (!parent) return;


    const dotClass =
        dot.className;


    parent.innerHTML = `
        <span
            class="${escapeHtml(dotClass)}"
        ></span>

        <span>
            ${escapeHtml(text)}
        </span>
    `;
}


// ============================================================
// RECOVERY STRATEGIES
// ============================================================

function updateStrategies(
    data
) {

    const distribution =
        data.strategy_distribution ||
        [];


    let aggressive = 0;
    let assisted = 0;
    let standard = 0;
    let lowCost = 0;


    distribution.forEach(
        item => {

            const strategy =
                String(
                    item.strategy || ""
                ).toLowerCase();


            const cases =
                Number(
                    item.cases || 0
                );


            switch (strategy) {

                case "aggressive_recovery":

                    aggressive = cases;

                    break;


                case "assisted_recovery":

                    assisted = cases;

                    break;


                case "standard_recovery":

                    standard = cases;

                    break;


                case "low_cost_recovery":

                    lowCost = cases;

                    break;

            }

        }
    );


    setElementText(
        "aggressive-count",
        aggressive.toLocaleString(
            "en-IN"
        )
    );


    setElementText(
        "assisted-count",
        assisted.toLocaleString(
            "en-IN"
        )
    );


    setElementText(
        "standard-count",
        standard.toLocaleString(
            "en-IN"
        )
    );


    setElementText(
        "low-cost-count",
        lowCost.toLocaleString(
            "en-IN"
        )
    );
}


// ============================================================
// TOP RECOVERY OPPORTUNITIES
// ============================================================

function updateOpportunities(
    opportunities
) {

    const table =
        document.getElementById(
            "opportunity-table"
        );


    if (!table) return;


    /*
     * The endpoint may return either:
     *
     * [
     *   {...},
     *   {...}
     * ]
     *
     * or:
     *
     * {
     *   value: [...]
     * }
     *
     * Support both without changing the API.
     */

    let items =
        opportunities;


    if (
        opportunities &&
        !Array.isArray(opportunities) &&
        Array.isArray(
            opportunities.value
        )
    ) {

        items =
            opportunities.value;
    }


    if (
        !Array.isArray(items) ||
        items.length === 0
    ) {

        table.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    class="loading"
                >
                    No recovery opportunities found.
                </td>
            </tr>
        `;

        return;
    }


    table.innerHTML =
        items
            .map(
                item => {

                    const priority =
                        String(
                            item.priority ||
                            "LOW"
                        ).toUpperCase();


                    const allowedPriorities = {
                        HIGH: true,
                        MEDIUM: true,
                        LOW: true
                    };


                    const safePriority =
                        allowedPriorities[
                            priority
                        ]
                            ? priority
                            : "LOW";


                    const priorityClass =
                        safePriority.toLowerCase();


                    const probability =
                        Number(
                            item.recovery_probability ||
                            0
                        );


                    return `
                        <tr>

                            <!-- Transaction -->

                            <td>

                                <strong>
                                    ${escapeHtml(
                                        item.transaction_id
                                    )}
                                </strong>

                            </td>


                            <!-- Amount -->

                            <td class="amount">

                                ${formatCurrency(
                                    item.transaction_amount
                                )}

                            </td>


                            <!-- Recovery Probability -->

                            <td class="probability">

                                ${(probability * 100)
                                    .toFixed(1)}%

                            </td>


                            <!-- Priority -->

                            <td>

                                <span
                                    class="badge badge-${escapeHtml(
                                        priorityClass
                                    )}"
                                >
                                    ${escapeHtml(
                                        safePriority
                                    )}
                                </span>

                            </td>


                            <!-- Strategy -->

                            <td>

                                ${escapeHtml(
                                    formatStrategy(
                                        item.strategy
                                    )
                                )}

                            </td>


                            <!-- Channel -->

                            <td>

                                ${escapeHtml(
                                    item.recommended_channel ||
                                    "—"
                                )}

                            </td>


                            <!-- Expected Recovery -->

                            <td class="amount">

                                ${formatCurrency(
                                    item.expected_recovery_value
                                )}

                            </td>

                        </tr>
                    `;
                }
            )
            .join("");
}


// ============================================================
// FORMAT STRATEGY NAME
// ============================================================

function formatStrategy(
    strategy
) {

    if (!strategy) {
        return "—";
    }


    return String(
        strategy
    )
        .replaceAll(
            "_",
            " "
        )
        .replace(
            /\b\w/g,
            letter =>
                letter.toUpperCase()
        );
}


// ============================================================
// FORMAT CURRENCY
// ============================================================

function formatCurrency(
    value
) {

    const number =
        Number(
            value || 0
        );


    return new Intl.NumberFormat(
        "en-IN",
        {
            style: "currency",
            currency: "INR",
            maximumFractionDigits: 2
        }
    ).format(number);
}


// ============================================================
// TABLE SEARCH
// ============================================================

function filterTable() {

    const input =
        document.getElementById(
            "search"
        );


    if (!input) return;


    const search =
        input.value
            .toLowerCase()
            .trim();


    const rows =
        document.querySelectorAll(
            "#opportunity-table tr"
        );


    rows.forEach(
        row => {

            const text =
                row.textContent
                    .toLowerCase();


            row.style.display =
                text.includes(search)
                    ? ""
                    : "none";

        }
    );
}


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeHtml(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";
    }


    return String(value)
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


// ============================================================
// SET ELEMENT TEXT
// ============================================================

function setElementText(
    id,
    value
) {

    const element =
        document.getElementById(
            id
        );


    if (element) {
        element.textContent =
            value;
    }
}


// ============================================================
// RECOVERY AI
// ============================================================

function getDashboardAIContext() {

    const text =
        id => {

            const element =
                document.getElementById(
                    id
                );

            return element
                ? element.textContent.trim()
                : null;
        };


    return {

        revenue_at_risk:
            text("total-risk"),

        expected_recovery:
            text("expected-recovery"),

        recovery_rate:
            text("recovery-rate"),

        high_priority_cases:
            text("high-priority"),

        strategies: {

            aggressive:
                text("aggressive-count"),

            assisted:
                text("assisted-count"),

            standard:
                text("standard-count"),

            low_cost:
                text("low-cost-count")
        },

        page:
            "merchant revenue recovery dashboard"
    };
}


// ============================================================
// RECOVERY AI QUESTION BUTTONS
// ============================================================

function useAIQuestion(
    question
) {

    const input =
        document.getElementById(
            "ai-question"
        );

    if (!input) return;


    input.value =
        question;


    input.focus();
}


// ============================================================
// ASK RECOVERY AI
// ============================================================

async function askRecoveryAI(
    event
) {

    if (event) {

        event.preventDefault();
    }


    const input =
        document.getElementById(
            "ai-question"
        );

    const button =
        document.getElementById(
            "ai-ask-button"
        );

    const response =
        document.getElementById(
            "ai-response"
        );

    const responseText =
        document.getElementById(
            "ai-response-text"
        );

    const status =
        document.getElementById(
            "ai-bar-status"
        );


    if (!input) {

        console.error(
            "AI question input not found."
        );

        return;
    }


    const question =
        input.value.trim();


    if (!question) {

        input.focus();

        return;
    }


    if (button) {

        button.disabled = true;

        button.textContent =
            "Thinking…";
    }


    if (status) {

        status.textContent =
            "Analyzing current recovery data…";
    }


    if (response) {

        response.classList.add(
            "visible"
        );
    }


    if (responseText) {

        responseText.textContent =
            "Preparing grounded analysis…";
    }


    try {

        const res =
            await fetch(
                `${API_BASE}/ai/analyze`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {
                                question,

                                conversation: []
                            }
                        )
                }
            );


        const data =
            await res
                .json()
                .catch(
                    () => ({})
                );


        if (!res.ok) {

            throw new Error(
                data.detail ||
                data.error ||
                `AI request failed (${res.status})`
            );
        }


        const answer =
            data.answer ||
            data.response ||
            data.message ||
            data.analysis;


        if (!answer) {

            throw new Error(
                "The AI endpoint returned no answer."
            );
        }


        if (responseText) {

            responseText.textContent =
                answer;
        }


        if (status) {

            status.textContent =
                "Analysis generated from current recovery data";
        }


    } catch (error) {

        console.error(
            "Recovery AI error:",
            error
        );


        if (responseText) {

            responseText.textContent =
                "Unable to generate the AI analysis right now. " +
                error.message;
        }


        if (status) {

            status.textContent =
                "AI analysis unavailable";
        }


    } finally {

        if (button) {

            button.disabled = false;

            button.textContent =
                "Ask AI";
        }

    }
}


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        console.log(
            "Recovery AI Dashboard starting..."
        );


        // ----------------------------------------------------
        // SIDEBAR
        // ----------------------------------------------------

        setupSidebar();


        // ----------------------------------------------------
        // REFRESH BUTTON
        // ----------------------------------------------------
        //
        // The current index.html uses:
        // onclick="loadDashboard()"
        //
        // Keep compatibility with either implementation.
        // ----------------------------------------------------

        const refreshButton =
            document.getElementById(
                "refresh-button"
            );


        if (refreshButton) {

            refreshButton.addEventListener(
                "click",
                loadDashboard
            );
        }


        // ----------------------------------------------------
        // SEARCH
        // ----------------------------------------------------

        const searchInput =
            document.getElementById(
                "search"
            );


        if (searchInput) {

            searchInput.addEventListener(
                "input",
                filterTable
            );
        }


        // ----------------------------------------------------
        // AI FORM
        // ----------------------------------------------------

        const aiForm =
            document.getElementById(
                "ai-bar-form"
            );


        if (aiForm) {

            aiForm.addEventListener(
                "submit",
                askRecoveryAI
            );
        }


        // ----------------------------------------------------
        // INITIAL LOAD
        // ----------------------------------------------------

        loadDashboard();


        // ----------------------------------------------------
        // AUTO REFRESH
        // ----------------------------------------------------

        setInterval(
            loadDashboard,
            30000
        );

    }
);