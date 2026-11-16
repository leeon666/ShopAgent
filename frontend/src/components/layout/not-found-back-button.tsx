"use client";

import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";

import { Button } from "@/components/ui/button";

export function NotFoundBackButton() {
  const router = useRouter();
  const isChinese = useLocale() === "zh";
  return (
    <Button variant="outline" onClick={() => router.back()}>
      {isChinese ? "返回上一页" : "Go back"}
    </Button>
  );
}
