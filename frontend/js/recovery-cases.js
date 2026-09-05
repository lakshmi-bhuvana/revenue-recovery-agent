document.addEventListener("DOMContentLoaded", () => {
    loadRecoveryCases();

    const refreshButton = document.getElementById("refresh-button");

    if (refreshButton) {
        refreshButton.addEventListener("click", loadRecoveryCases);
    }

    const searchInput = document.getElementById("case-search");

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            loadRecoveryCases(searchInput.value.trim());
        });
    }
});


async function loadRecoveryCases(search = "") {

    const table = document.getElementById("cases-table");

    if (table) {
        table.innerHTML = `
            <tr>
                <td colspan="9" class="loading">
                    Loading recovery cases...
                </td>
            </tr>
        `;
    }

    try {

        // IMPORTANT:
        // API maximum is 500, NOT 5000.
        const url = new URL(
            "/recovery-cases",
            window.location.origin
        );

        url.searchParams.set("limit", "500");

        if (search) {
            url.searchParams.set("search", search);
        }

        const response = await fetch(url, {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(
                `Recovery API returned ${response.status}`
            );
        }

        const data = await response.json();

        console.log("Recovery cases loaded:", data);

        renderCases(
            Array.isArray(data.cases)
                ? data.cases
                : []
        );

        // Load the REAL dashboard totals separately
        await loadDashboardSummary();

    } catch (error) {

        console.error("Recovery cases error:", error);

        if (table) {
            table.innerHTML = `
                <tr>
                    <td colspan="9" class="loading">
                        Failed to load recovery cases.
                    </td>
                </tr>
            `;
        }
    }
}


async function loadDashboardSummary() {

    try {

        const response = await fetch(
            "/dashboard-summary",
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                `Dashboard API returned ${response.status}`
            );
        }

        const data = await response.json();

        const totalCases =
            document.getElementById("total-cases");

        if (totalCases) {
            totalCases.textContent =
                Number(
                    data.at_risk_cases || 0
                ).toLocaleString("en-IN");
        }

        const highCases =
            document.getElementById("high-cases");

        if (highCases) {

            const highPriority =
                Array.isArray(
                    data.priority_distribution
                )
                    ? data.priority_distribution.find(
                          item => item.priority === "HIGH"
                      )
                    : null;

            highCases.textContent =
                Number(
                    highPriority?.cases || 0
                ).toLocaleString("en-IN");
        }

        const recoveredCases =
            document.getElementById("recovered-cases");

        if (recoveredCases) {
            recoveredCases.textContent =
                Number(
                    data.recovered_cases || 0
                ).toLocaleString("en-IN");
        }

        const moneyRecovered =
            document.getElementById("money-recovered");

        if (moneyRecovered) {
            moneyRecovered.textContent =
                formatCurrency(
                    data.actual_recovered_value
                );
        }

    } catch (error) {

        console.error(
            "Dashboard summary error:",
            error
        );

    }
}


function renderCases(cases) {

    const table =
        document.getElementById("cases-table");

    if (!table) {
        return;
    }

    if (!cases.length) {

        table.innerHTML = `
            <tr>
                <td colspan="9" class="loading">
                    No recovery cases found.
                </td>
            </tr>
        `;

        return;
    }

    table.innerHTML = cases.map(caseData => {

        const priority =
            String(
                caseData.priority || ""
            ).toUpperCase();

        const probability =
            Number(
                caseData.recovery_probability || 0
            ) * 100;

        const recovered =
            caseData.recovered === true ||
            caseData.recovered === 1;

        const transactionId =
            String(
                caseData.transaction_id || ""
            );

        const customerId =
            String(
                caseData.customer_id || ""
            );

        return `
            <tr>

                <td>
                    <a
                        class="transaction-link"
                        href="/recovery-case.html?transaction_id=${encodeURIComponent(transactionId)}&from=recovery-cases"
                        title="Open recovery case"
                    >
                        <strong>
                            ${escapeHtml(transactionId)}
                        </strong>
                    </a>
                </td>

                <td>
                    ${escapeHtml(customerId)}
                </td>

                <td>
                    ${formatCurrency(
                        caseData.transaction_amount
                    )}
                </td>

                <td>
                    <span class="priority-badge ${priority.toLowerCase()}">
                        ${escapeHtml(priority || "—")}
                    </span>
                </td>

                <td>
                    ${probability.toFixed(1)}%
                </td>

                <td>
                    ${formatStrategy(caseData.strategy)}
                </td>

                <td>
                    ${formatAction(caseData.recovery_action)}
                </td>

                <td>
                    ${recovered ? "✓ Yes" : "✕ No"}
                </td>

                <td>
                    ${formatCurrency(
                        caseData.expected_recovery_value
                    )}
                </td>

            </tr>
        `;

    }).join("");
}


function formatCurrency(value) {

    return "₹" + Number(value || 0).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

}


function formatStrategy(strategy) {

    if (!strategy) {
        return "—";
    }

    return String(strategy)
        .replace(/_/g, " ")
        .replace(/\b\w/g, letter => letter.toUpperCase());

}


function formatAction(action) {

    if (!action) {
        return "—";
    }

    return String(action)
        .replace(/_/g, " ")
        .replace(/\b\w/g, letter => letter.toUpperCase());

}


function escapeHtml(value) {

    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}