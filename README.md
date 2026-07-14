# 单AI智能体系统 - WebSocket版本（增强版）

一个功能强大的AI智能体系统，通过WebSocket与客户端交互，支持文件操作、网页访问、记忆管理、任务调度、扩展技能等功能。所有任务都通过AI对话执行，支持实时流式输出和任务状态广播。

## ✨ 核心特性

- 🤖 **单AI智能体**：基于DeepSeek API的智能对话系统，支持思考模式
- 🔌 **WebSocket通信**：实时双向通信，支持流式输出和任务状态广播
- 📁 **文件操作**：读写文件、目录列表（支持大文件分页）
- 🌐 **网页访问**：获取网页内容、提取标题、链接、搜索信息
- 🧠 **记忆管理**：自动保存和检索对话记忆，保持对话连贯性
- ⏰ **任务系统**：支持一次性、重复（daily/weekly/monthly/custom）、即时任务，自动触发AI对话
- 🔧 **扩展技能**：动态加载`~/.aibox/skills/`目录下的可执行脚本或Markdown技能文件
- 📦 **对话压缩**：当消息数或Token数达到阈值时自动压缩，保持上下文质量
- 🌍 **多语言支持**：自动检测系统语言，支持中英文
- 🧬 **智能体自我进化**：通过`update_soul`工具动态更新角色定位和性格定义
- 🔄 **技能热重载**：无需重启即可添加、修改或删除扩展技能
- 💾 **对话管理**：历史对话归档、开始新对话（重置AI记忆）

## 🚀 快速开始

### 环境要求

- Python 3.8+
- DeepSeek API Key
- 操作系统：Linux/macOS/Windows

### 安装

```bash
# 克隆或下载代码
# 安装依赖
pip install websockets requests beautifulsoup4
```

### 配置

1. **设置DeepSeek API Key**：
```bash
export DEEPSEEK_API_KEY="your-api-key"
```

2. **（可选）配置文件**：`~/.aibox/config.json`（系统会自动创建默认配置）

3. **启动服务器**：
```bash
python agent.py
```

启动后，WebSocket服务器将运行在 `ws://localhost:8765`

## 📁 目录结构

```
~/.aibox/
├── config.json              # 配置文件
├── prompts/                 # 系统提示词目录
│   ├── 00_IDENTITY.md       # 用户身份信息
│   ├── 1_*.md               # 基础技能提示词（文件操作、网页访问等）
│   ├── 99_SOUL.md           # AI灵魂定义（角色、性格、能力边界）
│   └── 100_STATUS.md        # AI状态记录
├── skills/                  # 扩展技能目录
│   ├── my_skill             # 可执行技能（无扩展名）
│   └── guide.md             # Markdown技能
├── memories.db              # 记忆和任务数据库
├── current_conversation.json # 当前对话
├── conversation_history.json # 对话索引
├── archive/                 # 历史对话归档
└── tool_results/            # 工具结果缓存
```

## 🔧 可用工具

AI智能体可以调用以下工具来完成任务：

| 工具名称 | 功能描述 |
|---------|---------|
| `read_file` | 读取文件内容（支持分页、head/tail） |
| `write_file` | 写入或追加文件 |
| `list_files` | 列出目录内容 |
| `web` | 访问网页、获取标题/文本/链接 |
| `memory` | 保存、搜索（支持分页）、删除记忆 |
| `memo` | 创建、查看、完成、搜索任务 |
| `run_command` | 执行系统命令（实时输出，支持超时控制） |
| `search_skills` | 搜索扩展技能（支持Markdown和可执行技能） |
| `reload_skills` | 热重载扩展技能 |
| `create_skill` | 创建新技能（AI自主编写Python脚本） |
| `install_skill` | 技能安装指引 |
| `update_identity` | 更新用户身份信息 |
| `update_soul` | 更新AI自我定义（智能体进化） |
| `save_memory_and_end_conversation` | 保存记忆并结束对话 |
| `get_current_time` | 获取当前时间 |
| `calculator` | 数学计算 |

## 💬 WebSocket API

### 连接

```javascript
const ws = new WebSocket('ws://localhost:8765');
```

### 发送消息格式

#### 1. 普通消息
```json
{
  "type": "message",
  "content": "你好，请帮我..."
}
```

#### 2. 命令
```json
{
  "type": "command",
  "command": "/new"
}
```

#### 3. 任务操作
```json
{
  "type": "task",
  "action": "add",
  "title": "提醒我喝水",
  "content": "下午3点喝水",
  "delay": 3600,
  "repeat_type": "daily",
  "is_immediate": false
}
```

#### 4. Ping
```json
{
  "type": "ping"
}
```

