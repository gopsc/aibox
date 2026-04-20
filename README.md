# 单AI智能体系统 - WebSocket版本

一个功能强大的AI智能体系统，通过WebSocket与客户端交互，支持文件操作、网页访问、记忆管理、定时任务等功能。

## ✨ 核心特性

- 🤖 **单AI智能体**：基于DeepSeek API的智能对话系统
- 🔌 **WebSocket通信**：实时双向通信，支持流式输出
- 📁 **文件操作**：读写文件、目录列表（支持大文件分页）
- 🌐 **网页访问**：获取网页内容、提取链接、搜索信息
- 🧠 **记忆管理**：自动保存和检索对话记忆，保持对话连贯性
- ⏰ **定时任务**：支持一次性、重复、即时任务，自动触发AI对话
- 🔧 **扩展技能**：动态加载`~/.aibox/skills/`目录下的可执行脚本
- 📝 **对话压缩**：当消息过多时自动压缩，保持上下文质量
- 🌍 **多语言支持**：自动检测系统语言，支持中英文

## 🚀 快速开始

### 环境要求

- Python 3.8+
- DeepSeek API Key

### 安装

```bash
# 克隆或下载代码
# 安装依赖
pip install websockets requests beautifulsoup4
```

### 配置

1. 设置DeepSeek API Key：
```bash
export DEEPSEEK_API_KEY="your-api-key"
```

2. （可选）配置文件：`~/.aibox/config.json`（系统会自动创建默认配置）

### 启动服务器

```bash
python agent.py
```

启动后，WebSocket服务器将运行在 `ws://localhost:8765`

## 📁 目录结构

```
~/.aibox/
├── config.json          # 配置文件
├── prompts/             # 系统提示词目录
│   ├── 00_IDENTITY.md   # 用户身份信息
│   ├── 1_*.md           # 基础技能提示词
│   ├── 99_SOUL.md       # AI灵魂定义（角色、性格）
│   └── 100_STATUS.md    # AI状态记录
├── skills/              # 扩展技能目录
├── memories.db          # 记忆数据库
├── archive/             # 对话归档目录
└── tool_results/        # 工具结果缓存
```

## 🔧 可用工具

AI智能体可以调用以下工具来完成任务：

| 工具名称 | 功能描述 |
|---------|---------|
| `read_file` | 读取文件内容（支持分页） |
| `write_file` | 写入或追加文件 |
| `list_files` | 列出目录内容 |
| `web` | 访问网页、获取标题/文本/链接 |
| `memory` | 保存、搜索、删除记忆 |
| `memo` | 创建、查看、完成任务 |
| `run_command` | 执行系统命令（实时输出） |
| `search_skills` | 搜索扩展技能 |
| `reload_skills` | 热重载扩展技能 |
| `create_skill` | 创建新技能（AI自主编写） |
| `update_identity` | 更新用户身份信息 |
| `update_soul` | 更新AI自我定义 |
| `save_memory_and_end_conversation` | 保存记忆并结束对话 |
| `get_current_time` | 获取当前时间 |
| `calculator` | 数学计算 |

## 💬 WebSocket API

### 连接

```javascript
const ws = new WebSocket('ws://localhost:8765');
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

#### 发送任务
```json
{
  "type": "task",
  "action": "add",
  "title": "提醒我喝水",
  "delay": 3600
}
```

### 支持的命令

| 命令 | 功能 |
|-----|------|
| `/exit` | 退出连接 |
| `/new` | 开始新对话（保存当前，重置记忆） |
| `/list` | 列出所有对话 |
| `/memories` | 查看最近记忆 |
| `/memos` | 查看待办任务 |
| `/search <关键词>` | 搜索记忆 |
| `/config` | 查看配置 |
| `/reload` | 重载配置 |
| `/reload_prompts` | 重载提示词 |
| `/check` | 检查过期任务 |
| `/tasks` | 查看任务状态 |
| `/help` | 显示帮助 |

### 接收消息类型

| 类型 | 说明 |
|-----|------|
| `chunk` | AI响应的片段（流式输出） |
| `complete` | AI响应完成 |
| `error` | 错误信息 |
| `command_result` | 命令执行结果 |
| `task_status` | 任务状态更新 |
| `dialogue_ended` | 对话结束通知 |

## ⏰ 任务系统

### 任务类型

1. **一次性任务**：在指定时间执行一次
2. **重复任务**：daily/weekly/monthly/自定义间隔
3. **即时任务**：立即执行（`is_immediate: true`）

### 添加任务示例

```json
{
  "type": "task",
  "action": "add",
  "title": "每天提醒",
  "repeat_type": "daily"
}
```

```json
{
  "type": "task",
  "action": "add",
  "title": "5分钟后提醒",
  "delay": 300
}
```

```json
{
  "type": "task",
  "action": "add",
  "title": "立即执行",
  "is_immediate": true
}
```

## 🔧 扩展技能

### 添加自定义技能

将可执行脚本放入 `~/.aibox/skills/` 目录，系统会自动识别。

**技能接口要求**：
- 支持 `--help` 参数
- `--help` 第一行为一句话简介
- 其余为完整的参数说明和使用示例

### 让AI创建技能

直接告诉AI：
```
创建一个技能，功能是将摄氏度转换为华氏度，接受 -c 参数输入温度
```

AI会自动编写脚本并部署。

## ⚙️ 配置说明

主要配置项（`~/.aibox/config.json`）：

```json
{
  "system": {
    "save_dir": "~/.aibox",
    "websocket_host": "localhost",
    "websocket_port": 8765,
    "debug_level": 1
  },
  "context": {
    "max_history_messages": 500,
    "compress_enabled": true,
    "compress_message_threshold": 100
  },
  "scheduler": {
    "enabled": true,
    "check_interval": 1.0
  }
}
```

## 🧠 对话压缩

当对话消息数达到阈值（默认100条）时，系统会自动：
1. 调用AI压缩早期对话内容
2. 保留最近的重要消息
3. 将压缩摘要作为系统消息

压缩过程静默执行，不影响用户体验。

## 📝 提示词系统

提示词文件位于 `~/.aibox/prompts/`：

- `00_IDENTITY.md`：用户身份信息（AI可通过工具更新）
- `1_*.md`：基础技能提示词（文件操作、网页访问等）
- `99_SOUL.md`：AI灵魂定义（角色、性格、能力边界）
- `100_STATUS.md`：AI状态记录

AI可以使用 `update_identity` 和 `update_soul` 工具动态更新自己的定义。

## 🛠️ 命令行参数

```bash
python agent.py [选项]

选项:
  --verbose, -v        显示详细日志
  --debug LEVEL        调试级别 (0-3)
  --lang zh|en         强制语言
  --host HOST          WebSocket主机
  --port PORT          WebSocket端口
  --no-scheduler       禁用任务调度器
  --check-memo         检查到期任务
  --memo-add "标题|内容|时间"  添加任务
  --memo-list          列出任务
  --memo-complete ID   完成任务
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！