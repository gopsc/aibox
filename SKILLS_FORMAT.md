# Aibox 扩展技能格式规范

本文档定义扩展技能的文件结构、接口约定和编写规范，供开发者与 AI 智能体参考。

## 概览

技能存放于 `~/.aibox/skills/` 目录，系统启动时自动扫描加载，运行时可通过 `reload_skills` 热重载。技能分为两种类型：

| 类型 | 识别方式 | 用途 |
|------|---------|------|
| 可执行技能 | 非 `.md` 文件，具有可执行权限 | 命令行工具，通过 `run_command` 调用 |
| Markdown 技能 | 以 `.md` 结尾 | 知识文档，AI 直接阅读并遵循 |

文件名仅允许字母、数字、下划线 `_` 和连字符 `-`，以 `_` 或 `.` 开头的文件会被忽略。

---

## 可执行技能

可执行技能是标准的命令行程序，系统仅依赖一个接口约定：**必须支持 `--help` 参数**。系统通过执行 `<skill> --help` 获取技能摘要和使用说明，不需要实现 `--description`、`--parameters`、`--execute` 等额外接口。

### 接口约定

系统按以下规则提取技能信息：

1. 执行 `<skill_path> --help`，超时上限 10 秒
2. 取 stdout 的第一个非空行作为**摘要**（若 stdout 为空则回退到 stderr）
3. 完整的 `--help` 输出作为技能**内容**，供 `search_skills` 展示

因此，`--help` 输出的第一行必须是一句简洁的功能描述，后续内容是完整的参数说明和使用示例。

### Python 技能模板

```python
#!/usr/bin/env python3
"""
技能模块内部说明（可选，不影响系统识别）
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="一句话功能摘要 —— 这是 --help 的第一行输出",
        epilog="""
参数说明:
  -x, --xxx    参数含义说明
  -y, --yyy    另一个参数说明

使用示例:
  my_skill -x value           # 基本用法
  my_skill -x value -y 10    # 组合用法
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-x", "--xxx", type=str, required=True, help="参数说明")
    parser.add_argument("-y", "--yyy", type=int, default=10, help="参数说明 (默认 10)")

    args = parser.parse_args()

    # --- 业务逻辑 ---
    print(f"执行结果: xxx={args.xxx}, yyy={args.yyy}")


if __name__ == "__main__":
    main()
```

### 关键要素

**Shebang 行**：Python 脚本使用 `#!/usr/bin/env python3`，Shell 脚本使用 `#!/bin/bash`。

**argparse `description`**：这是系统识别的技能摘要，必须是一句话，精准概括技能功能。它直接决定 AI 能否在 `search_skills` 时正确匹配到这个技能。

**argparse `epilog`**：包含两部分内容——参数说明和使用示例。使用 `RawDescriptionHelpFormatter` 保持排版原样输出。

**错误处理**：向 stderr 输出错误信息，以非零退出码退出。正常结果输出到 stdout。

```python
# 正确做法
print("错误: 参数无效", file=sys.stderr)
sys.exit(1)

# 避免
print("错误: 参数无效")  # 会混入 stdout，污染正常输出
```

**退出码约定**：

| 退出码 | 含义 |
|--------|------|
| 0 | 执行成功 |
| 1 | 参数错误或一般性失败 |
| 其他 | 自定义错误码 |

### Shell 技能模板

```bash
#!/bin/bash
# 用法通过 --help 输出

if [ "$1" = "--help" ]; then
    echo "一句话功能摘要"
    echo ""
    echo "用法: my_skill [选项]"
    echo ""
    echo "选项:"
    echo "  -n NAME    指定名称"
    echo "  -h         显示帮助"
    echo ""
    echo "示例:"
    echo "  my_skill -n hello"
    exit 0
fi

# --- 业务逻辑 ---
echo "执行结果"
```

---

## Markdown 技能

Markdown 技能是纯文档型技能，AI 阅读其内容后按指引行事，无需执行。

### 格式约定

```markdown
一句话功能摘要（首行，# 前缀会被自动去除）

## 技能说明
详细的功能描述、使用场景、操作步骤...

## 注意事项
需要特别关注的点...
```

系统提取第一个非空行作为摘要。若首行以 `#` 开头（如 `# 代码审查指南`），会自动去除 `#` 前缀，取 `代码审查指南` 作为摘要。其余全部内容为技能正文。

### 适用场景

Markdown 技能适合不需要代码执行的知识型内容：操作规范、审查清单、决策指引、回答模板等。

---

## 部署流程

### 开发阶段

源码保存在项目的 `skills/` 目录下，保留文件扩展名（`.py`、`.sh`、`.md`）便于开发维护。

### 安装到系统

部署到 `~/.aibox/skills/` 时需要去掉可执行技能的扩展名，并赋予执行权限：

```bash
# 手动安装
cp skills/my_skill.py ~/.aibox/skills/my_skill
chmod +x ~/.aibox/skills/my_skill

# 验证
~/.aibox/skills/my_skill --help
```

Markdown 技能保留 `.md` 扩展名直接复制。

### 通过 AI 安装

告诉 AI 使用 `install_skill` 工具，按指引操作：

```
使用 install_skill 工具安装 /path/to/my_skill.py
```

### 热重载

安装后调用 `reload_skills` 使新技能生效，无需重启服务：

```json
{
  "type": "message",
  "content": "使用 reload_skills 重载技能"
}
```

---

## 调用方式

AI 智能体通过 `search_skills` 搜索技能，通过 `run_command` 执行技能：

```json
// 1. 搜索
{"tool": "search_skills", "args": {"keyword": "邮件"}}

// 2. 执行
{"tool": "run_command", "args": {"command": "163mail --to user@example.com --subject 标题 --body 内容"}}
```

Markdown 技能不通过命令执行，AI 阅读 `search_skills` 返回的内容后直接遵循其中的指引。

---

## 编写建议

**摘要要精准**。`description` 是 AI 匹配技能的唯一线索。"温度转换工具 - 摄氏度转华氏度" 比 "一个转换工具" 好得多，因为 AI 能通过关键词准确命中。

**参数命名要直观**。优先使用有明确含义的长参数名（`--channel`、`--temperature`），短参数名（`-c`、`-t`）作为补充。

**输出要结构化**。结果输出到 stdout，错误输出到 stderr。多字段输出时每行一个字段，便于 AI 解析：

```
AIN0: +2.500000 V  (2500.000 mV)
AIN1: +1.234000 V  (1234.000 mV)
```

**依赖要自包含**。尽量使用标准库，若需要第三方库，在启动时检测并给出安装提示：

```python
try:
    import requests
except ImportError:
    print("错误: 需要 requests 库，请执行: pip install requests", file=sys.stderr)
    sys.exit(1)
```

**`--help` 要完备**。包含参数说明和使用示例两部分。AI 通过阅读 `--help` 输出学会如何调用技能，信息越完整，AI 调用越准确。
