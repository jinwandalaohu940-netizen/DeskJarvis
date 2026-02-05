#!/bin/bash

# DeskJarvis Tauri应用启动脚本

set -e

echo "🚀 启动 DeskJarvis Tauri应用..."
echo ""

# 加载Rust环境
if [ -f "$HOME/.cargo/env" ]; then
    source "$HOME/.cargo/env"
    echo "✅ Rust环境已加载"
else
    echo "❌ 错误: 找不到Rust环境，请先安装Rust"
    exit 1
fi

# 检查Rust
if ! command -v cargo &> /dev/null; then
    echo "❌ 错误: Cargo未找到，请检查Rust安装"
    exit 1
fi

echo "✅ Cargo版本: $(cargo --version)"
echo ""

# 检查Node.js
if ! command -v npm &> /dev/null; then
    echo "❌ 错误: npm未找到，请先安装Node.js"
    exit 1
fi

echo "✅ Node.js版本: $(node --version)"
echo "✅ npm版本: $(npm --version)"
echo ""

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装npm依赖..."
    npm install
fi

# 停止可能占用的端口
if lsof -ti:1420 &> /dev/null; then
    echo "🛑 停止占用1420端口的进程..."
    lsof -ti:1420 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo ""
echo "🔨 开始编译和启动Tauri应用..."
echo "⏳ 首次编译可能需要3-5分钟，请耐心等待..."
echo "📝 编译完成后，应用窗口会自动打开"
echo ""

# 启动Tauri应用
npm run tauri:dev
