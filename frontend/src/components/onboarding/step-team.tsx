"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Plus, X } from "lucide-react";
import { useLocale } from "next-intl";
import { toast } from "sonner";

import { Button, Input } from "@/components/ui";

import { OnboardingShell } from "./onboarding-shell";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function StepTeam() {
  const router = useRouter();
  const isChinese = useLocale() === "zh";
  const [emails, setEmails] = useState<string[]>(["", "", ""]);

  const updateEmail = (i: number, value: string) =>
    setEmails((prev) => prev.map((e, idx) => (idx === i ? value : e)));

  const addRow = () => setEmails((prev) => [...prev, ""]);
  const removeRow = (i: number) => setEmails((prev) => prev.filter((_, idx) => idx !== i));

  const validInvites = emails.filter((e) => e && EMAIL_RE.test(e));
  const invalid = emails.some((e) => e && !EMAIL_RE.test(e));

  const handleContinue = () => {
    if (invalid) {
      toast.error(isChinese ? "有一个邮箱地址格式不正确。" : "One of the emails looks invalid");
      return;
    }
    if (validInvites.length > 0) {
      toast.success(
        isChinese
          ? `已为 ${validInvites.length} 位成员加入邀请队列`
          : `Invites queued for ${validInvites.length} ${validInvites.length === 1 ? "person" : "people"}`,
      );
    }
    router.push("/onboarding/done");
  };

  return (
    <OnboardingShell
      step="team"
      title={isChinese ? "邀请团队成员" : "Bring your team along"}
      description={
        isChinese
          ? "现在最多可邀请 5 位成员，他们会收到一封包含免密登录链接的邮件。"
          : "Invite up to 5 teammates now — they'll get an email with a magic-link to join."
      }
    >
      <div className="space-y-2">
        {emails.map((email, i) => (
          <div key={i} className="flex items-center gap-2">
            <Input
              type="email"
              placeholder="teammate@company.com"
              value={email}
              onChange={(e) => updateEmail(i, e.target.value)}
              autoComplete="email"
              className="h-11 flex-1 rounded-xl"
            />
            {emails.length > 1 && (
              <button
                type="button"
                onClick={() => removeRow(i)}
                className="text-muted-foreground hover:text-foreground hover:bg-muted h-9 w-9 shrink-0 rounded-md transition-colors"
                aria-label={isChinese ? "移除邀请" : "Remove invite"}
              >
                <X className="mx-auto h-4 w-4" />
              </button>
            )}
          </div>
        ))}
      </div>

      {emails.length < 5 && (
        <button
          type="button"
          onClick={addRow}
          className="text-muted-foreground hover:text-foreground mt-3 inline-flex items-center gap-1.5 text-xs font-medium tracking-wide uppercase"
        >
          <Plus className="h-3.5 w-3.5" />
          {isChinese ? "再添加一位" : "Add another"}
        </button>
      )}

      <div className="mt-8 flex items-center gap-3">
        <Button size="lg" onClick={handleContinue}>
          {validInvites.length > 0
            ? isChinese
              ? `发送 ${validInvites.length} 份邀请`
              : `Send ${validInvites.length} invite${validInvites.length === 1 ? "" : "s"}`
            : isChinese
              ? "继续"
              : "Continue"}
          <ArrowRight className="h-4 w-4" />
        </Button>
        <Button size="lg" variant="ghost" onClick={() => router.push("/onboarding/done")}>
          {isChinese ? "跳过" : "Skip"}
        </Button>
      </div>
    </OnboardingShell>
  );
}
