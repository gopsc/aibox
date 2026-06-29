#!/usr/bin/env python3
"""
AI智能助手 - 命令行前端
"""

import asyncio
import json
import sys
import os
import threading
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
import websockets
from colorama import init, Fore, Style as ColoramaStyle

init(autoreset=True)

class Colors:
    USER = Fore.CYAN
    AI = Fore.GREEN
    TASK = Fore.YELLOW
    SYSTEM = Fore.BLUE
    ERROR = Fore.RED
    INFO = Fore.MAGENTA
    RESET = ColoramaStyle.RESET_ALL
    BOLD = ColoramaStyle.BRIGHT
    
    GREEN = Fore.GREEN
    RED = Fore.RED

class WebSocketClient:
    def __init__(self, uri: str, callback):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.callback = callback
        
    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            return True
        except Exception as e:
            self.callback("error", f"连接失败: {e}")
            return False
    
    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            self.connected = False
    
    async def send_message(self, message: str):
        if not self.websocket or not self.connected:
            return False
        
        try:
            if message.startswith('/'):
                data = {'type': 'command', 'command': message}
            else:
                data = {'type': 'message', 'content': message}
            
            await self.websocket.send(json.dumps(data))
            return True
        except Exception as e:
            self.callback("error", f"发送失败: {e}")
            return False
    
    async def receive_messages(self):
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    self.callback("chunk", message)
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            self.callback("system", "❌ 连接已断开")
        except Exception as e:
            self.callback("error", f"接收消息错误: {e}")
    
    async def _handle_message(self, data: dict):
        msg_type = data.get('type', '')
        content = data.get('content', '')
        
        if msg_type == 'chunk':
            self.callback("chunk", content)
        elif msg_type == 'complete':
            self.callback("complete", content)
        elif msg_type == 'dialogue_ended':
            self.callback("dialogue_ended", content)
        elif msg_type == 'task_process':
            msg_subtype = data.get('msg_type', '')
            task_content = data.get('content', '')
            task_title = data.get('task_title', '未知任务')
            if msg_subtype == 'chunk':
                self.callback("task_chunk", task_content, task_title)
            elif msg_subtype == 'complete':
                self.callback("task_complete", task_title)
        elif msg_type == 'task_status':
            task_id = data.get('task_id', 'unknown')
            title = data.get('title', '未知')
            status = data.get('status', 'unknown')
            message = data.get('message', content)
            status_icon = {'executing': '⚙️', 'complete': '✅', 'failed': '❌', 'added': '➕', 'batch_start': '🚀', 'batch_complete': '🏁'}.get(status, '📋')
            self.callback("info", f"{status_icon} [任务 {task_id}] {title}: {message}")
        elif msg_type == 'task_error':
            self.callback("error", f"[任务 {data.get('task_id', 'unknown')}] {data.get('task_title', '未知')}: {data.get('error', '未知错误')}")
        elif msg_type == 'interrupt_ack':
            self.callback("info", f"🛑 {content}")
        elif msg_type == 'error':
            self.callback("error", content)
        elif msg_type == 'info':
            self.callback("info", content)
        elif msg_type == 'command_result':
            self.callback("system", content)
        elif msg_type == 'connection_ack':
            self.callback("system", f"✅ {content}")
        elif msg_type == 'notification':
            self.callback("info", f"🔔 {content}")
        else:
            if content:
                self.callback("chunk", content)

