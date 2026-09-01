
// ============================================================
// REVENUE RECOVERY AI
// MAIN DASHBOARD JAVASCRIPT
// ============================================================

const API_BASE = "";

let dashboardLoading = false;

let aiConversation = [];

try {
    const savedConversation = localStorage.getItem(
        "recoveryAIConversation"
    );

    const parsed = savedConversation
        ? JSON.parse(savedConversation)
        : [];

    aiConversation = Array.isArray(parsed)
        ? parsed.slice(-40)
        : [];
} catch (error) {
    console.warn(
        "Could not restore AI conversation:",
        error
    );

    aiConversation = [];
}


// ============================================================
// HELPERS
// ============================================================

function esc(value) {

    const d = document.createElement("div");

    d.textContent =
        value === null ||
        value === undefined
            ? ""
            : String(value);

    return d.innerHTML;
}


function money(value) {

    return new Intl.NumberFormat(
        "en-IN",
        {
            style: "currency",
            currency: "INR",
            maximumFractionDigits: 2
        }
    ).format(
        Number(value || 0)
    );
}


function number(value) {

    return Number(
        value || 0
    ).toLocaleString(
        "en-IN"
    );
}


function pct(
    value,
    fromFraction = true
) {

    const n =
        Number(value || 0);

    return (
        (fromFraction
            ? n * 100
            : n
        ).toFixed(2)
        + "%"
    );
}


function text(id) {

    return (
        document
            .getElementById(id)
            ?.textContent
            ?.trim()
        || "—"
    );
}


function set(
    id,
    value
) {

    const el =
        document.getElementById(id);

    if (el) {
        el.textContent = value;
    }
}


// ============================================================
// SIDEBAR
// ============================================================

function setupSidebar() {

    const app =
        document.getElementById(
            "app"
        );

    const button =
        document.getElementById(
            "sidebar-toggle"
        );

    if (!app || !button) {
        return;
    }


    // Restore saved state
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


    function updateToggle() {

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

        button.title =
            collapsed
                ? "Expand sidebar"
                : "Collapse sidebar";

        button.setAttribute(
            "aria-label",
            collapsed
                ? "Expand sidebar"
                : "Collapse sidebar"
        );
    }


    if (
        button.dataset
            .sidebarBound !== "true"
    ) {

        button.addEventListener(
            "click",
            function () {

                app.classList.toggle(
                    "sidebar-collapsed"
                );

                const collapsed =
                    app.classList.contains(
                        "sidebar-collapsed"
                    );

                localStorage.setItem(
                    "sidebarCollapsed",
                    collapsed
                        ? "true"
                        : "false"
                );

                updateToggle();
            }
        );

        button.dataset.sidebarBound =
            "true";
    }


    updateToggle();
}


// ============================================================
// PRIORITY DONUT
// ============================================================

function renderPriorityChart(
    high,
    medium,
    low
) {

    const donut =
        document.getElementById(
            "priority-chart"
        );

    if (!donut) {
        return;
    }


    const total =
        Number(high || 0)
        + Number(medium || 0)
        + Number(low || 0);


    if (total <= 0) {

        donut.style.background =
            "#e2e8f0";

        set(
            "priority-total",
            "0"
        );

        return;
    }


    const highPercent =
        high / total * 100;

    const mediumPercent =
        medium / total * 100;

    const mediumEnd =
        highPercent
        + mediumPercent;


    donut.style.background =
        `conic-gradient(
            #2563eb 0 ${highPercent}%,
            #f59e0b ${highPercent}% ${mediumEnd}%,
            #cbd5e1 ${mediumEnd}% 100%
        )`;


    set(
        "priority-total",
        number(total)
    );
}


// ============================================================
// MAIN DASHBOARD METRICS
// ============================================================

function updateMetrics(
    data
) {

    const totalRisk =
        data.total_transaction_value ??
        data.total_risk ??
        data.total_at_risk ??
        0;

    const expectedRecovery =
        data.expected_recovery_value ??
        data.expected_recovery ??
        0;

    const recoveryRate =
        data.recovery_rate ??
        0;

    const highPriorityCases =
        data.high_priority_cases ??
        (
            data.priority_distribution || []
        ).find(
            item =>
                String(
                    item.priority
                ).toUpperCase()
                === "HIGH"
        )?.cases ??
        0;


    set(
        "total-risk",
        money(totalRisk)
    );

    set(
        "expected-recovery",
        money(expectedRecovery)
    );

    set(
        "recovery-rate",
        pct(
            recoveryRate,
            false
        )
    );

    set(
        "high-priority",
        number(highPriorityCases)
    );
}


// ============================================================
// OVERALL PERFORMANCE
// ============================================================

