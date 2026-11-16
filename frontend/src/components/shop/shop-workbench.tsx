"use client";

import { useMemo, useState } from "react";
import { useLocale } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BadgeCheck,
  Box,
  ClipboardCheck,
  FileSearch,
  MessageCircleQuestion,
  PackageCheck,
  RefreshCw,
  Sparkles,
} from "lucide-react";

import {
  ChatContainer,
  type ChatEmptyPrompt,
  type ChatPromptRequest,
} from "@/components/chat/chat-container";
import { Badge, Button, Card } from "@/components/ui";
import { useAuth } from "@/hooks";
import { apiClient } from "@/lib/api-client";
import { cn, isAppAdmin } from "@/lib/utils";

interface OrderItem {
  id: string;
  product_name: string;
  quantity: number;
  price: string;
}

interface Order {
  id: string;
  order_no: string;
  status: string;
  total_amount: string;
  created_at: string;
  items: OrderItem[];
}

interface Ticket {
  id: string;
  ticket_no: string;
  order_id: string;
  type: string;
  reason: string;
  status: string;
  refund_amount: string | null;
  created_at: string;
}

interface Proposal {
  id: string;
  proposal_no: string;
  ticket_id: string;
  ticket_no?: string | null;
  ticket_type?: string | null;
  ticket_status?: string | null;
  ticket_reason?: string | null;
  order_id?: string | null;
  order_no?: string | null;
  user_id: string;
  user_email?: string | null;
  recommended_action: string;
  refund_amount: string | null;
  rationale: string;
  status: string;
  evidence: Array<{ source?: string; quote?: string }>;
  created_at: string;
}

interface AgentStep {
  id: string;
  node: string;
  status: string;
  latency_ms: number;
  tool_name: string | null;
}

interface AgentRun {
  id: string;
  trace_id: string;
  status: string;
  stop_reason: string | null;
  total_tokens: number;
  latency_ms: number;
  created_at: string;
  steps: AgentStep[];
}

interface ListResponse<T> {
  items: T[];
  total: number;
}

const STATUS_TONE: Record<string, string> = {
  pending: "bg-amber-500/10 text-amber-700",
  paid: "bg-emerald-500/10 text-emerald-700",
  completed: "bg-sky-500/10 text-sky-700",
  waiting_approval: "bg-orange-500/10 text-orange-700",
  approved: "bg-emerald-500/10 text-emerald-700",
  rejected: "bg-red-500/10 text-red-700",
  refund_pending: "bg-violet-500/10 text-violet-700",
  refunded: "bg-teal-500/10 text-teal-700",
  resolved: "bg-teal-500/10 text-teal-700",
  failed: "bg-red-500/10 text-red-700",
};

const STATUS_LABELS_ZH: Record<string, string> = {
  pending: "待处理",
  paid: "已支付",
  completed: "已完成",
  waiting_approval: "待审批",
  approved: "已批准",
  rejected: "已拒绝",
  refund_pending: "退款处理中",
  refunded: "已退款",
  resolved: "已解决",
  failed: "失败",
  success: "成功",
  running: "运行中",
  cancelled: "已取消",
};

const ACTION_LABELS_ZH: Record<string, string> = {
  manual_review: "转人工复核",
  approve_refund: "批准退款",
  reject_refund: "拒绝退款",
  request_evidence: "补充证据",
  exchange: "换货",
  return_refund: "退货退款",
};

const TOOL_LABELS_ZH: Record<string, string> = {
  get_order: "查询订单",
  get_logistics: "查询物流",
  get_after_sales_ticket: "查询售后单",
  check_refund_eligibility: "校验退款资格",
  current_datetime: "获取当前时间",
  get_current_datetime: "获取当前时间",
  search_after_sales_policy: "检索售后政策",
  create_refund_proposal: "创建退款提案",
  ask_user: "向用户追问",
};

const STOP_REASON_ZH: Record<string, string> = {
  final_answer: "完成回答",
  user_cancelled: "用户取消",
  max_steps: "达到最大步骤数",
  token_budget: "达到 Token 预算",
  tool_failure: "工具调用失败",
  approval_required: "等待人工审批",
};

function statusLabel(status: string, isChinese: boolean): string {
  return isChinese ? (STATUS_LABELS_ZH[status] ?? status) : status;
}

function actionLabel(action: string, isChinese: boolean): string {
  return isChinese ? (ACTION_LABELS_ZH[action] ?? action) : action;
}

