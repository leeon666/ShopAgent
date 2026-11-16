"use client";

import Link from "next/link";
import { useLocale } from "next-intl";
import { ArrowRight, ShoppingBag } from "lucide-react";

import { ChatContainer, ConversationSidebar } from "@/components/chat";
import { ROUTES } from "@/lib/constants";

export default function ChatPage() {
  const isChinese = useLocale() === "zh";

  // The ?id= query param is read by useConversations.fetchConversations on mount;
  // it sets currentConversationId AND loads messages atomically. Pre-setting the
  // id here would short-circuit that loader and leave the chat empty on refresh.
  return (
    <div className="-mx-3 -mt-4 -mb-20 flex min-h-0 flex-1 flex-col sm:-mx-6 sm:-mt-8 lg:-mb-8">
      <div className="border-border bg-card mx-3 mb-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3 sm:mx-6">
        <div className="flex items-center gap-2">
          <ShoppingBag className="h-4 w-4" />
          <p className="text-sm">
            {isChinese
              ? "订单、售后工单和退款审批在售后工作台中处理。"
              : "Orders, after-sales tickets, and refund approvals live in the workbench."}
          </p>
        </div>
        <Link
          href={ROUTES.SHOP}
          className="text-foreground inline-flex items-center gap-1 text-sm font-medium hover:underline"
        >
          {isChinese ? "查看我的订单" : "Open after-sales workbench"}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
      <div className="flex min-h-0 flex-1">
        <ConversationSidebar />
        <div className="min-w-0 flex-1">
          <ChatContainer />
        </div>
      </div>
    </div>
  );
}
