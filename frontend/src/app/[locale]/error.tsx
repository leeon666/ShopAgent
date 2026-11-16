"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";

import { Button } from "@/components/ui/button";
import { ROUTES } from "@/lib/constants";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();
  const isChinese = useLocale() === "zh";

  useEffect(() => {
    console.error("Page error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <p className="text-destructive text-sm font-semibold tracking-wider uppercase">
        {isChinese ? "错误" : "Error"}
      </p>
      <h1 className="text-foreground mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
        {isChinese ? "发生错误" : "Something went wrong"}
      </h1>
      <p className="text-muted-foreground mt-3 max-w-md">
        {isChinese
          ? "加载页面时发生错误，请重试。"
          : "An error occurred while loading this page. Please try again."}
      </p>
      {error.digest && (
        <p className="text-muted-foreground/60 mt-1 text-xs">
          {isChinese ? "错误编号：" : "Error ID: "}
          {error.digest}
        </p>
      )}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Button onClick={reset}>{isChinese ? "重试" : "Try again"}</Button>
        <Button variant="secondary" onClick={() => router.back()}>
          {isChinese ? "返回上一页" : "Go back"}
        </Button>
        <Button variant="outline" asChild>
          <Link href={ROUTES.HOME}>{isChinese ? "返回首页" : "Go home"}</Link>
        </Button>
      </div>
    </div>
  );
}
