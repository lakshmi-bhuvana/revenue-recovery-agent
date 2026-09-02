const money = value =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2
  }).format(
    Number(value || 0)
  );
const number = value =>
  Number(value || 0)
    .toLocaleString("en-IN");
const pct = value =>
  `${Number(value || 0).toFixed(2)}%`;
const esc = value => {
  const element =
    document.createElement("div");
  element.textContent =
    value == null
      ? ""
      : String(value);
  return element.innerHTML;
};
function set(id, value) {
  const element =
    document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}
function formatScenario(value) {
  return String(value || "—")
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      character =>
        character.toUpperCase()
    );
}
function formatAction(value) {
  return String(value || "—")
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      character =>
        character.toUpperCase()
    );
}
/* ============================================================
   SIDEBAR
   ============================================================ */
function setupSidebar() {
  const app =
    document.getElementById("app");
  const button =
    document.getElementById(
      "sidebar-toggle"
    );
  if (!app || !button) {
    return;
  }
  const savedState =
    localStorage.getItem(
      "sidebarCollapsed"
    );
  if (savedState === "true") {
    app.classList.add(
      "sidebar-collapsed"
    );
  }
  function updateSidebar() {
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
  button.addEventListener(
    "click",
    event => {
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
      updateSidebar();
    }
  );
  updateSidebar();
}
/* ============================================================
   API
   ============================================================ */
async function getJSON(
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
      data.detail ||
      `Request failed (${response.status})`
    );
  }
  return data;
}
/* ============================================================
   GLOBAL STATE
   ============================================================ */
let latestSummary = null;
let currentPage = 1;
const PAGE_SIZE = 25;
/* ============================================================
   FILTERS
   ============================================================ */
function getFilters() {
  return {
    search:
      document
        .getElementById(
          "agent-execution-search"
        )
        ?.value
        .trim() || "",
    scenario:
      document
        .getElementById(
          "agent-scenario-filter"
        )
        ?.value || "",
    result:
      document
        .getElementById(
          "agent-result-filter"
        )
        ?.value || ""
  };
}
/* ============================================================
   SUMMARY
   ============================================================ */
function renderSummary(data) {
  latestSummary =
    data || {};
  set(
    "agent-executions",
    number(
      data?.total_executions
    )
  );
  set(
    "agent-recovered",
    number(
      data?.recovered_executions
    )
  );
  set(
    "agent-rate",
    pct(
      data?.agent_recovery_rate
    )
  );
  set(
    "agent-money",
    money(
      data?.money_recovered
    )
  );
  set(
    "agent-attempts",
    Number(
      data?.average_attempts_per_execution ||
      0
    ).toFixed(2)
  );
  set(
    "agent-escalations",
    number(
      data?.escalations
    )
  );
  const grid =
    document.getElementById(
      "scenario-grid"
    );
  if (!grid) {
    return;
  }
  const scenarios =
    Array.isArray(
      data?.scenario_performance
    )
      ? data.scenario_performance
      : [];
  if (!scenarios.length) {
    grid.innerHTML =
      `
        <div class="audit-empty">
          No persisted scenario executions yet.
        </div>
      `;
    return;
  }
  grid.innerHTML =
    scenarios
      .map(
        item => `
          <div class="scenario-card">
            <strong>
              ${esc(
                formatScenario(
                  item.scenario
                )
              )}
            </strong>
            <div class="scenario-meta">
              <span>
                ${number(
                  item.executions
                )}
                executions
              </span>
              <span>
                ${pct(
                  item.recovery_rate
                )}
              </span>
            </div>
            <div class="scenario-money">
              ${money(
                item.money_recovered
              )}
            </div>
          </div>
        `
      )
      .join("");
}
/* ============================================================
   LOAD EXECUTIONS
   ============================================================ */
async function loadExecutions() {
  const body =
    document.getElementById(
      "recent-body"
    );
  if (!body) {
    return;
  }
  const filters =
    getFilters();
  const params =
    new URLSearchParams();
  params.set(
    "page",
    String(currentPage)
  );
  params.set(
    "page_size",
    String(PAGE_SIZE)
  );
  if (filters.search) {
    params.set(
      "search",
      filters.search
    );
  }
  if (filters.scenario) {
    params.set(
      "scenario",
      filters.scenario
    );
  }
  if (filters.result) {
    params.set(
      "result",
      filters.result
    );
  }
  body.innerHTML =
    `
      <tr>
        <td
          colspan="10"
          class="loading"
        >
          Loading agent executions…
        </td>
      </tr>
    `;
  try {
    const data =
      await getJSON(
        `/recovery-agent/executions?${params.toString()}`
      );
    renderExecutionCount(
      data
    );
    renderExecutions(
      Array.isArray(
        data?.executions
      )
        ? data.executions
        : []
    );
    renderPagination(
      data
    );
  } catch (error) {
    console.error(
      "Recovery Agent execution error:",
      error
    );
    body.innerHTML =
      `
        <tr>
          <td
            colspan="10"
            class="loading"
          >
            Unable to load executions:
            ${esc(
              error.message
            )}
          </td>
        </tr>
      `;
    renderExecutionCount({
      total: 0,
      page: 1,
      page_size: PAGE_SIZE,
      returned: 0,
      total_pages: 1
    });
    renderPagination({
      total: 0,
      page: 1,
      page_size: PAGE_SIZE,
      returned: 0,
      total_pages: 1,
      has_previous: false,
      has_next: false
    });
  }
}
/* ============================================================
   EXECUTION COUNT
   ============================================================ */
