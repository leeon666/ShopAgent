const state = {
  userToken: null,
  adminToken: null,
  user: null,
  tickets: [],
  selectedId: null,
  selectedTicket: null,
  filter: "all",
  lastRun: null,
  proposal: null,
  evaluation: null,
  auditLoaded: false,
};

const statusLabels = {
  pending: "待处理",
  reviewing: "审核中",
  awaiting_user: "等待补充",
  rejected: "已驳回",
  completed: "已完成",
  cancelled: "已取消",
  paid: "已支付",
  shipped: "已发货",
};

const actionLabels = {
  create_refund_review: "发起退款审核",
  manual_review: "转人工复核",
  provide_logistics_update: "同步物流进展",
  request_order_info: "补充订单信息",
  provide_customer_service_answer: "生成客服答复",
};

const typeLabels = {
  refund: "退款",
  return: "退货",
  exchange: "换货",
  damage: "商品破损",
  logistics: "物流异常",
  other: "其他",
};

function $(selector) {
  return document.querySelector(selector);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 2800);
}

async function login(username, password) {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "登录失败");
  return body;
}

function headers(tokenType = "admin", json = true) {
  const token = tokenType === "admin" ? state.adminToken : state.userToken;
  const value = { Authorization: `Bearer ${token}` };
  if (json) value["Content-Type"] = "application/json";
  return value;
}

