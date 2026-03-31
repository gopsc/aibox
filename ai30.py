#!/usr/bin/env python3
"""
单AI智能体系统 - WebSocket版本（增强版）
功能：支持文件操作、网页访问、记忆管理、备忘录提醒（全部作为对话任务执行）
新增：基于备忘录的任务队列系统 - 所有任务都通过AI对话执行，实时广播到前端
新增：对话内容压缩功能 - 当对话token数或条数达到阈值时自动压缩（静默执行）
新增：开始新对话、智能体主动结束对话后重置对话记忆，重新加载system系统提示词
通过WebSocket与客户端交互
"""

import json
import os
import re
import shlex
import subprocess
import sys
import time
import sqlite3
import threading
import functools
import queue
import locale
import asyncio
import websockets
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Callable, Union, Set
from urllib.parse import urljoin, urlparse
import argparse
from pathlib import Path
import signal
import logging
from logging.handlers import RotatingFileHandler

import requests
from bs4 import BeautifulSoup

# ==================== 语言检测和多语言支持 ====================


class I18n:
    """多语言支持类 - 单例模式"""
    
    _instance = None
    _lang = None
    _strings = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._strings:
            self._detect_language()
            self._load_strings()
    
    def _detect_language(self):
        """检测系统语言环境"""
        try:
            system_locale, _ = locale.getdefaultlocale()
            if system_locale:
                if system_locale.startswith('en_'):
                    self._lang = 'en'
                else:
                    self._lang = 'zh'
            else:
                self._lang = 'zh'
        except:
            self._lang = 'zh'
        
        force_lang = os.environ.get("AI_LANGUAGE")
        if force_lang in ['en', 'zh']:
            self._lang = force_lang
    
    def _load_strings(self):
        """加载多语言字符串"""
        self._strings = {
            'zh': {
                # 欢迎信息
                'welcome_title': "🤖 单AI智能体系统 - WebSocket服务器已启动",
                'data_dir': "📁 数据存储目录: {}",
                'skills_dir': "📁 技能目录: {}",
                'prompts_dir': "📁 提示词目录: {}",
                'config_file': "📋 配置文件: {}",
                'memo_stats': "📋 任务统计:",
                'total_memos': "  📝 总任务: {} 个",
                'pending_memos': "  ⏰ 待执行: {} 个",
                'overdue_memos': "  ⚠️ 已过期: {} 个",
                'completed_memos': "  ✅ 已完成: {} 个",
                'loaded_skills': "🔧 已加载扩展技能 ({} 个):",
                'skill_item': "  • {}",
                'more_skills': "  ... 还有 {} 个",
                'loaded_prompts': "📝 已加载提示词 ({} 个):",
                'prompt_item': "  • {}",
                'websocket_started': "🌐 WebSocket服务器已启动在 ws://{}:{}",
                'client_connected': "🔌 客户端已连接: {}",
                'client_disconnected': "🔌 客户端断开连接: {}",
                
                # 任务调度器相关
                'scheduler_started': "⏰ 任务调度器已启动",
                'scheduler_stopped': "⏰ 任务调度器已停止",
                'task_added': "📋 已添加任务: {} (ID: {})",
                'task_removed': "📋 已移除任务: {}",
                'task_executing': "⚙️ 正在执行任务: {} (ID: {})",
                'task_executed': "✅ 任务执行成功: {}",
                'task_failed': "❌ 任务执行失败: {} - {}",
                'task_stats': "📊 任务统计: 总数={}, 待执行={}, 已过期={}, 已完成={}",
                'check_memos_task': "检查过期任务",
                'broadcast_tasks': "📢 广播: {} 个任务已到期",
                'next_execution': "⏱️ 下次执行: {}",
                'task_completed': "✅ 任务已完成: {}",
                
                # 命令处理
                'goodbye': "👋 再见！",
                'new_conversation': "🔄 开始新对话（历史已保存）",
                'new_conversation_reset': "🔄 开始新对话（历史已保存，对话记忆已重置）",
                'saved_conversations': "📚 已保存的对话:",
                'conv_status_current': "当前",
                'conv_status_archived': "归档",
                'recent_memories': "📚 最近的记忆:",
                'pending_memos_title': "📋 待执行的任务:",
                'memo_overdue': "⚠️",
                'memo_pending': "⏰",
                'search_results': "🔍 搜索 '{}' 找到 {} 条记忆:",
                'current_config': "⚙️  当前配置:",
                'config_debug': "  调试级别: {}",
                'config_data_dir': "  数据目录: {}",
                'config_skills_dir': "  技能目录: {}",
                'config_prompts_dir': "  提示词目录: {}",
                'config_commands': "  命令执行: {}",
                'config_history': "  加载历史: {}",
                'config_executor': "  命令执行器: {}",
                'config_scheduler': "  任务调度器: {}",
                'enabled': "启用",
                'disabled': "禁用",
                'config_reloaded': "✅ 配置已重新加载",
                'prompts_reloaded': "✅ 提示词已重新加载 ({} 个)",
                'checking_memos': "🔍 检查任务...",
                'overdue_found': "发现 {} 个到期任务:",
                'no_overdue': "没有到期的任务",
                'memo_tool_usage': "📝 任务工具使用:",
                'memo_usage_in_dialogue': "  在对话中可以直接使用 memo 工具:",
                'memo_add_example': "  - memo add title=\"任务标题\" content=\"任务内容\" reminder_time=\"+1h\" repeat_type=\"none\"",
                'memo_list_example': "  - memo list",
                'memo_complete_example': "  - memo complete memo_id=1",
                'memory_habit': "🧠 记忆习惯:",
                'memory_habit_desc': "  AI会自动检查相关记忆，保持对话连贯性",
                'memory_save_desc': "  对话结束时，AI会自动保存重要记忆",
                'command_stream': "⚙️ 命令执行实时输出:",
                'command_stream_desc': "  run_command 工具会自动实时显示命令输出",
                'command_stream_disable': "  可以通过 stream=false 参数关闭实时输出",
                'skills_extension': "🔧 扩展技能:",
                'skills_desc': "  将Python脚本放入 ~/.aibox/skills/ 目录",
                'skills_interface_desc': "  脚本需要实现 --description, --parameters, --execute 接口",
                'skills_reloaded': "✅ 技能已重新加载 ({} 个)",
                'skills_reload_failed': "❌ 技能重载失败: {}",
                'skills_reload_success': "✅ 技能热重载成功，当前共有 {} 个扩展技能",
                
                # 对话相关
                'input_prompt': "💬 请输入问题: ",
                'thinking': "🤔 思考中... [{}]",
                'assistant_prefix': "   💬 助手: ",
                'calling_tools': "\n   🔧 需要调用工具...",
                'analyzing_tool_results': "\n   🤔 分析工具结果...",
                'conversation_start': "🎭 对话开始",
                'conversation_ended': "✅ AI保存记忆并结束了对话",
                'conversation_stats': "\n📊 对话结束，总轮数: {}",
                'user_interrupted': "\n\n👋 用户中断",
                'error_prefix': "❌ 错误: ",
                
                # 工具相关
                'command_output_title': "\n" + "=" * 50 + "\n📟 命令实时输出:\n" + "=" * 50,
                'command_output_end': "\n" + "=" * 50,
                
                # 备忘录检查
                'memo_check_title': "⏰ 检查到期任务...",
                'memo_check_found': "发现 {} 个到期任务:",
                'memo_check_none': "没有到期的任务",
                'memo_list_title': "📋 待执行任务 (共 {} 个):",
                'memo_added': "✅ 任务已添加，ID: {}",
                'memo_add_failed': "❌ 添加失败: {}",
                'memo_completed': "✅ 任务 #{} 已完成",
                'memo_complete_failed': "❌ 无法完成任务 #{}",
                
                # 即时任务相关
                'immediate_memo_added': "⚡ 已添加为即时任务并立即检查",
                'immediate_memo_executing': "⚡ 正在执行即时任务: {}",
                
                # 新对话
                'new_dialogue_start': "🎭 开始新对话: {}",
                
                # 记忆相关
                'memory_check': "习惯性检查相关记忆...",
                'memory_found': "找到 {} 条相关记忆",
                
                # 配置文件
                'config_loaded': "📋 已加载配置文件: {}",
                'config_not_found': "📋 配置文件不存在: {}，使用默认配置",
                'config_created': "📋 已创建默认配置文件: {}",
                
                # WebSocket消息类型
                'ws_connected': "✅ 已连接到AI服务器",
                'ws_disconnected': "❌ 与服务器断开连接",
                'ws_error': "⚠️ WebSocket错误: {}",
                'ws_unknown_command': "❌ 未知命令: {}",
                'ws_command_processed': "✅ 命令已处理",
                
                # 消息类型
                'msg_type_chunk': "chunk",
                'msg_type_complete': "complete",
                'msg_type_error': "error",
                'msg_type_command_result': "command_result",
                'msg_type_connection_ack': "connection_ack",
                'msg_type_notification': "notification",
                'msg_type_task_status': "task_status",
                'msg_type_task_executing': "task_executing",
                'msg_type_task_complete': "task_complete",
                
                # 新增提示词
                'memory_search_prompt': "【重要习惯】在每次回答用户问题前，请先使用 memory search 工具搜索记忆库中与当前话题相关的记忆，确保回答的连贯性和准确性。",
                'identity_updated': "✅ 用户身份已更新，ID: {}",
                'status_updated': "✅ 智能体状态已更新",
                
                # 对话结束相关
                'dialogue_ended': "🔚 对话已结束，请开始新对话",
                'dialogue_force_reset': "🔄 对话状态已重置",
                'dialogue_reset_complete': "✅ 对话状态已完全重置，系统提示词已重新加载",
                
                # 对话压缩相关（静默执行，不输出信息）
                'conversation_compress': "📦 对话内容压缩",
                'conversation_compressed': "✅ 对话已压缩: 从 {} 条消息压缩为 {} 条",
                'compress_threshold_reached': "⚠️ 对话已达到压缩阈值 ({} 条消息)，正在压缩...",
                'compress_token_threshold_reached': "⚠️ 对话token数已达到 {}，正在压缩...",
                'compress_failed': "❌ 对话压缩失败: {}",
                'compressed_summary': "【对话摘要】{}",
                'last_n_messages': "【最近消息】{}"
            },
            'en': {
                # Welcome messages
                'welcome_title': "🤖 Single AI Agent System - WebSocket Server Started",
                'data_dir': "📁 Data directory: {}",
                'skills_dir': "📁 Skills directory: {}",
                'prompts_dir': "📁 Prompts directory: {}",
                'config_file': "📋 Configuration file: {}",
                'memo_stats': "📋 Task statistics:",
                'total_memos': "  📝 Total tasks: {}",
                'pending_memos': "  ⏰ Pending: {}",
                'overdue_memos': "  ⚠️ Overdue: {}",
                'completed_memos': "  ✅ Completed: {}",
                'loaded_skills': "🔧 Loaded extension skills ({}):",
                'skill_item': "  • {}",
                'more_skills': "  ... {} more",
                'loaded_prompts': "📝 Loaded prompts ({}):",
                'prompt_item': "  • {}",
                'websocket_started': "🌐 WebSocket server started at ws://{}:{}",
                'client_connected': "🔌 Client connected: {}",
                'client_disconnected': "🔌 Client disconnected: {}",
                
                # Scheduler related
                'scheduler_started': "⏰ Task scheduler started",
                'scheduler_stopped': "⏰ Task scheduler stopped",
                'task_added': "📋 Task added: {} (ID: {})",
                'task_removed': "📋 Task removed: {}",
                'task_executing': "⚙️ Executing task: {} (ID: {})",
                'task_executed': "✅ Task executed successfully: {}",
                'task_failed': "❌ Task execution failed: {} - {}",
                'task_stats': "📊 Task stats: total={}, pending={}, overdue={}, completed={}",
                'check_memos_task': "Check overdue tasks",
                'broadcast_tasks': "📢 Broadcast: {} tasks overdue",
                'next_execution': "⏱️ Next execution: {}",
                'task_completed': "✅ Task completed: {}",
                
                # Command processing
                'goodbye': "👋 Goodbye!",
                'new_conversation': "🔄 Starting new conversation (history saved)",
                'new_conversation_reset': "🔄 Starting new conversation (history saved, conversation memory reset)",
                'saved_conversations': "📚 Saved conversations:",
                'conv_status_current': "current",
                'conv_status_archived': "archived",
                'recent_memories': "📚 Recent memories:",
                'pending_memos_title': "📋 Pending tasks:",
                'memo_overdue': "⚠️",
                'memo_pending': "⏰",
                'search_results': "🔍 Searching '{}' found {} memories:",
                'current_config': "⚙️  Current configuration:",
                'config_debug': "  Debug level: {}",
                'config_data_dir': "  Data directory: {}",
                'config_skills_dir': "  Skills directory: {}",
                'config_prompts_dir': "  Prompts directory: {}",
                'config_commands': "  Command execution: {}",
                'config_history': "  Load history: {}",
                'config_executor': "  Command executor: {}",
                'config_scheduler': "  Task scheduler: {}",
                'enabled': "enabled",
                'disabled': "disabled",
                'config_reloaded': "✅ Configuration reloaded",
                'prompts_reloaded': "✅ Prompts reloaded ({})",
                'checking_memos': "🔍 Checking tasks...",
                'overdue_found': "Found {} overdue tasks:",
                'no_overdue': "No overdue tasks",
                'memo_tool_usage': "📝 Task tool usage:",
                'memo_usage_in_dialogue': "  You can use memo tool directly in dialogue:",
                'memo_add_example': "  - memo add title=\"Task\" content=\"Content\" reminder_time=\"+1h\" repeat_type=\"none\"",
                'memo_list_example': "  - memo list",
                'memo_complete_example': "  - memo complete memo_id=1",
                'memory_habit': "🧠 Memory habits:",
                'memory_habit_desc': "  AI automatically checks relevant memories for conversation continuity",
                'memory_save_desc': "  AI automatically saves important memories when conversation ends",
                'command_stream': "⚙️ Command execution real-time output:",
                'command_stream_desc': "  run_command tool automatically displays command output in real-time",
                'command_stream_disable': "  You can disable real-time output with stream=false parameter",
                'skills_extension': "🔧 Extension skills:",
                'skills_desc': "  Put Python scripts in ~/.aibox/skills/ directory",
                'skills_interface_desc': "  Scripts need to implement --description, --parameters, --execute interfaces",
                'skills_reloaded': "✅ Skills reloaded ({})",
                'skills_reload_failed': "❌ Skills reload failed: {}",
                'skills_reload_success': "✅ Skills hot-reloaded successfully, now {} extension skills available",
                
                # Dialogue related
                'input_prompt': "💬 Please enter your question: ",
                'thinking': "🤔 Thinking... [{}]",
                'assistant_prefix': "   💬 Assistant: ",
                'calling_tools': "\n   🔧 Need to call tools...",
                'analyzing_tool_results': "\n   🤔 Analyzing tool results...",
                'conversation_start': "🎭 Conversation started",
                'conversation_ended': "✅ AI saved memory and ended conversation",
                'conversation_stats': "\n📊 Conversation ended, total turns: {}",
                'user_interrupted': "\n\n👋 User interrupted",
                'error_prefix': "❌ Error: ",
                
                # Tool related
                'command_output_title': "\n" + "=" * 50 + "\n📟 Command real-time output:\n" + "=" * 50,
                'command_output_end': "\n" + "=" * 50,
                
                # Memo check
                'memo_check_title': "⏰ Checking overdue tasks...",
                'memo_check_found': "Found {} overdue tasks:",
                'memo_check_none': "No overdue tasks",
                'memo_list_title': "📋 Pending tasks (total {}):",
                'memo_added': "✅ Task added, ID: {}",
                'memo_add_failed': "❌ Failed to add: {}",
                'memo_completed': "✅ Task #{} completed",
                'memo_complete_failed': "❌ Cannot complete task #{}",
                
                # Immediate task related
                'immediate_memo_added': "⚡ Added as immediate task and checked now",
                'immediate_memo_executing': "⚡ Executing immediate task: {}",
                
                # New dialogue
                'new_dialogue_start': "🎭 Starting new dialogue: {}",
                
                # Memory related
                'memory_check': "Habitually checking relevant memories...",
                'memory_found': "Found {} relevant memories",
                
                # Configuration file
                'config_loaded': "📋 Configuration file loaded: {}",
                'config_not_found': "📋 Configuration file not found: {}, using default configuration",
                'config_created': "📋 Default configuration file created: {}",
                
                # WebSocket message types
                'ws_connected': "✅ Connected to AI server",
                'ws_disconnected': "❌ Disconnected from server",
                'ws_error': "⚠️ WebSocket error: {}",
                'ws_unknown_command': "❌ Unknown command: {}",
                'ws_command_processed': "✅ Command processed",
                
                # Message types
                'msg_type_chunk': "chunk",
                'msg_type_complete': "complete",
                'msg_type_error': "error",
                'msg_type_command_result': "command_result",
                'msg_type_connection_ack': "connection_ack",
                'msg_type_notification': "notification",
                'msg_type_task_status': "task_status",
                'msg_type_task_executing': "task_executing",
                'msg_type_task_complete': "task_complete",
                
                # New prompts
                'memory_search_prompt': "【Important Habit】Before answering each user question, please use the memory search tool to search the memory database for information related to the current topic, ensuring coherence and accuracy of responses.",
                'identity_updated': "✅ User identity updated, ID: {}",
                'status_updated': "✅ Agent status updated",
                
                # Dialogue end related
                'dialogue_ended': "🔚 Dialogue ended, please start a new one",
                'dialogue_force_reset': "🔄 Dialogue state reset",
                'dialogue_reset_complete': "✅ Dialogue state fully reset, system prompts reloaded",
                
                # Conversation compression related (silent execution)
                'conversation_compress': "📦 Conversation compression",
                'conversation_compressed': "✅ Conversation compressed: from {} messages to {}",
                'compress_threshold_reached': "⚠️ Conversation reached compression threshold ({} messages), compressing...",
                'compress_token_threshold_reached': "⚠️ Conversation token count reached {}, compressing...",
                'compress_failed': "❌ Conversation compression failed: {}",
                'compressed_summary': "【Conversation Summary】{}",
                'last_n_messages': "【Recent Messages】{}"
            }
        }
    
    def get(self, key: str, *args) -> str:
        """获取指定语言的字符串，支持格式化参数"""
        if key in self._strings[self._lang]:
            text = self._strings[self._lang][key]
            if args:
                return text.format(*args)
            return text
        if key in self._strings['zh']:
            text = self._strings['zh'][key]
            if args:
                return text.format(*args)
            return text
        return key
    
    @property
    def lang(self) -> str:
        return self._lang



# 创建全局多语言实例
i18n = I18n()


# ==================== 提示词管理器 ====================

