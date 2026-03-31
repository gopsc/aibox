# 单AI智能体系统 - WebSocket服务器

一个功能强大的AI智能体系统，支持对话管理、文件操作、网页访问、记忆管理、任务调度等功能。所有任务都作为对话任务执行，通过WebSocket与客户端实时交互。

## ✨ 核心特性

### 🤖 AI对话
- DeepSeek API集成
- 实时流式输出响应
- 工具调用支持（函数调用）
- 对话历史管理
- 对话内容自动压缩（当消息数或Token数达到阈值时）
- 开始新对话时重置记忆并重新加载系统提示词

### 📁 文件操作
- 读取文件（支持指定行范围）
- 写入文件（覆盖/追加）
- 列出目录内容
- 大文件处理提示

### 🌐 网页访问
- 获取网页内容
- 提取纯文本
- 获取标题
- 提取所有链接
- 搜索关键词

### 🧠 记忆管理
- 保存重要对话记忆
- 多关键词搜索记忆
- 查看最近记忆
- 分页浏览
- 记忆重要性标记

### 📋 任务管理（所有任务都是对话任务）
- 创建一次性/重复任务（daily/weekly/monthly/custom）
- 即时任务（立即执行）
- 任务列表查看
- 任务完成标记
- 任务搜索
- 任务统计

### 🔧 扩展技能
- 动态加载Python脚本作为工具
- 技能热重载（无需重启）
- 技能接口规范

### ⚙️ 系统功能
- 命令执行（支持超时和实时输出）
- 系统配置管理
- 日志系统
- 健康检查

## 🚀 快速开始

### 环境要求

- Python 3.8+
- DeepSeek API密钥

### 安装依赖

```bash
pip install websockets requests beautifulsoup4
```

### 配置API密钥

设置DeepSeek API密钥：

```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

或创建配置文件 `~/.aibox/config.json`：

```json
{
  "api": {
    "api_key_env": "DEEPSEEK_API_KEY",
    "deepseek_api_url": "https://api.deepseek.com/v1/chat/completions",
    "deepseek_model": "deepseek-chat"
  }
}
```

### 启动服务器

```bash
# 基本启动
python ai_agent.py

# 指定端口和主机
python ai_agent.py --host 0.0.0.0 --port 8765

# 启用详细日志
python ai_agent.py --verbose

# 禁用任务调度器
python ai_agent.py --no-scheduler

# 查看帮助
python ai_agent.py --help
```

## 📖 使用指南

### WebSocket连接

连接到服务器：

```javascript
const ws = new WebSocket('ws://localhost:8765');
```

### 发送消息

```javascript
// 发送对话消息
ws.send(JSON.stringify({
    type: "message",
    content: "你好，请帮我创建一个任务"
}));

// 发送命令
ws.send(JSON.stringify({
    type: "command",
    command: "/help"
}));
```

### 接收消息类型

服务器返回的消息格式：

```javascript
{
    "type": "chunk",        // 响应片段
    "content": "你好，"
}
{
    "type": "complete",     // 完整响应
    "content": "你好，我是AI助手..."
}
{
    "type": "error",        // 错误信息
    "content": "错误描述"
}
{
    "type": "info",         // 信息提示
    "content": "系统信息"
}
{
    "type": "task_status",  // 任务状态
    "task_id": 1,
    "title": "任务标题",
    "status": "executing",
    "message": "正在执行..."
}
{
    "type": "dialogue_ended", // 对话结束
    "content": "对话已结束"
}
```

### 支持的命令

| 命令 | 说明 |
|------|------|
| `/exit` | 退出连接 |
| `/new` | 开始新对话（保存当前对话，重置AI记忆，重新加载系统提示词） |
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

### 任务管理

添加任务：

```javascript
// 一次性任务（60秒后执行）
ws.send(JSON.stringify({
    type: "task",
    action: "add",
    title: "提醒喝水",
    content: "记得喝水哦",
    delay: 60
}));

// 即时任务（立即执行）
ws.send(JSON.stringify({
    type: "task",
    action: "add",
    title: "立即提醒",
    is_immediate: true
}));

// 重复任务（每5分钟）
ws.send(JSON.stringify({
    type: "task",
    action: "add",
    title: "定时提醒",
    repeat_type: "custom",
    repeat_interval: 5,
    repeat_interval_unit: "minutes"
}));

// 获取任务列表
ws.send(JSON.stringify({
    type: "task",
    action: "list"
}));

