import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, Mail } from "lucide-react";
import { getLocale } from "next-intl/server";

import type { Locale } from "@/i18n";
import { ROUTES } from "@/lib/constants";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const isChinese = locale === "zh";
  return pageMetadata({
    title: isChinese ? "请查看邮箱" : "Check your email",
    description: isChinese ? "登录链接已发送。" : "We sent you a sign-in link.",
    path: "/magic-link-sent",
    locale,
    noindex: true,
  });
}

interface PageProps {
  searchParams: Promise<{ email?: string }>;
}

export default async function MagicLinkSentPage({ searchParams }: PageProps) {
  const { email } = await searchParams;
  const locale = await getLocale();
  const isChinese = locale === "zh";

  return (
    <div className="space-y-8 text-center">
      <div
        className="bg-brand/15 mx-auto flex h-16 w-16 items-center justify-center rounded-full"
        style={{ boxShadow: "0 0 40px oklch(from var(--color-brand) l c h / 0.4)" }}
      >
        <Mail className="text-foreground h-7 w-7" />
      </div>

      <div className="space-y-2">
        <span className="eyebrow text-foreground/55">
          {isChinese ? "免密登录链接" : "Magic link"}
        </span>
        <h1 className="text-display-md text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
          {isChinese ? (
            <>
              邮件<em>已送达。</em>
            </>
          ) : (
            <>
              Inbox, <em>incoming.</em>
            </>
          )}
        </h1>
        <p className="text-foreground/70 text-sm">
          {isChinese ? "我们已发送登录链接" : "We sent a sign-in link"}
          {email ? (
            <>
              {" "}
              {isChinese ? "至" : "to"} <span className="text-foreground font-medium">{email}</span>
            </>
          ) : null}
          {isChinese
            ? "。点击链接即可继续，链接 15 分钟后失效。"
            : ". Click it to continue — expires in 15 minutes."}
        </p>
      </div>

      <div className="border-foreground/10 bg-foreground/[0.03] rounded-2xl border px-5 py-4 text-left">
        <p className="text-foreground/70 text-xs leading-relaxed">
          {isChinese
            ? "没有收到？请检查垃圾邮件，或者"
            : "Don't see it? Check your spam folder, or"}{" "}
          <Link
            href={ROUTES.LOGIN}
            className="text-foreground hover:text-foreground/80 font-medium underline-offset-4 hover:underline"
          >
            {isChinese ? "重新尝试" : "try again"}
          </Link>
          {isChinese ? "。" : "."}
        </p>
      </div>

      <Link
        href={ROUTES.LOGIN}
        className="text-foreground/55 hover:text-foreground inline-flex items-center gap-2 text-sm font-medium"
      >
        <ArrowLeft className="h-4 w-4" />
        {isChinese ? "返回登录" : "Back to sign in"}
      </Link>
    </div>
  );
}
