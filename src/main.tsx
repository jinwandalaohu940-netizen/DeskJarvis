import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

console.log("[main.tsx] 开始渲染应用");

const rootElement = document.getElementById("root");
if (!rootElement) {
  console.error("[main.tsx] 找不到 root 元素！");
} else {
  console.log("[main.tsx] 找到 root 元素，开始渲染");
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
  console.log("[main.tsx] 渲染完成");
}
