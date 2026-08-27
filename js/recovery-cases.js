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

        // Changed from 5000 to 500
        url.searchParams.set("limit", "500");

        if (search) {
            url.searchParams.set("search", search);
        }

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(
                `Recovery API returned ${response.status}`
            );
        }

        const data = await response.json();

        console.log("Recovery cases loaded:", data);

        renderCases(data.cases || []);

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

        const response = await fetch("/dashboard-summary");

        if (!response.ok) {
            throw new Error(
                `Dashboard API returned ${response.status}`
            );
        }

        const data = await response.json();

        document.getElementById("total-cases").textContent =
            Number(data.at_risk_cases).toLocaleString();

        document.getElementById("high-cases").textContent =
            Number(
                data.priority_distribution.find(
                    item => item.priority === "HIGH"
                )?.cases || 0
            ).toLocaleString();

        document.getElementById("recovered-cases").textContent =
            Number(data.recovered_cases).toLocaleString();

        document.getElementById("money-recovered").textContent =
            formatCurrency(data.actual_recovered_value);

    } catch (error) {

        console.error("Dashboard summary error:", error);

    }
}


function renderCases(cases) {

    const table = document.getElementById("cases-table");

    if (!table) {
        return;
    }

    if (cases.length === 0) {

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
            String(caseData.priority || "").toUpperCase();

        const probability =
            Number(caseData.recovery_probability || 0) * 100;

        const recovered =
            caseData.recovered === true;

        return `
            <tr>

                <td>
                    <strong>
                        ${escapeHtml(caseData.transaction_id)}
                    </strong>
                </td>

                <td>
                    ${escapeHtml(caseData.customer_id)}
                </td>

                <td>
                    ${formatCurrency(caseData.transaction_amount)}
                </td>

                <td>
                    <span class="priority-badge ${priority.toLowerCase()}">
                        ${escapeHtml(priority)}
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