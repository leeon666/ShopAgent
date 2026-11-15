import Link from "next/link";
import { useLocale } from "next-intl";
import {
  BookOpen,
  Database,
  MessageSquare,
  Settings,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { BACKEND_URL, ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface Action {
  label: string;
  icon: LucideIcon;
  href: string;
  external?: boolean;
  featured?: boolean;
}

export function QuickActions() {
  const isChinese = useLocale() === "zh";
  const actions: Action[] = [
    {
      label: isChinese ? "开始聊天" : "Start a chat",
      icon: MessageSquare,
      href: ROUTES.CHAT,
      featured: true,
    },
    { label: isChinese ? "上传到知识库" : "Upload to KB", icon: Database, href: ROUTES.RAG },
    { label: isChinese ? "设置" : "Settings", icon: Settings, href: ROUTES.SETTINGS },
    {
      label: isChinese ? "API 文档" : "API docs",
      icon: BookOpen,
      href: `${BACKEND_URL}/docs`,
      external: true,
    },
  ];
  return (
    <div className="border-border bg-card rounded-xl border p-4 sm:p-5">
      <h2 className="text-foreground/55 mb-2.5 font-mono text-[11px] tracking-wider uppercase">
        {isChinese ? "快捷操作" : "Quick actions"}
      </h2>
      <div className="flex flex-wrap gap-1.5">
        {actions.map((action) => (
          <ActionPill key={action.label} action={action} />
        ))}
      </div>
    </div>
  );
}

function ActionPill({ action }: { action: Action }) {
  const inner = (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
        action.featured
          ? "bg-foreground text-background border-foreground hover:bg-foreground/90"
          : "border-foreground/15 text-foreground hover:border-foreground/40 hover:bg-foreground/[0.04]",
      )}
    >
      <action.icon className="h-3.5 w-3.5 shrink-0" />
      {action.label}
    </span>
  );

  if (action.external) {
    return (
      <a href={action.href} target="_blank" rel="noopener noreferrer">
        {inner}
      </a>
    );
  }
  return <Link href={action.href}>{inner}</Link>;
}
