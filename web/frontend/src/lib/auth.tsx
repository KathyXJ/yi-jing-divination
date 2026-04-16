"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface User {
  id: number;
  email: string;
  name: string | null;
  avatar_url: string | null;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  token: null,
  isLoading: true,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 初始化时检查 localStorage 中的 token
  useEffect(() => {
    const storedToken = localStorage.getItem("auth_token");
    if (storedToken) {
      setToken(storedToken);
      fetchUserInfo(storedToken);
    } else {
      setIsLoading(false);
    }

    // 监听 auth_token_set 事件（登录回调时触发）
    function onTokenSet(e: Event) {
      const { token } = (e as CustomEvent).detail;
      setToken(token);
      fetchUserInfo(token);
    }
    window.addEventListener("auth_token_set", onTokenSet);
    return () => window.removeEventListener("auth_token_set", onTokenSet);
  }, []);

  async function fetchUserInfo(t: string) {
    try {
      const res = await fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) {
        const userData = await res.json();
        setUser(userData);
      } else {
        // token 无效，清除
        localStorage.removeItem("auth_token");
        setToken(null);
      }
    } catch {
      localStorage.removeItem("auth_token");
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }

  function login() {
    // 跳转到后端 Google OAuth 登录页面
    window.location.href = `${API_URL}/auth/google`;
  }

  function logout() {
    localStorage.removeItem("auth_token");
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

// 解析 callback URL 中的 token，并通知 AuthProvider
// Returns the token if found, null otherwise
export function handleAuthCallback(): string | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (token) {
    localStorage.setItem("auth_token", token);
    // 清除 URL 中的 token 参数
    window.history.replaceState({}, document.title, window.location.pathname);
    // 通知 AuthProvider 有新 token
    window.dispatchEvent(new CustomEvent("auth_token_set", { detail: { token } }));
  }
  return token;
}