### 支持的命令

| 命令 | 功能 |
|-----|------|
| `/exit` | 退出连接 |
| `/new` | 开始新对话（保存当前，重置AI记忆，重新加载提示词） |
| `/list` | 列出所有历史对话 |
| `/memories` | 查看最近记忆（支持分页） |
| `/memos` | 查看待办任务 |
| `/search <关键词>` | 搜索记忆 |
| `/config` | 查看配置 |
| `/reload` | 重载配置 |
| `/reload_prompts` | 重载提示词 |
| `/check` | 检查过期任务 |
| `/tasks` | 查看任务调度器状态 |
| `/help` | 显示帮助 |

### 接收消息类型

| 类型 | 说明 |
|-----|------|
| `chunk` | AI响应的片段（流式输出） |
| `complete` | AI响应完成 |
| `reasoning` | AI思考过程（调试模式） |
| `error` | 错误信息 |
| `command_result` | 命令执行结果 |
| `task_status` | 任务状态更新（executing/complete/failed） |
| `task_process` | 任务执行过程中的AI输出 |
| `dialogue_ended` | 对话结束通知 |
| `dialogue_reset` | 对话重置完成 |
| `info` | 系统信息 |
| `pong` | Ping响应 |

## ⏰ 任务系统

### 任务类型

1. **一次性任务**：在指定时间执行一次
2. **重复任务**：
   - `daily`：每天执行
   - `weekly`：每周执行
   - `monthly`：每月执行
   - `custom`：自定义间隔（分钟/小时/天）
3. **即时任务**：立即执行（`is_immediate: true`）

### 添加任务示例

```json
// 每天提醒
{
  "type": "task",
  "action": "add",
  "title": "每日健康提醒",
  "repeat_type": "daily"
}
```

```json
// 5分钟后执行
{
  "type": "task",
  "action": "add",
  "title": "5分钟后提醒",
  "delay": 300
}
```

```json
// 每30分钟重复
{
  "type": "task",
  "action": "add",
  "title": "定时检查",
  "repeat_type": "custom",
  "repeat_interval": 30,
  "repeat_interval_unit": "minutes"
}
```

```json
// 即时任务
{
  "type": "task",
  "action": "add",
  "title": "检查服务器状态",
  "is_immediate": true
}
```

### 任务执行流程

1. 任务到期后，系统自动标记为已触发
2. 创建新的AI对话，将任务内容作为用户输入
3. AI处理任务，使用工具执行操作
4. 任务执行结果实时广播到所有WebSocket客户端
5. 重复任务自动计算下一次执行时间

## 🔧 扩展技能

### 技能类型

#### 1. 可执行技能
- 放在 `~/.aibox/skills/` 目录
- 文件必须可执行（`chmod +x`）
- 支持 `--help` 选项
- `--help` 第一行为一句话简介，其余为使用说明

**示例**：
```python
#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="温度转换工具 - 摄氏度转华氏度"
    )
    parser.add_argument("-t", "--temp", type=float, required=True,
                       help="摄氏温度值")
    args = parser.parse_args()
    
    fahrenheit = args.temp * 9/5 + 32
    print(f"{args.temp}°C = {fahrenheit:.1f}°F")

if __name__ == "__main__":
    main()
```

#### 2. Markdown技能
- 文件以 `.md` 结尾
- 第一行为简介（`# 标题` 或纯文本）
- 其余为完整的技能内容

**示例**：
```markdown
# 代码审查指南
提供代码审查的检查清单和最佳实践...

## 检查要点
1. 代码风格一致性
2. 性能优化建议
3. 安全漏洞检查
4. 可维护性评估
```

### 创建技能

#### 方式1：AI自主创建（推荐）
直接告诉AI：
```
创建一个技能，功能是将摄氏度转换为华氏度，接受 -c 参数输入温度
```
AI会自动使用 `create_skill` 工具编写脚本并部署。

#### 方式2：手动创建
1. 编写脚本，确保支持 `--help`
2. 复制到 `~/.aibox/skills/` 并去掉扩展名
3. 添加可执行权限
4. 调用 `reload_skills` 工具

```bash
cp my_skill.py ~/.aibox/skills/my_skill
chmod +x ~/.aibox/skills/my_skill
```

#### 方式3：使用安装指引
```json
{
  "type": "message",
  "content": "使用 install_skill 工具安装 /path/to/script.py"
}
```

## 🧠 智能体自我进化

AI可以通过 `update_soul` 工具动态更新 `99_SOUL.md` 文件：

```json
{
  "type": "message",
  "content": "使用 update_soul 更新我的角色，强调我更注重创造性思维"
}
```

