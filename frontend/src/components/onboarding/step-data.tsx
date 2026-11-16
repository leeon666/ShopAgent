"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, FileText, FolderOpen, HardDrive, Upload } from "lucide-react";
import { useLocale } from "next-intl";
import { toast } from "sonner";

import { BrandIcon } from "@/components/marketing/brand-icon";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";

import { OnboardingShell } from "./onboarding-shell";

type Choice = "upload" | "gdrive" | "skip" | null;

export function StepData() {
  const router = useRouter();
  const isChinese = useLocale() === "zh";
  const [choice, setChoice] = useState<Choice>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File | null) => {
    if (!file) return;
    setUploading(true);
    setFilename(file.name);
    // We don't actually upload here — onboarding is a UX preview.
    // The real upload UI lives in /rag. Surface a toast and continue.
    setTimeout(() => {
      setUploading(false);
      toast.success(isChinese ? `${file.name} 已加入索引队列` : `Queued ${file.name} for indexing`);
    }, 600);
  };

  const handleNext = () => {
    router.push("/onboarding/team");
  };

  return (
    <OnboardingShell
      step="data"
      title={isChinese ? "连接数据" : "Connect your data"}
      description={
        isChinese
          ? "上传文档，让回答基于团队知识；也可以先跳过，稍后再添加。"
          : "Drop a doc to ground answers in your team's knowledge — or skip and add data later."
      }
    >
      <div className="grid gap-3">
        <ChoiceCard
          icon={Upload}
          title={isChinese ? "上传文件" : "Upload a file"}
          description={
            isChinese
              ? "支持 PDF、DOCX、MD 或 TXT，最大 50 MB"
              : "PDF, DOCX, MD, or TXT up to 50 MB"
          }
          selected={choice === "upload"}
          onClick={() => {
            setChoice("upload");
            fileInputRef.current?.click();
          }}
          accent
        />
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,.md,.txt"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
        <ChoiceCard
          brandIcon="gdrive"
          title={isChinese ? "从 Google Drive 同步" : "Sync from Google Drive"}
          description={
            isChinese
              ? "连接文件夹，内容变化后自动重新索引"
              : "Connect a folder — auto-reindex on changes"
          }
          selected={choice === "gdrive"}
          onClick={() => {
            setChoice("gdrive");
            toast.info(
              isChinese
                ? "请在“知识库 → 数据源”中配置云盘同步。"
                : "Drive sync configured in /rag → Sources",
            );
          }}
        />
        <ChoiceCard
          icon={HardDrive}
          title={isChinese ? "暂时跳过" : "Skip for now"}
          description={
            isChinese
              ? "之后可以随时在知识库中添加数据源。"
              : "You can add data sources from the Knowledge Base any time"
          }
          selected={choice === "skip"}
          onClick={() => setChoice("skip")}
        />
      </div>

      {filename && (
        <div className="border-border bg-muted mt-4 flex items-center gap-3 rounded-xl border px-4 py-3 text-sm">
          <FileText className="text-muted-foreground h-4 w-4" />
          <span className="text-foreground flex-1 truncate font-mono text-xs">{filename}</span>
          <span className="text-muted-foreground text-[11px] font-medium tracking-wide uppercase">
            {uploading ? (isChinese ? "加入队列中…" : "Queueing…") : isChinese ? "已就绪" : "Ready"}
          </span>
        </div>
      )}

      <Button size="lg" className="mt-8" onClick={handleNext}>
        {isChinese ? "继续" : "Continue"}
        <ArrowRight className="h-4 w-4" />
      </Button>
    </OnboardingShell>
  );
}

function ChoiceCard({
  icon: Icon,
  brandIcon,
  title,
  description,
  selected,
  onClick,
  accent,
}: {
  icon?: typeof FolderOpen;
  brandIcon?: "gdrive";
  title: string;
  description: string;
  selected?: boolean;
  onClick: () => void;
  accent?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "bg-card flex w-full items-center gap-4 rounded-xl border p-5 text-left transition-colors",
        selected ? "border-foreground" : "border-border hover:border-foreground/30",
      )}
    >
      <div
        className={cn(
          "flex h-11 w-11 shrink-0 items-center justify-center rounded-lg",
          accent || selected ? "bg-foreground text-background" : "bg-muted text-foreground",
        )}
      >
        {Icon && <Icon className="h-5 w-5" />}
        {brandIcon && <BrandIcon name={brandIcon} className="h-5 w-5" aria-hidden />}
      </div>
      <div className="flex-1">
        <p className="text-foreground text-base font-semibold">{title}</p>
        <p className="text-muted-foreground mt-0.5 text-sm">{description}</p>
      </div>
    </button>
  );
}