function updateOverall(
    data
) {

    const recovered =
        data.recovered_cases ??
        data.recovered_transactions ??
        data.total_recovered_cases ??
        0;


    const total =
        data.total_transactions ??
        data.total_dataset_cases ??
        data.total_cases ??
        0;


    const totalValue =
        data.total_transaction_value ??
        data.total_value ??
        0;


    const moneyRecovered =
        data.actual_recovered_value ??
        data.money_recovered ??
        data.total_money_recovered ??
        0;


    const recoveryRate =
        data.overall_recovery_rate ??
        data.recovery_rate ??
        (
            total
                ? recovered / total * 100
                : 0
        );


    const unrecovered =
        data.unrecovered_cases ??
        Math.max(
            0,
            total - recovered
        );


    const valueRate =
        data.recovery_value_rate ??
        (
            totalValue
                ? moneyRecovered
                    / totalValue
                    * 100
                : 0
        );


    const customers =
        data.total_dataset_customers ??
        data.total_customers ??
        data.customers ??
        0;


    set(
        "total-transactions",
        number(total)
    );

    set(
        "total-transaction-value",
        money(totalValue)
    );

    set(
        "overall-recovered-cases",
        number(recovered)
    );

    set(
        "overall-money-recovered",
        money(moneyRecovered)
    );

    set(
        "overall-recovery-rate",
        pct(
            recoveryRate,
            false
        )
    );

    set(
        "overall-unrecovered-cases",
        number(unrecovered)
    );

    set(
        "recovery-value-rate",
        pct(
            valueRate,
            false
        )
    );

    set(
        "overall-customers",
        number(customers)
    );
}


// ============================================================
// STRATEGY DISTRIBUTION
// ============================================================

