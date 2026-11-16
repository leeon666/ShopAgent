"use client";

import type { ReactNode } from "react";
import { Activity, LayoutDashboard, MessageSquare, Star, Users } from "lucide-react";
import { useLocale } from "next-intl";

import { ROUTES } from "@/lib/constants";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageTabs, type PageTab } from "@/components/dashboard/page-tabs";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const isChinese = useLocale() === "zh";
  const tabs: PageTab[] = [
    {
      label: isChinese ? "概览" : "Overview",
      href: ROUTES.ADMIN,
      icon: LayoutDashboard,
      exact: true,
    },
    { label: isChinese ? "用户" : "Users", href: ROUTES.ADMIN_USERS, icon: Users },
    {
      label: isChinese ? "对话" : "Conversations",
      href: ROUTES.ADMIN_CONVERSATIONS,
      icon: MessageSquare,
    },
    { label: isChinese ? "回复评价" : "Ratings", href: ROUTES.ADMIN_RATINGS, icon: Star },
    { label: isChinese ? "系统状态" : "System", href: ROUTES.ADMIN_SYSTEM, icon: Activity },
  ];
  return (
    <div className="space-y-6 pb-8">
      <PageHeader
        eyebrow={isChinese ? "后台管理" : "Admin"}
        title={isChinese ? "工作区管理" : "Workspace administration"}
        description={
          isChinese
            ? "管理用户、对话、回复评价、账单事件和系统健康状态。"
            : "Users, conversations, ratings, billing webhooks, and system health."
        }
      />
      <PageTabs tabs={tabs} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
