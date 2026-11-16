"use client";

import { useState } from "react";
import { notFound } from "next/navigation";
import { Sparkles, Trash2 } from "lucide-react";

import { PageHeader } from "@/components/dashboard/page-header";
import { StatCard } from "@/components/dashboard/stat-card";
import { EmptyState } from "@/components/states";
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Badge,
  Button,
  ConfirmDialog,
  FormField,
  IconButton,
  Input,
  SectionHeading,
} from "@/components/ui";

/**
 * Dev-only component gallery — a lightweight stand-in for Storybook that keeps
 * the design system honest. Renders the core primitives in one place so visual
 * regressions are easy to spot. Hidden in production builds.
 */
export default function ComponentGalleryPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return <Gallery />;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-border bg-card rounded-xl border p-5">
      <SectionHeading eyebrow="基础组件" title={title} className="mb-4" />
      <div className="flex flex-wrap items-start gap-3">{children}</div>
    </section>
  );
}

function Gallery() {
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <div className="space-y-6 pb-8">
      <PageHeader eyebrow="开发" title="组件展示" description="集中展示设计系统的基础组件。" />

      <Section title="按钮样式">
        {(["default", "secondary", "outline", "ghost", "destructive", "link"] as const).map((v) => (
          <Button key={v} variant={v}>
            {v}
          </Button>
        ))}
      </Section>

      <Section title="按钮尺寸">
        <Button size="sm">小号</Button>
        <Button size="default">默认</Button>
        <Button size="lg">大号</Button>
        <IconButton aria-label="闪光" size="icon-sm">
          <Sparkles />
        </IconButton>
        <IconButton aria-label="删除" size="icon">
          <Trash2 />
        </IconButton>
      </Section>

      <Section title="徽章">
        {(["default", "secondary", "outline", "destructive"] as const).map((v) => (
          <Badge key={v} variant={v}>
            {v}
          </Badge>
        ))}
      </Section>

      <Section title="提示">
        <div className="w-full space-y-2">
          {(["default", "warning", "destructive", "success"] as const).map((v) => (
            <Alert key={v} variant={v}>
              <AlertTitle>提示类型：{v}</AlertTitle>
              <AlertDescription>这里展示一条需要用户注意的提示信息。</AlertDescription>
            </Alert>
          ))}
        </div>
      </Section>

      <Section title="表单字段">
        <div className="w-full max-w-sm space-y-4">
          <FormField label="显示名称" htmlFor="g-name" description="团队成员可以看到。">
            <Input id="g-name" placeholder="Ada Lovelace" />
          </FormField>
          <FormField label="邮箱" htmlFor="g-email" error="该邮箱已被使用。" required>
            <Input id="g-email" type="email" defaultValue="taken@example.com" />
          </FormField>
        </div>
      </Section>

      <Section title="统计卡片">
        <div className="grid w-full gap-3 sm:grid-cols-3">
          <StatCard label="额度" value="1,240" delta={12.5} deltaLabel="较前 7 天" />
          <StatCard label="对话" value="38" footer="全部聊天" />
          <StatCard label="知识库" value="0" unit="个向量" />
        </div>
      </Section>

      <Section title="空状态">
        <div className="w-full">
          <EmptyState
            icon={Sparkles}
            title="这里还没有内容"
            description="创建第一条内容即可开始使用。"
            cta={{ label: "创建", onClick: () => {} }}
          />
        </div>
      </Section>

      <Section title="确认对话框">
        <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
          删除内容…
        </Button>
        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          title="要删除此资源吗？"
          description="此操作无法撤销。"
          destructive
          confirmText="删除"
          confirmLabel="删除"
          onConfirm={() => setConfirmOpen(false)}
        />
      </Section>
    </div>
  );
}
