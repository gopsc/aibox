# 单AI智能体系统 - WebSocket版本

一个功能强大的AI智能体系统，支持文件操作、网页访问、记忆管理、任务调度等功能，通过WebSocket与客户端实时通信。

## ✨ 主要特性

### 核心功能
- **智能对话**：基于DeepSeek API的AI对话能力
- **工具调用**：支持多种内置工具和扩展技能
- **记忆管理**：自动保存和检索对话记忆，保持对话连贯性
- **任务调度**：支持定时任务和即时任务，自动执行
- **实时通信**：WebSocket实时双向通信，支持流式输出

### 工具能力
| 工具 | 功能 |
|------|------|
| 📁 文件操作 | 读取、写入、列出目录 |
| 🌐 网页访问 | 获取网页内容、提取标题/链接 |
| 🧠 记忆管理 | 保存、搜索、删除记忆 |
| 📋 任务管理 | 创建、完成、查询定时/即时任务 |
| 🔧 命令执行 | 执行系统命令，支持流式输出 |
| 🎯 扩展技能 | 动态加载Python脚本作为技能 |

### 高级特性
- **对话压缩**：自动压缩过长对话，节省Token
- **热重载**：技能文件修改后无需重启即可生效
- **多语言**：自动检测系统语言，支持中文/英文
- **历史归档**：自动保存对话历史，支持查询

## 📋 系统要求

- Python 3.8+
- DeepSeek API Key

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install websockets requests beautifulsoup4
```

### 2. 配置API Key

设置环境变量或创建配置文件：

```bash
export DEEPSEEK_API_KEY="your-api-key"
```

### 3. 启动服务器

```bash
python main.py
```

### 4. 连接客户端

使用WebSocket客户端连接：`ws://localhost:8765`

## ⚙️ 配置

### 配置文件位置
`~/.aibox/config.json`（自动创建）

### 主要配置项

```json
{
  "system": {
    "save_dir": "~/.aibox",           // 数据存储目录
    "skills_dir": "~/.aibox/skills",   // 扩展技能目录
    "prompts_dir": "~/.aibox/prompts", // 提示词目录
    "websocket_host": "localhost",     // WebSocket主机
    "websocket_port": 8765             // WebSocket端口
  },
  "api": {
    "deepseek_model": "deepseek-chat", // AI模型
    "temperature": 0.7                // 回答温度
  },
  "context": {
    "compress_message_threshold": 100, // 消息压缩阈值
    "max_context_messages": 120        // 最大上下文消息数
  },
  "scheduler": {
    "enabled": true,                   // 启用任务调度器
    "check_interval": 1.0             // 检查间隔（秒）
  }
}
```

## 📁 目录结构

```
~/.aibox/
├── config.json           # 配置文件
├── memories.db           # 记忆和任务数据库
├── current_conversation.json  # 当前对话
├── archive/              # 历史对话归档
├── prompts/              # 系统提示词目录
│   ├── 00_IDENTITY.md    # 用户身份信息
│   ├── 1_*.md           # 基础技能提示词
│   ├── 99_SOUL.md        # 智能体自我定义
│   └── 100_STATUS.md     # 智能体状态
├── skills/               # 扩展技能目录
└── tool_results/         # 工具结果缓存
```

## 💬 WebSocket协议

### 消息格式

#### 发送消息（客户端 → 服务器）

**普通对话**
```json
{
  "type": "message",
  "content": "你好，请帮我..."
}
```

**命令**
```json
{
  "type": "command",
  "command": "/new"
}
```

**添加任务**
```json
{
  "type": "task",
  "action": "add",
  "title": "提醒我喝水",
  "delay": 3600,
  "repeat_type": "daily"
}
```

**即时任务**
```json
{
  "type": "task",
  "action": "add",
  "title": "立即执行的任务",
  "is_immediate": true
}
```

#### 接收消息（服务器 → 客户端）

**流式响应**
```json
{"type": "chunk", "content": "你好，"}
{"type": "chunk", "content": "我是AI助手"}
{"type": "complete", "content": "完整响应"}
```

**任务状态**
```json
{
  "type": "task_status",
  "task_id": 1,
  "title": "提醒喝水",
  "status": "executing",
  "message": "正在执行..."
}
```

**错误信息**
```json
{"type": "error", "content": "错误描述"}
```

## 🛠️ 支持的命令

