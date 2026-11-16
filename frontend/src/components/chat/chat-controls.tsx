"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, ChevronDown, Cpu, Settings2, Sliders } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useLocale } from "next-intl";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui";
import { useConversationStore } from "@/stores";
import { cn } from "@/lib/utils";

type ThinkingEffort = "off" | "low" | "medium" | "high";
type Tab = "model" | "settings";

interface ChatControlsProps {
  onModelChange?: (model: string | null) => void;
  onTemperatureChange?: (value: number | null) => void;
  onThinkingEffortChange?: (value: "low" | "medium" | "high" | null) => void;
}

const EFFORT_OPTIONS: {
  label: string;
  labelZh: string;
  value: ThinkingEffort;
  hint: string;
  hintZh: string;
}[] = [
  {
    label: "Off",
    labelZh: "关闭",
    value: "off",
    hint: "Direct answer, no reasoning",
    hintZh: "直接回答，不进行推理",
  },
  { label: "Low", labelZh: "低", value: "low", hint: "Quick reasoning", hintZh: "快速推理" },
  { label: "Medium", labelZh: "中", value: "medium", hint: "Balanced", hintZh: "速度与深度平衡" },
  {
    label: "High",
    labelZh: "高",
    value: "high",
    hint: "Deep, slower",
    hintZh: "推理更深入，速度更慢",
  },
];

/**
 * Unified popover panel that replaces the 3 separate triggers (KB / Model /
 * Chat settings) with a single button that summarizes current state and opens
 * a tabbed control surface.
 */
export function ChatControls({
  onModelChange,
  onTemperatureChange,
  onThinkingEffortChange,
}: ChatControlsProps) {
  const isChinese = useLocale() === "zh";
  const [tab, setTab] = useState<Tab>("model");
  const { currentConversationId } = useConversationStore();

  const [availableModels, setAvailableModels] = useState<{ value: string; label: string }[]>([
    { value: "", label: isChinese ? "默认" : "Default" },
  ]);
  const [selectedModel, setSelectedModel] = useState<{ value: string; label: string }>({
    value: "",
    label: isChinese ? "默认" : "Default",
  });

  useEffect(() => {
    // Fetch model list once on mount. `onModelChange` is intentionally NOT in
    // deps — parents (use-chat) pass an inline arrow each render, so depending
    // on it triggers a refetch every render → infinite loop during streaming.
    fetch("/api/v1/agent/models", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.models) {
          const models = [
            { value: "", label: `${isChinese ? "默认" : "Default"} (${data.default})` },
            ...data.models.map((m: string) => ({ value: m, label: m })),
          ];
          setAvailableModels(models);
          setSelectedModel(models[0]);
        }
      })
      .catch(() => {});
  }, [isChinese]);

  const [temperature, setTemperature] = useState<number | null>(null);
  const [effort, setEffort] = useState<ThinkingEffort>("off");
  const settingsOverridden = temperature !== null || effort !== "off";

  const triggerSummary = useMemo(() => {
    const parts: string[] = [];
    if (selectedModel.value) parts.push(selectedModel.value);
    if (settingsOverridden) parts.push(isChinese ? "自定义" : "Custom");
    return parts.length ? parts.join(" · ") : isChinese ? "控制项" : "Controls";
  }, [selectedModel, settingsOverridden, isChinese]);

  const hasOverrides = selectedModel.value !== "" || settingsOverridden;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={isChinese ? "聊天控制项" : "Chat controls"}
          className={cn(
            "border-foreground/10 bg-card hover:border-foreground/25 hover:bg-foreground/[0.04] inline-flex items-center gap-1.5 rounded-full border py-1 pr-2 pl-2.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
            hasOverrides ? "text-foreground" : "text-foreground/65",
          )}
        >
          <Sliders className="h-3 w-3" />
          <span className="max-w-[200px] truncate">{triggerSummary}</span>
          {hasOverrides && (
            <span aria-hidden className="bg-foreground inline-block h-1 w-1 rounded-full" />
          )}
          <ChevronDown className="text-foreground/45 h-3 w-3" />
        </button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="border-border bg-popover relative w-[380px] overflow-hidden rounded-2xl border p-0 shadow-md"
      >
        <div className="border-foreground/10 flex items-center gap-1 border-b p-2">
          {onModelChange && (
            <TabButton
              icon={Cpu}
              label={isChinese ? "模型" : "Model"}
              active={tab === "model"}
              onClick={() => setTab("model")}
            />
          )}
          {onTemperatureChange && onThinkingEffortChange && (
            <TabButton
              icon={Settings2}
              label={isChinese ? "设置" : "Settings"}
              active={tab === "settings"}
              onClick={() => setTab("settings")}
            />
          )}
        </div>

        <div className="max-h-[420px] scrollbar-thin overflow-y-auto p-4">
          {tab === "model" && (
            <ModelPanel
              models={availableModels}
              selected={selectedModel}
              onPick={(m) => {
                setSelectedModel(m);
                onModelChange?.(m.value || null);
              }}
            />
          )}
          {tab === "settings" && (
            <SettingsPanel
              temperature={temperature}
              effort={effort}
              onTemperatureChange={(v) => {
                setTemperature(v);
                onTemperatureChange?.(v);
              }}
              onEffortChange={(v) => {
                setEffort(v);
                onThinkingEffortChange?.(v === "off" ? null : v);
              }}
            />
          )}
        </div>

        <div className="border-foreground/10 text-foreground/45 flex items-center justify-between border-t px-4 py-2 font-mono text-[10px] tracking-wider uppercase">
          <span className="inline-flex items-center gap-1.5">
            <span
              aria-hidden
              className="bg-foreground inline-block h-1 w-1 animate-pulse rounded-full"
            />
            {currentConversationId
              ? isChinese
                ? "已保存到此对话"
                : "Saved for this chat"
              : isChinese
                ? "发送后保存"
                : "Saves on send"}
          </span>
          <span>{isChinese ? "按 Esc 关闭" : "esc to close"}</span>
        </div>
      </PopoverContent>
    </Popover>
  );
}

