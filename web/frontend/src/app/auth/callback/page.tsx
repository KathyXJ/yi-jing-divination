"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { handleAuthCallback } from "@/lib/auth";

export default function AuthCallbackPage() {
  const router = useRouter();

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
        <p className="text-[var(--color-text)]">登录中...</p>
      </div>
    </div>
  );
}
