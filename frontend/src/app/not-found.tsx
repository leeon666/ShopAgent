import Link from "next/link";
import { getLocale } from "next-intl/server";

import { Button } from "@/components/ui/button";
import { NotFoundBackButton } from "@/components/layout/not-found-back-button";
import { ROUTES } from "@/lib/constants";

export default async function NotFound() {
  const locale = await getLocale();
  const isChinese = locale === "zh";
  return (
    <div className="bg-background flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <p className="text-brand text-sm font-semibold tracking-wider uppercase">404</p>
      <h1 className="text-foreground mt-2 text-4xl font-bold tracking-tight sm:text-5xl">
        {isChinese ? "页面不存在" : "Page not found"}
      </h1>
      <p className="text-muted-foreground mt-4">
        {isChinese
          ? "你访问的页面不存在，或已经被移动。"
          : "The page you're looking for doesn't exist or has been moved."}
      </p>
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Button asChild>
          <Link href={ROUTES.HOME}>{isChinese ? "返回首页" : "Go home"}</Link>
        </Button>
        <NotFoundBackButton />
        <Button variant="secondary" asChild>
          <Link href={ROUTES.DASHBOARD}>{isChinese ? "进入仪表盘" : "Dashboard"}</Link>
        </Button>
      </div>
    </div>
  );
}
