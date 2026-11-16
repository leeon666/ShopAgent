import type { Metadata } from "next";

import { ForgotPasswordForm } from "@/components/auth";
import type { Locale } from "@/i18n";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const isChinese = locale === "zh";
  return pageMetadata({
    title: isChinese ? "重置密码" : "Reset password",
    description: isChinese ? "重置账户密码。" : "Reset your account password.",
    path: "/forgot-password",
    locale,
    noindex: true,
  });
}

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