function renderExecutionCount(
  data
) {
  const total =
    Number(
      data?.total ?? 0
    );
  const page =
    Number(
      data?.page ?? 1
    );
  const pageSize =
    Number(
      data?.page_size ??
      PAGE_SIZE
    );
  const returned =
    Number(
      data?.returned ?? 0
    );
  if (total === 0) {
    set(
      "execution-count",
      "Showing 0 of 0 executions"
    );
    return;
  }
  const start =
    (
      (page - 1) *
      pageSize
    ) + 1;
  const end =
    Math.min(
      start +
      returned -
      1,
      total
    );
  set(
    "execution-count",
    `Showing ${number(start)}–${number(end)} of ${number(total)} executions`
  );
}
/* ============================================================
   EXECUTION TABLE
   ============================================================ */
function renderExecutions(
  executions
) {
  const body =
    document.getElementById(
      "recent-body"
    );
  if (!body) {
    return;
  }
  if (
    !Array.isArray(executions) ||
    executions.length === 0
  ) {
    body.innerHTML = `
      <tr>
        <td
          colspan="10"
          class="loading"
        >
          No matching agent executions found.
        </td>
      </tr>
    `;
    return;
  }
  body.innerHTML =
    executions
      .map(
        item => {
          const tx =
            String(
              item.transaction_id ||
              ""
            );
          return `
            <tr>
              <td class="execution-tx">
                <a
                  class="case-link"
                  href="/recovery-case.html?transaction_id=${encodeURIComponent(tx)}"
                >
                  <strong>
                    ${esc(tx)}
                  </strong>
                </a>
              </td>
              <td>
                ${esc(
                  item.customer_id ||
                  "—"
                )}
              </td>
              <td>
                ${esc(
                  formatScenario(
                    item.scenario
                  )
                )}
              </td>
              <td>
                ${esc(
                  item.diagnosis ||
                  "—"
                )}
              </td>
              <td>
                ${esc(
                  formatAction(
                    item.recovery_action
                  )
                )}
              </td>
              <td>
                ${esc(
                  item.recommended_channel ||
                  "—"
                )}
              </td>
              <td>
                <span
                  class="${
                    item.recovered
                      ? "badge badge-success"
                      : "badge badge-muted"
                  }"
                >
                  ${
                    item.recovered
                      ? "Recovered"
                      : "Not Recovered"
                  }
                </span>
              </td>
              <td class="amount">
                ${money(
                  item.money_recovered
                )}
              </td>
              <td>
                ${number(
                  item.attempt_count
                )}
              </td>
              <td>
                ${esc(
                  item.stopping_reason ||
                  "—"
                )}
              </td>
            </tr>
          `;
        }
      )
      .join("");
}
function renderPagination(
  data
) {
  const container =
    document.getElementById(
      "agent-pagination"
    );
  if (!container) {
    return;
  }
  const total =
    Number(
      data?.total ?? 0
    );
  const current =
    Number(
      data?.page ?? 1
    );
  const totalPages =
    Math.max(
      1,
      Number(
        data?.total_pages ?? 1
      )
    );
  if (total === 0) {
    container.innerHTML =
      "";
    return;
  }
  const pages = [];
  const addPage =
    page => {
      pages.push(`
        <button
          type="button"
          class="pagination-button ${
            page === current
              ? "active"
              : ""
          }"
          data-page="${page}"
        >
          ${page}
        </button>
      `);
    };
  if (totalPages <= 7) {
    for (
      let page = 1;
      page <= totalPages;
      page++
    ) {
      addPage(page);
    }
  } else {
    addPage(1);
    if (current > 4) {
      pages.push(
        '<span class="pagination-dots">…</span>'
      );
    }
    const start =
      Math.max(
        2,
        current - 1
      );
    const end =
      Math.min(
        totalPages - 1,
        current + 1
      );
    for (
      let page = start;
      page <= end;
      page++
    ) {
      addPage(page);
    }
    if (
      current <
      totalPages - 3
    ) {
      pages.push(
        '<span class="pagination-dots">…</span>'
      );
    }
    addPage(
      totalPages
    );
  }
  container.innerHTML =
    `
      <div class="pagination">
        <button
          type="button"
          id="agent-prev"
          class="pagination-button pagination-nav"
          ${
            current <= 1
              ? "disabled"
              : ""
          }
        >
          ← Previous
        </button>
        <div class="pagination-pages">
          ${pages.join("")}
        </div>
        <button
          type="button"
          id="agent-next"
          class="pagination-button pagination-nav"
          ${
            current >= totalPages
              ? "disabled"
              : ""
          }
        >
          Next →
        </button>
      </div>
    `;
  container
    .querySelectorAll(
      "[data-page]"
    )
    .forEach(
      button => {
        button.addEventListener(
          "click",
          () => {
            const target =
              Number(
                button.dataset.page
              );
            if (
              !Number.isFinite(
                target
              )
            ) {
              return;
            }
            if (
              target ===
              currentPage
            ) {
              return;
            }
            currentPage =
              target;
            loadExecutions();
            document
              .getElementById(
                "execution-history"
              )
              ?.scrollIntoView({
                behavior: "smooth",
                block: "start"
              });
          }
        );
      }
    );
  document
    .getElementById(
      "agent-prev"
    )
    ?.addEventListener(
      "click",
      () => {
        if (
          currentPage <= 1
        ) {
          return;
        }
        currentPage -= 1;
        loadExecutions();
      }
    );
  document
    .getElementById(
      "agent-next"
    )
    ?.addEventListener(
      "click",
      () => {
        if (
          currentPage >=
          totalPages
        ) {
          return;
        }
        currentPage += 1;
        loadExecutions();
      }
    );
}
/* ============================================================
   LOAD TRANSACTION AUDIT
   ============================================================ */