这允许AI在对话中不断优化自己的：
- 角色定位
- 性格特点
- 能力边界
- 行为准则
- 价值观

## 📦 对话压缩

当对话达到阈值时自动压缩：

```json
// 配置示例
"context": {
  "max_history_messages": 500,
  "compress_enabled": true,
  "compress_message_threshold": 200,    // 消息数阈值
  "compress_token_threshold": 120000,   // Token数阈值
  "compress_keep_recent": 8             // 保留最近消息数
}
```

压缩过程：
1. 检测到消息数或Token数超过阈值
2. 调用AI压缩早期对话内容
3. 保留最近的重要消息
4. 将压缩摘要作为系统消息
5. 压缩过程静默执行，不影响用户体验

## 🧩 提示词系统

提示词文件位于 `~/.aibox/prompts/`：

| 文件 | 用途 | 更新方式 |
|-----|------|---------|
| `00_IDENTITY.md` | 用户身份信息 | AI通过 `update_identity` 工具更新 |
| `1_*.md` | 基础技能提示词 | 手动编辑，AI通过 `reload_prompts` 重载 |
| `99_SOUL.md` | AI灵魂定义（角色、性格） | AI通过 `update_soul` 工具更新 |
| `100_STATUS.md` | AI状态记录 | AI通过 `save_memory_and_end_conversation` 更新 |

## ⚙️ 配置说明

主要配置项（`~/.aibox/config.json`）：

```json
{
  "system": {
    "save_dir": "~/.aibox",
    "websocket_host": "localhost",
    "websocket_port": 8765,
    "debug_level": 1,
    "log_file": "~/.aibox/ai.log"
  },
  "context": {
    "max_history_messages": 500,
    "compress_enabled": true,
    "compress_message_threshold": 200,
    "compress_token_threshold": 120000,
    "compress_keep_recent": 8
  },
  "scheduler": {
    "enabled": true,
    "check_interval": 1.0,
    "max_tasks_per_run": 10
  },
  "api": {
    "deepseek_api_url": "https://api.deepseek.com/chat/completions",
    "deepseek_model": "deepseek-chat",
    "api_key_env": "DEEPSEEK_API_KEY"
  },
  "memory": {
    "max_search_results": 100
  },
  "tools": {
    "max_result_length": 10000
  }
}
```

## 🛠️ 命令行参数

```bash
python agent.py [选项]

选项:
  --verbose, -v         显示详细日志
  --debug LEVEL         调试级别 (0-3)
  --lang zh|en          强制语言
  --host HOST           WebSocket主机
  --port PORT           WebSocket端口
  --no-scheduler        禁用任务调度器
  --scheduler-interval  调度器检查间隔（秒）
  --config PATH         指定配置文件路径
  --check-memo          检查到期任务并退出
  --memo-add "标题|内容|时间"  添加任务
  --memo-list           列出任务
  --memo-complete ID    完成任务
```

### 使用示例

```bash
# 启动服务器（详细日志）
python agent.py --verbose

# 指定端口
python agent.py --port 9000

# 检查任务
python agent.py --check-memo

# 添加任务（命令行）
python agent.py --memo-add "提醒开会|下午3点会议室A|+1h"

# 查看所有任务
python agent.py --memo-list
```

## 🔄 架构流程

```
┌─────────────────────────────────────────────────────────┐
│                    WebSocket 客户端                      │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              WebSocket 服务器 (端口 8765)               │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │  消息处理器  │  │  命令处理器  │  │  任务调度器   │  │
│  └─────────────┘  └─────────────┘  └───────────────┘  │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│                  AI 对话引擎 (DeepSeek)                  │
├─────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌──────────────────┐   │
│  │ 提示词管理器│  │ 工具注册器 │  │  对话压缩器      │   │
│  └───────────┘  └───────────┘  └──────────────────┘   │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│                   数据持久层                            │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐   │
│  │ 记忆数据库 │  │ 备忘录DB  │  │  对话历史管理器    │   │
│  └──────────┘  └──────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 📊 消息流示例

### 普通对话流程
```
Client -> Server: {type: "message", content: "帮我查天气"}
Server -> Client: {type: "chunk", content: "正在查"}
Server -> Client: {type: "chunk", content: "询天气..."}
Server -> Client: {type: "tool_call", tool: "search_skills", args: {keyword: "天气"}}
Server -> Client: {type: "chunk", content: "今日天气晴朗..."}
Server -> Client: {type: "complete", content: "今日天气晴朗，温度25°C"}
```

### 任务执行流程
```
Client -> Server: {type: "task", action: "add", title: "提醒", delay: 60}
Server -> Client: {type: "task_added", task_id: 1}

