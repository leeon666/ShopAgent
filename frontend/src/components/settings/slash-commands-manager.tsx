"use client";

import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useLocale } from "next-intl";
import { toast } from "sonner";

import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Switch,
  Textarea,
} from "@/components/ui";
import { EmptyState } from "@/components/states";
import { ApiError } from "@/lib/api-client";
import { BUILTIN_COMMAND_LIST, isBuiltinEnabled, useSlashCommands } from "@/hooks";
import type { UserSlashCommandRecord } from "@/lib/slash-commands-api";

const NAME_PATTERN = /^[a-z0-9][a-z0-9-]{0,31}$/;
const BUILTIN_DESCRIPTIONS_ZH: Record<string, string> = {
  clear: "清空当前聊天，但不会删除对话记录。",
  regen: "重新生成上一条助手回复。",
  settings: "打开聊天设置（模型、温度、思考强度）。",
  summarize: "让 Agent 总结当前对话。",
  explain: "让 Agent 用更简单的方式解释上一条回复。",
};

export function SlashCommandsManager() {
  const isChinese = useLocale() === "zh";
  const {
    records,
    isLoading,
    error,
    refresh,
    createCustom,
    updateCustom,
    setBuiltinEnabled,
    remove,
  } = useSlashCommands();

  const customs = records.filter((r) => r.prompt !== null);

  const [editingId, setEditingId] = useState<string | "new" | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftPrompt, setDraftPrompt] = useState("");
  const [draftEnabled, setDraftEnabled] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const openCreate = () => {
    setEditingId("new");
    setDraftName("");
    setDraftPrompt("");
    setDraftEnabled(true);
  };

  const openEdit = (record: UserSlashCommandRecord) => {
    setEditingId(record.id);
    setDraftName(record.name);
    setDraftPrompt(record.prompt ?? "");
    setDraftEnabled(record.is_enabled);
  };

  const closeDialog = () => {
    if (submitting) return;
    setEditingId(null);
  };

  const handleSubmit = async () => {
    const name = draftName.trim().toLowerCase();
    const prompt = draftPrompt.trim();
    if (!NAME_PATTERN.test(name)) {
      toast.error(
        isChinese
          ? "名称只能包含小写字母、数字和连字符，最多 32 个字符。"
          : "Name must be lowercase letters, digits, and hyphens (max 32 chars).",
      );
      return;
    }
    if (!prompt) {
      toast.error(isChinese ? "提示词不能为空。" : "Prompt cannot be empty.");
      return;
    }
    setSubmitting(true);
    try {
      if (editingId === "new") {
        await createCustom({ name, prompt });
        toast.success(isChinese ? `/${name} 已创建。` : `/${name} created.`);
      } else if (editingId) {
        await updateCustom(editingId, { name, prompt, is_enabled: draftEnabled });
        toast.success(isChinese ? `/${name} 已更新。` : `/${name} updated.`);
      }
      setEditingId(null);
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : isChinese
              ? "保存快捷命令失败"
              : "Failed to save command";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleCustom = async (record: UserSlashCommandRecord, next: boolean) => {
    try {
      await updateCustom(record.id, { is_enabled: next });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : isChinese ? "切换失败" : "Failed to toggle");
    }
  };

  const handleToggleBuiltin = async (name: string, next: boolean) => {
    try {
      await setBuiltinEnabled(name, next);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : isChinese ? "切换失败" : "Failed to toggle");
    }
  };

  const handleDelete = async (record: UserSlashCommandRecord) => {
    if (!confirm(isChinese ? `要删除 /${record.name} 吗？` : `Delete /${record.name}?`)) return;
    try {
      await remove(record.id);
      toast.success(isChinese ? `/${record.name} 已删除。` : `/${record.name} deleted.`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : isChinese ? "删除失败" : "Failed to delete");
    }
  };

  return (
    <div className="space-y-8">
      {error && (
        <div className="border-destructive/30 bg-destructive/5 text-destructive flex items-center justify-between rounded-xl border px-4 py-3 text-sm">
          <span>{error}</span>
          <Button size="sm" variant="ghost" onClick={() => refresh()}>
            {isChinese ? "重试" : "Retry"}
          </Button>
        </div>
      )}

      <section className="space-y-3">
        <div className="flex items-baseline justify-between gap-3">
          <div>
            <h3 className="text-foreground text-sm font-semibold">
              {isChinese ? "内置命令" : "Built-in commands"}
            </h3>
            <p className="text-foreground/55 mt-0.5 text-xs">
              {isChinese
                ? "可以关闭不想在命令面板中显示的命令。"
                : "Disable any you don’t want to see in the palette."}
            </p>
          </div>
        </div>
        <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-xl border">
          {BUILTIN_COMMAND_LIST.map((cmd) => {
            const enabled = isBuiltinEnabled(cmd.name, records);
            return (
              <li key={cmd.name} className="flex items-center gap-4 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <code className="text-foreground bg-foreground/8 rounded px-1.5 py-0.5 font-mono text-xs">
                      /{cmd.name}
                    </code>
                    {cmd.action.kind === "client" && (
                      <span className="text-foreground/45 font-mono text-[10px] tracking-wider uppercase">
                        {isChinese ? "本地" : "local"}
                      </span>
                    )}
                  </div>
                  <p className="text-foreground/65 mt-1 text-xs">
                    {isChinese
                      ? (BUILTIN_DESCRIPTIONS_ZH[cmd.name] ?? cmd.description)
                      : cmd.description}
                  </p>
                </div>
                <Switch
                  checked={enabled}
                  onCheckedChange={(v) => handleToggleBuiltin(cmd.name, v)}
                  disabled={isLoading}
                  aria-label={isChinese ? `切换 /${cmd.name}` : `Toggle /${cmd.name}`}
                />
              </li>
            );
          })}
        </ul>
      </section>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between gap-3">
          <div>
            <h3 className="text-foreground text-sm font-semibold">
              {isChinese ? "我的自定义命令" : "Your custom commands"}
            </h3>
            <p className="text-foreground/55 mt-0.5 text-xs">
              {isChinese
                ? "为常用提示词创建快捷入口。在聊天中输入 "
                : "Slash shortcuts for prompts you type often. Typing "}
              <code>/name</code>
              {isChinese ? " 即可发送保存的提示词。" : " in chat sends the stored prompt."}
            </p>
          </div>
          <Button size="sm" onClick={openCreate}>
            <Plus className="mr-1 h-3.5 w-3.5" />
            {isChinese ? "新建命令" : "New command"}
          </Button>
        </div>

        {customs.length === 0 ? (
          <EmptyState
            title={isChinese ? "暂无自定义命令" : "No custom commands yet"}
            description={
              isChinese
                ? "创建一个命令，即可用几个按键发送长提示词。"
                : "Create one to send a long prompt with a few keystrokes."
            }
          />
        ) : (
          <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-xl border">
            {customs.map((record) => (
              <li key={record.id} className="flex items-start gap-4 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <code className="text-foreground bg-foreground/8 rounded px-1.5 py-0.5 font-mono text-xs">
                      /{record.name}
                    </code>
                  </div>
                  <p className="text-foreground/65 mt-1 line-clamp-2 text-xs">{record.prompt}</p>
                </div>
                <Switch
                  checked={record.is_enabled}
                  onCheckedChange={(v) => handleToggleCustom(record, v)}
                  aria-label={isChinese ? `切换 /${record.name}` : `Toggle /${record.name}`}
                />
                <button
                  type="button"
                  onClick={() => openEdit(record)}
                  className="text-foreground/55 hover:bg-foreground/5 hover:text-foreground inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                  title={isChinese ? "编辑" : "Edit"}
                  aria-label={isChinese ? "编辑" : "Edit"}
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(record)}
                  className="text-foreground/55 hover:bg-destructive/10 hover:text-destructive inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                  title={isChinese ? "删除" : "Delete"}
                  aria-label={isChinese ? "删除" : "Delete"}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Dialog open={editingId !== null} onOpenChange={(o) => !o && closeDialog()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingId === "new"
                ? isChinese
                  ? "新建自定义命令"
                  : "New custom command"
                : isChinese
                  ? `编辑 /${draftName}`
                  : `Edit /${draftName}`}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="cmd-name">{isChinese ? "名称" : "Name"}</Label>
              <div className="mt-1.5 flex items-center gap-2">
                <span className="text-foreground/45 font-mono text-sm">/</span>
                <Input
                  id="cmd-name"
                  value={draftName}
                  onChange={(e) => setDraftName(e.target.value.toLowerCase())}
                  placeholder="todo"
                  maxLength={32}
                  autoFocus
                />
              </div>
              <p className="text-foreground/45 mt-1 text-[11px]">
                {isChinese
                  ? "仅支持小写字母、数字和连字符，最多 32 个字符。"
                  : "Lowercase letters, digits, hyphens. Max 32 chars."}
              </p>
            </div>
            <div>
              <Label htmlFor="cmd-prompt">{isChinese ? "提示词" : "Prompt"}</Label>
              <Textarea
                id="cmd-prompt"
                value={draftPrompt}
                onChange={(e) => setDraftPrompt(e.target.value)}
                placeholder={
                  isChinese
                    ? "把当前对话总结成一份可执行的事项清单。"
                    : "Summarize the conversation as a checklist of action items."
                }
                rows={6}
                maxLength={10_000}
                className="mt-1.5 font-mono text-sm"
              />
              <p className="text-foreground/45 mt-1 text-[11px]">
                {isChinese ? "输入 " : "Sent as a regular user message when you type "}
                <code>/{draftName || (isChinese ? "名称" : "name")}</code>
                {isChinese ? " 后会作为普通用户消息发送。" : "."}
              </p>
            </div>
            {editingId !== "new" && (
              <div className="flex items-center gap-3">
                <Switch id="cmd-enabled" checked={draftEnabled} onCheckedChange={setDraftEnabled} />
                <Label htmlFor="cmd-enabled" className="text-sm font-normal">
                  {isChinese ? "启用" : "Enabled"}
                </Label>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={closeDialog} disabled={submitting}>
              {isChinese ? "取消" : "Cancel"}
            </Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting
                ? isChinese
                  ? "保存中…"
                  : "Saving…"
                : editingId === "new"
                  ? isChinese
                    ? "创建"
                    : "Create"
                  : isChinese
                    ? "保存"
                    : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