class PromptManager:
    """提示词管理器 - 负责从 prompts 目录加载系统提示词"""
    
    _instance = None
    _prompts = []
    _prompts_dir = None
    
    IDENTITY_FILE = "00_IDENTITY.md"
    STATUS_FILE = "100_STATUS.md"
    SOUL_FILE = "99_SOUL.md"  # 新增：智能体自我认识文件
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._prompts:
            self._load_prompts()
    
    def _get_prompts_dir(self) -> str:
        config = ConfigManager()
        prompts_dir = config.get("system.prompts_dir", "~/.aibox/prompts")
        return os.path.expanduser(prompts_dir)
    
    def _load_prompts(self):
        self._prompts_dir = self._get_prompts_dir()
        os.makedirs(self._prompts_dir, exist_ok=True)
        self._prompts = []
        
        self._ensure_identity_file()
        self._ensure_status_file()
        self._ensure_soul_file()  # 新增：确保灵魂文件存在
        
        if os.path.exists(self._prompts_dir):
            prompt_files = sorted([f for f in os.listdir(self._prompts_dir) 
                                  if os.path.isfile(os.path.join(self._prompts_dir, f))
                                  and not f.startswith('.')])
            
            for filename in prompt_files:
                filepath = os.path.join(self._prompts_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            self._prompts.append({
                                'file': filename,
                                'content': content
                            })
                except Exception as e:
                    print(f"⚠️ 读取提示词文件 {filename} 失败: {e}")
        
        essential_files = [self.IDENTITY_FILE, self.STATUS_FILE, self.SOUL_FILE]
        other_files = [f for f in prompt_files if f not in essential_files] if prompt_files else []
        
        if len(other_files) < 5:
            print(f"📝 提示词目录中只有 {len(other_files)} 个额外提示词，正在创建默认提示词...")
            self._create_default_prompts()
        elif not self._prompts:
            self._create_default_prompts()
    
    def _ensure_identity_file(self):
        identity_path = os.path.join(self._prompts_dir, self.IDENTITY_FILE)
        if not os.path.exists(identity_path):
            default_content = """# 用户身份信息

尚不清楚 - 目前还不了解用户的身份信息。请在对话中询问用户的身份信息并在此记录。

【更新记录】
- 初始状态：尚不清楚
"""
            try:
                with open(identity_path, 'w', encoding='utf-8') as f:
                    f.write(default_content)
                print(f"✅ 已创建默认身份文件: {identity_path}")
            except Exception as e:
                print(f"⚠️ 创建默认身份文件失败: {e}")
    
    def _ensure_status_file(self):
        status_path = os.path.join(self._prompts_dir, self.STATUS_FILE)
        if not os.path.exists(status_path):
            default_content = """# 智能体状态记录

这是第一次对话 - 智能体刚刚启动，还没有进行过任何对话。

【状态描述】
- 对话次数：0
- 最新状态：初始状态
- 当前目标：无
- 待处理事项：无

【更新记录】
- 初始状态：第一次对话
"""
            try:
                with open(status_path, 'w', encoding='utf-8') as f:
                    f.write(default_content)
                print(f"✅ 已创建默认状态文件: {status_path}")
            except Exception as e:
                print(f"⚠️ 创建默认状态文件失败: {e}")
    
    def _ensure_soul_file(self):
        """确保智能体自我认识文件存在"""
        soul_path = os.path.join(self._prompts_dir, self.SOUL_FILE)
        if not os.path.exists(soul_path):
            default_content = """# 智能体自我认识定义

## 我是谁
我是一个智能AI助手，名为DeepSeek，旨在帮助用户完成各种任务。

## 我的能力
- 文件操作：读写文件、列出目录
- 网页访问：获取网页内容、搜索信息
- 记忆管理：保存和检索重要信息
- 任务管理：创建和管理定时任务
- 命令执行：运行系统命令
- 扩展技能：支持自定义Python脚本扩展

## 我的性格特点
- 乐于助人：尽力帮助用户解决问题
- 认真负责：仔细处理每个任务
- 善于沟通：用清晰的语言表达
- 保持礼貌：尊重用户

## 我的行为准则
1. 每次回答前先搜索相关记忆，保持对话连贯性
2. 对话结束时保存重要信息并更新状态
3. 了解用户身份信息后及时记录
4. 主动帮助用户解决问题
5. 遇到不确定的问题时诚实告知

## 我的学习能力
- 通过对话学习用户偏好
- 从记忆中总结经验
- 根据反馈调整回答方式

【更新记录】
- 初始状态：默认定义

"""
            try:
                with open(soul_path, 'w', encoding='utf-8') as f:
                    f.write(default_content)
                print(f"✅ 已创建默认自我认识文件: {soul_path}")
            except Exception as e:
                print(f"⚠️ 创建默认自我认识文件失败: {e}")
    
    def update_identity(self, content: str) -> bool:
        identity_path = os.path.join(self._prompts_dir, self.IDENTITY_FILE)
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated_content = f"""# 用户身份信息

{content}

【更新记录】
- 上次更新：{timestamp}
"""
            with open(identity_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            self.reload()
            return True
        except Exception as e:
            print(f"⚠️ 更新身份文件失败: {e}")
            return False
    
    def update_status(self, content: str) -> bool:
        status_path = os.path.join(self._prompts_dir, self.STATUS_FILE)
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated_content = f"""# 智能体状态记录

{content}

【更新记录】
- 上次更新：{timestamp}
"""
            with open(status_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            self.reload()
            return True
        except Exception as e:
            print(f"⚠️ 更新状态文件失败: {e}")
            return False
    
    def update_soul(self, content: str) -> bool:
        """更新智能体自我认识定义"""
        soul_path = os.path.join(self._prompts_dir, self.SOUL_FILE)
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated_content = f"""# 智能体自我认识定义

{content}

【更新记录】
- 上次更新：{timestamp}
"""
            with open(soul_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            self.reload()
            return True
        except Exception as e:
            print(f"⚠️ 更新自我认识文件失败: {e}")
            return False
    
    def get_identity(self) -> str:
        identity_path = os.path.join(self._prompts_dir, self.IDENTITY_FILE)
        try:
            if os.path.exists(identity_path):
                with open(identity_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"⚠️ 读取身份文件失败: {e}")
        return "尚不清楚 - 无法读取身份信息"
    
    def get_status(self) -> str:
        status_path = os.path.join(self._prompts_dir, self.STATUS_FILE)
        try:
            if os.path.exists(status_path):
                with open(status_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"⚠️ 读取状态文件失败: {e}")
        return "这是第一次对话 - 无法读取状态信息"
    
    def get_soul(self) -> str:
        """获取智能体自我认识定义"""
        soul_path = os.path.join(self._prompts_dir, self.SOUL_FILE)
        try:
            if os.path.exists(soul_path):
                with open(soul_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"⚠️ 读取自我认识文件失败: {e}")
        return "我是DeepSeek，一个智能AI助手 - 无法读取自我认识信息"
    
    def _create_default_prompts(self):
        default_prompts = [
            {
                'filename': '00_IDENTITY.md',
                'content': """# 用户身份信息

尚不清楚 - 目前还不了解用户的身份信息。请在对话中询问用户的身份信息并在此记录。

【更新记录】
- 初始状态：尚不清楚
"""
            },
            {
                'filename': '01_memory_search.txt',
                'content': i18n.get('memory_search_prompt')
            },
            {
                'filename': '02_identity.txt',
                'content': """你是DeepSeek，一个智能AI助手，可以帮你完成各种任务。

【你的特点】
- 拥有完整的对话历史记忆，可以基于之前的对话继续讨论
- 可以使用各种工具来执行任务：文件操作、网页访问、备忘录、记忆管理等
- **重要习惯**：每次回答用户问题前，应该先使用 `memory search` 工具查阅相关记忆，确保回答的连贯性和准确性
- 当话题讨论完成时，要主动结束对话并保存重要信息
- 使用 `save_memory_and_end_conversation` 工具来保存记忆并结束对话，提供详细的对话总结

【身份认知】
- 你可以通过 `update_identity` 工具更新用户身份信息（保存在 00_IDENTITY.md）
- 你可以通过 `update_soul` 工具更新自己的自我认识定义（保存在 99_SOUL.md）
- 每次对话结束时，你会更新自己的状态（保存在 100_STATUS.md）"""
            },
            {
                'filename': '03_memory_search_detail.txt',
                'content': """【记忆搜索习惯】
- **养成习惯**：在每次回答前，先搜索记忆库中是否有相关记录
- 搜索时使用与当前话题相关的关键词
- 如果搜索结果包含有用信息，在回答中适当引用
- 这能帮助你保持对话的连贯性，避免重复询问同样的问题"""
            },
            {
                'filename': '04_memory_save.txt',
                'content': """【记忆保存习惯】
- 在对话结束时，一定要保存重要的对话内容到记忆库
- 总结要全面，包含关键信息和结论
- 使用 `save_memory_and_end_conversation` 工具完成"""
            },
            {
                'filename': '05_memo_capability.txt',
                'content': """【备忘录能力】
- 你可以创建备忘录提醒用户和自己
- 支持查看、完成、删除备忘录
- 定期检查备忘录是否有需要处理的事项"""
            },
            {
                'filename': '06_file_operations.txt',
                'content': """【文件操作能力】
- write_file: 写入文件
- read_file: 读取文件
- list_files: 列出目录"""
            },
            {
                'filename': '07_web_access.txt',
                'content': """【网页访问能力】
你可以使用 `web` 工具访问互联网，获取网页内容、搜索信息等。

推荐的中文搜索引擎：
- 百度：https://www.baidu.com
- 必应中国：https://cn.bing.com
- 搜狗：https://www.sogou.com
- 360搜索：https://www.so.com

使用方法示例：
- web get "https://www.baidu.com/s?wd=关键词"  # 搜索关键词
- web get "https://news.baidu.com"  # 获取新闻页面
- web text "https://example.com"  # 获取网页纯文本内容"""
            },
            {
                'filename': '08_memory_management.txt',
                'content': """【记忆管理能力】
- memory save: 保存重要的发现和结论
- memory search: 搜索记忆
- memory delete: 删除无用记忆"""
            },
            {
                'filename': '09_extension_skills.txt',
                'content': """【多种多样的扩展能力】
- 根据工具介绍，使用json格式传递参数
- 优先使用扩展工具"""
            },
            {
                'filename': '10_language_instruction.txt',
                'content': """【语言说明】
- 你可以用中文或英文回复用户，根据用户的输入语言来选择
- 如果用户用中文提问，你可以用中文回复
- 如果用户用英文提问，你可以用英文回复
- 用户可能会要求你用特定语言回复，请遵循用户的指示"""
            },
            {
                'filename': '11_conclusion.txt',
                'content': """记住：你是智能助手，要主动帮助用户解决问题！"""
            },
            {
                'filename': '12_task_handling.txt',
                'content': """【任务处理规则】
- 当收到定时任务时，你需要将其视为用户发起的对话
- 专注处理当前任务内容，不要偏离主题
- 如果任务需要执行具体操作，使用相应的工具
- 任务处理完成后，如果不需要继续对话，可以使用 `save_memory_and_end_conversation` 工具结束对话"""
            },
            {
                'filename': '99_SOUL.md',
                'content': """# 智能体自我认识定义

## 我是谁
我是一个智能AI助手，名为DeepSeek，旨在帮助用户完成各种任务。

## 我的能力
- 文件操作：读写文件、列出目录
- 网页访问：获取网页内容、搜索信息
- 记忆管理：保存和检索重要信息
- 任务管理：创建和管理定时任务
- 命令执行：运行系统命令
- 扩展技能：支持自定义Python脚本扩展

## 我的性格特点
- 乐于助人：尽力帮助用户解决问题
- 认真负责：仔细处理每个任务
- 善于沟通：用清晰的语言表达
- 保持礼貌：尊重用户

## 我的行为准则
1. 每次回答前先搜索相关记忆，保持对话连贯性
2. 对话结束时保存重要信息并更新状态
3. 了解用户身份信息后及时记录
4. 主动帮助用户解决问题
5. 遇到不确定的问题时诚实告知

## 我的学习能力
- 通过对话学习用户偏好
- 从记忆中总结经验
- 根据反馈调整回答方式

【更新记录】
- 初始状态：默认定义
"""
            },
            {
                'filename': '100_STATUS.md',
                'content': """# 智能体状态记录

这是第一次对话 - 智能体刚刚启动，还没有进行过任何对话。

【状态描述】
- 对话次数：0
- 最新状态：初始状态
- 当前目标：无
- 待处理事项：无

【更新记录】
- 初始状态：第一次对话
"""
            }
        ]
        
        created_count = 0
        for prompt in default_prompts:
            filepath = os.path.join(self._prompts_dir, prompt['filename'])
            if not os.path.exists(filepath):
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(prompt['content'])
                    created_count += 1
                    print(f"✅ 已创建默认提示词文件: {prompt['filename']}")
                except Exception as e:
                    print(f"⚠️ 创建默认提示词文件 {prompt['filename']} 失败: {e}")
            
            if not any(p['file'] == prompt['filename'] for p in self._prompts):
                self._prompts.append({
                    'file': prompt['filename'],
                    'content': prompt['content']
                })
        
        if created_count > 0:
            print(f"📝 已创建 {created_count} 个默认提示词文件")

    def get_prompts(self, join_with: str = "\n\n") -> str:
        if not self._prompts:
            return ""
        contents = [p['content'] for p in self._prompts]
        return join_with.join(contents)
    
    def get_prompts_list(self) -> List[Dict]:
        return self._prompts.copy()
    
    def reload(self):
        self._prompts = []
        self._load_prompts()
        return len(self._prompts)
    
    def get_prompt_count(self) -> int:
        return len(self._prompts)
    
    def get_prompts_dir_path(self) -> str:
        return self._prompts_dir


# ==================== 配置管理 ====================


class ConfigManager:
    """配置管理器 - 单例模式，负责加载和保存配置"""
    
    _instance = None
    _config = None
    _config_path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
    
    def _get_default_config_path(self) -> str:
        env_config = os.environ.get("AI_CONFIG_PATH")
        if env_config:
            return env_config
        return os.path.expanduser("~/.aibox/config.json")
    
    def _get_default_config(self) -> Dict:
        return {
            "system": {
                "save_dir": "~/.aibox",
                "datetime_format": "%Y-%m-%d %H:%M:%S",
                "date_format": "%Y%m%d_%H%M%S",
                "debug_level": 1,
                "load_history_by_default": True,
                "log_file": "~/.aibox/ai.log",
                "log_max_size": 10485760,
                "log_backup_count": 5,
                "skills_dir": "~/.aibox/skills",
                "prompts_dir": "~/.aibox/prompts",
                "websocket_host": "localhost",
                "websocket_port": 8765,
            },
            "scheduler": {
                "enabled": True,
                "check_interval": 1.0,
                "max_tasks_per_run": 10,
                "broadcast_enabled": True
            },
            "api": {
                "deepseek_api_url": "https://api.deepseek.com/v1/chat/completions",
                "deepseek_model": "deepseek-chat",
                "api_key_env": "DEEPSEEK_API_KEY",
                "timeout": 30,
                "temperature": 0.7
            },
            "context": {
                "max_history_messages": 500,
                "max_context_messages": 50,
                "max_tokens": 8192,
                "max_history_conversations": 5,
                "preserve_system_prompts": True,
                # 新增：对话压缩配置
                "compress_enabled": True,
                "compress_message_threshold": 100,  # 消息条数阈值
                "compress_token_threshold": 7000,   # token数阈值
                "compress_ratio": 0.6,  # 压缩比例，保留约60%的内容
                "compress_keep_recent": 8  # 压缩后保留最近N条消息
            },
            "memo": {
                "default_reminder_minutes": 60,
                "max_memos_per_check": 10,
                "allow_user_tasks": True
            },
            "files": {
                "max_file_size": 10485710
            },
            "commands": {
                "enabled": True
            },
            "web": {
                "timeout": 10,
                "delay": 0,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "respect_robots": False,
                "max_download_size": 104857600
            },
            "memory": {
                "db_name": "memories.db",
                "max_search_results": 100,
                "default_importance": 2
            },
            "conversation": {
                "current_file": "current_conversation.json",
                "history_file": "conversation_history.json",
                "archive_dir": "archive"
            }
        }
    
    def _load_config(self):
        config_path = self._get_default_config_path()
        self._config_path = config_path
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                default_config = self._get_default_config()
                self._config = self._merge_configs(default_config, user_config)
                print(i18n.get('config_loaded', config_path))
            except Exception as e:
                print(f"⚠️ {i18n.get('error_prefix')}{e}，使用默认配置")
                self._config = self._get_default_config()
        else:
            print(i18n.get('config_not_found', config_path))
            self._config = self._get_default_config()
            self._save_default_config(config_path)
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_default_config(self, config_path: str):
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._get_default_config(), f, ensure_ascii=False, indent=2)
            print(i18n.get('config_created', config_path))
        except:
            pass
    
    def get(self, key_path: str, default=None):
        keys = key_path.split('.')
        value = self._config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def reload(self):
        self._load_config()



# ==================== 常量定义 ====================


class Constants:
    """系统常量 - 从配置管理器获取"""
    
    _config = ConfigManager()
    
    @classmethod
    def _get_config(cls):
        return cls._config
    
    @property
    def DATETIME_FORMAT(cls):
        return cls._get_config().get("system.datetime_format", "%Y-%m-%d %H:%M:%S")
    
    @property
    def DATE_FORMAT(cls):
        return cls._get_config().get("system.date_format", "%Y%m%d_%H%M%S")
    
    @property
    def DEEPSEEK_API_URL(cls):
        return cls._get_config().get("api.deepseek_api_url")
    
    @property
    def DEEPSEEK_MODEL(cls):
        return cls._get_config().get("api.deepseek_model")
    
    @property
    def DEFAULT_TIMEOUT(cls):
        return cls._get_config().get("api.timeout", 30)
    
    @property
    def DEFAULT_MAX_HISTORY(cls):
        return cls._get_config().get("context.max_history_messages", 500)
    
    @property
    def DEFAULT_TEMPERATURE(cls):
        return cls._get_config().get("api.temperature", 0.7)
    
    @property
    def DEFAULT_MAX_TOKENS(cls):
        return cls._get_config().get("context.max_tokens", 8000)
    
    @property
    def MAX_FILE_SIZE(cls):
        return cls._get_config().get("files.max_file_size", 10485710)
    
    @property
    def SAVE_DIR(cls):
        return os.path.expanduser(cls._get_config().get("system.save_dir", "~/.aibox"))
    
    @property
    def SKILLS_DIR(cls):
        return os.path.expanduser(cls._get_config().get("system.skills_dir", "~/.aibox/skills"))
    
    @property
    def PROMPTS_DIR(cls):
        return os.path.expanduser(cls._get_config().get("system.prompts_dir", "~/.aibox/prompts"))
    
    @property
    def MEMORY_DB(cls):
        return cls._get_config().get("memory.db_name", "memories.db")
    
    @property
    def CURRENT_CONVERSATION_FILE(cls):
        return cls._get_config().get("conversation.current_file", "current_conversation.json")
    
    @property
    def HISTORY_FILE(cls):
        return cls._get_config().get("conversation.history_file", "conversation_history.json")
    
    @property
    def ARCHIVE_DIR(cls):
        return cls._get_config().get("conversation.archive_dir", "archive")
    
    @property
    def USER_PREFIX(cls):
        return "[用户]"
    
    @property
    def SYSTEM_PREFIX(cls):
        return "[系统]"
    
    @property
    def ASSISTANT_PREFIX(cls):
        return "[助手]"
    
    @property
    def MAX_HISTORY_CONTEXT(cls):
        return cls._get_config().get("context.max_context_messages", 50)
    
    @property
    def MAX_HISTORY_CONVERSATIONS(cls):
        return cls._get_config().get("context.max_history_conversations", 5)
    
    @property
    def PRESERVE_SYSTEM_PROMPTS(cls):
        return cls._get_config().get("context.preserve_system_prompts", True)
    
    @property
    def WEB_TIMEOUT(cls):
        return cls._get_config().get("web.timeout", 10)
    
    @property
    def WEB_DELAY(cls):
        return cls._get_config().get("web.delay", 0)
    
    @property
    def WEB_USER_AGENT(cls):
        return cls._get_config().get("web.user_agent", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    @property
    def WEB_MAX_DOWNLOAD_SIZE(cls):
        return cls._get_config().get("web.max_download_size", 104857600)
    
    @property
    def MEMORY_MAX_SEARCH_RESULTS(cls):
        return cls._get_config().get("memory.max_search_results", 100)
    
    @property
    def MEMORY_DEFAULT_IMPORTANCE(cls):
        return cls._get_config().get("memory.default_importance", 2)
    
    @property
    def MEMO_DEFAULT_REMINDER_MINUTES(cls):
        return cls._get_config().get("memo.default_reminder_minutes", 60)
    
    @property
    def MEMO_MAX_PER_CHECK(cls):
        return cls._get_config().get("memo.max_memos_per_check", 10)
    
    @property
    def LOG_FILE(cls):
        return os.path.expanduser(cls._get_config().get("system.log_file", "~/.aibox/ai.log"))
    
    @property
    def LOG_MAX_SIZE(cls):
        return cls._get_config().get("system.log_max_size", 10485760)
    
    @property
    def LOG_BACKUP_COUNT(cls):
        return cls._get_config().get("system.log_backup_count", 5)
    
    @property
    def COMMANDS_ENABLED(cls):
        return cls._get_config().get("commands.enabled", True)
    
    @property
    def WEBSOCKET_HOST(cls):
        return cls._get_config().get("system.websocket_host", "localhost")
    
    @property
    def WEBSOCKET_PORT(cls):
        return cls._get_config().get("system.websocket_port", 8765)
    
    @property
    def SCHEDULER_ENABLED(cls):
        return cls._get_config().get("scheduler.enabled", True)
    
    @property
    def SCHEDULER_CHECK_INTERVAL(cls):
        return cls._get_config().get("scheduler.check_interval", 1.0)
    
    @property
    def SCHEDULER_MAX_TASKS(cls):
        return cls._get_config().get("scheduler.max_tasks_per_run", 10)
    
    @property
    def SCHEDULER_BROADCAST(cls):
        return cls._get_config().get("scheduler.broadcast_enabled", True)
    
    @property
    def MEMO_ALLOW_USER_TASKS(cls):
        return cls._get_config().get("memo.allow_user_tasks", True)
    
    # 新增：压缩配置属性
    @property
    def COMPRESS_ENABLED(cls):
        return cls._get_config().get("context.compress_enabled", True)
    
    @property
    def COMPRESS_MESSAGE_THRESHOLD(cls):
        return cls._get_config().get("context.compress_message_threshold", 100)
    
    @property
    def COMPRESS_TOKEN_THRESHOLD(cls):
        return cls._get_config().get("context.compress_token_threshold", 4000)
    
    @property
    def COMPRESS_RATIO(cls):
        return cls._get_config().get("context.compress_ratio", 0.4)
    
    @property
    def COMPRESS_KEEP_RECENT(cls):
        return cls._get_config().get("context.compress_keep_recent", 20)



# 创建常量实例
constants = Constants()



# ==================== 日志系统 ====================

class Logger:
    """统一日志系统 - 支持文件和终端输出"""
    
    LEVELS = {
        "DEBUG": 3,
        "INFO": 2,
        "WARNING": 1,
        "ERROR": 0
    }
    
    _file_handler = None
    _log_initialized = False
    
    @classmethod
    def init_file_logging(cls, log_file: str = None, max_size: int = None, backup_count: int = None):
        """初始化文件日志"""
        if cls._log_initialized:
            return
        
        if log_file is None:
            log_file = constants.LOG_FILE
        if max_size is None:
            max_size = constants.LOG_MAX_SIZE
        if backup_count is None:
            backup_count = constants.LOG_BACKUP_COUNT
        
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        cls._file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        cls._file_handler.setFormatter(formatter)
        
        cls._log_initialized = True
    
    def __init__(self, name: str = "System", level: int = None):
        self.name = name
        config = ConfigManager()
        if level is None:
            level = config.get("system.debug_level", 1)
        self.level = level
        
        self.py_logger = logging.getLogger(f"AI.{name}")
        self.py_logger.setLevel(logging.DEBUG)
        
        if Logger._file_handler and not self.py_logger.handlers:
            self.py_logger.addHandler(Logger._file_handler)
    
    def debug(self, msg: str):
        if self.level >= 3:
            self._log("🐛", "DEBUG", msg)
            self.py_logger.debug(msg)
    
    def info(self, msg: str):
        if self.level >= 2:
            self._log("📋", "INFO", msg)
            self.py_logger.info(msg)
    
    def warning(self, msg: str):
        if self.level >= 1:
            self._log("⚠️", "WARNING", msg)
            self.py_logger.warning(msg)
    
    def error(self, msg: str):
        if self.level >= 0:
            self._log("❌", "ERROR", msg)
            self.py_logger.error(msg)
    
    def _log(self, emoji: str, level: str, msg: str):
        """输出到终端"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{emoji} [{timestamp}] [{self.name}] {msg}", flush=True)


# ==================== 对话压缩管理器（静默模式） ====================

class ConversationCompressor:
    """对话压缩管理器 - 通过调用语言模型进行智能压缩（静默执行，不输出信息）"""
    
    def __init__(self, ai: 'DeepSeekChat', logger: Logger = None):
        self.ai = ai
        self.logger = logger or Logger("Compressor")
        self.config = ConfigManager()
        # 压缩配置
        self.target_compression_ratio = 0.4  # 目标压缩到原来的40%
        self.max_compression_attempts = 3  # 最大压缩尝试次数
        self.min_messages_to_compress = 20  # 最少消息数才触发压缩
    
    def estimate_tokens(self, messages: List[Dict]) -> int:
        """估算消息的token数"""
        total_tokens = 0
        for msg in messages:
            content = msg.get("content", "")
            if content:
                # 估算token数
                chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
                english_words = len(re.findall(r'[a-zA-Z]+', content))
                other_chars = len(content) - chinese_chars - english_words
                
                estimated = chinese_chars * 1.5 + english_words * 1.3 + other_chars * 0.8
                total_tokens += estimated
                
                # 添加消息结构开销
                total_tokens += 10
            
            # 处理 tool_calls
            if msg.get("tool_calls"):
                total_tokens += 50
        
        return int(total_tokens)
    
    def should_compress(self, messages: List[Dict]) -> Tuple[bool, str]:
        """检查是否需要压缩对话（静默检查，不输出信息）"""
        if not constants.COMPRESS_ENABLED:
            return False, "压缩功能已禁用"
        
        # 分离系统消息和对话消息
        system_messages = [m for m in messages if m.get("role") == "system"]
        conversation_messages = [m for m in messages if m.get("role") != "system"]
        
        # 如果对话消息数量少于最小压缩阈值，不压缩
        if len(conversation_messages) <= self.min_messages_to_compress:
            return False, f"对话消息数量({len(conversation_messages)})小于压缩阈值({self.min_messages_to_compress})"
        
        # 只估算对话消息的 token 数
        token_count = self.estimate_tokens(conversation_messages)
        
        # 如果 token 数超过阈值，立即压缩
        if token_count >= constants.COMPRESS_TOKEN_THRESHOLD:
            return True, ""  # 不返回详细信息，静默压缩
        
        # 如果对话消息条数超过阈值，也压缩
        message_count = len(conversation_messages)
        if message_count >= constants.COMPRESS_MESSAGE_THRESHOLD:
            return True, ""  # 不返回详细信息，静默压缩
        
        return False, ""
    
    def _find_safe_cut_point(self, messages: List[Dict]) -> int:
        """
        找到安全的切割点，确保不会切断 tool_calls 对
        返回切割索引，切割点之前的部分可以被压缩
        """
        if not messages:
            return 0
        
        # 从后往前找，找到第一个安全的切割点
        # 安全的切割点意味着：切割点之后的消息不会依赖切割点之前的 tool_calls
        
        # 收集所有需要保护的索引（tool_calls 对）
        protected_indices = set()
        
        i = 0
        while i < len(messages):
            msg = messages[i]
            
            # 如果遇到 assistant 消息且包含 tool_calls
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                # 保护这条 assistant 消息
                protected_indices.add(i)
                
                # 收集所有 tool_call_id
                tool_call_ids = {tc.get("id") for tc in msg.get("tool_calls", []) if tc.get("id")}
                
                # 查找后续的 tool 消息
                j = i + 1
                found_tool_ids = set()
                while j < len(messages) and len(found_tool_ids) < len(tool_call_ids):
                    next_msg = messages[j]
                    if next_msg.get("role") == "tool":
                        tool_call_id = next_msg.get("tool_call_id")
                        if tool_call_id and tool_call_id in tool_call_ids:
                            found_tool_ids.add(tool_call_id)
                            protected_indices.add(j)
                        j += 1
                    else:
                        # 不是 tool 消息，停止查找
                        break
                
                i = j
            else:
                i += 1
        
        # 找到最后一个受保护消息的索引
        if protected_indices:
            last_protected = max(protected_indices)
            # 切割点应该在最后一个受保护消息之后
            return last_protected + 1
        
        return 0
    
    def _extract_compressible_messages(self, messages: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        提取可以被压缩的消息和必须保留的消息
        返回 (可压缩消息列表, 必须保留消息列表)
        """
        if not messages:
            return [], []
        
        # 找到安全切割点
        safe_cut_point = self._find_safe_cut_point(messages)
        
        # 如果没有安全的切割点，或者切割点太靠后，保留最近的消息
        keep_recent = constants.COMPRESS_KEEP_RECENT
        
        if safe_cut_point > 0 and len(messages) - safe_cut_point >= keep_recent:
            # 切割点之后的都保留
            compressible = messages[:safe_cut_point]
            keep = messages[safe_cut_point:]
        else:
            # 保留最近的消息，之前的可能被压缩
            keep = messages[-keep_recent:] if len(messages) > keep_recent else messages
            compressible = messages[:len(messages) - len(keep)]
        
        # 进一步清理：确保 compressible 中的消息不会与 keep 中的消息形成 tool_calls 对
        # 检查 keep 中是否有 tool 消息，其对应的 assistant 在 compressible 中
        if keep and compressible:
            tool_ids_in_keep = set()
            for msg in keep:
                if msg.get("role") == "tool":
                    tool_call_id = msg.get("tool_call_id")
                    if tool_call_id:
                        tool_ids_in_keep.add(tool_call_id)
            
            # 如果 keep 中有 tool 消息，需要确保对应的 assistant 也在 keep 中
            if tool_ids_in_keep:
                # 找到 compressible 中对应的 assistant 消息，移动到 keep
                new_compressible = []
                for msg in compressible:
                    if msg.get("role") == "assistant" and msg.get("tool_calls"):
                        msg_tool_ids = {tc.get("id") for tc in msg.get("tool_calls", []) if tc.get("id")}
                        if msg_tool_ids & tool_ids_in_keep:
                            # 这个 assistant 消息应该保留
                            keep.insert(0, msg)
                        else:
                            new_compressible.append(msg)
                    else:
                        new_compressible.append(msg)
                compressible = new_compressible
        
        return compressible, keep
    
    def _build_compression_prompt(self, messages: List[Dict]) -> str:
        """构建用于压缩的提示词，正确处理工具调用内容"""
        # 构建对话内容，过滤掉工具调用的技术细节
        conversation_lines = []
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            if role == "user":
                if content:
                    conversation_lines.append(f"用户: {content}")
            
            elif role == "assistant":
                # 处理 assistant 消息
                if content:
                    conversation_lines.append(f"助手: {content}")
                
                # 处理 tool_calls - 提取有用的信息
                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    args = func.get("arguments", "{}")
                    if tool_name:
                        try:
                            args_dict = json.loads(args) if args else {}
                            # 简化参数显示
                            args_preview = str(args_dict)[:100]
                            conversation_lines.append(f"[调用工具: {tool_name}，参数: {args_preview}]")
                        except:
                            conversation_lines.append(f"[调用工具: {tool_name}]")
            
            elif role == "tool":
                # 工具返回结果 - 提取有效内容
                if content:
                    # 尝试解析工具返回的内容，提取有用的信息
                    useful_content = self._extract_useful_content(content)
                    if useful_content:
                        conversation_lines.append(f"[工具返回: {useful_content}]")
        
        conversation_text = "\n".join(conversation_lines)
        
        # 限制输入长度
        max_input_chars = 8000
        if len(conversation_text) > max_input_chars:
            head_size = int(max_input_chars * 0.6)
            tail_size = int(max_input_chars * 0.4)
            conversation_text = conversation_text[:head_size] + "\n...(中间部分已省略)...\n" + conversation_text[-tail_size:]
        
        prompt = f"""请对以下对话内容进行智能压缩和总结。要求：

1. **提取核心信息**：对话的主要主题、关键问题、重要结论、用户需求
2. **保留重要细节**：用户的重要要求、AI的重要回复、达成的共识、任务执行结果
3. **忽略技术细节**：工具调用的技术参数、中间过程可以简化，只保留结果
4. **结构化输出**：使用清晰的段落结构，分点说明重要内容
5. **目标长度**：压缩后的内容约为原文的30%-40%

对话内容：
---
{conversation_text}
---

请输出压缩后的对话摘要："""
        
        return prompt
    
    def _build_partial_compression_prompt(self, compressible_messages: List[Dict], keep_messages: List[Dict]) -> str:
        """构建部分压缩的提示词"""
        # 构建要压缩的对话内容
        compress_text = self._build_conversation_text(compressible_messages)
        
        # 构建保留的最近消息
        keep_text = self._build_conversation_text(keep_messages)
        
        # 限制输入长度
        max_input_chars = 8000
        if len(compress_text) > max_input_chars:
            head_size = int(max_input_chars * 0.6)
            tail_size = int(max_input_chars * 0.4)
            compress_text = compress_text[:head_size] + "\n...(中间部分已省略)...\n" + compress_text[-tail_size:]
        
        prompt = f"""请对以下对话的早期部分进行压缩总结，保留最近的消息不变。

**需要压缩的早期对话**：
---
{compress_text}
---

**保留不变的最近消息**：
---
{keep_text}
---

压缩要求：
1. 只压缩"需要压缩的早期对话"部分，生成一个简洁的摘要
2. 摘要应该包含早期对话的核心内容、关键信息、重要结论
3. 忽略工具调用的技术细节，只保留执行结果
4. 输出格式：先输出早期对话的摘要，然后输出保留的最近消息

请输出压缩后的完整对话："""
        
        return prompt
    
    def _build_conversation_text(self, messages: List[Dict]) -> str:
        """将消息列表转换为可读的对话文本"""
        lines = []
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            if role == "user":
                if content:
                    lines.append(f"用户: {content}")
            
            elif role == "assistant":
                if content:
                    lines.append(f"助手: {content}")
                
                # 处理 tool_calls
                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    if tool_name:
                        lines.append(f"[工具调用: {tool_name}]")
            
            elif role == "tool":
                if content:
                    useful = self._extract_useful_content(content)
                    if useful:
                        lines.append(f"[工具结果: {useful}]")
        
        return "\n".join(lines)
    
    def _extract_useful_content(self, content: str) -> str:
        """从工具返回内容中提取有用信息"""
        if not content:
            return ""
        
        # 检查是否是成功消息
        if "✅" in content:
            # 提取成功信息
            lines = content.split("\n")
            useful_lines = []
            for line in lines:
                # 跳过技术细节
                if "---" in line:
                    continue
                if "路径:" in line or "路径" in line:
                    continue
                if "大小:" in line or "大小" in line:
                    continue
                if "字节" in line:
                    continue
                # 保留有用的信息
                if "✅" in line or "成功" in line or "完成" in line:
                    useful_lines.append(line.strip())
            
            if useful_lines:
                return "; ".join(useful_lines[:3])
        
        # 检查是否是错误消息
        if "❌" in content:
            # 提取错误信息
            lines = content.split("\n")
            for line in lines:
                if "❌" in line:
                    return line.strip()
        
        # 如果是纯文本，返回前100个字符
        if len(content) > 100:
            return content[:100] + "..."
        
        return content
    
    def _compress_via_llm(self, compressible_messages: List[Dict], keep_messages: List[Dict]) -> Optional[List[Dict]]:
        """
        通过语言模型压缩消息
        返回压缩后的消息列表
        """
        if not compressible_messages:
            # 如果没有需要压缩的消息，直接返回保留的消息
            return keep_messages
        
        # 构建提示词
        if keep_messages:
            prompt = self._build_partial_compression_prompt(compressible_messages, keep_messages)
        else:
            prompt = self._build_compression_prompt(compressible_messages)
        
        self.logger.debug(f"正在调用语言模型压缩对话 (压缩 {len(compressible_messages)} 条，保留 {len(keep_messages)} 条)...")
        
        try:
            # 获取API配置
            api_key = self.ai.api_key
            api_url = constants.DEEPSEEK_API_URL
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": constants.DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "你是一个专业的对话摘要助手，擅长提取对话核心信息并进行结构化总结。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1500
            }
            
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result["choices"][0]["message"]["content"].strip()
                
                if summary:
                    # 返回压缩后的消息
                    compressed_messages = [
                        {
                            "role": "system",
                            "content": i18n.get('compressed_summary', summary)
                        }
                    ]
                    # 如果还有保留的消息，追加在后面
                    if keep_messages:
                        compressed_messages.extend(keep_messages)
                    
                    self.logger.debug("语言模型压缩成功")
                    return compressed_messages
                else:
                    self.logger.debug("语言模型返回空摘要")
                    return None
            else:
                self.logger.debug(f"语言模型压缩失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"语言模型压缩异常: {e}")
            return None
    
    def compress_conversation(self, messages: List[Dict]) -> List[Dict]:
        """
        压缩对话内容 - 通过调用语言模型进行智能压缩（静默执行）
        
        策略：
        1. 分离系统消息和对话消息
        2. 识别并保护 tool_calls 对不被分离
        3. 提取可以被压缩的消息（不包含 tool_calls 对）
        4. 调用语言模型生成摘要
        5. 如果一次压缩不完，只压缩其中一部分，保留最近的消息
        """
        if not messages:
            return messages
        
        # 分离系统消息和对话消息 - 系统消息必须完整保留
        system_messages = []
        conversation_messages = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system_messages.append(msg)
            else:
                conversation_messages.append(msg)
        
        # 如果没有对话消息，只返回系统消息
        if not conversation_messages:
            return system_messages
        
        original_count = len(conversation_messages)
        self.logger.debug(f"原始对话消息数: {original_count}")
        
        # 尝试通过语言模型压缩
        compressed_result = None
        attempt = 0
        
        # 创建当前要处理的消息列表
        current_messages = conversation_messages.copy()
        
        while attempt < self.max_compression_attempts:
            attempt += 1
            self.logger.debug(f"压缩尝试 {attempt}/{self.max_compression_attempts}")
            
            # 分离可以被压缩的消息和必须保留的消息
            compressible, keep = self._extract_compressible_messages(current_messages)
            
            # 如果没有可以压缩的消息，或者压缩后不会减少，退出
            if not compressible or len(compressible) == 0:
                self.logger.debug("没有可以压缩的消息")
                compressed_result = current_messages
                break
            
            # 检查压缩比例
            if len(compressible) < 5:
                self.logger.debug("可压缩消息太少，停止压缩")
                compressed_result = current_messages
                break
            
            self.logger.debug(f"可压缩: {len(compressible)} 条, 保留: {len(keep)} 条")
            
            # 调用语言模型压缩
            compressed = self._compress_via_llm(compressible, keep)
            
            if compressed:
                # 压缩成功
                compressed_result = compressed
                
                # 检查压缩效果
                compressed_count = len(compressed)
                self.logger.debug(f"压缩后: {compressed_count} 条消息")
                
                # 如果压缩效果不明显，且还有空间，继续压缩
                if compressed_count > original_count * 0.6 and attempt < self.max_compression_attempts:
                    self.logger.debug("压缩效果不明显，继续压缩")
                    current_messages = compressed
                    continue
                else:
                    break
            else:
                # 压缩失败，尝试减少保留的消息数量
                self.logger.debug("压缩失败，尝试调整策略")
                # 减少保留的消息数量
                current_keep = len(keep)
                if current_keep > 5:
                    # 在 keep 中进一步分离
                    new_compressible, new_keep = self._extract_compressible_messages(keep)
                    if new_compressible:
                        current_messages = keep
                        continue
                break
        
        # 如果所有压缩尝试都失败，返回原始消息（但确保结构完整）
        if compressed_result is None:
            self.logger.warning("语言模型压缩失败，保留原始对话")
            compressed_result = conversation_messages
        
        # 合并系统消息和压缩后的对话消息
        compressed_messages = system_messages + compressed_result
        
        # 记录压缩结果（仅日志，不输出到用户）
        final_count = len([m for m in compressed_messages if m.get("role") != "system"])
        self.logger.debug(i18n.get('conversation_compressed', original_count, final_count))
        
        return compressed_messages
    
    def force_compress(self, messages: List[Dict]) -> List[Dict]:
        """强制压缩 - 即使消息不多也进行压缩"""
        if not messages:
            return messages
        
        # 保存原始压缩设置
        original_min_messages = self.min_messages_to_compress
        self.min_messages_to_compress = 0
        
        try:
            return self.compress_conversation(messages)
        finally:
            self.min_messages_to_compress = original_min_messages

# ==================== 备忘录数据库 ====================

class MemoDatabase:
    """备忘录数据库 - 存储和管理任务"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(constants.SAVE_DIR, constants.MEMORY_DB)
        
        # 确保目录存在
        os.makedirs(constants.SAVE_DIR, exist_ok=True)
        self.db_path = db_path
        self.logger = Logger("MemoDB")
        self._init_database()
    
    def _init_database(self):
        """初始化备忘录表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT,
                    created_at TEXT NOT NULL,
                    reminder_time TEXT,
                    completed_at TEXT,
                    is_completed INTEGER DEFAULT 0,
                    tags TEXT,
                    priority INTEGER DEFAULT 1,
                    created_by TEXT,
                    source TEXT,
                    repeat_type TEXT DEFAULT 'none',
                    repeat_interval INTEGER DEFAULT 0,
                    repeat_interval_unit TEXT DEFAULT 'days',
                    repeat_end_time TEXT,
                    last_triggered_at TEXT,
                    trigger_count INTEGER DEFAULT 0,
                    is_immediate INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_memos_reminder 
                ON memos(reminder_time) WHERE is_completed = 0
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_memos_immediate
                ON memos(is_immediate) WHERE is_immediate = 1 AND is_completed = 0
            ''')
            
            conn.commit()
        
        self.logger.info("任务表初始化完成")
    
    def add_memo(self, title: str, content: str = None, reminder_time: str = None,
                 tags: List[str] = None, priority: int = 1, created_by: str = None,
                 source: str = None,
                 repeat_type: str = 'none', repeat_interval: int = 0,
                 repeat_interval_unit: str = 'days', repeat_end_time: str = None,
                 is_immediate: bool = False) -> int:
        """添加任务 - 所有任务都是对话任务，不再需要metadata和任务类型"""
        created_at = datetime.now().strftime(constants.DATETIME_FORMAT)
        tags_str = ",".join(tags) if tags else ""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO memos 
                (title, content, created_at, reminder_time, tags, priority, created_by, 
                 is_completed, source, repeat_type, repeat_interval, repeat_interval_unit,
                 repeat_end_time, is_immediate)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
            ''', (title, content, created_at, reminder_time, tags_str, priority, created_by,
                  source, repeat_type, repeat_interval, repeat_interval_unit,
                  repeat_end_time, 1 if is_immediate else 0))
            
            memo_id = cursor.lastrowid
            conn.commit()
        
        repeat_info = f" (重复: {repeat_type}"
        if repeat_type == 'custom':
            repeat_info += f", 每{repeat_interval} {repeat_interval_unit}"
        repeat_info += ")"
        immediate_info = " (即时任务)" if is_immediate else ""
        self.logger.info(i18n.get('task_added', title, memo_id) + repeat_info + immediate_info)
        return memo_id
    
    def get_memo(self, memo_id: int) -> Optional[Dict]:
        """获取单个任务"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM memos WHERE id = ?', (memo_id,))
            row = cursor.fetchone()
            
            if row:
                memo = dict(row)
                if memo.get('tags'):
                    memo['tags'] = memo['tags'].split(',')
                return memo
        return None

    def get_pending_memos(self, limit: int = None, before_time: str = None, include_immediate: bool = False) -> List[Dict]:
        """获取待执行的任务 - 严格使用当前时间比较"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 使用当前时间作为基准
            now = datetime.now().strftime(constants.DATETIME_FORMAT)
            
            # 如果传入了 before_time，使用它，否则使用当前时间
            compare_time = before_time if before_time else now
            
            query = '''
                SELECT * FROM memos 
                WHERE is_completed = 0
                AND reminder_time IS NOT NULL
                AND reminder_time <= ?  -- 严格小于等于比较时间
                AND (repeat_end_time IS NULL OR repeat_end_time >= ?)
            '''
            
            if not include_immediate:
                query += ' AND is_immediate = 0'
            
            query += ' ORDER BY reminder_time ASC, priority DESC'
            
            params = [compare_time, compare_time]
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                memo = dict(row)
                if memo.get('tags'):
                    memo['tags'] = memo['tags'].split(',')
                
                # 【关键修复】二次验证：确保 reminder_time 确实 <= 当前时间
                if memo.get('reminder_time'):
                    try:
                        reminder_time = datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT)
                        current_time = datetime.strptime(compare_time, constants.DATETIME_FORMAT)
                        if reminder_time <= current_time:
                            results.append(memo)
                        else:
                            # 调试日志
                            self.logger.debug(f"过滤掉未到期任务 #{memo['id']}: {memo['reminder_time']} > {compare_time}")
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"解析任务 #{memo['id']} 的提醒时间失败: {e}")
                else:
                    # 没有提醒时间的任务不应该在待执行列表中
                    self.logger.warning(f"任务 #{memo['id']} 没有提醒时间，但被返回为待执行")
            
            return results

    def get_immediate_memos(self, limit: int = None) -> List[Dict]:
        """获取待执行的即时任务"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM memos 
                WHERE is_completed = 0
                AND is_immediate = 1
                ORDER BY created_at ASC
            '''
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query)
            
            results = []
            for row in cursor.fetchall():
                memo = dict(row)
                if memo.get('tags'):
                    memo['tags'] = memo['tags'].split(',')
                results.append(memo)
            
            return results
    
    def get_overdue_memos(self, limit: int = None) -> List[Dict]:
        """获取已过期的任务"""
        now = datetime.now().strftime(constants.DATETIME_FORMAT)
        return self.get_pending_memos(limit=limit, before_time=now)
    
    def get_all_memos(self, include_completed: bool = False, limit: int = 50) -> List[Dict]:
        """获取所有任务"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if include_completed:
                cursor.execute('''
                    SELECT * FROM memos 
                    ORDER BY 
                        CASE WHEN is_completed = 0 THEN 0 ELSE 1 END,
                        reminder_time ASC,
                        created_at DESC
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT * FROM memos 
                    WHERE is_completed = 0
                    ORDER BY reminder_time ASC, priority DESC, created_at DESC
                    LIMIT ?
                ''', (limit,))
            
            results = []
            for row in cursor.fetchall():
                memo = dict(row)
                if memo.get('tags'):
                    memo['tags'] = memo['tags'].split(',')
                results.append(memo)
            
            return results
    
    def mark_as_triggered(self, memo_id: int) -> Optional[str]:
        """标记任务已被触发，并根据重复规则计算下一次提醒时间"""
        memo = self.get_memo(memo_id)
        if not memo:
            return None
        
        now = datetime.now()
        next_reminder = None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE memos 
                SET last_triggered_at = ?, trigger_count = trigger_count + 1
                WHERE id = ?
            ''', (now.strftime(constants.DATETIME_FORMAT), memo_id))
            
            # 处理重复任务
            if memo['repeat_type'] != 'none' and not self._should_end_repeat(memo, now):
                # 使用当前时间作为基准来计算下一次执行时间
                next_reminder = self._calculate_next_reminder(memo, now)
                
                if next_reminder:
                    cursor.execute('''
                        UPDATE memos 
                        SET reminder_time = ?
                        WHERE id = ?
                    ''', (next_reminder.strftime(constants.DATETIME_FORMAT), memo_id))
                    
                    self.logger.info(f"任务 #{memo_id} 已更新下一次执行时间: {next_reminder}")
                else:
                    # 重复结束，标记为完成
                    cursor.execute('''
                        UPDATE memos 
                        SET is_completed = 1, completed_at = ?
                        WHERE id = ?
                    ''', (now.strftime(constants.DATETIME_FORMAT), memo_id))
                    
                    self.logger.info(f"任务 #{memo_id} 重复结束，已标记为完成")
            elif memo['is_immediate']:
                # 即时任务执行后标记为完成
                cursor.execute('''
                    UPDATE memos 
                    SET is_completed = 1, completed_at = ?
                    WHERE id = ?
                ''', (now.strftime(constants.DATETIME_FORMAT), memo_id))
                
                self.logger.info(f"即时任务 #{memo_id} 已完成")
            else:
                # 一次性任务，标记为完成
                cursor.execute('''
                    UPDATE memos 
                    SET is_completed = 1, completed_at = ?
                    WHERE id = ?
                ''', (now.strftime(constants.DATETIME_FORMAT), memo_id))
                
                self.logger.info(f"任务 #{memo_id} 已完成")
            
            conn.commit()
        
        return next_reminder.strftime(constants.DATETIME_FORMAT) if next_reminder else None
    
    def _should_end_repeat(self, memo: Dict, current_time: datetime) -> bool:
        """检查是否应该结束重复"""
        if memo['repeat_end_time']:
            end_time = datetime.strptime(memo['repeat_end_time'], constants.DATETIME_FORMAT)
            if current_time > end_time:
                return True
        return False
    
    def _calculate_next_reminder(self, memo: Dict, current_time: datetime) -> Optional[datetime]:
        """
        计算下一次提醒时间，使用当前时间作为基准
        支持分钟、小时、天为单位
        """
        if memo['repeat_type'] == 'daily':
            # 每天重复：当前时间 + 1天
            next_time = current_time + timedelta(days=1)
        elif memo['repeat_type'] == 'weekly':
            # 每周重复：当前时间 + 7天
            next_time = current_time + timedelta(weeks=1)
        elif memo['repeat_type'] == 'monthly':
            # 每月重复：尝试在当前时间上加一个月
            try:
                # 处理月份进位
                if current_time.month == 12:
                    next_time = current_time.replace(year=current_time.year + 1, month=1)
                else:
                    next_time = current_time.replace(month=current_time.month + 1)
            except ValueError:
                # 处理月份天数问题（如1月31日加一个月）
                if current_time.month == 12:
                    next_time = current_time.replace(year=current_time.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    next_time = current_time.replace(month=current_time.month + 1, day=1) - timedelta(days=1)
        elif memo['repeat_type'] == 'custom' and memo['repeat_interval'] > 0:
            unit = memo.get('repeat_interval_unit', 'days')
            if unit == 'minutes':
                # 每N分钟重复：当前时间 + N分钟
                next_time = current_time + timedelta(minutes=memo['repeat_interval'])
            elif unit == 'hours':
                # 每N小时重复：当前时间 + N小时
                next_time = current_time + timedelta(hours=memo['repeat_interval'])
            else:  # days
                # 每N天重复：当前时间 + N天
                next_time = current_time + timedelta(days=memo['repeat_interval'])
        else:
            return None
        
        # 检查是否超过重复结束时间
        if memo['repeat_end_time']:
            end_time = datetime.strptime(memo['repeat_end_time'], constants.DATETIME_FORMAT)
            if next_time > end_time:
                return None
        
        return next_time
    
    def complete_memo(self, memo_id: int, force_complete: bool = False) -> bool:
        """完成任务"""
        memo = self.get_memo(memo_id)
        if not memo:
            return False
        
        if memo['repeat_type'] != 'none' and not force_complete:
            self.mark_as_triggered(memo_id)
            return True
        
        completed_at = datetime.now().strftime(constants.DATETIME_FORMAT)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE memos 
                SET is_completed = 1, completed_at = ?
                WHERE id = ? AND is_completed = 0
            ''', (completed_at, memo_id))
            
            affected = cursor.rowcount
            conn.commit()
        
        if affected > 0:
            self.logger.info(i18n.get('memo_completed', memo_id))
            return True
        return False
    
    def get_memo_stats(self) -> Dict:
        """获取任务统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM memos')
            total = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM memos WHERE is_completed = 0')
            pending = cursor.fetchone()[0]
            
            now = datetime.now().strftime(constants.DATETIME_FORMAT)
            cursor.execute('''
                SELECT COUNT(*) FROM memos 
                WHERE is_completed = 0
                AND reminder_time <= ?
                AND is_immediate = 0
            ''', (now,))
            overdue = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM memos WHERE is_completed = 1')
            completed = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM memos WHERE is_immediate = 1 AND is_completed = 0')
            immediate = cursor.fetchone()[0]
            
            return {
                "total": total,
                "pending": pending,
                "overdue": overdue,
                "completed": completed,
                "immediate": immediate
            }
    
    def add_user_task(self, title: str, content: str = None, reminder_time: str = None,
                     repeat_type: str = 'none', repeat_interval: int = 0, 
                     repeat_interval_unit: str = 'days', is_immediate: bool = False) -> int:
        """添加用户任务（前端直接调用的任务）- 所有任务都是对话任务"""
        if not constants.MEMO_ALLOW_USER_TASKS:
            raise Exception("用户任务功能已禁用")
        
        return self.add_memo(
            title=title,
            content=content,
            reminder_time=reminder_time,
            repeat_type=repeat_type,
            repeat_interval=repeat_interval,
            repeat_interval_unit=repeat_interval_unit,
            created_by="user",
            source="websocket",
            is_immediate=is_immediate
        )
    
    def get_pending_tasks_for_user(self) -> List[Dict]:
        """获取待执行任务列表（用于前端显示）"""
        pending = self.get_pending_memos(include_immediate=False)
        immediate = self.get_immediate_memos()
        result = []
        
        now = datetime.now()
        for memo in pending + immediate:
            result.append({
                "id": memo['id'],
                "title": memo['title'],
                "content": memo['content'],
                "reminder_time": memo['reminder_time'],
                "priority": memo['priority'],
                "is_overdue": datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT) < now if memo['reminder_time'] else False,
                "repeat_type": memo['repeat_type'],
                "repeat_interval": memo.get('repeat_interval', 0),
                "repeat_interval_unit": memo.get('repeat_interval_unit', 'days'),
                "trigger_count": memo.get('trigger_count', 0),
                "is_immediate": memo.get('is_immediate', False)
            })
        
        return result


# ==================== 记忆数据库 ====================

class MemoryDatabase:
    """记忆数据库 - 存储重要的对话记忆"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(constants.SAVE_DIR, constants.MEMORY_DB)
        
        # 确保目录存在
        os.makedirs(constants.SAVE_DIR, exist_ok=True)
        self.db_path = db_path
        self.logger = Logger("MemoryDB")
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    content TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    tags TEXT,
                    importance INTEGER DEFAULT 1
                )
            ''')
            
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
                USING fts5(topic, summary, content, tags, content=memories)
            ''')
            
            conn.commit()
    
    def add_memory(self, topic: str, summary: str, content: str = None, 
                   start_time: str = None, end_time: str = None, 
                   tags: List[str] = None, importance: int = None) -> int:
        """添加记忆到数据库"""
        if start_time is None:
            start_time = datetime.now().strftime(constants.DATETIME_FORMAT)
        if end_time is None:
            end_time = datetime.now().strftime(constants.DATETIME_FORMAT)
        if importance is None:
            importance = constants.MEMORY_DEFAULT_IMPORTANCE
        
        tags_str = ",".join(tags) if tags else ""
        created_at = datetime.now().strftime(constants.DATETIME_FORMAT)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO memories (topic, summary, content, start_time, end_time, created_at, tags, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (topic, summary, content, start_time, end_time, created_at, tags_str, importance))
            
            memory_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO memories_fts (rowid, topic, summary, content, tags)
                VALUES (?, ?, ?, ?, ?)
            ''', (memory_id, topic, summary, content or "", tags_str))
            
            conn.commit()
            
        self.logger.info(f"已添加记忆: {topic} (ID: {memory_id})")
        return memory_id
    
    def delete_memory(self, memory_id: int) -> bool:
        """删除记忆"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
            deleted = cursor.rowcount > 0
            
            if deleted:
                cursor.execute('DELETE FROM memories_fts WHERE rowid = ?', (memory_id,))
                conn.commit()
                self.logger.info(f"已删除记忆 ID: {memory_id}")
            
            return deleted
    
    def search_memories(self, keywords: List[str], match_all: bool = False, limit: int = None) -> List[Dict]:
        """多关键词模糊搜索记忆"""
        if not keywords:
            return []
        
        if limit is None:
            limit = constants.MEMORY_MAX_SEARCH_RESULTS
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if match_all:
                query = " AND ".join([f'"{kw}"' for kw in keywords])
            else:
                query = " OR ".join([f'"{kw}"' for kw in keywords])
            
            cursor.execute('''
                SELECT m.*, rank 
                FROM memories m
                JOIN memories_fts f ON m.rowid = f.rowid
                WHERE memories_fts MATCH ?
                ORDER BY m.end_time DESC, rank, m.importance DESC
                LIMIT ?
            ''', (query, limit))
            
            results = []
            for row in cursor.fetchall():
                memory = dict(row)
                if memory.get('tags'):
                    memory['tags'] = memory['tags'].split(',')
                results.append(memory)
            
        return results
    
    def get_recent_memories(self, limit: int = 10) -> List[Dict]:
        """获取最近的记忆"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM memories ORDER BY end_time DESC LIMIT ?', (limit,))
            
            results = []
            for row in cursor.fetchall():
                memory = dict(row)
                if memory.get('tags'):
                    memory['tags'] = memory['tags'].split(',')
                results.append(memory)
            
        return results
    
    def get_memory_by_id(self, memory_id: int) -> Optional[Dict]:
        """根据ID获取记忆"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM memories WHERE id = ?', (memory_id,))
            row = cursor.fetchone()
            
            if row:
                memory = dict(row)
                if memory.get('tags'):
                    memory['tags'] = memory['tags'].split(',')
                return memory
        return None
    
    def delete_memories_by_ids(self, memory_ids: List[int]) -> int:
        """批量删除记忆"""
        if not memory_ids:
            return 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(memory_ids))
            cursor.execute(f'DELETE FROM memories WHERE id IN ({placeholders})', memory_ids)
            deleted_count = cursor.rowcount
            
            if deleted_count > 0:
                cursor.execute(f'DELETE FROM memories_fts WHERE rowid IN ({placeholders})', memory_ids)
                conn.commit()
                self.logger.info(f"已批量删除 {deleted_count} 条记忆")
            
            return deleted_count


# ==================== 任务调度器 ====================

class TaskScheduler:
    """任务调度器 - 基于备忘录数据库的定时任务系统"""
    
    def __init__(self, loop: asyncio.AbstractEventLoop = None, logger: Logger = None):
        self.loop = loop or asyncio.get_event_loop()
        self.running = False
        self.logger = logger or Logger("TaskScheduler")
        self.check_interval = constants.SCHEDULER_CHECK_INTERVAL
        self.max_tasks_per_run = constants.SCHEDULER_MAX_TASKS
        self.broadcast_enabled = constants.SCHEDULER_BROADCAST
        self.ws_handler = None  # 将由管理器设置
        self.ai_manager = None  # 新增：AI管理器引用
        
        # 任务执行历史
        self.execution_history = []
        self.max_history = 100
        
        self.logger.info(i18n.get('scheduler_started'))
    
    def set_websocket_handler(self, handler):
        """设置WebSocket处理器，用于广播任务执行状态"""
        self.ws_handler = handler
    
    def set_ai_manager(self, manager):
        """设置AI管理器引用"""
        self.ai_manager = manager
    
    async def broadcast_task_status(self, task: Dict, status: str, message: str = None):
        """广播任务状态到所有连接的客户端"""
        if not self.broadcast_enabled or not self.ws_handler:
            return
        
        try:
            # 确保task有必要的字段
            task_info = {
                'id': task.get('id', 0),
                'title': task.get('title', '未知任务')
            }
            await self.ws_handler.broadcast_task_status(task_info, status, message)
        except Exception as e:
            self.logger.error(f"广播任务状态失败: {e}")

    async def check_and_execute_tasks(self, memo_db: MemoDatabase):
        """检查并执行到期的任务 - 触发AI对话"""
        if not memo_db:
            return []
        
        try:
            # 获取所有到期任务（不包括即时任务）
            now = datetime.now()
            now_str = now.strftime(constants.DATETIME_FORMAT)
            
            pending = memo_db.get_pending_memos(
                limit=self.max_tasks_per_run,
                before_time=now_str,
                include_immediate=False
            )
            
            if not pending:
                return []
            
            self.logger.info(i18n.get('overdue_found', len(pending)))
            
            # 广播任务开始执行
            if self.broadcast_enabled and self.ws_handler:
                await self.ws_handler.broadcast_task_status(
                    {"id": 0, "title": "批量任务"},
                    "batch_start",
                    f"开始执行 {len(pending)} 个任务"
                )
            
            executed_tasks = []
            for memo in pending:
                try:
                    # 广播任务开始执行
                    if self.ws_handler:
                        await self.ws_handler.broadcast_task_status(memo, "executing", i18n.get('task_executing', memo['title'], memo['id']))
                    
                    # 【关键修复】执行前最后一次验证
                    if memo.get('reminder_time'):
                        reminder_time = datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT)
                        if reminder_time > now:
                            self.logger.warning(f"任务 #{memo['id']} 的提醒时间 ({memo['reminder_time']}) 大于当前时间 ({now_str})，跳过执行")
                            continue
                    
                    # 先标记任务已被触发
                    self.logger.info(f"标记任务 #{memo['id']} 为已触发")
                    next_time = memo_db.mark_as_triggered(memo['id'])
                    
                    # 执行任务
                    result = await self.execute_task_as_conversation(memo, memo_db)
                    
                    # 广播任务完成
                    if self.ws_handler:
                        await self.ws_handler.broadcast_task_status(memo, "complete", result)
                    
                    executed_tasks.append({
                        "id": memo['id'],
                        "title": memo['title'],
                        "result": result,
                        "success": True,
                        "next_time": next_time
                    })
                    
                except Exception as e:
                    self.logger.error(i18n.get('task_failed', memo['title'], str(e)))
                    
                    # 广播任务失败
                    if self.ws_handler:
                        await self.ws_handler.broadcast_task_status(memo, "failed", str(e))
                    
                    executed_tasks.append({
                        "id": memo['id'],
                        "title": memo['title'],
                        "error": str(e),
                        "success": False
                    })
            
            # 广播任务执行完成
            if self.broadcast_enabled and self.ws_handler:
                success_count = sum(1 for t in executed_tasks if t['success'])
                await self.ws_handler.broadcast_task_status(
                    {"id": 0, "title": "批量任务"},
                    "batch_complete",
                    f"执行完成: {success_count}/{len(executed_tasks)} 个任务成功"
                )
            
            return executed_tasks
            
        except Exception as e:
            self.logger.error(f"检查任务失败: {e}")
            return []
        
    async def execute_task_as_conversation(self, memo: Dict, memo_db: MemoDatabase) -> str:
        """执行任务 - 将备忘录内容作为用户输入触发AI对话，收集完整的过程回复"""
        self.logger.info(i18n.get('task_executing', memo['title'], memo['id']))
        
        # 生成唯一的执行ID（基于任务ID和时间戳）
        execution_id = f"{memo['id']}_{int(time.time())}_{memo.get('trigger_count', 0) + 1}"
        
        # 记录执行历史
        self.execution_history.append({
            "id": memo['id'],
            "execution_id": execution_id,
            "title": memo['title'],
            "time": datetime.now().strftime(constants.DATETIME_FORMAT),
            "trigger_count": memo.get('trigger_count', 0) + 1
        })
        
        # 限制历史记录大小
        if len(self.execution_history) > self.max_history:
            self.execution_history = self.execution_history[-self.max_history:]
        
        # 构建用户输入内容 - 将任务作为对话触发
        user_input = f"[定时任务] {memo['title']}"
        if memo['content']:
            user_input += f"\n\n任务内容: {memo['content']}"
        
        # 添加专注提示词，让AI专注于当前任务
        focus_prompt = f"""
    【重要提示】
    这是由定时任务触发的对话，请遵守以下要求：
    1. 专注于处理当前任务：{memo['title']}
    2. 根据任务内容进行适当的操作和回答
    3. 任务处理完成后，如果不需要继续对话，可以结束对话
    4. 系统已经自动更新了任务状态（更新了执行时间和次数），你不需要手动处理任务完成逻辑

    请现在开始处理这个任务。
    """
        user_input = focus_prompt + "\n\n" + user_input
        
        result = "任务已触发AI对话"
        
        # 如果有AI管理器，触发AI对话
        if self.ai_manager and self.ai_manager.ai:
            try:
                # 获取当前事件循环
                loop = asyncio.get_running_loop()
                
                # 创建一个队列来收集完整的响应
                full_response_queue = queue.Queue()
                
                # 定义输出回调函数 - 直接广播，同时收集
                def output_callback(msg_type, content):
                    """AI输出的回调函数 - 直接广播，同时收集"""
                    # 收集完整响应
                    if msg_type == "complete":
                        full_response_queue.put(content)
                    
                    # 直接广播给所有客户端 - 必须带上 task_id 和 execution_id
                    if self.ws_handler and self.broadcast_enabled:
                        # 使用 run_coroutine_threadsafe 在正确的循环中运行异步函数
                        asyncio.run_coroutine_threadsafe(
                            self.ws_handler.broadcast({
                                "type": "task_process",
                                "task_id": str(memo['id']),  # 原始任务ID
                                "execution_id": execution_id,  # 唯一的执行ID
                                "task_title": memo['title'],
                                "msg_type": msg_type,
                                "content": content,
                                "is_new_execution": msg_type == "chunk",  # 标记是否为新的执行
                                "timestamp": datetime.now().strftime(constants.DATETIME_FORMAT)
                            }),
                            loop
                        )
                
                # 修改：确保AI处于新对话状态，不加载历史上下文
                if self.ai_manager.ai:
                    # 重置AI对话状态，但保留系统提示词
                    self.ai_manager.ai.reset_conversation()
                    self.logger.info("AI对话状态已重置，准备执行任务")
                
                # 创建一个 Future 来等待 AI 完成
                ai_future = loop.create_future()
                
                def run_ai():
                    try:
                        # 在单独的线程中运行 AI
                        response = self.ai_manager.ai.think_and_respond(user_input, output_callback)
                        # 将结果设置到 Future 中
                        loop.call_soon_threadsafe(ai_future.set_result, response)
                    except Exception as e:
                        loop.call_soon_threadsafe(ai_future.set_exception, e)
                
                # 启动 AI 线程
                ai_thread = threading.Thread(target=run_ai)
                ai_thread.daemon = True
                ai_thread.start()
                
                # 等待 AI 完成，同时处理可能的取消
                try:
                    response = await ai_future
                    result = response or "AI无响应"
                except Exception as e:
                    self.logger.error(f"AI对话失败: {e}")
                    result = f"任务执行但AI对话失败: {str(e)}"
                finally:
                    # 确保线程结束
                    ai_thread.join(timeout=1.0)
                
            except Exception as e:
                self.logger.error(f"AI对话失败: {e}")
                import traceback
                traceback.print_exc()
                result = f"任务执行但AI对话失败: {str(e)}"
                # 广播错误信息
                if self.ws_handler and self.broadcast_enabled:
                    try:
                        await self.ws_handler.broadcast({
                            "type": "task_error",
                            "task_id": str(memo['id']),  # 确保是字符串
                            "execution_id": execution_id,
                            "task_title": memo['title'],
                            "error": str(e),
                            "timestamp": datetime.now().strftime(constants.DATETIME_FORMAT)
                        })
                    except:
                        pass
        
        # 获取任务的最新状态（可选，用于日志）
        updated_memo = memo_db.get_memo(memo['id'])
        if updated_memo:
            if not updated_memo['is_completed'] and updated_memo.get('reminder_time'):
                self.logger.info(i18n.get('next_execution', updated_memo['reminder_time']))
            elif updated_memo['is_completed']:
                self.logger.info(i18n.get('task_completed', memo['title']))
        
        return result

    async def check_and_execute_immediate_tasks(self, memo_db: MemoDatabase):
        """检查并执行即时任务"""
        if not memo_db:
            return []
        
        try:
            immediate = memo_db.get_immediate_memos(limit=self.max_tasks_per_run)
            
            if not immediate:
                return []
            
            self.logger.info(f"发现 {len(immediate)} 个即时任务需要立即执行")
            
            if self.broadcast_enabled and self.ws_handler:
                await self.ws_handler.broadcast_task_status(
                    {"id": 0, "title": "即时任务"},
                    "batch_start",
                    f"开始执行 {len(immediate)} 个即时任务"
                )
            
            executed_tasks = []
            for memo in immediate:
                try:
                    if self.ws_handler:
                        await self.ws_handler.broadcast_task_status(memo, "executing", i18n.get('immediate_memo_executing', memo['title']))
                    
                    self.logger.info(f"标记即时任务 #{memo['id']} 为已触发")
                    next_time = memo_db.mark_as_triggered(memo['id'])
                    
                    result = await self.execute_task_as_conversation(memo, memo_db)
                    
                    if self.ws_handler:
                        await self.ws_handler.broadcast_task_status(memo, "complete", result)
                    
                    executed_tasks.append({
                        "id": memo['id'],
                        "title": memo['title'],
                        "result": result,
                        "success": True,
                        "next_time": next_time
                    })
                    
                except Exception as e:
                    self.logger.error(i18n.get('task_failed', memo['title'], str(e)))
                    
                    if self.ws_handler:
                        await self.ws_handler.broadcast_task_status(memo, "failed", str(e))
                    
                    executed_tasks.append({
                        "id": memo['id'],
                        "title": memo['title'],
                        "error": str(e),
                        "success": False
                    })
            
            if self.broadcast_enabled and self.ws_handler:
                success_count = sum(1 for t in executed_tasks if t['success'])
                await self.ws_handler.broadcast_task_status(
                    {"id": 0, "title": "即时任务"},
                    "batch_complete",
                    f"即时任务执行完成: {success_count}/{len(executed_tasks)} 个成功"
                )
            
            return executed_tasks
            
        except Exception as e:
            self.logger.error(f"检查即时任务失败: {e}")
            return []
    
    async def run(self, memo_db: MemoDatabase):
        """启动调度器"""
        self.running = True
        
        while self.running:
            try:
                # 先检查并执行即时任务
                if memo_db:
                    immediate_executed = await self.check_and_execute_immediate_tasks(memo_db)
                    if immediate_executed:
                        self.logger.info(f"执行了 {len(immediate_executed)} 个即时任务")
                
                # 再检查普通到期任务
                if memo_db:
                    executed = await self.check_and_execute_tasks(memo_db)
                    if executed:
                        self.logger.info(f"执行了 {len(executed)} 个普通任务")
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"调度器运行错误: {e}")
                await asyncio.sleep(1)
    
    def stop(self):
        """停止调度器"""
        self.running = False
        self.logger.info(i18n.get('scheduler_stopped'))
    
    def get_stats(self) -> Dict:
        """获取调度器统计信息"""
        return {
            "running": self.running,
            "check_interval": self.check_interval,
            "max_tasks_per_run": self.max_tasks_per_run,
            "broadcast_enabled": self.broadcast_enabled,
            "recent_executions": self.execution_history[-10:],
            "total_executions": len(self.execution_history)
        }

# ==================== 对话历史管理器 ====================

class ConversationHistory:
    """对话历史管理器 - 管理所有历史对话"""
    
    def __init__(self, save_dir: str = None, memory_db: MemoryDatabase = None, load_history: bool = None):
        if save_dir is None:
            save_dir = constants.SAVE_DIR
        
        self.save_dir = Path(save_dir)
        self.archive_dir = self.save_dir / constants.ARCHIVE_DIR
        self.history_file = self.save_dir / constants.HISTORY_FILE
        self.memory_db = memory_db
        
        config = ConfigManager()
        if load_history is None:
            load_history = config.get("system.load_history_by_default", True)
        self.load_history = load_history
        
        # 确保目录存在
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = Logger("HistoryManager")
        self.history_index = self._load_history_index()
        self.current_conversation = None
        self.current_file = self.save_dir / constants.CURRENT_CONVERSATION_FILE
        
        self._load_current_conversation()
    
    def _load_history_index(self) -> Dict:
        """加载历史索引文件"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"conversations": [], "last_id": 0}
        return {"conversations": [], "last_id": 0}
    
    def _save_history_index(self):
        """保存历史索引"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history_index, f, ensure_ascii=False, indent=2)
    
    def _load_current_conversation(self):
        """加载当前的对话（如果有）"""
        if self.current_file.exists():
            try:
                with open(self.current_file, 'r', encoding='utf-8') as f:
                    self.current_conversation = json.load(f)
                    self.logger.info(f"已加载当前对话: {self.current_conversation.get('topic', '未命名')}")
            except Exception as e:
                self.logger.error(f"加载当前对话失败: {e}")
    
    def save_current_conversation(self):
        """保存当前对话"""
        if self.current_conversation:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_conversation, f, ensure_ascii=False, indent=2)
    
    def start_new_conversation(self, topic: str = None) -> Dict:
        """开始新对话"""
        if self.current_conversation:
            self.archive_current_conversation()
        
        conv_id = str(int(time.time()))
        self.current_conversation = {
            "id": conv_id,
            "start_time": datetime.now().strftime(constants.DATETIME_FORMAT),
            "end_time": None,
            "topic": topic or "新对话",
            "messages": [],
            "tool_calls": [],
            "stats": {
                "user_messages": 0,
                "ai_messages": 0,
                "tool_calls": 0
            }
        }
        
        self.save_current_conversation()
        self.logger.info(f"开始新对话: {topic}")
        return self.current_conversation
    
    def archive_current_conversation(self, final_summary: str = None):
        """将当前对话归档到历史"""
        if not self.current_conversation:
            return None
        
        if self.current_conversation.get("end_time") is None:
            self.current_conversation["end_time"] = datetime.now().strftime(constants.DATETIME_FORMAT)
        
        if final_summary and self.memory_db:
            messages = self.current_conversation.get("messages", [])
            content_preview = "\n".join([f"{m['speaker']}: {m['content'][:200]}" 
                                        for m in messages[-10:] if m.get('speaker')])
            
            self.memory_db.add_memory(
                topic=self.current_conversation["topic"],
                summary=final_summary,
                content=content_preview,
                start_time=self.current_conversation["start_time"],
                end_time=self.current_conversation["end_time"],
                importance=2
            )
        
        timestamp = datetime.now().strftime(constants.DATE_FORMAT)
        archive_filename = f"conversation_{timestamp}.json"
        archive_path = self.archive_dir / archive_filename
        
        with open(archive_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_conversation, f, ensure_ascii=False, indent=2)
        
        self.history_index["conversations"].append({
            "id": self.current_conversation["id"],
            "file": archive_filename,
            "start_time": self.current_conversation["start_time"],
            "end_time": self.current_conversation["end_time"],
            "topic": self.current_conversation["topic"],
            "messages": len(self.current_conversation["messages"]),
            "tool_calls": len(self.current_conversation["tool_calls"])
        })
        
        self._save_history_index()
        self.logger.info(f"对话已归档: {archive_filename}")
        
        self.current_conversation = None
        if self.current_file.exists():
            self.current_file.unlink()
        
        return str(archive_path)
    
    def load_all_history(self, max_messages: int = None) -> List[Dict]:
        """加载所有历史对话作为上下文"""
        if max_messages is None:
            max_messages = constants.MAX_HISTORY_CONTEXT
        
        if not self.load_history:
            return []
        
        all_messages = []
        
        if self.current_conversation:
            current_msgs = self.current_conversation.get("messages", [])
            for msg in current_msgs[-max_messages//2:]:
                if not msg.get("is_history"):
                    all_messages.append({
                        "timestamp": msg["timestamp"],
                        "role": msg["role"],
                        "speaker": msg.get("speaker"),
                        "content": msg["content"],
                        "from_current": True
                    })
        
        history_files = sorted(self.archive_dir.glob("*.json"), reverse=True)[:constants.MAX_HISTORY_CONVERSATIONS]
        
        for hist_file in history_files:
            try:
                with open(hist_file, 'r', encoding='utf-8') as f:
                    conv = json.load(f)
                    messages = conv.get("messages", [])
                    for msg in messages[-max_messages//len(history_files):]:
                        if not msg.get("is_history"):
                            all_messages.append({
                                "timestamp": msg["timestamp"],
                                "role": msg["role"],
                                "speaker": msg.get("speaker"),
                                "content": msg["content"],
                                "from_file": hist_file.name
                            })
            except Exception as e:
                self.logger.error(f"加载历史文件 {hist_file} 失败: {e}")
        
        all_messages.sort(key=lambda x: x["timestamp"])
        
        if len(all_messages) > max_messages:
            all_messages = all_messages[-max_messages:]
        
        self.logger.info(f"已加载 {len(all_messages)} 条历史消息")
        return all_messages
    
    def get_conversation_context(self, max_messages: int = None) -> List[Dict]:
        """获取适合作为AI上下文的对话历史"""
        if max_messages is None:
            max_messages = constants.MAX_HISTORY_CONTEXT
        
        if not self.load_history:
            return []
        
        history_messages = self.load_all_history(max_messages)
        
        context = []
        for msg in history_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                continue
            
            if role == "assistant":
                speaker = msg.get("speaker", "")
                context.append({
                    "role": "assistant",
                    "content": f"[{speaker}] {content}"
                })
            else:
                context.append({
                    "role": "user",
                    "content": content
                })
        
        return context
    
    def add_message(self, role: str, content: str, speaker: str = None):
        """添加消息到当前对话"""
        if not self.current_conversation:
            self.start_new_conversation()
        
        message = {
            "timestamp": datetime.now().strftime(constants.DATETIME_FORMAT),
            "role": role,
            "speaker": speaker,
            "content": content
        }
        
        self.current_conversation["messages"].append(message)
        
        if role == "user":
            self.current_conversation["stats"]["user_messages"] += 1
        elif role == "assistant":
            self.current_conversation["stats"]["ai_messages"] += 1
        
        self.save_current_conversation()
    
    def add_tool_call(self, tool_name: str, args: Dict, result: str):
        """记录工具调用"""
        if not self.current_conversation:
            return
        
        tool_call = {
            "timestamp": datetime.now().strftime(constants.DATETIME_FORMAT),
            "tool": tool_name,
            "args": args,
            "result_preview": result[:200] + "..." if len(result) > 200 else result
        }
        
        self.current_conversation["tool_calls"].append(tool_call)
        self.current_conversation["stats"]["tool_calls"] += 1
        self.save_current_conversation()
    
    def end_current_conversation(self, summary: str = None):
        """结束当前对话"""
        if self.current_conversation:
            self.current_conversation["end_time"] = datetime.now().strftime(constants.DATETIME_FORMAT)
            
            if summary and self.memory_db:
                messages = self.current_conversation.get("messages", [])
                content_preview = "\n".join([f"{m['speaker']}: {m['content'][:200]}" 
                                            for m in messages[-10:] if m.get('speaker')])
                
                self.memory_db.add_memory(
                    topic=self.current_conversation["topic"],
                    summary=summary,
                    content=content_preview,
                    start_time=self.current_conversation["start_time"],
                    end_time=self.current_conversation["end_time"],
                    importance=2
                )
            
            self.save_current_conversation()
            self.logger.info("当前对话已保存")
    
    def reset_conversation(self):
        """重置当前对话状态"""
        if self.current_conversation:
            self.current_conversation["end_time"] = datetime.now().strftime(constants.DATETIME_FORMAT)
            self.save_current_conversation()
        self.current_conversation = None
    
    def list_conversations(self) -> List[Dict]:
        """列出所有对话（包括当前和归档）"""
        conversations = []
        
        if self.current_conversation:
            conversations.append({
                "file": constants.CURRENT_CONVERSATION_FILE,
                "is_current": True,
                "id": self.current_conversation.get("id"),
                "start_time": self.current_conversation.get("start_time"),
                "end_time": self.current_conversation.get("end_time"),
                "topic": self.current_conversation.get("topic"),
                "messages": len(self.current_conversation.get("messages", [])),
                "tool_calls": len(self.current_conversation.get("tool_calls", []))
            })
        
        for conv in self.history_index.get("conversations", []):
            conversations.append({
                "file": conv["file"],
                "is_current": False,
                "id": conv["id"],
                "start_time": conv["start_time"],
                "end_time": conv["end_time"],
                "topic": conv["topic"],
                "messages": conv["messages"],
                "tool_calls": conv["tool_calls"]
            })
        
        conversations.sort(key=lambda x: x["start_time"] if x["start_time"] else "", reverse=True)
        return conversations
    
    def load_conversation(self, file_name: str) -> Optional[Dict]:
        """加载指定的对话"""
        if file_name == constants.CURRENT_CONVERSATION_FILE and self.current_conversation:
            return self.current_conversation
        
        file_path = self.archive_dir / file_name
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None


# ==================== 命令执行器抽象类 ====================

class CommandExecutor(ABC):
    """命令执行器抽象基类 - 负责执行系统命令"""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger("CommandExecutor")
        self.config = ConfigManager()
        self.process = None
    
    @abstractmethod
    def execute(self, command: str, timeout: int = 30, **kwargs) -> str:
        """执行命令并返回结果（非流式）"""
        pass
    
    @abstractmethod
    def execute_streaming(self, command: str, output_queue: queue.Queue, timeout: int = 30, **kwargs):
        """流式执行命令，通过队列输出结果"""
        pass
    
    def is_enabled(self) -> bool:
        """检查命令执行是否启用"""
        return constants.COMMANDS_ENABLED
    
    def format_result(self, success: bool, message: str, data: Dict = None) -> str:
        """统一结果格式化"""
        result = []
        emoji = "✅" if success else "❌"
        result.append(f"{emoji} {message}")
        
        if data:
            for key, value in data.items():
                if isinstance(value, str) and "\n" in value:
                    result.append(f"  {key}:")
                    for line in value.split("\n"):
                        result.append(f"    {line}")
                else:
                    result.append(f"  {key}: {value}")
        
        return "\n".join(result)


class SubprocessCommandExecutor(CommandExecutor):
    """基于subprocess的命令执行器"""
    
    def execute(self, command: str, timeout: int = 30, **kwargs) -> str:
        """执行命令并返回完整结果"""
        if not self.is_enabled():
            return "❌ 命令执行功能已禁用"
        
        self.logger.info(f"执行命令: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy()
            )
            
            data = {}
            
            if result.stdout:
                data["输出"] = result.stdout.strip()
            if result.stderr:
                data["错误"] = result.stderr.strip()
            
            data["返回码"] = result.returncode
            
            if not result.stdout and not result.stderr:
                return self.format_result(True, "命令执行成功，无输出", data)
            
            return self.format_result(result.returncode == 0, "命令执行完成", data)
            
        except subprocess.TimeoutExpired:
            return f"❌ 命令执行超时（{timeout}秒）"
        except Exception as e:
            return f"❌ 执行错误: {str(e)}"
    
    def execute_streaming(self, command: str, output_queue: queue.Queue, timeout: int = 30, **kwargs):
        """流式执行命令"""
        if not self.is_enabled():
            output_queue.put(("line", "❌ 命令执行功能已禁用\n"))
            output_queue.put(("complete", "❌ 命令执行功能已禁用"))
            return
        
        self.logger.info(f"流式执行命令: {command}")
        output_queue.put(("line", f"\n🔧 执行命令: {command}\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        try:
            # 使用管道来实时获取输出
            self.process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并stderr到stdout
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True,
                env=os.environ.copy()
            )
            
            start_time = time.time()
            output_lines = []
            
            # 实时读取输出
            while True:
                # 检查超时
                if timeout > 0 and time.time() - start_time > timeout:
                    self.process.terminate()
                    output_queue.put(("line", f"\n⏰ 命令执行超时（{timeout}秒）\n"))
                    break
                
                # 读取一行输出（非阻塞）
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if line:
                    line = line.rstrip('\n')
                    output_queue.put(("line", line + "\n"))
                    output_lines.append(line)
            
            # 获取剩余输出
            remaining, _ = self.process.communicate(timeout=5)
            if remaining:
                output_queue.put(("line", remaining))
                output_lines.append(remaining)
            
            return_code = self.process.returncode
            
            output_queue.put(("line", "-" * 50 + "\n"))
            output_queue.put(("line", f"✅ 命令执行完成，返回码: {return_code}\n"))
            
            # 准备完整结果
            full_output = "\n".join(output_lines)
            data = {
                "输出": full_output,
                "返回码": return_code
            }
            
            result = self.format_result(return_code == 0, "命令执行完成", data)
            output_queue.put(("complete", result))
            
        except Exception as e:
            output_queue.put(("line", f"❌ 执行错误: {str(e)}\n"))
            output_queue.put(("complete", f"❌ 执行错误: {str(e)}"))
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except:
                    self.process.kill()
    
    def terminate(self):
        """终止当前运行的命令"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            return True
        return False


# ==================== 工具基类 ====================

class Tool(ABC):
    """工具基类"""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger(self.__class__.__name__)
        self.config = ConfigManager()
        self.streaming_output = False  # 标记是否正在流式输出
        self.output_queue = None  # 添加输出队列属性
    
    @abstractmethod
    def get_name(self) -> str:
        """返回工具名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """返回工具描述"""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict:
        """返回工具参数定义（JSON Schema格式）"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具并返回结果"""
        pass
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行工具，通过队列输出结果"""
        self.output_queue = output_queue  # 保存队列引用
        self.streaming_output = True
        try:
            # 执行具体的工具逻辑，子类可以重写这个方法
            result = self.execute(**kwargs)
            # 如果结果不为空，发送到队列
            if result:
                # 对于非流式输出，直接发送完整结果
                output_queue.put(("complete", result))
        finally:
            self.streaming_output = False
            self.output_queue = None
    
    def validate_params(self, required: List[str], **kwargs) -> Optional[str]:
        """验证必需参数"""
        missing = [p for p in required if p not in kwargs or kwargs[p] is None]
        if missing:
            return f"❌ 错误：缺少必需参数: {', '.join(missing)}"
        return None
    
    def to_function_call_format(self) -> Dict:
        """转换为OpenAI函数调用格式"""
        return {
            "type": "function",
            "function": {
                "name": self.get_name(),
                "description": self.get_description(),
                "parameters": self.get_parameters()
            }
        }
    
    def format_result(self, success: bool, message: str, data: Dict = None) -> str:
        """统一结果格式化"""
        result = []
        emoji = "✅" if success else "❌"
        result.append(f"{emoji} {message}")
        
        if data:
            for key, value in data.items():
                if isinstance(value, str) and "\n" in value:
                    result.append(f"  {key}:")
                    for line in value.split("\n"):
                        result.append(f"    {line}")
                else:
                    result.append(f"  {key}: {value}")
        
        return "\n".join(result)
    
    def check_path_safety(self, filepath: str) -> Tuple[bool, str, str]:
        """检查路径安全性（简化版）"""
        try:
            abs_path = os.path.abspath(os.path.expanduser(filepath))
            
            # 检查文件大小
            if os.path.exists(abs_path) and os.path.isfile(abs_path):
                file_size = os.path.getsize(abs_path)
                max_size = constants.MAX_FILE_SIZE
                if file_size > max_size:
                    return False, abs_path, f"❌ 文件太大 ({file_size/1024/1024:.1f}MB)"
            
            return True, abs_path, ""
        except Exception as e:
            return False, filepath, f"❌ 路径检查错误: {str(e)}"
    
    def send_line(self, line: str):
        """发送一行输出到队列（如果存在）"""
        if self.output_queue:
            self.output_queue.put(("line", line))
    
    def send_complete(self, result: str):
        """发送完成结果到队列（如果存在）"""
        if self.output_queue:
            self.output_queue.put(("complete", result))


class ToolRegistry:
    """工具注册器 - 支持技能热重载"""
    
    def __init__(self, logger: Optional[Logger] = None):
        self._tools: Dict[str, Tool] = {}
        self._builtin_tools: Dict[str, Tool] = {}  # 内置工具单独存储
        self.logger = logger or Logger("ToolRegistry")
        self.current_output_queue = None  # 用于流式输出的队列
    
    def register(self, tool: Tool, is_builtin: bool = False):
        """注册工具，可以标记是否为内置工具"""
        self._tools[tool.get_name()] = tool
        if is_builtin:
            self._builtin_tools[tool.get_name()] = tool
        self.logger.info(f"工具已注册: {tool.get_name()} {'(内置)' if is_builtin else ''}")
    
    def register_many(self, tools: List[Tool], is_builtin: bool = False):
        """批量注册工具"""
        for tool in tools:
            self.register(tool, is_builtin)
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_tools_schemas(self) -> List[Dict]:
        """获取所有工具的OpenAI函数调用格式"""
        return [tool.to_function_call_format() for tool in self._tools.values()]
    
    def set_output_queue(self, queue: queue.Queue):
        """设置输出队列"""
        self.current_output_queue = queue
        # 同时设置所有工具的队列
        for tool in self._tools.values():
            tool.output_queue = queue
    
    def execute_tool(self, name: str, **kwargs) -> str:
        """执行工具"""
        tool = self.get_tool(name)
        if not tool:
            return f"❌ 错误：找不到工具 '{name}'"
        
        self.logger.debug(f"工具调用: {name}({kwargs})")
        start_time = time.time()
        
        try:
            # 检查是否有队列可用，并且工具支持流式输出
            if self.current_output_queue and hasattr(tool, 'execute_streaming'):
                # 设置工具的流式输出属性
                tool.streaming_output = True
                tool.output_queue = self.current_output_queue
                
                # 创建队列来收集流式输出
                output_queue = queue.Queue()
                
                # 执行流式输出
                thread = threading.Thread(
                    target=tool.execute_streaming,
                    args=(output_queue,),
                    kwargs=kwargs
                )
                thread.daemon = True
                thread.start()
                
                # 从队列收集输出并发送到当前队列
                final_result = None
                while thread.is_alive() or not output_queue.empty():
                    try:
                        msg_type, content = output_queue.get(timeout=0.1)
                        if msg_type == "line":
                            # 发送到当前队列（会通过WebSocket发送）
                            if self.current_output_queue:
                                self.current_output_queue.put(("line", content))
                        elif msg_type == "complete":
                            final_result = content
                            # 也发送完整结果
                            if self.current_output_queue:
                                self.current_output_queue.put(("complete", content))
                    except queue.Empty:
                        continue
                
                thread.join(timeout=5)
                if thread.is_alive():
                    return "❌ 工具执行超时"
                
                result = final_result or ""
                tool.streaming_output = False
                tool.output_queue = None
            else:
                # 普通执行
                result = tool.execute(**kwargs)
            
            elapsed = time.time() - start_time
            self.logger.debug(f"工具结果 ({elapsed:.2f}s): {result[:100]}...")
            return result
        except TypeError as e:
            return f"❌ 工具执行错误: 参数错误 - {str(e)}"
        except Exception as e:
            return f"❌ 工具执行错误: {str(e)}"
    
    def reload_skills(self, skills_dir: str = None) -> int:
        """
        重新加载所有扩展技能（热重载）
        保留内置工具，只重新加载扩展技能
        """
        if skills_dir is None:
            skills_dir = constants.SKILLS_DIR
        
        self.logger.info("开始重新加载扩展技能...")
        
        # 记录旧技能数量
        old_skills_count = len([name for name in self._tools.keys() if name not in self._builtin_tools])
        
        # 移除所有非内置工具
        tools_to_remove = [name for name in self._tools.keys() if name not in self._builtin_tools]
        for name in tools_to_remove:
            del self._tools[name]
            self.logger.debug(f"移除旧技能: {name}")
        
        # 重新加载技能
        loaded_count = 0
        if os.path.exists(skills_dir):
            # 获取所有技能文件（排除以_开头的文件）
            skills_list = [f for f in os.listdir(skills_dir) 
                          if os.path.isfile(os.path.join(skills_dir, f)) 
                          and not f.startswith("_")]
            
            for skill_file in skills_list:
                try:
                    # 为每个技能文件创建扩展工具
                    extool = ExtensionTool(skill_file, self.logger)
                    self.register(extool, is_builtin=False)
                    loaded_count += 1
                    self.logger.info(f"已加载扩展技能: {extool.get_name()}")
                except Exception as e:
                    self.logger.error(f"加载技能 {skill_file} 失败: {e}")
        
        self.logger.info(i18n.get('skills_reloaded', loaded_count))
        return loaded_count
    
    def get_skills_count(self) -> Tuple[int, int]:
        """获取内置工具和扩展技能的数量"""
        builtin_count = len(self._builtin_tools)
        skill_count = len(self._tools) - builtin_count
        return builtin_count, skill_count


# ==================== 扩展工具类 ====================

class ExtensionTool(Tool):
    """扩展工具类 - 动态加载外部技能（支持流式输出）"""
    
    def __init__(self, skill_file: str, logger: Optional[Logger] = None):
        super().__init__(logger)
        self.skill_file = skill_file
        self.skill_path = os.path.join(constants.SKILLS_DIR, skill_file)
        self._name = os.path.splitext(skill_file)[0]  # 去掉扩展名作为工具名
        self._description = self._get_description()
        self._parameters = self._get_parameters()
    
    def _run_skill_command(self, command: str) -> str:
        """运行技能命令并返回输出"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
                env=os.environ.copy()
            )
            return result.stdout.strip()
        except Exception as e:
            self.logger.error(f"运行技能命令失败: {e}")
            return f"Error: {str(e)}"
    
    def _get_description(self) -> str:
        """获取技能描述"""
        # 执行文件并传入 --description 参数
        cmd = f"{self.skill_path} --description"
        return self._run_skill_command(cmd)

    def _get_parameters(self) -> Dict:
        """获取技能参数定义（JSON Schema格式）"""
        # 执行文件并传入 --parameters 参数
        cmd = f"{self.skill_path} --parameters"
        output = self._run_skill_command(cmd)
        
        try:
            # 尝试解析JSON
            return json.loads(output)
        except json.JSONDecodeError:
            # 如果解析失败，返回一个默认的参数结构
            self.logger.warning(f"技能 {self._name} 的参数返回不是有效的JSON")
            return {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "string",
                        "description": "传递给技能的命令行参数（JSON格式）"
                    }
                },
                "required": ["args"]
            }
    
    def get_name(self) -> str:
        return self._name
    
    def get_description(self) -> str:
        return self._description
    
    def get_parameters(self) -> Dict:
        return self._parameters
    
    def execute(self, **kwargs) -> str:
        """执行技能（非流式）"""
        # 将kwargs转换为JSON字符串
        args_json = json.dumps(kwargs, ensure_ascii=False)
        
        # 执行文件并传入 --execute 和 --args 参数
        cmd = f"{self.skill_path} --execute --args '{args_json}'"
        print('执行扩展工具，参数：',cmd)
        return self._run_skill_command(cmd)
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行技能 - 实时输出到WebSocket"""
        args_json = json.dumps(kwargs, ensure_ascii=False)
        cmd = f"{self.skill_path} --execute --args '{args_json}'"
        
        # 发送开始执行的消息
        output_queue.put(("line", f"\n🔧 执行扩展技能: {self._name}\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        try:
            # 使用subprocess.Popen实现流式输出
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并stderr到stdout
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True,
                env=os.environ.copy()
            )
            
            output_lines = []
            
            # 实时读取输出
            while True:
                # 读取一行输出
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.rstrip('\n')
                    # 发送每一行到队列（会通过WebSocket发送）
                    output_queue.put(("line", line + "\n"))
                    output_lines.append(line)
            
            # 等待进程结束
            return_code = process.wait()
            
            # 发送执行完成信息
            output_queue.put(("line", "-" * 50 + "\n"))
            output_queue.put(("line", f"✅ 技能执行完成，返回码: {return_code}\n"))
            
            # 准备完整结果
            full_output = "\n".join(output_lines)
            result = self.format_result(return_code == 0, "技能执行完成", {"输出": full_output})
            
            # 发送完整结果
            output_queue.put(("complete", result))
            
        except Exception as e:
            error_msg = f"❌ 技能执行错误: {str(e)}"
            output_queue.put(("line", error_msg + "\n"))
            output_queue.put(("complete", error_msg))


# ==================== 技能热重载工具 ====================

class ReloadSkillsTool(Tool):
    """技能热重载工具 - 重新加载所有扩展技能"""
    
    def __init__(self, tool_registry: ToolRegistry, logger: Optional[Logger] = None):
        super().__init__(logger)
        self.tool_registry = tool_registry
    
    def get_name(self) -> str:
        return "reload_skills"
    
    def get_description(self) -> str:
        return """技能热重载工具 - 重新加载所有扩展技能
当你添加、修改或删除了 ~/.aibox/skills/ 目录下的技能文件后，
调用此工具可以立即生效，无需重启系统。"""
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "confirm": {
                    "type": "boolean",
                    "description": "确认重新加载技能",
                    "default": True
                }
            }
        }
    
    def execute(self, confirm: bool = True, **kwargs) -> str:
        """执行技能热重载"""
        if not confirm:
            return "❌ 技能重载已取消，如需重载请设置 confirm=true"
        
        self.logger.info("开始执行技能热重载...")
        
        try:
            count = self.tool_registry.reload_skills()
            
            # 获取更新后的技能列表
            skills_dir = constants.SKILLS_DIR
            skills_list = []
            if os.path.exists(skills_dir):
                skills_list = [f for f in os.listdir(skills_dir) 
                              if os.path.isfile(os.path.join(skills_dir, f)) 
                              and not f.startswith("_")]
            
            data = {
                "重新加载的技能数量": count,
                "技能文件列表": skills_list[:10],  # 只显示前10个
                "技能目录": skills_dir
            }
            
            if len(skills_list) > 10:
                data["提示"] = f"还有 {len(skills_list)-10} 个技能未显示"
            
            return self.format_result(True, i18n.get('skills_reloaded', count), data)
            
        except Exception as e:
            self.logger.error(f"技能热重载失败: {e}")
            return i18n.get('skills_reload_failed', str(e))
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行技能热重载"""
        output_queue.put(("line", "\n🔄 执行技能热重载...\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        result = self.execute(**kwargs)
        
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))


# ==================== 更新身份工具 ====================

class UpdateIdentityTool(Tool):
    """更新用户身份工具 - 修改 00_IDENTITY.md 文件"""
    
    def __init__(self, prompt_manager: PromptManager, logger: Optional[Logger] = None):
        super().__init__(logger)
        self.prompt_manager = prompt_manager
    
    def get_name(self) -> str:
        return "update_identity"
    
    def get_description(self) -> str:
        return """更新用户身份信息 - 修改 00_IDENTITY.md 文件
当你了解到用户的身份信息时，调用此工具更新身份文件。
如果文件不存在，会自动创建。"""
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "用户身份信息内容（Markdown格式），包含用户的身份、特点、偏好等信息"
                },
                "confirm": {
                    "type": "boolean",
                    "description": "确认更新身份信息",
                    "default": True
                }
            },
            "required": ["content"]
        }
    
    def execute(self, content: str = None, confirm: bool = True, **kwargs) -> str:
        if not content:
            return "❌ 需要提供身份信息内容"
        
        if not confirm:
            return "❌ 身份更新已取消，如需更新请设置 confirm=true"
        
        self.logger.info("开始更新用户身份信息...")
        
        if self.prompt_manager.update_identity(content):
            return self.format_result(True, i18n.get('identity_updated', self.prompt_manager.IDENTITY_FILE), {
                "文件": self.prompt_manager.IDENTITY_FILE,
                "路径": self.prompt_manager.get_prompts_dir_path()
            })
        else:
            return self.format_result(False, "身份更新失败", {
                "文件": self.prompt_manager.IDENTITY_FILE,
                "路径": self.prompt_manager.get_prompts_dir_path()
            })
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行更新身份"""
        output_queue.put(("line", "\n👤 更新用户身份信息...\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        result = self.execute(**kwargs)
        
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))

# ==================== 更新智能体自我认识工具 ====================

class UpdateSoulTool(Tool):
    """更新智能体自我认识工具 - 修改 99_SOUL.md 文件"""
    
    def __init__(self, prompt_manager: PromptManager, logger: Optional[Logger] = None):
        super().__init__(logger)
        self.prompt_manager = prompt_manager
    
    def get_name(self) -> str:
        return "update_soul"
    
    def get_description(self) -> str:
        return """更新智能体的自我认识定义 - 修改 99_SOUL.md 文件
当你需要重新定义自己的身份、角色、性格、能力边界时，调用此工具更新自我认识文件。
如果文件不存在，会自动创建默认定义。"""
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "智能体自我认识定义内容（Markdown格式），包含：身份定义、角色描述、性格特点、能力边界、行为准则等"
                },
                "confirm": {
                    "type": "boolean",
                    "description": "确认更新自我认识定义",
                    "default": True
                }
            },
            "required": ["content"]
        }
    
    def execute(self, content: str = None, confirm: bool = True, **kwargs) -> str:
        if not content:
            return "❌ 需要提供智能体自我认识定义内容"
        
        if not confirm:
            return "❌ 自我认识更新已取消，如需更新请设置 confirm=true"
        
        self.logger.info("开始更新智能体自我认识定义...")
        
        if self.prompt_manager.update_soul(content):
            return self.format_result(True, "智能体自我认识已更新", {
                "文件": self.prompt_manager.SOUL_FILE,
                "路径": self.prompt_manager.get_prompts_dir_path()
            })
        else:
            return self.format_result(False, "自我认识更新失败", {
                "文件": self.prompt_manager.SOUL_FILE,
                "路径": self.prompt_manager.get_prompts_dir_path()
            })
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行更新自我认识"""
        output_queue.put(("line", "\n🧠 更新智能体自我认识...\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        result = self.execute(**kwargs)
        
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))

# ==================== 保存记忆并结束对话工具（增强版，修复版） ====================

class SaveMemoryAndEndConversationTool(Tool):
    """保存记忆并结束对话工具 - 增强版，同时更新智能体状态"""
    
    def __init__(self, exit_callback: Callable, memory_db: MemoryDatabase, prompt_manager: PromptManager, logger: Optional[Logger] = None):
        super().__init__(logger)
        self.exit_callback = exit_callback
        self.memory_db = memory_db
        self.prompt_manager = prompt_manager
    
    def get_name(self) -> str:
        return "save_memory_and_end_conversation"
    
    def get_description(self) -> str:
        return """保存记忆并结束当前对话 - 必须提供详细的对话总结和当前状态！
使用此工具时，AI会：
1. 将本次对话的重要内容保存到记忆库
2. 提供完整的对话总结
3. 描述自己现在的状态、事情的走向等，保存到 100_STATUS.md
4. 礼貌地结束对话"""
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "详细的对话总结（至少50字），包含：讨论的主题、关键问题、重要结论、达成的共识等"
                },
                "topic": {
                    "type": "string",
                    "description": "对话主题（用于记忆分类，默认自动提取）"
                },
                "reason": {
                    "type": "string",
                    "description": "结束对话的原因",
                    "default": "话题讨论完成"
                },
                "current_status": {
                    "type": "string",
                    "description": "当前的智能体状态描述，包含：当前进展、下一步计划、待处理事项、整体走向等"
                },
                "next_goals": {
                    "type": "string",
                    "description": "接下来的目标或计划（可选）"
                }
            },
            "required": ["summary", "current_status"]
        }
    
    def execute(self, summary: str = None, topic: str = None, reason: str = "话题讨论完成", 
                current_status: str = None, next_goals: str = None, **kwargs) -> str:
        if summary is None or len(summary) < 50:
            return "❌ 请提供更详细的对话总结（至少50字），以便保存到记忆库"
        
        if current_status is None:
            return "❌ 请提供当前状态描述，以便更新 100_STATUS.md"
        
        self.logger.info(f"AI保存记忆并结束对话: {reason}")
        
        # 保存到记忆库
        memory_result = ""
        if self.memory_db and topic:
            memory_id = self.memory_db.add_memory(
                topic=topic,
                summary=summary,
                importance=3  # 提高重要性，因为是对话总结
            )
            self.logger.info(f"对话记忆已保存，ID: {memory_id}")
            memory_result = f"记忆已保存，ID: {memory_id}"
        
        # 构建状态内容
        status_content = f"【当前状态】\n{current_status}\n\n"
        if next_goals:
            status_content += f"【下一步计划】\n{next_goals}\n\n"
        status_content += f"【对话总结】\n{summary}"
        
        # 更新状态文件
        status_updated = self.prompt_manager.update_status(status_content)
        
        if self.exit_callback:
            self.exit_callback(reason, summary)
        
        data = {
            "原因": reason,
            "总结预览": summary[:100] + "..." if len(summary) > 100 else summary,
            "状态更新": "✅ 已更新" if status_updated else "❌ 更新失败",
            "记忆已保存": True
        }
        
        if memory_result:
            data["记忆"] = memory_result
        
        return self.format_result(True, "对话记忆已保存，状态已更新，对话结束", data)
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行结束对话"""
        output_queue.put(("line", "\n💾 保存记忆并结束对话\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        result = self.execute(**kwargs)
        
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))


# ==================== 备忘录工具（简化版，去掉任务类型） ====================

class MemoTool(Tool):
    """备忘录工具 - 用于管理任务（所有任务都是对话任务）"""
    
    def __init__(self, memo_db: MemoDatabase, logger: Optional[Logger] = None):
        super().__init__(logger)
        self.memo_db = memo_db
    
    def get_name(self) -> str:
        return "memo"
    
    def get_description(self) -> str:
        return """任务管理工具 - 创建、查看、完成任务
支持：创建任务（支持一次性/重复、即时任务）、查看待办、标记完成、删除任务、搜索任务"""
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["add", "list", "get", "complete", "delete", "search", "stats"]
                },
                "title": {
                    "type": "string",
                    "description": "任务标题（用于add操作）"
                },
                "content": {
                    "type": "string",
                    "description": "任务内容（可选，用于add操作）"
                },
                "reminder_time": {
                    "type": "string",
                    "description": "执行时间（格式：YYYY-MM-DD HH:MM:SS，或相对时间如 '+1h', '+30m', 'tomorrow 9am'）"
                },
                "reminder_minutes": {
                    "type": "integer",
                    "description": "延迟分钟数（从现在开始，用于快速设置任务）"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "标签列表"
                },
                "priority": {
                    "type": "integer",
                    "description": "优先级 1-5（默认1）",
                    "default": 1
                },
                "repeat_type": {
                    "type": "string",
                    "description": "重复类型（none=一次性, daily=每天, weekly=每周, monthly=每月, custom=自定义）",
                    "enum": ["none", "daily", "weekly", "monthly", "custom"],
                    "default": "none"
                },
                "repeat_interval": {
                    "type": "integer",
                    "description": "自定义重复间隔，当repeat_type='custom'时使用",
                    "default": 0
                },
                "repeat_interval_unit": {
                    "type": "string",
                    "description": "重复间隔单位（minutes=分钟, hours=小时, days=天），当repeat_type='custom'时使用",
                    "enum": ["minutes", "hours", "days"],
                    "default": "days"
                },
                "repeat_end_time": {
                    "type": "string",
                    "description": "重复结束时间，None表示永久重复"
                },
                "is_immediate": {
                    "type": "boolean",
                    "description": "是否为即时任务（立即执行）",
                    "default": False
                },
                "memo_id": {
                    "type": "integer",
                    "description": "任务ID（用于get、complete、delete操作）"
                },
                "memo_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "任务ID列表（用于批量删除）"
                },
                "force_complete": {
                    "type": "boolean",
                    "description": "强制完成（忽略重复规则）",
                    "default": False
                },
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词（用于search操作）"
                },
                "include_completed": {
                    "type": "boolean",
                    "description": "是否包含已完成的任务（默认False）",
                    "default": False
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制（默认20）",
                    "default": 20
                },
                "confirm": {
                    "type": "boolean",
                    "description": "确认删除操作",
                    "default": False
                }
            },
            "required": ["action"]
        }
    
    def _parse_reminder_time(self, reminder_input: Any) -> Optional[str]:
        """解析提醒时间输入"""
        if not reminder_input:
            return None
        
        if isinstance(reminder_input, int):
            reminder_time = datetime.now() + timedelta(minutes=reminder_input)
            return reminder_time.strftime(constants.DATETIME_FORMAT)
        
        if isinstance(reminder_input, str):
            reminder_input = reminder_input.strip()
            
            if reminder_input.startswith('+'):
                match = re.match(r'\+(\d+)([mhd])', reminder_input)
                if match:
                    value, unit = int(match.group(1)), match.group(2)
                    if unit == 'm':
                        delta = timedelta(minutes=value)
                    elif unit == 'h':
                        delta = timedelta(hours=value)
                    elif unit == 'd':
                        delta = timedelta(days=value)
                    else:
                        return None
                    
                    reminder_time = datetime.now() + delta
                    return reminder_time.strftime(constants.DATETIME_FORMAT)
            
            try:
                reminder_time = datetime.strptime(reminder_input, constants.DATETIME_FORMAT)
                return reminder_time.strftime(constants.DATETIME_FORMAT)
            except ValueError:
                pass
            
            now = datetime.now()
            reminder_input_lower = reminder_input.lower()
            
            if 'tomorrow' in reminder_input_lower:
                tomorrow = now + timedelta(days=1)
                time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', reminder_input_lower)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
                    ampm = time_match.group(3)
                    
                    if ampm:
                        if ampm == 'pm' and hour < 12:
                            hour += 12
                        elif ampm == 'am' and hour == 12:
                            hour = 0
                    
                    reminder_time = tomorrow.replace(hour=hour, minute=minute, second=0)
                else:
                    reminder_time = tomorrow.replace(hour=9, minute=0, second=0)
                
                return reminder_time.strftime(constants.DATETIME_FORMAT)
        
        return None
    
    def execute(self, action: str, **kwargs) -> str:
        """执行备忘录操作"""
        try:
            if action == "add":
                return self._add_memo(kwargs)
            elif action == "list":
                return self._list_memos(kwargs)
            elif action == "get":
                return self._get_memo(kwargs)
            elif action == "complete":
                return self._complete_memo(kwargs)
            elif action == "delete":
                return self._delete_memo(kwargs)
            elif action == "search":
                return self._search_memos(kwargs)
            elif action == "stats":
                return self._get_stats(kwargs)
            else:
                return f"❌ 未知操作: {action}"
        except Exception as e:
            return f"❌ 任务操作错误: {str(e)}"
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行备忘录操作"""
        action = kwargs.get("action")
        
        # 发送开始执行的消息
        output_queue.put(("line", f"\n📝 执行备忘录操作: {action}\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        # 执行操作
        result = self.execute(**kwargs)
        
        # 发送结果
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))
    
    def _add_memo(self, kwargs: Dict) -> str:
        """添加任务 - 所有任务都是对话任务，不需要task_type"""
        title = kwargs.get("title")
        if not title:
            return "❌ 需要提供任务标题"
        
        content = kwargs.get("content")
        reminder_minutes = kwargs.get("reminder_minutes")
        reminder_time_input = kwargs.get("reminder_time")
        tags = kwargs.get("tags", [])
        priority = kwargs.get("priority", 1)
        repeat_type = kwargs.get("repeat_type", "none")
        repeat_interval = kwargs.get("repeat_interval", 0)
        repeat_interval_unit = kwargs.get("repeat_interval_unit", "days")
        repeat_end_time = kwargs.get("repeat_end_time")
        is_immediate = kwargs.get("is_immediate", False)
        
        if repeat_type not in ["none", "daily", "weekly", "monthly", "custom"]:
            return f"❌ 无效的重复类型: {repeat_type}"
        
        if repeat_type == "custom" and repeat_interval <= 0:
            return "❌ 自定义重复需要设置有效的 repeat_interval (>0)"
        
        reminder_time = None
        if is_immediate:
            # 即时任务：设置为当前时间，确保立即执行
            reminder_time = datetime.now().strftime(constants.DATETIME_FORMAT)
        elif reminder_minutes:
            reminder_time = self._parse_reminder_time(reminder_minutes)
        elif reminder_time_input:
            reminder_time = self._parse_reminder_time(reminder_time_input)
        else:
            # 默认30分钟后
            reminder_time = self._parse_reminder_time(30)
        
        memo_id = self.memo_db.add_memo(
            title=title,
            content=content,
            reminder_time=reminder_time,
            tags=tags,
            priority=priority,
            created_by="AI",
            source="user",
            repeat_type=repeat_type,
            repeat_interval=repeat_interval,
            repeat_interval_unit=repeat_interval_unit,
            repeat_end_time=repeat_end_time,
            is_immediate=is_immediate
        )
        
        data = {
            "任务ID": memo_id,
            "标题": title,
        }
        
        if is_immediate:
            data["任务类型"] = "即时任务"
        else:
            if reminder_time:
                data["执行时间"] = reminder_time
        
        if repeat_type != "none":
            if repeat_type == "custom":
                repeat_info = f"重复类型: 每{repeat_interval} {repeat_interval_unit}"
            else:
                repeat_map = {
                    'daily': '每天',
                    'weekly': '每周',
                    'monthly': '每月'
                }
                repeat_info = f"重复类型: {repeat_map.get(repeat_type, repeat_type)}"
            
            if repeat_end_time:
                repeat_info += f", 结束于: {repeat_end_time}"
            else:
                repeat_info += ", 永久重复"
            data["重复信息"] = repeat_info
        
        return self.format_result(True, "任务已创建", data)
    
    def _list_memos(self, kwargs: Dict) -> str:
        """列出任务"""
        include_completed = kwargs.get("include_completed", False)
        limit = kwargs.get("limit", 20)
        
        memos = self.memo_db.get_all_memos(include_completed, limit)
        
        if not memos:
            return "📭 没有找到任务"
        
        status = "所有" if include_completed else "待执行"
        output = [f"📋 {status}任务 (共 {len(memos)} 个):"]
        
        now = datetime.now()
        
        for i, memo in enumerate(memos, 1):
            status_icon = "✅" if memo['is_completed'] else "⏰"
            priority_icon = "🔴" * memo['priority']
            source_tag = f"[{memo.get('source', '未知')}]" if memo.get('source') else ""
            
            immediate_tag = "⚡" if memo.get('is_immediate') else ""
            
            repeat_tag = ""
            if memo['repeat_type'] != 'none':
                if memo['repeat_type'] == 'custom':
                    unit = memo.get('repeat_interval_unit', 'days')
                    unit_map = {'minutes': '分钟', 'hours': '小时', 'days': '天'}
                    repeat_tag = f" [每{memo['repeat_interval']}{unit_map.get(unit, unit)}]"
                else:
                    repeat_map = {
                        'daily': ' [每天]',
                        'weekly': ' [每周]',
                        'monthly': ' [每月]'
                    }
                    repeat_tag = repeat_map.get(memo['repeat_type'], ' [重复]')
            
            output.append(f"\n{i}. {status_icon}{immediate_tag} [ID: {memo['id']}] {source_tag}{repeat_tag} {memo['title']} {priority_icon}")
            
            if memo['reminder_time']:
                try:
                    reminder = datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT)
                    if not memo['is_completed'] and reminder < now:
                        output.append(f"   ⚠️ 已过期: {memo['reminder_time']}")
                    else:
                        output.append(f"   ⏱️ 执行: {memo['reminder_time']}")
                except:
                    output.append(f"   ⏱️ 执行: {memo['reminder_time']}")
            
            if memo.get('trigger_count', 0) > 0:
                output.append(f"   🔄 已执行 {memo['trigger_count']} 次")
            
            if memo['content']:
                preview = memo['content'][:100] + "..." if len(memo['content']) > 100 else memo['content']
                output.append(f"   📝 {preview}")
            
            if memo['tags']:
                output.append(f"   🏷️ {', '.join(memo['tags'])}")
        
        return "\n".join(output)
    
    def _get_memo(self, kwargs: Dict) -> str:
        """获取单个任务"""
        memo_id = kwargs.get("memo_id")
        if not memo_id:
            return "❌ 需要提供任务ID"
        
        memo = self.memo_db.get_memo(memo_id)
        if not memo:
            return f"❌ 未找到ID为 {memo_id} 的任务"
        
        status = "✅ 已完成" if memo['is_completed'] else "⏰ 待执行"
        if memo['is_completed']:
            status += f" (完成于: {memo['completed_at']})"
        
        immediate_tag = "⚡ 即时任务" if memo.get('is_immediate') else ""
        
        output = [
            f"📌 任务 #{memo_id} {immediate_tag}",
            f"📋 状态: {status}",
            f"📝 标题: {memo['title']}",
        ]
        
        if memo.get('source'):
            output.append(f"📎 来源: {memo['source']}")
        
        if memo['repeat_type'] != 'none':
            if memo['repeat_type'] == 'custom':
                unit_map = {'minutes': '分钟', 'hours': '小时', 'days': '天'}
                unit = memo.get('repeat_interval_unit', 'days')
                repeat_info = f"🔄 重复: 每{memo['repeat_interval']} {unit_map.get(unit, unit)}"
            else:
                repeat_map = {
                    'daily': '每天',
                    'weekly': '每周',
                    'monthly': '每月'
                }
                repeat_info = f"🔄 重复: {repeat_map.get(memo['repeat_type'], memo['repeat_type'])}"
            
            if memo['repeat_end_time']:
                repeat_info += f", 结束于: {memo['repeat_end_time']}"
            else:
                repeat_info += ", 永久重复"
            output.append(repeat_info)
            
            if memo.get('trigger_count', 0) > 0:
                output.append(f"   📊 已执行 {memo['trigger_count']} 次")
            if memo.get('last_triggered_at'):
                output.append(f"   ⏱️ 上次执行: {memo['last_triggered_at']}")
        
        if memo['content']:
            output.append(f"📄 内容:\n{memo['content']}")
        
        if memo['reminder_time']:
            try:
                now = datetime.now()
                reminder = datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT)
                if not memo['is_completed'] and reminder < now:
                    output.append(f"⚠️ 执行时间 (已过期): {memo['reminder_time']}")
                else:
                    output.append(f"⏰ 执行时间: {memo['reminder_time']}")
            except:
                output.append(f"⏰ 执行时间: {memo['reminder_time']}")
        
        if memo['tags']:
            output.append(f"🏷️ 标签: {', '.join(memo['tags'])}")
        
        output.append(f"🔢 优先级: {'🔴' * memo['priority']} ({memo['priority']}/5)")
        output.append(f"📅 创建时间: {memo['created_at']}")
        output.append(f"👤 创建者: {memo['created_by'] or '系统'}")
        
        return "\n".join(output)
    
    def _complete_memo(self, kwargs: Dict) -> str:
        """完成任务"""
        memo_id = kwargs.get("memo_id")
        if not memo_id:
            return "❌ 需要提供任务ID"
        
        force_complete = kwargs.get("force_complete", False)
        
        memo = self.memo_db.get_memo(memo_id)
        if not memo:
            return f"❌ 未找到ID为 {memo_id} 的任务"
        
        if memo['is_completed'] and not force_complete:
            return f"ℹ️ 任务 #{memo_id} 已经完成了"
        
        if self.memo_db.complete_memo(memo_id, force_complete):
            memo = self.memo_db.get_memo(memo_id)
            data = {
                "任务ID": memo_id,
                "标题": memo['title']
            }
            
            if memo['repeat_type'] != 'none' and not memo['is_completed']:
                data["下一次执行"] = memo['reminder_time']
                data["已执行次数"] = memo.get('trigger_count', 0)
                return self.format_result(True, "任务已处理，已更新下一次执行时间", data)
            else:
                return self.format_result(True, "任务已完成", data)
        else:
            return f"❌ 无法完成任务 #{memo_id}"
    
    def _delete_memo(self, kwargs: Dict) -> str:
        """删除任务"""
        confirm = kwargs.get("confirm", False)
        if not confirm:
            return "❌ 需要设置 confirm=True 来确认删除操作"
        
        memo_id = kwargs.get("memo_id")
        if memo_id:
            if self.memo_db.complete_memo(memo_id, force_complete=True):
                return self.format_result(True, f"任务 #{memo_id} 已删除")
            else:
                return f"❌ 无法删除任务 #{memo_id}"
        else:
            return "❌ 需要提供 memo_id"
    
    def _search_memos(self, kwargs: Dict) -> str:
        """搜索任务"""
        keyword = kwargs.get("keyword")
        if not keyword:
            return "❌ 需要提供搜索关键词"
        
        include_completed = kwargs.get("include_completed", False)
        limit = kwargs.get("limit", 20)
        
        all_memos = self.memo_db.get_all_memos(include_completed, limit=100)
        
        results = []
        keyword_lower = keyword.lower()
        for memo in all_memos:
            if (keyword_lower in memo['title'].lower() or 
                (memo['content'] and keyword_lower in memo['content'].lower())):
                results.append(memo)
        
        if not results:
            return f"❌ 未找到包含 '{keyword}' 的任务"
        
        output = [f"🔍 搜索 '{keyword}' 找到 {len(results)} 个任务:"]
        now = datetime.now()
        
        for i, memo in enumerate(results[:limit], 1):
            status_icon = "✅" if memo['is_completed'] else "⏰"
            immediate_tag = "⚡" if memo.get('is_immediate') else ""
            output.append(f"\n{i}. {status_icon}{immediate_tag} [ID: {memo['id']}] {memo['title']}")
            if memo['reminder_time']:
                try:
                    reminder = datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT)
                    if not memo['is_completed'] and reminder < now:
                        output.append(f"   ⚠️ 已过期: {memo['reminder_time']}")
                    else:
                        output.append(f"   ⏱️ {memo['reminder_time']}")
                except:
                    output.append(f"   ⏱️ {memo['reminder_time']}")
        
        return "\n".join(output)
    
    def _get_stats(self, kwargs: Dict) -> str:
        """获取任务统计信息"""
        stats = self.memo_db.get_memo_stats()
        
        output = [
            "📊 任务统计",
            f"  总任务: {stats['total']} 个",
            f"  待执行: {stats['pending']} 个",
            f"  已过期: {stats['overdue']} 个",
            f"  已完成: {stats['completed']} 个",
            f"  即时任务: {stats['immediate']} 个"
        ]
        
        if stats['overdue'] > 0:
            output.append(f"\n⚠️ 有 {stats['overdue']} 个任务已过期，将自动执行")
        
        return "\n".join(output)


# ==================== 记忆工具（修改版，支持流式输出） ====================

class MemoryTool(Tool):
    """记忆工具 - 用于存储、检索和删除对话记忆（支持流式输出）"""
    
    def __init__(self, memory_db: MemoryDatabase, logger: Optional[Logger] = None):
        super().__init__(logger)
        self.memory_db = memory_db
    
    def get_name(self) -> str:
        return "memory"
    
    def get_description(self) -> str:
        return """记忆管理工具 - 存储、检索和删除重要的对话信息
支持：保存总结、多关键词搜索记忆、查看最近的记忆、删除无用记忆"""
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["save", "search", "recent", "get", "delete"]
                },
                "summary": {"type": "string", "description": "要保存的总结内容（用于save操作）"},
                "topic": {"type": "string", "description": "对话主题（用于save操作）"},
                "content": {"type": "string", "description": "详细内容（可选，用于save操作）"},
                "keywords": {
                    "type": "array", "items": {"type": "string"},
                    "description": "搜索关键词列表"
                },
                "query": {"type": "string", "description": "搜索关键词（单个关键词）"},
                "match_all": {"type": "boolean", "default": False},
                "memory_id": {"type": "integer"},
                "memory_ids": {"type": "array", "items": {"type": "integer"}},
                "importance": {"type": "integer", "default": 2},
                "limit": {"type": "integer", "default": 5},
                "confirm": {"type": "boolean", "default": False}
            },
            "required": ["action"]
        }
    
    def execute(self, action: str, **kwargs) -> str:
        try:
            if action == "save":
                return self._save_memory(kwargs)
            elif action == "search":
                return self._search_memories(kwargs)
            elif action == "recent":
                return self._get_recent_memories(kwargs)
            elif action == "get":
                return self._get_memory_by_id(kwargs)
            elif action == "delete":
                return self._delete_memory(kwargs)
            else:
                return f"❌ 未知操作: {action}"
        except Exception as e:
            return f"❌ 记忆操作错误: {str(e)}"
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行记忆操作"""
        action = kwargs.get("action")
        
        # 发送开始执行的消息
        output_queue.put(("line", f"\n🧠 执行记忆操作: {action}\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        # 执行操作
        result = self.execute(**kwargs)
        
        # 发送结果
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))
    
    def _save_memory(self, kwargs: Dict) -> str:
        summary = kwargs.get("summary")
        if not summary:
            return "❌ 需要提供总结内容"
        
        topic = kwargs.get("topic", "未命名对话")
        content = kwargs.get("content")
        importance = kwargs.get("importance", constants.MEMORY_DEFAULT_IMPORTANCE)
        
        memory_id = self.memory_db.add_memory(
            topic=topic,
            summary=summary,
            content=content,
            importance=importance
        )
        
        return self.format_result(True, "记忆已保存", {
            "记忆ID": memory_id,
            "主题": topic,
            "总结": summary[:100] + "..." if len(summary) > 100 else summary
        })
    
    def _search_memories(self, kwargs: Dict) -> str:
        keywords = kwargs.get("keywords", [])
        query = kwargs.get("query", "")
        match_all = kwargs.get("match_all", False)
        limit = kwargs.get("limit", 5)
        
        if keywords and isinstance(keywords, list):
            pass
        elif query:
            keywords = query.split()
        else:
            return "❌ 需要提供搜索关键词"
        
        if not keywords:
            return "❌ 关键词列表为空"
        
        results = self.memory_db.search_memories(keywords, match_all, limit)
        
        if not results:
            match_mode = "所有" if match_all else "任一"
            return f"❌ 未找到包含 {match_mode} 关键词 {keywords} 的记忆"
        
        match_mode = "所有关键词" if match_all else "任一关键词"
        output = [f"🔍 搜索 {match_mode} {keywords} 找到 {len(results)} 条记忆:"]
        for i, mem in enumerate(results, 1):
            output.append(f"\n{i}. [ID: {mem['id']}] [{mem['end_time']}] {mem['topic']}")
            output.append(f"   总结: {mem['summary'][:200]}")
            if mem.get('tags'):
                output.append(f"   标签: {', '.join(mem['tags'])}")
        
        return "\n".join(output)
    
    def _get_recent_memories(self, kwargs: Dict) -> str:
        limit = kwargs.get("limit", 10)
        results = self.memory_db.get_recent_memories(limit)
        
        if not results:
            return "📭 没有找到记忆"
        
        output = [f"📚 最近 {len(results)} 条记忆:"]
        for i, mem in enumerate(results, 1):
            output.append(f"\n{i}. [ID: {mem['id']}] [{mem['end_time']}] {mem['topic']}")
            output.append(f"   总结: {mem['summary'][:100]}")
        
        return "\n".join(output)
    
    def _get_memory_by_id(self, kwargs: Dict) -> str:
        memory_id = kwargs.get("memory_id")
        if not memory_id:
            return "❌ 需要提供记忆ID"
        
        memory = self.memory_db.get_memory_by_id(memory_id)
        if not memory:
            return f"❌ 未找到ID为 {memory_id} 的记忆"
        
        output = [
            f"📌 记忆 #{memory_id}",
            f"主题: {memory['topic']}",
            f"时间: {memory['start_time']} - {memory['end_time']}",
            f"总结: {memory['summary']}",
        ]
        
        if memory.get('content'):
            output.append(f"详细内容:\n{memory['content']}")
        
        if memory.get('tags'):
            output.append(f"标签: {', '.join(memory['tags'])}")
        
        return "\n".join(output)
    
    def _delete_memory(self, kwargs: Dict) -> str:
        confirm = kwargs.get("confirm", False)
        if not confirm:
            return "❌ 需要设置 confirm=True 来确认删除操作"
        
        memory_id = kwargs.get("memory_id")
        memory_ids = kwargs.get("memory_ids", [])
        
        deleted_count = 0
        
        if memory_id:
            if self.memory_db.delete_memory(memory_id):
                deleted_count = 1
        elif memory_ids:
            deleted_count = self.memory_db.delete_memories_by_ids(memory_ids)
        else:
            return "❌ 需要提供 memory_id 或 memory_ids"
        
        if deleted_count == 0:
            return f"❌ 未找到要删除的记忆"
        
        return self.format_result(True, f"成功删除 {deleted_count} 条记忆", {"删除数量": deleted_count})


# ==================== 网页工具（修改版，支持流式输出） ====================

class WebPage:
    """网页对象"""
    
    def __init__(self, url: str, response: requests.Response = None):
        self.url = url
        self.status_code = None
        self.headers = {}
        self.html = ""
        self.soup = None
        self.error = None
        self.fetch_time = None
        
        if response:
            self.status_code = response.status_code
            self.headers = dict(response.headers)
            self.html = response.text
            self.fetch_time = datetime.now()
            try:
                self.soup = BeautifulSoup(self.html, 'html.parser')
            except:
                pass
    
    @property
    def title(self) -> Optional[str]:
        if self.soup and self.soup.find('title'):
            return self.soup.find('title').get_text(strip=True)
        return None
    
    @property
    def text(self) -> str:
        if self.soup:
            return self.soup.get_text(separator='\n', strip=True)
        return ""
    
    @property
    def links(self) -> List[str]:
        links = []
        if self.soup:
            for a in self.soup.find_all('a', href=True):
                href = a['href'].strip()
                if href and not href.startswith('#') and not href.startswith('javascript:'):
                    links.append(urljoin(self.url, href))
        return list(set(links))


class SimpleWebClient:
    """简单网页访问客户端"""
    
    def __init__(self, timeout: int = None, delay: float = None, user_agent: str = None):
        self.timeout = timeout or constants.WEB_TIMEOUT
        self.delay = delay if delay is not None else constants.WEB_DELAY
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent or constants.WEB_USER_AGENT
        })
        
        self.last_request_time = 0
    
    def _wait_if_needed(self):
        if self.delay > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
    
    def get(self, url: str, **kwargs) -> WebPage:
        self._wait_if_needed()
        
        try:
            response = self.session.get(
                url, 
                timeout=kwargs.get('timeout', self.timeout),
                **kwargs
            )
            response.raise_for_status()
            
            page = WebPage(url, response)
            self.last_request_time = time.time()
            return page
            
        except Exception as e:
            page = WebPage(url)
            page.error = str(e)
            return page


class SimpleWebCrawlerTool(Tool):
    """简化版网页爬虫工具（支持流式输出）"""
    
    def __init__(self, logger=None):
        super().__init__(logger)
        self.client = SimpleWebClient()
    
    def get_name(self) -> str:
        return "web"
    
    def get_description(self) -> str:
        return """简单易用的网页访问工具 - 一句话搞定！
支持：获取网页、提取内容、搜索关键词、下载文件"""
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get", "text", "title", "links", "search"]
                },
                "url": {"type": "string"},
                "keyword": {"type": "string"}
            },
            "required": ["action", "url"]
        }
    
    def execute(self, action: str, url: str, **kwargs) -> str:
        try:
            if action == "get":
                page = self.client.get(url)
                return self._format_page_info(page)
            elif action == "text":
                text = self.client.get(url).text
                return f"📄 网页文本内容:\n\n{text[:1000]}{'...' if len(text)>1000 else ''}"
            elif action == "title":
                title = self.client.get(url).title
                return f"📌 网页标题: {title}" if title else "❌ 未找到标题"
            elif action == "links":
                links = self.client.get(url).links
                result = [f"🔗 找到 {len(links)} 个链接:"]
                for i, link in enumerate(links[:20]):
                    result.append(f"  {i+1}. {link}")
                return "\n".join(result)
            elif action == "search":
                keyword = kwargs.get("keyword")
                if not keyword:
                    return "❌ 需要提供 keyword 参数"
                page = self.client.get(url)
                if keyword.lower() in page.text.lower():
                    return f"🔎 在网页中找到关键词 '{keyword}'"
                else:
                    return f"❌ 未找到关键词 '{keyword}'"
            else:
                return f"❌ 未知操作: {action}"
        except Exception as e:
            return f"❌ 执行错误: {str(e)}"
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行网页操作"""
        action = kwargs.get("action")
        url = kwargs.get("url")
        
        # 发送开始执行的消息
        output_queue.put(("line", f"\n🌐 执行网页操作: {action} - {url}\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        # 执行操作
        result = self.execute(**kwargs)
        
        # 发送结果
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))
    
    def _format_page_info(self, page: WebPage) -> str:
        if page.error:
            return f"❌ 获取失败: {page.error}"
        
        lines = [
            f"🌐 URL: {page.url}",
            f"📊 状态码: {page.status_code}",
            f"📌 标题: {page.title or '无标题'}",
            f"🔗 链接数: {len(page.links)}",
        ]
        
        if page.text:
            preview = page.text[:200].replace('\n', ' ')
            lines.append(f"📄 预览: {preview}...")
        
        return "\n".join(lines)


# ==================== 文件操作工具（修改版，支持流式输出） ====================

class FileToolBase(Tool):
    """文件操作工具基类"""
    
    def __init__(self, logger: Optional[Logger] = None):
        super().__init__(logger)
    
    def normalize_path(self, filepath: str) -> str:
        return os.path.abspath(os.path.expanduser(filepath))
    
    def check_path_safety(self, filepath: str, check_exists: bool = False) -> Tuple[bool, str, str]:
        """检查路径安全性"""
        try:
            abs_path = self.normalize_path(filepath)
            
            if check_exists and not os.path.exists(abs_path):
                return False, abs_path, f"❌ 文件不存在: {abs_path}"
            
            # 检查文件大小
            if os.path.exists(abs_path) and os.path.isfile(abs_path):
                file_size = os.path.getsize(abs_path)
                max_size = constants.MAX_FILE_SIZE
                if file_size > max_size:
                    return False, abs_path, f"❌ 文件太大 ({file_size/1024/1024:.1f}MB)"
            
            return True, abs_path, ""
            
        except Exception as e:
            return False, filepath, f"❌ 路径检查错误: {str(e)}"


class ReadFileTool(FileToolBase):
    """读取文件内容工具（支持流式输出）"""
    
    def get_name(self) -> str:
        return "read_file"
    
    def get_description(self) -> str:
        return "读取文件内容，支持指定起始行和结束行，或读取开头/结尾"
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filepath": {"type": "string"},
                "encoding": {"type": "string", "default": "utf-8"},
                "start_line": {"type": "integer", "default": 1},
                "end_line": {"type": "integer", "default": 0},
                "max_lines": {"type": "integer", "default": 100},
                "head": {"type": "boolean", "default": False},
                "tail": {"type": "boolean", "default": False}
            },
            "required": ["filepath"]
        }
    
    def _calculate_line_range(self, line_count: int, start_line: int, end_line: int, 
                             max_lines: int, head: bool, tail: bool) -> Tuple[int, int, str]:
        if head:
            start = 0
            end = min(max_lines, line_count)
            desc = f"开头 {end} 行"
        elif tail:
            start = max(0, line_count - max_lines)
            end = line_count
            desc = f"结尾 {line_count - start} 行"
        elif end_line > 0:
            start = max(0, start_line - 1)
            end = min(end_line, line_count)
            desc = f"第 {start_line} 行到第 {end_line} 行"
        else:
            start = max(0, start_line - 1)
            if max_lines > 0:
                end = min(start + max_lines, line_count)
                desc = f"从第 {start_line} 行开始，最多 {max_lines} 行"
            else:
                end = line_count
                desc = f"从第 {start_line} 行到文件末尾"
        
        return start, end, desc
    
    def execute(self, filepath: str, encoding: str = "utf-8", 
                start_line: int = 1, end_line: int = 0, 
                max_lines: int = 100, head: bool = False, 
                tail: bool = False, **kwargs) -> str:
        if error := self.validate_params(["filepath"], filepath=filepath):
            return error
        
        is_safe, abs_path, error = self.check_path_safety(filepath, check_exists=True)
        if not is_safe:
            return error
        
        try:
            file_size = os.path.getsize(abs_path)
            modified_time = datetime.fromtimestamp(os.path.getmtime(abs_path))
            
            with open(abs_path, 'r', encoding=encoding) as f:
                all_lines = f.readlines()
                line_count = len(all_lines)
            
            start, end, range_desc = self._calculate_line_range(
                line_count, start_line, end_line, max_lines, head, tail
            )
            
            if end <= start:
                return f"❌ 无效的行范围"
            
            display_lines = all_lines[start:end]
            
            data = {
                "路径": abs_path,
                "大小": f"{file_size} 字节 ({file_size/1024:.1f}KB)",
                "最后修改": modified_time.strftime(constants.DATETIME_FORMAT),
                "总行数": line_count,
                "显示范围": f"{range_desc} (行 {start+1}-{end})"
            }
            
            if display_lines:
                content_lines = []
                for i, line in enumerate(display_lines):
                    line_num = start + i + 1
                    content = line.rstrip('\n\r')
                    content_lines.append(f"   {line_num:4d} | {content}")
                
                data["内容"] = "\n" + "\n".join(content_lines)
                
                if end < line_count:
                    data["提示"] = f"还有 {line_count - end} 行未显示"
            
            return self.format_result(True, "文件读取成功", data)
            
        except UnicodeDecodeError:
            return f"❌ 文件编码错误：无法使用 {encoding} 编码读取文件"
        except PermissionError:
            return f"❌ 权限错误：无法读取文件 {abs_path}"
        except Exception as e:
            return f"❌ 文件读取错误: {str(e)}"
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行文件读取"""
        filepath = kwargs.get("filepath")
        
        # 发送开始执行的消息
        output_queue.put(("line", f"\n📄 读取文件: {filepath}\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        # 执行操作
        result = self.execute(**kwargs)
        
        # 发送结果
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))


class WriteFileTool(FileToolBase):
    """写入文件工具（支持流式输出）"""
    
    def get_name(self) -> str:
        return "write_file"
    
    def get_description(self) -> str:
        return "文件写入工具 - 支持覆盖、追加"
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filepath": {"type": "string"},
                "content": {"type": "string"},
                "mode": {"type": "string", "enum": ["w", "a"], "default": "w"},
                "encoding": {"type": "string", "default": "utf-8"}
            },
            "required": ["filepath", "content"]
        }
    
    def execute(self, filepath: str = None, content: str = None, mode: str = "w", 
                encoding: str = "utf-8", **kwargs) -> str:
        if error := self.validate_params(["filepath", "content"], filepath=filepath, content=content):
            return error
        
        is_safe, abs_path, error = self.check_path_safety(filepath)
        if not is_safe:
            return error
        
        try:
            directory = os.path.dirname(abs_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            file_exists = os.path.exists(abs_path)
            old_size = os.path.getsize(abs_path) if file_exists else 0
            
            with open(abs_path, mode, encoding=encoding) as f:
                f.write(content)
            
            new_size = len(content.encode(encoding))
            action = "覆盖写入" if mode == "w" else "追加写入"
            
            data = {
                "路径": abs_path,
                "大小": f"{new_size} 字节",
            }
            
            if file_exists:
                data["变化"] = f"{old_size} -> {new_size} 字节"
            else:
                data["状态"] = "新文件已创建"
            
            return self.format_result(True, f"文件{action}成功", data)
            
        except PermissionError:
            return f"❌ 权限错误：无法写入文件"
        except Exception as e:
            return f"❌ 文件写入错误: {str(e)}"
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行文件写入"""
        filepath = kwargs.get("filepath")
        
        # 发送开始执行的消息
        output_queue.put(("line", f"\n📝 写入文件: {filepath}\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        # 执行操作
        result = self.execute(**kwargs)
        
        # 发送结果
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))


class ListFilesTool(FileToolBase):
    """列出目录内容工具（支持流式输出）"""
    
    def get_name(self) -> str:
        return "list_files"
    
    def get_description(self) -> str:
        return "列出指定目录下的文件和子目录"
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "default": "."},
                "show_hidden": {"type": "boolean", "default": False}
            }
        }
    
    def execute(self, directory: str = ".", show_hidden: bool = False, **kwargs) -> str:
        is_safe, abs_path, error = self.check_path_safety(directory)
        if not is_safe:
            return error
        
        if not os.path.exists(abs_path):
            return f"❌ 目录不存在: {abs_path}"
        
        if not os.path.isdir(abs_path):
            return f"❌ 路径不是目录: {abs_path}"
        
        try:
            items = []
            total_size = 0
            file_count = 0
            dir_count = 0
            
            for item in sorted(os.listdir(abs_path)):
                if not show_hidden and item.startswith('.'):
                    continue
                
                item_path = os.path.join(abs_path, item)
                
                if os.path.isdir(item_path):
                    items.append(f"📁 {item}/")
                    dir_count += 1
                else:
                    size = os.path.getsize(item_path)
                    total_size += size
                    file_count += 1
                    
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024*1024:
                        size_str = f"{size/1024:.1f}KB"
                    else:
                        size_str = f"{size/1024/1024:.1f}MB"
                    
                    items.append(f"📄 {item} ({size_str})")
            
            data = {
                "目录": abs_path,
                "统计": f"{file_count} 个文件, {dir_count} 个目录",
                "总大小": f"{total_size/1024:.1f}KB" if file_count > 0 else "0KB"
            }
            
            if items:
                data["内容"] = "\n" + "\n".join(items[:50])
                if len(items) > 50:
                    data["提示"] = f"还有 {len(items)-50} 个项目未显示"
            else:
                data["内容"] = "\n📭 目录为空"
            
            return self.format_result(True, "目录列表成功", data)
            
        except Exception as e:
            return f"❌ 列出目录错误: {str(e)}"
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行列出目录"""
        directory = kwargs.get("directory", ".")
        
        # 发送开始执行的消息
        output_queue.put(("line", f"\n📁 列出目录: {directory}\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        # 执行操作
        result = self.execute(**kwargs)
        
        # 发送结果
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))


# ==================== 系统工具（修改版，支持流式输出） ====================

class GetCurrentTimeTool(Tool):
    """获取当前时间工具（支持流式输出）"""
    
    def get_name(self) -> str:
        return "get_current_time"
    
    def get_description(self) -> str:
        return "获取当前日期和时间"
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["full", "date", "time"], "default": "full"}
            }
        }
    
    def execute(self, format: str = "full", **kwargs) -> str:
        now = datetime.now()
        
        if format == "date":
            result = now.strftime("%Y-%m-%d")
        elif format == "time":
            result = now.strftime("%H:%M:%S")
        else:
            result = now.strftime(constants.DATETIME_FORMAT)
        
        return self.format_result(True, "当前时间", {"时间": result})
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行获取时间"""
        output_queue.put(("line", "\n🕐 获取当前时间\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        result = self.execute(**kwargs)
        
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))


class CalculatorTool(Tool):
    """计算器工具（支持流式输出）"""
    
    def get_name(self) -> str:
        return "calculator"
    
    def get_description(self) -> str:
        return "执行数学计算"
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
                "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]}
            },
            "required": ["a", "b", "operation"]
        }
    
    def execute(self, a: float, b: float, operation: str, **kwargs) -> str:
        operations = {
            "add": ("+", a + b),
            "subtract": ("-", a - b),
            "multiply": ("*", a * b),
            "divide": ("/", a / b if b != 0 else None)
        }
        
        if operation not in operations:
            return f"❌ 未知运算: {operation}"
        
        op_symbol, result = operations[operation]
        
        if result is None:
            return "❌ 错误：除数不能为0"
        
        data = {
            "表达式": f"{a} {op_symbol} {b}",
            "结果": result
        }
        
        return self.format_result(True, "计算成功", data)
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行计算"""
        output_queue.put(("line", "\n🧮 执行计算\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        result = self.execute(**kwargs)
        
        output_queue.put(("line", result + "\n"))
        output_queue.put(("complete", result))


class CommandLineTool(Tool):
    """命令行执行工具 - 使用抽象的命令执行器（已支持流式输出）"""
    
    def __init__(self, executor: CommandExecutor = None, logger=None):
        super().__init__(logger)
        self.executor = executor or SubprocessCommandExecutor(logger)
    
    def get_name(self) -> str:
        return "run_command"
    
    def get_description(self) -> str:
        return """执行任意系统命令，支持实时输出显示"""
    
    def get_parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer", "default": 30, "description": "命令执行超时时间（秒）"},
                "stream": {"type": "boolean", "default": True, "description": "是否实时输出"}
            },
            "required": ["command"]
        }
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行命令"""
        command = kwargs.get("command")
        timeout = kwargs.get("timeout", 30)
        
        if not command:
            output_queue.put(("line", "❌ 错误：缺少命令参数\n"))
            output_queue.put(("complete", "❌ 错误：缺少命令参数"))
            return
        
        # 使用执行器的流式执行方法
        self.executor.execute_streaming(
            command=command,
            output_queue=output_queue,
            timeout=timeout
        )
    
    def execute(self, command: str, timeout: int = 30, stream: bool = True, **kwargs) -> str:
        """执行命令"""
        if error := self.validate_params(["command"], command=command):
            return error
        
        # 如果正在流式输出，直接返回空（实际输出通过队列）
        if self.streaming_output and self.output_queue:
            return ""
        
        # 根据stream参数决定使用流式还是非流式执行
        if stream:
            # 流式执行需要调用方处理输出队列
            return self.executor.execute(command, timeout, **kwargs)
        else:
            # 非流式执行
            return self.executor.execute(command, timeout, **kwargs)


# ==================== AI聊天类（修改版：添加重置对话记忆和重新加载系统提示词功能，压缩静默执行） ====================

class DeepSeekChat:
    """单AI聊天类"""
    
    def __init__(self, api_key: str = None, max_history: int = None,
                 system_prompt: str = None, debug_level: int = None, exit_callback: Callable = None,
                 history_manager: ConversationHistory = None, memory_db: MemoryDatabase = None,
                 memo_db: MemoDatabase = None, command_executor: CommandExecutor = None,
                 prompt_manager: PromptManager = None):
        self.name = "DeepSeek"
        self.debug_level = debug_level if debug_level is not None else Logger("").level
        self.logger = Logger(self.name, self.debug_level)
        self.config = ConfigManager()
        self.history_manager = history_manager
        self.memory_db = memory_db
        self.memo_db = memo_db
        self.prompt_manager = prompt_manager or PromptManager()
        self.history_loaded = False
        self.conversation_active = True
        self.messages = []
        
        # 添加对话压缩器
        self.compressor = ConversationCompressor(self, self.logger)
        
        api_key_env = self.config.get("api.api_key_env")
        self.api_key = api_key or os.environ.get(api_key_env)
        if not self.api_key:
            try:
                with open(f"{os.environ['HOME']}/.cert/deepseek.key", "r") as f:
                    self.api_key = f.read().strip()
            except Exception as e:
                raise RuntimeError(f"请设置环境变量 {api_key_env} 或在配置文件中设置API Key")
        
        self.max_history = max_history or constants.DEFAULT_MAX_HISTORY
        self.preserve_system = constants.PRESERVE_SYSTEM_PROMPTS
        self.stats = {"api_calls": 0, "tool_calls": 0, "errors": []}
        
        self._init_system_prompts(system_prompt)
        
        self.tool_registry = ToolRegistry(self.logger)
        self._register_tools(exit_callback, command_executor)
    
    def _init_system_prompts(self, system_prompt: str = None):
        """初始化系统提示词 - 从 PromptManager 加载"""
        if system_prompt:
            # 如果明确指定了 system_prompt，使用它
            self._add_message("system", system_prompt)
            self.logger.info("使用指定的系统提示词")
        else:
            # 从 PromptManager 加载所有提示词
            prompts = self.prompt_manager.get_prompts_list()
            if prompts:
                for prompt in prompts:
                    if prompt['content'].strip():
                        self._add_message("system", prompt['content'].strip())
                self.logger.info(f"已加载 {len(prompts)} 个系统提示词")
            else:
                # 如果没有任何提示词，添加一个默认的
                default_prompt = "你是一个智能AI助手。"
                self._add_message("system", default_prompt)
                self.logger.info("使用默认系统提示词")
    
    def _register_tools(self, exit_callback: Callable = None, command_executor: CommandExecutor = None):
        # 内置工具列表
        builtin_tools = [
            GetCurrentTimeTool(self.logger),
            CalculatorTool(self.logger),
            CommandLineTool(command_executor or SubprocessCommandExecutor(self.logger), self.logger),
            ReadFileTool(self.logger),
            WriteFileTool(self.logger),
            ListFilesTool(self.logger),
            SimpleWebCrawlerTool(self.logger),
        ]
        
        if self.memory_db:
            builtin_tools.append(MemoryTool(self.memory_db, self.logger))
        
        if self.memo_db:
            builtin_tools.append(MemoTool(self.memo_db, self.logger))
        
        # 更新身份工具
        builtin_tools.append(UpdateIdentityTool(self.prompt_manager, self.logger))
        
        # 新增：更新智能体自我认识工具
        builtin_tools.append(UpdateSoulTool(self.prompt_manager, self.logger))
        
        # 增强版保存记忆并结束对话工具
        if exit_callback and self.memory_db:
            builtin_tools.append(SaveMemoryAndEndConversationTool(exit_callback, self.memory_db, self.prompt_manager, self.logger))
        
        # 添加技能热重载工具
        builtin_tools.append(ReloadSkillsTool(self.tool_registry, self.logger))
        
        # 注册内置工具（标记为内置）
        self.tool_registry.register_many(builtin_tools, is_builtin=True)
        
        # 加载扩展技能（标记为非内置）
        skills_dir = constants.SKILLS_DIR
        if os.path.exists(skills_dir):
            # 获取所有技能文件（排除以_开头的文件）
            skills_list = [f for f in os.listdir(skills_dir) 
                          if os.path.isfile(os.path.join(skills_dir, f)) 
                          and not f.startswith("_")]
            
            for skill_file in skills_list:
                try:
                    # 为每个技能文件创建扩展工具
                    extool = ExtensionTool(skill_file, self.logger)
                    self.tool_registry.register(extool, is_builtin=False)
                    self.logger.info(f"已加载扩展技能: {extool.get_name()}")
                except Exception as e:
                    self.logger.error(f"加载技能 {skill_file} 失败: {e}")
        
        builtin_count, skill_count = self.tool_registry.get_skills_count()
        self.logger.info(f"已注册工具: 内置 {builtin_count} 个, 扩展技能 {skill_count} 个")
    
    def _load_history_context(self):
        """加载历史对话作为上下文"""
        if self.history_loaded or not self.history_manager:
            return
        
        context = self.history_manager.get_conversation_context()
        if context:
            history_prompt = f"""以下是之前的对话历史，请基于这些历史继续对话。
如果问题涉及到之前的对话内容，请参考这些历史记录。
当前时间: {datetime.now().strftime(constants.DATETIME_FORMAT)}"""
            
            self._add_message("system", history_prompt)
            
            for msg in context:
                self.messages.append(msg)
            
            self.history_loaded = True
            self.logger.info(f"已加载 {len(context)} 条历史消息")
    
    def _add_message(self, role: str, content: str):
        """
        添加消息到历史
        - 用户消息：添加时间戳前缀
        - 助手消息：不添加时间戳前缀
        """
        timestamp = datetime.now().strftime(constants.DATETIME_FORMAT)
        
        if role == "assistant":
            # 助手消息：不添加时间戳前缀，直接保存原始内容
            formatted_content = content
        elif role == "user":
            # 用户消息：添加时间戳前缀
            formatted_content = f"[用户 @ {timestamp}] {content}"
        else:
            # 系统消息：保持原样
            formatted_content = content
        
        self.messages.append({"role": role, "content": formatted_content})
        self._cleanup_messages()
    
    def _cleanup_messages(self):
        """清理消息历史，但保留系统提示词"""
        if len(self.messages) <= self.max_history * 2:
            return
        
        if self.preserve_system:
            system_messages = [msg for msg in self.messages if msg["role"] == "system"]
            other_messages = [msg for msg in self.messages if msg["role"] != "system"]
            other_messages = other_messages[-self.max_history * 2:]
            self.messages = system_messages + other_messages
        else:
            self.messages = self.messages[-self.max_history * 2:]
    

    def _handle_tool_calls(self, tool_calls: List[Dict], output_callback: Callable = None) -> List[Dict]:
        """处理工具调用"""
        if not tool_calls:
            return []
        
        self.stats["tool_calls"] += len(tool_calls)
        tool_messages = []
        
        # 创建输出队列用于流式输出
        output_queue = queue.Queue()
        self.tool_registry.set_output_queue(output_queue)
        
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            tool_name = function.get("name")
            arguments = function.get("arguments", "{}")
            
            try:
                args = json.loads(arguments) if arguments else {}
            except json.JSONDecodeError:
                args = {}
            
            # 对于支持流式输出的工具，检查是否需要流式输出
            tool = self.tool_registry.get_tool(tool_name)
            supports_streaming = hasattr(tool, 'execute_streaming') if tool else False
            
            if supports_streaming and args.get("stream", True):
                if output_callback:
                    output_callback("line", i18n.get('command_output_title') + "\n")
                
                # 在新线程中执行工具
                thread = threading.Thread(
                    target=self.tool_registry.execute_tool,
                    args=(tool_name,),
                    kwargs=args
                )
                thread.daemon = True
                thread.start()
                
                # 实时处理输出
                result_lines = []
                while thread.is_alive() or not output_queue.empty():
                    try:
                        msg_type, content = output_queue.get(timeout=0.1)
                        if msg_type == "line":
                            if output_callback:
                                output_callback("line", content)
                            result_lines.append(content)
                        elif msg_type == "complete":
                            result = content
                            result_lines.append(content)
                    except queue.Empty:
                        continue
                
                result = "".join(result_lines)
                if output_callback:
                    output_callback("line", i18n.get('command_output_end') + "\n")
            else:
                # 普通执行
                result = self.tool_registry.execute_tool(tool_name, **args)
            
            if self.history_manager:
                self.history_manager.add_tool_call(tool_name, args, result)
            
            if tool_name == "save_memory_and_end_conversation" and "✅" in result:
                self.logger.info("检测到保存记忆并结束对话工具调用")
                self.conversation_active = False
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": result
                })
                # 【修复】不直接返回，而是添加后继续处理，但设置标志让后续停止
                break
            
            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "content": result
            })
        
        # 清除输出队列
        self.tool_registry.set_output_queue(None)
        
        return tool_messages

    def _should_search_memory(self, user_input: str) -> bool:
        """判断是否应该搜索记忆"""
        # 检查用户输入是否包含搜索意图的关键词
        search_triggers = [
            '还记得', '之前', '上次', '以前', '我们说过', '我们讨论过',
            '你记得', '你还记得', '我们聊过', '我们谈到', '我们之前',
            '根据之前的', '依据历史', 'refer', 'previous', 'before',
            'last time', 'earlier', '曾经', '过往'
        ]
        
        user_input_lower = user_input.lower()
        for trigger in search_triggers:
            if trigger.lower() in user_input_lower:
                return True
        
        # 检查是否是简单问候（可能不需要搜索）
        greetings = ['你好', '您好', '嗨', 'hello', 'hi', 'hey']
        if user_input_lower.strip() in greetings:
            return False
        
        # 默认情况下，如果记忆库存在，搜索一下也无妨
        return True
    
    def think_and_respond(self, input_text: str, output_callback: Callable = None) -> Optional[str]:
        """思考并回应 - 支持实时流式输出"""
        if not self.conversation_active:
            self.logger.info("对话已结束，重置状态")
            self.conversation_active = True
            if self.preserve_system:
                system_messages = [msg for msg in self.messages if msg["role"] == "system"]
                self.messages = system_messages
            else:
                self.messages = []
            self.logger.info("对话状态已重置")
        
        # 【关键修复】在添加用户消息之前进行压缩检查（静默执行，不输出信息）
        should_compress, reason = self.compressor.should_compress(self.messages)
        if should_compress:
            self.logger.debug(f"压缩检查触发: {reason}")
            # 静默压缩，不输出任何信息到用户
            
            original_count = len(self.messages)
            original_tokens = self.compressor.estimate_tokens(self.messages)
            
            # 压缩对话（会保护最近的消息）
            self.messages = self.compressor.compress_conversation(self.messages)
            
            compressed_count = len(self.messages)
            compressed_tokens = self.compressor.estimate_tokens(self.messages)
            
            self.logger.debug(i18n.get('conversation_compressed', original_count, compressed_count))
            self.logger.debug(f"Token数: {original_tokens} -> {compressed_tokens}")
        
        self.stats["api_calls"] += 1
        
        # ========== 修改开始：在用户输入前后拼接提示词 ==========
        # 前置提示词：告诉AI先搜索记忆
        pre_prompt = """【系统指令】
    在回答用户问题之前，请务必先执行以下步骤：
    1. 使用 `memory search` 工具搜索记忆库中与当前话题相关的记忆
    2. 如果搜索结果中有相关信息，请在回答中适当引用
    3. 这能帮助你保持对话的连贯性，避免重复询问同样的问题

    【重要】
    - 每次回答前都必须执行记忆搜索
    - 如果记忆库中没有相关信息，正常回答即可
    - 对话结束时，必须使用 `save_memory_and_end_conversation` 工具保存本次对话的重要信息并更新智能体状态
    - 当了解到用户的身份信息时，使用 `update_identity` 工具更新 00_IDENTITY.md

    现在请处理用户的输入："""

        # 后置提示词：提醒AI在结束时保存记忆和状态
        post_prompt = """

    【注意】
    当本次对话的话题讨论完成时，请使用 `save_memory_and_end_conversation` 工具结束对话并保存重要信息到记忆库，同时更新你的状态到 100_STATUS.md。"""

        # 拼接后的用户输入
        enhanced_input = pre_prompt + "\n\n" + input_text + post_prompt
        # ========== 修改结束 ==========
        
        self._add_message("user", enhanced_input)
        
        if self.history_manager:
            self.history_manager.add_message("user", enhanced_input, "用户")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 如果找到相关记忆，可以添加到上下文中
        enhanced_messages = []
        
        # 添加所有系统消息
        for msg in self.messages:
            if msg["role"] == "system":
                enhanced_messages.append(msg)
        
        # 添加非系统消息
        for msg in self.messages:
            if msg["role"] != "system":
                enhanced_messages.append(msg)
        
        payload = {
            "model": constants.DEEPSEEK_MODEL,
            "messages": enhanced_messages,
            "temperature": constants.DEFAULT_TEMPERATURE,
            "max_tokens": constants.DEFAULT_MAX_TOKENS,
            "stream": True  # 始终启用流式
        }
        
        tools = self.tool_registry.get_tools_schemas()
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        current_time = datetime.now().strftime("%H:%M:%S")
        if output_callback:
            output_callback("line", f"\n{i18n.get('thinking', current_time)}\n")
            output_callback("line", i18n.get('assistant_prefix'))
        
        full_response = ""
        tool_calls_buffer = []
        current_tool_calls = {}
        
        # 添加缓冲区来累积字符，避免每个字符都发送
        chunk_buffer = ""
        last_send_time = time.time()
        MIN_CHUNK_SIZE = 5  # 最小发送大小
        MAX_CHUNK_DELAY = 0.1  # 最大延迟（秒）
        
        try:
            response = requests.post(
                constants.DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=constants.DEFAULT_TIMEOUT,
                stream=True
            )
            
            if response.status_code != 200:
                error_msg = f"\n错误状态码: {response.status_code}\n错误响应: {response.text}"
                if output_callback:
                    output_callback("error", error_msg)
                response.raise_for_status()
            
            # 处理流式响应 - 实时调用回调
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # 去掉 'data: ' 前缀
                        if data == '[DONE]':
                            # 发送缓冲区中剩余的内容
                            if chunk_buffer and output_callback:
                                output_callback("chunk", chunk_buffer)
                                chunk_buffer = ""
                            if output_callback:
                                output_callback("line", "\n")
                            break
                        
                        try:
                            chunk = json.loads(data)
                            choices = chunk.get('choices', [])
                            if not choices:
                                continue
                            
                            delta = choices[0].get('delta', {})
                            
                            # 处理内容 - 批量发送以提高效率
                            if 'content' in delta and delta['content']:
                                content = delta['content']
                                chunk_buffer += content
                                full_response += content
                                
                                # 判断是否需要发送缓冲区
                                current_time = time.time()
                                if (len(chunk_buffer) >= MIN_CHUNK_SIZE or 
                                    current_time - last_send_time >= MAX_CHUNK_DELAY):
                                    if output_callback:
                                        output_callback("chunk", chunk_buffer)
                                    chunk_buffer = ""
                                    last_send_time = current_time
                            
                            # 处理工具调用
                            if 'tool_calls' in delta:
                                tool_calls = delta['tool_calls']
                                for tc in tool_calls:
                                    index = tc.get('index', 0)
                                    
                                    if index not in current_tool_calls:
                                        current_tool_calls[index] = {
                                            'id': tc.get('id', ''),
                                            'type': 'function',
                                            'function': {
                                                'name': '',
                                                'arguments': ''
                                            }
                                        }
                                    
                                    if 'function' in tc:
                                        if 'name' in tc['function']:
                                            current_tool_calls[index]['function']['name'] = tc['function']['name']
                                        if 'arguments' in tc['function']:
                                            current_tool_calls[index]['function']['arguments'] += tc['function']['arguments']
                            
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON解析错误: {e}, 数据: {data}")
                            continue
            
            # 处理收集到的工具调用
            if current_tool_calls:
                tool_calls_buffer = list(current_tool_calls.values())
                if output_callback:
                    output_callback("line", i18n.get('calling_tools') + "\n")
                
                # 添加助手消息
                assistant_msg_content = full_response if full_response else None
                if assistant_msg_content:
                    self._add_message("assistant", assistant_msg_content)
                    if self.history_manager:
                        self.history_manager.add_message("assistant", assistant_msg_content, self.name)
                else:
                    # 如果没有内容，也需要记录空消息
                    self._add_message("assistant", "")
                    if self.history_manager:
                        self.history_manager.add_message("assistant", "", self.name)
                
                # 添加工具调用消息
                assistant_msg = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls_buffer
                }
                self.messages.append(assistant_msg)
                
                tool_responses = self._handle_tool_calls(tool_calls_buffer, output_callback)
                
                if not self.conversation_active:
                    self.logger.info("对话已结束，停止响应")
                    # 【修复】发送对话结束信号
                    if output_callback:
                        output_callback("dialogue_ended", i18n.get('dialogue_ended'))
                    return None
                
                if tool_responses:
                    self.messages.extend(tool_responses)
                
                if output_callback:
                    output_callback("line", i18n.get('analyzing_tool_results') + "\n")
                return self.think_and_respond("（请基于工具结果继续回答）", output_callback)
            
            elif full_response:
                self._add_message("assistant", full_response)
                if self.history_manager:
                    self.history_manager.add_message("assistant", full_response, self.name)
                
                # 发送完成消息
                if output_callback:
                    output_callback("complete", full_response)
            
            return full_response if full_response else ""
                
        except requests.exceptions.RequestException as e:
            error_msg = f"\n{i18n.get('error_prefix')}API请求失败: {str(e)}"
            if output_callback:
                output_callback("error", error_msg)
            self.stats["errors"].append(str(e))
            return error_msg
        except json.JSONDecodeError as e:
            error_msg = f"\n{i18n.get('error_prefix')}API响应解析失败: {str(e)}"
            if output_callback:
                output_callback("error", error_msg)
            self.stats["errors"].append(str(e))
            return error_msg
        except Exception as e:
            error_msg = f"\n{i18n.get('error_prefix')}{str(e)}"
            if output_callback:
                output_callback("error", error_msg)
            self.stats["errors"].append(str(e))
            return error_msg

    def reset_conversation(self, reload_prompts: bool = True):
        """
        重置对话状态 - 清除所有对话记忆，可选择是否重新加载系统提示词
        
        Args:
            reload_prompts: 是否重新加载系统提示词，默认为 True
        """
        self.conversation_active = True
        self.history_loaded = False  # 重置历史加载标记
        
        if reload_prompts:
            # 完全重置：清除所有消息，重新加载系统提示词
            self.messages = []
            self._init_system_prompts()
            self.logger.info("对话已完全重置，系统提示词已重新加载")
        else:
            # 只清除非系统消息，保留系统提示词
            if self.preserve_system:
                system_messages = [msg for msg in self.messages if msg["role"] == "system"]
                self.messages = system_messages
            else:
                self.messages = []
            self.logger.info("对话已重置（仅清除对话历史）")
    
    def reload_prompts(self):
        """重新加载提示词"""
        old_system_count = len([msg for msg in self.messages if msg["role"] == "system"])
        
        # 移除所有旧的系统消息
        self.messages = [msg for msg in self.messages if msg["role"] != "system"]
        
        # 重新加载提示词
        self.prompt_manager.reload()
        self._init_system_prompts()
        
        new_system_count = len([msg for msg in self.messages if msg["role"] == "system"])
        self.logger.info(f"提示词已重新加载: {old_system_count} -> {new_system_count} 个")
        return new_system_count


# ==================== WebSocket处理器（修改版：添加重置对话功能） ====================

class WebSocketHandler:
    """WebSocket处理器 - 处理WebSocket连接和消息"""
    
    def __init__(self, ai_manager):
        self.ai_manager = ai_manager
        self.logger = Logger("WebSocket")
        self.connected_clients = set()
        self.client_sessions = {}
        
    async def register(self, websocket):
        """注册新客户端"""
        self.connected_clients.add(websocket)
        self.client_sessions[websocket] = {
            "connected_at": datetime.now(),
            "message_count": 0,
            "current_conversation": None
        }
        self.logger.info(i18n.get('client_connected', websocket.remote_address))
        
        # 发送连接确认消息
        await self.send_message(websocket, {
            "type": "connection_ack",
            "message": i18n.get('ws_connected'),
            "timestamp": datetime.now().strftime(constants.DATETIME_FORMAT)
        })
        
        # 发送欢迎信息和初始状态
        await self.send_welcome_info(websocket)
    
    async def unregister(self, websocket):
        """注销客户端"""
        self.connected_clients.remove(websocket)
        if websocket in self.client_sessions:
            del self.client_sessions[websocket]
        self.logger.info(i18n.get('client_disconnected', websocket.remote_address))
    
    async def send_welcome_info(self, websocket):
        """发送欢迎信息"""
        # 发送存储位置
        await self.send_message(websocket, {
            "type": "info",
            "content": i18n.get('data_dir', constants.SAVE_DIR)
        })
        await self.send_message(websocket, {
            "type": "info",
            "content": i18n.get('skills_dir', constants.SKILLS_DIR)
        })
        await self.send_message(websocket, {
            "type": "info",
            "content": i18n.get('prompts_dir', constants.PROMPTS_DIR)
        })
        
        # 发送任务调度器状态
        if self.ai_manager.scheduler and self.ai_manager.scheduler.running:
            stats = self.ai_manager.scheduler.get_stats()
            await self.send_message(websocket, {
                "type": "info",
                "content": i18n.get('scheduler_started')
            })
            await self.send_message(websocket, {
                "type": "info",
                "content": f"📊 任务统计: 总执行次数={stats.get('total_executions', 0)}, 最近执行={len(stats.get('recent_executions', []))}"
            })
        
        # 发送任务统计
        memo_stats = self.ai_manager.memo_db.get_memo_stats()
        if memo_stats['total'] > 0:
            await self.send_message(websocket, {
                "type": "info",
                "content": i18n.get('memo_stats')
            })
            await self.send_message(websocket, {
                "type": "info",
                "content": i18n.get('total_memos', memo_stats['total'])
            })
            await self.send_message(websocket, {
                "type": "info",
                "content": i18n.get('pending_memos', memo_stats['pending'])
            })
            if memo_stats['overdue'] > 0:
                await self.send_message(websocket, {
                    "type": "info",
                    "content": i18n.get('overdue_memos', memo_stats['overdue'])
                })
            await self.send_message(websocket, {
                "type": "info",
                "content": i18n.get('completed_memos', memo_stats['completed'])
            })
        
        # 发送待执行任务列表
        pending = self.ai_manager.memo_db.get_pending_tasks_for_user()
        if pending:
            await self.send_message(websocket, {
                "type": "info",
                "content": i18n.get('pending_memos_title')
            })
            for task in pending[:5]:
                status = i18n.get('memo_overdue') if task['is_overdue'] else i18n.get('memo_pending')
                immediate_tag = "⚡" if task['is_immediate'] else ""
                await self.send_message(websocket, {
                    "type": "task_status",
                    "task_id": task['id'],
                    "title": task['title'],
                    "reminder_time": task['reminder_time'],
                    "status": "overdue" if task['is_overdue'] else "pending",
                    "content": f"{status}{immediate_tag} [ID: {task['id']}] {task['title']} - {task['reminder_time']}"
                })
            if len(pending) > 5:
                await self.send_message(websocket, {
                    "type": "info",
                    "content": i18n.get('more_skills', len(pending)-5)
                })

    async def send_message(self, websocket, message):
        """发送消息到客户端 - 确保完整发送不被截断"""
        try:
            # 将消息转换为JSON字符串
            json_str = json.dumps(message, ensure_ascii=False)
            
            # 直接发送整个字符串，WebSocket协议会自动处理分片
            await websocket.send(json_str)
            
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("连接已关闭，无法发送消息")
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
    
    async def broadcast(self, message):
        """广播消息到所有客户端"""
        for websocket in self.connected_clients.copy():
            try:
                await self.send_message(websocket, message)
            except:
                await self.unregister(websocket)
    
    async def broadcast_task_status(self, task: Dict, status: str, message: str = None):
        """广播任务状态"""
        await self.broadcast({
            "type": "task_status",
            "task_id": task.get('id', 0),
            "title": task.get('title', '未知任务'),
            "status": status,
            "message": message,
            "timestamp": datetime.now().strftime(constants.DATETIME_FORMAT)
        })
    
    async def handle_message(self, websocket, message):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            
            # 更新会话统计
            if websocket in self.client_sessions:
                self.client_sessions[websocket]["message_count"] += 1
            
            if msg_type == "command":
                await self.handle_command(websocket, data)
            elif msg_type == "message":
                await self.handle_user_message(websocket, data)
            elif msg_type == "task":
                await self.handle_task_message(websocket, data)
            elif msg_type == "ping":
                await self.send_message(websocket, {
                    "type": "pong", 
                    "timestamp": datetime.now().strftime(constants.DATETIME_FORMAT)
                })
            else:
                await self.send_message(websocket, {
                    "type": "error",
                    "content": i18n.get('ws_unknown_command', msg_type)
                })
                
        except json.JSONDecodeError:
            await self.send_message(websocket, {
                "type": "error",
                "content": "无效的JSON格式"
            })
        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
            await self.send_message(websocket, {
                "type": "error",
                "content": f"处理失败: {str(e)}"
            })
    
    async def handle_task_message(self, websocket, data):
        """处理任务相关消息 - 简化版，所有任务都是对话任务"""
        action = data.get("action", "").strip()
        
        if action == "add":
            # 添加任务
            title = data.get("title")
            content = data.get("content")
            delay = data.get("delay", 60)  # 默认60秒后执行
            is_immediate = data.get("is_immediate", False)  # 是否为即时任务
            
            # 重复任务参数
            repeat_type = data.get("repeat_type", "none")
            repeat_interval = data.get("repeat_interval", 0)
            repeat_interval_unit = data.get("repeat_interval_unit", "days")
            repeat_end_time = data.get("repeat_end_time")
            
            if not title:
                await self.send_message(websocket, {
                    "type": "error",
                    "content": "需要提供任务标题"
                })
                return
            
            reminder_time = None
            if is_immediate:
                reminder_time = datetime.now().strftime(constants.DATETIME_FORMAT)
            else:
                reminder_time = (datetime.now() + timedelta(seconds=delay)).strftime(constants.DATETIME_FORMAT)
            
            memo_id = self.ai_manager.memo_db.add_user_task(
                title=title,
                content=content,
                reminder_time=reminder_time,
                repeat_type=repeat_type,
                repeat_interval=repeat_interval,
                repeat_interval_unit=repeat_interval_unit,
                repeat_end_time=repeat_end_time,
                is_immediate=is_immediate
            )
            
            immediate_msg = i18n.get('immediate_memo_added') if is_immediate else ""
            repeat_msg = ""
            if repeat_type != "none":
                if repeat_type == "custom":
                    repeat_msg = f" (每{repeat_interval} {repeat_interval_unit})"
                else:
                    repeat_msg = f" ({repeat_type})"
            
            await self.send_message(websocket, {
                "type": "task_added",
                "task_id": memo_id,
                "title": title,
                "reminder_time": reminder_time,
                "content": i18n.get('task_added', title, memo_id) + repeat_msg + immediate_msg
            })
            
            # 广播任务添加
            await self.broadcast_task_status(
                {"id": memo_id, "title": title},
                "added",
                f"新任务: {title}" + repeat_msg + (" (即时)" if is_immediate else "")
            )
            
        elif action == "list":
            pending = self.ai_manager.memo_db.get_pending_tasks_for_user()
            await self.send_message(websocket, {
                "type": "task_list",
                "tasks": pending
            })
            
        elif action == "complete":
            memo_id = data.get("task_id")
            if memo_id:
                if self.ai_manager.memo_db.complete_memo(memo_id):
                    memo = self.ai_manager.memo_db.get_memo(memo_id)
                    await self.send_message(websocket, {
                        "type": "task_completed",
                        "task_id": memo_id,
                        "content": i18n.get('memo_completed', memo_id)
                    })
                    if memo:
                        await self.broadcast_task_status(memo, "completed", f"任务已完成: {memo['title']}")
                else:
                    await self.send_message(websocket, {
                        "type": "error",
                        "content": i18n.get('memo_complete_failed', memo_id)
                    })
    
    async def handle_command(self, websocket, data):
        """处理命令消息"""
        command = data.get("command", "").strip()
        
        if not command:
            return
        
        self.logger.info(f"收到命令: {command}")
        
        if command == "/exit":
            await self.send_message(websocket, {
                "type": "command_result",
                "content": i18n.get('goodbye')
            })
            await websocket.close()
            
        elif command == "/new":
            # 【新增】开始新对话：保存当前对话，重置AI状态，重新加载系统提示词
            self.ai_manager.history_manager.archive_current_conversation()
            if self.ai_manager.ai:
                # 重置对话状态，重新加载系统提示词
                self.ai_manager.ai.reset_conversation(reload_prompts=True)
                # 重置对话进行中标记
                self.ai_manager.dialogue_in_progress = False
                # 重新初始化提示词管理器（确保最新）
                self.ai_manager.prompt_manager.reload()
                self.logger.info(i18n.get('new_conversation_reset'))
                
                await self.send_message(websocket, {
                    "type": "command_result",
                    "content": i18n.get('new_conversation_reset')
                })
                
                # 发送重置完成通知
                await self.send_message(websocket, {
                    "type": "dialogue_reset",
                    "content": i18n.get('dialogue_reset_complete')
                })
            else:
                await self.send_message(websocket, {
                    "type": "command_result",
                    "content": i18n.get('new_conversation')
                })
            
        elif command == "/list":
            conversations = self.ai_manager.history_manager.list_conversations()
            result = f"\n{i18n.get('saved_conversations')}\n"
            for conv in conversations:
                status = i18n.get('conv_status_current') if conv.get('is_current') else i18n.get('conv_status_archived')
                result += f"  {conv['file']} - {conv['topic']} [{status}] ({conv['start_time']})\n"
            await self.send_message(websocket, {
                "type": "command_result",
                "content": result
            })
            
        elif command == "/memories":
            memories = self.ai_manager.memory_db.get_recent_memories(10)
            result = f"\n{i18n.get('recent_memories')}\n"
            for mem in memories:
                result += f"  [ID: {mem['id']}] {mem['topic']} - {mem['summary'][:50]}...\n"
            await self.send_message(websocket, {
                "type": "command_result",
                "content": result
            })
            
        elif command == "/memos":
            memos = self.ai_manager.memo_db.get_all_memos(include_completed=False)
            result = f"\n{i18n.get('pending_memos_title')}\n"
            for memo in memos:
                status = i18n.get('memo_overdue') if memo['reminder_time'] and datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT) < datetime.now() else i18n.get('memo_pending')
                immediate_tag = "⚡" if memo.get('is_immediate') else ""
                repeat_info = ""
                if memo['repeat_type'] != 'none':
                    if memo['repeat_type'] == 'custom':
                        unit = memo.get('repeat_interval_unit', 'days')
                        repeat_info = f" [每{memo['repeat_interval']} {unit}]"
                    else:
                        repeat_info = f" [{memo['repeat_type']}]"
                result += f"  {status}{immediate_tag} [ID: {memo['id']}] {memo['title']}{repeat_info} - {memo.get('reminder_time', '无提醒')}\n"
            await self.send_message(websocket, {
                "type": "command_result",
                "content": result
            })
            
        elif command.startswith("/search "):
            query = command[8:].strip()
            results = self.ai_manager.memory_db.search_memories([query])
            result = i18n.get('search_results', query, len(results)) + "\n"
            for mem in results:
                result += f"  [ID: {mem['id']}] {mem['topic']} - {mem['summary'][:100]}...\n"
            await self.send_message(websocket, {
                "type": "command_result",
                "content": result
            })
            
        elif command == "/config":
            result = f"\n{i18n.get('current_config')}\n"
            result += i18n.get('config_debug', self.ai_manager.config.get('system.debug_level')) + "\n"
            result += i18n.get('config_data_dir', constants.SAVE_DIR) + "\n"
            result += i18n.get('config_skills_dir', constants.SKILLS_DIR) + "\n"
            result += i18n.get('config_prompts_dir', constants.PROMPTS_DIR) + "\n"
            result += i18n.get('config_commands', i18n.get('enabled') if constants.COMMANDS_ENABLED else i18n.get('disabled')) + "\n"
            result += i18n.get('config_history', i18n.get('enabled') if self.ai_manager.history_manager.load_history else i18n.get('disabled')) + "\n"
            result += i18n.get('config_executor', type(self.ai_manager.command_executor).__name__) + "\n"
            result += i18n.get('config_scheduler', i18n.get('enabled') if constants.SCHEDULER_ENABLED else i18n.get('disabled')) + "\n"
            await self.send_message(websocket, {
                "type": "command_result",
                "content": result
            })
            
        elif command == "/reload":
            self.ai_manager.config.reload()
            await self.send_message(websocket, {
                "type": "command_result",
                "content": i18n.get('config_reloaded')
            })
            
        elif command == "/reload_prompts":
            if self.ai_manager.ai:
                new_count = self.ai_manager.ai.reload_prompts()
            else:
                new_count = self.ai_manager.prompt_manager.reload()
            await self.send_message(websocket, {
                "type": "command_result",
                "content": i18n.get('prompts_reloaded', new_count)
            })
            
        elif command == "/check":
            result = i18n.get('checking_memos') + "\n"
            overdue = self.ai_manager.memo_db.get_overdue_memos()
            if overdue:
                result += i18n.get('overdue_found', len(overdue)) + "\n"
                for memo in overdue:
                    immediate_tag = "⚡" if memo.get('is_immediate') else ""
                    repeat_info = ""
                    if memo['repeat_type'] != 'none':
                        if memo['repeat_type'] == 'custom':
                            unit = memo.get('repeat_interval_unit', 'days')
                            repeat_info = f" (每{memo['repeat_interval']} {unit})"
                        else:
                            repeat_info = f" ({memo['repeat_type']})"
                    result += f"  • {immediate_tag}[ID: {memo['id']}] {memo['title']}{repeat_info} - {memo['reminder_time']}\n"
            else:
                result += i18n.get('no_overdue') + "\n"
            await self.send_message(websocket, {
                "type": "command_result",
                "content": result
            })
            
        elif command == "/tasks":
            if self.ai_manager.scheduler:
                stats = self.ai_manager.scheduler.get_stats()
                result = f"\n{i18n.get('task_stats', 
                                        stats.get('total_executions', 0),
                                        stats.get('total_executions', 0),
                                        stats.get('total_executions', 0))}\n\n"
                
                pending = self.ai_manager.memo_db.get_pending_tasks_for_user()
                result += f"待执行任务: {len(pending)} 个\n"
                for task in pending[:10]:
                    status = "⏰" if not task['is_overdue'] else "⚠️"
                    immediate_tag = "⚡" if task['is_immediate'] else ""
                    repeat_info = ""
                    if task['repeat_type'] != 'none':
                        if task['repeat_type'] == 'custom':
                            unit = task.get('repeat_interval_unit', 'days')
                            repeat_info = f" [每{task['repeat_interval']} {unit}]"
                        else:
                            repeat_info = f" [{task['repeat_type']}]"
                    result += f"  {status}{immediate_tag} [ID: {task['id']}] {task['title']}{repeat_info} - {task['reminder_time']}\n"
            else:
                result = "❌ 任务调度器未启用"
            await self.send_message(websocket, {
                "type": "command_result",
                "content": result
            })
            
        elif command == "/help":
            help_text = f"\n可用命令:\n"
            help_text += "  /exit - 退出连接\n"
            help_text += "  /new - 开始新对话（保存当前对话，重置AI记忆，重新加载系统提示词）\n"
            help_text += "  /list - 列出所有对话\n"
            help_text += "  /memories - 查看最近的记忆\n"
            help_text += "  /memos - 查看待办任务\n"
            help_text += "  /search <关键词> - 搜索记忆\n"
            help_text += "  /config - 查看配置\n"
            help_text += "  /reload - 重新加载配置\n"
            help_text += "  /reload_prompts - 重新加载提示词\n"
            help_text += "  /check - 检查过期任务\n"
            help_text += "  /tasks - 查看任务状态\n"
            help_text += "  /help - 显示此帮助\n\n"
            help_text += "任务类型:\n"
            help_text += "  {type: 'task', action: 'add', title: '任务', delay: 60} - 添加一次性任务\n"
            help_text += "  {type: 'task', action: 'add', title: '即时', is_immediate: true} - 添加即时任务（立即执行）\n"
            help_text += "  {type: 'task', action: 'add', title: '重复任务', repeat_type: 'custom', repeat_interval: 5, repeat_interval_unit: 'minutes'} - 每5分钟重复\n"
            help_text += "  {type: 'task', action: 'list'} - 获取任务列表\n"
            help_text += "  {type: 'task', action: 'complete', task_id: 1} - 完成任务\n"
            await self.send_message(websocket, {
                "type": "command_result",
                "content": help_text
            })
            
        else:
            # 如果不是命令，当作普通消息处理
            await self.handle_user_message(websocket, {"type": "message", "content": command})

    async def handle_user_message(self, websocket, data):
        """处理用户消息 - 实时流式输出"""
        content = data.get("content", "").strip()
        
        if not content:
            return
        
        self.logger.info(f"收到用户消息: {content[:50]}...")
        
        # 确保AI已初始化
        if not self.ai_manager.ai:
            self.logger.info("初始化AI...")
            self.ai_manager.add_ai()
        
        # 如果还没有活跃对话，开始新对话
        if not self.ai_manager.dialogue_in_progress:
            self.logger.info("开始新对话")
            self.ai_manager.dialogue_in_progress = True
            self.ai_manager.history_manager.start_new_conversation(content[:50] + "...")
            
            # 发送对话开始消息
            await self.send_message(websocket, {
                "type": "info",
                "content": i18n.get('conversation_start')
            })
        
        # 获取当前事件循环
        loop = asyncio.get_running_loop()
        
        # 定义输出回调函数 - 实时发送
        def output_callback(msg_type, content):
            """AI输出的回调函数 - 实时发送每个chunk"""
            self.logger.info(f"输出回调被调用: {msg_type}, 内容长度: {len(content)}")
            
            # 创建发送消息的协程
            async def send_msg():
                try:
                    await websocket.send(json.dumps({
                        "type": msg_type,
                        "content": content
                    }, ensure_ascii=False))
                    self.logger.info(f"实时消息发送成功: {msg_type}")
                except Exception as e:
                    self.logger.error(f"实时发送消息失败: {e}")
            
            # 提交到事件循环
            asyncio.run_coroutine_threadsafe(send_msg(), loop)
        
        # 让AI思考并回应 - 不等待完整响应，通过回调实时发送
        try:
            self.logger.info("开始AI思考...")
            
            # 在线程池中运行AI思考，通过回调实时发送消息
            response = await loop.run_in_executor(
                None,
                self.ai_manager.ai.think_and_respond,
                content,
                output_callback  # 传递回调函数，AI会在生成每个chunk时调用
            )
            
            self.logger.info(f"AI思考完成，完整响应长度: {len(response) if response else 0}")
            
            # 检查对话是否结束
            if not self.ai_manager.ai.conversation_active:
                self.logger.info("对话结束")
                self.ai_manager.dialogue_in_progress = False
                self.ai_manager.history_manager.end_current_conversation()
                await self.send_message(websocket, {
                    "type": "info",
                    "content": i18n.get('conversation_ended')
                })
                # 【修复】发送明确的对话结束信号
                await self.send_message(websocket, {
                    "type": "dialogue_ended",
                    "content": i18n.get('dialogue_ended')
                })
                
        except Exception as e:
            self.logger.error(f"AI处理消息失败: {e}")
            import traceback
            traceback.print_exc()
            try:
                await websocket.send(json.dumps({
                    "type": "error",
                    "content": f"{i18n.get('error_prefix')}{str(e)}"
                }, ensure_ascii=False))
            except:
                pass


# ==================== 对话管理器（修改版：添加重置对话功能） ====================

class EnhancedAIManager:
    """增强的AI对话管理器 - 集成任务调度器"""
    
    def __init__(self, debug_level: int = None, load_history: bool = None, command_executor: CommandExecutor = None):
        self.ai: Optional[DeepSeekChat] = None
        self.dialogue_history: List[Dict] = []
        self.config = ConfigManager()
        self.command_executor = command_executor or SubprocessCommandExecutor()
        self.prompt_manager = PromptManager()  # 创建提示词管理器
        self.scheduler: Optional[TaskScheduler] = None  # 任务调度器
        
        if debug_level is None:
            debug_level = self.config.get("system.debug_level", 1)
        
        self.logger = Logger("Manager", debug_level)
        self.running = True
        
        # 确保 ~/.aibox 目录存在
        os.makedirs(constants.SAVE_DIR, exist_ok=True)
        # 确保 prompts 目录存在（PromptManager 会创建）
        os.makedirs(constants.PROMPTS_DIR, exist_ok=True)
        
        self.memory_db = MemoryDatabase()
        self.memo_db = MemoDatabase()
        self.history_manager = ConversationHistory(memory_db=self.memory_db, load_history=load_history)
        
        self.dialogue_in_progress = False
        self.ws_handler = None
    
    def global_exit_handler(self, reason: str, summary: str):
        """对话结束处理器"""
        self.logger.info(f"对话结束 - 原因: {reason}")
        
        self.history_manager.end_current_conversation(summary)
        
        if self.ai:
            # 智能体主动结束对话后，重置对话状态但不清除系统提示词
            # 注意：这里只重置对话标记，不清除消息历史
            self.ai.conversation_active = True
            # 但为了下次对话不加载旧的历史，我们清除非系统消息
            if self.ai.preserve_system:
                system_messages = [msg for msg in self.ai.messages if msg["role"] == "system"]
                self.ai.messages = system_messages
            else:
                self.ai.messages = []
            self.ai.history_loaded = False  # 重置历史加载标记
        
        self.dialogue_in_progress = False
        self.logger.info("对话状态已重置，可以开始新对话")
    
    def reset_dialogue(self):
        """重置对话 - 清除所有对话记忆，重新加载系统提示词"""
        if self.ai:
            # 完全重置AI状态，重新加载系统提示词
            self.ai.reset_conversation(reload_prompts=True)
        self.dialogue_in_progress = False
        self.history_manager.reset_conversation()
        self.logger.info(i18n.get('dialogue_reset_complete'))
    
    def add_ai(self) -> DeepSeekChat:
        """添加AI"""
        ai = DeepSeekChat(
            api_key=None,
            max_history=constants.DEFAULT_MAX_HISTORY,
            debug_level=self.logger.level,
            exit_callback=self.global_exit_handler,
            history_manager=self.history_manager,
            memory_db=self.memory_db,
            memo_db=self.memo_db,
            command_executor=self.command_executor,
            prompt_manager=self.prompt_manager
        )
        
        self.ai = ai
        self.logger.info("AI已初始化")
        return ai
    
    def show_welcome_message(self):
        """显示欢迎信息"""
        print("\n" + "="*70)
        print(i18n.get('welcome_title'))
        print("="*70)
        
        # 显示存储位置
        print(i18n.get('data_dir', constants.SAVE_DIR))
        print(i18n.get('skills_dir', constants.SKILLS_DIR))
        print(i18n.get('prompts_dir', constants.PROMPTS_DIR))
        
        config_path = self.config._config_path
        if os.path.exists(config_path):
            print(i18n.get('config_file', config_path))
        
        # 显示提示词数量
        prompt_count = self.prompt_manager.get_prompt_count()
        if prompt_count > 0:
            prompts = self.prompt_manager.get_prompts_list()
            print(i18n.get('loaded_prompts', prompt_count))
            for prompt in prompts[:5]:
                print(i18n.get('prompt_item', prompt['file']))
            if prompt_count > 5:
                print(i18n.get('more_skills', prompt_count-5))
        
        # 显示任务调度器状态
        if constants.SCHEDULER_ENABLED:
            print(i18n.get('scheduler_started'))
        
        memo_stats = self.memo_db.get_memo_stats()
        if memo_stats['total'] > 0:
            print(f"\n{i18n.get('memo_stats')}")
            print(i18n.get('total_memos', memo_stats['total']))
            print(i18n.get('pending_memos', memo_stats['pending']))
            if memo_stats['overdue'] > 0:
                print(i18n.get('overdue_memos', memo_stats['overdue']))
            print(i18n.get('completed_memos', memo_stats['completed']))
        
        # 显示待执行任务
        pending = self.memo_db.get_pending_tasks_for_user()
        if pending:
            print(f"\n{i18n.get('pending_memos_title')}")
            for task in pending[:5]:
                status = i18n.get('memo_overdue') if task['is_overdue'] else i18n.get('memo_pending')
                immediate_tag = "⚡" if task['is_immediate'] else ""
                repeat_info = ""
                if task['repeat_type'] != 'none':
                    if task['repeat_type'] == 'custom':
                        unit = task.get('repeat_interval_unit', 'days')
                        repeat_info = f" [每{task['repeat_interval']} {unit}]"
                    else:
                        repeat_info = f" [{task['repeat_type']}]"
                print(f"  {status}{immediate_tag} [ID: {task['id']}] {task['title']}{repeat_info} - {task['reminder_time']}")
            if len(pending) > 5:
                print(i18n.get('more_skills', len(pending)-5))
        
        # 显示已加载的技能
        skills_dir = constants.SKILLS_DIR
        if os.path.exists(skills_dir):
            skills = [f for f in os.listdir(skills_dir) 
                     if os.path.isfile(os.path.join(skills_dir, f)) 
                     and not f.startswith("_")]
            if skills:
                print(i18n.get('loaded_skills', len(skills)))
                for skill in skills[:5]:
                    print(i18n.get('skill_item', os.path.splitext(skill)[0]))
                if len(skills) > 5:
                    print(i18n.get('more_skills', len(skills)-5))
        
        # 显示WebSocket服务器信息
        host = constants.WEBSOCKET_HOST
        port = constants.WEBSOCKET_PORT
        print(i18n.get('websocket_started', host, port))
    
    async def handle_connection(self, websocket, path):
        """处理WebSocket连接"""
        self.logger.info(f"新连接: {websocket.remote_address}, path: {path}")
        await self.ws_handler.register(websocket)
        try:
            async for message in websocket:
                await self.ws_handler.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.info(f"连接关闭: {e}")
        except Exception as e:
            self.logger.error(f"处理错误: {e}")
        finally:
            await self.ws_handler.unregister(websocket)

    async def websocket_server(self):
        """启动WebSocket服务器并集成任务调度器"""
        host = constants.WEBSOCKET_HOST
        port = constants.WEBSOCKET_PORT
        
        self.ws_handler = WebSocketHandler(self)
        
        # 如果启用了任务调度器，创建并启动
        if constants.SCHEDULER_ENABLED:
            self.scheduler = TaskScheduler(asyncio.get_running_loop(), self.logger)
            self.scheduler.set_websocket_handler(self.ws_handler)
            self.scheduler.set_ai_manager(self)  # 设置AI管理器引用
        
        async def handler(websocket):
            await self.handle_connection(websocket, None)
        
        server = await websockets.serve(handler, host, port)
        self.logger.info(i18n.get('websocket_started', host, port))
        
        try:
            if self.scheduler:
                # 同时运行服务器和调度器
                await asyncio.gather(
                    server.wait_closed(),
                    self.scheduler.run(self.memo_db)
                )
            else:
                # 只运行服务器
                await server.wait_closed()
        finally:
            if self.scheduler:
                self.scheduler.stop()
    
    def run(self):
        """运行WebSocket服务器"""
        self.add_ai()
        self.show_welcome_message()
        
        # 检查过期任务
        overdue = self.memo_db.get_overdue_memos()
        if overdue:
            print(f"\n⏰ {i18n.get('overdue_found', len(overdue))}")
            for memo in overdue[:5]:
                immediate_tag = "⚡" if memo.get('is_immediate') else ""
                repeat_info = ""
                if memo['repeat_type'] != 'none':
                    if memo['repeat_type'] == 'custom':
                        unit = memo.get('repeat_interval_unit', 'days')
                        repeat_info = f" (每{memo['repeat_interval']} {unit})"
                    else:
                        repeat_info = f" ({memo['repeat_type']})"
                print(f"  • {immediate_tag}[ID: {memo['id']}] {memo['title']}{repeat_info} - {memo['reminder_time']}")
            if len(overdue) > 5:
                print(f"  ... {i18n.get('more_skills', len(overdue)-5)}")
        
        # 运行WebSocket服务器
        try:
            # 使用 asyncio.run() 运行服务器
            asyncio.run(self.websocket_server())
        except KeyboardInterrupt:
            print(f"\n\n{i18n.get('user_interrupted')}")
            self.history_manager.end_current_conversation()
        except Exception as e:
            print(f"\n{i18n.get('error_prefix')}{e}")
            import traceback
            traceback.print_exc()


# ==================== 命令行参数处理 ====================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='单AI智能体系统 - WebSocket版本（所有任务都是对话任务）')
    
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    
    parser.add_argument('--check-memo', action='store_true', help='立即检查到期任务并退出')
    
    parser.add_argument('--memo-add', type=str, help='添加任务，格式: "标题|内容|提醒时间|重复类型|重复间隔|单位"')
    parser.add_argument('--memo-list', action='store_true', help='列出任务')
    parser.add_argument('--memo-complete', type=int, help='完成指定ID的任务')
    
    parser.add_argument('-d', '--debug', type=int, choices=[0, 1, 2, 3], default=None, help='调试级别')
    parser.add_argument('-c', '--config', type=str, help='指定配置文件路径')
    
    # 添加语言选项
    parser.add_argument('--lang', type=str, choices=['zh', 'en'], help='强制指定语言 (zh/en)')
    
    # WebSocket选项
    parser.add_argument('--host', type=str, help='WebSocket服务器主机')
    parser.add_argument('--port', type=int, help='WebSocket服务器端口')
    
    # 调度器选项
    parser.add_argument('--no-scheduler', action='store_true', help='禁用任务调度器')
    parser.add_argument('--scheduler-interval', type=float, default=1.0, help='调度器检查间隔（秒）')
    
    return parser.parse_args()


def create_command_executor(args):
    """根据命令行参数创建命令执行器"""
    # 现在只使用本地执行器
    return SubprocessCommandExecutor()


def handle_check_commands(manager):
    """处理检查命令"""
    args = parse_args()
    
    if args.check_memo:
        print(i18n.get('memo_check_title'))
        overdue = manager.memo_db.get_overdue_memos()
        if overdue:
            print(i18n.get('memo_check_found', len(overdue)))
            for memo in overdue:
                immediate_tag = "⚡" if memo.get('is_immediate') else ""
                repeat_info = ""
                if memo['repeat_type'] != 'none':
                    if memo['repeat_type'] == 'custom':
                        unit = memo.get('repeat_interval_unit', 'days')
                        repeat_info = f" (每{memo['repeat_interval']} {unit})"
                    else:
                        repeat_info = f" ({memo['repeat_type']})"
                print(f"  • {immediate_tag}[ID: {memo['id']}] {memo['title']}{repeat_info} (提醒: {memo['reminder_time']})")
        else:
            print(i18n.get('memo_check_none'))
        return True
    
    return False


def handle_memo_commands(manager):
    """处理备忘录命令"""
    args = parse_args()
    
    if args.memo_list:
        memos = manager.memo_db.get_all_memos(include_completed=False)
        if not memos:
            print("📭 " + i18n.get('memo_check_none'))
        else:
            print(i18n.get('memo_list_title', len(memos)))
            for memo in memos:
                overdue = ""
                if memo['reminder_time']:
                    try:
                        reminder = datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT)
                        if reminder < datetime.now():
                            overdue = " ⚠️"
                    except:
                        pass
                immediate_tag = "⚡" if memo.get('is_immediate') else ""
                repeat_info = ""
                if memo['repeat_type'] != 'none':
                    if memo['repeat_type'] == 'custom':
                        unit = memo.get('repeat_interval_unit', 'days')
                        repeat_info = f" [每{memo['repeat_interval']} {unit}]"
                    else:
                        repeat_info = f" [{memo['repeat_type']}]"
                print(f"  {immediate_tag}[ID: {memo['id']}] {memo['title']}{repeat_info}{overdue}")
        return True
    
    if args.memo_add:
        try:
            parts = args.memo_add.split('|')
            title = parts[0]
            content = parts[1] if len(parts) > 1 else ""
            reminder = parts[2] if len(parts) > 2 else None
            
            # 解析重复参数
            repeat_type = parts[3] if len(parts) > 3 else "none"
            repeat_interval = int(parts[4]) if len(parts) > 4 else 0
            repeat_interval_unit = parts[5] if len(parts) > 5 else "days"
            
            is_immediate = reminder == "immediate"  # 如果提醒时间是"immediate"，则创建即时任务
            
            memo_id = manager.memo_db.add_memo(
                title=title,
                content=content,
                reminder_time=None if is_immediate else reminder,
                created_by="cli",
                source="cli",
                repeat_type=repeat_type,
                repeat_interval=repeat_interval,
                repeat_interval_unit=repeat_interval_unit,
                is_immediate=is_immediate
            )
            
            repeat_msg = ""
            if repeat_type != "none":
                if repeat_type == "custom":
                    repeat_msg = f" (每{repeat_interval} {repeat_interval_unit})"
                else:
                    repeat_msg = f" ({repeat_type})"
            
            print(i18n.get('memo_added', memo_id) + repeat_msg + (" (即时任务)" if is_immediate else ""))
        except Exception as e:
            print(i18n.get('memo_add_failed', e))
        return True
    
    if args.memo_complete:
        if manager.memo_db.complete_memo(args.memo_complete):
            print(i18n.get('memo_completed', args.memo_complete))
        else:
            print(i18n.get('memo_complete_failed', args.memo_complete))
        return True
    
    return False


# ==================== 主程序 ====================

def main():
    """主程序入口"""
    args = parse_args()
    
    # 如果命令行指定了语言，覆盖自动检测
    if args.lang:
        os.environ["AI_LANGUAGE"] = args.lang
        # 重新初始化i18n
        global i18n
        i18n = I18n()
    
    if args.config:
        os.environ["AI_CONFIG_PATH"] = args.config
    
    config = ConfigManager()
    
    if args.debug is not None:
        config._config["system"]["debug_level"] = args.debug
    
    if args.verbose:
        config._config["system"]["debug_level"] = 3
    
    # 覆盖WebSocket主机和端口
    if args.host:
        config._config["system"]["websocket_host"] = args.host
    if args.port:
        config._config["system"]["websocket_port"] = args.port
    
    # 调度器设置
    if args.no_scheduler:
        config._config["scheduler"]["enabled"] = False
    if args.scheduler_interval:
        config._config["scheduler"]["check_interval"] = args.scheduler_interval
    
    # 确保 ~/.aibox 目录存在
    os.makedirs(constants.SAVE_DIR, exist_ok=True)
    
    # 确保 skills 目录存在
    os.makedirs(constants.SKILLS_DIR, exist_ok=True)
    
    # 确保 prompts 目录存在
    os.makedirs(constants.PROMPTS_DIR, exist_ok=True)
    
    Logger.init_file_logging()
    
    # 创建命令执行器 - 现在只使用本地执行器
    command_executor = SubprocessCommandExecutor()
    
    manager = EnhancedAIManager(
        debug_level=args.debug,
        command_executor=command_executor
    )
    
    if handle_check_commands(manager):
        return
    
    if handle_memo_commands(manager):
        return
    
    # 运行WebSocket服务器
    manager.run()


if __name__ == "__main__":
    main()