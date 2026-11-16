"use client";

import type { ReactNode } from "react";
import { Bell, Palette, Shield, Slash, UserCircle } from "lucide-react";
import { useLocale } from "next-intl";

import { ROUTES } from "@/lib/constants";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageTabs, type PageTab } from "@/components/dashboard/page-tabs";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const isChinese = useLocale() === "zh";
  const tabs: PageTab[] = [
    {
      label: isChinese ? "个人资料" : "Profile",
      href: ROUTES.SETTINGS_PROFILE,
      icon: UserCircle,
    },
    {
      label: isChinese ? "账户安全" : "Account",
      href: ROUTES.SETTINGS_ACCOUNT,
      icon: Shield,
    },
    {
      label: isChinese ? "快捷命令" : "Slash commands",
      href: ROUTES.SETTINGS_SLASH_COMMANDS,
      icon: Slash,
    },
    {
      label: isChinese ? "通知设置" : "Notifications",
      href: ROUTES.SETTINGS_NOTIFICATIONS,
      icon: Bell,
    },
    {
      label: isChinese ? "外观设置" : "Appearance",
      href: ROUTES.SETTINGS_APPEARANCE,
      icon: Palette,
    },
  ];

  return (
    <div className="space-y-6 pb-8">
      <PageHeader
        eyebrow={isChinese ? "设置中心" : "Settings"}
        title={isChinese ? "设置" : "Settings"}
        description={
          isChinese
            ? "管理个人资料、账户安全、外观、通知和快捷命令。"
            : "Manage your account, appearance, notifications, and slash commands."
        }
      />
      <PageTabs tabs={tabs} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
