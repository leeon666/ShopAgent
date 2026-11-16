"use client";

import { useRouter } from "next/navigation";
import { ArrowRight, Database, MessageSquare, Users } from "lucide-react";
import { useLocale } from "next-intl";

import { Button } from "@/components/ui";
import { useAuth } from "@/hooks";

import { OnboardingShell } from "./onboarding-shell";

export function StepWelcome() {
  const router = useRouter();
  const isChinese = useLocale() === "zh";
  const { user } = useAuth();
  const perks = [
    {
      icon: MessageSquare,
      title: isChinese ? "选择 Agent 框架" : "Pick your agent",
      description: isChinese
        ? "选择驱动助手的 Agent 框架。"
        : "Choose the framework that powers your assistant.",
    },
    {
      icon: Database,
      title: isChinese ? "连接数据" : "Connect your data",
      description: isChinese
        ? "上传文档或同步云盘，系统会自动建立索引。"
        : "Upload docs or sync from Drive — we'll index them.",
    },
    {
      icon: Users,
      title: isChinese ? "邀请团队成员" : "Invite your team",
      description: isChinese
        ? "邀请同事加入，让团队共享同一套对话和知识。"
        : "Bring teammates so everyone's chats stay in sync.",
    },
  ];

  return (
    <OnboardingShell
      step="welcome"
      title={
        isChinese
          ? user?.full_name
            ? `欢迎你，${user.full_name.split(" ")[0]}。`
            : "欢迎使用 ShopAgent。"
          : user?.full_name
            ? `Welcome, ${user.full_name.split(" ")[0]}.`
            : "Welcome aboard."
      }
      description={
        isChinese
          ? "两分钟内完成基础设置。你可以跳过任意步骤，稍后再回来。"
          : "Let's get you set up in under 2 minutes. You can skip any step and come back later."
      }
    >
      <ul className="space-y-3">
        {perks.map((perk) => (
          <li
            key={perk.title}
            className="border-border bg-card flex items-start gap-4 rounded-xl border p-5"
          >
            <div className="bg-muted text-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded-lg">
              <perk.icon className="h-4 w-4" />
            </div>
            <div className="flex-1">
              <p className="text-foreground text-base font-semibold">{perk.title}</p>
              <p className="text-muted-foreground mt-0.5 text-sm">{perk.description}</p>
            </div>
          </li>
        ))}
      </ul>

      <Button size="lg" className="mt-8" onClick={() => router.push("/onboarding/agent")}>
        {isChinese ? "开始" : "Let's go"}
        <ArrowRight className="h-4 w-4" />
      </Button>
    </OnboardingShell>
  );
}