async function request(path, options = {}) {
  const { method = "GET", body, tokenType = "admin", json = true } = options;
  const response = await fetch(path, {
    method,
    headers: headers(tokenType, json),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

async function loginAll() {
  const [admin, user] = await Promise.all([
    login("admin", "admin123"),
    login("demo", "123456"),
  ]);
  state.adminToken = admin.token;
  state.userToken = user.token;
  state.user = user.user;
}

function statusBadge(status) {
  const label = statusLabels[status] || status;
  let cls = "status-neutral";
  if (["pending", "awaiting_user", "reviewing"].includes(status)) cls = "status-warning";
  if (["completed"].includes(status)) cls = "status-success";
  if (["rejected", "cancelled"].includes(status)) cls = "status-danger";
  if (["paid", "shipped"].includes(status)) cls = "status-info";
  return `<span class="status-badge ${cls}">${escapeHtml(label)}</span>`;
}

function formatDate(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatMoney(value) {
  return `¥${Number(value || 0).toFixed(2)}`;
}

async function loadDashboard() {
  const [stats, evaluation, allTickets] = await Promise.all([
    request("/api/admin/stats"),
    request("/api/admin/evaluation/latest"),
    request("/api/after-sales/all"),
  ]);
  state.evaluation = evaluation;
  state.tickets = allTickets.items.filter((ticket) => ticket.user_id === state.user.id);
  renderKpis(stats);
  renderTickets();
  renderEvaluation();

  if (state.tickets.length) {
    const preferred = state.tickets.find((ticket) => ticket.status === "pending") || state.tickets[0];
    await selectTicket(preferred.id);
  } else {
    renderNoTicket();
  }
}

function renderKpis(stats) {
  const pending = state.tickets.filter((ticket) =>
    ["pending", "reviewing", "awaiting_user"].includes(ticket.status)
  ).length;
  $("#kpiRevenue").textContent = formatMoney(stats.revenue);
  $("#kpiOrders").textContent = stats.order_total;
  $("#kpiTickets").textContent = pending;
  $("#kpiStock").textContent = stats.low_stock;
  $("#queueCount").textContent = state.tickets.length;
}

function renderTickets() {
  const list = $("#ticketList");
  const filtered = state.tickets.filter((ticket) => {
    if (state.filter === "pending") {
      return ["pending", "reviewing", "awaiting_user"].includes(ticket.status);
    }
    if (state.filter === "completed") {
      return ["completed", "rejected", "cancelled"].includes(ticket.status);
    }
    return true;
  });

  if (!filtered.length) {
    list.innerHTML = `<div class="empty-state">当前筛选下没有工单</div>`;
    return;
  }

  list.innerHTML = filtered.map((ticket) => `
    <button class="ticket-item ${ticket.id === state.selectedId ? "active" : ""}" data-ticket-id="${ticket.id}">
      <div class="ticket-top">
        <span class="ticket-no">${escapeHtml(ticket.ticket_no)}</span>
        ${statusBadge(ticket.status)}
      </div>
      <div class="ticket-reason">${escapeHtml(ticket.reason || "售后工单")}</div>
      <div class="ticket-bottom">
        <span>${escapeHtml(typeLabels[ticket.type] || ticket.type)} · ${formatMoney(ticket.order.total_amount)}</span>
        <span>${formatDate(ticket.created_at)}</span>
      </div>
    </button>
  `).join("");

  list.querySelectorAll("[data-ticket-id]").forEach((button) => {
    button.addEventListener("click", () => selectTicket(Number(button.dataset.ticketId)));
  });
}

async function selectTicket(ticketId) {
  state.selectedId = ticketId;
  state.selectedTicket = await request(`/api/after-sales/${ticketId}`, { tokenType: "user" });
  const ticket = state.selectedTicket;
  $("#ticketTitle").textContent = `${typeLabels[ticket.type] || ticket.type} · ${ticket.ticket_no}`;
  $("#ticketMeta").textContent = `创建于 ${formatDate(ticket.created_at)} · 更新时间 ${formatDate(ticket.updated_at)}`;
  $("#ticketStatus").outerHTML = statusBadge(ticket.status).replace(
    'class="status-badge',
    'id="ticketStatus" class="status-badge'
  );
  $("#orderNo").textContent = ticket.order.order_no;
  $("#orderStatus").textContent = statusLabels[ticket.order.status] || ticket.order.status;
  $("#orderAmount").textContent = formatMoney(ticket.order.total_amount);
  $("#messageInput").value = "";
  $("#composerHint").textContent = `已有 ${ticket.messages.length} 条补充消息，Agent 会压缩长上下文`;
  renderConversation(ticket);
  renderTickets();
  resetAgentPanel();
}

function renderConversation(ticket) {
  const items = ticket.messages.length
    ? ticket.messages.map((message) => ({
        role: message.sender_role,
        content: message.content,
        created_at: message.created_at,
      }))
    : [{ role: "user", content: ticket.reason || "请帮我处理这个售后问题", created_at: ticket.created_at }];

  $("#conversation").innerHTML = items.map((message) => `
    <div class="message ${message.role === "admin" ? "admin" : "user"}">
      <div class="message-head">
        <span>${message.role === "admin" ? "客服" : "顾客"}</span>
        <span>${formatDate(message.created_at)}</span>
      </div>
      ${escapeHtml(message.content)}
    </div>
  `).join("");
  $("#conversation").scrollTop = $("#conversation").scrollHeight;
}

function renderNoTicket() {
  $("#ticketTitle").textContent = "还没有售后工单";
  $("#ticketMeta").textContent = "生成一张演示工单后开始体验";
  $("#conversation").innerHTML = `<div class="empty-state tall">点击顶部“生成演示工单”创建订单和售后数据。</div>`;
}

function resetAgentPanel() {
  state.lastRun = null;
  state.proposal = null;
  $("#agentPlaceholder").classList.remove("hidden");
  $("#agentResult").classList.add("hidden");
  $("#traceSummary").textContent = "还没有运行记录";
  $("#traceList").innerHTML = "";
}

async function sendMessage() {
  if (!state.selectedTicket) return toast("请先选择工单");
  const content = $("#messageInput").value.trim();
  if (!content) return toast("请输入补充说明");
  try {
    await request(`/api/after-sales/${state.selectedTicket.id}/messages`, {
      method: "POST",
      tokenType: "user",
      body: { content },
    });
    toast("补充说明已写入工单");
    await selectTicket(state.selectedTicket.id);
  } catch (error) {
    toast(error.message);
  }
}

async function runAgent() {
  if (!state.selectedTicket) return toast("请先选择工单");
  const message = $("#messageInput").value.trim() || state.selectedTicket.reason;
  setActiveTab("trail");
  $("#traceList").innerHTML = "";
  $("#traceSummary").textContent = "Agent 正在建立执行链路...";
  $("#agentPlaceholder").classList.add("hidden");
  $("#agentResult").classList.add("hidden");

  try {
    const response = await fetch(`/api/agent-runs/tickets/${state.selectedTicket.id}/stream`, {
      method: "POST",
      headers: headers("user"),
      body: JSON.stringify({ message }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let trace = [];
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";
      for (const chunk of chunks) {
        const line = chunk.split("\n").find((item) => item.startsWith("data: "));
        if (!line) continue;
        const event = JSON.parse(line.slice(6));
        if (event.event === "node") {
          trace.push(event.step);
          renderTrace(trace, event.run_id, event.step.request_id);
        }
        if (event.event === "completed") {
          state.lastRun = event.run;
          renderTrace(event.run.steps, event.run.id, event.run.request_id, event.run);
          renderAgentResult(event.run);
          toast(`Agent 完成，耗时 ${event.run.latency_ms} ms`);
        }
      }
    }
  } catch (error) {
    toast(error.message);
    $("#traceSummary").textContent = `运行失败：${error.message}`;
  }
}

function renderTrace(steps, runId, requestId, run = null) {
  $("#traceSummary").innerHTML = `
    <strong>Run #${escapeHtml(runId || "--")}</strong><br>
    Request ID <code>${escapeHtml(requestId || "--")}</code>
    ${run ? `<br>总耗时 ${run.latency_ms} ms · ${run.tokens_used} tokens` : ""}
  `;
  $("#traceList").innerHTML = steps.map((step) => `
    <div class="trace-item">
      <strong>${escapeHtml(step.node)}</strong>
      <span>${step.duration_ms ?? 0} ms</span>
      <p>${escapeHtml(JSON.stringify(step.detail || {}))}</p>
    </div>
  `).join("");
}

function renderAgentResult(run) {
  const output = run.output || {};
  $("#agentResult").classList.remove("hidden");
  $("#resultIntent").textContent = escapeHtml(output.intent || "--");
  $("#resultPlanSource").textContent = output.decision_source === "llm" ? "DeepSeek" : "规则兜底";
  $("#resultSummary").textContent = output.summary || "--";
  $("#resultRequestId").textContent = run.request_id || "--";
  $("#resultAction").textContent = actionLabels[output.recommended_action] || output.recommended_action || "--";
  $("#confidenceValue").textContent = `${Math.round((output.confidence || 0) * 100)}%`;
  $("#confidenceBar").style.width = `${Math.round((output.confidence || 0) * 100)}%`;

  const approval = $("#approvalBadge");
  approval.textContent = output.requires_human_approval ? "需要人工审批" : "可自动处理";
  approval.className = `status-badge ${output.requires_human_approval ? "status-warning" : "status-success"}`;

  const evidence = output.evidence || [];
  $("#evidenceList").innerHTML = evidence.length
    ? evidence.map((item) => `
      <article class="evidence-card">
        <strong>${escapeHtml(item.claim)}</strong>
        <span>${escapeHtml(item.source || "")}</span>
        <p>${escapeHtml(item.quote || "")}</p>
      </article>
    `).join("")
    : `<div class="empty-state">没有可用证据</div>`;

  const missing = output.missing_information || [];
  $("#missingSection").classList.toggle("hidden", !missing.length);
  $("#missingList").innerHTML = missing.map((item) => `<li>${escapeHtml(item)}</li>`).join("");

  const actions = $("#approvalActions");
  if (!output.requires_human_approval) {
    actions.innerHTML = "";
  } else {
    actions.innerHTML = `
      <button class="button button-primary" data-proposal-action="create">生成执行提案</button>
      <button class="button button-secondary" data-approval="awaiting_user">要求补充</button>
    `;
  }
  actions.querySelectorAll("[data-proposal-action]").forEach((button) => {
    button.addEventListener("click", createProposal);
  });
  actions.querySelectorAll("[data-approval]").forEach((button) => {
    button.addEventListener("click", () => reviewTicket(button.dataset.approval));
  });
  renderProposalActions();
}

function renderProposalActions() {
  const actions = $("#approvalActions");
  if (!state.proposal) return;
  const proposal = state.proposal;
  if (proposal.status !== "pending") {
    actions.innerHTML = `
      <div class="proposal-state">
        <strong>执行提案 #${proposal.id}</strong>
        <span>${proposal.status === "approved" ? "已批准执行" : "已驳回"}</span>
      </div>
    `;
    return;
  }
  actions.innerHTML = `
    <div class="proposal-state">
      <strong>执行提案 #${proposal.id} · 待审批</strong>
      <span>退款金额 ${formatMoney(proposal.payload?.refund_amount)}</span>
    </div>
    <button class="button button-primary" data-proposal-review="approve">批准执行</button>
    <button class="button button-danger" data-proposal-review="reject">驳回提案</button>
  `;
  actions.querySelectorAll("[data-proposal-review]").forEach((button) => {
    button.addEventListener("click", () => reviewProposal(button.dataset.proposalReview));
  });
}

async function createProposal() {
  if (!state.lastRun) return toast("请先运行 Agent");
  try {
    state.proposal = await request(`/api/agent-runs/${state.lastRun.id}/proposals`, {
      method: "POST",
      tokenType: "user",
      json: false,
    });
    toast(`执行提案 #${state.proposal.id} 已创建`);
    renderProposalActions();
  } catch (error) {
    toast(error.message);
  }
}

async function reviewProposal(action) {
  if (!state.proposal) return;
  try {
    state.proposal = await request(`/api/proposals/${state.proposal.id}/${action}`, {
      method: "POST",
      tokenType: "admin",
      body: {
        decision_note:
          action === "approve" ? "管理员确认执行退款提案" : "管理员驳回退款提案",
      },
    });
    toast(action === "approve" ? "提案已批准并执行" : "提案已驳回");
    await loadDashboard();
  } catch (error) {
    toast(error.message);
  }
}

async function reviewTicket(status) {
  if (!state.selectedTicket) return;
  try {
    await request(`/api/after-sales/${state.selectedTicket.id}/review`, {
      method: "POST",
      tokenType: "admin",
      body: {
        status,
        resolution: status === "completed" ? "人工审核通过" : status === "rejected" ? "不符合退款条件" : "已转入人工审核",
        refund_amount: status === "completed" ? state.selectedTicket.order.total_amount : null,
      },
    });
    toast(`工单已更新为${statusLabels[status] || status}`);
    await loadDashboard();
  } catch (error) {
    toast(error.message);
  }
}

async function loadAudit() {
  const data = await request("/api/admin/audit-logs?page=1&size=14");
  $("#auditList").innerHTML = data.items.map((item) => `
    <article class="audit-item">
      <strong>${escapeHtml(item.action)}</strong>
      <span>${formatDate(item.created_at)} · ${escapeHtml(item.actor_role)}</span>
      <code>${escapeHtml(item.request_id || "no-request-id")}</code>
    </article>
  `).join("");
}

function renderEvaluation() {
  const full = state.evaluation?.modes?.full;
  if (!full) {
    $("#evalMetrics").innerHTML = `<div class="empty-state">暂无评测结果</div>`;
    return;
  }
  const metrics = [
    ["意图准确率", full.intent_accuracy],
    ["审批准确率", full.approval_accuracy],
    ["引用覆盖率", full.policy_citation_coverage],
    ["工具正确率", full.tool_call_accuracy],
    ["工具成功率", full.tool_success_rate],
    ["P95 延迟", `${full.p95_latency_ms} ms`],
  ];
  $("#evalMetrics").innerHTML = metrics.map(([label, value]) => `
    <div class="eval-metric"><span>${label}</span><strong>${value ?? "--"}</strong></div>
  `).join("");
}

function setActiveTab(tabName) {
  document.querySelectorAll("#insightTabs [data-tab]").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-view").forEach((view) => {
    view.classList.toggle("active", view.dataset.view === tabName);
  });
  if (tabName === "audit") loadAudit().catch((error) => toast(error.message));
}

async function generateDemo() {
  try {
    $("#generateDemo").disabled = true;
    $("#generateDemo").textContent = "正在准备...";
    await request("/api/cart", { method: "DELETE", tokenType: "user", json: false });
    await request("/api/cart", {
      method: "POST",
      tokenType: "user",
      body: { product_id: 5, quantity: 1 },
    });
    const order = await request("/api/orders", { method: "POST", tokenType: "user", json: false });
    await request("/api/payment/mock", {
      method: "POST",
      tokenType: "user",
      body: { order_id: order.id },
    });
    await request("/api/after-sales", {
      method: "POST",
      tokenType: "user",
      body: { order_id: order.id, type: "damage", reason: "商品破损，顾客要求退款" },
    });
    await request("/api/knowledge", {
      method: "POST",
      body: {
        title: "商品破损退款政策",
        source: "policy/damage-refund.md",
        content: "商品签收后七日内发生非人为损坏，可以申请退货退款。退款必须经过审核，超过一百元由主管人工审批。",
      },
    });
    toast("演示工单已生成");
    await loadDashboard();
  } catch (error) {
    toast(error.message);
  } finally {
    $("#generateDemo").disabled = false;
    $("#generateDemo").textContent = "生成演示工单";
  }
}

function bindEvents() {
  $("#sendMessage").addEventListener("click", sendMessage);
  $("#runAgent").addEventListener("click", runAgent);
  $("#generateDemo").addEventListener("click", generateDemo);
  $("#insightTabs").addEventListener("click", (event) => {
    const tab = event.target.closest("[data-tab]");
    if (tab) setActiveTab(tab.dataset.tab);
  });
  $("#ticketFilters").addEventListener("click", (event) => {
    const button = event.target.closest("[data-filter]");
    if (!button) return;
    state.filter = button.dataset.filter;
    document.querySelectorAll("#ticketFilters .filter").forEach((item) => item.classList.toggle("active", item === button));
    renderTickets();
  });
  $("#messageInput").addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runAgent();
  });
}

async function init() {
  bindEvents();
  try {
    await loginAll();
    await loadDashboard();
    toast("已连接到 ShopAgent 后端");
  } catch (error) {
    toast(`初始化失败：${error.message}`);
    $("#conversation").innerHTML = `<div class="empty-state tall">初始化失败：${escapeHtml(error.message)}</div>`;
  }
}

init();
