/**
 * Cloudflare Worker: Google OAuth Callback 中转
 * 
 * 拦截 /auth/google/callback，将请求转发到 Render 后端换 token，
 * 再重定向回前端页面，避免用户看到 Render 域名。
 * 
 * 流程：
 *   Google → Worker(i-chingstudio.cc) → Render(callback) → Worker(重定向) → 前端(callback) → 首页
 */

// 后端 OAuth callback 地址（不变）
const BACKEND_CALLBACK = "https://yi-jing-divination-4h6y.onrender.com/auth/google/callback";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 只处理 /auth/google/callback
    if (url.pathname !== "/auth/google/callback") {
      // 其他请求走正常的 Next.js 页面（Cloudflare Pages 自动处理）
      return fetch(request);
    }

    // 提取 Google 返回的 code 和 state
    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state");
    const error = url.searchParams.get("error");

    // 如果 Google 返回了错误
    if (error) {
      const errorUrl = new URL("/auth/callback", url.origin);
      errorUrl.searchParams.set("error", error);
      return Response.redirect(errorUrl.toString(), 302);
    }

    if (!code) {
      return new Response("Missing code parameter", { status: 400 });
    }

    try {
      // 构建转发到后端的 URL（带上 code 和 state）
      const backendUrl = new URL(BACKEND_CALLBACK);
      backendUrl.searchParams.set("code", code);
      if (state) backendUrl.searchParams.set("state", state);

      // 转发 GET 请求到后端（后端会返回 307 重定向到前端页面）
      const response = await fetch(backendUrl.toString(), {
        method: "GET",
        redirect: "manual", // 不自动跟随重定向，获取后端返回的重定向地址
      });

      // 获取后端返回的 Location（重定向目标：https://i-chingstudio.cc/auth/callback?token=xxx）
      const location = response.headers.get("location");

      if (location) {
        // 直接将后端的重定向响应返回给浏览器
        return new Response(null, {
          status: response.status,
          headers: {
            Location: location,
          },
        });
      }

      // 如果后端没有返回重定向，尝试从响应体中提取 token
      const text = await response.text();
      let frontendRedirectUrl;

      try {
        const data = JSON.parse(text);
        if (data.token) {
          const callbackUrl = new URL("/auth/callback", url.origin);
          callbackUrl.searchParams.set("token", data.token);
          frontendRedirectUrl = callbackUrl.toString();
        }
      } catch {
        // 响应体不是 JSON，忽略
      }

      if (frontendRedirectUrl) {
        return Response.redirect(frontendRedirectUrl, 302);
      }

      return new Response("OAuth callback failed: no redirect location", { status: 500 });
    } catch (err) {
      console.error("Worker error:", err);
      return new Response("OAuth callback error: " + err.message, { status: 500 });
    }
  },
};
