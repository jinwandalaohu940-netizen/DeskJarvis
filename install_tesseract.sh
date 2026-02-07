#!/bin/bash
# Tesseract OCR 安装脚本

echo "🔧 开始安装 Tesseract OCR..."

# 1. 修复 Homebrew 权限（如果需要）
echo "📝 步骤 1: 检查并修复 Homebrew 权限..."
if [ ! -w "/usr/local/Cellar" ]; then
    echo "⚠️  需要管理员权限来修复 Homebrew 目录权限"
    echo "请执行以下命令（需要输入密码）："
    echo ""
    echo "sudo chown -R $(whoami) /Users/$(whoami)/Library/Logs/Homebrew /usr/local/Cellar /usr/local/Frameworks /usr/local/Homebrew /usr/local/bin /usr/local/etc /usr/local/etc/bash_completion.d /usr/local/include /usr/local/lib /usr/local/lib/pkgconfig /usr/local/opt /usr/local/sbin /usr/local/share /usr/local/share/aclocal /usr/local/share/doc /usr/local/share/info /usr/local/share/locale /usr/local/share/man /usr/local/share/man/man1 /usr/local/share/man/man3 /usr/local/share/man/man5 /usr/local/share/man/man7 /usr/local/share/man/man8 /usr/local/share/zsh /usr/local/share/zsh/site-functions /usr/local/var/homebrew/linked /usr/local/var/homebrew/locks"
    echo ""
    read -p "是否已执行上述命令？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 请先修复权限后再运行此脚本"
        exit 1
    fi
fi

# 2. 安装 Tesseract
echo "📦 步骤 2: 安装 Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract 已安装: $(tesseract --version | head -n 1)"
else
    echo "正在安装 Tesseract..."
    brew install tesseract
    
    if [ $? -eq 0 ]; then
        echo "✅ Tesseract 安装成功"
        tesseract --version | head -n 1
    else
        echo "❌ Tesseract 安装失败"
        exit 1
    fi
fi

# 3. 安装中文语言包（强烈推荐，用于中文文本识别）
echo "📚 步骤 3: 安装中文语言包（chi_sim）..."
if brew list tesseract-lang &> /dev/null; then
    echo "✅ 中文语言包已安装"
else
    echo "正在安装中文语言包..."
    brew install tesseract-lang
    
    if [ $? -eq 0 ]; then
        echo "✅ 中文语言包安装成功"
    else
        echo "⚠️  中文语言包安装失败，但 Tesseract 仍可使用（仅支持英文）"
    fi
fi

# 4. 验证安装
echo "✅ 验证安装..."
tesseract --version
echo ""
echo "🎉 Tesseract OCR 安装完成！"
echo ""
echo "📝 已安装的语言包："
tesseract --list-langs