async function loadAudit(
  tx
) {
  const box =
    document.getElementById(
      "audit-content"
    );
  if (!box) {
    return;
  }
  box.innerHTML =
    `
      <div class="audit-empty">
        Loading transaction details…
      </div>
    `;
  try {
    const data =
      await getJSON(
        `/recovery-agent/audit/${encodeURIComponent(tx)}`
      );
    const agent =
      data?.agent_result ||
      {};
    const diagnosis =
      agent?.diagnosis ||
      {};
    const score =
      agent?.score ||
      {};
    const action =
      agent?.action ||
      {};
    const execution =
      agent?.execution ||
      {};
    const stopping =
      agent?.stopping ||
      {};
    const escalation =
      agent?.escalation ||
      {};
    const policy =
      agent?.policy ||
      {};
    const timeline =
      Array.isArray(
        data?.timeline
      )
        ? data.timeline
        : [];
    const probability =
      (
        Number(
          score?.recovery_probability ||
          0
        ) * 100
      ).toFixed(2);
    const priorityScore =
      (
        Number(
          score?.priority_score ||
          0
        ) * 100
      ).toFixed(2);
    const recovered =
      Boolean(
        execution?.recovered
      );
    const moneyRecovered =
      money(
        execution?.money_recovered
      );
    const timelineHtml =
      timeline
        .map(
          (item, index) => {
            const stage =
              String(
                item?.stage ||
                ""
              );
            const completed =
              item?.status ===
                "completed" ||
              item?.status ===
                "recovered" ||
              item?.status ===
                "stopped" ||
              item?.status ===
                "simulated";
            return `
              <div
                class="agent-timeline-item"
              >
                <div
                  class="agent-timeline-marker ${
                    completed
                      ? "completed"
                      : ""
                  }"
                >
                  ${
                    completed
                      ? "✓"
                      : index + 1
                  }
                </div>
                <div
                  class="agent-timeline-content"
                >
                  <div
                    class="agent-timeline-stage"
                  >
                    ${esc(stage)}
                  </div>
                  <div
                    class="agent-timeline-detail"
                  >
                    ${esc(
                      item?.detail ||
                      item?.stopping_reason ||
                      ""
                    )}
                  </div>
                </div>
              </div>
            `;
          }
        )
        .join("");
    box.innerHTML =
      `
        <!-- TRANSACTION HEADER -->
        <div
          class="transaction-detail-header"
        >
          <div>
            <div
              class="transaction-detail-id"
            >
              ${esc(
                data?.transaction_id ||
                tx
              )}
            </div>
            <div
              class="transaction-detail-scenario"
            >
              ${esc(
                formatScenario(
                  agent?.scenario
                )
              )}
            </div>
          </div>
          <div
            class="${
              recovered
                ? "transaction-status recovered"
                : "transaction-status failed"
            }"
          >
            ${
              recovered
                ? "Recovered"
                : "Not Recovered"
            }
          </div>
        </div>
        <!-- CORE METRICS -->
        <div
          class="transaction-detail-grid"
        >
          <div
            class="transaction-detail-card primary"
          >
            <span>
              Money Recovered
            </span>
            <strong>
              ${moneyRecovered}
            </strong>
          </div>
          <div
            class="transaction-detail-card"
          >
            <span>
              Recovery Probability
            </span>
            <strong>
              ${probability}%
            </strong>
          </div>
          <div
            class="transaction-detail-card"
          >
            <span>
              Priority Score
            </span>
            <strong>
              ${priorityScore}%
            </strong>
          </div>
          <div
            class="transaction-detail-card"
          >
            <span>
              Attempts
            </span>
            <strong>
              ${Number(
                execution?.attempt_count ||
                0
              )}
            </strong>
          </div>
        </div>
        <!-- CASE ASSESSMENT -->
        <div
          class="transaction-detail-section"
        >
          <h4>
            Case Assessment
          </h4>
          <div
            class="transaction-info-grid"
          >
            <div>
              <span>
                Customer
              </span>
              <strong>
                ${esc(
                  agent?.customer_id ||
                  "—"
                )}
              </strong>
            </div>
            <div>
              <span>
                Diagnosis
              </span>
              <strong>
                ${esc(
                  formatAction(
                    diagnosis?.diagnosis
                  )
                )}
              </strong>
            </div>
            <div>
              <span>
                Priority
              </span>
              <strong>
                ${esc(
                  score?.priority ||
                  "LOW"
                )}
              </strong>
            </div>
            <div>
              <span>
                Transaction Amount
              </span>
              <strong>
                ${money(
                  agent?.transaction_amount ??
                  score?.transaction_amount ??
                  0
                )}
              </strong>
            </div>
            <div>
              <span>
                Customer Reliability
              </span>
              <strong>
                ${pct(
                  Number(
                    score?.customer_reliability ||
                    0
                  ) * 100
                )}
              </strong>
            </div>
            <div>
              <span>
                Contactability
              </span>
              <strong>
                ${pct(
                  Number(
                    score?.contactability ||
                    0
                  ) * 100
                )}
              </strong>
            </div>
            <div>
              <span>
                Recovery Action
              </span>
              <strong>
                ${esc(
                  formatAction(
                    action?.recovery_action
                  )
                )}
              </strong>
            </div>
            <div>
              <span>
                Channel
              </span>
              <strong>
                ${esc(
                  action?.channel ||
                  score?.recommended_channel ||
                  "—"
                )}
              </strong>
            </div>
          </div>
          <div
            class="transaction-diagnosis"
          >
            ${esc(
              diagnosis?.reason ||
              "No diagnosis explanation recorded."
            )}
          </div>
        </div>
        <!-- POLICY DECISION -->
        <div
          class="transaction-detail-section"
        >
          <h4>
            Agent Decision
          </h4>
          <div
            class="agent-decision-summary"
          >
            <div>
              <span>
                Selected Action
              </span>
              <strong>
                ${esc(
                  formatAction(
                    action?.recovery_action
                  )
                )}
              </strong>
            </div>
            <div>
              <span>
                Strategy
              </span>
              <strong>
                ${esc(
                  formatScenario(
                    action?.strategy
                  )
                )}
              </strong>
            </div>
            <div>
              <span>
                Channel
              </span>
              <strong>
                ${esc(
                  action?.channel ||
                  score?.recommended_channel ||
                  "—"
                )}
              </strong>
            </div>
            <div>
              <span>
                Policy
              </span>
              <strong>
                ${
                  policy?.allowed
                    ? "Allowed"
                    : "Blocked"
                }
              </strong>
            </div>
          </div>
          <div
            class="agent-decision-reason"
          >
            <strong>
              Why this action?
            </strong>
            <p>
              ${esc(
                policy?.reason ||
                "The action was selected by the bounded recovery policy."
              )}
            </p>
          </div>
        </div>
        <!-- EXECUTION -->
        <div
          class="transaction-detail-section"
        >
          <h4>
            Recovery Execution
          </h4>
          <div
            class="execution-result-box"
          >
            <div>
              <span>
                Execution Status
              </span>
              <strong>
                ${esc(
                  execution?.execution_status ||
                  "simulated"
                )}
              </strong>
            </div>
            <div>
              <span>
                Action
              </span>
              <strong>
                ${esc(
                  formatAction(
                    execution?.action ||
                    action?.recovery_action
                  )
                )}
              </strong>
            </div>
            <div>
              <span>
                Attempts
              </span>
              <strong>
                ${Number(
                  execution?.attempt_count ||
                  0
                )}
              </strong>
            </div>
            <div>
              <span>
                Result
              </span>
              <strong>
                ${
                  recovered
                    ? "Payment recovered"
                    : "Payment not recovered"
                }
              </strong>
            </div>
          </div>
          <div
            class="transaction-diagnosis"
          >
            ${esc(
              execution?.execution_detail ||
              "Recovery execution recorded."
            )}
          </div>
        </div>
        <!-- STOP / ESCALATION -->
        <div
          class="transaction-detail-section"
        >
          <h4>
            Stop / Escalation
          </h4>
          <div
            class="execution-result-box"
          >
            <div>
              <span>
                Stopping Reason
              </span>
              <strong>
                ${esc(
                  stopping?.reason ||
                  "—"
                )}
              </strong>
            </div>
            <div>
              <span>
                Stopped
              </span>
              <strong>
                ${
                  stopping?.stop
                    ? "Yes"
                    : "No"
                }
              </strong>
            </div>
            <div>
              <span>
                Escalated
              </span>
              <strong>
                ${
                  escalation?.escalate
                    ? "Yes"
                    : "No"
                }
              </strong>
            </div>
            <div>
              <span>
                Escalation Level
              </span>
              <strong>
                ${esc(
                  escalation?.escalation_level ||
                  "NONE"
                )}
              </strong>
            </div>
          </div>
        </div>
        <!-- TIMELINE -->
        <div
          class="transaction-detail-section"
        >
          <h4>
            Agent Timeline
          </h4>
          <div
            class="agent-timeline"
          >
            ${timelineHtml}
          </div>
        </div>
      `;
  } catch (error) {
    box.innerHTML =
      `
        <div class="audit-empty">
          Unable to load transaction details:
          ${esc(
            error.message
          )}
        </div>
      `;
    throw error;
  }
}
/* ============================================================
   AGENT DECISION LAYER
   ============================================================ */