function updateStrategies(
    data
) {

    const distribution =
        Array.isArray(
            data.strategy_distribution
        )
            ? data.strategy_distribution
            : [];


    function getCount(
        strategyName
    ) {

        const item =
            distribution.find(
                entry =>
                    String(
                        entry.strategy || ""
                    ).toLowerCase()
                    === strategyName
            );

        return number(
            item?.cases || 0
        );
    }


    set(
        "aggressive-count",
        getCount(
            "aggressive_recovery"
        )
    );

    set(
        "assisted-count",
        getCount(
            "assisted_recovery"
        )
    );

    set(
        "standard-count",
        getCount(
            "standard_recovery"
        )
    );

    set(
        "low-cost-count",
        getCount(
            "low_cost_recovery"
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
        Array.isArray(
            data.priority_distribution
        )
            ? data.priority_distribution
            : [];


    const high =
        Number(
            distribution.find(
                item =>
                    String(
                        item.priority || ""
                    ).toUpperCase()
                    === "HIGH"
            )?.cases || 0
        );


    const medium =
        Number(
            distribution.find(
                item =>
                    String(
                        item.priority || ""
                    ).toUpperCase()
                    === "MEDIUM"
            )?.cases || 0
        );


    const low =
        Number(
            distribution.find(
                item =>
                    String(
                        item.priority || ""
                    ).toUpperCase()
                    === "LOW"
            )?.cases || 0
        );


    set(
        "high-legend",
        `High Priority (${number(high)})`
    );

    set(
        "medium-legend",
        `Medium Priority (${number(medium)})`
    );

    set(
        "low-legend",
        `Low Priority (${number(low)})`
    );


    renderPriorityChart(
        high,
        medium,
        low
    );
}


// ============================================================
// FORMAT STRATEGY
// ============================================================

function formatStrategy(
    value
) {

    if (!value) {
        return "—";
    }

    return String(value)
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
// TOP RECOVERY OPPORTUNITIES
// ============================================================

function updateOpportunities(opportunities) {

    const body =
        document.getElementById(
            "opportunity-table"
        );

    if (!body) return;


    if (
        !Array.isArray(opportunities)
        || !opportunities.length
    ) {

        body.innerHTML = `
            <tr>
                <td
                    colspan="8"
                    class="loading"
                >
                    No recovery opportunities found.
                </td>
            </tr>
        `;

        return;
    }


    body.innerHTML =
        opportunities
            .map(
                item => {

                    const priority =
                        String(
                            item.priority || "LOW"
                        ).toUpperCase();


                    const transactionId =
                        String(
                            item.transaction_id || ""
                        );


                    const transactionUrl =
                        `/recovery-case.html?transaction_id=${encodeURIComponent(
                            transactionId
                        )}`;


                    return `
                        <tr>

                            <!-- Transaction -->
                            <td>
                                <a
                                    class="case-link opportunity-transaction-link"
                                    href="${transactionUrl}"
                                >
                                    <strong>
                                        ${esc(transactionId)}
                                    </strong>
                                </a>

                                <div class="opportunity-customer">
                                    ${esc(
                                        item.customer_id || "—"
                                    )}
                                </div>
                            </td>


                            <!-- Amount -->
                            <td class="amount">
                                ${money(
                                    item.transaction_amount
                                )}
                            </td>


                            <!-- Probability -->
                            <td class="probability">
                                ${pct(
                                    item.recovery_probability
                                )}
                            </td>


                            <!-- Priority -->
                            <td>
                                <a
                                    class="opportunity-priority-link"
                                    href="${transactionUrl}"
                                >
                                    <span
                                        class="badge badge-${esc(
                                            priority.toLowerCase()
                                        )}"
                                    >
                                        ${esc(priority)}
                                    </span>
                                </a>
                            </td>


                            <!-- Strategy -->
                            <td>
                                ${esc(
                                    formatStrategy(
                                        item.strategy
                                    )
                                )}
                            </td>


                            <!-- Channel -->
                            <td>
                                ${esc(
                                    item.recommended_channel
                                    || "—"
                                )}
                            </td>


                            <!-- Expected Recovery -->
                            <td class="amount">
                                <a
                                    class="opportunity-value-link"
                                    href="${transactionUrl}"
                                >
                                    ${money(
                                        item.expected_recovery_value
                                    )}
                                </a>
                            </td>


                            <!-- Action -->
                            <td>
                                <a
                                    class="view-btn"
                                    href="${transactionUrl}"
                                >
                                    View Case
                                </a>
                            </td>

                        </tr>
                    `;
                }
            )
            .join("");
}


// ============================================================
// API HELPER
// ============================================================

async function fetchJson(
    url,
    options = {}
) {

    const response =
        await fetch(
            url,
            {
                cache: "no-store",
                ...options
            }
        );


    let data = {};

    try {

        data =
            await response.json();

    } catch (_) {

        data = {};
    }


    if (!response.ok) {

        throw new Error(
            data.detail
            || data.message
            || `Request failed (${response.status})`
        );
    }


    return data;
}


// ============================================================
// LOAD DASHBOARD
// ============================================================

async function loadDashboard() {

    if (dashboardLoading) {
        return;
    }


    dashboardLoading = true;


    const live =
        document.getElementById(
            "live-text"
        );


    if (live) {
        live.textContent =
            "Updating…";
    }


    try {

        // ----------------------------------------------------
        // PRIMARY DASHBOARD SUMMARY
        // ----------------------------------------------------

        const summary =
            await fetchJson(
                `${API_BASE}/dashboard-summary`
            );


        updateMetrics(
            summary
        );

        updateOverall(
            summary
        );

        updatePriority(
            summary
        );

        updateStrategies(
            summary
        );


        if (live) {
            live.textContent =
                "Live";
        }

    } catch (error) {

        console.error(
            "Dashboard summary error:",
            error
        );


        if (live) {
            live.textContent =
                "API Error";
        }
    }


    try {

        // ----------------------------------------------------
        // DATASET-WIDE PERFORMANCE
        // ----------------------------------------------------

        const overall =
            await fetchJson(
                `${API_BASE}/overall-metrics`
            );


        updateOverall(
            overall
        );

    } catch (error) {

        console.warn(
            "Overall metrics unavailable. Summary values remain visible.",
            error
        );
    }


    try {

        // ----------------------------------------------------
        // TOP OPPORTUNITIES
        // ----------------------------------------------------

        const opportunities =
            await fetchJson(
                `${API_BASE}/top-opportunities?limit=10`
            );


        updateOpportunities(
            opportunities
        );

    } catch (error) {

        console.warn(
            "Top opportunities unavailable:",
            error
        );
    }


    dashboardLoading = false;
}


// ============================================================
// AI CONVERSATION
// ============================================================

function saveAIConversation() {

    aiConversation =
        aiConversation.slice(-40);

    localStorage.setItem(
        "recoveryAIConversation",
        JSON.stringify(
            aiConversation
        )
    );
}


function renderAI() {

    const chat =
        document.getElementById(
            "ai-chat"
        );

    if (!chat) {
        return;
    }


    if (!aiConversation.length) {

        chat.innerHTML = `
            <div class="chat-empty">
                Ask a question about revenue risk,
                priorities, recovery strategy,
                customers, or agent decisions.
            </div>
        `;

        return;
    }


    chat.innerHTML =
        aiConversation
            .map(
                message => {

                    const role =
                        message.role === "user"
                            ? "chat-user"
                            : "chat-assistant";


                    return `
                        <div
                            class="chat-msg ${role}"
                        >
                            ${esc(
                                message.content
                            )}
                        </div>
                    `;
                }
            )
            .join("");


    // Keep newest message visible
    chat.scrollTop =
        chat.scrollHeight;
}


// ============================================================
// ASK RECOVERY AI
// ============================================================

async function askRecoveryAI() {

    const input =
        document.getElementById(
            "ai-question"
        );


    const button =
        document.getElementById(
            "ai-ask-button"
        );


    const status =
        document.getElementById(
            "ai-status"
        );


    if (!input || !button) {
        return;
    }


    const question =
        input.value.trim();


    if (!question) {

        input.focus();

        return;
    }


    // --------------------------------------------------------
    // ADD USER MESSAGE
    // --------------------------------------------------------

    aiConversation.push(
        {
            role: "user",
            content: question
        }
    );


    saveAIConversation();

    renderAI();


    input.value = "";

    button.disabled = true;


    if (status) {
        status.textContent =
            "Thinking…";
    }


    try {

        const data =
            await fetchJson(
                "/ai/analyze",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(
                        {
                            question,

                            // Send the recent complete
                            // conversation so follow-up
                            // questions remain contextual.
                            conversation:
                                aiConversation.slice(
                                    -40
                                ),

                            context: {

                                revenue_at_risk:
                                    text(
                                        "total-risk"
                                    ),

                                expected_recovery:
                                    text(
                                        "expected-recovery"
                                    ),

                                recovery_rate:
                                    text(
                                        "recovery-rate"
                                    ),

                                high_priority_cases:
                                    text(
                                        "high-priority"
                                    ),

                                total_transactions:
                                    text(
                                        "total-transactions"
                                    ),

                                recovered_cases:
                                    text(
                                        "overall-recovered-cases"
                                    ),

                                unrecovered_cases:
                                    text(
                                        "overall-unrecovered-cases"
                                    ),

                                customers:
                                    text(
                                        "overall-customers"
                                    ),

                                page:
                                    "dashboard"
                            }
                        }
                    )
                }
            );


        const answer =
            data.answer
            || data.response
            || data.message
            || data.analysis
            || "I could not generate an answer.";


        aiConversation.push(
            {
                role: "assistant",
                content: answer
            }
        );


        saveAIConversation();

        renderAI();


        if (status) {
            status.textContent =
                "Online";
        }

    } catch (error) {

        console.error(
            "Recovery AI error:",
            error
        );


        aiConversation.push(
            {
                role: "assistant",

                content:
                    `I couldn't reach the Recovery AI service: ${error.message}`
            }
        );


        saveAIConversation();

        renderAI();


        if (status) {
            status.textContent =
                "Connection error";
        }

    } finally {

        button.disabled = false;

        input.focus();
    }
}


// ============================================================
// NEW AI CHAT
// ============================================================

function newAIChat() {

    aiConversation = [];

    localStorage.removeItem(
        "recoveryAIConversation"
    );

    renderAI();


    document
        .getElementById(
            "ai-question"
        )
        ?.focus();
}


// ============================================================
// QUICK AI QUESTIONS
// ============================================================

function useAIQuestion(
    question
) {

    const input =
        document.getElementById(
            "ai-question"
        );


    if (!input) {
        return;
    }


    input.value =
        question;


    input.focus();
}


// ============================================================
// PUBLIC FUNCTIONS
// ============================================================

window.loadDashboard =
    loadDashboard;

window.askRecoveryAI =
    askRecoveryAI;

window.newAIChat =
    newAIChat;

window.useAIQuestion =
    useAIQuestion;


// ============================================================
// INITIALIZATION
// ============================================================

function initializeDashboard() {

    setupSidebar();

    renderAI();


    const refreshButton =
        document.getElementById(
            "refresh-button"
        );


    if (
        refreshButton
        && refreshButton.dataset
            .dashboardBound !== "true"
    ) {

        refreshButton.addEventListener(
            "click",
            loadDashboard
        );

        refreshButton.dataset
            .dashboardBound = "true";
    }


    const askButton =
        document.getElementById(
            "ai-ask-button"
        );


    if (
        askButton
        && askButton.dataset
            .aiBound !== "true"
    ) {

        askButton.addEventListener(
            "click",
            askRecoveryAI
        );

        askButton.dataset.aiBound =
            "true";
    }


    const questionInput =
        document.getElementById(
            "ai-question"
        );


    if (
        questionInput
        && questionInput.dataset
            .aiBound !== "true"
    ) {

        questionInput.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Enter"
                    && !event.shiftKey
                ) {

                    event.preventDefault();

                    askRecoveryAI();
                }
            }
        );


        questionInput.dataset.aiBound =
            "true";
    }


    // Initial dashboard load
    loadDashboard();


    // Auto refresh every 30 seconds
    setInterval(
        loadDashboard,
        30000
    );
}


// ============================================================
// START
// ============================================================

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeDashboard
    );

} else {

    initializeDashboard();
}
