import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const backendUrl = API_BASE_URL
      ? `${API_BASE_URL}/api/ai/interpret`
      : `http://127.0.0.1:8000/api/ai/interpret`;

    const response = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(600 * 1000), // 600s timeout for AI interpret
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    console.error("[/api/ai/interpret] Error:", error.message);
    return NextResponse.json(
      { detail: error.message || "后端请求失败" },
      { status: 500 }
    );
  }
}
