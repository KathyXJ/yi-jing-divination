"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { handleAuthCallback } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

export default function AuthCallbackPage() {
  const router = useRouter();
  const { lang } = useLang();

  useEffect(() => {
    const token = handleAuthCallback();
    if (token) {
      // 登录成功，跳回首页
      router.replace("/");
    } else {
      // 没有 token，跳回首页
      router.replace("/");
    }
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <p className="text-[var(--color-text)]">
          {lang === "zh" ? "登录中..." : "Logging in..."}
        </p>
      </div>
    </div>
  );
}
