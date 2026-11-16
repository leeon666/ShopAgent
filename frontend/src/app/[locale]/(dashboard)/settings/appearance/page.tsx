"use client";

import { SectionCard } from "@/components/settings/settings-section";
import { ThemeToggle } from "@/components/theme";
import { useLocale } from "next-intl";

export default function AppearanceSettingsPage() {
  const isChinese = useLocale() === "zh";
  return (
    <div className="space-y-6">
      <SectionCard
        title={isChinese ? "主题" : "Theme"}
        description={
          isChinese
            ? "选择浅色、深色，或跟随系统设置。"
            : "Light, dark, or follow your system preference."
        }
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-foreground text-sm font-medium">
              {isChinese ? "配色方案" : "Color scheme"}
            </p>
            <p className="text-muted-foreground mt-0.5 text-xs leading-relaxed">
              {isChinese
                ? "该设置会影响整个工作台。营销页面会按版块自动切换配色。"
                : "Affects the entire dashboard. Marketing pages alternate sections regardless."}
            </p>
          </div>
          <div className="shrink-0">
            <ThemeToggle variant="dropdown" />
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
