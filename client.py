#!/usr/bin/env python3
"""
AI智能助手 - Python命令行前端
支持WebSocket直连、流式消息、命令系统和定时任务
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
import websockets
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from colorama import init, Fore, Style as ColoramaStyle
import threading
import queue

# 初始化colorama
init(autoreset=True)

class Colors:
    """终端颜色定义"""
    USER = Fore.CYAN
    AI = Fore.GREEN
    TASK = Fore.YELLOW
    SYSTEM = Fore.BLUE
    ERROR = Fore.RED
    INFO = Fore.MAGENTA
    RESET = ColoramaStyle.RESET_ALL
    BOLD = ColoramaStyle.BRIGHT

class StreamingMessage:
    """流式消息管理器"""
    def __init__(self):
        self.content = ""
        self.is_active = False
        self.last_update = datetime.now()
    
    def add_chunk(self, chunk: str):
        self.content += chunk
        self.is_active = True
        self.last_update = datetime.now()
    
    def get_content(self) -> str:
        return self.content
    
    def clear(self):
        self.content = ""
        self.is_active = False

class WebSocketClient:
    """WebSocket客户端管理"""
    def __init__(self, uri: str):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.message_queue = asyncio.Queue()
        self.streaming_messages: Dict[str, StreamingMessage] = {
            'chat': StreamingMessage(),
            'tasks': {}
        }
        self.running = True
        
    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            return True
        except Exception as e:
            print(f"{Colors.ERROR}❌ 连接失败: {e}{Colors.RESET}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
    
    async def send_message(self, message: str):
        """发送消息"""
        if not self.websocket or not self.connected:
            print(f"{Colors.ERROR}❌ 未连接到服务器{Colors.RESET}")
            return False
        
        try:
            # 判断消息类型
            if message.startswith('/'):
                data = {
                    'type': 'command',
                    'command': message
                }
            else:
                data = {
                    'type': 'message',
                    'content': message
                }
            
            await self.websocket.send(json.dumps(data))
            return True
        except Exception as e:
            print(f"{Colors.ERROR}❌ 发送失败: {e}{Colors.RESET}")
            return False
    
    async def receive_messages(self):
        """接收消息的异步任务"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    # 如果不是JSON，当作流式文本处理
                    await self.handle_stream_chunk(message, 'chat')
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            print(f"\n{Colors.ERROR}❌ 连接已断开{Colors.RESET}")
        except Exception as e:
            print(f"\n{Colors.ERROR}❌ 接收消息错误: {e}{Colors.RESET}")
    
    async def handle_message(self, data: dict):
        """处理接收到的消息"""
        msg_type = data.get('type', '')
        content = data.get('content', '')
        
        if msg_type == 'chunk':
            await self.handle_stream_chunk(content, 'chat')
        
        elif msg_type == 'complete':
            await self.handle_stream_complete('chat')
        
        elif msg_type == 'dialogue_ended':
            await self.handle_dialogue_ended()
        
        elif msg_type == 'task_process':
            msg_subtype = data.get('msg_type', '')
            task_content = data.get('content', '')
            task_id = data.get('task_id', 'unknown')
            execution_id = data.get('execution_id', 'unknown')
            task_title = data.get('task_title', '未知任务')
            
            if msg_subtype == 'chunk':
                await self.handle_stream_chunk(
                    task_content, 
                    'task',
                    task_info={'task_id': task_id, 'execution_id': execution_id, 'title': task_title}
                )
            elif msg_subtype == 'complete':
                await self.handle_stream_complete('task', execution_id)
        
        elif msg_type == 'task_status':
            task_id = data.get('task_id', 'unknown')
            title = data.get('title', '未知')
            status = data.get('status', 'unknown')
            message = data.get('message', content)
            
            status_icon = {
                'executing': '⚙️',
                'complete': '✅',
                'failed': '❌',
                'added': '➕',
                'batch_start': '🚀',
                'batch_complete': '🏁'
            }.get(status, '📋')
            
            print(f"{Colors.TASK}{status_icon} [任务 {task_id}] {title}: {message}{Colors.RESET}")
        
        elif msg_type == 'task_error':
            task_id = data.get('task_id', 'unknown')
            execution_id = data.get('execution_id', 'unknown')
            task_title = data.get('task_title', '未知')
            error = data.get('error', '未知错误')
            
            print(f"{Colors.ERROR}❌ [任务 {task_id}] {task_title}: {error}{Colors.RESET}")
            
            if execution_id:
                await self.handle_stream_complete('task', execution_id)
        
        elif msg_type == 'error':
            print(f"{Colors.ERROR}❌ {content}{Colors.RESET}")
        
        elif msg_type == 'info':
            print(f"{Colors.INFO}ℹ️  {content}{Colors.RESET}")
        
        elif msg_type == 'command_result':
            print(f"{Colors.SYSTEM}📋 {content}{Colors.RESET}")
        
        elif msg_type == 'connection_ack':
            print(f"{Colors.AI}✅ {content}{Colors.RESET}")
        
        elif msg_type == 'notification':
            print(f"{Colors.INFO}🔔 {content}{Colors.RESET}")
        
        else:
            if content:
                await self.handle_stream_chunk(content, 'chat')
    
    async def handle_stream_chunk(self, content: str, msg_type: str = 'chat', task_info: dict = None):
        """处理流式消息块"""
        if msg_type == 'chat':
            stream = self.streaming_messages['chat']
            stream.add_chunk(content)
            
            # 实时输出流式内容
            if not stream.is_active:
                print(f"\n{Colors.AI}🤖 AI助手: ", end='', flush=True)
                stream.is_active = True
            
            print(content, end='', flush=True)
        
        elif msg_type == 'task' and task_info:
            execution_id = task_info.get('execution_id', 'unknown')
            task_id = task_info.get('task_id', 'unknown')
            title = task_info.get('title', '未知任务')
            
            if execution_id not in self.streaming_messages['tasks']:
                self.streaming_messages['tasks'][execution_id] = StreamingMessage()
                print(f"\n{Colors.TASK}⚡ 定时任务 #{task_id} - {title}{Colors.RESET}")
                print(f"{Colors.TASK}📋 ", end='', flush=True)
            
            stream = self.streaming_messages['tasks'][execution_id]
            stream.add_chunk(content)
            print(content, end='', flush=True)
    
    async def handle_stream_complete(self, msg_type: str = 'chat', execution_id: str = None):
        """处理流式消息完成"""
        if msg_type == 'chat':
            stream = self.streaming_messages['chat']
            print()  # 换行
            stream.clear()
        
        elif msg_type == 'task' and execution_id:
            if execution_id in self.streaming_messages['tasks']:
                print()  # 换行
                del self.streaming_messages['tasks'][execution_id]
    
    async def handle_dialogue_ended(self):
        """处理对话结束"""
        print(f"\n{Colors.SYSTEM}✅ 对话已结束，可以开始新对话{Colors.RESET}")
        self.streaming_messages['chat'].clear()
        self.streaming_messages['tasks'].clear()

