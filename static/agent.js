const state = { userToken: null, adminToken: null, ticketId: null };

function log(text) {
  const el = document.getElementById("logs");
  el.textContent += "\n" + text;
  el.scrollTop = el.scrollHeight;
}

function resetLog() {
  document.getElementById("logs").textContent = "等待开始...";
}

async function request(path, options = {}) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `HTTP ${response.status}`);
  }
  return body;
}

async function login(username, password) {
  return request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

function userHeaders() {
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${state.userToken}`,
  };
}

function adminHeaders() {
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${state.adminToken}`,
  };
}

async function setupDemo() {
  resetLog();
  try {
    const user = await login("demo", "123456");
    state.userToken = user.token;
    log(`✓ 用户登录：${user.user.username}`);

    await request("/api/cart", { method: "DELETE", headers: userHeaders() });
    await request("/api/cart", {
      method: "POST",
      headers: userHeaders(),
      body: JSON.stringify({ product_id: 1, quantity: 1 }),
    });
    log("✓ 已加入评测商品");

    const order = await request("/api/orders", { method: "POST", headers: userHeaders() });
    log(`✓ 已创建订单：${order.order_no}`);

    await request("/api/payment/mock", {
      method: "POST",
      headers: userHeaders(),
      body: JSON.stringify({ order_id: order.id }),
    });
    log("✓ 模拟支付成功");

    const ticket = await request("/api/after-sales", {
      method: "POST",
      headers: userHeaders(),
      body: JSON.stringify({ order_id: order.id, type: "damage", reason: "商品破损，想申请退款" }),
    });
    state.ticketId = ticket.id;
    document.getElementById("ticketId").value = ticket.id;
    log(`✓ 已创建售后工单：${ticket.id}`);

    const admin = await login("admin", "admin123");
    state.adminToken = admin.token;
    await request("/api/knowledge", {
      method: "POST",
      headers: adminHeaders(),
      body: JSON.stringify({
        title: "售后演示政策",
        source: "demo/policy.md",
        content: "商品签收后七日内发生非人为损坏，可以申请退货退款。退款必须经过审核，金额超过一百元时由主管人工审批。",
      }),
    });
    log("✓ 已导入售后政策知识库");
    log("演示数据准备完成，可以运行 Agent。");
  } catch (error) {
    log(`✗ ${error.message}`);
  }
}

async function runAgent() {
  const ticketId = document.getElementById("ticketId").value.trim();
  const message = document.getElementById("message").value.trim();
  if (!state.userToken) {
    log("请先点击“一键准备演示数据”。");
    return;
  }
  if (!ticketId || !message) {
    log("请填写工单 ID 和售后描述。");
    return;
  }

  log("\n开始流式运行 Agent...");
  try {
    const response = await fetch(`/api/agent-runs/tickets/${ticketId}/stream`, {
      method: "POST",
      headers: userHeaders(),
      body: JSON.stringify({ message }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        const line = part.split("\n").find((item) => item.startsWith("data: "));
        if (!line) continue;
        const event = JSON.parse(line.slice(6));
        if (event.event === "node") {
          log(`→ ${event.step.node} (${event.step.duration_ms} ms)`);
        } else if (event.event === "completed") {
          log("\n结构化结果：\n" + JSON.stringify(event.run.output, null, 2));
          log(`\nRequest ID: ${event.run.request_id}`);
          log(`总耗时：${event.run.latency_ms} ms`);
        } else {
          log(JSON.stringify(event));
        }
      }
    }
  } catch (error) {
    log(`✗ ${error.message}`);
  }
}
