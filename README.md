# 🤖 单AI智能体系统

一个功能强大的AI智能体系统，支持文件操作、网页访问、记忆管理、定时任务等功能，通过WebSocket与客户端实时交互。

## ✨ 核心特性

### 🧠 智能对话
- **流式响应**：AI回复实时流式输出，无需等待完整响应
- **记忆管理**：自动保存和检索重要对话记忆，保持对话连贯性
- **多语言支持**：自动检测系统语言，支持中英文界面

### 🔧 内置工具
| 工具 | 功能 |
|------|------|
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件 |
| `list_files` | 列出目录内容 |
| `web` | 访问网页、提取内容 |
| `run_command` | 执行系统命令（实时输出） |
| `memory` | 保存/搜索/删除记忆 |
| `memo` | 创建/管理定时任务 |
| `get_current_time` | 获取当前时间 |
| `calculator` | 数学计算 |
| `update_identity` | 更新用户身份信息 |
| `update_soul` | 更新智能体自我定义 |
| `search_skills` | 搜索扩展技能 |
| `reload_skills` | 热重载扩展技能 |

### ⏰ 任务调度器
- **定时任务**：支持一次性、每天、每周、每月、自定义间隔重复
- **即时任务**：添加后立即执行
- **任务队列**：到期自动触发AI对话执行
- **实时广播**：任务执行状态实时推送到前端

### 📦 对话压缩
- 当对话消息数达到阈值（默认100条）时自动压缩
- 使用LLM智能总结早期对话内容
- 保留最近N条消息，保证上下文连贯

### 🔌 扩展技能系统
- 将Python脚本放入 `~/.aibox/skills/` 目录即可扩展
- 脚本需实现 `--description`、`--parameters`、`--execute` 接口
- 支持热重载，无需重启系统

## 📁 目录结构

```
~/.aibox/
├── config.json          # 配置文件
├── ai.log              # 运行日志
├── memories.db         # 记忆和任务数据库
├── current_conversation.json  # 当前对话
├── archive/            # 历史对话归档
├── prompts/            # 系统提示词目录
│   ├── 00_IDENTITY.md  # 用户身份信息
│   ├── 1_*.md          # 基础技能（1_开头）
│   ├── 99_SOUL.md      # 智能体灵魂定义
│   └── 100_STATUS.md   # 智能体状态记录
├── skills/             # 扩展技能目录
└── tool_results/       # 工具结果缓存
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- 依赖包：`websockets`, `requests`, `beautifulsoup4`

### 安装依赖
```bash
pip install websockets requests beautifulsoup4
```

### 配置API密钥
设置环境变量：
```bash
export ARK_API_KEY="your-api-key"
```

### 启动服务器
```bash
python ai_agent.py
```

### 命令行选项
```bash
# 详细日志模式
python ai_agent.py --verbose

# 指定调试级别 (0-3)
python ai_agent.py --debug 3

# 指定语言
python ai_agent.py --lang en

# 指定WebSocket端口
python ai_agent.py --port 8765

# 禁用任务调度器
python ai_agent.py --no-scheduler

# 命令行添加任务
python ai_agent.py --memo-add "提醒标题|提醒内容|+1h"

# 列出所有待执行任务
python ai_agent.py --memo-list

