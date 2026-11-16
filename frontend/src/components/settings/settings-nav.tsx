"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale } from "next-intl";
import { Bell, Palette, Shield, Slash, UserCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  description: string;
}

export function SettingsNav() {
  const pathname = usePathname();
  const isChinese = useLocale() === "zh";
  const stripped = pathname.replace(/^\/[a-z]{2}/, "");
  const items: NavItem[] = [
    {
      label: isChinese ? "个人资料" : "Profile",
      href: ROUTES.SETTINGS_PROFILE,
      icon: UserCircle,
      description: isChinese ? "头像、姓名、邮箱与登录会话" : "Avatar, name, email, sessions",
    },
    {
      label: isChinese ? "账户安全" : "Account",
      href: ROUTES.SETTINGS_ACCOUNT,
      icon: Shield,
      description: isChinese ? "密码、双重验证与危险操作" : "Password, two-factor, danger zone",
    },
    {
      label: isChinese ? "快捷命令" : "Slash commands",
      href: ROUTES.SETTINGS_SLASH_COMMANDS,
      icon: Slash,
      description: isChinese ? "自定义快捷命令与内置开关" : "Custom shortcuts + built-in toggles",
    },
    {
      label: isChinese ? "通知设置" : "Notifications",
      href: ROUTES.SETTINGS_NOTIFICATIONS,
      icon: Bell,
      description: isChinese ? "选择需要通过邮件通知的事件" : "What we email you about",
    },
    {
      label: isChinese ? "外观设置" : "Appearance",
      href: ROUTES.SETTINGS_APPEARANCE,
      icon: Palette,
      description: isChinese ? "主题、密度与品牌颜色" : "Theme, density, brand color",
    },
  ];

  return (
    <>
      <nav className="hidden lg:block">
        <ul className="space-y-1">
          {items.map((item) => {
            const active = stripped === item.href || stripped.startsWith(item.href + "/");
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "group flex items-start gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
                    active
                      ? "bg-foreground text-background"
                      : "text-foreground/65 hover:bg-foreground/5 hover:text-foreground",
                  )}
                >
                  <item.icon
                    className={cn(
                      "mt-0.5 h-4 w-4 shrink-0",
                      active ? "text-background" : "text-foreground/40 group-hover:text-foreground",
                    )}
                  />
                  <div className="min-w-0">
                    <p className="font-semibold">{item.label}</p>
                    <p
                      className={cn(
                        "mt-0.5 text-xs",
                        active ? "text-background/65" : "text-foreground/45",
                      )}
                    >
                      {item.description}
                    </p>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <nav className="-mx-3 flex scrollbar-thin gap-1.5 overflow-x-auto px-3 pb-2 lg:hidden">
        {items.map((item) => {
          const active = stripped === item.href || stripped.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "border-foreground/15 inline-flex shrink-0 items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                active
                  ? "bg-foreground text-background border-foreground"
                  : "text-foreground/65 hover:text-foreground hover:border-foreground/40",
              )}
            >
              <item.icon className="h-3.5 w-3.5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
