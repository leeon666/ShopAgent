import { fireEvent, render, screen } from "@testing-library/react";
import { PackageCheck } from "lucide-react";
import { describe, expect, it, vi } from "vitest";

import { ChatEmptyState } from "./chat-empty-state";

vi.mock("next-intl", () => ({
  useLocale: () => "zh",
}));

vi.mock("@/hooks", () => ({
  useAuth: () => ({ user: null }),
}));

describe("ChatEmptyState", () => {
  it("uses page-specific prompts instead of generic Chinese prompts", () => {
    const onPick = vi.fn();

    render(
      <ChatEmptyState
        onPick={onPick}
        prompts={[
          {
            icon: PackageCheck,
            title: "检查物流异常",
            prompt: "请说明物流停滞 72 小时应该怎么处理。",
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /检查物流异常/ }));

    expect(onPick).toHaveBeenCalledWith("请说明物流停滞 72 小时应该怎么处理。");
    expect(screen.queryByText("总结知识库")).not.toBeInTheDocument();
  });
});
