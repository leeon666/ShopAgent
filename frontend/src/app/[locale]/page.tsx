import type { Metadata } from "next";
import {
  Download,
  Lock,
  Quote,
  RefreshCw,
  Search,
  Smartphone,
  ThumbsUp,
  Users,
  Workflow,
} from "lucide-react";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n";
import { pageMetadata } from "@/lib/seo";

import { CaseStudy } from "@/components/marketing/case-study";
import { ComparisonTable } from "@/components/marketing/comparison-table";
import { DataFlowDiagram } from "@/components/marketing/data-flow-diagram";
import { EnterpriseSecurity } from "@/components/marketing/enterprise-security";
import { FaqAccordion } from "@/components/marketing/faq-accordion";
import { FeatureBento } from "@/components/marketing/feature-bento";
import { FeatureMockup } from "@/components/marketing/feature-mockup";
import { FinalCta } from "@/components/marketing/final-cta";
import { IntegrationsGrid } from "@/components/marketing/integrations-grid";
import { OutcomesBand } from "@/components/marketing/outcomes-band";
import {
  buildFooterColumns,
  buildFooterLegal,
  buildMarketingNav,
} from "@/components/marketing/footer-config";
import { Hero } from "@/components/marketing/hero";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { LogosStrip } from "@/components/marketing/logos-strip";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { Marquee } from "@/components/marketing/marquee";
import { PillNav } from "@/components/marketing/pill-nav";
import { PricingTeaser } from "@/components/marketing/pricing-teaser";
import { Reveal } from "@/components/marketing/reveal";
import { Section } from "@/components/marketing/section";
import { SmoothScroll } from "@/components/marketing/smooth-scroll";
import { TestimonialGrid } from "@/components/marketing/testimonial-grid";
import { JsonLd } from "@/components/seo/json-ld";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { faqSchema, organizationSchema, websiteSchema } from "@/lib/schema-org";

const LOGOS = [
  { brand: "google" as const, name: "Google" },
  { brand: "microsoft" as const, name: "Microsoft" },
  { brand: "stripe" as const, name: "Stripe" },
  { brand: "notion" as const, name: "Notion" },
  { brand: "linear" as const, name: "Linear" },
  { brand: "vercel" as const, name: "Vercel" },
  { brand: "figma" as const, name: "Figma" },
  { brand: "loom" as const, name: "Loom" },
];

const MARQUEE_ITEMS = [
  "Discover",
  "Search",
  "Summarize",
  "Decide",
  "Connect",
  "Automate",
  "Track",
  "Improve",
  "Onboard",
  "Analyze",
  "Translate",
  "Draft",
  "Schedule",
  "Resolve",
  "Forecast",
  "Iterate",
];

const MARQUEE_ITEMS_ZH = [
  "发现",
  "搜索",
  "总结",
  "决策",
  "连接",
  "自动化",
  "追踪",
  "优化",
  "引导",
  "分析",
  "翻译",
  "起草",
  "调度",
  "解决",
  "预测",
  "迭代",
];

const TESTIMONIALS = [
  {
    quote:
      "Our team finds answers in seconds instead of digging through Notion and Google Drive. It paid for itself in the first week.",
    name: "Marta Kowal",
    title: "Head of Operations",
    company: "Northwind Labs",
  },
  {
    quote:
      "We rolled it out to support, then sales picked it up, then everyone wanted access. It just keeps surprising us.",
    name: "Daniel Reyes",
    title: "VP Customer Success",
    company: "Acme Studios",
  },
  {
    quote:
      "The chat is great — the analytics dashboard is what sold it to me. We finally see how the team is using AI.",
    name: "Priya Anand",
    title: "Chief of Staff",
    company: "Helios",
  },
];

const TESTIMONIALS_ZH = [
  {
    quote: "团队现在几秒钟就能找到答案，不需要再翻 Notion 和 Google Drive。第一周就收回了成本。",
    name: "Marta Kowal",
    title: "运营负责人",
    company: "Northwind Labs",
  },
  {
    quote: "最初只给客服团队使用，后来销售也开始用，最后所有人都想要权限。它总能带来新的惊喜。",
    name: "Daniel Reyes",
    title: "客户成功副总裁",
    company: "Acme Studios",
  },
  {
    quote: "聊天体验很好，但真正打动我的是分析看板。我们终于能看到团队如何使用 AI。",
    name: "Priya Anand",
    title: "幕僚长",
    company: "Helios",
  },
];

