import Link from "next/link";
import {
  ArrowUpRight,
  Fingerprint,
  KeyRound,
  Lock,
  ScrollText,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

import { cn, uiText } from "@/lib/utils";

interface EnterpriseSecurityProps {
  cta?: { label: string; href: string };
}

const CARD =
  "group border-foreground/12 bg-card lift hover:border-foreground/25 relative overflow-hidden rounded-2xl border transition-colors";

const FEATURES: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: KeyRound,
    title: "SSO & SAML",
    body: "One-click sign-in with Okta, Google, Azure AD and any SAML provider.",
  },
  {
    icon: Fingerprint,
    title: "Role-based access",
    body: "Granular roles and permissions so people see only what they should.",
  },
  {
    icon: Lock,
    title: "Encrypted end to end",
    body: "AES-256 at rest, TLS 1.3 in transit. Your keys, your data.",
  },
  {
    icon: ScrollText,
    title: "Audit logs",
    body: "Every action recorded and exportable for compliance reviews.",
  },
];

const COMPLIANCE = ["SOC 2 Type II", "GDPR", "ISO 27001", "HIPAA"];

export function EnterpriseSecurity({ cta }: EnterpriseSecurityProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:auto-rows-[200px] md:grid-cols-4">
      <div className={cn(CARD, "md:col-span-2 md:row-span-2", "flex flex-col p-8")}>
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 -right-24 -z-0 h-72 w-72 rounded-full blur-3xl"
          style={{ background: "oklch(from var(--color-brand) l c h / 0.18)" }}
        />
        <div className="relative z-10 flex h-full flex-col">
          <span className="eyebrow-badge mb-6 self-start">
            {uiText("企业级能力", "Enterprise-ready")}
          </span>
          <h2 className="text-display-md text-foreground [&_em]:font-accent [&_em]:text-foreground/85 [&_em]:font-normal [&_em]:italic">
            {uiText("安全与管控，", "Security and control, ")}
            <em>{uiText("原生内置。", "built in.")}</em>
          </h2>
          <p className="text-foreground/70 mt-4 max-w-md text-base leading-relaxed">
            {uiText(
              "从第一天起，数据就具备加密、访问控制和审计能力。企业团队还可获得 SSO、数据驻留和专属客户成功经理支持。",
              "From day one your data is encrypted, access-controlled and audited. Enterprise teams get SSO, data residency and a dedicated success manager.",
            )}
          </p>

          <div className="mt-auto pt-8">
            <div className="flex flex-wrap gap-2">
              {COMPLIANCE.map((c) => (
                <span
                  key={c}
                  className="border-foreground/15 bg-background/40 text-foreground/80 inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 font-mono text-xs"
                >
                  <ShieldCheck className="text-brand h-3.5 w-3.5" />
                  {c}
                </span>
              ))}
            </div>
            {cta && (
              <Link
                href={cta.href}
                className="text-foreground hover:text-brand group/cta mt-6 inline-flex items-center gap-1.5 text-sm font-medium"
              >
                {cta.label}
                <ArrowUpRight className="h-4 w-4 transition-transform group-hover/cta:translate-x-0.5 group-hover/cta:-translate-y-0.5" />
              </Link>
            )}
          </div>
        </div>
      </div>

      {FEATURES.map((f) => (
        <div key={f.title} className={cn(CARD, "flex flex-col justify-center p-6")}>
          <span
            aria-hidden
            className="bg-brand/12 text-brand ring-brand/20 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ring-1"
          >
            <f.icon className="h-5 w-5" strokeWidth={2} />
          </span>
          <p className="text-foreground font-display mt-4 text-base font-bold">
            {uiText(
              {
                "SSO & SAML": "SSO 与 SAML",
                "Role-based access": "基于角色的访问控制",
                "Encrypted end to end": "端到端加密",
                "Audit logs": "审计日志",
              }[f.title] ?? f.title,
              f.title,
            )}
          </p>
          <p className="text-foreground/65 mt-1 text-sm leading-relaxed">
            {uiText(
              {
                "SSO & SAML": "支持 Okta、Google、Azure AD 以及任意 SAML 提供商一键登录。",
                "Role-based access": "通过细粒度角色和权限控制，让每个人只看到应有内容。",
                "Encrypted end to end":
                  "静态数据使用 AES-256，传输使用 TLS 1.3。数据与密钥均由你掌控。",
                "Audit logs": "记录所有关键操作，并可导出用于合规审查。",
              }[f.title] ?? f.body,
              f.body,
            )}
          </p>
        </div>
      ))}
    </div>
  );
}
