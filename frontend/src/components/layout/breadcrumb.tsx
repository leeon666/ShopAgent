"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale } from "next-intl";
import { ChevronRight } from "lucide-react";
import { ROUTES } from "@/lib/constants";

export function Breadcrumb() {
  const pathname = usePathname();
  const isChinese = useLocale() === "zh";
  const routeLabels: Record<string, string> = {
    [ROUTES.DASHBOARD]: isChinese ? "仪表盘" : "Dashboard",
    [ROUTES.CHAT]: isChinese ? "聊天" : "Chat",
    [ROUTES.RAG]: isChinese ? "知识库" : "Knowledge Base",
    [ROUTES.PROFILE]: isChinese ? "个人资料" : "Profile",
    "/settings": isChinese ? "设置" : "Settings",
  };

  const segments = pathname?.split("/").filter(Boolean) || [];
  const routeSegments = segments.length > 1 ? segments.slice(1) : segments;

  if (routeSegments.length <= 1) return null;

  const crumbs = routeSegments.map((_, i) => {
    const path = "/" + routeSegments.slice(0, i + 1).join("/");
    const segment = routeSegments[i] ?? "";
    const label = routeLabels[path] || segment.charAt(0).toUpperCase() + segment.slice(1);
    const isLast = i === routeSegments.length - 1;
    return { path, label, isLast };
  });

  return (
    <nav
      aria-label={isChinese ? "面包屑导航" : "Breadcrumb"}
      className="mb-4 flex items-center gap-1 text-sm"
    >
      {crumbs.map((crumb, i) => (
        <span key={crumb.path} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="text-muted-foreground h-3 w-3" />}
          {crumb.isLast ? (
            <span className="text-foreground font-medium">{crumb.label}</span>
          ) : (
            <Link
              href={crumb.path}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}
