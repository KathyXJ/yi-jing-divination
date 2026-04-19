"use client";

import { useState, useEffect } from "react";
import { getCreditsTransactions, type Transaction } from "@/lib/api";
import { useLang, TXT } from "@/lib/i18n";
import { useAuth } from "@/lib/auth";
import Link from "next/link";
import styles from "../page.module.css";

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const { lang } = useLang();
  const { token } = useAuth();
  const t = TXT[lang];

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    
    const userToken = token; // TypeScript now knows this is string
    
    async function fetchTransactions() {
      try {
        const data = await getCreditsTransactions(userToken, 100);
        setTransactions(data);
      } catch (e) {
        console.error("Failed to fetch transactions:", e);
      } finally {
        setLoading(false);
      }
    }
    fetchTransactions();
  }, [token]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(lang === "zh" ? "zh-CN" : "en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getTypeName = (type: string) => {
    const names: Record<string, string> = {
      grant: lang === "zh" ? "赠送" : "Grant",
      deduct: lang === "zh" ? "消耗" : "Deduct",
      purchase: lang === "zh" ? "购买" : "Purchase",
      refund: lang === "zh" ? "退款" : "Refund",
    };
    return names[type] || type;
  };

  const getAmountDisplay = (amount: number) => {
    if (amount > 0) {
      return `+${amount}`;
    }
    return `${amount}`;
  };

  return (
    <main className={styles.container}>
      <header className={styles.header}>
        <Link href="/me" className={styles.backLink}>
          ← {lang === "zh" ? "返回账户中心" : "Back to Account"}
        </Link>
        <h1 className={styles.title}>
          {lang === "zh" ? "积分使用明细" : "Transaction History"}
        </h1>
      </header>

      <div className={styles.card}>
        {loading ? (
          <div className={styles.loading}>
            {lang === "zh" ? "加载中..." : "Loading..."}
          </div>
        ) : transactions.length === 0 ? (
          <div className={styles.empty}>
            {lang === "zh" ? "暂无记录" : "No transactions yet"}
          </div>
        ) : (
          <div className={styles.transactionList}>
            {transactions.map((tx) => (
              <div key={tx.id} className={styles.transactionItem}>
                <div className={styles.txInfo}>
                  <span className={styles.txType}>{getTypeName(tx.type)}</span>
                  {tx.description && (
                    <span className={styles.txDesc}>{tx.description}</span>
                  )}
                  <span className={styles.txDate}>{formatDate(tx.created_at)}</span>
                </div>
                <div className={styles.txAmount}>
                  <span className={tx.amount > 0 ? styles.positive : styles.negative}>
                    {getAmountDisplay(tx.amount)}
                  </span>
                  <span className={styles.balanceAfter}>
                    {lang === "zh" ? "余额" : "Balance"}: {tx.balance_after}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