# 完成任务
python ai_agent.py --memo-complete 1
```

## 📡 WebSocket API

### 连接
```
ws://localhost:8765
```

### 消息格式

#### 发送用户消息
```json
{
    "type": "message",
    "content": "你好，请帮我..."
}
```

#### 发送命令
```json
{
    "type": "command",
    "command": "/new"
}
```

#### 添加任务
```json
{
    "type": "task",
    "action": "add",
    "title": "提醒标题",
    "content": "提醒内容",
    "delay": 3600,
    "repeat_type": "daily"
}
```

#### 列出任务
```json
{
    "type": "task",
    "action": "list"
}
```

#### 完成任务
```json
{
    "type": "task",
    "action": "complete",
    "task_id": 1
}
```

### 接收消息类型

| 类型 | 说明 |
|------|------|
| `chunk` | AI响应片段（流式） |
| `complete` | AI响应完成 |
| `error` | 错误信息 |
| `task_status` | 任务状态更新 |
| `command_result` | 命令执行结果 |
| `info` | 系统信息 |
| `dialogue_ended` | 对话结束信号 |

## ⌨️ 内置命令

| 命令 | 说明 |
|------|------|
| `/new` | 开始新对话（保存当前对话，重置AI记忆） |
| `/list` | 列出所有对话历史 |
| `/memories` | 查看最近的记忆 |
| `/memos` | 查看待办任务 |
| `/search <关键词>` | 搜索记忆库 |
| `/config` | 查看当前配置 |
| `/reload` | 重新加载配置 |
| `/reload_prompts` | 重新加载提示词 |
| `/check` | 检查过期任务 |
| `/tasks` | 查看任务调度器状态 |
| `/help` | 显示帮助信息 |
| `/exit` | 断开连接 |

## 🔧 配置文件

配置文件位于 `~/.aibox/config.json`：

```json
{
    "system": {
        "save_dir": "~/.aibox",
        "debug_level": 1,
        "websocket_host": "localhost",
        "websocket_port": 8765
    },
    "api": {
        "deepseek_api_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "deepseek_model": "doubao-seed-2-0-mini-260215",
        "api_key_env": "ARK_API_KEY",
        "timeout": 30
    },
    "context": {
        "max_history_messages": 500,
        "compress_enabled": true,
        "compress_message_threshold": 100,
        "compress_keep_recent": 8
    },
    "scheduler": {
        "enabled": true,
        "check_interval": 1.0
    },
    "commands": {
        "enabled": true
    }
}
```

## 📝 系统提示词管理

### 文件说明
- **00_IDENTITY.md**：用户身份信息（AI可通过 `update_identity` 工具更新）
- **1_*.md**：基础技能文件，定义AI的能力和行为习惯
- **99_SOUL.md**：智能体灵魂文件，定义AI的角色定位、性格、价值观（AI可通过 `update_soul` 工具自我更新）
- **100_STATUS.md**：智能体状态记录（AI可通过 `save_memory_and_end_conversation` 工具更新）

### 自定义提示词
在 `~/.aibox/prompts/` 目录下创建 `.md` 或 `.txt` 文件，系统会自动加载并按文件名排序后作为系统提示词。

## 🔌 扩展技能开发

### 创建技能脚本
将Python脚本放入 `~/.aibox/skills/` 目录，确保文件可执行（`chmod +x`）。

### 脚本接口要求
```python
#!/usr/bin/env python3
import argparse
import json

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--description", action="store_true")
    parser.add_argument("--parameters", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    
    if args.description:
        print("技能简短描述（第一行会作为摘要显示）")
    elif args.parameters:
        print(json.dumps({
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数说明"}
            },
            "required": ["param1"]
        }))
    elif args.execute:
        # 执行技能逻辑
        print("执行结果")
```

### 使用扩展技能
1. 使用 `search_skills` 工具搜索可用技能
2. 使用 `run_command` 执行 `技能名 --help` 查看完整帮助
3. 使用 `run_command` 按正确格式调用技能

## 🎯 使用示例

### 添加定时任务
```
用户: 帮我设置一个提醒，1小时后提醒我开会
AI: [调用 memo 工具添加任务] ✅ 任务已添加，ID: 1，执行时间: 2024-01-15 14:30:00
```

### 搜索记忆
```
用户: 我们上次讨论的项目怎么样了？
AI: [调用 memory search 工具搜索相关记忆] 根据之前的对话，您提到项目已完成80%...
```

### 结束对话并保存记忆
```
用户: 好了，今天就到这里吧
AI: [调用 save_memory_and_end_conversation 工具] ✅ 对话记忆已保存，状态已更新，对话结束
```

## 📊 日志系统

日志文件位置：`~/.aibox/ai.log`

支持日志轮转：
- 最大大小：10MB（可配置）
- 备份数量：5个（可配置）

## 🐛 调试

启用详细日志：
```bash
python ai_agent.py --verbose
# 或
python ai_agent.py --debug 3
```

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交Issue和Pull Request。
