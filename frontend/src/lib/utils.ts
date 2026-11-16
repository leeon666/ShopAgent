import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function getRuntimeLocale(): "zh-CN" | "en-US" {
  if (typeof document !== "undefined" && document.documentElement.lang.startsWith("en")) {
    return "en-US";
  }
  return "zh-CN";
}

export function uiText(chinese: string, english: string): string {
  return getRuntimeLocale() === "zh-CN" ? chinese : english;
}

export function getErrorMessage(err: unknown, fallback = "发生未知错误"): string {
  return err instanceof Error ? err.message : fallback;
}

export function isAppAdmin(user: { role?: string } | null | undefined): boolean {
  return user?.role === "admin";
}

export function setUrlParam(key: string, value: string | null): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (value === null) {
    url.searchParams.delete(key);
  } else {
    url.searchParams.set(key, value);
  }
  window.history.replaceState({}, "", url.toString());
}

export function getPasswordStrength(pw: string): { score: number; label: string; color: string } {
  if (!pw) return { score: 0, label: "", color: "" };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^a-zA-Z0-9]/.test(pw)) score++;
  if (score <= 1) return { score: 1, label: uiText("弱", "Weak"), color: "bg-destructive" };
  if (score <= 2) return { score: 2, label: uiText("一般", "Fair"), color: "bg-orange-500" };
  if (score <= 3) return { score: 3, label: uiText("良好", "Good"), color: "bg-yellow-500" };
  return { score: 4, label: uiText("很强", "Strong"), color: "bg-brand" };
}

export const MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024;

export const MAX_UPLOAD_SIZE_MB = parseInt(process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB || "50", 10);

export function formatBytes(bytes: number): string {
  if (!bytes || bytes < 0) return "0 B";
  const KB = 1024;
  const MB = KB * 1024;
  const GB = MB * 1024;
  if (bytes >= GB) return `${(bytes / GB).toFixed(2)} GB`;
  if (bytes >= MB) return `${(bytes / MB).toFixed(1)} MB`;
  if (bytes >= KB) return `${(bytes / KB).toFixed(1)} KB`;
  return `${bytes} B`;
}

export function timeAgo(dateStr: string): string {
  const then = new Date(dateStr).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Math.round((Date.now() - then) / 1000);
  if (diff < 0) return "";
  const minutes = Math.floor(diff / 60);
  const hours = Math.floor(diff / 3600);
  const days = Math.floor(diff / 86400);
  if (diff < 60) return uiText("刚刚", "just now");
  if (diff < 3600) return uiText(`${minutes} 分钟前`, `${minutes}m ago`);
  if (diff < 86400) return uiText(`${hours} 小时前`, `${hours}h ago`);
  if (diff < 86400 * 7) return uiText(`${days} 天前`, `${days}d ago`);
  return new Date(dateStr).toLocaleDateString(getRuntimeLocale(), {
    month: "short",
    day: "numeric",
  });
}

export function formatCurrency(
  amountCents: number,
  currency = "USD",
  minimumFractionDigits = 0,
): string {
  return (amountCents / 100).toLocaleString(getRuntimeLocale(), {
    style: "currency",
    currency: currency.toUpperCase(),
    minimumFractionDigits,
  });
}

export function formatDate(date: Date | string | null | undefined): string {
  if (!date) return "—";
  const d = typeof date === "string" ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(getRuntimeLocale(), {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleString(getRuntimeLocale(), {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + "...";
}
