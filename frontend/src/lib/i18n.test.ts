import { describe, expect, it } from "vitest";

import { getLocaleLabel, locales } from "@/i18n";

describe("supported locales", () => {
  it("only exposes Simplified Chinese and English", () => {
    expect(locales).toEqual(["zh", "en"]);
    expect(locales.map(getLocaleLabel)).toEqual(["简体中文", "English"]);
  });
});
