"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useLang } from "@/lib/i18n";
import { getCreditsBalance, getCreditsTransactions, type BalanceInfo, type Transaction } from "@/lib/api";
import Link from "next/link";
import styles from "./page.module.css";

export default function MePage() {
  const { user, token, isLoading } = useAuth();
  const { lang } = useLang();
  const [balance, setBalance] = useState<BalanceInfo | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    loadData();
  }, [token]);

  async function loadData() {
    if (!token) return;
    setLoading(true);
    try {
      const [bal, txs] = await Promise.all([
        getCreditsBalance(token),
        getCreditsTransactions(token, 20),
      ]);
      setBalance(bal);
      setTransactions(txs);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }

  if (isLoading || loading) {
    return <div className={styles.container}><div className={styles.loading}>{lang === "zh" ? "加载中..." : "Loading..."}</div></div>;
  }

  if (!user || !token) {
    return (
      <div className={styles.container}>
        <div className={styles.notLoggedIn}>
          <h2>{lang === "zh" ? "请先登录" : "Please login first"}</h2>
          <p>{lang === "zh" ? "登录后查看您的账户信息" : "Login to view your account"}</p>
        </div>
      </div>
    );
  }

  const t = {
    credits: lang === "zh" ? "积分余额" : "Credits Balance",
    subscription: lang === "zh" ? "订阅状态" : "Subscription",
    active: lang === "zh" ? "激活中" : "Active",
    inactive: lang === "zh" ? "未订阅" : "Inactive",
    expiresAt: lang === "zh" ? "到期时间" : "Expires at",
    permanent: lang === "zh" ? "永久有效" : "Permanent",
    remainingDays: lang === "zh" ? "剩余天数" : "days left",
    transactionHistory: lang === "zh" ? "积分记录" : "Transaction History",
    noTransactions: lang === "zh" ? "暂无记录" : "No transactions yet",
    recharge: lang === "zh" ? "充值积分" : "Buy Credits",
    buyPackage: lang === "zh" ? "购买积分包" : "Buy Package",
    subscribe: lang === "zh" ? "订阅会员" : "Subscribe",
    accountInfo: lang === "zh" ? "账户信息" : "Account Info",
    email: "Email",
    name: lang === "zh" ? "昵称" : "Name",
    memberSince: lang === "zh" ? "注册时间" : "Member since",
    recentTransactions: lang === "zh" ? "最近积分变动" : "Recent Transactions",
    viewAll: lang === "zh" ? "查看全部" : "View All",
  };

  return (
    <div className={styles.container}>
      <h1 className={styles.pageTitle}>{lang === "zh" ? "个人中心" : "My Account"}</h1>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.grid}>
        {/* Credits Card */}
        <div className={styles.card}>
          <div className={styles.creditsDisplay}>
            <div className={styles.creditsNumber}>{balance?.credits ?? 0}</div>
            <div className={styles.creditsLabel}>{lang === "zh" ? "可用积分" : "Available Credits"}</div>
          </div>
          <div className={styles.cardActions}>
            <Link href="/pricing" className={styles.primaryBtn}>
              {t.buyPackage}
            </Link>
          </div>
        </div>

        {/* Subscription Card */}
        <div className={styles.card}>
          <div className={styles.subscriptionSection}>
            <div className={styles.subLabel}>{t.subscription}</div>
            {(balance?.is_subscription_active || balance?.has_permanent_credits) && (
              <div className={`${styles.subBadge} ${styles.active}`}>
                {t.active}
              </div>
            )}
            {!balance?.is_subscription_active && !balance?.has_permanent_credits && (
              <div className={`${styles.subBadge} ${styles.inactive}`}>
                {t.inactive}
              </div>
            )}
          </div>
          
          {/* 订阅详情 */}
          {balance?.is_subscription_active && (
            <div className={styles.subDetails}>
              <div className={styles.subName}>
                {lang === "zh" ? balance.subscription_name : balance.subscription_name_en}
              </div>
              <div className={styles.subExpiry}>
                {balance.subscription_remaining_days !== null 
                  ? `${balance.subscription_remaining_days} ${t.remainingDays}`
                  : balance.subscription_expires_at 
                    ? `${t.expiresAt}: ${new Date(balance.subscription_expires_at).toLocaleDateString()}`
                    : ""
                }
              </div>
            </div>
          )}
          
          {/* 永久积分包 */}
          {balance?.has_permanent_credits && (
            <div className={styles.subDetails}>
              <div className={styles.subName}>
                {lang === "zh" ? "标准积分包" : "Standard Pack"}
              </div>
              <div className={styles.subPermanent}>
                {t.permanent}
              </div>
            </div>
          )}
          
          {!balance?.is_subscription_active && !balance?.has_permanent_credits && (
            <div className={styles.cardActions}>
              <Link href="/pricing" className={styles.secondaryBtn}>
                {t.subscribe}
              </Link>
            </div>
          )}
        </div>

        {/* Account Info Card */}
        <div className={styles.card}>
          <div className={styles.cardTitle}>{t.accountInfo}</div>
          <div className={styles.accountInfo}>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>{t.email}</span>
              <span className={styles.infoValue}>{user.email}</span>
            </div>
            {user.name && (
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>{t.name}</span>
                <span className={styles.infoValue}>{user.name}</span>
              </div>
            )}
          </div>
        </div>

        {/* Transaction History Card */}
        <div className={`${styles.card} ${styles.txCard}`}>
          <div className={styles.cardTitle}>{t.recentTransactions}</div>
          {transactions.length === 0 ? (
            <div className={styles.empty}>{t.noTransactions}</div>
          ) : (
            <div className={styles.txList}>
              {transactions.slice(0, 5).map((tx) => (
                <div key={tx.id} className={styles.txItem}>
                  <div className={styles.txLeft}>
                    <span className={`${styles.txAmount} ${tx.amount > 0 ? styles.positive : styles.negative}`}>
                      {tx.amount > 0 ? "+" : ""}{tx.amount}
                    </span>
                    <span className={styles.txDesc}>
                      {lang === "zh" ? (tx.description || tx.type) :
                        (tx.description?.replace("AI解读消耗", "AI Interpretation")
                          .replace("注册赠送3积分（7天有效）", "Welcome Bonus (3 credits, 7 days)")
                          .replace("AI解读消耗积分（订阅额度）", "AI Interpretation (subscription)")
                          .replace("购买积分包", "Purchased credits")
                          .replace("月度订阅", "Monthly subscription")
                          || tx.type)}
                    </span>
                  </div>
                  <span className={styles.txDate}>
                    {new Date(tx.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          )}
          {transactions.length > 5 && (
            <Link href="/me/transactions" className={styles.viewAllLink}>
              {t.viewAll} →
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