// 完成任务
ws.send(JSON.stringify({
    type: "task",
    action: "complete",
    task_id: 1
}));
```

## 🔧 工具系统

AI可以通过工具调用执行各种操作：

### 内置工具

| 工具名称 | 说明 |
|---------|------|
| `get_current_time` | 获取当前时间 |
| `calculator` | 数学计算 |
| `run_command` | 执行系统命令（支持实时输出） |
| `read_file` | 读取文件（支持行范围） |
| `write_file` | 写入文件 |
| `list_files` | 列出目录 |
| `web` | 网页访问 |
| `memory` | 记忆管理 |
| `memo` | 任务管理 |
| `update_identity` | 更新用户身份 |
| `update_soul` | 更新AI自我认知 |
| `reload_skills` | 热重载技能 |
| `save_memory_and_end_conversation` | 保存记忆并结束对话 |

### 扩展技能

将Python脚本放入 `~/.aibox/skills/` 目录，脚本需要实现以下接口：

```python
#!/usr/bin/env python3
import argparse
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--description', action='store_true')
    parser.add_argument('--parameters', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--args', type=str)
    
    args = parser.parse_args()
    
    if args.description:
        print("技能描述")
    elif args.parameters:
        print(json.dumps({
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数1"}
            },
            "required": ["param1"]
        }))
    elif args.execute:
        # 执行技能逻辑
        params = json.loads(args.args)
        result = f"执行结果: {params}"
        print(result)

if __name__ == "__main__":
    main()
```

## 📁 目录结构

```
~/.aibox/
├── config.json              # 配置文件
├── memories.db              # 记忆数据库
├── ai.log                   # 日志文件
├── current_conversation.json # 当前对话
├── conversation_history.json  # 对话历史索引
├── archive/                 # 归档对话
├── skills/                  # 扩展技能目录
│   ├── my_skill.py
│   └── another_skill.py
├── prompts/                 # 提示词目录
│   ├── 00_IDENTITY.md       # 用户身份信息
│   ├── 1_memory_search.md   # 基础技能
│   ├── 2_memory_save.md
│   ├── ...
│   ├── 99_SOUL.md           # AI灵魂定义
│   └── 100_STATUS.md        # AI状态记录
└── tool_results/            # 工具结果缓存
```

## ⚙️ 配置说明

配置文件位置：`~/.aibox/config.json`

```json
{
  "system": {
    "save_dir": "~/.aibox",
    "debug_level": 1,
    "load_history_by_default": true,
    "websocket_host": "localhost",
    "websocket_port": 8765
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
    "timeout": 30,
    "temperature": 0.7
  },
  "context": {
    "max_history_messages": 500,
    "max_context_messages": 120,
    "max_tokens": 8192,
    "compress_enabled": true,
    "compress_message_threshold": 100,
    "compress_token_threshold": 4000,
    "compress_ratio": 0.4,
    "compress_keep_recent": 20
  },
  "commands": {
    "enabled": true
  },
  "web": {
    "timeout": 10,
    "user_agent": "Mozilla/5.0..."
  },
  "memory": {
    "max_search_results": 100,
    "default_importance": 2
  },
  "memo": {
    "default_reminder_minutes": 60,
    "allow_user_tasks": true
  }
}
```

## 📝 提示词系统

系统从 `~/.aibox/prompts/` 目录加载提示词：

- **00_IDENTITY.md**：用户身份信息（AI会记录用户身份）
- **1_*.md**：基础技能提示词（记忆搜索、保存、文件操作等）
- **99_SOUL.md**：AI灵魂定义（角色、性格、能力边界）
- **100_STATUS.md**：AI状态记录（当前状态、下一步计划）

AI可以通过工具更新这些文件：
- `update_identity`：更新用户身份
- `update_soul`：更新自我认知
- `save_memory_and_end_conversation`：保存记忆并更新状态

## 🔄 对话压缩

当对话消息数或Token数达到阈值时，系统会自动压缩较早的对话内容：

- 使用AI生成对话摘要
- 保留最近的对话轮次
- 压缩后的摘要作为系统消息插入
- 静默执行，不影响用户体验

配置参数：
- `compress_enabled`：是否启用压缩
- `compress_message_threshold`：消息数阈值（默认100）
- `compress_token_threshold`：Token数阈值（默认4000）
- `compress_keep_recent`：保留最近的消息数（默认20）

## 📊 命令行工具

```bash
# 列出所有任务
python ai_agent.py --memo-list

# 添加任务
python ai_agent.py --memo-add "提醒|记得喝水|+1h|daily"

# 完成任务
python ai_agent.py --memo-complete 1

# 检查过期任务
python ai_agent.py --check-memo

# 指定配置文件
python ai_agent.py --config /path/to/config.json

# 强制使用英文
python ai_agent.py --lang en
```

## 🔒 安全提示

1. **命令执行**：默认启用，可通过配置禁用
2. **文件访问**：只能访问系统允许的路径
3. **网络请求**：网页访问会使用延迟避免过载
4. **超时控制**：所有操作都有超时限制

## 🐛 故障排除

### 连接失败
- 检查WebSocket服务器是否启动
- 确认端口没有被占用

### API调用失败
- 确认DeepSeek API密钥已正确设置
- 检查网络连接

### 任务不执行
- 检查调度器是否启用
- 确认任务提醒时间是否正确

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！