function toolLabel(name: string, isChinese: boolean): string {
  return isChinese ? (TOOL_LABELS_ZH[name] ?? name) : name;
}

function stopReasonLabel(reason: string | null, isChinese: boolean): string {
  if (!reason) return isChinese ? "无停止原因" : "no stop reason";
  return isChinese ? (STOP_REASON_ZH[reason] ?? reason) : reason;
}

const SHOP_PROMPTS: ChatEmptyPrompt[] = [
  {
    icon: PackageCheck,
    title: "检查物流异常",
    prompt: "请说明物流停滞 72 小时和超过七天分别应该怎么处理，并引用售后政策。",
  },
  {
    icon: FileSearch,
    title: "需要哪些售后证据",
    prompt: "商品破损和错发分别需要哪些证据？请引用政策来源。",
  },
  {
    icon: MessageCircleQuestion,
    title: "何时必须人工审批",
    prompt: "售后 Agent 必须把哪些高风险情况转人工？为什么不能直接退款？",
  },
  {
    icon: ClipboardCheck,
    title: "解释退换货规则",
    prompt: "请比较七天无理由退货、质量问题退货和换货的适用条件。",
  },
];

export function ShopWorkbench() {
  const isChinese = useLocale() === "zh";
  const { user } = useAuth();
  const admin = isAppAdmin(user);
  const queryClient = useQueryClient();
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);

  const ordersQuery = useQuery({
    queryKey: ["shop", "orders"],
    queryFn: () => apiClient.get<ListResponse<Order>>("/shop/orders?limit=100"),
  });
  const ticketsQuery = useQuery({
    queryKey: ["shop", "tickets"],
    queryFn: () => apiClient.get<ListResponse<Ticket>>("/shop/after-sales?limit=100"),
  });
  const proposalsQuery = useQuery({
    queryKey: ["shop", "proposals"],
    queryFn: () =>
      apiClient.get<ListResponse<Proposal>>(
        admin ? "/shop/admin/proposals?status=pending&limit=100" : "/shop/proposals?limit=100",
      ),
  });
  const runsQuery = useQuery({
    queryKey: ["shop", "runs", admin],
    queryFn: () =>
      apiClient.get<ListResponse<AgentRun>>(
        admin ? "/shop/admin/runs?limit=10" : "/shop/runs?limit=10",
      ),
  });

  const orders = useMemo(() => ordersQuery.data?.items ?? [], [ordersQuery.data]);
  const tickets = useMemo(() => ticketsQuery.data?.items ?? [], [ticketsQuery.data]);
  const proposals = useMemo(() => proposalsQuery.data?.items ?? [], [proposalsQuery.data]);
  const runs = useMemo(() => runsQuery.data?.items ?? [], [runsQuery.data]);
  const selectedOrder = useMemo(
    () => orders.find((order) => order.id === selectedOrderId) ?? orders[0],
    [orders, selectedOrderId],
  );
  const orderTickets = useMemo(
    () => tickets.filter((ticket) => ticket.order_id === selectedOrder?.id),
    [tickets, selectedOrder?.id],
  );
  const orderProposals = useMemo(() => {
    const ticketIds = new Set(orderTickets.map((ticket) => ticket.id));
    return proposals.filter((proposal) => ticketIds.has(proposal.ticket_id));
  }, [orderTickets, proposals]);
  const selectedTicket = useMemo(
    () => orderTickets.find((ticket) => ticket.id === selectedTicketId) ?? orderTickets[0] ?? null,
    [orderTickets, selectedTicketId],
  );
  const selectedProposal = useMemo(
    () => proposals.find((proposal) => proposal.id === selectedProposalId) ?? proposals[0] ?? null,
    [proposals, selectedProposalId],
  );

  const payMutation = useMutation({
    mutationFn: (orderId: string) => apiClient.post(`/shop/orders/${orderId}/pay`),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["shop", "orders"] });
    },
  });

  const decisionMutation = useMutation({
    mutationFn: ({
      proposalId,
      decision,
    }: {
      proposalId: string;
      decision: "approve" | "reject";
    }) =>
      apiClient.post(`/shop/admin/proposals/${proposalId}/decision`, {
        decision,
        note:
          decision === "approve" ? "Approved from ShopAgent workbench" : "Rejected after review",
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["shop", "proposals"] }),
        queryClient.invalidateQueries({ queryKey: ["shop", "tickets"] }),
        queryClient.invalidateQueries({ queryKey: ["shop", "orders"] }),
      ]);
    },
  });

  function askAgent() {
    const order = selectedOrder;
    const ticket = selectedTicket;
    if (!order) return;
    const ticketContext = ticket
      ? `售后单号 ${ticket.ticket_no}，类型 ${ticket.type}，当前状态 ${ticket.status}，用户描述：${ticket.reason}。`
      : "目前尚未创建售后工单，请先判断是否应该创建以及缺少什么材料。";
    const content =
      `请对订单 ${order.order_no} 做完整售后研判。` +
      `${ticketContext} 请查询订单与物流，检索售后政策并引用来源。` +
      "如果需要退款、退货、换货或拒绝，请只创建待人工审批提案，不得声称已经执行。";
    window.dispatchEvent(
      new CustomEvent<ChatPromptRequest>("shopagent:prompt", {
        detail: { id: crypto.randomUUID(), content },
      }),
    );
  }

  const loading =
    ordersQuery.isLoading ||
    ticketsQuery.isLoading ||
    proposalsQuery.isLoading ||
    runsQuery.isLoading;
  const pendingCount = tickets.filter((ticket) =>
    ["pending", "agent_review", "waiting_approval", "waiting_customer"].includes(ticket.status),
  ).length;

  return (
    <div className="grid gap-4 pb-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-muted-foreground font-mono text-[11px] tracking-[0.18em] uppercase">
            {isChinese ? "商城运营" : "Commerce operations"}
          </p>
          <h1 className="font-display mt-1 text-2xl font-semibold">售后 Agent 工作台</h1>
          <p className="text-muted-foreground mt-1 max-w-2xl text-sm">
            同一套业务数据里查看订单、工单、Agent 证据与退款提案。高风险动作只能由人工审批。
          </p>
          <p className="text-muted-foreground mt-1 max-w-2xl text-xs">
            {admin
              ? "管理员使用方式：从左侧待审批队列选择提案，核对关联工单、订单和证据后批准或拒绝。"
              : "使用方式：先点选左侧订单，再点“让 Agent 研判”。无需自己编写专业提示词，系统会自动带入订单和工单信息。"}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() =>
            Promise.all([
              ordersQuery.refetch(),
              ticketsQuery.refetch(),
              proposalsQuery.refetch(),
              runsQuery.refetch(),
            ])
          }
          disabled={loading}
        >
          <RefreshCw className="h-4 w-4" />
          刷新业务数据
        </Button>
      </div>

      <div className="order-2 grid gap-3 sm:grid-cols-2 xl:order-1 xl:grid-cols-4">
        <Metric icon={Box} label="订单" value={orders.length} note="当前登录用户" />
        <Metric icon={PackageCheck} label="开放工单" value={pendingCount} note="待处理或待审批" />
        <Metric
          icon={ClipboardCheck}
          label="待审批提案"
          value={proposals.filter((proposal) => proposal.status === "pending").length}
          note={admin ? "管理员队列" : "当前用户"}
        />
        <Metric icon={Sparkles} label="Agent 工具" value={8} note="查询、RAG、提案" />
      </div>

      <div
        data-testid="shop-workbench-grid"
        className="order-1 grid gap-4 xl:order-2 xl:h-[clamp(560px,calc(100vh-18rem),760px)] xl:grid-cols-[310px_minmax(0,1fr)_430px]"
      >
        <Card className="flex h-[580px] min-h-0 min-w-0 shrink-0 flex-col overflow-hidden p-0 xl:h-full">
          <div className="border-border border-b px-4 py-3">
            <p className="text-sm font-semibold">{admin ? "待审批队列" : "业务对象"}</p>
            <p className="text-muted-foreground mt-1 text-xs">
              {admin ? "所有用户提交的高风险售后提案" : "先选订单，再选关联售后单"}
            </p>
          </div>
          <div className="min-h-0 flex-1 scrollbar-thin overflow-y-auto p-2">
            {admin
              ? proposals.map((proposal) => {
                  const active = proposal.id === selectedProposal?.id;
                  return (
                    <button
                      key={proposal.id}
                      type="button"
                      onClick={() => setSelectedProposalId(proposal.id)}
                      className={cn(
                        "mb-2 w-full rounded-xl border p-3 text-left transition-colors",
                        active
                          ? "border-foreground/30 bg-accent"
                          : "hover:bg-accent/60 border-transparent",
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[11px]">{proposal.proposal_no}</span>
                        <Badge>{actionLabel(proposal.recommended_action, isChinese)}</Badge>
                      </div>
                      <p className="text-foreground mt-2 truncate text-sm font-medium">
                        {proposal.ticket_no || proposal.ticket_id}
                      </p>
                      <div className="text-muted-foreground mt-1 flex justify-between gap-2 text-xs">
                        <span className="truncate">{proposal.user_email || proposal.user_id}</span>
                        <span>
                          {proposal.refund_amount ? `¥${proposal.refund_amount}` : "未指定金额"}
                        </span>
                      </div>
                    </button>
                  );
                })
              : orders.map((order) => {
                  const relatedTickets = tickets.filter((ticket) => ticket.order_id === order.id);
                  const active = order.id === selectedOrder?.id;
                  return (
                    <button
                      key={order.id}
                      type="button"
                      onClick={() => {
                        setSelectedOrderId(order.id);
                        setSelectedTicketId(relatedTickets[0]?.id ?? null);
                      }}
                      className={cn(
                        "mb-2 w-full rounded-xl border p-3 text-left transition-colors",
                        active
                          ? "border-foreground/30 bg-accent"
                          : "hover:bg-accent/60 border-transparent",
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[11px]">{order.order_no}</span>
                        <Badge className={STATUS_TONE[order.status] ?? ""}>
                          {statusLabel(order.status, isChinese)}
                        </Badge>
                      </div>
                      <p className="mt-2 truncate text-sm font-medium">
                        {order.items.map((item) => item.product_name).join(" + ")}
                      </p>
                      <div className="text-muted-foreground mt-1 flex justify-between text-xs">
                        <span>¥{order.total_amount}</span>
                        <span>{relatedTickets.length} 个售后单</span>
                      </div>
                    </button>
                  );
                })}
            {admin && !proposals.length && !proposalsQuery.isLoading && (
              <p className="text-muted-foreground p-4 text-sm">暂无待审批提案。</p>
            )}
            {!admin && !orders.length && !ordersQuery.isLoading && (
              <p className="text-muted-foreground p-4 text-sm">
                暂无订单。运行 seed-shop 或先创建订单。
              </p>
            )}
          </div>
        </Card>

        <Card className="flex h-[580px] min-h-0 min-w-0 shrink-0 flex-col overflow-hidden p-0 xl:h-full">
          <div className="border-border flex flex-wrap items-center justify-between gap-2 border-b px-4 py-3">
            <div>
              <p className="text-sm font-semibold">
                {admin ? "待审批提案详情" : "订单与工单上下文"}
              </p>
              <p className="text-muted-foreground mt-1 text-xs">
                {admin
                  ? "核对客户、订单、工单和 Agent 证据后再作决定"
                  : "Agent 只能读取当前用户的订单与工单"}
              </p>
            </div>
            {!admin && (
              <Button onClick={askAgent} disabled={!selectedOrder}>
                <Sparkles className="h-4 w-4" />让 Agent 研判
              </Button>
            )}
          </div>
          <div className="min-h-0 flex-1 scrollbar-thin space-y-4 overflow-y-auto p-4">
            {admin && selectedProposal ? (
              <AdminProposalReview
                proposal={selectedProposal}
                isChinese={isChinese}
                onDecision={(decision) =>
                  decisionMutation.mutate({
                    proposalId: selectedProposal.id,
                    decision,
                  })
                }
                deciding={decisionMutation.isPending}
              />
            ) : selectedOrder ? (
              <>
                <section>
                  <div className="flex items-center justify-between">
                    <h2 className="font-mono text-sm font-semibold">{selectedOrder.order_no}</h2>
                    <Badge className={STATUS_TONE[selectedOrder.status] ?? ""}>
                      {statusLabel(selectedOrder.status, isChinese)}
                    </Badge>
                  </div>
                  <div className="mt-3 space-y-2">
                    {selectedOrder.items.map((item) => (
                      <div
                        key={item.id}
                        className="bg-muted/40 flex items-center justify-between rounded-lg px-3 py-2 text-sm"
                      >
                        <span>{item.product_name}</span>
                        <span className="text-muted-foreground">
                          ¥{item.price} × {item.quantity}
                        </span>
                      </div>
                    ))}
                  </div>
                  {selectedOrder.status === "pending" && (
                    <Button
                      className="mt-3"
                      size="sm"
                      variant="outline"
                      onClick={() => payMutation.mutate(selectedOrder.id)}
                      disabled={payMutation.isPending}
                    >
                      <BadgeCheck className="h-4 w-4" />
                      模拟支付
                    </Button>
                  )}
                </section>

                <section>
                  <h3 className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
                    关联售后单
                  </h3>
                  <div className="mt-2 space-y-2">
                    {orderTickets.map((ticket) => (
                      <button
                        key={ticket.id}
                        type="button"
                        onClick={() => setSelectedTicketId(ticket.id)}
                        className={cn(
                          "w-full rounded-xl border p-3 text-left",
                          ticket.id === selectedTicket?.id
                            ? "border-foreground/30 bg-accent"
                            : "border-border",
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs">{ticket.ticket_no}</span>
                          <Badge className={STATUS_TONE[ticket.status] ?? ""}>
                            {statusLabel(ticket.status, isChinese)}
                          </Badge>
                        </div>
                        <p className="text-muted-foreground mt-2 line-clamp-2 text-xs">
                          {ticket.reason}
                        </p>
                      </button>
                    ))}
                    {!orderTickets.length && (
                      <div className="border-border text-muted-foreground rounded-xl border border-dashed p-3 text-xs">
                        这个订单还没有售后单。可以直接让 Agent 判断是否需要创建。
                      </div>
                    )}
                  </div>
                </section>

                <section>
                  <h3 className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
                    {admin ? "待审批提案" : "我的提案"}
                  </h3>
                  <div className="mt-2 space-y-2">
                    {orderProposals.map((proposal) => (
                      <div key={proposal.id} className="border-border rounded-xl border p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs">{proposal.proposal_no}</span>
                          <Badge>{actionLabel(proposal.recommended_action, isChinese)}</Badge>
                        </div>
                        <p className="text-muted-foreground mt-2 text-xs">{proposal.rationale}</p>
                        <div className="mt-3 flex items-center justify-between gap-2">
                          <span className="text-xs">
                            退款 {proposal.refund_amount ? `¥${proposal.refund_amount}` : "未指定"}
                          </span>
                          {admin && proposal.status === "pending" && (
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={() =>
                                  decisionMutation.mutate({
                                    proposalId: proposal.id,
                                    decision: "approve",
                                  })
                                }
                              >
                                批准
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  decisionMutation.mutate({
                                    proposalId: proposal.id,
                                    decision: "reject",
                                  })
                                }
                              >
                                拒绝
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {!orderProposals.length && (
                      <div className="border-border text-muted-foreground rounded-xl border border-dashed p-3 text-xs">
                        暂无提案。让 Agent 研判后，高风险动作会出现在这里。
                      </div>
                    )}
                  </div>
                </section>

                <section>
                  <h3 className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
                    最近 Agent 运行记录
                  </h3>
                  <div className="mt-2 space-y-2">
                    {runs.slice(0, 4).map((run) => (
                      <div key={run.id} className="border-border rounded-xl border p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate font-mono text-[11px]">{run.trace_id}</span>
                          <Badge className={STATUS_TONE[run.status] ?? ""}>
                            {statusLabel(run.status, isChinese)}
                          </Badge>
                        </div>
                        <div className="text-muted-foreground mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
                          <span>{run.latency_ms} ms</span>
                          <span>{run.total_tokens} tokens</span>
                          <span>{stopReasonLabel(run.stop_reason, isChinese)}</span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {run.steps.map((step) => (
                            <span
                              key={step.id}
                              className={cn(
                                "rounded px-1.5 py-0.5 font-mono text-[10px]",
                                step.status === "success"
                                  ? "bg-emerald-500/10 text-emerald-700"
                                  : "bg-red-500/10 text-red-700",
                              )}
                            >
                              {toolLabel(step.tool_name || step.node, isChinese)} ·{" "}
                              {step.latency_ms}ms
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                    {!runs.length && (
                      <div className="border-border text-muted-foreground rounded-xl border border-dashed p-3 text-xs">
                        暂无 Agent Trace。发起一次研判后会记录耗时、Token 和工具步骤。
                      </div>
                    )}
                  </div>
                </section>
              </>
            ) : (
              <div className="text-muted-foreground flex h-full min-h-80 items-center justify-center text-sm">
                {loading ? "正在加载业务数据..." : admin ? "暂无待审批提案" : "暂无订单数据"}
              </div>
            )}
          </div>
        </Card>

        <Card
          data-testid="shop-agent-panel"
          className="flex h-[640px] min-w-0 shrink-0 flex-col overflow-hidden p-0 xl:h-full"
        >
          <div className="border-border border-b px-4 py-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <p className="text-sm font-semibold">Agent 研判台</p>
            </div>
            <p className="text-muted-foreground mt-1 text-xs">
              工具调用、政策引用和结构化结论会在这里展示
            </p>
          </div>
          <div className="min-h-0 flex-1">
            <ChatContainer emptyPrompts={SHOP_PROMPTS} />
          </div>
        </Card>
      </div>
    </div>
  );
}

function AdminProposalReview({
  proposal,
  isChinese,
  onDecision,
  deciding,
}: {
  proposal: Proposal;
  isChinese: boolean;
  onDecision: (decision: "approve" | "reject") => void;
  deciding: boolean;
}) {
  return (
    <div className="space-y-4">
      <section className="border-border bg-muted/30 rounded-xl border p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="font-mono text-xs font-semibold">{proposal.proposal_no}</p>
            <p className="text-muted-foreground mt-1 text-xs">
              {proposal.user_email || proposal.user_id}
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            <Badge>{actionLabel(proposal.recommended_action, isChinese)}</Badge>
            <Badge className={STATUS_TONE[proposal.status] ?? ""}>
              {statusLabel(proposal.status, isChinese)}
            </Badge>
          </div>
        </div>

        <dl className="mt-4 grid gap-3 text-xs sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">售后工单</dt>
            <dd className="text-foreground mt-0.5 font-mono">
              {proposal.ticket_no || proposal.ticket_id}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">关联订单</dt>
            <dd className="text-foreground mt-0.5 font-mono">
              {proposal.order_no || proposal.order_id || "未提供"}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">工单类型</dt>
            <dd className="text-foreground mt-0.5">{proposal.ticket_type || "未提供"}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">退款金额</dt>
            <dd className="text-foreground mt-0.5 font-medium">
              {proposal.refund_amount ? `¥${proposal.refund_amount}` : "未指定"}
            </dd>
          </div>
        </dl>

        {proposal.ticket_reason && (
          <div className="border-border mt-4 border-t pt-3">
            <p className="text-muted-foreground text-xs">客户描述</p>
            <p className="text-foreground mt-1 text-sm leading-relaxed">{proposal.ticket_reason}</p>
          </div>
        )}
      </section>

      <section className="border-border bg-card flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3">
        <p className="text-muted-foreground text-xs">
          批准后由后台任务处理退款；Agent 不会直接执行资金操作。
        </p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => onDecision("reject")} disabled={deciding}>
            拒绝
          </Button>
          <Button onClick={() => onDecision("approve")} disabled={deciding}>
            {deciding ? "处理中…" : "批准"}
          </Button>
        </div>
      </section>

      <section>
        <h3 className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
          Agent 处理依据
        </h3>
        <p className="text-foreground mt-2 text-sm leading-relaxed">{proposal.rationale}</p>
      </section>

      {proposal.evidence.length > 0 && (
        <section>
          <h3 className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
            证据与引用
          </h3>
          <ul className="mt-2 space-y-2">
            {proposal.evidence.map((evidence, index) => (
              <li
                key={`${evidence.source || "evidence"}-${index}`}
                className="border-border rounded-xl border p-3"
              >
                <p className="text-foreground font-mono text-[11px] font-medium">
                  {evidence.source || `证据 ${index + 1}`}
                </p>
                {evidence.quote && (
                  <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
                    {evidence.quote}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  note,
}: {
  icon: typeof Box;
  label: string;
  value: number;
  note: string;
}) {
  return (
    <Card className="flex items-center gap-3 p-4">
      <span className="bg-foreground/5 flex h-10 w-10 items-center justify-center rounded-full">
        <Icon className="h-4 w-4" />
      </span>
      <div>
        <p className="text-muted-foreground text-xs">{label}</p>
        <p className="text-xl font-semibold">{value}</p>
        <p className="text-muted-foreground text-[11px]">{note}</p>
      </div>
    </Card>
  );
}