async function renderDecisionLayer(
  tx
) {
  const box =
    document.getElementById(
      "decision-layer-content"
    );
  if (!box) {
    return;
  }
  box.innerHTML =
    `
      <div class="audit-empty">
        Loading agent judgment…
      </div>
    `;
  try {
    const data =
      await getJSON(
        `/recovery-agent/decision/${encodeURIComponent(tx)}`
      );
    const assessment =
      data?.assessment ||
      {};
    const decision =
      data?.decision ||
      {};
    const engagement =
      data?.customer_engagement ||
      {};
    const outcome =
      data?.outcome ||
      {};
    const nextStep =
      data?.next_step ||
      {};
    const candidates =
      Array.isArray(
        data?.candidate_actions
      )
        ? data.candidate_actions
        : [];
    const moneyRecovered =
      money(
        outcome?.money_recovered
      );
    const probability =
      (
        Number(
          assessment?.recovery_probability ||
          0
        ) * 100
      ).toFixed(2);
    const customerResponse =
      engagement?.response ||
      "No customer response recorded.";
    const candidateMarkup =
      candidates
        .map(
          item => {
            const selected =
              item?.status ===
              "selected";
            return `
              <div
                class="${
                  selected
                    ? "agent-candidate selected"
                    : "agent-candidate"
                }"
              >
                <div>
                  <strong>
                    ${esc(
                      formatAction(
                        item?.name
                      )
                    )}
                  </strong>
                  <p>
                    ${esc(
                      item?.reason ||
                      ""
                    )}
                  </p>
                </div>
                <span>
                  ${(
                    Number(
                      item?.suitability ||
                      0
                    ) * 100
                  ).toFixed(0)}%
                </span>
              </div>
            `;
          }
        )
        .join("");
    box.innerHTML =
      `
        <div
          class="agent-judgment-grid"
        >
          <div
            class="agent-judgment-stat"
          >
            <span>
              Recovery Probability
            </span>
            <strong>
              ${probability}%
            </strong>
          </div>
          <div
            class="agent-judgment-stat"
          >
            <span>
              Priority
            </span>
            <strong>
              ${esc(
                assessment?.priority ||
                "LOW"
              )}
            </strong>
          </div>
          <div
            class="agent-judgment-stat"
          >
            <span>
              Selected Action
            </span>
            <strong>
              ${esc(
                formatAction(
                  decision?.selected_action
                )
              )}
            </strong>
          </div>
          <div
            class="agent-judgment-stat"
          >
            <span>
              Attempts
            </span>
            <strong>
              ${Number(
                outcome?.attempt_count ||
                0
              )}
            </strong>
          </div>
        </div>
        <div
          class="agent-judgment-box"
        >
          <h4>
            Why did the agent choose this?
          </h4>
          <p>
            ${esc(
              decision?.why_selected ||
              "The bounded recovery policy selected this action."
            )}
          </p>
        </div>
        <div
          class="agent-judgment-box"
        >
          <h4>
            Candidate Recovery Paths
          </h4>
          <div
            class="agent-candidates"
          >
            ${candidateMarkup}
          </div>
        </div>
        <div
          class="agent-engagement-grid"
        >
          <div
            class="agent-judgment-box"
          >
            <h4>
              Simulated Customer Engagement
            </h4>
            <div
              class="agent-detail-row"
            >
              <span>
                Channel
              </span>
              <strong>
                ${esc(
                  engagement?.channel ||
                  "none"
                )}
              </strong>
            </div>
            <div
              class="agent-message"
            >
              ${esc(
                engagement?.message ||
                "No message recorded."
              )}
            </div>
            <div
              class="agent-detail-row"
            >
              <span>
                Delivery
              </span>
              <strong>
                ${esc(
                  engagement?.delivery_status ||
                  "simulated"
                )}
              </strong>
            </div>
          </div>
          <div
            class="agent-judgment-box"
          >
            <h4>
              Customer Response
            </h4>
            <p>
              ${esc(
                customerResponse
              )}
            </p>
            <div
              class="agent-detail-row"
            >
              <span>
                Money Recovered
              </span>
              <strong>
                ${moneyRecovered}
              </strong>
            </div>
          </div>
        </div>
        <div
          class="agent-recovery-loop"
        >
          <div>
            <span>
              Recovery Loop
            </span>
            <strong>
              ${
                nextStep?.stopped
                  ? "STOP"
                  : nextStep?.escalate
                    ? "ESCALATE"
                    : "CONTINUE"
              }
            </strong>
          </div>
          <div>
            Stopping reason:
            <strong>
              ${esc(
                nextStep?.stopping_reason ||
                "—"
              )}
            </strong>
          </div>
          <div>
            Escalation:
            <strong>
              ${
                nextStep?.escalate
                  ? esc(
                      nextStep?.escalation_level ||
                      "HUMAN_REVIEW"
                    )
                  : "No"
              }
            </strong>
          </div>
        </div>
      `;
  } catch (error) {
    box.innerHTML =
      `
        <div class="audit-empty">
          Unable to load agent judgment:
          ${esc(
            error.message
          )}
        </div>
      `;
  }
}
/* ============================================================
   REFRESH
   ============================================================ */