const PLANS = [
  {
    name: "Starter",
    price: "$0",
    cadence: "/ month",
    description: "For individuals exploring the product.",
    features: ["100 messages / day", "1 connected data source", "Community support"],
    cta: { label: "Start free", href: ROUTES.REGISTER },
  },
  {
    name: "Pro",
    price: "$29",
    cadence: "/ user / month",
    description: "For small teams getting real work done.",
    features: [
      "Unlimited messages",
      "10 connected sources",
      "Email + chat support",
      "Workflow automations",
    ],
    cta: { label: "Start 14-day trial", href: ROUTES.REGISTER },
    featured: true,
    badge: "Most popular",
  },
  {
    name: "Business",
    price: "$99",
    cadence: "/ user / month",
    description: "For organisations rolling out across teams.",
    features: [
      "Everything in Pro",
      "SSO + audit log",
      "Role-based access control",
      "Dedicated success manager",
    ],
    cta: { label: "Talk to sales", href: ROUTES.CONTACT },
  },
];

const PLANS_ZH = [
  {
    name: "入门版",
    price: "¥0",
    cadence: "/ 月",
    description: "适合个人了解和使用产品。",
    features: ["每天 100 条消息", "连接 1 个数据源", "社区支持"],
    cta: { label: "免费开始", href: ROUTES.REGISTER },
  },
  {
    name: "专业版",
    price: "¥29",
    cadence: "/ 用户 / 月",
    description: "适合需要高效率协作的小团队。",
    features: ["不限消息数量", "连接 10 个数据源", "邮件与在线客服支持", "工作流自动化"],
    cta: { label: "开始 14 天试用", href: ROUTES.REGISTER },
    featured: true,
    badge: "最受欢迎",
  },
  {
    name: "企业版",
    price: "¥99",
    cadence: "/ 用户 / 月",
    description: "适合跨团队部署和统一管理。",
    features: ["包含专业版全部能力", "SSO 与审计日志", "基于角色的访问控制", "专属客户成功经理"],
    cta: { label: "联系销售", href: ROUTES.CONTACT },
  },
];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "marketing.landing" });
  return pageMetadata({
    title: APP_NAME,
    description: t("metaDescription"),
    path: "/",
    locale,
  });
}

