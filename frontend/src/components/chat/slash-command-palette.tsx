"use client";

import { useEffect, useRef } from "react";
import { useLocale } from "next-intl";

import { cn } from "@/lib/utils";
import type { SlashCommand } from "./slash-commands";

interface SlashCommandPaletteProps {
  commands: SlashCommand[];
  selectedIndex: number;
  onSelectIndex: (i: number) => void;
  onPick: (cmd: SlashCommand) => void;
}

/** Floating palette rendered above the chat input when the user types `/`. */
export function SlashCommandPalette({
  commands,
  selectedIndex,
  onSelectIndex,
  onPick,
}: SlashCommandPaletteProps) {
  const isChinese = useLocale() === "zh";
  const listRef = useRef<HTMLUListElement>(null);

  // Keep the highlighted row in view as the user arrow-keys through the list.
  useEffect(() => {
    const el = listRef.current?.children[selectedIndex] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [selectedIndex]);

  if (commands.length === 0) {
    return (
      <div className="border-foreground/10 bg-popover absolute bottom-full left-0 mb-2 w-full max-w-sm rounded-xl border p-3 shadow-lg">
        <p className="text-foreground/55 text-xs">
          {isChinese ? "没有匹配的命令。按 " : "No matching commands. Press "}
          <kbd className="font-mono">Esc</kbd>
          {isChinese ? " 关闭。" : " to dismiss."}
        </p>
      </div>
    );
  }

  return (
    <div className="border-foreground/10 bg-popover absolute bottom-full left-0 mb-2 w-full max-w-md overflow-hidden rounded-xl border shadow-lg">
      <div className="border-foreground/8 text-foreground/55 flex items-center justify-between border-b px-3 py-1.5 font-mono text-[10px] tracking-wider uppercase">
        <span>{isChinese ? "命令" : "Commands"}</span>
        <span className="hidden sm:inline">
          {isChinese ? "↑↓ 选择 · ↵ 执行 · Esc 关闭" : "↑↓ to navigate · ↵ to run · esc to dismiss"}
        </span>
      </div>
      <ul ref={listRef} className="max-h-64 overflow-y-auto py-1">
        {commands.map((cmd, i) => (
          <li
            key={cmd.name}
            onMouseEnter={() => onSelectIndex(i)}
            onMouseDown={(e) => {
              e.preventDefault(); // keep textarea focus
              onPick(cmd);
            }}
            className={cn(
              "flex cursor-pointer items-center justify-between gap-3 px-3 py-1.5",
              selectedIndex === i ? "bg-foreground/[0.06]" : "hover:bg-foreground/[0.03]",
            )}
          >
            <div className="min-w-0 flex-1">
              <p className="text-foreground font-mono text-xs">/{cmd.name}</p>
              <p className="text-foreground/55 truncate text-xs">
                {isChinese
                  ? ({
                      clear: "清空当前聊天，但不会删除对话记录。",
                      regen: "重新生成上一条助手回复。",
                      settings: "打开模型、温度和思考强度设置。",
                      summarize: "让 Agent 总结当前对话。",
                      explain: "让 Agent 用更简单的方式解释上一条回复。",
                    }[cmd.name] ?? cmd.description)
                  : cmd.description}
              </p>
            </div>
            {cmd.aliases && cmd.aliases.length > 0 && (
              <span className="text-foreground/40 hidden font-mono text-[10px] sm:inline">
                /{cmd.aliases[0]}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