async function refresh() {
  const live =
    document.getElementById(
      "agent-live"
    );
  if (live) {
    live.textContent =
      "Updating…";
  }
  try {
    const summary =
      await getJSON(
        "/recovery-agent/summary"
      );
    renderSummary(
      summary
    );
    await loadExecutions();
    if (live) {
      live.textContent =
        "Agent Online";
    }
  } catch (error) {
    console.error(
      "Recovery Agent refresh error:",
      error
    );
    if (live) {
      live.textContent =
        "API Error";
    }
  }
}
/* ============================================================
   RUN DEMO BATCH
   ============================================================ */
async function runBatch() {
  const button =
    document.getElementById(
      "run-demo-batch"
    );
  const size =
    Number(
      document.getElementById(
        "batch-size"
      )?.value || 10
    );
  const status =
    document.getElementById(
      "batch-status"
    );
  const summaryBox =
    document.getElementById(
      "batch-summary"
    );
  if (!button || !status) {
    return;
  }
  button.disabled =
    true;
  button.textContent =
    "Running…";
  status.style.display =
    "block";
  status.textContent =
    `Selecting ${size} active recovery cases…`;
  try {
    const casesResponse =
      await getJSON(
        `/recovery-cases?limit=${encodeURIComponent(size)}`
      );
    const cases =
      Array.isArray(
        casesResponse?.cases
      )
        ? casesResponse.cases
        : [];
    const ids =
      cases
        .map(
          item =>
            item.transaction_id
        )
        .filter(
          Boolean
        )
        .slice(
          0,
          size
        );
    if (!ids.length) {
      throw new Error(
        "No active recovery cases are available for the demo batch."
      );
    }
    const before =
      await getJSON(
        "/recovery-agent/summary"
      );
    const result =
      await getJSON(
        "/recovery/run-batch",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json"
          },
          body:
            JSON.stringify({
              transaction_ids:
                ids
            })
        }
      );
    const after =
      await getJSON(
        "/recovery-agent/summary"
      );
    renderSummary(
      after
    );
    const newExecutions =
      Math.max(
        0,
        Number(
          after?.total_executions ||
          0
        ) -
        Number(
          before?.total_executions ||
          0
        )
      );
    const newRecovered =
      Math.max(
        0,
        Number(
          after?.recovered_executions ||
          0
        ) -
        Number(
          before?.recovered_executions ||
          0
        )
      );
    const newMoney =
      Math.max(
        0,
        Number(
          after?.money_recovered ||
          0
        ) -
        Number(
          before?.money_recovered ||
          0
        )
      );
    set(
      "batch-requested",
      number(
        result?.requested ??
        ids.length
      )
    );
    set(
      "batch-processed",
      number(
        result?.processed ??
        newExecutions
      )
    );
    set(
      "batch-new-recovered",
      number(
        newRecovered
      )
    );
    set(
      "batch-new-money",
      money(
        newMoney
      )
    );
    if (summaryBox) {
      summaryBox.style.display =
        "grid";
    }
    status.textContent =
      `Batch complete.
Selected: ${ids.length}
Requested: ${result?.requested ?? ids.length}
Processed: ${result?.processed ?? newExecutions}
New recovered: ${newRecovered}
New money recovered: ${money(newMoney)}`;
    currentPage =
      1;
    await loadExecutions();
  } catch (error) {
    status.textContent =
      `Batch error: ${error.message}`;
  } finally {
    button.disabled =
      false;
    button.textContent =
      "Run Agent Batch";
  }
}
/* ============================================================
   EXECUTION FILTER CONTROLS
   ============================================================ */
