"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Check } from "lucide-react";
import { useLocale } from "next-intl";

import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";

import { OnboardingShell } from "./onboarding-shell";

interface AgentOption {
  id: string;
  name: string;
  tagline: string;
  description: string;
  recommended?: boolean;
}

const AGENTS: AgentOption[] = [
  {
    id: "pydantic_ai",
    name: "PydanticAI",
    tagline: "Type-safe, fast, opinionated",
    description: "Best default — typed tools, structured outputs, Logfire telemetry.",
    recommended: true,
  },
  {
    id: "langgraph",
    name: "LangGraph",
    tagline: "Stateful graphs, complex flows",
    description: "Multi-step agents with branching logic and persistent state.",
  },
  {
    id: "deepagents",
    name: "DeepAgents",
    tagline: "Long-horizon planning",
    description: "Built for autonomous tasks that span many tool calls.",
  },
];

export function StepAgent() {
  const router = useRouter();
  const isChinese = useLocale() === "zh";
  const agents = AGENTS.map((agent) => ({
    ...agent,
    tagline: isChinese
      ? ({
          pydantic_ai: "类型安全、快速、工程化",
          langgraph: "有状态图与复杂工作流",
          deepagents: "长周期自主任务规划",
        }[agent.id] ?? agent.tagline)
      : agent.tagline,
    description: isChinese
      ? ({
          pydantic_ai: "推荐的默认方案：类型安全工具、结构化输出与完整遥测。",
          langgraph: "适合带分支逻辑和持久状态的多步骤 Agent。",
          deepagents: "适合需要连续调用大量工具的自主任务。",
        }[agent.id] ?? agent.description)
      : agent.description,
  }));
  const [selected, setSelected] = useState<string>(
    () => AGENTS.find((a) => a.recommended)?.id ?? AGENTS[0]!.id,
  );

  const handleNext = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("onboarding.agent", selected);
    }
    router.push("/onboarding/data");
  };

  return (
    <OnboardingShell
      step="agent"
      title={isChinese ? "选择 Agent 框架" : "Pick your agent framework"}
      description={
        isChinese
          ? "每个框架都支持流式输出、工具调用和可观测性，之后也可以切换。"
          : "Each comes wired with streaming, tool calls, and observability. You can switch later."
      }
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {agents.map((agent) => {
          const isSelected = selected === agent.id;
          return (
            <button
              key={agent.id}
              type="button"
              onClick={() => setSelected(agent.id)}
              className={cn(
                "bg-card relative flex flex-col gap-2 rounded-xl border p-5 text-left transition-colors",
                isSelected ? "border-foreground" : "border-border hover:border-foreground/30",
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-foreground text-base font-semibold">{agent.name}</p>
                  <p className="text-muted-foreground text-xs">{agent.tagline}</p>
                </div>
                <span
                  className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors",
                    isSelected
                      ? "border-foreground bg-foreground text-background"
                      : "border-border",
                  )}
                >
                  {isSelected && <Check className="h-3 w-3" />}
                </span>
              </div>
              <p className="text-muted-foreground mt-1 text-sm leading-relaxed">
                {agent.description}
              </p>
              {agent.recommended && (
                <span className="bg-muted text-foreground border-border absolute -top-2 right-4 rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase">
                  {isChinese ? "推荐" : "Recommended"}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <Button size="lg" className="mt-8" onClick={handleNext}>
        {isChinese ? "继续" : "Continue"}
        <ArrowRight className="h-4 w-4" />
      </Button>
    </OnboardingShell>
  );
}
