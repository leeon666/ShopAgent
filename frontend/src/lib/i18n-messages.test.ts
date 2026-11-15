import { describe, expect, it } from "vitest";

import en from "../../messages/en.json";
import zh from "../../messages/zh.json";

function flatten(value: unknown, prefix = ""): Record<string, string> {
  const output: Record<string, string> = {};
  if (typeof value === "string") {
    output[prefix] = value;
    return output;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => Object.assign(output, flatten(item, `${prefix}[${index}]`)));
    return output;
  }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      Object.assign(output, flatten(child, prefix ? `${prefix}.${key}` : key));
    }
  }
  return output;
}

function placeholders(value: string): string[] {
  return [...value.matchAll(/\{[^}]+\}/g)].map((match) => match[0]).sort();
}

describe("Simplified Chinese messages", () => {
  it("has exactly the same message keys as English", () => {
    expect(Object.keys(flatten(zh)).sort()).toEqual(Object.keys(flatten(en)).sort());
  });

  it("preserves every interpolation placeholder", () => {
    const english = flatten(en);
    const chinese = flatten(zh);
    for (const [key, value] of Object.entries(english)) {
      expect(placeholders(chinese[key] ?? ""), key).toEqual(placeholders(value));
    }
  });
});
