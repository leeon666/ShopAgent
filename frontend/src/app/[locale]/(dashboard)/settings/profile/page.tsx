"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, Globe, Monitor, Smartphone, Trash2 } from "lucide-react";
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
import {
  cn,
  formatDate,
  getErrorMessage,
  isAppAdmin,
  MAX_AVATAR_SIZE_BYTES,
  timeAgo,
} from "@/lib/utils";
import { useAuthStore } from "@/stores";
import type { Session, SessionListResponse, User } from "@/types";

function DeviceIcon({ type }: { type?: string | null }) {
  if (type === "mobile") return <Smartphone className="h-4 w-4" />;
  if (type === "desktop") return <Monitor className="h-4 w-4" />;
  return <Globe className="h-4 w-4" />;
}

export default function ProfileSettingsPage() {
  const isChinese = useLocale() === "zh";
  const { user } = useAuth();
  const { setUser, bumpAvatarVersion, avatarVersion } = useAuthStore();

  const [name, setName] = useState(user?.full_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [saving, setSaving] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const avatarInputRef = useRef<HTMLInputElement>(null);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  // Backend may not have a sessions endpoint when `enable_session_management`
  // is off (stateless JWT). Track availability so we can hide the whole section
  // instead of showing a misleading "no data" placeholder.
  const [sessionsAvailable, setSessionsAvailable] = useState(true);

  useEffect(() => {
    setName(user?.full_name ?? "");
    setEmail(user?.email ?? "");
  }, [user?.id, user?.email, user?.full_name]);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await apiClient.get<SessionListResponse>("/sessions");
      setSessions(data.sessions);
      setSessionsAvailable(true);
    } catch (err) {
      // 404 = endpoint not exposed (session management disabled at gen time).
      if (err instanceof ApiError && err.status === 404) {
        setSessionsAvailable(false);
      }
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleSaveProfile = async () => {
    if (!user) return;
    setSaving(true);
    try {
      const payload: { email?: string; full_name?: string | null } = {};
      if (email !== user.email) payload.email = email;
      if (name !== (user.full_name ?? "")) payload.full_name = name || null;
      if (Object.keys(payload).length === 0) {
        toast.info(isChinese ? "没有需要保存的修改" : "Nothing changed");
        setSaving(false);
        return;
      }
      const updated = await apiClient.patch<User>("/users/me", payload);
      setUser(updated);
      toast.success(isChinese ? "个人资料已更新" : "Profile updated");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.message
          : isChinese
            ? "更新个人资料失败"
            : "Failed to update profile",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    if (file.size > MAX_AVATAR_SIZE_BYTES) {
      toast.error(isChinese ? "头像文件过大，最大支持 2MB。" : "Avatar too large. Maximum 2MB.");
      return;
    }
    setAvatarUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/users/me/avatar", { method: "POST", body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({
          detail: isChinese ? "上传失败" : "Upload failed",
        }));
        throw new Error(err.detail || (isChinese ? "上传失败" : "Upload failed"));
      }
      const updated = await res.json();
      setUser(updated);
      bumpAvatarVersion();
      toast.success(isChinese ? "头像已更新" : "Avatar updated");
    } catch (err) {
      toast.error(getErrorMessage(err, isChinese ? "上传头像失败" : "Failed to upload avatar"));
    } finally {
      setAvatarUploading(false);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await apiClient.delete(`/sessions/${sessionId}`);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      toast.success(isChinese ? "登录会话已撤销" : "Session revoked");
    } catch {
      toast.error(isChinese ? "撤销登录会话失败" : "Failed to revoke session");
    }
  };

  const handleRevokeAll = async () => {
    try {
      await apiClient.delete("/sessions");
      setSessions((prev) => prev.filter((s) => s.is_current));
      toast.success(isChinese ? "其他登录会话已全部撤销" : "All other sessions revoked");
    } catch {
      toast.error(isChinese ? "撤销登录会话失败" : "Failed to revoke sessions");
    }
  };

  if (!user) {
    return null;
  }

  return (
    <div className="space-y-6">
      <SectionCard
        title={isChinese ? "头像" : "Avatar"}
        description={
          isChinese
            ? "建议使用正方形图片，最大 2MB，支持 JPG、PNG、WEBP 或 GIF。"
            : "Square images look best. Up to 2MB. JPG, PNG, WEBP, or GIF."
        }
      >
        <div className="flex items-center gap-5">
          <button
            type="button"
            onClick={() => avatarInputRef.current?.click()}
            disabled={avatarUploading}
            aria-label={
              user.avatar_url
                ? isChinese
                  ? "更换头像"
                  : "Replace avatar"
                : isChinese
                  ? "上传头像"
                  : "Upload avatar"
            }
            className="border-border bg-muted hover:bg-accent group relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-xl border transition-colors"
          >
            {user.avatar_url ? (
              <Image
                src={`/api/users/avatar/${user.id}?v=${avatarVersion}`}
                alt=""
                width={80}
                height={80}
                className="h-full w-full object-cover"
                unoptimized
              />
            ) : (
              <span className="text-foreground text-lg font-semibold">
                {(user.full_name || user.email).slice(0, 2).toUpperCase()}
              </span>
            )}
            <span className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 transition-opacity group-hover:opacity-100">
              <Camera className="h-5 w-5 text-white" />
            </span>
          </button>
          <input
            ref={avatarInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleAvatarUpload}
            className="hidden"
          />
          <div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => avatarInputRef.current?.click()}
              disabled={avatarUploading}
            >
              {avatarUploading
                ? isChinese
                  ? "上传中…"
                  : "Uploading…"
                : user.avatar_url
                  ? isChinese
                    ? "更换头像"
                    : "Replace avatar"
                  : isChinese
                    ? "上传头像"
                    : "Upload avatar"}
            </Button>
            <p className="text-muted-foreground mt-2 text-xs">
              {isAppAdmin(user) ? (isChinese ? "管理员 · " : "Admin · ") : ""}
              {isChinese ? "加入于 " : "Member since "}
              {formatDate(user.created_at)}
            </p>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title={isChinese ? "个人信息" : "Personal info"}
        description={
          isChinese
            ? "共享组织中的成员可以看到这些信息。"
            : "Visible to teammates in shared organizations."
        }
        action={
          <Button onClick={handleSaveProfile} disabled={saving} size="sm">
            {saving ? (isChinese ? "保存中…" : "Saving…") : isChinese ? "保存修改" : "Save changes"}
          </Button>
        }
      >
        <div className="space-y-4">
          <FormField label={isChinese ? "显示名称" : "Display name"} htmlFor="profile-name">
            <Input
              id="profile-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={isChinese ? "你希望别人怎么称呼你？" : "How should we call you?"}
            />
          </FormField>
          <FormField
            label={isChinese ? "邮箱" : "Email"}
            htmlFor="profile-email"
            description={
              isChinese
                ? "修改邮箱后，可能需要根据当前认证方式重新验证。"
                : "Changing email may require re-verification depending on your auth setup."
            }
          >
            <Input
              id="profile-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </FormField>
        </div>
      </SectionCard>

      {sessionsAvailable && (
        <SectionCard
          title={isChinese ? "活动登录会话" : "Active sessions"}
          description={
            isChinese ? "当前已登录此账户的设备。" : "Devices currently signed in to your account."
          }
          action={
            sessions.filter((s) => !s.is_current).length > 0 ? (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    {isChinese ? "撤销其他会话" : "Revoke all others"}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>
                      {isChinese ? "要撤销其他所有会话吗？" : "Revoke all other sessions?"}
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                      {isChinese
                        ? "除当前设备外，所有已登录此账户的设备都会退出登录。"
                        : "Every device signed in to your account will be signed out, except this one."}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>{isChinese ? "取消" : "Cancel"}</AlertDialogCancel>
                    <AlertDialogAction onClick={handleRevokeAll}>
                      {isChinese ? "全部撤销" : "Revoke all"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            ) : null
          }
        >
          {sessionsLoading ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="bg-muted h-14 animate-pulse rounded-xl" />
              ))}
            </div>
          ) : sessions.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              {isChinese ? "暂无登录会话数据。" : "No session data available."}
            </p>
          ) : (
            <ul className="space-y-2">
              {sessions.map((session) => (
                <li
                  key={session.id}
                  className={cn(
                    "border-border flex items-center justify-between gap-3 rounded-xl border px-4 py-3",
                    session.is_current ? "bg-muted" : "bg-card hover:bg-accent",
                  )}
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="bg-muted text-muted-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
                      <DeviceIcon type={session.device_type} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-foreground flex items-center gap-2 text-sm font-medium">
                        <span className="truncate">
                          {session.device_name &&
                          !["unknown browser", "unknown device"].includes(
                            session.device_name.toLowerCase(),
                          )
                            ? session.device_name
                            : isChinese
                              ? "未知浏览器"
                              : "Unknown browser"}
                        </span>
                        {session.is_current && (
                          <span className="bg-card border-border text-muted-foreground inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase">
                            {isChinese ? "当前" : "Current"}
                          </span>
                        )}
                      </p>
                      <p className="text-muted-foreground truncate text-xs">
                        {session.ip_address && `${session.ip_address} · `}
                        {isChinese ? "最后活动：" : "Last active "}
                        {timeAgo(session.last_used_at)}
                      </p>
                    </div>
                  </div>
                  {!session.is_current && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground hover:text-destructive h-8 shrink-0"
                      onClick={() => handleRevokeSession(session.id)}
                      title={isChinese ? "撤销会话" : "Revoke session"}
                      aria-label={isChinese ? "撤销会话" : "Revoke session"}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      )}
    </div>
  );
}
