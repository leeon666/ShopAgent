"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useLocale } from "next-intl";
import { Database, List, MessageSquare, Plus, Star } from "lucide-react";
import { ActiveSessions } from "@/components/dashboard/active-sessions";
import { OnboardingBanner } from "@/components/dashboard/onboarding-banner";
import { PageHeader } from "@/components/dashboard/page-header";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { StatCard } from "@/components/dashboard/stat-card";
import { Button } from "@/components/ui";
import { useAuth } from "@/hooks";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { getCollectionInfo, listCollections } from "@/lib/rag-api";
import { cn, isAppAdmin } from "@/lib/utils";
import type { HealthResponse } from "@/types";
interface ConversationsResponse {
  total?: number;
  items: Array<{ id: string }>;
}

function getGreeting(isChinese = false): string {
  const hour = new Date().getHours();
  if (isChinese) {
    if (hour < 12) return "早上好";
    if (hour < 18) return "下午好";
    return "晚上好";
  }
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function DashboardPage() {
  const { user } = useAuth();
  const isChinese = useLocale() === "zh";

  // All independent → run in parallel, cached by React Query.
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get<HealthResponse>("/health"),
    staleTime: 60_000,
  });
  const conversations = useQuery({
    queryKey: ["conversations", "count"],
    queryFn: async () => {
      const d = await apiClient.get<ConversationsResponse>("/conversations?limit=1");
      return d.total ?? d.items?.length ?? 0;
    },
  });
  const rag = useQuery({
    queryKey: ["rag", "stats"],
    queryFn: async () => {
      const list = await listCollections();
      const infos = await Promise.all(
        list.items.map((name) => getCollectionInfo(name).catch(() => null)),
      );
      return {
        collections: list.items.length,
        vectors: infos.reduce((s, i) => s + (i?.total_vectors ?? 0), 0),
      };
    },
  });

  const firstName = user?.full_name?.split(" ")[0] || user?.email?.split("@")[0];
  const healthy = !health.isError;

  return (
    <div className="space-y-6 pb-8">
      <OnboardingBanner />

      <PageHeader
        eyebrow={isChinese ? "仪表盘" : "Dashboard"}
        title={firstName ? `${getGreeting(isChinese)}, ${firstName}` : getGreeting(isChinese)}
        description={
          isChinese
            ? "查看今天的工作区运行情况。"
            : "Here's what's happening with your workspace today."
        }
        actions={
          <Button asChild>
            <Link href={ROUTES.CHAT}>
              <Plus className="h-4 w-4" />
              {isChinese ? "新建对话" : "New chat"}
            </Link>
          </Button>
        }
      />

      <div className="border-border bg-card flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border px-4 py-3 text-sm">
        <span className="inline-flex items-center gap-2">
          <span
            aria-hidden
            className={cn(
              "inline-block h-2 w-2 rounded-full",
              healthy ? "bg-emerald-500" : "bg-destructive",
            )}
          />
          <span className="text-foreground font-medium">
            {healthy
              ? health.data?.status === "healthy" && isChinese
                ? "运行正常"
                : health.data?.status || (isChinese ? "运行正常" : "Operational")
              : isChinese
                ? "API 离线"
                : "API offline"}
          </span>
        </span>
        {health.data?.version && (
          <span className="text-muted-foreground font-mono text-xs">v{health.data.version}</span>
        )}
        <span className="text-muted-foreground inline-flex items-center gap-1.5 text-xs">
          <Database className="h-3.5 w-3.5" />
          {rag.data
            ? isChinese
              ? `${rag.data.collections} 个集合`
              : `${rag.data.collections} collections`
            : "—"}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-muted-foreground font-mono text-xs tracking-wider uppercase">
          {isChinese ? "工作区指标" : "Workspace metrics"}
        </h2>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={isChinese ? "对话" : "Conversations"}
          value={conversations.isLoading ? "—" : (conversations.data ?? 0).toLocaleString()}
          icon={MessageSquare}
          footer={isChinese ? "全部聊天" : "across all chats"}
          loading={conversations.isLoading}
        />
        <StatCard
          label={isChinese ? "知识库" : "Knowledge base"}
          value={rag.data ? rag.data.vectors.toLocaleString() : "—"}
          unit={
            rag.data
              ? isChinese
                ? "个向量"
                : `vector${rag.data.vectors === 1 ? "" : "s"}`
              : undefined
          }
          icon={Database}
          footer={
            rag.data
              ? isChinese
                ? `已索引 ${rag.data.collections} 个集合`
                : `${rag.data.collections} collection${rag.data.collections === 1 ? "" : "s"} indexed`
              : isChinese
                ? "已索引向量"
                : "indexed vectors"
          }
          loading={rag.isLoading}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <RecentActivity />
      </div>

      <div className="grid gap-4 lg:grid-cols-2"></div>
      <ActiveSessions />

      <QuickActions />

      {isAppAdmin(user) && (
        <div>
          <h2 className="font-display text-foreground mb-3 text-base font-semibold">
            {isChinese ? "管理操作" : "Admin actions"}
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <AdminTile
              icon={Star}
              label={isChinese ? "响应评分" : "Response ratings"}
              description={isChinese ? "查看和管理用户评分" : "View and manage ratings"}
              href={ROUTES.ADMIN_RATINGS}
            />
            <AdminTile
              icon={List}
              label={isChinese ? "所有对话" : "All conversations"}
              description={isChinese ? "查看任意用户的聊天" : "Inspect any user's chats"}
              href={ROUTES.ADMIN_CONVERSATIONS}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function AdminTile({
  icon: Icon,
  label,
  description,
  href,
}: {
  icon: typeof Star;
  label: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="border-border hover:border-foreground/30 bg-card hover:bg-accent flex items-center gap-3 rounded-xl border p-4 transition-colors"
    >
      <span className="bg-foreground/8 text-foreground flex h-9 w-9 items-center justify-center rounded-full">
        <Icon className="h-4 w-4" />
      </span>
      <div className="flex-1">
        <p className="text-foreground text-sm font-semibold">{label}</p>
        <p className="text-muted-foreground text-xs">{description}</p>
      </div>
    </Link>
  );
}
