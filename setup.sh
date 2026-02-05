#!/bin/bash

# DeskJarvis 快速设置脚本

set -e

echo "🚀 DeskJarvis 项目设置"
echo "===================="
echo ""

# 检查Python版本
echo "📋 检查Python版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查是否满足Python 3.11+
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "❌ 错误: 需要Python 3.11或更高版本"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo ""
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装Python依赖
echo ""
echo "📥 安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 安装Playwright浏览器
echo ""
echo "🌐 安装Playwright浏览器..."
playwright install chromium

# 创建配置目录
echo ""
echo "📁 创建配置目录..."
mkdir -p ~/.deskjarvis/sandbox
mkdir -p ~/.deskjarvis/logs

# 提示设置API密钥
echo ""
echo "✅ 设置完成！"
echo ""
echo "📝 下一步："
echo "1. 编辑配置文件: ~/.deskjarvis/config.json"
echo "2. 设置你的Claude API密钥"
echo "3. 运行测试: python agent/main.py '测试指令'"
echo ""
echo "💡 提示: 配置文件会在首次运行时自动创建"
