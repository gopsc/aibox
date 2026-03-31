# AI智能体系统 - WebSocket服务器

单AI智能体系统，支持文件操作、网页访问、记忆管理、备忘录提醒等功能。所有任务都通过AI对话执行，并通过WebSocket实时与前端交互。

## 📋 目录

- [快速开始](#快速开始)
- [启动方式](#启动方式)
- [功能特点](#功能特点)
- [配置说明](#配置说明)
- [WebSocket API](#websocket-api)
- [任务系统](#任务系统)
- [工具列表](#工具列表)
- [扩展技能](#扩展技能)
- [命令参考](#命令参考)
- [项目结构](#项目结构)

## 🚀 快速开始

### 环境要求
- Python 3.12+
- DeepSeek API密钥

### 首次启动
```bash
# 首次启动（会自动创建必要的目录和配置文件）
bash _set.sh
```

### 启动服务
```bash
# 启动AGENT服务（WebSocket服务器）
bash _run.sh

# 启动网页端（如果使用提供的网页界面）
bash _runapp.sh
```

## 🎯 启动方式

### 详细启动步骤

1. **首次运行（初始化）**
   ```bash
   bash _set.sh
   ```
   此命令会：
   - 创建 `~/.aibox/` 数据目录
   - 生成默认配置文件 `~/.aibox/config.json`
   - 创建提示词目录 `~/.aibox/prompts/`
   - 创建技能目录 `~/.aibox/skills/`
   - 初始化数据库

2. **启动WebSocket服务器**
   ```bash
   bash _run.sh
   ```
   默认监听：`ws://localhost:8765`

3. **启动网页客户端**
   ```bash
   bash _runapp.sh
   ```
   打开浏览器访问 `http://localhost:8080`

### 命令行选项

```bash
python ai20.py [选项]

选项：
  --verbose, -v        显示详细日志
  --debug LEVEL        调试级别 (0-3)
  --host HOST          WebSocket服务器主机 (默认: localhost)
  --port PORT          WebSocket服务器端口 (默认: 8765)
  --lang {zh,en}       强制指定语言
  --no-scheduler       禁用任务调度器
  --scheduler-interval 调度器检查间隔（秒）
  
  # 任务管理快捷命令
  --check-memo         立即检查到期任务并退出
  --memo-add STR       添加任务，格式: "标题|内容|提醒时间|重复类型|重复间隔|单位"
  --memo-list          列出任务
  --memo-complete ID   完成指定ID的任务
```

## ✨ 功能特点

### 核心功能
- **🤖 智能对话** - 基于DeepSeek API，支持工具调用
- **📁 文件操作** - 读写文件、列出目录
- **🌐 网页访问** - 获取网页内容、搜索关键词
- **🧠 记忆管理** - 自动保存和检索重要对话内容
- **⏰ 任务系统** - 支持一次性、重复、即时任务
- **🔧 扩展技能** - 通过外部脚本动态扩展功能

### 特色功能
- **任务即对话** - 所有定时任务都作为AI对话执行
- **实时广播** - 任务状态和执行过程实时推送到前端
- **多语言支持** - 自动检测系统语言（中文/英文）
- **流式输出** - 命令执行和AI思考过程实时显示

## ⚙️ 配置说明

配置文件位置：`~/.aibox/config.json`

```json
{
  "system": {
    "save_dir": "~/.aibox",
    "debug_level": 1,
    "websocket_host": "localhost",
    "websocket_port": 8765,
    "skills_dir": "~/.aibox/skills",
    "prompts_dir": "~/.aibox/prompts"
  },
  "scheduler": {
    "enabled": true,
    "check_interval": 1.0,
    "max_tasks_per_run": 10,
    "broadcast_enabled": true
  },
  "api": {
    "deepseek_api_url": "https://api.deepseek.com/v1/chat/completions",
    "deepseek_model": "deepseek-chat",
    "api_key_env": "DEEPSEEK_API_KEY"
  },
  "memory": {
    "db_name": "memories.db",
    "max_search_results": 100
  }
}
```

## 🔌 WebSocket API

### 连接
```
ws://localhost:8765
```

### 消息格式

#### 1. 发送消息
```json
{
  "type": "message",
  "content": "你的问题"
}
```

#### 2. 发送命令
```json
{
  "type": "command",
  "command": "/help"
}
```

#### 3. 任务操作
```json
{
  "type": "task",
  "action": "add",
  "title": "提醒我喝水",
  "content": "记得喝水",
  "delay": 3600,
  "repeat_type": "custom",
  "repeat_interval": 30,
  "repeat_interval_unit": "minutes"
}
```

### 接收消息类型

| 类型 | 说明 |
|------|------|
| `chunk` | AI回复的流式片段 |
| `complete` | AI回复完成 |
| `error` | 错误信息 |
| `info` | 系统信息 |
| `task_status` | 任务状态更新 |
| `task_executing` | 任务开始执行 |
| `task_complete` | 任务执行完成 |

## 📅 任务系统

### 任务类型

1. **一次性任务** - 指定时间执行一次
2. **重复任务** - 按天/周/月/自定义间隔重复
3. **即时任务** - 立即执行（用于快速触发）

### 重复任务配置

```json
{
  "repeat_type": "custom",  // none, daily, weekly, monthly, custom
  "repeat_interval": 5,
  "repeat_interval_unit": "minutes",  // minutes, hours, days
  "repeat_end_time": "2024-12-31 23:59:59"  // 可选
}
```

### 任务状态流转
```
创建 → 待执行 → 触发AI对话 → 更新下次时间/完成 → 结束
```

## 🛠️ 工具列表

AI可以通过以下工具执行操作：

| 工具名 | 功能 | 示例 |
|--------|------|------|
| `memo` | 任务管理 | `memo add title="提醒" reminder_time="+1h"` |
| `memory` | 记忆管理 | `memory search keywords=["会议"]` |
| `web` | 网页访问 | `web get url="https://example.com"` |
| `read_file` | 读取文件 | `read_file filepath="~/test.txt"` |
| `write_file` | 写入文件 | `write_file filepath="~/test.txt" content="Hello"` |
| `list_files` | 列出目录 | `list_files directory="~/"` |
| `run_command` | 执行命令 | `run_command command="ls -la"` |
| `get_current_time` | 获取时间 | `get_current_time format="full"` |
| `calculator` | 数学计算 | `calculator a=10 b=5 operation="add"` |
| `save_memory_and_end_conversation` | 结束对话 | `save_memory_and_end_conversation summary="..."` |

## 🔧 扩展技能

将Python脚本放入 `~/.aibox/skills/` 目录，脚本需要实现以下接口：

### 脚本规范

```python
#!/usr/bin/env python3
import sys
import json
import argparse

def get_description():
    """返回工具描述"""
    return "工具功能说明"

def get_parameters():
    """返回参数定义（JSON Schema格式）"""
    return {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数说明"}
        },
        "required": ["param1"]
    }

def execute(**kwargs):
    """执行工具逻辑"""
    # 处理参数
    result = f"处理结果: {kwargs}"
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--description", action="store_true")
    parser.add_argument("--parameters", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--args", type=str)
    
    args = parser.parse_args()
    
    if args.description:
        print(get_description())
    elif args.parameters:
        print(json.dumps(get_parameters()))
    elif args.execute:
        kwargs = json.loads(args.args) if args.args else {}
        result = execute(**kwargs)
        print(result)
```

## 📟 命令参考

在WebSocket连接中可使用的命令：

| 命令 | 说明 |
|------|------|
| `/exit` | 退出连接 |
| `/new` | 开始新对话 |
| `/list` | 列出所有对话 |
| `/memories` | 查看最近的记忆 |
| `/memos` | 查看待办任务 |
| `/search <关键词>` | 搜索记忆 |
| `/config` | 查看配置 |
| `/reload` | 重新加载配置 |
| `/reload_prompts` | 重新加载提示词 |
| `/check` | 检查过期任务 |
| `/tasks` | 查看任务状态 |
| `/help` | 显示帮助 |

## 📁 项目结构

```
~/.aibox/
├── config.json          # 配置文件
├── memories.db          # SQLite数据库（记忆和任务）
├── current_conversation.json  # 当前对话
├── conversation_history.json  # 对话历史索引
├── archive/             # 已归档对话
├── prompts/             # 系统提示词
│   ├── 00_no_timestamp.txt
│   ├── 01_identity.txt
│   └── ...
└── skills/              # 扩展技能
    └── example_skill.py
```

## 📝 提示词管理

系统提示词按文件名顺序加载，位于 `~/.aibox/prompts/`：

- `00_no_timestamp.txt` - 禁止输出时间戳
- `01_identity.txt` - AI身份定义
- `02_memory_search.txt` - 记忆搜索习惯
- `03_memory_save.txt` - 记忆保存习惯
- ...

## 🌐 语言支持

系统自动检测系统语言环境（中文/英文），可通过环境变量或命令行参数强制指定：

```bash
# 环境变量
export AI_LANGUAGE=en

# 命令行参数
python ai20.py --lang en
```

## 🚨 注意事项

1. **API密钥**：需要设置 `DEEPSEEK_API_KEY` 环境变量
2. **文件安全**：文件操作限制在用户目录内
3. **命令执行**：默认启用，可通过配置禁用
4. **数据存储**：所有数据存储在 `~/.aibox/`
5. **任务执行**：所有任务都会触发AI对话，确保AI处于活动状态

## 🐛 故障排除

### 常见问题

1. **WebSocket连接失败**
   - 检查端口是否被占用
   - 确认防火墙设置

2. **任务不执行**
   - 检查调度器是否启用
   - 确认任务时间格式正确

3. **API调用失败**
   - 验证 `DEEPSEEK_API_KEY` 是否设置正确
   - 检查网络连接

### 日志查看
日志文件位置：`~/.aibox/ai.log`

---

## 📄 许可证

MIT License