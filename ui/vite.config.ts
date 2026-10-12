import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/projects": "http://127.0.0.1:8000",
      "/settings": {
        target: "http://127.0.0.1:8000",
        bypass(req) {
          if (req.headers.accept?.includes("text/html")) return "/index.html";
        },
      },
      "/media": "http://127.0.0.1:8000",
      "/browse": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
