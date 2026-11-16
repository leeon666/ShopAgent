"use client";

import { useEffect, useState } from "react";
import { Moon, Sun, Monitor } from "lucide-react";
import { useLocale } from "next-intl";
import { Button } from "@/components/ui/button";
import { useThemeStore, Theme, getResolvedTheme } from "@/stores/theme-store";

interface ThemeToggleProps {
  variant?: "icon" | "dropdown";
  className?: string;
}

export function ThemeToggle({ variant = "icon", className }: ThemeToggleProps) {
  const isChinese = useLocale() === "zh";
  const { theme, setTheme } = useThemeStore();
  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch by only rendering after mount
  useEffect(() => {
    setMounted(true);
  }, []);

  const resolvedTheme = getResolvedTheme(theme);

  const cycleTheme = () => {
    const themes: Theme[] = ["light", "dark", "system"];
    const currentIndex = themes.indexOf(theme ?? "system");
    const nextIndex = (currentIndex + 1) % themes.length;
    setTheme(themes[nextIndex] ?? "system");
  };

  // Render placeholder during SSR to prevent hydration mismatch
  if (!mounted) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className={className}
        aria-label={isChinese ? "切换主题" : "Toggle theme"}
      >
        <Sun className="h-5 w-5" />
      </Button>
    );
  }

  if (variant === "icon") {
    return (
      <Button
        variant="ghost"
        size="icon"
        onClick={cycleTheme}
        className={className}
        aria-label={isChinese ? `切换主题（当前：${theme}）` : `Switch theme (current: ${theme})`}
        title={isChinese ? `主题：${theme}` : `Theme: ${theme}`}
      >
        {resolvedTheme === "dark" ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
        {theme === "system" && (
          <span className="sr-only">{isChinese ? "（跟随系统）" : "(following system)"}</span>
        )}
      </Button>
    );
  }

  return (
    <div className={`flex gap-1 ${className}`}>
      <Button
        variant={theme === "light" ? "default" : "ghost"}
        size="icon"
        onClick={() => setTheme("light")}
        aria-label={isChinese ? "浅色模式" : "Light mode"}
        title={isChinese ? "浅色模式" : "Light mode"}
      >
        <Sun className="h-4 w-4" />
      </Button>
      <Button
        variant={theme === "dark" ? "default" : "ghost"}
        size="icon"
        onClick={() => setTheme("dark")}
        aria-label={isChinese ? "深色模式" : "Dark mode"}
        title={isChinese ? "深色模式" : "Dark mode"}
      >
        <Moon className="h-4 w-4" />
      </Button>
      <Button
        variant={theme === "system" ? "default" : "ghost"}
        size="icon"
        onClick={() => setTheme("system")}
        aria-label={isChinese ? "跟随系统" : "System theme"}
        title={isChinese ? "跟随系统" : "System theme"}
      >
        <Monitor className="h-4 w-4" />
      </Button>
    </div>
  );
}