| 命令 | 说明 |
|------|------|
| `/new` | 开始新对话（保存当前对话，重置AI） |
| `/list` | 列出所有历史对话 |
| `/memories` | 查看最近的记忆 |
| `/memos` | 查看待办任务 |
| `/search <关键词>` | 搜索记忆 |
| `/config` | 查看当前配置 |
| `/reload` | 重新加载配置 |
| `/reload_prompts` | 重新加载提示词 |
| `/check` | 检查过期任务 |
| `/tasks` | 查看任务调度器状态 |
| `/exit` | 断开连接 |
| `/help` | 显示帮助 |

## 🧩 扩展技能开发

### 创建技能

1. 在 `~/.aibox/skills/` 目录下放置可执行脚本
2. 脚本必须支持 `--help` 参数
3. `--help` 输出**第一行**为技能简介，其余为使用说明

### 技能示例（Python）

```python
#!/usr/bin/env python3
"""
示例技能 - 计算两个数字的和
"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="计算两个数字的和")
    parser.add_argument("--a", type=float, required=True, help="第一个数字")
    parser.add_argument("--b", type=float, required=True, help="第二个数字")
    args = parser.parse_args()
    
    result = args.a + args.b
    print(f"{args.a} + {args.b} = {result}")

if __name__ == "__main__":
    main()
```

### 使用技能

```bash
# 1. 确保脚本可执行
chmod +x ~/.aibox/skills/adder

# 2. 重载技能（在对话中）
用户: reload_skills confirm=true

# 3. 搜索技能
用户: search_skills keyword="计算"

# 4. 查看帮助
用户: run_command command="adder --help"

# 5. 执行技能
用户: run_command command="adder --a 10 --b 20"
```

## 📝 提示词定制

### 目录结构

```
~/.aibox/prompts/
├── 00_IDENTITY.md    # 用户身份信息
├── 1_*.md           # 基础技能（以1_开头）
├── 99_SOUL.md        # AI角色定义
└── 100_STATUS.md     # AI状态记录
```

### 自定义AI性格

编辑 `99_SOUL.md` 文件，定义：
- 核心身份和角色定位
- 性格特点
- 能力边界
- 行为准则
- 工作流程

## 🔧 命令行选项

```bash
python main.py [选项]

选项:
  --verbose, -v        显示详细日志
  --debug LEVEL        调试级别 (0-3)
  --config PATH        指定配置文件路径
  --host HOST          WebSocket主机
  --port PORT          WebSocket端口
  --lang zh|en         强制语言
  --no-scheduler       禁用任务调度器
  --scheduler-interval 调度器检查间隔
  
  # 任务管理
  --memo-list          列出所有任务
  --memo-add "标题|内容|时间"  添加任务
  --memo-complete ID   完成任务
  --check-memo         检查过期任务
```

## 🔄 工作流程

```
用户 ──WebSocket──→ 服务器 ──API调用──→ DeepSeek API
                          │
                          ↓
                    工具执行器
                    ├── 文件操作
                    ├── 网页访问
                    ├── 命令执行
                    ├── 记忆管理
                    └── 任务调度器
                          │
                          ↓
用户 ←──WebSocket── 服务器 ←── 结果 ──┘
```

## 📊 任务类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 一次性 | 执行一次后自动完成 | `delay: 3600` |
| 每日 | 每天同一时间执行 | `repeat_type: "daily"` |
| 每周 | 每周同一时间执行 | `repeat_type: "weekly"` |
| 每月 | 每月同一时间执行 | `repeat_type: "monthly"` |
| 自定义 | 自定义间隔 | `repeat_type: "custom", repeat_interval: 5, repeat_interval_unit: "minutes"` |
| 即时 | 立即执行 | `is_immediate: true` |

## ❓ 常见问题

### Q: 如何查看API Key是否正确配置？
```bash
echo $DEEPSEEK_API_KEY
```

### Q: 技能不生效？
1. 确认文件可执行：`chmod +x 脚本名`
2. 确认支持`--help`参数
3. 调用`reload_skills confirm=true`重载
4. 检查`~/.aibox/skills/`目录

### Q: 如何备份数据？
备份 `~/.aibox/` 目录即可

### Q: 对话历史保存在哪里？
- 当前对话：`~/.aibox/current_conversation.json`
- 历史归档：`~/.aibox/archive/`

## 📄 许可证

MIT License

---

**提示**：首次启动会自动创建配置目录和默认提示词文件，可以根据需要修改定制。
