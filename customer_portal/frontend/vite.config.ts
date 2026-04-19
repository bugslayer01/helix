import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    host: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        timeout: 60_000,
        proxyTimeout: 60_000,
        configure: (proxy) => {
          proxy.on("error", (err, _req, res) => {
            const code = (err as any).code || err.message;
            const body = JSON.stringify({
              detail: {
                error: {
                  code: "backend_unreachable",
                  message: `LenderCo backend not reachable (${code}). Restart \`make dev\` or check :8001 is up.`,
                },
              },
            });
            try {
              (res as any).writeHead(502, { "Content-Type": "application/json" });
              (res as any).end(body);
            } catch { /* socket may already be closed */ }
          });
        },
      },
    },
  },
});
