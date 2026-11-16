"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Monitor, Shield, Smartphone } from "lucide-react";
import { useLocale } from "next-intl";

import { LoadingState } from "@/components/states";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { cn, timeAgo } from "@/lib/utils";
import type { Session, SessionListResponse } from "@/types";

const MAX_ROWS = 4;

function DeviceIcon({ type }: { type?: string | null }) {
  if (type === "mobile") return <Smartphone className="h-4 w-4" />;
  return <Monitor className="h-4 w-4" />;
}

export function ActiveSessions() {
  const isChinese = useLocale() === "zh";
  const [sessions, setSessions] = useState<Session[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<SessionListResponse>("/sessions")
      .then((d) => !cancelled && setSessions(d.sessions))
      .catch(() => !cancelled && setSessions([]));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="border-border bg-card flex flex-col rounded-xl border p-5 lg:p-6">
      <header className="flex items-end justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            {isChinese ? "活动登录会话" : "Active sessions"}
          </p>
          <h2 className="font-display text-foreground mt-1 text-xl font-semibold tracking-tight">
            {sessions
              ? isChinese
                ? `${sessions.length} 台已登录设备`
                : `${sessions.length} signed-in device${sessions.length === 1 ? "" : "s"}`
              : "—"}
          </h2>
        </div>
        <Link
          href={ROUTES.SETTINGS_PROFILE}
          className="text-foreground/55 hover:text-foreground inline-flex items-center gap-1 text-xs font-medium transition-colors"
        >
          {isChinese ? "管理" : "Revoke"}
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </header>

      <div className="mt-5">
        {sessions === null ? (
          <LoadingState variant="skeleton-list" rows={3} />
        ) : sessions.length === 0 ? (
          <div className="border-foreground/10 bg-card flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed py-8 text-center">
            <Shield className="text-foreground/30 h-7 w-7" />
            <p className="text-foreground/55 text-sm">
              {isChinese ? "暂无活动登录会话。" : "No active sessions tracked."}
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {sessions.slice(0, MAX_ROWS).map((s) => (
              <li
                key={s.id}
                className="border-border/60 bg-background/60 flex items-center gap-3 rounded-xl border p-3"
              >
                <span
                  className={cn(
                    "bg-foreground/8 text-foreground inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                    s.is_current && "bg-muted",
                  )}
                >
                  <DeviceIcon type={s.device_type} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-foreground truncate text-sm font-medium">
                    {s.device_name &&
                    !["unknown browser", "unknown device"].includes(s.device_name.toLowerCase())
                      ? s.device_name
                      : isChinese
                        ? "未知浏览器"
                        : "Unknown browser"}
                    {s.is_current && (
                      <span className="text-foreground/55 ml-2 font-mono text-[10px] tracking-wider uppercase">
                        {isChinese ? "当前设备" : "This device"}
                      </span>
                    )}
                  </p>
                  <p className="text-foreground/55 text-xs">
                    {s.ip_address ? `${s.ip_address} · ` : ""}
                    {isChinese ? "最后活动 " : "Active "}
                    {timeAgo(s.last_used_at)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
