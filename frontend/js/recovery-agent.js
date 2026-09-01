const money = v =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2
  }).format(Number(v || 0));
const number = v =>
  Number(v || 0).toLocaleString("en-IN");
const pct = v =>
  `${Number(v || 0).toFixed(2)}%`;
const esc = v => {
  const d = document.createElement("div");
  d.textContent = v == null ? "" : String(v);
  return d.innerHTML;
};
function set(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}
function formatScenario(value) {
  return String(value || "—")
    .replaceAll("_", " ")
    .replace(/\b\w/g, x => x.toUpperCase());
}
function formatAction(value) {
  return String(value || "—")
    .replaceAll("_", " ")
    .replace(/\b\w/g, x => x.toUpperCase());
}
function setupSidebar() {
  const app = document.getElementById("app");
  const btn = document.getElementById("sidebar-toggle");
  if (!app || !btn) return;
  if (
    localStorage.getItem("sidebarCollapsed") === "true"
  ) {
    app.classList.add("sidebar-collapsed");
  }
  const update = () => {
    const collapsed =
      app.classList.contains("sidebar-collapsed");
    const icon =
      btn.querySelector(".toggle-icon");
    if (icon) {
      icon.textContent = collapsed ? "›" : "‹";
    }
    btn.title =
      collapsed
        ? "Expand sidebar"
        : "Collapse sidebar";
    btn.setAttribute(
      "aria-label",
      collapsed
        ? "Expand sidebar"
        : "Collapse sidebar"
    );
  };
  btn.addEventListener("click", () => {
    app.classList.toggle("sidebar-collapsed");
    localStorage.setItem(
      "sidebarCollapsed",
      app.classList.contains("sidebar-collapsed")
        ? "true"
        : "false"
    );
    update();
  });
  update();
}
async function getJSON(url, options = {}) {
  const response = await fetch(
    url,
    {
      cache: "no-store",
      ...options
    }
  );
  let data = {};
  try {
    data = await response.json();
  } catch (_) {}
  if (!response.ok) {
    throw new Error(
      data.detail ||
      `Request failed (${response.status})`
    );
  }
  return data;
}
let latestSummary = null;
let currentPage = 1;
const PAGE_SIZE = 50;
function getFilters() {
  return {
    search:
      document.getElementById(
        "agent-execution-search"
      )?.value.trim() || "",
    scenario:
      document.getElementById(
        "agent-scenario-filter"
      )?.value || "",
    result:
      document.getElementById(
        "agent-result-filter"
      )?.value || ""
  };
}
function renderSummary(data) {
  latestSummary = data || {};
  set(
    "agent-executions",
    number(data?.total_executions)
  );
  set(
    "agent-recovered",
    number(data?.recovered_executions)
  );
  set(
    "agent-rate",
    pct(data?.agent_recovery_rate)
  );
  set(
    "agent-money",
    money(data?.money_recovered)
  );
  set(
    "agent-attempts",
    Number(
      data?.average_attempts_per_execution || 0
    ).toFixed(2)
  );
  set(
    "agent-escalations",
    number(data?.escalations)
  );
  const grid =
    document.getElementById("scenario-grid");
  if (!grid) return;
  const scenarios =
    Array.isArray(
      data?.scenario_performance
    )
      ? data.scenario_performance
      : [];
  if (!scenarios.length) {
    grid.innerHTML =
      '<div class="audit-empty">No persisted scenario executions yet.</div>';
    return;
  }
  grid.innerHTML =
    scenarios.map(item => `
      <div class="scenario-card">
        <strong>
          ${esc(
            formatScenario(item.scenario)
          )}
        </strong>
        <div class="scenario-meta">
          <span>
            ${number(item.executions)} executions
          </span>
          <span>
            ${pct(item.recovery_rate)}
          </span>
        </div>
        <div class="scenario-money">
          ${money(item.money_recovered)}
        </div>
      </div>
    `).join("");
}
async function loadExecutions() {
  const body =
    document.getElementById("recent-body");
  if (!body) return;
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
  body.innerHTML = `
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
    renderExecutionCount(data);
    renderExecutions(
      Array.isArray(data?.executions)
        ? data.executions
        : []
    );
    renderPagination(data);
  } catch (error) {
    console.error(
      "Recovery Agent execution error:",
      error
    );
    body.innerHTML = `
      <tr>
        <td
          colspan="10"
          class="loading"
        >
          Unable to load executions:
          ${esc(error.message)}
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
function renderExecutionCount(data) {
  const total =
    Number(data?.total ?? 0);
  const page =
    Number(data?.page ?? 1);
  const pageSize =
    Number(
      data?.page_size ?? PAGE_SIZE
    );
  const returned =
    Number(data?.returned ?? 0);
  if (total === 0) {
    set(
      "execution-count",
      "Showing 0 of 0 executions"
    );
    return;
  }
  const start =
    ((page - 1) * pageSize) + 1;
  const end =
    Math.min(
      start + returned - 1,
      total
    );
  set(
    "execution-count",
    `Showing ${number(start)}–${number(end)} of ${number(total)} executions`
  );
}
function renderExecutions(executions) {
  const body =
    document.getElementById(
      "recent-body"
    );
  if (!body) return;
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
    executions.map(item => {
      const tx =
        String(
          item.transaction_id || ""
        );
      return `
        <tr>
          <td class="execution-tx">
            <a
              class="case-link"
              href="/recovery-case.html?transaction_id=${encodeURIComponent(tx)}"
              data-audit-tx="${esc(tx)}"
            >
              <strong>
                ${esc(tx)}
              </strong>
            </a>
          </td>
          <td>
            ${esc(
              item.customer_id || "—"
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
              item.diagnosis || "—"
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
              item.recommended_channel || "—"
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
              item.stopping_reason || "—"
            )}
          </td>
        </tr>
      `;
    }).join("");
}


function renderPagination(data) {
  const container =
    document.getElementById(
      "agent-pagination"
    );
  if (!container) return;
  const total =
    Number(data?.total ?? 0);
  const current =
    Number(data?.page ?? 1);
  const totalPages =
    Math.max(
      1,
      Number(
        data?.total_pages ?? 1
      )
    );
  if (total === 0) {
    container.innerHTML = "";
    return;
  }
  const pages = [];
  const addPage = page => {
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
    addPage(totalPages);
  }
  container.innerHTML = `
    <div class="pagination">
      <button
        type="button"
        id="agent-prev"
        class="pagination-button pagination-nav"
        ${current <= 1 ? "disabled" : ""}
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
        ${current >= totalPages ? "disabled" : ""}
      >
        Next →
      </button>
    </div>
  `;
  container
    .querySelectorAll(
      "[data-page]"
    )
    .forEach(button => {
      button.addEventListener(
        "click",
        () => {
          const target =
            Number(
              button.dataset.page
            );
          if (
            !Number.isFinite(target)
          ) {
            return;
          }
          if (
            target === currentPage
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
    });
  document
    .getElementById(
      "agent-prev"
    )
    ?.addEventListener(
      "click",
      () => {
        if (currentPage <= 1) {
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
          currentPage >= totalPages
        ) {
          return;
        }
        currentPage += 1;
        loadExecutions();
      }
    );
}
async function loadAudit(tx) {
  const box =
    document.getElementById(
      "audit-content"
    );
  if (!box) return;
  box.innerHTML =
    "Loading audit…";
  try {
    const data =
      await getJSON(
        `/recovery-agent/audit/${encodeURIComponent(tx)}`
      );
    const timeline =
      Array.isArray(data?.timeline)
        ? data.timeline
        : [];
    box.innerHTML = `
      <pre class="audit-pre">${esc(
        JSON.stringify(
          {
            transaction_id:
              data.transaction_id,
            scenario:
              data.scenario,
            agent_result:
              data.agent_result,
            timeline
          },
          null,
          2
        )
      )}</pre>
    `;
  } catch (error) {
    box.innerHTML = `
      <div class="audit-empty">
        Unable to load audit:
        ${esc(error.message)}
      </div>
    `;
  }
}
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
    renderSummary(summary);
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
async function runBatch() {
  const btn =
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
  if (!btn || !status) {
    return;
  }
  btn.disabled = true;
  btn.textContent =
    "Running…";
  status.style.display =
    "block";
  status.textContent =
    `Selecting ${size} active recovery cases…`;
  try {
    const casesResp =
      await getJSON(
        `/recovery-cases?limit=${encodeURIComponent(size)}`
      );
    const cases =
      Array.isArray(
        casesResp?.cases
      )
        ? casesResp.cases
        : [];
    const ids =
      cases
        .map(
          item =>
            item.transaction_id
        )
        .filter(Boolean)
        .slice(0, size);
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
          body: JSON.stringify({
            transaction_ids: ids
          })
        }
      );
    const after =
      await getJSON(
        "/recovery-agent/summary"
      );
    renderSummary(after);
    const newExecutions =
      Math.max(
        0,
        Number(
          after?.total_executions || 0
        ) -
        Number(
          before?.total_executions || 0
        )
      );
    const newRecovered =
      Math.max(
        0,
        Number(
          after?.recovered_executions || 0
        ) -
        Number(
          before?.recovered_executions || 0
        )
      );
    const newMoney =
      Math.max(
        0,
        Number(
          after?.money_recovered || 0
        ) -
        Number(
          before?.money_recovered || 0
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
      money(newMoney)
    );
    if (summaryBox) {
      summaryBox.style.display =
        "grid";
    }
    status.textContent =
      `Batch complete.\nSelected: ${ids.length}\nRequested: ${result?.requested ?? ids.length}\nProcessed: ${result?.processed ?? newExecutions}\nNew recovered: ${newRecovered}\nNew money recovered: ${money(newMoney)}`;
    currentPage = 1;
    await loadExecutions();
  } catch (error) {
    status.textContent =
      `Batch error: ${error.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent =
      "Run Agent Batch";
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
      clearTimeout(timer);
      timer =
        setTimeout(
          () => {
            currentPage = 1;
            loadExecutions();
          },
          250
        );
    }
  );
  scenario?.addEventListener(
    "change",
    () => {
      currentPage = 1;
      loadExecutions();
    }
  );
  result?.addEventListener(
    "change",
    () => {
      currentPage = 1;
      loadExecutions();
    }
  );
}
window.addEventListener(
  "popstate",
  event => {
    const tx =
      event.state?.tx ||
      new URLSearchParams(
        location.search
      ).get("transaction_id");
    if (tx) {
      loadAudit(tx);
    }
  }
);
document.addEventListener(
  "DOMContentLoaded",
  () => {
    setupSidebar();
    setupExecutionControls();
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
      loadAudit(tx);
    }
    setInterval(
      refresh,
      30000
    );
  }
);
