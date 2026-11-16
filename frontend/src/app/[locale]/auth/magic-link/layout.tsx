import type { Metadata, Viewport } from "next";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    title: locale === "zh" ? "登录" : "Sign in",
    robots: { index: false, follow: false },
  };
}

export const viewport: Viewport = {
  themeColor: "#0E0E0C",
};

export default function MagicLinkVerifyLayout({ children }: { children: React.ReactNode }) {
  return children;
}
