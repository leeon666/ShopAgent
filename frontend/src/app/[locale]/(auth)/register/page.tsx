import type { Metadata } from "next";

import { RegisterForm } from "@/components/auth";
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
    title: isChinese ? "创建账户" : "Create your account",
    description: isChinese
      ? "开始免费试用，无需信用卡。"
      : "Start your free trial — no credit card required.",
    path: "/register",
    locale,
  });
}

export default function RegisterPage() {
  return <RegisterForm />;
}
