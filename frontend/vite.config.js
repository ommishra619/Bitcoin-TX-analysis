import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        priceDashboard: resolve(__dirname, "price-dashboard.html"),
        txAlert: resolve(__dirname, "tx-alert.html")
      }
    }
  }
});
