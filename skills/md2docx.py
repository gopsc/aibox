#!/usr/bin/env python3
"""
md2docx - 输出 Pandoc Markdown 转 Word 命令使用手册
"""

import sys

MANUAL = """
╔══════════════════════════════════════════════════════════════╗
║          Pandoc 命令使用手册（Markdown → Word 篇）           ║
╚══════════════════════════════════════════════════════════════╝

📌 概述
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
pandoc 是一个强大的通用文档格式转换工具，由 John MacFarlane 开发。
本手册聚焦于将 Markdown 文件转换为 Word (.docx) 文档的常用用法。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 基本命令格式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    pandoc 输入文件.md -o 输出文件.docx

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 核心参数详解
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  -o, --output FILE        指定输出 Word 文档路径
  --reference-doc FILE     使用样式参考模板（控制输出样式）
  --metadata KEY=VAL       设置文档元数据（如 title="标题"）
  --toc                    启用自动目录
  --toc-depth=N            设置目录层级深度（默认 3）
  -f, --from FORMAT        指定输入格式（如 markdown）
  -t, --to FORMAT          指定输出格式（如 docx）
  --resource-path PATH     指定图片等资源搜索路径
  --wrap=MODE              设置换行模式（preserve/auto/none）
  -V, --variable KEY=VAL   设置模板变量

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 常用示例
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  基本转换
    pandoc README.md -o README.docx

2️⃣  指定输出文件名
    pandoc 文档.md -o 项目报告.docx

3️⃣  使用样式模板
    pandoc 文档.md -o 报告.docx --reference-doc 模板.docx

4️⃣  添加标题 + 自动目录
    pandoc 文档.md -o 报告.docx --metadata title="项目报告" --toc

5️⃣  自定义目录深度（2级）
    pandoc 文档.md -o 报告.docx --toc --toc-depth=2

6️⃣  从管道输入
    echo "# Hello" | pandoc -o output.docx

7️⃣  批量转换所有 .md 文件
    for f in *.md; do pandoc "$f" -o "${{f%.md}}.docx"; done

8️⃣  带图片的文档
    pandoc 文档.md -o 文档.docx --resource-path=./images

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎨 样式模板制作技巧
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

导出一个默认参考模板，用 Word 修改样式后复用：

    pandoc -o custom-reference.docx \\
        --print-default-data-file reference.docx

修改完成后，用 --reference-doc 引用即可控制输出样式。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📥 安装 pandoc
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Debian/Ubuntu:  sudo apt-get install -y pandoc
  macOS:          brew install pandoc
  Windows:        winget install pandoc

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 常见问题
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ❓ 中文乱码？   → 安装中文字体：sudo apt-get install fonts-wqy-microhei
  ❓ 目录不生效？ → 确保 Markdown 标题级别正确（# 一级、## 二级）
  ❓ 图片不显示？ → 使用 --resource-path 指定图片所在目录
  ❓ 模板无效？   → 确认模板是用 Word 修改样式后的 .docx 文件

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 更多信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Pandoc 官方文档:  https://pandoc.org/MANUAL.html
  运行 pandoc --help 查看所有参数
"""


def main():
    # 检查参数
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("-h", "--help"):
            print(__doc__.strip())
            print("\n运行本脚本（不带参数）即可输出 Pandoc 命令使用手册。")
            sys.exit(0)
        elif arg in ("-v", "--version"):
            print("md2docx v1.0.0 (Pandoc 命令手册版)")
            sys.exit(0)
        else:
            print(f"未知参数: {arg}")
            print("使用 --help 查看帮助")
            sys.exit(1)

    # 输出手册
    print(MANUAL)


if __name__ == "__main__":
    main()
