#!/usr/bin/env python3
"""
AI智能助手 - 语音命令行前端
支持WebSocket直连、语音输入、语音输出、命令系统
"""

import asyncio
import json
import sys
import os
import threading
import warnings
from typing import Optional, Dict, Any
import websockets
from colorama import init, Fore, Style as ColoramaStyle

init(autoreset=True)

warnings.filterwarnings('ignore')
os.environ['ALSA_CONFIG_PATH'] = '/dev/null'
os.environ['JACK_NO_START_SERVER'] = '1'

try:
    import speech_recognition as sr
except ImportError:
    print("❌ 缺少语音识别库，请安装: pip install SpeechRecognition pyaudio")
    sys.exit(1)

try:
    import pyttsx3
except ImportError:
    print("❌ 缺少文本转语音库，请安装: pip install pyttsx3")
    sys.exit(1)

class Colors:
    USER = Fore.CYAN
    AI = Fore.GREEN
    TASK = Fore.YELLOW
    SYSTEM = Fore.BLUE
    ERROR = Fore.RED
    INFO = Fore.MAGENTA
    WARNING = Fore.LIGHTYELLOW_EX
    RESET = ColoramaStyle.RESET_ALL
    BOLD = ColoramaStyle.BRIGHT

class TextToSpeech:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            try:
                if hasattr(voice, 'language'):
                    lang_attr = voice.language
                elif hasattr(voice, 'languages'):
                    lang_attr = voice.languages[0] if voice.languages else ''
                else:
                    continue
                if 'zh' in str(lang_attr) or 'Chinese' in str(lang_attr):
                    self.engine.setProperty('voice', voice.id)
                    break
            except Exception:
                continue
    
    def speak(self, text: str):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"{Colors.ERROR}❌ 语音输出失败: {e}{Colors.RESET}")

class StreamingMessage:
    def __init__(self):
        self.content = ""
        self.is_active = False
    
    def add_chunk(self, chunk: str):
        self.content += chunk
        self.is_active = True
    
    def get_content(self) -> str:
        return self.content
    
    def clear(self):
        self.content = ""
        self.is_active = False

