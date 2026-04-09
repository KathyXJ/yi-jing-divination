#!/usr/bin/env node
/**
 * 轻量代理服务器
 * 将 /api/* 请求转发到后端 localhost:8000，超时时间 5 分钟
 */
const http = require("http");
const { URL } = require("url");

const TARGET_HOST = "127.0.0.1";
const TARGET_PORT = 8000;
const LISTEN_PORT = 3000;
const TIMEOUT_MS = 5 * 60 * 1000; // 5 分钟

const server = http.createServer(async (req, res) => {
  if (!req.url.startsWith("/api/")) {
    res.writeHead(404);
    res.end("Not found");
    return;
  }

  const target = `http://${TARGET_HOST}:${TARGET_PORT}${req.url}`;
  console.log(`[proxy] ${req.method} ${req.url} -> ${target}`);

  const options = {
    method: req.method,
    headers: {
      "Content-Type": "application/json",
      ...req.headers,
    },
    hostname: TARGET_HOST,
    port: TARGET_PORT,
    path: req.url,
  };

  try {
    const proxyReq = http.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });

    proxyReq.on("error", (err) => {
      console.error(`[proxy] request error: ${err.message}`);
      res.writeHead(502, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "后端无响应" }));
    });

    proxyReq.on("timeout", () => {
      console.error(`[proxy] timeout after ${TIMEOUT_MS}ms`);
      proxyReq.destroy();
      res.writeHead(504, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "请求超时" }));
    });

    proxyReq.setTimeout(TIMEOUT_MS);
    req.pipe(proxyReq);
  } catch (err) {
    console.error(`[proxy] error: ${err.message}`);
    res.writeHead(500);
    res.end();
  }
});

server.listen(LISTEN_PORT, "0.0.0.0", () => {
  console.log(`[proxy] Listening on 0.0.0.0:${LISTEN_PORT}`);
});
