"use client";

import { SlashCommandsManager } from "@/components/settings/slash-commands-manager";
import { useLocale } from "next-intl";

export default function SlashCommandsSettingsPage() {
  const isChinese = useLocale() === "zh";
  return (
    <div className="space-y-6">
      <section className="border-border bg-card rounded-xl border">
        <header className="border-border border-b px-5 py-4">
          <h2 className="text-foreground text-sm font-semibold">
            {isChinese ? "快捷命令" : "Slash commands"}
          </h2>
          <p className="text-muted-foreground mt-1 text-xs">
            {isChinese
              ? "自定义聊天中的 / 命令面板，可以关闭内置命令或创建自己的快捷提示词。"
              : "Customize the /command palette in chat — disable built-ins, or define your own quick prompts."}
          </p>
        </header>
        <div className="px-5 py-5">
          <SlashCommandsManager />
        </div>
      </section>
    </div>
  );
}
