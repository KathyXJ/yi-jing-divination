"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useLang } from "@/lib/i18n";
import { getProducts, type Product } from "@/lib/api";
import Link from "next/link";
import styles from "./page.module.css";

export default function PricingPage() {
  const { user, token, isLoading } = useAuth();
  const { lang } = useLang();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState<number | null>(null);

  useEffect(() => {
    getProducts()
      .then(setProducts)
      .catch(() => setError("Failed to load products"))
      .finally(() => setLoading(false));
  }, []);

  async function handleBuy(productId: number) {
    if (!token) return;
    setProcessing(productId);
    try {
      // TODO: 后续接入 PayPal SDK，这里先创建订单获取信息
      const order = await createOrder(token, productId);
      alert(`Order #${order.order_id} created! Amount: $${(order.amount_cents / 100).toFixed(2)} — PayPal integration coming soon!`);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Purchase failed");
    } finally {
      setProcessing(null);
    }
  }

  const t = {
    title: lang === "zh" ? "选择适合您的方案" : "Choose Your Plan",
    subtitle: lang === "zh"
      ? "注册即送3免费积分，体验AI解卦的魅力"
      : "Sign up and get 3 free credits to experience AI-powered divination",
    permanent: lang === "zh" ? "永久有效" : "Forever valid",
    perMonth: lang === "zh" ? "/月" : "/month",
    buy: lang === "zh" ? "立即购买" : "Buy Now",
    currentBalance: lang === "zh" ? "当前余额" : "Current balance",
    credits: lang === "zh" ? "积分" : "credits",
    features: {
      aiInterpretation: lang === "zh" ? "AI智能解卦" : "AI Interpretation",
      forever: lang === "zh" ? "永久有效" : "Forever valid",
      monthly: lang === "zh" ? "每月补充" : "Monthly renewal",
      support: lang === "zh" ? "邮件支持" : "Email Support",
    },
    popular: lang === "zh" ? "最受欢迎" : "Most Popular",
    bestValue: lang === "zh" ? "最佳选择" : "Best Value",
    getStarted: lang === "zh" ? "开始体验" : "Get Started",
    loginToBuy: lang === "zh" ? "登录后购买" : "Login to buy",
    needMore: lang === "zh" ? "需要更多？" : "Need more?",
    contactUs: lang === "zh" ? "联系我们" : "Contact us",
  };

  if (isLoading || loading) {
    return <div className={styles.container}><div className={styles.loading}>{lang === "zh" ? "加载中..." : "Loading..."}</div></div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>{t.title}</h1>
        <p className={styles.subtitle}>{t.subtitle}</p>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.pricingGrid}>
        {products.map((product) => {
          const isSubscription = product.type === "subscription";
          const isFree = product.type === "free";
          const isPopular = product.type === "one_time" && product.credits >= 50;
          const isBestValue = product.type === "subscription";

          return (
            <div
              key={product.id}
              className={`${styles.card} ${isPopular ? styles.popular : ""} ${isBestValue ? styles.bestValue : ""}`}
            >
              {(isPopular || isBestValue) && (
                <div className={styles.badge}>
                  {isPopular ? t.popular : t.bestValue}
                </div>
              )}

              <div className={styles.cardHeader}>
                <div className={styles.productName}>
                  {lang === "zh" ? product.name : product.name_en}
                </div>
                <div className={styles.price}>
                  {product.price_cents === 0 ? (
                    <span className={styles.free}>{lang === "zh" ? "免费" : "Free"}</span>
                  ) : (
                    <>
                      <span className={styles.currency}>$</span>
                      <span className={styles.amount}>{(product.price_cents / 100).toFixed(2).replace(/\.?0+$/, '')}</span>
                      {isSubscription && <span className={styles.period}>{t.perMonth}</span>}
                    </>
                  )}
                </div>
                <div className={styles.creditsInfo}>
                  <span className={styles.creditsNum}>{product.credits}</span>
                  <span className={styles.creditsUnit}> {t.credits}</span>
                  <span className={styles.validity}>
                    {!isSubscription && (
                      product.valid_days
                        ? (lang === "zh" ? ` · ${product.valid_days}天内有效` : ` · Valid for ${product.valid_days} days`)
                        : ` · ${t.permanent}`
                    )}
                    {isSubscription && ` · ${t.features.monthly}`}
                  </span>
                </div>
              </div>

              <div className={styles.cardBody}>
                <div className={styles.desc}>
                  {lang === "zh" ? product.description : (product.description_en || product.description)}
                </div>
              </div>

              <div className={styles.cardFooter}>
                {!user ? (
                  <Link href="/" className={styles.ctaBtn}>
                    {t.getStarted}
                  </Link>
                ) : product.price_cents === 0 ? (
                  <span className={styles.freeNote}>
                    {lang === "zh" ? "注册时已获得" : "Granted on registration"}
                  </span>
                ) : (
                  <button
                    onClick={() => handleBuy(product.id)}
                    disabled={processing === product.id}
                    className={styles.ctaBtn}
                  >
                    {processing === product.id
                      ? (lang === "zh" ? "处理中..." : "Processing...")
                      : t.buy}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className={styles.footer}>
        <p>{t.needMore} <a href="mailto:support@i-chingstudio.cc" className={styles.contactLink}>{t.contactUs}</a></p>
      </div>
    </div>
  );
}

// Import createOrder here - it's from api.ts
import { createOrder } from "@/lib/api";
