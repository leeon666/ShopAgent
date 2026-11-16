import type { Metadata } from "next";
import Link from "next/link";
import { getLocale } from "next-intl/server";

import { ResetPasswordForm } from "@/components/auth/reset-password-form";
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
    title: isChinese ? "设置新密码" : "Set a new password",
    description: isChinese ? "重置账户密码。" : "Reset your account password.",
    path: "/reset-password",
    locale,
    noindex: true,
  });
}

interface PageProps {
  searchParams: Promise<{ token?: string }>;
}

export default async function ResetPasswordPage({ searchParams }: PageProps) {
  const { token } = await searchParams;
  const locale = await getLocale();
  const isChinese = locale === "zh";

  if (!token) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <span className="eyebrow text-foreground/55">
            {isChinese ? "重置密码" : "Reset password"}
          </span>
          <h1 className="text-display-md text-foreground">
            {isChinese ? "链接缺失或已失效" : "Missing or expired link"}
          </h1>
          <p className="text-foreground/70 text-sm">
            {isChinese
              ? "此页面需要使用重置邮件中的令牌。请重新申请一个链接。"
              : "This page expects a token from your reset email. Request a new link to continue."}
          </p>
        </div>
        <Link
          href={ROUTES.FORGOT_PASSWORD}
          className="bg-foreground text-background hover:bg-foreground/90 inline-flex h-11 items-center justify-center gap-2 rounded-full px-5 text-sm font-medium transition-colors"
        >
          {isChinese ? "重新申请链接" : "Request a new link"}
        </Link>
        <p className="text-foreground/55 text-xs">
          {isChinese ? "或者" : "Or"}{" "}
          <Link
            href={ROUTES.LOGIN}
            className="text-foreground hover:text-foreground/80 underline-offset-4 hover:underline"
          >
            {isChinese ? "返回登录" : "return to sign in"}
          </Link>
          {isChinese ? "。" : "."}
        </p>
      </div>
    );
  }

  return <ResetPasswordForm token={token} />;
}
