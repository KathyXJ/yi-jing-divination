"""临时脚本：修复产品表中的英文翻译字段"""
import asyncio
import aiosqlite
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data", "users.db")

PRODUCT_TRANSLATIONS = {
    "注册赠送": {
        "name_en": "Welcome Bonus",
        "description_en": "New users get 3 free credits, valid for 7 days",
    },
    "标准积分包": {
        "name_en": "Standard Pack",
        "description_en": "50 credits, forever valid",
    },
    "月度订阅": {
        "name_en": "Monthly Subscription",
        "description_en": "200 credits/month, auto-renewal",
    },
}

async def fix_translations():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for name, trans in PRODUCT_TRANSLATIONS.items():
            cursor = await db.execute(
                "SELECT id FROM products WHERE name = ?", (name,)
            )
            row = await cursor.fetchone()
            if row:
                await db.execute(
                    "UPDATE products SET name_en = ?, description_en = ? WHERE name = ?",
                    (trans["name_en"], trans["description_en"], name)
                )
                print(f"Updated: {name} -> {trans['name_en']}")
            else:
                print(f"Not found: {name}")
        await db.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(fix_translations())