export default async function HomePage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const isChinese = locale === "zh";
  const t = await getTranslations("marketing.landing");
  const tNav = await getTranslations("marketing");

  const navLinks = buildMarketingNav((k) => tNav(k));
  const footerColumns = buildFooterColumns((k) => tNav(k));
  const footerLegal = buildFooterLegal((k) => tNav(k));

  const heroStats = [
    { value: "10k", label: t("hero.stat_teams") },
    { value: "98%", label: t("hero.stat_speed") },
    { value: "24/7", label: t("hero.stat_uptime") },
  ];
  const faqItems = t.raw("faq.items") as { q: string; a: string }[];

  return (
    <>
      <SmoothScroll />
      <JsonLd data={[organizationSchema(), websiteSchema(), faqSchema(faqItems)]} />

      <PillNav
        brand={APP_NAME}
        links={navLinks}
        ctaLabel={tNav("nav.getStarted")}
        ctaHref={ROUTES.REGISTER}
        secondaryCta={{ label: tNav("nav.signIn"), href: ROUTES.LOGIN }}
      />

      <main id="main">
        <Hero
          eyebrow={t("hero.eyebrow")}
          title={
            <>
              {t("hero.titlePre")} <em>{t("hero.titleHighlight")}</em> <em>{t("hero.titleEm")}</em>
            </>
          }
          description={t("hero.description")}
          primaryCta={{ label: t("hero.ctaPrimary"), href: ROUTES.REGISTER }}
          secondaryCta={{ label: t("hero.ctaSecondary"), href: ROUTES.CONTACT }}
          ratingLabel={t("hero.ratingLabel")}
          trustNote={t("hero.trustNote")}
          stats={heroStats}
          theme="dark"
        />

        <Marquee items={isChinese ? MARQUEE_ITEMS_ZH : MARQUEE_ITEMS} />

        <Section theme="light" padding="py-16 md:py-20">
          <Reveal>
            <LogosStrip
              label={isChinese ? "受到各行业团队信赖" : "Trusted by teams across industries"}
              logos={LOGOS}
            />
          </Reveal>
        </Section>

        <Section theme="dark" id="how">
          <div className="mb-14 max-w-2xl">
            <div className="mb-5">
              <span className="eyebrow-badge">{isChinese ? "使用方式" : "How it works"}</span>
            </div>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
              {isChinese ? (
                <>
                  三步<em>开始使用。</em>
                </>
              ) : (
                <>
                  Get started in <em>three steps.</em>
                </>
              )}
            </h2>
          </div>
          <Reveal>
            <HowItWorks />
          </Reveal>
        </Section>

        <Section theme="light">
          <Reveal>
            <OutcomesBand />
          </Reveal>
        </Section>

        <Section theme="dark" id="features">
          <Reveal>
            <FeatureBento
              eyebrow={isChinese ? "连接知识" : "Connected knowledge"}
              title={
                isChinese ? (
                  <>
                    汇聚全部数据，<em>一个助手。</em>
                  </>
                ) : (
                  <>
                    All your data, <em>one assistant.</em>
                  </>
                )
              }
              description={
                isChinese
                  ? "支持从 Google Drive、Notion、Slack、S3 等来源同步。文件保留在原位置，系统持续建立索引并随时用于回答。"
                  : "Sync from Google Drive, Notion, Slack, S3 and more. Files stay where they are — we keep them indexed and ready to answer."
              }
              cta={{
                label: isChinese ? "查看已连接数据源" : "See connected sources",
                href: ROUTES.RAG,
              }}
              mockup={<FeatureMockup kind="rag" className="max-w-none" />}
              mockupSide="left"
              stat={{ value: "20+", label: isChinese ? "已连接数据源" : "connected data sources" }}
              bullets={[
                {
                  icon: RefreshCw,
                  title: isChinese ? "始终保持最新" : "Always up to date",
                  body: isChinese
                    ? "源文件发生变化后，索引会自动更新。"
                    : "Documents re-index automatically when they change at the source.",
                },
                {
                  icon: Lock,
                  title: isChinese ? "细粒度权限" : "Granular permissions",
                  body: isChinese
                    ? "每位用户只能看到自己有权访问的内容。"
                    : "Each user only sees what they're allowed to see. Nothing leaks.",
                },
                {
                  icon: Search,
                  title: isChinese ? "内置搜索" : "Built-in search",
                  body: isChinese
                    ? "在一个搜索框里检索所有已连接的数据源。"
                    : "Find anything across every connected source from one box.",
                },
              ]}
            />
          </Reveal>
        </Section>

        <Section theme="light">
          <Reveal>
            <FeatureBento
              eyebrow={isChinese ? "AI 对话" : "AI Chat"}
              title={
                isChinese ? (
                  <>
                    回答基于<em>你自己的业务内容。</em>
                  </>
                ) : (
                  <>
                    Answers grounded in <em>your own work.</em>
                  </>
                )
              }
              description={
                isChinese
                  ? "直接用自然语言提问，得到带引用来源的回答。助手会记住上下文，并随业务变化持续适应。"
                  : "Ask questions in plain English and get answers with citations. Your assistant remembers context and adapts as your work evolves."
              }
              cta={{ label: isChinese ? "试用对话" : "Try the chat", href: ROUTES.CHAT }}
              mockup={<FeatureMockup kind="agents" className="max-w-none" />}
              mockupSide="right"
              stat={{
                value: "100%",
                label: isChinese ? "回答均附带来源" : "answers cite their sources",
              }}
              bullets={[
                {
                  icon: Quote,
                  title: isChinese ? "每次都引用来源" : "Cites sources, every time",
                  body: isChinese
                    ? "每个回答都会链接回原始文档或工单。"
                    : "Every answer links back to the document or ticket it came from.",
                },
                {
                  icon: Workflow,
                  title: isChinese ? "多步骤推理" : "Multi-step reasoning",
                  body: isChinese
                    ? "把复杂请求拆解成多个步骤并逐步执行。"
                    : "Breaks complex requests into steps and acts on each.",
                },
                {
                  icon: Smartphone,
                  title: isChinese ? "支持网页和移动端" : "Works on web and mobile",
                  body: isChinese
                    ? "各设备体验一致，还可接入 Slack 和 Teams。"
                    : "Identical across devices, plus Slack and Teams integrations.",
                },
              ]}
            />
          </Reveal>
        </Section>

        <Section theme="dark">
          <Reveal>
            <FeatureBento
              eyebrow={isChinese ? "洞察分析" : "Insights"}
              title={
                isChinese ? (
                  <>
                    了解团队正在<em>关心什么。</em>
                  </>
                ) : (
                  <>
                    Know what your team <em>is asking.</em>
                  </>
                )
              }
              description={
                isChinese
                  ? "实时查看每个问题、评价和工作流执行情况，发现知识缺口、核心用户，并量化实际收益。"
                  : "A live dashboard of every question asked, answer rated, and workflow run. Spot gaps, find power users, and prove the ROI."
              }
              cta={{
                label: isChinese ? "查看仪表盘" : "Explore the dashboard",
                href: ROUTES.DASHBOARD,
              }}
              mockup={<FeatureMockup kind="billing" className="max-w-none" />}
              mockupSide="left"
              stat={{
                value: "+18%",
                label: isChinese ? "月均参与度提升" : "avg. monthly engagement",
              }}
              bullets={[
                {
                  icon: Users,
                  title: isChinese ? "按团队或个人统计使用情况" : "Usage by team or person",
                  body: isChinese
                    ? "下钻查看谁在使用、价值集中在哪些环节。"
                    : "Drill down to see who's getting value and where questions concentrate.",
                },
                {
                  icon: ThumbsUp,
                  title: isChinese ? "质量反馈闭环" : "Quality feedback loop",
                  body: isChinese
                    ? "用户评价回答，你可以看到哪些有效、哪些需要改进。"
                    : "Users rate answers; you see what's working and what to improve.",
                },
                {
                  icon: Download,
                  title: isChinese ? "导出到数据仓库" : "Export to your warehouse",
                  body: isChinese
                    ? "通过 API 把事件同步到 BigQuery、Snowflake 或内部工具。"
                    : "Stream events to BigQuery, Snowflake or your tools via the API.",
                },
              ]}
            />
          </Reveal>
        </Section>

        <Section theme="light" className="relative overflow-hidden">
          <div aria-hidden className="bg-dots pointer-events-none absolute inset-0 -z-10" />
          <div className="mb-14 max-w-2xl">
            <div className="mb-5">
              <span className="eyebrow-badge">
                {isChinese ? "数据如何连接" : "How it connects"}
              </span>
            </div>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
              {isChinese ? (
                <>
                  数据流入，<em>答案返回。</em>
                </>
              ) : (
                <>
                  Your data flows in. <em>Answers come back.</em>
                </>
              )}
            </h2>
            <p className="text-foreground/70 mt-5 max-w-xl text-lg leading-relaxed">
              {isChinese
                ? "源文档、对话和云端文件会持续建立索引。每个回答都基于你自己的业务内容，并附带回溯到原始来源的引用。"
                : "Source documents, conversations, and cloud files are continuously indexed. Every answer is grounded in your own work — with citations back to the source."}
            </p>
          </div>
          <Reveal>
            <DataFlowDiagram />
          </Reveal>
        </Section>

        <Section theme="dark" id="security">
          <Reveal>
            <EnterpriseSecurity
              cta={{
                label: isChinese ? "查看安全说明" : "Read our security overview",
                href: ROUTES.SECURITY,
              }}
            />
          </Reveal>
        </Section>

        <Section theme="light">
          <Reveal>
            <IntegrationsGrid
              cta={{
                label: isChinese ? "浏览全部集成" : "Browse all integrations",
                href: ROUTES.HELP,
              }}
            />
          </Reveal>
        </Section>

        <Section theme="dark">
          <Reveal>
            <CaseStudy
              quote={
                isChinese
                  ? "我们替换了三个内部工具，把答案获取时间从数小时缩短到几秒。新员工上手时间也从一个月缩短到一周。"
                  : "We replaced three internal tools and cut answer time from hours to seconds. Onboarding a new hire used to take a month — now it's a week."
              }
              name="Marta Kowal"
              role={isChinese ? "首席运营官" : "COO"}
              company="Northwind Labs"
              metrics={[
                { value: "−68%", label: isChinese ? "首次获得答案耗时" : "time to first answer" },
                { value: "3×", label: isChinese ? "上手速度提升" : "faster onboarding" },
                { value: "12 小时", label: isChinese ? "每人每周节省" : "saved per person / week" },
              ]}
            />
          </Reveal>
        </Section>

        <Section theme="light">
          <div className="mb-14 text-center">
            <p className="eyebrow text-foreground/55 mb-4">{t("testimonials.eyebrow")}</p>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent mx-auto max-w-2xl [&_em]:font-normal [&_em]:italic">
              {t("testimonials.titlePre")} <em>{t("testimonials.titleEm")}</em>
            </h2>
          </div>
          <Reveal>
            <TestimonialGrid items={isChinese ? TESTIMONIALS_ZH : TESTIMONIALS} />
          </Reveal>
        </Section>

        <Section theme="light">
          <Reveal>
            <ComparisonTable
              brand={APP_NAME}
              alternatives={
                isChinese
                  ? ["通用 AI 聊天", "自研 / 内部搭建"]
                  : ["Generic AI chat", "DIY / in-house"]
              }
              rows={[
                {
                  feature: isChinese ? "基于你自己的数据" : "Grounded in your own data",
                  cells: ["yes", "no", "partial"],
                },
                {
                  feature: isChinese ? "每个回答都有引用" : "Citations on every answer",
                  cells: ["yes", "no", "partial"],
                },
                {
                  feature: isChinese ? "连接你现有的工具" : "Connects to your tools",
                  cells: ["yes", "partial", "partial"],
                },
                {
                  feature: isChinese ? "企业安全（SSO、审计）" : "Enterprise security (SSO, audit)",
                  cells: ["yes", "partial", "partial"],
                },
                {
                  feature: isChinese ? "使用分析与 ROI" : "Usage analytics & ROI",
                  cells: ["yes", "no", "partial"],
                },
                {
                  feature: isChinese ? "几分钟内上线" : "Live in minutes",
                  cells: ["yes", "yes", "no"],
                },
                {
                  feature: isChinese ? "专属支持" : "Dedicated support",
                  cells: ["yes", "no", "partial"],
                },
              ]}
            />
          </Reveal>
        </Section>

        <Section theme="dark" id="pricing">
          <div className="mb-14 max-w-2xl">
            <div className="mb-5">
              <span className="eyebrow-badge">{t("pricing.eyebrow")}</span>
            </div>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
              {t("pricing.titlePre")} <em>{t("pricing.titleEm")}</em>
            </h2>
            <p className="text-foreground/70 mt-5 max-w-xl text-lg leading-relaxed">
              {t("pricing.subtitle")}
            </p>
          </div>
          <Reveal>
            <PricingTeaser plans={isChinese ? PLANS_ZH : PLANS} fullPricingHref={ROUTES.PRICING} />
          </Reveal>
        </Section>

        <Section theme="light" id="faq">
          <div className="mb-14 text-center">
            <p className="eyebrow text-foreground/55 mb-4">{t("faq.eyebrow")}</p>
            <h2 className="text-display-lg text-foreground">{t("faq.title")}</h2>
          </div>
          <Reveal>
            <FaqAccordion
              items={faqItems.map((it) => ({ ...it, q: it.q.replace("{appName}", APP_NAME) }))}
            />
          </Reveal>
        </Section>

        <Section theme="light" padding="pb-24 md:pb-32">
          <Reveal>
            <FinalCta
              stat={{ value: t("finalCta.statValue"), label: t("finalCta.statLabel") }}
              title={
                <>
                  {t("finalCta.titlePre")} <em>{t("finalCta.titleEm")}</em>
                </>
              }
              description={t("finalCta.description")}
              primary={{ label: t("finalCta.primary"), href: ROUTES.REGISTER }}
              secondary={{ label: t("finalCta.secondary"), href: ROUTES.PRICING }}
            />
          </Reveal>
        </Section>
      </main>

      <MarketingFooter
        brand={APP_NAME}
        tagline={tNav("footer.tagline")}
        operationalLabel={tNav("footer.operational")}
        columns={footerColumns}
        legal={footerLegal}
      />
    </>
  );
}