class WebSocketClient:
    def __init__(self, uri: str):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.streaming_messages: Dict[str, StreamingMessage] = {
            'chat': StreamingMessage(),
            'tasks': {}
        }
        self.running = True
        
    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            return True
        except Exception as e:
            print(f"{Colors.ERROR}❌ 连接失败: {e}{Colors.RESET}")
            return False
    
    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            self.connected = False
    
    async def send_message(self, message: str):
        if not self.websocket or not self.connected:
            print(f"{Colors.ERROR}❌ 未连接到服务器{Colors.RESET}")
            return False
        
        try:
            if message.startswith('/'):
                data = {'type': 'command', 'command': message}
            else:
                data = {'type': 'message', 'content': message}
            
            await self.websocket.send(json.dumps(data))
            return True
        except Exception as e:
            print(f"{Colors.ERROR}❌ 发送失败: {e}{Colors.RESET}")
            return False
    
    async def receive_messages(self, tts: TextToSpeech):
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data, tts)
                except json.JSONDecodeError:
                    await self.handle_stream_chunk(message, 'chat', tts)
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            print(f"\n{Colors.ERROR}❌ 连接已断开{Colors.RESET}")
        except Exception as e:
            print(f"\n{Colors.ERROR}❌ 接收消息错误: {e}{Colors.RESET}")
    
    async def handle_message(self, data: dict, tts: TextToSpeech):
        msg_type = data.get('type', '')
        content = data.get('content', '')
        
        if msg_type == 'chunk':
            await self.handle_stream_chunk(content, 'chat', tts)
        
        elif msg_type == 'complete':
            await self.handle_stream_complete('chat', tts)
        
        elif msg_type == 'dialogue_ended':
            await self.handle_dialogue_ended(tts)
        
        elif msg_type == 'task_process':
            msg_subtype = data.get('msg_type', '')
            task_content = data.get('content', '')
            task_id = data.get('task_id', 'unknown')
            execution_id = data.get('execution_id', 'unknown')
            task_title = data.get('task_title', '未知任务')
            
            if msg_subtype == 'chunk':
                await self.handle_stream_chunk(
                    task_content, 'task', tts,
                    {'task_id': task_id, 'execution_id': execution_id, 'title': task_title}
                )
            elif msg_subtype == 'complete':
                await self.handle_stream_complete('task', tts, execution_id)
        
        elif msg_type == 'task_status':
            task_id = data.get('task_id', 'unknown')
            title = data.get('title', '未知')
            status = data.get('status', 'unknown')
            message = data.get('message', content)
            
            status_icon = {
                'executing': '⚙️', 'complete': '✅', 'failed': '❌',
                'added': '➕', 'batch_start': '🚀', 'batch_complete': '🏁'
            }.get(status, '📋')
            
            print(f"{Colors.TASK}{status_icon} [任务 {task_id}] {title}: {message}{Colors.RESET}")
        
        elif msg_type == 'task_error':
            task_id = data.get('task_id', 'unknown')
            execution_id = data.get('execution_id', 'unknown')
            task_title = data.get('task_title', '未知')
            error = data.get('error', '未知错误')
            
            print(f"{Colors.ERROR}❌ [任务 {task_id}] {task_title}: {error}{Colors.RESET}")
            tts.speak(f"任务 {task_id} 出错了，错误是 {error}")
            
            if execution_id:
                await self.handle_stream_complete('task', tts, execution_id)
        
        elif msg_type == 'error':
            print(f"{Colors.ERROR}❌ {content}{Colors.RESET}")
            tts.speak(f"错误，{content}")
        
        elif msg_type == 'info':
            print(f"{Colors.INFO}ℹ️  {content}{Colors.RESET}")
            tts.speak(content)
        
        elif msg_type == 'command_result':
            print(f"{Colors.SYSTEM}📋 {content}{Colors.RESET}")
        
        elif msg_type == 'connection_ack':
            print(f"{Colors.AI}✅ {content}{Colors.RESET}")
        
        elif msg_type == 'notification':
            print(f"{Colors.INFO}🔔 {content}{Colors.RESET}")
            tts.speak(content)
        
        else:
            if content:
                await self.handle_stream_chunk(content, 'chat', tts)
    
    async def handle_stream_chunk(self, content: str, msg_type: str = 'chat', 
                                   tts: TextToSpeech = None, task_info: dict = None):
        if msg_type == 'chat':
            stream = self.streaming_messages['chat']
            stream.add_chunk(content)
            
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
    
    async def handle_stream_complete(self, msg_type: str = 'chat', 
                                      tts: TextToSpeech = None, execution_id: str = None):
        if msg_type == 'chat':
            stream = self.streaming_messages['chat']
            print()
            if tts and stream.content:
                tts.speak(stream.content)
            stream.clear()
        
        elif msg_type == 'task' and execution_id:
            if execution_id in self.streaming_messages['tasks']:
                print()
                del self.streaming_messages['tasks'][execution_id]
    
    async def handle_dialogue_ended(self, tts: TextToSpeech):
        print(f"\n{Colors.SYSTEM}✅ 对话已结束，可以开始新对话{Colors.RESET}")
        tts.speak("对话已结束")
        self.streaming_messages['chat'].clear()
        self.streaming_messages['tasks'].clear()