class SimpleCLI:
    def __init__(self):
        self.client: Optional[WebSocketClient] = None
        self.connected = False
        self.running = True
        
        # AI消息缓冲
        self.ai_previous = ""
        self.ai_full = ""
        self.ai_prefix_shown = False
        
        # 已显示消息的去重
        self.displayed_messages: set = set()
        
        # 锁和状态
        self.lock = threading.Lock()
        self.current_input = ""
        
        # 流式输出状态
        self.streaming_line = False  # 是否正在流式输出行
        self.in_tool_phase = False  # 是否在工具调用阶段
        self.waiting_for_response = False  # 是否在等待AI响应
        self.prompt_shown = True  # 提示符是否已显示
        
        # 命令列表
        self.commands = {
            '/help': '显示帮助信息',
            '/connect': '连接到服务器',
            '/disconnect': '断开连接',
            '/quit': '退出程序',
            '/clear': '清屏',
            '/status': '显示连接状态',
            '/interrupt': '发送中断信号（或按 Ctrl+C）',
        }
    
    def _get_prompt(self) -> str:
        status = "● 已连接" if self.connected else "○ 未连接"
        color = Colors.GREEN if self.connected else Colors.RED
        return f"{color}{status}{Colors.RESET} >>> "
    
    def _print_line(self, line: str = "", end: str = "\n"):
        """打印一行，并恢复提示符"""
        with self.lock:
            current = self.current_input
            sys.stdout.write('\r' + ' ' * 120 + '\r')
            sys.stdout.write(line + end)
            sys.stdout.flush()
            if not self.waiting_for_response and not self.in_tool_phase:
                sys.stdout.write(self._get_prompt() + current)
                sys.stdout.flush()
                self.prompt_shown = True
            self.streaming_line = False
    
    def _print_prompt(self, clear_input: bool = False):
        """显示提示符"""
        with self.lock:
            if clear_input:
                self.current_input = ""
            self.waiting_for_response = False
            self.in_tool_phase = False
            self.prompt_shown = True
            sys.stdout.write('\r' + ' ' * 120 + '\r')
            sys.stdout.write(self._get_prompt() + self.current_input)
            sys.stdout.flush()
            self.streaming_line = False
    
    def _print_stream(self, text: str):
        """流式打印文本（不换行，不显示提示符）"""
        with self.lock:
            # 保存当前输入
            current = self.current_input
            
            if not self.streaming_line:
                # 首次流式输出，先换行再打印前缀
                sys.stdout.write('\n')
                sys.stdout.write(f"{Colors.AI}🤖 AI助手: ")
                self.streaming_line = True
                self.prompt_shown = False
            
            # 打印文本
            sys.stdout.write(text)
            sys.stdout.flush()
            
            # 注意：不恢复提示符，保持在同一行
    
    def _finish_stream(self):
        """完成流式输出，换行并恢复提示符"""
        with self.lock:
            if self.streaming_line:
                sys.stdout.write('\n')
                self.streaming_line = False
            if not self.in_tool_phase and not self.waiting_for_response:
                current = self.current_input
                sys.stdout.write(self._get_prompt() + current)
                sys.stdout.flush()
                self.prompt_shown = True
    
    def _clean_content(self, content: str) -> str:
        if not content:
            return ""
        if '💬 助手:' in content:
            content = content.split('💬 助手:', 1)[1].strip()
        content = content.lstrip()
        return content
    
    def _show_streaming(self, content: str):
        """流式显示增量内容"""
        if not content:
            return
        
        # 清理内容
        clean = self._clean_content(content)
        if not clean:
            return
        
        key = clean[:200]
        if key in self.displayed_messages:
            return
        
        # 检测增量
        if self.ai_previous and clean.startswith(self.ai_previous):
            new_part = clean[len(self.ai_previous):]
            if new_part:
                # 如果是首次流式输出，显示前缀
                if not self.ai_prefix_shown:
                    self._print_stream("")
                    self.ai_prefix_shown = True
                self._print_stream(new_part)
                self.ai_previous = clean
                self.ai_full = clean
            return
        
        if self.ai_previous and self.ai_previous in clean:
            idx = clean.find(self.ai_previous) + len(self.ai_previous)
            new_part = clean[idx:]
            if new_part:
                if not self.ai_prefix_shown:
                    self._print_stream("")
                    self.ai_prefix_shown = True
                self._print_stream(new_part)
                self.ai_previous = clean
                self.ai_full = clean
            return
        
        # 全新内容 - 显示前缀和内容
        if not self.ai_prefix_shown:
            self._print_stream("")
            self.ai_prefix_shown = True
        self._print_stream(clean)
        self.ai_previous = clean
        self.ai_full = clean
    
    def display(self, msg_type: str, content: str, extra: Any = None):
        """显示消息"""
        if msg_type == 'chunk':
            self._handle_chunk(content)
        elif msg_type == 'complete':
            self._handle_complete(content)
        elif msg_type == 'task_chunk':
            self._handle_task_chunk(content, extra)
        elif msg_type == 'task_complete':
            self._handle_task_complete(extra)
        elif msg_type == 'dialogue_ended':
            with self.lock:
                if self.streaming_line:
                    sys.stdout.write('\n')
                    self.streaming_line = False
                self.in_tool_phase = False
                self.waiting_for_response = False
                self.prompt_shown = True
            self._print_line(f"{Colors.SYSTEM}✅ {content}{Colors.RESET}")
            self.ai_previous = ""
            self.ai_full = ""
            self.ai_prefix_shown = False
            self.displayed_messages.clear()
            self.streaming_line = False
        elif msg_type == 'system':
            self._finish_stream()
            self._print_line(f"{Colors.SYSTEM}{content}{Colors.RESET}")
        elif msg_type == 'info':
            self._finish_stream()
            self._print_line(f"{Colors.INFO}ℹ️  {content}{Colors.RESET}")
        elif msg_type == 'error':
            self._finish_stream()
            self._print_line(f"{Colors.ERROR}❌ {content}{Colors.RESET}")
    
    def _handle_chunk(self, content: str):
        """处理流式块"""
        # 检查是否是工具调用相关的消息
        if content.startswith('🔧 调用工具'):
            with self.lock:
                self.in_tool_phase = True
                self.prompt_shown = False
                # 打印工具调用信息
                if self.streaming_line:
                    sys.stdout.write('\n')
                    self.streaming_line = False
                sys.stdout.write(f"{Colors.TASK}{content}{Colors.RESET}\n")
                sys.stdout.flush()
            return
        
        # 检查是否是工具结果
        if content.startswith(('✅ 对话记忆已保存', '💾 保存记忆', '❌', '⚠️')):
            with self.lock:
                # 打印工具结果
                sys.stdout.write(f"{Colors.TASK}{content}{Colors.RESET}\n")
                sys.stdout.flush()
            return
        
        # 如果之前在工具阶段，现在退出工具阶段
        if self.in_tool_phase:
            with self.lock:
                self.in_tool_phase = False
                # 工具结束后不立即显示提示符，等待AI继续响应
                self.prompt_shown = False
        
        # 系统消息
        if content.startswith(('📩', '[', '📁', '🔧', '📝', '✅', 'ℹ️', '⏰')):
            self._finish_stream()
            self._print_line(f"{Colors.INFO}{content}{Colors.RESET}")
            return
        
        # 流式显示
        self._show_streaming(content)
    
    def _handle_complete(self, content: str):
        """处理完成事件 - 只负责结束流式输出，不重复显示内容"""
        # 如果之前在工具阶段，现在退出
        if self.in_tool_phase:
            with self.lock:
                self.in_tool_phase = False
                self.waiting_for_response = False
                self.prompt_shown = True
                current = self.current_input
                sys.stdout.write(self._get_prompt() + current)
                sys.stdout.flush()
            self.ai_previous = ""
            self.ai_full = ""
            self.ai_prefix_shown = False
            self.streaming_line = False
            return
        
        # 如果流式输出正在进行，结束它
        if self.streaming_line:
            self._finish_stream()
        
        # 如果内容不为空，检查是否已经通过流式显示了
        if content and content.strip():
            clean = self._clean_content(content)
            if clean:
                # 检查是否已通过流式显示
                if self.ai_full and (clean in self.ai_full or self.ai_full in clean):
                    # 已经流式显示过了，不重复打印
                    self.ai_previous = ""
                    self.ai_full = ""
                    self.ai_prefix_shown = False
                    self.streaming_line = False
                    # 确保提示符显示
                    with self.lock:
                        self.waiting_for_response = False
                        self.prompt_shown = True
                        current = self.current_input
                        sys.stdout.write(self._get_prompt() + current)
                        sys.stdout.flush()
                    return
                
                # 检查是否已经在 displayed_messages 中
                key = clean[:200]
                if key in self.displayed_messages:
                    self.ai_previous = ""
                    self.ai_full = ""
                    self.ai_prefix_shown = False
                    self.streaming_line = False
                    # 确保提示符显示
                    with self.lock:
                        self.waiting_for_response = False
                        self.prompt_shown = True
                        current = self.current_input
                        sys.stdout.write(self._get_prompt() + current)
                        sys.stdout.flush()
                    return
                
                # 只有当内容没有被流式显示时才显示完整消息
                self.displayed_messages.add(key)
                # 如果之前没有流式输出，现在显示完整消息
                self._print_line(f"{Colors.AI}🤖 AI助手: {clean}")
        
        # 重置状态
        self.ai_previous = ""
        self.ai_full = ""
        self.ai_prefix_shown = False
        self.streaming_line = False
        self.waiting_for_response = False
        # 确保提示符显示
        with self.lock:
            self.prompt_shown = True
            current = self.current_input
            sys.stdout.write('\r' + ' ' * 120 + '\r')
            sys.stdout.write(self._get_prompt() + current)
            sys.stdout.flush()
    
    def _handle_task_chunk(self, content: str, task_title: str):
        """处理任务流式块"""
        if not hasattr(self, '_task_buffers'):
            self._task_buffers = {}
        
        if task_title not in self._task_buffers:
            self._task_buffers[task_title] = ""
            self._finish_stream()
            self._print_line(f"{Colors.TASK}⚡ 任务 - {task_title}: ", end="")
            self.streaming_line = True
        
        prev = self._task_buffers[task_title]
        if content.startswith(prev):
            new_part = content[len(prev):]
            if new_part:
                with self.lock:
                    sys.stdout.write(new_part)
                    sys.stdout.flush()
                self._task_buffers[task_title] = content
        elif prev in content:
            idx = content.find(prev) + len(prev)
            new_part = content[idx:]
            if new_part:
                with self.lock:
                    sys.stdout.write(new_part)
                    sys.stdout.flush()
                self._task_buffers[task_title] = content
        else:
            with self.lock:
                sys.stdout.write(content)
                sys.stdout.flush()
            self._task_buffers[task_title] = content
    
    def _handle_task_complete(self, task_title: str):
        """处理任务完成"""
        self._finish_stream()
        if hasattr(self, '_task_buffers') and task_title in self._task_buffers:
            content = self._task_buffers[task_title]
            if content:
                clean = content.strip()
                key = clean[:200]
                if key not in self.displayed_messages:
                    self.displayed_messages.add(key)
                    self._print_line(f"{Colors.TASK}⚡ 任务 - {task_title}: {clean}")
            del self._task_buffers[task_title]
        self.streaming_line = False
    
    def print_banner(self):
        banner = f"""
{Colors.BOLD}{Colors.AI}
╔══════════════════════════════════════════════════════════╗
║              AI智能助手 - 命令行前端                      ║
║              WebSocket 直连 + CTRL+C 中断                ║
╚══════════════════════════════════════════════════════════╝
{Colors.RESET}
"""
        self._print_line(banner)
        self._print_line(f"{Colors.INFO}📌 输入 /help 查看可用命令")
        self._print_line(f"{Colors.INFO}📌 按 Ctrl+C 发送中断信号 (而非退出)")
        self._print_line(f"{Colors.INFO}📌 按 Ctrl+D 退出程序{Colors.RESET}")
        self._print_line("")
        self._print_line("=" * 60)
        self._print_line("")
        self._print_prompt(clear_input=True)
    
    def show_help(self):
        self._print_line("")
        self._print_line(f"{Colors.BOLD}可用命令:{Colors.RESET}")
        self._print_line("")
        self._print_line(f"{Colors.USER}本地命令:{Colors.RESET}")
        self._print_line("  /connect <url>    连接到WebSocket服务器")
        self._print_line("  /disconnect       断开连接")
        self._print_line("  /status           显示连接状态")
        self._print_line("  /clear            清屏")
        self._print_line("  /interrupt        发送中断信号 (或按 Ctrl+C)")
        self._print_line("  /quit             退出程序 (或按 Ctrl+D)")
        self._print_line("  /help             显示此帮助")
        self._print_line("")
        self._print_line(f"{Colors.AI}服务器命令 (需要先连接):{Colors.RESET}")
        for cmd, desc in self.commands.items():
            if cmd not in ['/help', '/connect', '/disconnect', '/quit', '/clear', '/status', '/interrupt']:
                self._print_line(f"  {cmd:<15} {desc}")
        self._print_prompt()
    
    async def handle_command(self, command: str):
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == '/help':
            self.show_help()
        elif cmd == '/connect':
            if len(parts) < 2:
                self.display("error", "用法: /connect ws://host:port")
                return
            uri = parts[1]
            if self.client and self.client.connected:
                await self.client.disconnect()
            self.client = WebSocketClient(uri, self.display)
            if await self.client.connect():
                self.connected = True
                self.display("system", f"✅ 已连接到 {uri}")
                asyncio.create_task(self.client.receive_messages())
            else:
                self.client = None
                self.connected = False
        elif cmd == '/disconnect':
            if self.client:
                await self.client.disconnect()
                self.client = None
                self.connected = False
                self.display("system", "已断开连接")
            else:
                self.display("error", "未连接到服务器")
        elif cmd == '/status':
            if self.connected:
                self.display("system", f"✅ 已连接: {self.client.uri}")
            else:
                self.display("system", "未连接")
        elif cmd == '/clear':
            os.system('clear' if os.name == 'posix' else 'cls')
            self.displayed_messages.clear()
            self.current_input = ""
            self.print_banner()
        elif cmd == '/interrupt':
            if self.client and self.client.connected:
                await self._send_interrupt()
                self.display("info", "🛑 已发送中断信号")
            else:
                self.display("error", "未连接到服务器")
        elif cmd == '/quit':
            self.display("system", "👋 再见！")
            self.running = False
            if self.client:
                await self.client.disconnect()
            return
        elif cmd in self.commands:
            if self.client and self.client.connected:
                await self.client.send_message(command)
                self.display("system", f"📤 发送命令: {command}")
            else:
                self.display("error", "未连接到服务器")
        else:
            self.display("error", f"未知命令: {cmd}")
        self._print_prompt(clear_input=True)
    
    async def _send_interrupt(self):
        if self.client and self.client.connected:
            interrupt_msg = {"type": "interrupt", "content": "用户按下了 Ctrl+C 中断当前操作"}
            try:
                await self.client.websocket.send(json.dumps(interrupt_msg))
            except Exception as e:
                self.display("error", f"发送中断失败: {e}")
    
    async def send_user_message(self, message: str):
        if not self.client or not self.client.connected:
            self.display("error", "未连接到服务器")
            return
        
        # 重置流式状态
        with self.lock:
            if self.streaming_line:
                sys.stdout.write('\n')
                self.streaming_line = False
            self.waiting_for_response = True
            self.in_tool_phase = False
            self.prompt_shown = False
            # 【关键】清除当前输入，避免显示之前输入的内容
            self.current_input = ""
        
        self.ai_previous = ""
        self.ai_full = ""
        self.ai_prefix_shown = False
        
        self.display("system", f"{Colors.USER}👤 用户: {message}{Colors.RESET}")
        await self.client.send_message(message)
        # 不在这里显示提示符，等待AI响应结束后再显示
    
    async def run(self):
        self.print_banner()
        self._task_buffers = {}
        
        while self.running:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: sys.stdin.readline()
                )
                if not line:
                    break
                
                self.current_input = line.rstrip('\n')
                line = line.strip()
                
                if not line:
                    self._print_prompt(clear_input=True)
                    continue
                
                if line.startswith('/'):
                    await self.handle_command(line)
                else:
                    await self.send_user_message(line)
                
            except KeyboardInterrupt:
                if self.client and self.client.connected:
                    await self._send_interrupt()
                    self.display("info", "🛑 已发送中断信号")
                else:
                    self.display("error", "未连接到服务器")
                self._print_prompt(clear_input=True)
                continue
            except Exception as e:
                if self.running:
                    self.display("error", f"错误: {e}")
                break

async def main():
    default_uri = "ws://localhost:8765"
    uri = sys.argv[1] if len(sys.argv) > 1 else default_uri
    
    cli = SimpleCLI()
    
    cli.client = WebSocketClient(uri, cli.display)
    if await cli.client.connect():
        cli.connected = True
        cli.display("system", f"✅ 已连接到 {uri}")
        asyncio.create_task(cli.client.receive_messages())
    else:
        cli.display("error", f"无法连接到 {uri}")
        cli.display("info", f"你可以通过命令行参数指定地址: python client.py ws://your-server:8765")
    
    try:
        await cli.run()
    except KeyboardInterrupt:
        print(f"\n{Colors.SYSTEM}程序已退出{Colors.RESET}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.SYSTEM}程序已退出{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.ERROR}错误: {e}{Colors.RESET}")