class CommandLineInterface:
    """命令行界面管理"""
    def __init__(self):
        self.client: Optional[WebSocketClient] = None
        self.console = Console()
        self.history = InMemoryHistory()
        self.style = Style.from_dict({
            'prompt': 'ansicyan bold',
            '': 'ansigreen',
        })
        
        self.commands = {
            '/help': '显示帮助信息',
            '/connect': '连接到服务器 (用法: /connect ws://host:port)',
            '/disconnect': '断开连接',
            '/quit': '退出程序',
            '/clear': '清屏',
            '/status': '显示连接状态',
            '/list': '列出可用命令',
            '/memories': '查看记忆',
            '/memos': '查看备忘录',
            '/check': '检查提醒',
            '/config': '查看配置',
            '/new': '新建对话',
            '/tasks': '查看任务列表',
        }
    
    def print_banner(self):
        """打印欢迎横幅"""
        banner = f"""
{Colors.BOLD}{Colors.AI}
╔══════════════════════════════════════════╗
║         AI智能助手 - 命令行前端           ║
║         WebSocket 直连版本                ║
╚══════════════════════════════════════════╝
{Colors.RESET}
"""
        print(banner)
        print(f"{Colors.INFO}输入 /help 查看可用命令")
        print(f"输入 /connect ws://localhost:8765 连接到服务器{Colors.RESET}")
        print()
    
    async def handle_command(self, command: str):
        """处理本地命令"""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == '/help':
            self.show_help()
        
        elif cmd == '/connect':
            if len(parts) < 2:
                print(f"{Colors.ERROR}用法: /connect ws://host:port{Colors.RESET}")
                return
            
            uri = parts[1]
            if self.client and self.client.connected:
                await self.client.disconnect()
            
            self.client = WebSocketClient(uri)
            if await self.client.connect():
                print(f"{Colors.AI}✅ 已连接到 {uri}{Colors.RESET}")
                # 启动接收消息的任务
                asyncio.create_task(self.client.receive_messages())
            else:
                self.client = None
        
        elif cmd == '/disconnect':
            if self.client:
                await self.client.disconnect()
                self.client = None
                print(f"{Colors.SYSTEM}已断开连接{Colors.RESET}")
            else:
                print(f"{Colors.ERROR}未连接到服务器{Colors.RESET}")
        
        elif cmd == '/status':
            if self.client and self.client.connected:
                print(f"{Colors.AI}✅ 已连接: {self.client.uri}{Colors.RESET}")
            else:
                print(f"{Colors.SYSTEM}未连接{Colors.RESET}")
        
        elif cmd == '/clear':
            os.system('clear' if os.name == 'posix' else 'cls')
            self.print_banner()
        
        elif cmd == '/quit':
            print(f"{Colors.SYSTEM}再见！{Colors.RESET}")
            if self.client:
                await self.client.disconnect()
            sys.exit(0)
        
        elif cmd in self.commands:
            # 发送到服务器的命令
            if self.client and self.client.connected:
                await self.client.send_message(command)
            else:
                print(f"{Colors.ERROR}未连接到服务器，请先使用 /connect 连接{Colors.RESET}")
        
        else:
            print(f"{Colors.ERROR}未知命令: {cmd}{Colors.RESET}")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = f"""
{Colors.BOLD}可用命令:{Colors.RESET}

{Colors.USER}本地命令:{Colors.RESET}
  /connect <url>    连接到WebSocket服务器
  /disconnect       断开连接
  /status           显示连接状态
  /clear            清屏
  /quit             退出程序
  /help             显示此帮助

{Colors.AI}服务器命令 (需要先连接):{Colors.RESET}
"""
        for cmd, desc in self.commands.items():
            if cmd not in ['/help', '/connect', '/disconnect', '/quit', '/clear', '/status']:
                help_text += f"  {cmd:<15} {desc}\n"
        
        print(help_text)
    
    async def send_user_message(self, message: str):
        """发送用户消息"""
        if not self.client or not self.client.connected:
            print(f"{Colors.ERROR}❌ 未连接到服务器{Colors.RESET}")
            return
        
        print(f"\n{Colors.USER}👤 用户: {message}{Colors.RESET}")
        await self.client.send_message(message)
    
    async def run(self):
        """运行命令行界面"""
        self.print_banner()

        # 使用prompt_toolkit创建交互式会话
        session = PromptSession(
            history=self.history,
            auto_suggest=AutoSuggestFromHistory(),
            style=self.style,
        )

        while True:
            try:
                # 获取用户输入（使用prompt_toolkit的样式，不使用colorama颜色代码）
                user_input = await session.prompt_async(
                    ">>> ",
                    multiline=False,
                )

                user_input = user_input.strip()
                if not user_input:
                    continue

                # 判断是命令还是消息
                if user_input.startswith('/'):
                    await self.handle_command(user_input)
                else:
                    await self.send_user_message(user_input)

            except KeyboardInterrupt:
                continue
            except EOFError:
                print(f"\n{Colors.SYSTEM}再见！{Colors.RESET}")
                if self.client:
                    await self.client.disconnect()
                break
            except Exception as e:
                print(f"{Colors.ERROR}错误: {e}{Colors.RESET}")

async def main():
    """主函数"""
    cli = CommandLineInterface()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 如果提供了WebSocket URL，自动连接
        uri = sys.argv[1]
        cli.client = WebSocketClient(uri)
        if await cli.client.connect():
            print(f"{Colors.AI}✅ 已连接到 {uri}{Colors.RESET}")
            asyncio.create_task(cli.client.receive_messages())
        else:
            print(f"{Colors.ERROR}无法连接到 {uri}{Colors.RESET}")
            return
    
    await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.SYSTEM}程序已退出{Colors.RESET}")