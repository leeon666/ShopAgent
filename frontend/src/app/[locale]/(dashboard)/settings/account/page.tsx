"use client";

import { useState } from "react";
import { AlertTriangle, Lock } from "lucide-react";
import { useLocale } from "next-intl";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
  Button,
  FormField,
  Input,
} from "@/components/ui";
import { SectionCard } from "@/components/settings/settings-section";
import { useAuth } from "@/hooks";
import { apiClient, ApiError } from "@/lib/api-client";

export default function AccountSettingsPage() {
  const isChinese = useLocale() === "zh";
  const { user, logout } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleChangePassword = async () => {
    if (newPassword.length < 8) {
      toast.error(
        isChinese ? "新密码至少需要 8 个字符" : "New password must be at least 8 characters",
      );
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error(isChinese ? "两次输入的密码不一致" : "Passwords do not match");
      return;
    }
    setSaving(true);
    try {
      await apiClient.post("/auth/password/change", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success(isChinese ? "密码已更新" : "Password updated");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      // Backend may not have this endpoint yet — surface a helpful message.
      if (err instanceof ApiError && err.status === 404) {
        toast.error(
          isChinese
            ? "当前后端尚未启用修改密码接口。"
            : "Password change requires backend wiring (POST /auth/password/change).",
        );
      } else {
        toast.error(
          err instanceof ApiError
            ? err.message
            : isChinese
              ? "修改密码失败"
              : "Failed to update password",
        );
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!user) return;
    setDeleting(true);
    try {
      await apiClient.delete(`/users/${user.id}`);
      toast.success(isChinese ? "账户已删除" : "Account deleted");
      logout();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        toast.error(
          isChinese
            ? "当前未开放自助注销，请联系管理员。"
            : "Self-delete not enabled. Contact support.",
        );
      } else {
        toast.error(
          err instanceof ApiError
            ? err.message
            : isChinese
              ? "删除账户失败"
              : "Failed to delete account",
        );
      }
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <SectionCard
        title={isChinese ? "修改密码" : "Change password"}
        description={
          isChinese
            ? "请使用强度较高且不重复的密码：至少 8 位，并包含大小写字母和数字。"
            : "Use a strong, unique password — 8+ characters, mixed case, numbers."
        }
        action={
          <Button
            onClick={handleChangePassword}
            disabled={saving || !currentPassword || !newPassword}
            size="sm"
          >
            {saving
              ? isChinese
                ? "保存中…"
                : "Saving…"
              : isChinese
                ? "更新密码"
                : "Update password"}
          </Button>
        }
      >
        <div className="space-y-4">
          <FormField label={isChinese ? "当前密码" : "Current password"} htmlFor="current-pw">
            <Input
              id="current-pw"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
            />
          </FormField>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label={isChinese ? "新密码" : "New password"} htmlFor="new-pw">
              <Input
                id="new-pw"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
              />
            </FormField>
            <FormField
              label={isChinese ? "确认新密码" : "Confirm new password"}
              htmlFor="confirm-pw"
            >
              <Input
                id="confirm-pw"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
              />
            </FormField>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title={isChinese ? "退出所有设备" : "Sign out everywhere"}
        description={
          isChinese
            ? "撤销包括当前设备在内的所有登录会话，你会立即退出登录。"
            : "Revoke every active session including this one. You'll be signed out immediately."
        }
      >
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="sm">
              <Lock className="mr-2 h-3.5 w-3.5" />
              {isChinese ? "退出所有设备" : "Sign out everywhere"}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                {isChinese ? "要退出所有设备吗？" : "Sign out from all devices?"}
              </AlertDialogTitle>
              <AlertDialogDescription>
                {isChinese
                  ? "这会撤销所有活动会话，同时也会退出当前设备。"
                  : "This revokes every active session and signs you out of this device too."}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{isChinese ? "取消" : "Cancel"}</AlertDialogCancel>
              <AlertDialogAction
                onClick={async () => {
                  try {
                    await apiClient.delete("/sessions");
                    toast.success(isChinese ? "已退出所有设备" : "Signed out from all devices");
                    logout();
                  } catch {
                    toast.error(isChinese ? "退出所有设备失败" : "Failed to sign out everywhere");
                  }
                }}
              >
                {isChinese ? "退出所有设备" : "Sign out everywhere"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </SectionCard>

      <SectionCard
        title={isChinese ? "删除账户" : "Delete account"}
        description={
          isChinese
            ? "永久删除账户、对话和已上传的数据，此操作无法撤销。"
            : "Permanently remove your account, conversations, and uploaded data. This can't be undone."
        }
      >
        <div className="border-border bg-muted flex items-start gap-3 rounded-xl border p-4">
          <span className="bg-card border-border text-muted-foreground flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border">
            <AlertTriangle className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-foreground text-sm font-semibold">
              {isChinese ? "此操作不可逆" : "This is irreversible"}
            </p>
            <p className="text-muted-foreground mt-0.5 text-xs leading-relaxed">
              {isChinese
                ? "所有对话、知识库内容、API 密钥和个人数据都会被永久删除，当前订阅也会被取消。"
                : "All conversations, knowledge base contents, API keys, and personal data will be permanently deleted. Active subscriptions will be canceled."}
            </p>
          </div>
        </div>
        <div className="mt-4">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm">
                {isChinese ? "删除我的账户" : "Delete my account"}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>
                  {isChinese ? "要删除账户吗？" : "Delete your account?"}
                </AlertDialogTitle>
                <AlertDialogDescription>
                  {isChinese
                    ? "你的对话、知识库内容、API 密钥和所有个人数据都会被永久删除，当前订阅也会被取消。此操作无法撤销。"
                    : "Your conversations, knowledge base contents, API keys, and all personal data will be permanently deleted. Active subscriptions will be canceled. This cannot be undone."}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>{isChinese ? "取消" : "Cancel"}</AlertDialogCancel>
                <AlertDialogAction
                  disabled={deleting}
                  onClick={handleDeleteAccount}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  {deleting
                    ? isChinese
                      ? "删除中…"
                      : "Deleting…"
                    : isChinese
                      ? "确认删除我的账户"
                      : "Yes, delete my account"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </SectionCard>
    </div>
  );
}
