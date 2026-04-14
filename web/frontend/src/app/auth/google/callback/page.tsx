"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function GoogleCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    // Google redirects here with query params: ?code=xxx&state=xxx&...
    // Forward to backend callback so it can exchange code for JWT token
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");

    if (!code) {
      router.replace("/");
      return;
    }

    // Redirect to backend callback - backend will process and redirect back
    // to frontend /auth/callback?token=xxx
    const backendCallbackUrl = `${API_URL}/auth/google/callback?code=${encodeURIComponent(code || "")}&state=${encodeURIComponent(state || "")}`;
    window.location.href = backendCallbackUrl;
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <p className="text-[var(--color-text)]">正在处理登录...</p>
      </div>
    </div>
  );
}