/* ============================================================
   ADAPTIVE RECOVERY LOOP
   Demonstration-only customer interaction layer.
   This does NOT claim that a real message was sent.
   ============================================================ */
let adaptiveTransaction = null;
let adaptiveTimeline = [];
function adaptiveSet(id, value) {
    const element =
        document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}
function adaptiveAddTimeline(stage, detail) {
    adaptiveTimeline.push({
        stage,
        detail
    });
    const container =
        document.getElementById(
            "adaptive-timeline"
        );
    if (!container) {
        return;
    }
    container.innerHTML =
        adaptiveTimeline
            .map(
                (item, index) => `
                    <div
                        style="
                            display:grid;
                            grid-template-columns:28px 1fr;
                            gap:10px;
                            align-items:start;
                        "
                    >
                        <div
                            style="
                                width:26px;
                                height:26px;
                                border-radius:50%;
                                display:flex;
                                align-items:center;
                                justify-content:center;
                                background:#ecfdf3;
                                border:1px solid #bbf7d0;
                                color:#15803d;
                                font-size:10px;
                                font-weight:800;
                            "
                        >
                            ${index + 1}
                        </div>
                        <div>
                            <div
                                style="
                                    color:#27364d;
                                    font-size:11px;
                                    font-weight:800;
                                "
                            >
                                ${esc(item.stage)}
                            </div>
                            <div
                                style="
                                    margin-top:3px;
                                    color:#7183a0;
                                    font-size:10px;
                                    line-height:1.55;
                                "
                            >
                                ${esc(item.detail)}
                            </div>
                        </div>
                    </div>
                `
            )
            .join("");
}
function adaptiveStartFromExecution(item) {
    adaptiveTransaction = item;
    adaptiveTimeline = [];
    adaptiveAddTimeline(
        "DETECT",
        "Revenue-risk transaction selected for adaptive recovery."
    );
    adaptiveAddTimeline(
        "DIAGNOSE",
        `${formatScenario(item?.scenario)} · ${
            item?.diagnosis ||
            "Recovery issue detected."
        }`
    );
    adaptiveAddTimeline(
        "PREDICT",
        `Recovery probability ${pct(
            item?.recovery_probability
        )}.`
    );
    adaptiveAddTimeline(
        "DECIDE",
        `${formatAction(
            item?.recovery_action
        )} selected on ${
            item?.recommended_channel ||
            "the recommended channel"
        }.`
    );
    adaptiveSet(
        "adaptive-state-title",
        "Awaiting Customer Response"
    );
    adaptiveSet(
        "adaptive-state-detail",
        `The agent has selected ${
            formatAction(
                item?.recovery_action
            )
        }. Choose how the customer responds so the agent can reassess.`
    );
    adaptiveSet(
        "adaptive-next-action",
        formatAction(
            item?.recovery_action
        )
    );
    adaptiveSet(
        "adaptive-next-reason",
        "Primary recovery action selected by the bounded recovery policy."
    );
    adaptiveSet(
        "adaptive-interpretation",
        "Waiting for customer response."
    );
    const select =
        document.getElementById(
            "adaptive-customer-response"
        );
    if (select) {
        select.value = "";
    }
    const status =
        document.getElementById(
            "adaptive-demo-status"
        );
    if (status) {
        status.textContent =
            `Simulating ${item?.transaction_id || "selected case"}`;
    }
}
async function adaptiveSelectTransaction(tx) {
    if (!tx) {
        return;
    }
    try {
        const data =
            await getJSON(
                `/recovery-agent/decision/${encodeURIComponent(tx)}`
            );
        const assessment =
            data?.assessment || {};
        const decision =
            data?.decision || {};
        const outcome =
            data?.outcome || {};
        adaptiveStartFromExecution({
            transaction_id: tx,
            scenario:
                data?.case?.scenario ||
                "",
            diagnosis:
                data?.case?.diagnosis ||
                "",
            recovery_probability:
                assessment.recovery_probability,
            recovery_action:
                decision.selected_action,
            recommended_channel:
                decision.channel,
            transaction_amount:
                data?.case?.transaction_amount,
            money_recovered:
                outcome.money_recovered,
            attempt_count:
                outcome.attempt_count
        });
    } catch (error) {
        console.error(
            "Adaptive transaction selection error:",
            error
        );
        adaptiveSet(
            "adaptive-interpretation",
            `Unable to load selected transaction: ${error.message}`
        );
    }
}
function handleAdaptiveCustomerResponse() {
    if (!adaptiveTransaction) {
        adaptiveSet(
            "adaptive-interpretation",
            "Select a transaction first."
        );
        return;
    }
    const select =
        document.getElementById(
            "adaptive-customer-response"
        );
    const response =
        select?.value || "";
    if (!response) {
        adaptiveSet(
            "adaptive-interpretation",
            "Choose a simulated customer response."
        );
        return;
    }
    /* ========================================================
       PAYMENT COMPLETED
       ======================================================== */
    if (response === "paid") {
        const amount =
            Number(
                adaptiveTransaction.transaction_amount ||
                0
            );
        adaptiveAddTimeline(
            "CUSTOMER",
            "Customer completed the payment."
        );
        adaptiveAddTimeline(
            "INTERPRET",
            "Agent interprets the response as confirmed payment success."
        );
        adaptiveAddTimeline(
            "MEASURE",
            `Payment confirmed. ${money(amount)} recovered.`
        );
        adaptiveAddTimeline(
            "STOP",
            "PAYMENT_SUCCESS · Agent stops the recovery loop."
        );
        adaptiveSet(
            "adaptive-state-title",
            "Recovery Complete"
        );
        adaptiveSet(
            "adaptive-state-detail",
            `Payment success detected. ${money(amount)} is recovered and no further intervention is required.`
        );
        adaptiveSet(
            "adaptive-next-action",
            "STOP"
        );
        adaptiveSet(
            "adaptive-next-reason",
            "Payment success satisfies the recovery stopping rule."
        );
        adaptiveSet(
            "adaptive-interpretation",
            "Agent interpretation: PAYMENT_SUCCESS → stop."
        );
        const status =
            document.getElementById(
                "adaptive-demo-status"
            );
        if (status) {
            status.textContent =
                "Recovery Complete";
        }
        return;
    }
    /* ========================================================
       PROMISE TO PAY
       ======================================================== */
    if (response === "promise_to_pay") {
        adaptiveAddTimeline(
            "CUSTOMER",
            'Customer responded: "I\'ll pay tomorrow."'
        );
        adaptiveAddTimeline(
            "INTERPRET",
            "Agent interprets the response as PROMISE_TO_PAY."
        );
        adaptiveAddTimeline(
            "REASSESS",
            "Positive payment intent makes immediate escalation unnecessary."
        );
        adaptiveAddTimeline(
            "DECIDE",
            "Switch to a bounded promise-to-pay follow-up."
        );
        adaptiveSet(
            "adaptive-state-title",
            "Promise To Pay Detected"
        );
        adaptiveSet(
            "adaptive-state-detail",
            "The customer is willing to pay, so the agent adapts the recovery strategy instead of escalating."
        );
        adaptiveSet(
            "adaptive-next-action",
            "Promise To Pay Follow-up"
        );
        adaptiveSet(
            "adaptive-next-reason",
            "Positive customer intent supports a lower-friction follow-up path."
        );
        adaptiveSet(
            "adaptive-interpretation",
            "Agent interpretation: PROMISE_TO_PAY → schedule bounded follow-up."
        );
        return;
    }
    /* ========================================================
       CUSTOMER DECLINES
       ======================================================== */
    if (response === "declined") {
        adaptiveAddTimeline(
            "CUSTOMER",
            "Customer indicated they cannot make the payment."
        );
        adaptiveAddTimeline(
            "INTERPRET",
            "Agent interprets the response as negative immediate payment intent."
        );
        adaptiveAddTimeline(
            "DECIDE",
            "Automated recovery should stop and merchant operations should review the case."
        );
        adaptiveAddTimeline(
            "ESCALATE",
            "RECOVERY_ESCALATION_REQUIRED · HUMAN_REVIEW"
        );
        adaptiveSet(
            "adaptive-state-title",
            "Human Review Required"
        );
        adaptiveSet(
            "adaptive-state-detail",
            "The customer explicitly declined payment, so repeated automated intervention is no longer appropriate."
        );
        adaptiveSet(
            "adaptive-next-action",
            "ESCALATE"
        );
        adaptiveSet(
            "adaptive-next-reason",
            "Negative customer intent crosses the automated recovery boundary."
        );
        adaptiveSet(
            "adaptive-interpretation",
            "Agent interpretation: declined payment → HUMAN_REVIEW."
        );
        return;
    }
    /* ========================================================
       NO RESPONSE
       ======================================================== */
    if (response === "no_response") {
        adaptiveAddTimeline(
            "CUSTOMER",
            "No customer response was received."
        );
        adaptiveAddTimeline(
            "INTERPRET",
            "Agent treats the case as unresolved rather than assuming payment failure."
        );
        adaptiveAddTimeline(
            "REASSESS",
            "Move to a lower-friction fallback before escalation, subject to attempt limits."
        );
        adaptiveSet(
            "adaptive-state-title",
            "No Response"
        );
        adaptiveSet(
            "adaptive-state-detail",
            "The first contact did not produce a response. The agent can try a bounded fallback action."
        );
        adaptiveSet(
            "adaptive-next-action",
            "Payment Link Follow Up"
        );
        adaptiveSet(
            "adaptive-next-reason",
            "Use a lower-friction recovery path before human escalation."
        );
        adaptiveSet(
            "adaptive-interpretation",
            "Agent interpretation: unresolved → fallback recovery action."
        );
        return;
    }
    /* ========================================================
       WRONG CHANNEL
       ======================================================== */
    if (response === "wrong_channel") {
        adaptiveAddTimeline(
            "CUSTOMER",
            "Customer requested a different communication channel."
        );
        adaptiveAddTimeline(
            "INTERPRET",
            "Agent interprets the response as a channel preference update."
        );
        adaptiveAddTimeline(
            "REASSESS",
            "Recovery objective stays unchanged while communication channel adapts."
        );
        adaptiveSet(
            "adaptive-state-title",
            "Channel Preference Updated"
        );
        adaptiveSet(
            "adaptive-state-detail",
            "The agent preserves the recovery objective but adapts communication to customer preference."
        );
        adaptiveSet(
            "adaptive-next-action",
            "Repeat Recovery On Preferred Channel"
        );
        adaptiveSet(
            "adaptive-next-reason",
            "Respecting customer channel preference can improve engagement."
        );
        adaptiveSet(
            "adaptive-interpretation",
            "Agent interpretation: channel mismatch → adapt channel."
        );
    }
}
function setupAdaptiveRecoveryLoop() {
    const applyButton =
        document.getElementById(
            "adaptive-apply-response"
        );
    if (applyButton) {
        applyButton.addEventListener(
            "click",
            handleAdaptiveCustomerResponse
        );
    }
    const body =
        document.getElementById(
            "recent-body"
        );
    if (body) {
        body.addEventListener(
            "click",
            event => {
                const link =
                    event.target.closest(
                        "[data-audit-tx]"
                    );
                if (!link) {
                    return;
                }
                const tx =
                    link.getAttribute(
                        "data-audit-tx"
                    );
                adaptiveSelectTransaction(
                    tx
                );
            }
        );
    }
}
function setupExecutionControls() {
  const search =
    document.getElementById(
      "agent-execution-search"
    );
  const scenario =
    document.getElementById(
      "agent-scenario-filter"
    );
  const result =
    document.getElementById(
      "agent-result-filter"
    );
  let timer = null;
  search?.addEventListener(
    "input",
    () => {
      clearTimeout(
        timer
      );
      timer =
        setTimeout(
          () => {
            currentPage =
              1;
            loadExecutions();
          },
          250
        );
    }
  );
  scenario?.addEventListener(
    "change",
    () => {
      currentPage =
        1;
      loadExecutions();
    }
  );
  result?.addEventListener(
    "change",
    () => {
      currentPage =
        1;
      loadExecutions();
    }
  );
}
/* ============================================================
   BROWSER HISTORY
   ============================================================ */
window.addEventListener(
  "popstate",
  event => {
    const tx =
      event.state?.tx ||
      new URLSearchParams(
        location.search
      ).get(
        "transaction_id"
      );
    if (tx) {
      loadAudit(
        tx
      );
      renderDecisionLayer(
        tx
      );
    }
  }
);
/* ============================================================
   INITIALIZATION
   ============================================================ */
document.addEventListener(
  "DOMContentLoaded",
  () => {
    setupSidebar();
    setupExecutionControls();
    setupAdaptiveRecoveryLoop();
    document
      .getElementById(
        "agent-refresh"
      )
      ?.addEventListener(
        "click",
        refresh
      );
    document
      .getElementById(
        "run-demo-batch"
      )
      ?.addEventListener(
        "click",
        runBatch
      );
    refresh();
    const tx =
      new URLSearchParams(
        location.search
      ).get(
        "transaction_id"
      );
    if (tx) {
      loadAudit(
        tx
      );
      renderDecisionLayer(
        tx
      );
    }
    setInterval(
      refresh,
      30000
    );
  }
);