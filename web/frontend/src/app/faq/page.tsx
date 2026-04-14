"use client";

import { useState } from "react";
import { useLang } from "@/lib/i18n";
import styles from "./page.module.css";

interface FAQItem {
  q: string;
  a: string;
}

const faqData = {
  zh: [
    {
      q: "占卜是免费的吗？",
      a: "基础占卜（生成卦象）是免费的。只有 AI 智能解读需要消耗积分。注册即送 3 积分，可体验 1 次 AI 解读。",
    },
    {
      q: "积分会过期吗？",
      a: "积分包（一次性购买）的积分永久有效。订阅用户的每月额度在当月内有效，到期后自动续费。注册赠送的 3 积分有效期为 7 天。",
    },
    {
      q: "如何购买积分？",
      a: "登录后进入「定价」页面，选择适合您的积分包或订阅计划，通过 PayPal 完成支付。",
    },
    {
      q: "订阅可以随时取消吗？",
      a: "可以。随时取消订阅，取消后您仍可使用当月剩余额度，但不会续费。",
    },
    {
      q: "AI 解读消耗多少积分？",
      a: "每次 AI 智能解读消耗 3 积分。",
    },
    {
      q: "我的隐私安全吗？",
      a: "我们非常重视隐私。您使用 Google 账号登录，我们只获取您的邮箱信息，不会收集其他个人数据。所有支付由 PayPal 处理，我们不会存储您的支付信息。",
    },
    {
      q: "DeepSeek 是什么？",
      a: "DeepSeek 是一个先进的大语言模型，我们用它来生成专业、深刻的易经卦象解读，为您提供有价值的参考意见。",
    },
    {
      q: "占卜结果准确吗？",
      a: "易经占卜是一种传统文化，我们通过算法随机生成卦象。AI 解读能提供有参考价值的分析，但仅供参考娱乐，不作为人生重大决策的唯一依据。",
    },
  ],
  en: [
    {
      q: "Is divination free?",
      a: "Basic divination (generating hexagrams) is free. Only AI-powered interpretation requires credits. Sign up to get 3 free credits — enough for 1 AI interpretation.",
    },
    {
      q: "Do credits expire?",
      a: "One-time credit packs never expire. Monthly subscription credits are valid for that month only. New user bonus (3 credits) expires in 7 days.",
    },
    {
      q: "How do I buy credits?",
      a: "Log in and go to the Pricing page. Choose a credit pack or subscription plan and complete payment via PayPal.",
    },
    {
      q: "Can I cancel my subscription anytime?",
      a: "Yes. Cancel anytime — you'll keep your remaining monthly credits until the end of the billing period, and won't be charged again.",
    },
    {
      q: "How many credits does one AI interpretation cost?",
      a: "Each AI interpretation costs 3 credits.",
    },
    {
      q: "Is my privacy protected?",
      a: "We take privacy seriously. You sign in with Google — we only access your email address. All payments are processed by PayPal; we never store your payment details.",
    },
    {
      q: "What is DeepSeek?",
      a: "DeepSeek is a state-of-the-art large language model we use to generate professional, insightful I Ching interpretations.",
    },
    {
      q: "Are the divination results accurate?",
      a: "I Ching is a traditional Chinese practice. We generate hexagrams randomly through an algorithm. AI interpretation provides valuable reference, but is for entertainment only and should not be the sole basis for major life decisions.",
    },
  ],
};

export default function FAQPage() {
  const { lang } = useLang();
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  const faqs = faqData[lang] || faqData.zh;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>
          {lang === "zh" ? "常见问题" : "Frequently Asked Questions"}
        </h1>
        <p className={styles.subtitle}>
          {lang === "zh"
            ? "有问题？这里或许有答案。"
            : "Have questions? You might find answers here."}
        </p>
      </div>

      <div className={styles.faqList}>
        {faqs.map((faq, index) => (
          <div
            key={index}
            className={`${styles.faqItem} ${openIndex === index ? styles.open : ""}`}
          >
            <button
              className={styles.faqQuestion}
              onClick={() => setOpenIndex(openIndex === index ? null : index)}
            >
              <span>{faq.q}</span>
              <span className={styles.toggleIcon}>{openIndex === index ? "−" : "+"}</span>
            </button>
            {openIndex === index && (
              <div className={styles.faqAnswer}>
                <p>{faq.a}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className={styles.contact}>
        <p>
          {lang === "zh" ? "还有其他问题？" : "Still have questions?"}
          {" "}
          <a href="mailto:support@i-chingstudio.cc" className={styles.contactLink}>
            {lang === "zh" ? "联系我们" : "Contact us"}
          </a>
        </p>
      </div>
    </div>
  );
}
