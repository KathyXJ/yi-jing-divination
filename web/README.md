# 周易占卜 · AI 智能解卦

融合千年《周易》智慧与 DeepSeek 深度思考模型的智能占卜网站。

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Next.js 15 + TypeScript + Tailwind CSS v4 |
| 后端 | Python FastAPI |
| AI | DeepSeek DeepThink (deepseek-reasoner) |
| 部署 | 腾讯云服务器 |

## 项目结构

```
web/
├── frontend/          # Next.js 前端
│   ├── src/
│   │   ├── app/          # App Router 页面
│   │   │   ├── page.tsx      # 主页面（占卜流程）
│   │   │   ├── layout.tsx    # 根布局
│   │   │   └── globals.css   # 全局样式（深色+金色主题）
│   │   ├── components/
│   │   │   ├── CoinCaster.tsx      # 投币动画组件
│   │   │   ├── GuaDisplay.tsx       # 卦象展示组件
│   │   │   └── InterpretationPanel.tsx  # AI 解读面板
│   │   └── lib/
│   │       └── api.ts           # API 调用封装
│   └── package.json
│
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── divination.py      # 占卜核心算法
│   │   ├── data_loader.py     # 周易数据加载
│   │   └── routers/
│   │       ├── divination.py  # 占卜 API 路由
│   │       └── ai.py          # AI 解读路由
│   ├── data/             # 周易原始数据（来自 GitHub）
│   └── requirements.txt
│
└── README.md
```

## 快速启动

### 后端

```bash
cd backend
pip3 install fastapi uvicorn pydantic openai python-dotenv --break-system-packages

# 配置 DeepSeek API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=你的密钥

# 启动
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

## 功能说明

1. **自动占卜**：模拟掷三枚硬币 × 6次，生成64卦中的任一卦
2. **卦象展示**：显示本卦、之卦、卦辞、变爻爻辞
3. **AI 智能解卦**：接入 DeepSeek 深度思考模型，结合卦象和用户问题进行解读

## 视觉风格

- 深色神秘感背景（#0a0a0f）
- 金色点缀（#d4a843）
- 古风与现代融合的 UI 设计
