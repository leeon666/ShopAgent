"use client";

import {
  ArrowUpRight,
  BookOpen,
  Code2,
  FileSearch,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import { useLocale } from "next-intl";

import { useAuth } from "@/hooks";

const DEFAULT_PROMPTS = [
  {
    icon: FileSearch,
    title: "Summarize my docs",
    prompt: "Summarize the key points from my latest indexed documents.",
  },
  {
    icon: BookOpen,
    title: "Explain a concept",
    prompt: "Explain how vector search and RAG work together — keep it under 200 words.",
  },
  {
    icon: Code2,
    title: "Write some code",
    prompt: "Write a Python function that hashes a password with bcrypt and verifies it.",
  },
  {
    icon: Sparkles,
    title: "Brainstorm",
    prompt: "Give me 5 ideas for an onboarding email sequence for a developer tool.",
  },
];

const CHINESE_PROMPTS = [
  {
    icon: FileSearch,
    title: "总结知识库",
    prompt: "请总结知识库中最新导入文档的核心内容。",
  },
  {
    icon: BookOpen,
    title: "解释 RAG",
    prompt: "请用 200 字以内解释向量检索和 RAG 如何配合工作。",
  },
  {
    icon: Code2,
    title: "编写代码",
    prompt: "请写一个使用 bcrypt 哈希密码并校验密码的 Python 函数。",
  },
  {
    icon: Sparkles,
    title: "整理思路",
    prompt: "请给我 5 个面向开发工具的新用户引导邮件创意。",
  },
];

export interface ChatEmptyPrompt {
  icon: LucideIcon;
  title: string;
  prompt: string;
}

interface ChatEmptyStateProps {
  onPick: (prompt: string) => void;
  agentLabel?: string;
  prompts?: ChatEmptyPrompt[];
}

export function ChatEmptyState({
  onPick,
  agentLabel = "pydantic_ai",
  prompts,
}: ChatEmptyStateProps) {
  const locale = useLocale();
  const isChinese = locale === "zh";
  const { user } = useAuth();
  const firstName = user?.full_name?.split(" ")[0] || user?.email?.split("@")[0];
  const activePrompts = prompts ?? (isChinese ? CHINESE_PROMPTS : DEFAULT_PROMPTS);

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-12 md:py-16">
      <div className="text-center">
        <div className="bg-muted text-foreground mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl">
          <Sparkles className="h-5 w-5" />
        </div>
        <h2 className="text-foreground font-display text-2xl font-semibold tracking-tight md:text-3xl">
          {isChinese
            ? firstName
              ? `需要我做什么，${firstName}？`
              : "今天需要我做什么？"
            : firstName
              ? `How can I help, ${firstName}?`
              : "How can I help today?"}
        </h2>
        <p className="text-muted-foreground mx-auto mt-2 max-w-md text-sm leading-relaxed">
          {isChinese
            ? "直接描述你的问题，Agent 会调用工具、检索证据并给出来源。"
            : "Ask anything — get streaming answers with tool calls and citations from your knowledge."}
        </p>
      </div>

      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        {activePrompts.map((p) => (
          <button
            key={p.title}
            type="button"
            onClick={() => onPick(p.prompt)}
            className="group border-border bg-card hover:border-foreground/30 hover:bg-accent flex items-start gap-3 rounded-xl border p-4 text-left transition-colors"
          >
            <span className="bg-muted text-muted-foreground group-hover:text-foreground flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors">
              <p.icon className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-foreground text-sm font-medium">{p.title}</p>
              <p className="text-muted-foreground mt-0.5 line-clamp-2 text-xs leading-relaxed">
                {p.prompt}
              </p>
            </div>
            <ArrowUpRight className="text-muted-foreground/50 group-hover:text-foreground mt-0.5 h-4 w-4 shrink-0 transition-colors" />
          </button>
        ))}
      </div>

      <div className="text-muted-foreground mt-8 flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-xs">
        <kbd className="border-border bg-card rounded px-1.5 py-0.5 font-mono text-[10px]">⌘K</kbd>
        <span>{isChinese ? "命令面板" : "command palette"}</span>
        <span className="text-border">·</span>
        <kbd className="border-border bg-card rounded px-1.5 py-0.5 font-mono text-[10px]">/</kbd>
        <span>{isChinese ? "斜杠命令" : "slash commands"}</span>
        <span className="text-border">·</span>
        <span className="text-muted-foreground/70">
          {isChinese ? "由" : "Powered by"} {agentLabel} {isChinese ? "驱动" : ""}
        </span>
      </div>
    </div>
  );
}