function TabButton({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex flex-1 items-center justify-center gap-1.5 rounded-full px-3 py-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
        active
          ? "bg-foreground text-background"
          : "text-foreground/55 hover:bg-foreground/[0.04] hover:text-foreground",
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </button>
  );
}

/** Model picker panel. */
function ModelPanel({
  models,
  selected,
  onPick,
}: {
  models: { value: string; label: string }[];
  selected: { value: string; label: string };
  onPick: (m: { value: string; label: string }) => void;
}) {
  const isChinese = useLocale() === "zh";
  return (
    <div>
      <p className="text-foreground mb-1 text-sm font-semibold">{isChinese ? "模型" : "Model"}</p>
      <p className="text-foreground/55 mb-4 text-xs leading-relaxed">
        {isChinese ? "选择处理当前对话的模型。" : "Pick the model that handles this conversation."}
      </p>
      <ul className="space-y-1">
        {models.map((m) => {
          const isActive = selected.value === m.value;
          return (
            <li key={m.value || "default"}>
              <button
                type="button"
                onClick={() => onPick(m)}
                className={cn(
                  "flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-xs transition-all",
                  isActive
                    ? "border-foreground/30 bg-accent text-foreground"
                    : "border-border text-foreground/75 hover:border-foreground/25 hover:bg-accent/60 hover:text-foreground",
                )}
              >
                <span className="truncate font-medium">{m.label}</span>
                {isActive && <Check className="text-foreground h-3.5 w-3.5 shrink-0" />}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Chat settings panel — temperature + thinking effort. */
function SettingsPanel({
  temperature,
  effort,
  onTemperatureChange,
  onEffortChange,
}: {
  temperature: number | null;
  effort: ThinkingEffort;
  onTemperatureChange: (v: number | null) => void;
  onEffortChange: (v: ThinkingEffort) => void;
}) {
  const isChinese = useLocale() === "zh";
  return (
    <div className="space-y-6">
      <div className="space-y-2.5">
        <div className="flex items-baseline justify-between">
          <label htmlFor="chat-temp" className="text-foreground text-sm font-semibold">
            {isChinese ? "温度" : "Temperature"}
          </label>
          <span className="text-foreground font-mono text-xs tabular-nums">
            {temperature === null ? (
              <span className="text-foreground/55">{isChinese ? "默认" : "default"}</span>
            ) : (
              temperature.toFixed(2)
            )}
          </span>
        </div>
        <input
          id="chat-temp"
          type="range"
          min={0}
          max={2}
          step={0.05}
          value={temperature ?? 0.7}
          onChange={(e) => onTemperatureChange(parseFloat(e.target.value))}
          className="bg-foreground/15 h-1.5 w-full cursor-pointer appearance-none rounded-full accent-[var(--color-brand)]"
        />
        <div className="text-foreground/45 flex justify-between font-mono text-[10px] tracking-wider uppercase">
          <span>{isChinese ? "更聚焦" : "focused"}</span>
          <span>{isChinese ? "更发散" : "creative"}</span>
        </div>
        {temperature !== null && (
          <button
            type="button"
            onClick={() => onTemperatureChange(null)}
            className="text-foreground/55 hover:text-foreground text-[11px] underline-offset-2 hover:underline"
          >
            {isChinese ? "恢复服务端默认值" : "Reset to server default"}
          </button>
        )}
      </div>

      <div className="space-y-2.5">
        <div className="flex items-baseline justify-between">
          <span className="text-foreground text-sm font-semibold">
            {isChinese ? "思考强度" : "Thinking effort"}
          </span>
          <span className="text-foreground/45 text-[10px]">
            {isChinese ? "取决于模型" : "model-dependent"}
          </span>
        </div>
        <div className="grid grid-cols-4 gap-1">
          {EFFORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onEffortChange(opt.value)}
              className={cn(
                "rounded-lg px-2 py-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
                effort === opt.value
                  ? "bg-foreground text-background"
                  : "border-foreground/15 text-foreground/55 hover:text-foreground border",
              )}
            >
              {isChinese ? opt.labelZh : opt.label}
            </button>
          ))}
        </div>
        <p className="text-foreground/55 text-[11px]">
          {isChinese
            ? EFFORT_OPTIONS.find((o) => o.value === effort)?.hintZh
            : EFFORT_OPTIONS.find((o) => o.value === effort)?.hint}
        </p>
      </div>

      <p className="text-foreground/45 text-[10px] leading-relaxed">
        {isChinese
          ? "这些设置仅对当前聊天会话生效。部分模型不支持某些控制项，调整后可能没有变化。"
          : "Settings persist for the current chat session. Some controls are no-ops on models that don't support them."}
      </p>
    </div>
  );
}
