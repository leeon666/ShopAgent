"use client";

import { useEffect } from "react";
import { useLocale } from "next-intl";

import { ErrorState } from "@/components/states";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const isChinese = useLocale() === "zh";
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex min-h-0 flex-1 items-center justify-center py-10">
      <ErrorState
        className="w-full max-w-md"
        title={isChinese ? "当前页面加载失败" : "This section failed to load"}
        description={
          error.digest
            ? isChinese
              ? `发生了意外错误。错误编号：${error.digest}`
              : `An unexpected error occurred. Error ID: ${error.digest}`
            : isChinese
              ? "加载此页面时发生意外错误，请重试。"
              : "An unexpected error occurred while loading this view. Please try again."
        }
        cta={{ label: isChinese ? "重试" : "Try again", onClick: () => reset() }}
      />
    </div>
  );
}
