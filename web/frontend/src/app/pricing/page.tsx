"use client";

import { Suspense, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useLang } from "@/lib/i18n";
import { getProducts, type Product } from "@/lib/api";
import { useSearchParams, useRouter } from "next/navigation";
import styles from "./page.module.css";

function PaymentHandler({ onStatus }: { onStatus: (status: "success" | "cancelled" | "failed" | null, message: string) => void }) {
  const { user, token } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { lang } = useLang();

  useEffect(() => {
    const status = searchParams.get("payment");
    const tokenId = searchParams.get("token");
    
    if (status === "success" && tokenId && user && token) {
      handleCapture(tokenId);
    } else if (status === "cancelled") {
      onStatus("cancelled", lang === "zh" ? "支付已取消" : "Payment cancelled");
    }
  }, [searchParams, user, token]);

  async function handleCapture(orderId: string) {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/paypal/capture-order`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          order_id: orderId,
          user_id: user?.id,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Capture failed" }));
        throw new Error(err.detail || "Failed to capture order");
      }

      const result = await res.json();
      onStatus("success", lang === "zh" 
        ? `支付成功！已获得 ${result.credits_added} 积分`
        : `Payment successful! ${result.credits_added} credits added`
      );
      router.replace("/pricing");
    } catch (e: unknown) {
      onStatus("failed", e instanceof Error ? e.message : (lang === "zh" ? "支付失败" : "Payment failed"));
    }
  }

  return null;
}

export default function PricingPage() {
  const { user, token, isLoading } = useAuth();
  const { lang } = useLang();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState<number | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<"success" | "cancelled" | "failed" | null>(null);
  const [paymentMessage, setPaymentMessage] = useState("");

  useEffect(() => {
    getProducts()
      .then(setProducts)
      .catch(() => setError("Failed to load products"))
      .finally(() => setLoading(false));
  }, []);

  function handlePaymentStatus(status: "success" | "cancelled" | "failed" | null, message: string) {
    setPaymentStatus(status);
    setPaymentMessage(message);
  }

  async function handleBuy(product: Product) {
    if (!token || !user) return;
    setProcessing(product.id);
    setError("");
    
    // 根据产品积分确定 PayPal product_id
    // product.id: 1=免费(3积分), 2=$9.9(50积分), 3=$19.9(200积分/月)
    // PayPal: 50_credits=$9.9, monthly_200=$19.9
    let paypalProductId: string;
    if (product.credits === 50) {
      paypalProductId = "50_credits";
    } else if (product.credits === 200) {
      paypalProductId = "monthly_200";
    } else {
      setError(lang === "zh" ? "不支持的产品" : "Unsupported product");
      setProcessing(null);
      return;
    }
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/paypal/create-order`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          product_id: paypalProductId,
          user_id: user.id,
          lang: lang,
        }),
      });
      
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Create order failed" }));
        throw new Error(err.detail || "Failed to create order");
      }
      
      const order = await res.json();
      
      if (order.approval_url) {
        window.location.href = order.approval_url;
      } else {
        throw new Error("No approval URL received");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Purchase failed");
    } finally {
      setProcessing(null);
    }
  }

  const t = {
    title: lang === "zh" ? "选择适合您的方案" : "Choose Your Plan",
    subtitle: lang === "zh"
      ? "注册即送3免费积分，体验AI解卦的魅力"
      : "Sign up and get 3 free credits to experience AI-powered divination",
    perMonth: lang === "zh" ? "/月" : "/month",
    buy: lang === "zh" ? "立即购买" : "Buy Now",
    credits: lang === "zh" ? "积分" : "credits",
    popular: lang === "zh" ? "最受欢迎" : "Most Popular",
    bestValue: lang === "zh" ? "最佳选择" : "Best Value",
    getStarted: lang === "zh" ? "开始体验" : "Get Started",
    needMore: lang === "zh" ? "需要更多？" : "Need more?",
    contactUs: lang === "zh" ? "联系我们" : "Contact us",
  };

  if (isLoading || loading) {
    return <div className={styles.container}><div className={styles.loading}>{lang === "zh" ? "加载中..." : "Loading..."}</div></div>;
  }

  return (
    <div className={styles.container}>
      <Suspense fallback={null}>
        <PaymentHandler onStatus={handlePaymentStatus} />
      </Suspense>

      <div className={styles.header}>
        <h1 className={styles.title}>{t.title}</h1>
        <p className={styles.subtitle}>{t.subtitle}</p>
      </div>

      {paymentStatus && (
        <div className={`${styles.paymentMessage} ${styles[paymentStatus]}`}>
          {paymentMessage}
        </div>
      )}

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
                </div>
              </div>

              <div className={styles.cardBody}>
                <div className={styles.desc}>
                  {lang === "zh" ? product.description : (product.description_en || product.description)}
                </div>
              </div>

              <div className={styles.cardFooter}>
                {!user ? (
                  <span className={styles.ctaBtn}>{t.getStarted}</span>
                ) : product.price_cents === 0 ? (
                  <span className={styles.freeNote}>
                    {lang === "zh" ? "注册时已获得" : "Granted on registration"}
                  </span>
                ) : processing !== null ? (
                  <span className={styles.ctaBtn}>
                    {processing === product.id
                      ? (lang === "zh" ? "跳转中..." : "Redirecting...")
                      : t.buy}
                  </span>
                ) : (
                  <button
                    onClick={() => handleBuy(product)}
                    className={styles.ctaBtn}
                  >
                    {t.buy}
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
