"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Sparkles } from "lucide-react";
import { useLocale } from "next-intl";

import { Button } from "@/components/ui";
import { ROUTES } from "@/lib/constants";

import { OnboardingShell } from "./onboarding-shell";
import { markOnboardingCompleted } from "./onboarding-state";

export function StepDone() {
  const router = useRouter();
  const isChinese = useLocale() === "zh";

  useEffect(() => {
    void markOnboardingCompleted();
  }, []);

  return (
    <OnboardingShell
      step="done"
      title={isChinese ? "设置完成" : "You're all set."}
      description={
        isChinese
          ? "工作区已准备好。试着向助手提问，它会使用你连接的数据。"
          : "Your workspace is ready. Try asking your assistant anything — it'll use the data you connected."
      }
      hideSkip
    >
      <div className="border-border bg-card flex items-center gap-4 rounded-xl border p-6">
        <div className="bg-muted text-foreground flex h-12 w-12 items-center justify-center rounded-lg">
          <Sparkles className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <p className="text-foreground text-base font-semibold">
            {isChinese ? "开始第一次对话" : "Open your first chat"}
          </p>
          <p className="text-muted-foreground mt-0.5 text-sm">
            {isChinese
              ? "系统会预填一条示例提示词，让你直接看到流式输出和工具调用。"
              : "We'll prefill a starter prompt so you see streaming + tools in action."}
          </p>
        </div>
      </div>

      <div className="mt-8 flex items-center gap-3">
        <Button size="lg" onClick={() => router.push(`${ROUTES.CHAT}?onboarding=1`)}>
          {isChinese ? "打开聊天" : "Open chat"}
          <ArrowRight className="h-4 w-4" />
        </Button>
        <Button size="lg" variant="ghost" onClick={() => router.push(ROUTES.DASHBOARD)}>
          {isChinese ? "进入仪表盘" : "Go to dashboard"}
        </Button>
      </div>
    </OnboardingShell>
  );
}
