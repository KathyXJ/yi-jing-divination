"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useLang } from "@/lib/i18n";
import styles from "./Navbar.module.css";

export default function Navbar() {
  const pathname = usePathname();
  const { user, isLoading, login, logout, token } = useAuth();
  const { lang, toggleLang } = useLang();

  const navLinks = [
    { href: "/", label: lang === "zh" ? "首页" : "Home" },
    { href: "/pricing", label: lang === "zh" ? "定价" : "Pricing" },
    { href: "/faq", label: lang === "zh" ? "常见问题" : "FAQ" },
  ];

  return (
    <nav className={styles.navbar}>
      <div className={styles.container}>
        {/* Logo */}
        <Link href="/" className={styles.logo}>
          <span className={styles.logoIcon}>☰</span>
          <span className={styles.logoText}>
            {lang === "zh" ? "周易占卜" : "I Ching"}
          </span>
        </Link>

        {/* Nav Links */}
        <div className={styles.navLinks}>
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`${styles.navLink} ${pathname === link.href ? styles.active : ""}`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Right side: Language toggle + Auth */}
        <div className={styles.rightSection}>
          {/* Language Toggle */}
          <button onClick={toggleLang} className={styles.langBtn}>
            {lang === "zh" ? "EN" : "中文"}
          </button>

          {/* User Area */}
          {!isLoading && (
            <>
              {user ? (
                <div className={styles.userArea}>
                  <Link href="/me" className={styles.userBtn}>
                    {user.name || user.email?.split("@")[0] || "我的账户"}
                  </Link>
                  <button onClick={logout} className={styles.logoutBtn}>
                    {lang === "zh" ? "退出" : "Logout"}
                  </button>
                </div>
              ) : (
                <button onClick={login} className={styles.loginBtn}>
                  {lang === "zh" ? "登录" : "Login"}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