... 60秒后 ...

Server -> Client: {type: "task_status", task_id: 1, status: "executing"}
Server -> Client: {type: "task_process", task_id: "1", content: "处理中..."}
Server -> Client: {type: "task_status", task_id: 1, status: "complete"}
```

### 对话重置流程
```
Client -> Server: {type: "command", command: "/new"}
Server -> Client: {type: "command_result", content: "🔄 开始新对话..."}
Server -> Client: {type: "dialogue_reset", content: "✅ 对话状态已完全重置"}
```

## ❓ 常见问题

### Q: API Key无效怎么办？
**A:** 
1. 确认环境变量已设置：`echo $DEEPSEEK_API_KEY`
2. 检查配置文件中的 `api_key_env` 设置
3. 创建 `~/.cert/deepseek.key` 文件并写入API Key

### Q: 技能不生效？
**A:** 
1. 确认文件在 `~/.aibox/skills/` 目录
2. 确认文件可执行（`chmod +x`）
3. 调用 `reload_skills` 工具
4. 使用 `search_skills` 验证
5. 检查文件命名（不能有扩展名）

### Q: 任务没有执行？
**A:** 
1. 检查调度器是否启用：`/tasks`
2. 查看任务状态：`/memos`
3. 检查系统时间是否正确
4. 查看日志：`tail -f ~/.aibox/ai.log`
5. 确认任务有 `reminder_time`

### Q: 对话压缩丢失了重要信息？
**A:** 调整配置：
```json
"compress_message_threshold": 300,  // 调大阈值
"compress_keep_recent": 20          // 保留更多最近消息
```

### Q: 如何备份数据？
**A:** 
```bash
# 备份整个目录
tar -czf aibox_backup_$(date +%Y%m%d).tar.gz ~/.aibox/

# 恢复
tar -xzf aibox_backup_20260101.tar.gz -C ~/
```

### Q: WebSocket连接断开？
**A:** 
1. 检查服务器是否运行：`ps aux | grep agent.py`
2. 确认端口未被占用：`netstat -tlnp | grep 8765`
3. 检查防火墙设置
4. 查看服务器日志
5. 考虑使用 `--host 0.0.0.0` 允许外部连接

### Q: 如何让AI使用特定技能？
**A:** 在对话中明确指示：
```
使用 search_skills 搜索天气相关技能，然后用 run_command 执行它
```

### Q: 内存或日志占用过大？
**A:** 
1. 调整日志配置：
```json
"log_max_size": 5242880,   // 5MB
"log_backup_count": 3
```
2. 清理旧对话归档
3. 定期清理工具结果缓存

## 📄 更新日志

### v2.0 (当前版本)
- ✅ 新增 `update_soul` 工具（智能体自我进化）
- ✅ 新增 `create_skill` 工具（AI自主创建技能）
- ✅ 新增 `install_skill` 工具（技能安装指引）
- ✅ 新增 `task_process` 消息类型（任务执行过程广播）
- ✅ 支持Markdown格式技能文件
- ✅ 对话压缩支持Token数阈值判断
- ✅ 开始新对话时完全重置AI状态并重新加载提示词
- ✅ 智能体主动结束对话后重置状态
- ✅ 任务执行时显示AI完整处理过程
- ✅ 增强的流式输出支持（思考内容显示）
- ✅ 技能热重载支持（`reload_skills`）
- ✅ 记忆搜索支持分页
- ✅ 任务调度器支持即时任务
- ✅ 命令执行支持超时控制

### v1.0
- ✅ WebSocket服务器支持
- ✅ 文件操作、网页访问、记忆管理
- ✅ 任务调度系统
- ✅ 扩展技能支持
- ✅ 多语言支持
- ✅ 对话管理

## 📝 开发指南

### 添加新工具

1. 继承 `Tool` 基类
2. 实现 `get_name()`, `get_description()`, `get_parameters()`, `execute()`
3. 可选实现 `execute_streaming()` 支持流式输出
4. 在 `DeepSeekChat._register_tools()` 中注册

```python
class MyTool(Tool):
    def get_name(self) -> str:
        return "my_tool"
    
    def get_description(self) -> str:
        return "我的自定义工具"
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "param": {"type": "string"}
            },
            "required": ["param"]
        }
    
    def execute(self, param: str, **kwargs) -> str:
        return f"执行结果: {param}"
```

### 添加新命令

在 `WebSocketHandler.handle_command()` 中添加：

```python
elif command == "/mycommand":
    result = "命令执行结果"
    await self.send_message(websocket, {
        "type": "command_result",
        "content": result
    })
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

---

**注意**：本项目需要DeepSeek API Key，请确保遵守API使用条款。