class VoiceInterface:
    def __init__(self):
        self.client: Optional[WebSocketClient] = None
        self.tts = None
        self.recognizer = None
        self.microphone = None
        self.has_audio = False
        self.has_tts = False
        self.has_microphone = False
        
        try:
            self.tts = TextToSpeech()
            self.has_tts = True
            print(f"{Colors.INFO}🔊 语音输出已就绪{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.WARNING}⚠️  语音输出不可用: {e}{Colors.RESET}")
        
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
            self.has_microphone = True
            print(f"{Colors.INFO}🎤 麦克风已就绪{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.WARNING}⚠️  麦克风不可用: {e}{Colors.RESET}")
        
        self.has_audio = self.has_tts or self.has_microphone
        
        if not self.has_audio:
            print(f"{Colors.INFO}ℹ️  将以纯文本模式运行{Colors.RESET}")
        
        self.commands = {
            '/help': '显示帮助信息',
            '/connect': '连接到服务器',
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
        banner = f"""
{Colors.BOLD}{Colors.AI}
╔══════════════════════════════════════════╗
║         AI智能助手 - 语音前端             ║
║         WebSocket 直连版本                ║
╚══════════════════════════════════════════╝
{Colors.RESET}
"""
        print(banner)
        print(f"{Colors.INFO}输入 /help 查看可用命令")
        print(f"输入语音开始对话，或输入文本命令{Colors.RESET}")
        print()
    
    def listen_voice(self) -> Optional[str]:
        """监听语音输入"""
        if not self.has_microphone:
            print(f"{Colors.WARNING}⚠️  麦克风不可用，请使用文本输入{Colors.RESET}")
            return None
        
        if not self.client or not self.client.connected:
            print(f"{Colors.ERROR}❌ 未连接到服务器，请先连接{Colors.RESET}")
            return None
        
        print(f"{Colors.INFO}🎤 正在听... (按 Ctrl+C 取消){Colors.RESET}")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source, timeout=15)
            
            text = self.recognizer.recognize_google(audio, language='zh-CN')
            print(f"{Colors.USER}👤 语音输入: {text}{Colors.RESET}")
            return text
        except sr.WaitTimeoutError:
            print(f"{Colors.INFO}⏱️  等待超时，请重试{Colors.RESET}")
            return None
        except sr.UnknownValueError:
            print(f"{Colors.INFO}😕 无法识别语音，请重试{Colors.RESET}")
            return None
        except sr.RequestError as e:
            print(f"{Colors.ERROR}❌ 语音识别服务错误: {e}{Colors.RESET}")
            return None
        except Exception as e:
            print(f"{Colors.ERROR}❌ 语音输入错误: {e}{Colors.RESET}")
            return None
    
    async def handle_command(self, command: str):
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
                if self.tts:
                    self.tts.speak(f"已连接到 {uri}")
                asyncio.create_task(self.client.receive_messages(self.tts))
            else:
                self.client = None
        
        elif cmd == '/disconnect':
            if self.client:
                await self.client.disconnect()
                self.client = None
                print(f"{Colors.SYSTEM}已断开连接{Colors.RESET}")
                if self.tts:
                    self.tts.speak("已断开连接")
            else:
                print(f"{Colors.ERROR}未连接到服务器{Colors.RESET}")
        
        elif cmd == '/status':
            if self.client and self.client.connected:
                print(f"{Colors.AI}✅ 已连接: {self.client.uri}{Colors.RESET}")
                if self.tts:
                    self.tts.speak(f"已连接到 {self.client.uri}")
            else:
                print(f"{Colors.SYSTEM}未连接{Colors.RESET}")
                if self.tts:
                    self.tts.speak("未连接")
        
        elif cmd == '/clear':
            os.system('clear' if os.name == 'posix' else 'cls')
            self.print_banner()
        
        elif cmd == '/quit':
            print(f"{Colors.SYSTEM}再见！{Colors.RESET}")
            if self.tts:
                self.tts.speak("再见")
            if self.client:
                await self.client.disconnect()
            sys.exit(0)
        
        elif cmd in self.commands:
            if self.client and self.client.connected:
                await self.client.send_message(command)
            else:
                print(f"{Colors.ERROR}未连接到服务器，请先使用 /connect 连接{Colors.RESET}")
        
        else:
            print(f"{Colors.ERROR}未知命令: {cmd}{Colors.RESET}")
    
    def show_help(self):
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
        if not self.client or not self.client.connected:
            print(f"{Colors.ERROR}❌ 未连接到服务器{Colors.RESET}")
            return
        
        print(f"\n{Colors.USER}👤 用户: {message}{Colors.RESET}")
        await self.client.send_message(message)
    
    async def run(self):
        self.print_banner()
        
        while True:
            try:
                user_input = await asyncio.to_thread(
                    input, f"{Colors.USER}>>> {Colors.RESET}"
                )
                user_input = user_input.strip()
                
                if not user_input:
                    if self.has_microphone:
                        print(f"{Colors.INFO}🎤 开始语音输入...{Colors.RESET}")
                        voice_text = await asyncio.to_thread(self.listen_voice)
                        if voice_text:
                            await self.send_user_message(voice_text)
                    else:
                        print(f"{Colors.WARNING}⚠️  麦克风不可用，请输入文本{Colors.RESET}")
                    continue
                
                if user_input.startswith('/'):
                    await self.handle_command(user_input)
                else:
                    await self.send_user_message(user_input)
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.INFO}⏹️  语音输入已取消{Colors.RESET}")
                continue
            except EOFError:
                print(f"\n{Colors.SYSTEM}再见！{Colors.RESET}")
                if self.tts:
                    self.tts.speak("再见")
                if self.client:
                    await self.client.disconnect()
                break
            except Exception as e:
                print(f"{Colors.ERROR}错误: {e}{Colors.RESET}")

async def main():
    cli = VoiceInterface()
    
    default_uri = "ws://localhost:8765"
    uri = sys.argv[1] if len(sys.argv) > 1 else default_uri
    
    cli.client = WebSocketClient(uri)
    if await cli.client.connect():
        print(f"{Colors.AI}✅ 已连接到 {uri}{Colors.RESET}")
        if cli.tts:
            cli.tts.speak(f"已连接到 {uri}")
        asyncio.create_task(cli.client.receive_messages(cli.tts))
    else:
        print(f"{Colors.WARNING}⚠️  无法连接到 {uri}{Colors.RESET}")
        print(f"{Colors.INFO}ℹ️  你可以通过命令行参数指定地址: python voice_client.py ws://your-server:8765{Colors.RESET}")
        print(f"{Colors.INFO}ℹ️  或者使用 /connect 命令手动连接{Colors.RESET}")
    
    await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.SYSTEM}程序已退出{Colors.RESET}")
