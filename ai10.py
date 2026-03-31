#!/usr/bin/env python3
"""
单AI智能体系统 - 与用户直接对话
功能：支持文件操作、网页访问、记忆管理、备忘录提醒、命令行执行（支持流式输出）
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
import queue
import locale
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Callable, Union
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
            # 尝试获取系统locale
            system_locale, _ = locale.getdefaultlocale()
            if system_locale:
                # 检查是否为英文环境
                if system_locale.startswith('en_'):
                    self._lang = 'en'
                else:
                    self._lang = 'zh'
            else:
                # 默认使用中文
                self._lang = 'zh'
        except:
            self._lang = 'zh'
        
        # 可以通过环境变量强制指定
        force_lang = os.environ.get("AI_LANGUAGE")
        if force_lang in ['en', 'zh']:
            self._lang = force_lang
    
    def _load_strings(self):
        """加载多语言字符串"""
        self._strings = {
            'zh': {
                # 欢迎信息
                'welcome_title': "🤖 单AI智能体系统 - 与用户直接对话",
                'data_dir': "📁 数据存储目录: {}",
                'skills_dir': "📁 技能目录: {}",
                'config_file': "📋 配置文件: {}",
                'memo_stats': "📋 备忘录统计:",
                'total_memos': "  📝 总备忘录: {} 条",
                'pending_memos': "  ⏰ 待处理: {} 条",
                'overdue_memos': "  ⚠️ 已过期: {} 条",
                'completed_memos': "  ✅ 已完成: {} 条",
                'loaded_skills': "🔧 已加载扩展技能 ({} 个):",
                'skill_item': "  • {}",
                'more_skills': "  ... 还有 {} 个",
                'available_commands': "📚 可用命令:",
                'cmd_exit': "  /exit   - 退出程序",
                'cmd_new': "  /new    - 开始新对话（历史已保存）",
                'cmd_list': "  /list   - 查看所有保存的对话",
                'cmd_memories': "  /memories - 查看最近的记忆",
                'cmd_memos': "  /memos  - 查看所有待处理的备忘录",
                'cmd_search': "  /search <关键词> - 搜索记忆",
                'cmd_config': "  /config - 查看当前配置",
                'cmd_reload': "  /reload - 重新加载配置文件",
                'cmd_check': "  /check  - 检查备忘录",
                'cmd_help': "  /help   - 显示此帮助",
                'features_title': "⚙️ 功能说明:",
                'feature_data_dir': "  - 所有数据都保存在 ~/.aibox/ 目录下",
                'feature_memory_check': "  - AI会习惯性查看相关记忆，保持对话连贯性",
                'feature_memory_save': "  - 对话结束时会自动保存记忆到记忆库",
                'feature_command_full': "  - 命令执行工具已完全解放，可执行任意命令",
                'feature_command_stream': "  - 命令执行支持实时输出显示",
                'feature_skills': "  - 支持通过 skills 目录动态加载扩展技能",
                'feature_skills_interface': "  - 扩展技能需要实现 --description, --parameters, --execute 接口",
                
                # 命令处理
                'goodbye': "👋 再见！",
                'new_conversation': "🔄 开始新对话（历史已保存）",
                'saved_conversations': "📚 已保存的对话:",
                'conv_status_current': "当前",
                'conv_status_archived': "归档",
                'recent_memories': "📚 最近的记忆:",
                'pending_memos_title': "📋 待处理的备忘录:",
                'memo_overdue': "⚠️",
                'memo_pending': "⏰",
                'search_results': "🔍 搜索 '{}' 找到 {} 条记忆:",
                'current_config': "⚙️  当前配置:",
                'config_debug': "  调试级别: {}",
                'config_data_dir': "  数据目录: {}",
                'config_skills_dir': "  技能目录: {}",
                'config_commands': "  命令执行: {}",
                'config_history': "  加载历史: {}",
                'config_executor': "  命令执行器: {}",
                'enabled': "启用",
                'disabled': "禁用",
                'config_reloaded': "✅ 配置已重新加载",
                'checking_memos': "🔍 检查备忘录...",
                'overdue_found': "发现 {} 条到期备忘录:",
                'no_overdue': "没有到期备忘录",
                'memo_tool_usage': "📝 备忘录工具使用:",
                'memo_usage_in_dialogue': "  在对话中可以直接使用 memo 工具:",
                'memo_add_example': "  - memo add title=\"标题\" content=\"内容\" reminder_time=\"+1h\"",
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
                
                # 对话相关
                'input_prompt': "💬 请输入问题 (输入 /help 查看命令): ",
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
                'memo_check_title': "⏰ 检查到期备忘录...",
                'memo_check_found': "发现 {} 条到期备忘录:",
                'memo_check_none': "没有到期的备忘录",
                'memo_list_title': "📋 待处理备忘录 (共 {} 条):",
                'memo_added': "✅ 备忘录已添加，ID: {}",
                'memo_add_failed': "❌ 添加失败: {}",
                'memo_completed': "✅ 备忘录 #{} 已完成",
                'memo_complete_failed': "❌ 无法完成备忘录 #{}",
                
                # 新对话
                'new_dialogue_start': "🎭 开始新对话: {}",
                
                # 记忆相关
                'memory_check': "习惯性检查相关记忆...",
                'memory_found': "找到 {} 条相关记忆",
                
                # 配置文件
                'config_loaded': "📋 已加载配置文件: {}",
                'config_not_found': "📋 配置文件不存在: {}，使用默认配置",
                'config_created': "📋 已创建默认配置文件: {}",
                
                # 系统提示词（这部分保持不变，只是说明可以回复英文）
                'system_prompt': [
                    "你是DeepSeek，一个智能AI助手，可以帮你完成各种任务。",
                    "",
                    "【你的特点】",
                    "- 拥有完整的对话历史记忆，可以基于之前的对话继续讨论",
                    "- 可以使用各种工具来执行任务：文件操作、网页访问、备忘录、记忆管理等",
                    "- **重要习惯**：每次回答用户问题前，应该先使用 `memory search` 工具查阅相关记忆，确保回答的连贯性和准确性",
                    "- 当话题讨论完成时，要主动结束对话并保存重要信息",
                    "- 使用 `save_memory_and_end_conversation` 工具来保存记忆并结束对话，提供详细的对话总结",
                    "",
                    "【记忆搜索习惯】",
                    "- **养成习惯**：在每次回答前，先搜索记忆库中是否有相关记录",
                    "- 搜索时使用与当前话题相关的关键词",
                    "- 如果搜索结果包含有用信息，在回答中适当引用",
                    "- 这能帮助你保持对话的连贯性，避免重复询问同样的问题",
                    "",
                    "【记忆保存习惯】",
                    "- 在对话结束时，一定要保存重要的对话内容到记忆库",
                    "- 总结要全面，包含关键信息和结论",
                    "- 使用 `save_memory_and_end_conversation` 工具完成",
                    "",
                    "【备忘录能力】",
                    "- 你可以创建备忘录提醒用户和自己",
                    "- 支持查看、完成、删除备忘录",
                    "- 定期检查备忘录是否有需要处理的事项",
                    "",
                    "【文件操作能力】",
                    "- write_file: 写入文件",
                    "- read_file: 读取文件",
                    "- list_files: 列出目录",
                    "",
                    "【网页访问能力】",
                    "- web: 获取网页内容、搜索关键词、下载文件",
                    "",
                    "【记忆管理能力】",
                    "- memory save: 保存重要的发现和结论",
                    "- memory search: 搜索记忆",
                    "- memory delete: 删除无用记忆",
                    "",
                    "【多种多样的扩展能力】",
                    "- 根据工具介绍，使用json格式传递参数",
                    "- 优先使用扩展工具",
                    "",
                    "【语言说明】",
                    "- 你可以用中文或英文回复用户，根据用户的输入语言来选择",
                    "- 如果用户用中文提问，你可以用中文回复",
                    "- 如果用户用英文提问，你可以用英文回复",
                    "- 用户可能会要求你用特定语言回复，请遵循用户的指示",
                    "",
                    "记住：你是智能助手，要主动帮助用户解决问题！"
                ]
            },
            'en': {
                # Welcome messages
                'welcome_title': "🤖 Single AI Agent System - Direct Dialogue with User",
                'data_dir': "📁 Data directory: {}",
                'skills_dir': "📁 Skills directory: {}",
                'config_file': "📋 Configuration file: {}",
                'memo_stats': "📋 Memo statistics:",
                'total_memos': "  📝 Total memos: {}",
                'pending_memos': "  ⏰ Pending: {}",
                'overdue_memos': "  ⚠️ Overdue: {}",
                'completed_memos': "  ✅ Completed: {}",
                'loaded_skills': "🔧 Loaded extension skills ({}):",
                'skill_item': "  • {}",
                'more_skills': "  ... {} more",
                'available_commands': "📚 Available commands:",
                'cmd_exit': "  /exit   - Exit program",
                'cmd_new': "  /new    - Start new conversation (history saved)",
                'cmd_list': "  /list   - View all saved conversations",
                'cmd_memories': "  /memories - View recent memories",
                'cmd_memos': "  /memos  - View all pending memos",
                'cmd_search': "  /search <keyword> - Search memories",
                'cmd_config': "  /config - View current configuration",
                'cmd_reload': "  /reload - Reload configuration file",
                'cmd_check': "  /check  - Check memos",
                'cmd_help': "  /help   - Show this help",
                'features_title': "⚙️ Features:",
                'feature_data_dir': "  - All data is saved in ~/.aibox/ directory",
                'feature_memory_check': "  - AI habitually checks relevant memories for conversation continuity",
                'feature_memory_save': "  - Automatically saves memories to database when conversation ends",
                'feature_command_full': "  - Command execution tool is fully enabled, can execute any command",
                'feature_command_stream': "  - Command execution supports real-time output display",
                'feature_skills': "  - Supports dynamic loading of extension skills through skills directory",
                'feature_skills_interface': "  - Extension skills need to implement --description, --parameters, --execute interfaces",
                
                # Command processing
                'goodbye': "👋 Goodbye!",
                'new_conversation': "🔄 Starting new conversation (history saved)",
                'saved_conversations': "📚 Saved conversations:",
                'conv_status_current': "current",
                'conv_status_archived': "archived",
                'recent_memories': "📚 Recent memories:",
                'pending_memos_title': "📋 Pending memos:",
                'memo_overdue': "⚠️",
                'memo_pending': "⏰",
                'search_results': "🔍 Searching '{}' found {} memories:",
                'current_config': "⚙️  Current configuration:",
                'config_debug': "  Debug level: {}",
                'config_data_dir': "  Data directory: {}",
                'config_skills_dir': "  Skills directory: {}",
                'config_commands': "  Command execution: {}",
                'config_history': "  Load history: {}",
                'config_executor': "  Command executor: {}",
                'enabled': "enabled",
                'disabled': "disabled",
                'config_reloaded': "✅ Configuration reloaded",
                'checking_memos': "🔍 Checking memos...",
                'overdue_found': "Found {} overdue memos:",
                'no_overdue': "No overdue memos",
                'memo_tool_usage': "📝 Memo tool usage:",
                'memo_usage_in_dialogue': "  You can use memo tool directly in dialogue:",
                'memo_add_example': "  - memo add title=\"Title\" content=\"Content\" reminder_time=\"+1h\"",
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
                
                # Dialogue related
                'input_prompt': "💬 Please enter your question (enter /help for commands): ",
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
                'memo_check_title': "⏰ Checking overdue memos...",
                'memo_check_found': "Found {} overdue memos:",
                'memo_check_none': "No overdue memos",
                'memo_list_title': "📋 Pending memos (total {}):",
                'memo_added': "✅ Memo added, ID: {}",
                'memo_add_failed': "❌ Failed to add: {}",
                'memo_completed': "✅ Memo #{} completed",
                'memo_complete_failed': "❌ Cannot complete memo #{}",
                
                # New dialogue
                'new_dialogue_start': "🎭 Starting new dialogue: {}",
                
                # Memory related
                'memory_check': "Habitually checking relevant memories...",
                'memory_found': "Found {} relevant memories",
                
                # Configuration file
                'config_loaded': "📋 Configuration file loaded: {}",
                'config_not_found': "📋 Configuration file not found: {}, using default configuration",
                'config_created': "📋 Default configuration file created: {}",
                
                # System prompts (keep Chinese but add instruction about English)
                'system_prompt': [
                    "你是DeepSeek，一个智能AI助手，可以帮你完成各种任务。",
                    "",
                    "【你的特点】",
                    "- 拥有完整的对话历史记忆，可以基于之前的对话继续讨论",
                    "- 可以使用各种工具来执行任务：文件操作、网页访问、备忘录、记忆管理等",
                    "- **重要习惯**：每次回答用户问题前，应该先使用 `memory search` 工具查阅相关记忆，确保回答的连贯性和准确性",
                    "- 当话题讨论完成时，要主动结束对话并保存重要信息",
                    "- 使用 `save_memory_and_end_conversation` 工具来保存记忆并结束对话，提供详细的对话总结",
                    "",
                    "【记忆搜索习惯】",
                    "- **养成习惯**：在每次回答前，先搜索记忆库中是否有相关记录",
                    "- 搜索时使用与当前话题相关的关键词",
                    "- 如果搜索结果包含有用信息，在回答中适当引用",
                    "- 这能帮助你保持对话的连贯性，避免重复询问同样的问题",
                    "",
                    "【记忆保存习惯】",
                    "- 在对话结束时，一定要保存重要的对话内容到记忆库",
                    "- 总结要全面，包含关键信息和结论",
                    "- 使用 `save_memory_and_end_conversation` 工具完成",
                    "",
                    "【备忘录能力】",
                    "- 你可以创建备忘录提醒用户和自己",
                    "- 支持查看、完成、删除备忘录",
                    "- 定期检查备忘录是否有需要处理的事项",
                    "",
                    "【文件操作能力】",
                    "- write_file: 写入文件",
                    "- read_file: 读取文件",
                    "- list_files: 列出目录",
                    "",
                    "【网页访问能力】",
                    "- web: 获取网页内容、搜索关键词、下载文件",
                    "",
                    "【记忆管理能力】",
                    "- memory save: 保存重要的发现和结论",
                    "- memory search: 搜索记忆",
                    "- memory delete: 删除无用记忆",
                    "",
                    "【多种多样的扩展能力】",
                    "- 根据工具介绍，使用json格式传递参数",
                    "- 优先使用扩展工具",
                    "",
                    "【语言说明】",
                    "- 你可以用中文或英文回复用户，根据用户的输入语言来选择",
                    "- 如果用户用中文提问，你可以用中文回复",
                    "- 如果用户用英文提问，你可以用英文回复",
                    "- 用户可能会要求你用特定语言回复，请遵循用户的指示",
                    "",
                    "记住：你是智能助手，要主动帮助用户解决问题！"
                ]
            }
        }
    
    def get(self, key: str, *args) -> str:
        """获取指定语言的字符串，支持格式化参数"""
        if key in self._strings[self._lang]:
            text = self._strings[self._lang][key]
            if args:
                return text.format(*args)
            return text
        # 如果当前语言没有该键，尝试返回中文
        if key in self._strings['zh']:
            text = self._strings['zh'][key]
            if args:
                return text.format(*args)
            return text
        return key
    
    def get_system_prompt(self, join_with: str = "\n") -> str:
        """获取系统提示词（保持中文）"""
        prompts = self._strings[self._lang].get('system_prompt', self._strings['zh']['system_prompt'])
        if isinstance(prompts, list):
            return join_with.join(prompts)
        return prompts if isinstance(prompts, str) else ""
    
    @property
    def lang(self) -> str:
        return self._lang


# 创建全局多语言实例
i18n = I18n()


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
        """获取默认配置文件路径 - 统一到 ~/.aibox/"""
        env_config = os.environ.get("AI_CONFIG_PATH")
        if env_config:
            return env_config
        
        # 统一使用 ~/.aibox/config.json
        return os.path.expanduser("~/.aibox/config.json")
    
    def _get_default_config(self) -> Dict:
        """获取默认配置 - 所有路径都统一到 ~/.aibox/"""
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
                "skills_dir": "~/.aibox/skills"  # 新增技能目录配置
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
                "max_tokens": 8000,
                "max_history_conversations": 5,
                "preserve_system_prompts": True
            },
            "system_prompts": {
                "default": i18n.get_system_prompt()
            },
            "memo": {
                "default_reminder_minutes": 60,
                "max_memos_per_check": 10
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
        """加载配置文件"""
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
        """递归合并配置"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_default_config(self, config_path: str):
        """保存默认配置到文件"""
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._get_default_config(), f, ensure_ascii=False, indent=2)
            print(i18n.get('config_created', config_path))
        except:
            pass
    
    def get(self, key_path: str, default=None):
        """获取配置值，支持点号分隔的路径"""
        keys = key_path.split('.')
        value = self._config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_system_prompt(self, join_with: str = "\n") -> str:
        """获取系统提示词"""
        prompts = self.get("system_prompts.default", [])
        if isinstance(prompts, list):
            return join_with.join(prompts)
        return prompts if isinstance(prompts, str) else ""
    
    def reload(self):
        """重新加载配置"""
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
        """获取技能目录路径"""
        return os.path.expanduser(cls._get_config().get("system.skills_dir", "~/.aibox/skills"))
    
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


# ==================== 备忘录数据库 ====================

class MemoDatabase:
    """备忘录数据库 - 存储和管理备忘录"""
    
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
                    metadata TEXT,
                    repeat_type TEXT DEFAULT 'none',
                    repeat_interval INTEGER DEFAULT 0,
                    repeat_end_time TEXT,
                    last_triggered_at TEXT,
                    trigger_count INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_memos_reminder 
                ON memos(reminder_time) WHERE is_completed = 0
            ''')
            
            conn.commit()
        
        self.logger.info("备忘录表初始化完成")
    
    def add_memo(self, title: str, content: str = None, reminder_time: str = None,
                 tags: List[str] = None, priority: int = 1, created_by: str = None,
                 source: str = None, metadata: Dict = None,
                 repeat_type: str = 'none', repeat_interval: int = 0,
                 repeat_end_time: str = None) -> int:
        """添加备忘录"""
        created_at = datetime.now().strftime(constants.DATETIME_FORMAT)
        tags_str = ",".join(tags) if tags else ""
        metadata_str = json.dumps(metadata, ensure_ascii=False) if metadata else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO memos 
                (title, content, created_at, reminder_time, tags, priority, created_by, 
                 is_completed, source, metadata, repeat_type, repeat_interval, repeat_end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
            ''', (title, content, created_at, reminder_time, tags_str, priority, created_by,
                  source, metadata_str, repeat_type, repeat_interval, repeat_end_time))
            
            memo_id = cursor.lastrowid
            conn.commit()
        
        repeat_info = f" (重复: {repeat_type})" if repeat_type != 'none' else ""
        self.logger.info(f"已添加备忘录: {title}{repeat_info} (ID: {memo_id})")
        return memo_id
    
    def get_memo(self, memo_id: int) -> Optional[Dict]:
        """获取单个备忘录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM memos WHERE id = ?', (memo_id,))
            row = cursor.fetchone()
            
            if row:
                memo = dict(row)
                if memo.get('tags'):
                    memo['tags'] = memo['tags'].split(',')
                if memo.get('metadata'):
                    try:
                        memo['metadata'] = json.loads(memo['metadata'])
                    except:
                        memo['metadata'] = {}
                return memo
        return None
    
    def get_pending_memos(self, limit: int = None, before_time: str = None) -> List[Dict]:
        """获取未完成的备忘录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM memos 
                WHERE (is_completed = 0 OR repeat_type != 'none')
                AND reminder_time IS NOT NULL
            '''
            params = []
            
            if before_time:
                query += ' AND reminder_time <= ?'
                params.append(before_time)
            
            query += ' AND (repeat_end_time IS NULL OR repeat_end_time >= ?)'
            params.append(datetime.now().strftime(constants.DATETIME_FORMAT))
            
            query += ' ORDER BY reminder_time ASC, priority DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
            
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                memo = dict(row)
                if memo.get('tags'):
                    memo['tags'] = memo['tags'].split(',')
                if memo.get('metadata'):
                    try:
                        memo['metadata'] = json.loads(memo['metadata'])
                    except:
                        memo['metadata'] = {}
                results.append(memo)
            
            return results
    
    def get_overdue_memos(self, limit: int = None) -> List[Dict]:
        """获取已过期的备忘录"""
        now = datetime.now().strftime(constants.DATETIME_FORMAT)
        return self.get_pending_memos(limit=limit, before_time=now)
    
    def get_all_memos(self, include_completed: bool = False, limit: int = 50) -> List[Dict]:
        """获取所有备忘录"""
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
                    WHERE is_completed = 0 OR repeat_type != 'none'
                    ORDER BY reminder_time ASC, priority DESC, created_at DESC
                    LIMIT ?
                ''', (limit,))
            
            results = []
            for row in cursor.fetchall():
                memo = dict(row)
                if memo.get('tags'):
                    memo['tags'] = memo['tags'].split(',')
                if memo.get('metadata'):
                    try:
                        memo['metadata'] = json.loads(memo['metadata'])
                    except:
                        memo['metadata'] = {}
                results.append(memo)
            
            return results
    
    def mark_as_triggered(self, memo_id: int) -> Optional[str]:
        """标记备忘录已被触发，并根据重复规则计算下一次提醒时间"""
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
            
            if memo['repeat_type'] != 'none' and not self._should_end_repeat(memo, now):
                next_reminder = self._calculate_next_reminder(memo, now)
                
                if next_reminder:
                    cursor.execute('''
                        UPDATE memos 
                        SET reminder_time = ?
                        WHERE id = ?
                    ''', (next_reminder.strftime(constants.DATETIME_FORMAT), memo_id))
                    
                    self.logger.info(f"备忘录 #{memo_id} 已更新下一次提醒时间: {next_reminder}")
                else:
                    cursor.execute('''
                        UPDATE memos 
                        SET is_completed = 1, completed_at = ?
                        WHERE id = ?
                    ''', (now.strftime(constants.DATETIME_FORMAT), memo_id))
                    
                    self.logger.info(f"备忘录 #{memo_id} 重复结束，已标记为完成")
            else:
                cursor.execute('''
                    UPDATE memos 
                    SET is_completed = 1, completed_at = ?
                    WHERE id = ?
                ''', (now.strftime(constants.DATETIME_FORMAT), memo_id))
                
                self.logger.info(f"备忘录 #{memo_id} 已完成")
            
            conn.commit()
        
        return next_reminder.strftime(constants.DATETIME_FORMAT) if next_reminder else None
    
    def _should_end_repeat(self, memo: Dict, current_time: datetime) -> bool:
        """检查是否应该结束重复提醒"""
        if memo['repeat_end_time']:
            end_time = datetime.strptime(memo['repeat_end_time'], constants.DATETIME_FORMAT)
            if current_time > end_time:
                return True
        return False
    
    def _calculate_next_reminder(self, memo: Dict, current_time: datetime) -> Optional[datetime]:
        """计算下一次提醒时间"""
        current = current_time
        
        if memo['repeat_type'] == 'daily':
            next_time = current + timedelta(days=1)
        elif memo['repeat_type'] == 'weekly':
            next_time = current + timedelta(weeks=1)
        elif memo['repeat_type'] == 'monthly':
            try:
                if current.month == 12:
                    next_time = current.replace(year=current.year + 1, month=1)
                else:
                    next_time = current.replace(month=current.month + 1)
            except ValueError:
                if current.month == 12:
                    next_time = current.replace(year=current.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    next_time = current.replace(month=current.month + 1, day=1) - timedelta(days=1)
        elif memo['repeat_type'] == 'custom' and memo['repeat_interval'] > 0:
            next_time = current + timedelta(days=memo['repeat_interval'])
        else:
            return None
        
        if memo['repeat_end_time']:
            end_time = datetime.strptime(memo['repeat_end_time'], constants.DATETIME_FORMAT)
            if next_time > end_time:
                return None
        
        return next_time
    
    def complete_memo(self, memo_id: int, force_complete: bool = False) -> bool:
        """完成备忘录"""
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
            self.logger.info(f"已完成备忘录 ID: {memo_id}")
            return True
        return False
    
    def get_memo_stats(self) -> Dict:
        """获取备忘录统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM memos')
            total = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM memos WHERE is_completed = 0 OR repeat_type != "none"')
            pending = cursor.fetchone()[0]
            
            now = datetime.now().strftime(constants.DATETIME_FORMAT)
            cursor.execute('''
                SELECT COUNT(*) FROM memos 
                WHERE (is_completed = 0 OR repeat_type != "none")
                AND reminder_time <= ?
            ''', (now,))
            overdue = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM memos WHERE is_completed = 1')
            completed = cursor.fetchone()[0]
            
            return {
                "total": total,
                "pending": pending,
                "overdue": overdue,
                "completed": completed
            }


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
                raw_content = re.sub(r'^\[.*? @ .*?\]\s*', '', content)
                context.append({
                    "role": "assistant",
                    "content": f"[{speaker}] {raw_content}"
                })
            else:
                raw_content = re.sub(r'^\[.*? @ .*?\]\s*', '', content)
                context.append({
                    "role": "user",
                    "content": raw_content
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
            result = self.execute(**kwargs)
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


class ToolRegistry:
    """工具注册器"""
    
    def __init__(self, logger: Optional[Logger] = None):
        self._tools: Dict[str, Tool] = {}
        self.logger = logger or Logger("ToolRegistry")
        self.current_output_queue = None  # 用于流式输出的队列
    
    def register(self, tool: Tool):
        """注册工具"""
        self._tools[tool.get_name()] = tool
        self.logger.info(f"工具已注册: {tool.get_name()}")
    
    def register_many(self, tools: List[Tool]):
        """批量注册工具"""
        for tool in tools:
            self.register(tool)
    
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
            # 检查工具是否支持流式输出且有队列可用
            if hasattr(tool, 'execute_streaming') and self.current_output_queue:
                tool.streaming_output = True
                tool.output_queue = self.current_output_queue  # 设置工具的队列
                
                # 执行流式输出 - 确保参数正确传递
                thread = threading.Thread(
                    target=tool.execute_streaming,
                    args=(self.current_output_queue,),  # output_queue作为位置参数
                    kwargs=kwargs  # 其他参数作为关键字参数
                )
                thread.daemon = True
                thread.start()
                
                # 收集输出
                final_result = None
                collected_lines = []
                
                while thread.is_alive() or not self.current_output_queue.empty():
                    try:
                        msg_type, content = self.current_output_queue.get(timeout=0.1)
                        if msg_type == "line":
                            # 对于命令行工具，直接打印到终端
                            print(content, end="", flush=True)
                            collected_lines.append(content)
                        elif msg_type == "complete":
                            final_result = content
                            collected_lines.append(content)
                    except queue.Empty:
                        continue
                
                thread.join(timeout=5)
                if thread.is_alive():
                    return "❌ 工具执行超时"
                
                result = final_result or "".join(collected_lines)
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


# ==================== 扩展工具类 ====================

class ExtensionTool(Tool):
    """扩展工具类 - 动态加载外部技能"""
    
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
        """执行技能"""
        # 将kwargs转换为JSON字符串
        args_json = json.dumps(kwargs, ensure_ascii=False)
        
        # 执行文件并传入 --execute 和 --args 参数
        cmd = f"{self.skill_path} --execute --args '{args_json}'"
        print('执行扩展工具，参数：',cmd)
        return self._run_skill_command(cmd)
    
    def execute_streaming(self, output_queue: queue.Queue, **kwargs):
        """流式执行技能"""
        args_json = json.dumps(kwargs, ensure_ascii=False)
        cmd = f"{self.skill_path} --execute --args '{args_json}'"
        
        output_queue.put(("line", f"\n🔧 执行扩展技能: {self._name}\n"))
        output_queue.put(("line", "-" * 50 + "\n"))
        
        try:
            # 使用subprocess.Popen实现流式输出
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=os.environ.copy()
            )
            
            output_lines = []
            
            # 实时读取输出
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.rstrip('\n')
                    output_queue.put(("line", line + "\n"))
                    output_lines.append(line)
            
            return_code = process.returncode
            
            output_queue.put(("line", "-" * 50 + "\n"))
            output_queue.put(("line", f"✅ 技能执行完成，返回码: {return_code}\n"))
            
            # 准备完整结果
            full_output = "\n".join(output_lines)
            result = self.format_result(return_code == 0, "技能执行完成", {"输出": full_output})
            output_queue.put(("complete", result))
            
        except Exception as e:
            output_queue.put(("line", f"❌ 技能执行错误: {str(e)}\n"))
            output_queue.put(("complete", f"❌ 技能执行错误: {str(e)}"))


# ==================== 备忘录工具 ====================

class MemoTool(Tool):
    """备忘录工具 - 用于管理备忘录"""
    
    def __init__(self, memo_db: MemoDatabase, logger: Optional[Logger] = None):
        super().__init__(logger)
        self.memo_db = memo_db
    
    def get_name(self) -> str:
        return "memo"
    
    def get_description(self) -> str:
        return """备忘录管理工具 - 创建、查看、完成和删除备忘录
支持：创建提醒（支持重复提醒）、查看待办、标记完成、删除备忘录、搜索备忘录"""
    
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
                    "description": "备忘录标题（用于add操作）"
                },
                "content": {
                    "type": "string",
                    "description": "备忘录内容（可选，用于add操作）"
                },
                "reminder_time": {
                    "type": "string",
                    "description": "提醒时间（格式：YYYY-MM-DD HH:MM:SS，或相对时间如 '+1h', '+30m', 'tomorrow 9am'）"
                },
                "reminder_minutes": {
                    "type": "integer",
                    "description": "提醒分钟数（从现在开始，用于快速设置提醒）"
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
                    "description": "重复类型",
                    "enum": ["none", "daily", "weekly", "monthly", "custom"],
                    "default": "none"
                },
                "repeat_interval": {
                    "type": "integer",
                    "description": "自定义重复间隔（天），当repeat_type='custom'时使用",
                    "default": 0
                },
                "repeat_end_time": {
                    "type": "string",
                    "description": "重复结束时间，None表示永久重复"
                },
                "memo_id": {
                    "type": "integer",
                    "description": "备忘录ID（用于get、complete、delete操作）"
                },
                "memo_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "备忘录ID列表（用于批量删除）"
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
                    "description": "是否包含已完成的备忘录（默认False）",
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
                match = re.match(r'\+(\d+)([hmd])', reminder_input)
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
            return f"❌ 备忘录操作错误: {str(e)}"
    
    def _add_memo(self, kwargs: Dict) -> str:
        """添加备忘录"""
        title = kwargs.get("title")
        if not title:
            return "❌ 需要提供备忘录标题"
        
        content = kwargs.get("content")
        reminder_minutes = kwargs.get("reminder_minutes")
        reminder_time_input = kwargs.get("reminder_time")
        tags = kwargs.get("tags", [])
        priority = kwargs.get("priority", 1)
        repeat_type = kwargs.get("repeat_type", "none")
        repeat_interval = kwargs.get("repeat_interval", 0)
        repeat_end_time = kwargs.get("repeat_end_time")
        
        if repeat_type not in ["none", "daily", "weekly", "monthly", "custom"]:
            return f"❌ 无效的重复类型: {repeat_type}"
        
        if repeat_type == "custom" and repeat_interval <= 0:
            return "❌ 自定义重复需要设置有效的 repeat_interval (>0)"
        
        reminder_time = None
        if reminder_minutes:
            reminder_time = self._parse_reminder_time(reminder_minutes)
        elif reminder_time_input:
            reminder_time = self._parse_reminder_time(reminder_time_input)
        
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
            repeat_end_time=repeat_end_time
        )
        
        data = {
            "备忘录ID": memo_id,
            "标题": title,
        }
        
        if reminder_time:
            data["提醒时间"] = reminder_time
        
        if repeat_type != "none":
            repeat_info = f"重复类型: {repeat_type}"
            if repeat_type == "custom":
                repeat_info += f" (每{repeat_interval}天)"
            if repeat_end_time:
                repeat_info += f", 结束于: {repeat_end_time}"
            else:
                repeat_info += ", 永久重复"
            data["重复信息"] = repeat_info
        
        return self.format_result(True, "备忘录已创建", data)
    
    def _list_memos(self, kwargs: Dict) -> str:
        """列出备忘录"""
        include_completed = kwargs.get("include_completed", False)
        limit = kwargs.get("limit", 20)
        
        memos = self.memo_db.get_all_memos(include_completed, limit)
        
        if not memos:
            return "📭 没有找到备忘录"
        
        status = "所有" if include_completed else "待办"
        output = [f"📋 {status}备忘录 (共 {len(memos)} 条):"]
        
        now = datetime.now()
        
        for i, memo in enumerate(memos, 1):
            status_icon = "✅" if memo['is_completed'] else "⏰"
            priority_icon = "🔴" * memo['priority']
            source_tag = f"[{memo.get('source', '未知')}]" if memo.get('source') else ""
            
            repeat_tag = ""
            if memo['repeat_type'] != 'none':
                repeat_map = {
                    'daily': '📅每日',
                    'weekly': '📅每周',
                    'monthly': '📅每月',
                    'custom': f'📅每{memo["repeat_interval"]}天'
                }
                repeat_tag = f" [{repeat_map.get(memo['repeat_type'], '重复')}]"
            
            output.append(f"\n{i}. {status_icon} [ID: {memo['id']}] {source_tag}{repeat_tag} {memo['title']} {priority_icon}")
            
            if memo['reminder_time']:
                try:
                    reminder = datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT)
                    if not memo['is_completed'] and reminder < now:
                        output.append(f"   ⚠️ 已过期: {memo['reminder_time']}")
                    else:
                        output.append(f"   ⏱️ 提醒: {memo['reminder_time']}")
                except:
                    output.append(f"   ⏱️ 提醒: {memo['reminder_time']}")
            
            if memo.get('trigger_count', 0) > 0:
                output.append(f"   🔄 已提醒 {memo['trigger_count']} 次")
            
            if memo['content']:
                preview = memo['content'][:100] + "..." if len(memo['content']) > 100 else memo['content']
                output.append(f"   📝 {preview}")
            
            if memo['tags']:
                output.append(f"   🏷️ {', '.join(memo['tags'])}")
        
        return "\n".join(output)
    
    def _get_memo(self, kwargs: Dict) -> str:
        """获取单个备忘录"""
        memo_id = kwargs.get("memo_id")
        if not memo_id:
            return "❌ 需要提供备忘录ID"
        
        memo = self.memo_db.get_memo(memo_id)
        if not memo:
            return f"❌ 未找到ID为 {memo_id} 的备忘录"
        
        status = "✅ 已完成" if memo['is_completed'] else "⏰ 待处理"
        if memo['is_completed']:
            status += f" (完成于: {memo['completed_at']})"
        
        output = [
            f"📌 备忘录 #{memo_id}",
            f"📋 状态: {status}",
            f"📝 标题: {memo['title']}",
        ]
        
        if memo.get('source'):
            output.append(f"📎 来源: {memo['source']}")
        
        if memo.get('metadata'):
            output.append(f"📎 元数据: {memo['metadata']}")
        
        if memo['repeat_type'] != 'none':
            repeat_info = f"🔄 重复类型: {memo['repeat_type']}"
            if memo['repeat_type'] == 'custom':
                repeat_info += f" (每{memo['repeat_interval']}天)"
            if memo['repeat_end_time']:
                repeat_info += f", 结束于: {memo['repeat_end_time']}"
            else:
                repeat_info += ", 永久重复"
            output.append(repeat_info)
            
            if memo.get('trigger_count', 0) > 0:
                output.append(f"   📊 已触发 {memo['trigger_count']} 次")
            if memo.get('last_triggered_at'):
                output.append(f"   ⏱️ 上次触发: {memo['last_triggered_at']}")
        
        if memo['content']:
            output.append(f"📄 内容:\n{memo['content']}")
        
        if memo['reminder_time']:
            try:
                now = datetime.now()
                reminder = datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT)
                if not memo['is_completed'] and reminder < now:
                    output.append(f"⚠️ 提醒时间 (已过期): {memo['reminder_time']}")
                else:
                    output.append(f"⏰ 提醒时间: {memo['reminder_time']}")
            except:
                output.append(f"⏰ 提醒时间: {memo['reminder_time']}")
        
        if memo['tags']:
            output.append(f"🏷️ 标签: {', '.join(memo['tags'])}")
        
        output.append(f"🔢 优先级: {'🔴' * memo['priority']} ({memo['priority']}/5)")
        output.append(f"📅 创建时间: {memo['created_at']}")
        output.append(f"👤 创建者: {memo['created_by'] or '系统'}")
        
        return "\n".join(output)
    
    def _complete_memo(self, kwargs: Dict) -> str:
        """完成备忘录"""
        memo_id = kwargs.get("memo_id")
        if not memo_id:
            return "❌ 需要提供备忘录ID"
        
        force_complete = kwargs.get("force_complete", False)
        
        memo = self.memo_db.get_memo(memo_id)
        if not memo:
            return f"❌ 未找到ID为 {memo_id} 的备忘录"
        
        if memo['is_completed'] and not force_complete:
            return f"ℹ️ 备忘录 #{memo_id} 已经完成了"
        
        if self.memo_db.complete_memo(memo_id, force_complete):
            memo = self.memo_db.get_memo(memo_id)
            data = {
                "备忘录ID": memo_id,
                "标题": memo['title']
            }
            
            if memo['repeat_type'] != 'none' and not memo['is_completed']:
                data["下一次提醒"] = memo['reminder_time']
                data["已触发次数"] = memo.get('trigger_count', 0)
                return self.format_result(True, "备忘录已处理，已更新下一次提醒时间", data)
            else:
                return self.format_result(True, "备忘录已完成", data)
        else:
            return f"❌ 无法完成备忘录 #{memo_id}"
    
    def _delete_memo(self, kwargs: Dict) -> str:
        """删除备忘录"""
        confirm = kwargs.get("confirm", False)
        if not confirm:
            return "❌ 需要设置 confirm=True 来确认删除操作"
        
        memo_id = kwargs.get("memo_id")
        if memo_id:
            if self.memo_db.complete_memo(memo_id, force_complete=True):
                return self.format_result(True, f"备忘录 #{memo_id} 已删除")
            else:
                return f"❌ 无法删除备忘录 #{memo_id}"
        else:
            return "❌ 需要提供 memo_id"
    
    def _search_memos(self, kwargs: Dict) -> str:
        """搜索备忘录"""
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
            return f"❌ 未找到包含 '{keyword}' 的备忘录"
        
        output = [f"🔍 搜索 '{keyword}' 找到 {len(results)} 条备忘录:"]
        now = datetime.now()
        
        for i, memo in enumerate(results[:limit], 1):
            status_icon = "✅" if memo['is_completed'] else "⏰"
            output.append(f"\n{i}. {status_icon} [ID: {memo['id']}] {memo['title']}")
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
        """获取备忘录统计信息"""
        stats = self.memo_db.get_memo_stats()
        
        output = [
            "📊 备忘录统计",
            f"  总备忘录: {stats['total']} 条",
            f"  待处理: {stats['pending']} 条",
            f"  已过期: {stats['overdue']} 条",
            f"  已完成: {stats['completed']} 条"
        ]
        
        if stats['overdue'] > 0:
            output.append(f"\n⚠️ 有 {stats['overdue']} 条备忘录已过期，请及时处理")
        
        return "\n".join(output)


# ==================== 记忆工具 ====================

class MemoryTool(Tool):
    """记忆工具 - 用于存储、检索和删除对话记忆"""
    
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


# ==================== 网页工具 ====================

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
    """简化版网页爬虫工具"""
    
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


# ==================== 文件操作工具 ====================

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
    """读取文件内容工具"""
    
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


class WriteFileTool(FileToolBase):
    """写入文件工具"""
    
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


class ListFilesTool(FileToolBase):
    """列出目录内容工具"""
    
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


# ==================== 系统工具 ====================

class GetCurrentTimeTool(Tool):
    """获取当前时间工具"""
    
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


class CalculatorTool(Tool):
    """计算器工具"""
    
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


class CommandLineTool(Tool):
    """命令行执行工具 - 使用抽象的命令执行器"""
    
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
        # 从kwargs中提取参数，避免重复传递
        command = kwargs.get("command")
        timeout = kwargs.get("timeout", 30)
        
        if not command:
            output_queue.put(("line", "❌ 错误：缺少命令参数\n"))
            output_queue.put(("complete", "❌ 错误：缺少命令参数"))
            return
        
        # 使用执行器的流式执行方法，只传递需要的参数
        # 注意：不要在这里传递command参数，因为它已经在kwargs中
        self.executor.execute_streaming(
            command=command,  # 显式指定command参数
            output_queue=output_queue,  # 显式指定output_queue参数
            timeout=timeout,  # 显式指定timeout参数
            **{k: v for k, v in kwargs.items() if k not in ['command', 'timeout', 'stream']}  # 传递其他参数，排除已处理的
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


class SaveMemoryAndEndConversationTool(Tool):
    """保存记忆并结束对话工具"""
    
    def __init__(self, exit_callback: Callable, memory_db: MemoryDatabase, logger: Optional[Logger] = None):
        super().__init__(logger)
        self.exit_callback = exit_callback
        self.memory_db = memory_db
    
    def get_name(self) -> str:
        return "save_memory_and_end_conversation"
    
    def get_description(self) -> str:
        return """保存记忆并结束当前对话 - 必须提供详细的对话总结！
使用此工具时，AI会：
1. 将本次对话的重要内容保存到记忆库
2. 提供完整的对话总结
3. 礼貌地结束对话"""
    
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
                }
            },
            "required": ["summary"]
        }
    
    def execute(self, summary: str = None, topic: str = None, reason: str = "话题讨论完成", **kwargs) -> str:
        if summary is None or len(summary) < 50:
            return "❌ 请提供更详细的对话总结（至少50字），以便保存到记忆库"
        
        self.logger.info(f"AI保存记忆并结束对话: {reason}")
        
        # 保存到记忆库
        if self.memory_db and topic:
            memory_id = self.memory_db.add_memory(
                topic=topic,
                summary=summary,
                importance=3  # 提高重要性，因为是对话总结
            )
            self.logger.info(f"对话记忆已保存，ID: {memory_id}")
        
        if self.exit_callback:
            self.exit_callback(reason, summary)
        
        return self.format_result(True, "对话记忆已保存，对话结束", {
            "原因": reason,
            "总结预览": summary[:100] + "..." if len(summary) > 100 else summary,
            "记忆已保存": True
        })


# ==================== AI聊天类 ====================

class DeepSeekChat:
    """单AI聊天类"""
    
    def __init__(self, api_key: str = None, max_history: int = None,
                 system_prompt: str = None, debug_level: int = None, exit_callback: Callable = None,
                 history_manager: ConversationHistory = None, memory_db: MemoryDatabase = None,
                 memo_db: MemoDatabase = None, command_executor: CommandExecutor = None):
        self.name = "DeepSeek"
        self.debug_level = debug_level if debug_level is not None else Logger("").level
        self.logger = Logger(self.name, self.debug_level)
        self.config = ConfigManager()
        self.history_manager = history_manager
        self.memory_db = memory_db
        self.memo_db = memo_db
        self.history_loaded = False
        self.conversation_active = True
        self.messages = []
        
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
        """初始化系统提示词"""
        if system_prompt:
            self._add_message("system", system_prompt)
        else:
            prompts = self.config.get("system_prompts.default", [])
            if prompts:
                if isinstance(prompts, list):
                    for prompt in prompts:
                        if prompt.strip():
                            self._add_message("system", prompt)
                else:
                    self._add_message("system", str(prompts))
            else:
                self._add_message("system", "你是一个智能AI助手。")
    
    def _register_tools(self, exit_callback: Callable = None, command_executor: CommandExecutor = None):
        tools = [
            GetCurrentTimeTool(self.logger),
            CalculatorTool(self.logger),
            CommandLineTool(command_executor or SubprocessCommandExecutor(self.logger), self.logger),
            ReadFileTool(self.logger),
            WriteFileTool(self.logger),
            ListFilesTool(self.logger),
            SimpleWebCrawlerTool(self.logger),
        ]
        
        if self.memory_db:
            tools.append(MemoryTool(self.memory_db, self.logger))
        
        if self.memo_db:
            tools.append(MemoTool(self.memo_db, self.logger))
        
        if exit_callback and self.memory_db:
            tools.append(SaveMemoryAndEndConversationTool(exit_callback, self.memory_db, self.logger))
        
        # 加载扩展技能（工具）
        skills_dir = constants.SKILLS_DIR
        if os.path.exists(skills_dir):
            # 获取所有技能文件（排除以_开头的文件）
            skills_list = [f for f in os.listdir(skills_dir) 
                          if os.path.isfile(os.path.join(skills_dir, f)) 
                          and not f.startswith("_")
                          #and f.endswith('.py')
                          ]  # 只考虑Python文件作为技能
            
            for skill_file in skills_list:
                try:
                    # 为每个技能文件创建扩展工具
                    extool = ExtensionTool(skill_file, self.logger)
                    tools.append(extool)
                    self.logger.info(f"已加载扩展技能: {extool.get_name()}")
                except Exception as e:
                    self.logger.error(f"加载技能 {skill_file} 失败: {e}")
    
        self.tool_registry.register_many(tools)
        self.logger.info(f"已注册 {len(tools)} 个工具")
    
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
        """添加消息到历史"""
        timestamp = datetime.now().strftime(constants.DATETIME_FORMAT)
        
        if role == "assistant":
            formatted_content = f"[{self.name} @ {timestamp}] {content}"
        elif role == "user":
            formatted_content = content
        else:
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
    
    def _handle_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
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
            
            # 对于命令行工具，检查是否需要流式输出
            if tool_name == "run_command" and args.get("stream", True):
                print(i18n.get('command_output_title'))
                
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
                            print(content, end="", flush=True)
                            result_lines.append(content)
                        elif msg_type == "complete":
                            result = content
                            result_lines.append(content)
                    except queue.Empty:
                        continue
                
                result = "".join(result_lines)
                print(i18n.get('command_output_end'))
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
                return tool_messages
            
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
    
    def think_and_respond(self, input_text: str) -> Optional[str]:
        """思考并回应"""
        if not self.conversation_active:
            self.logger.info("对话已结束，重置状态")
            self.conversation_active = True
            if self.preserve_system:
                system_messages = [msg for msg in self.messages if msg["role"] == "system"]
                self.messages = system_messages
            else:
                self.messages = []
            self.logger.info("对话状态已重置")
        
        self.stats["api_calls"] += 1
        self._add_message("user", input_text)
        
        if self.history_manager:
            self.history_manager.add_message("user", input_text, "用户")
        
        # 在调用API之前，先检查是否应该搜索记忆
        memory_search_needed = self._should_search_memory(input_text)
        memory_results = None
        
        if memory_search_needed and self.memory_db:
            self.logger.info(i18n.get('memory_check'))
            # 从用户输入中提取关键词进行搜索
            keywords = [word for word in input_text.split() if len(word) > 1][:3]
            if keywords:
                memory_results = self.memory_db.search_memories(keywords, limit=3)
                if memory_results:
                    self.logger.info(i18n.get('memory_found', len(memory_results)))
        
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
        
        # 添加记忆上下文（如果有）
        if memory_results:
            memory_context = "根据记忆库，以下是与当前话题相关的历史记录：\n\n"
            for mem in memory_results:
                memory_context += f"- [{mem['topic']}] {mem['summary']}\n"
            enhanced_messages.append({"role": "system", "content": memory_context})
        
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
        print(f"\n{i18n.get('thinking', current_time)}")
        print(i18n.get('assistant_prefix'), end="", flush=True)
        
        full_response = ""
        tool_calls_buffer = []
        current_tool_calls = {}
        
        try:
            response = requests.post(
                constants.DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=constants.DEFAULT_TIMEOUT,
                stream=True
            )
            
            if response.status_code != 200:
                print(f"\n错误状态码: {response.status_code}")
                print(f"错误响应: {response.text}")
                response.raise_for_status()
            
            # 处理流式响应
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # 去掉 'data: ' 前缀
                        if data == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data)
                            choices = chunk.get('choices', [])
                            if not choices:
                                continue
                            
                            delta = choices[0].get('delta', {})
                            
                            # 处理内容
                            if 'content' in delta and delta['content']:
                                content = delta['content']
                                print(content, end="", flush=True)
                                full_response += content
                            
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
            
            print()  # 换行
            
            # 处理收集到的工具调用
            if current_tool_calls:
                tool_calls_buffer = list(current_tool_calls.values())
                print(i18n.get('calling_tools'))
                
                assistant_msg = {
                    "role": "assistant",
                    "content": full_response if full_response else None,
                    "tool_calls": tool_calls_buffer
                }
                self.messages.append(assistant_msg)
                
                tool_responses = self._handle_tool_calls(tool_calls_buffer)
                
                if not self.conversation_active:
                    self.logger.info("对话已结束，停止响应")
                    return None
                
                if tool_responses:
                    self.messages.extend(tool_responses)
                
                print(i18n.get('analyzing_tool_results'))
                return self.think_and_respond("（请基于工具结果继续回答）")
            
            elif full_response:
                self._add_message("assistant", full_response)
                if self.history_manager:
                    self.history_manager.add_message("assistant", full_response, self.name)
            
            return full_response
                
        except requests.exceptions.RequestException as e:
            error_msg = f"\n{i18n.get('error_prefix')}API请求失败: {str(e)}"
            print(error_msg)
            self.stats["errors"].append(str(e))
            return error_msg
        except json.JSONDecodeError as e:
            error_msg = f"\n{i18n.get('error_prefix')}API响应解析失败: {str(e)}"
            print(error_msg)
            self.stats["errors"].append(str(e))
            return error_msg
        except Exception as e:
            error_msg = f"\n{i18n.get('error_prefix')}{str(e)}"
            print(error_msg)
            self.stats["errors"].append(str(e))
            return error_msg
    
    def _process_tool_call_chunk(self, tool_calls: List[Dict], buffer: List[Dict]):
        """处理工具调用块"""
        for tc in tool_calls:
            index = tc.get("index", 0)
            
            while len(buffer) <= index:
                buffer.append({
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""}
                })
            
            if "id" in tc:
                buffer[index]["id"] = tc["id"]
            if "function" in tc:
                if "name" in tc["function"]:
                    buffer[index]["function"]["name"] = tc["function"]["name"]
                if "arguments" in tc["function"]:
                    buffer[index]["function"]["arguments"] += tc["function"]["arguments"]
    
    def reset_conversation(self):
        """重置对话状态"""
        self.conversation_active = True
        if self.preserve_system:
            system_messages = [msg for msg in self.messages if msg["role"] == "system"]
            self.messages = system_messages
        else:
            self.messages = []
        self.logger.info("对话已重置，可以继续提问")


# ==================== 对话管理器 ====================

class SingleAIDialogueManager:
    """单AI对话管理器 - 与用户直接对话"""
    
    def __init__(self, debug_level: int = None, load_history: bool = None, command_executor: CommandExecutor = None):
        self.ai: Optional[DeepSeekChat] = None
        self.dialogue_history: List[Dict] = []
        self.config = ConfigManager()
        self.command_executor = command_executor or SubprocessCommandExecutor()
        
        if debug_level is None:
            debug_level = self.config.get("system.debug_level", 1)
        
        self.logger = Logger("Manager", debug_level)
        self.running = True
        
        # 确保 ~/.aibox 目录存在
        os.makedirs(constants.SAVE_DIR, exist_ok=True)
        
        self.memory_db = MemoryDatabase()
        self.memo_db = MemoDatabase()
        self.history_manager = ConversationHistory(memory_db=self.memory_db, load_history=load_history)
        
        self.dialogue_in_progress = False
    
    def global_exit_handler(self, reason: str, summary: str):
        """对话结束处理器"""
        self.logger.info(f"对话结束 - 原因: {reason}")
        
        self.history_manager.end_current_conversation(summary)
        
        if self.ai:
            self.ai.reset_conversation()
            self.ai.conversation_active = True
        
        self.dialogue_in_progress = False
        self.logger.info("对话状态已重置，可以开始新对话")
    
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
            command_executor=self.command_executor
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
        
        config_path = self.config._config_path
        if os.path.exists(config_path):
            print(i18n.get('config_file', config_path))
        
        memo_stats = self.memo_db.get_memo_stats()
        if memo_stats['total'] > 0:
            print(f"\n{i18n.get('memo_stats')}")
            print(i18n.get('total_memos', memo_stats['total']))
            print(i18n.get('pending_memos', memo_stats['pending']))
            if memo_stats['overdue'] > 0:
                print(i18n.get('overdue_memos', memo_stats['overdue']))
            print(i18n.get('completed_memos', memo_stats['completed']))
        
        # 显示已加载的技能
        skills_dir = constants.SKILLS_DIR
        if os.path.exists(skills_dir):
            skills = [f for f in os.listdir(skills_dir) 
                     if os.path.isfile(os.path.join(skills_dir, f)) 
                     and not f.startswith("_") 
                     #and f.endswith('.py')
                     ]
            if skills:
                print(i18n.get('loaded_skills', len(skills)))
                for skill in skills[:5]:
                    print(i18n.get('skill_item', os.path.splitext(skill)[0]))
                if len(skills) > 5:
                    print(i18n.get('more_skills', len(skills)-5))
        
        print(f"\n{i18n.get('available_commands')}")
        print(i18n.get('cmd_exit'))
        print(i18n.get('cmd_new'))
        print(i18n.get('cmd_list'))
        print(i18n.get('cmd_memories'))
        print(i18n.get('cmd_memos'))
        print(i18n.get('cmd_search'))
        print(i18n.get('cmd_config'))
        print(i18n.get('cmd_reload'))
        print(i18n.get('cmd_check'))
        print(i18n.get('cmd_help'))
        
        print(f"\n{i18n.get('features_title')}")
        print(i18n.get('feature_data_dir'))
        print(i18n.get('feature_memory_check'))
        print(i18n.get('feature_memory_save'))
        print(i18n.get('feature_command_full'))
        print(i18n.get('feature_command_stream'))
        print(i18n.get('feature_skills'))
        print(i18n.get('feature_skills_interface'))
    
    def process_command(self, cmd: str) -> bool:
        """处理命令，返回True表示应该继续，False表示应该退出"""
        cmd = cmd.lower().strip()
        
        if cmd == '/exit':
            print(i18n.get('goodbye'))
            self.history_manager.end_current_conversation()
            return False
        
        elif cmd == '/new':
            print(i18n.get('new_conversation'))
            self.history_manager.archive_current_conversation()
            if self.ai:
                self.ai.reset_conversation()
            return True
        
        elif cmd == '/list':
            conversations = self.history_manager.list_conversations()
            print(f"\n{i18n.get('saved_conversations')}")
            for conv in conversations:
                status = i18n.get('conv_status_current') if conv.get('is_current') else i18n.get('conv_status_archived')
                print(f"  {conv['file']} - {conv['topic']} [{status}] ({conv['start_time']})")
            return True
        
        elif cmd == '/memories':
            memories = self.memory_db.get_recent_memories(10)
            print(f"\n{i18n.get('recent_memories')}")
            for mem in memories:
                print(f"  [ID: {mem['id']}] {mem['topic']} - {mem['summary'][:50]}...")
            return True
        
        elif cmd == '/memos':
            memos = self.memo_db.get_all_memos(include_completed=False)
            print(f"\n{i18n.get('pending_memos_title')}")
            for memo in memos:
                status = i18n.get('memo_overdue') if memo['reminder_time'] and datetime.strptime(memo['reminder_time'], constants.DATETIME_FORMAT) < datetime.now() else i18n.get('memo_pending')
                print(f"  {status} [ID: {memo['id']}] {memo['title']} - {memo.get('reminder_time', '无提醒')}")
            return True
        
        elif cmd.startswith('/search '):
            query = cmd[8:].strip()
            results = self.memory_db.search_memories([query])
            print(i18n.get('search_results', query, len(results)))
            for mem in results:
                print(f"  [ID: {mem['id']}] {mem['topic']} - {mem['summary'][:100]}...")
            return True
        
        elif cmd == '/config':
            print(f"\n{i18n.get('current_config')}")
            print(i18n.get('config_debug', self.config.get('system.debug_level')))
            print(i18n.get('config_data_dir', constants.SAVE_DIR))
            print(i18n.get('config_skills_dir', constants.SKILLS_DIR))
            print(i18n.get('config_commands', i18n.get('enabled') if constants.COMMANDS_ENABLED else i18n.get('disabled')))
            print(i18n.get('config_history', i18n.get('enabled') if self.history_manager.load_history else i18n.get('disabled')))
            print(i18n.get('config_executor', type(self.command_executor).__name__))
            return True
        
        elif cmd == '/reload':
            self.config.reload()
            print(i18n.get('config_reloaded'))
            return True
        
        elif cmd == '/check':
            print(i18n.get('checking_memos'))
            overdue = self.memo_db.get_overdue_memos()
            if overdue:
                print(i18n.get('overdue_found', len(overdue)))
                for memo in overdue:
                    print(f"  • [ID: {memo['id']}] {memo['title']} - {memo['reminder_time']}")
            else:
                print(i18n.get('no_overdue'))
            return True
        
        elif cmd == '/help':
            print(f"\n{i18n.get('available_commands')}")
            print(i18n.get('cmd_exit'))
            print(i18n.get('cmd_new'))
            print(i18n.get('cmd_list'))
            print(i18n.get('cmd_memories'))
            print(i18n.get('cmd_memos'))
            print(i18n.get('cmd_search'))
            print(i18n.get('cmd_config'))
            print(i18n.get('cmd_reload'))
            print(i18n.get('cmd_check'))
            print(i18n.get('cmd_help'))
            
            print(f"\n{i18n.get('memo_tool_usage')}")
            print(i18n.get('memo_usage_in_dialogue'))
            print(i18n.get('memo_add_example'))
            print(i18n.get('memo_list_example'))
            print(i18n.get('memo_complete_example'))
            
            print(f"\n{i18n.get('memory_habit')}")
            print(i18n.get('memory_habit_desc'))
            print(i18n.get('memory_save_desc'))
            
            print(f"\n{i18n.get('command_stream')}")
            print(i18n.get('command_stream_desc'))
            print(i18n.get('command_stream_disable'))
            
            print(f"\n{i18n.get('skills_extension')}")
            print(i18n.get('skills_desc'))
            print(i18n.get('skills_interface_desc'))
            return True
        
        return None  # 不是命令
    
    def run(self):
        """运行对话循环"""
        self.add_ai()
        self.show_welcome_message()
        
        # 检查过期备忘录
        overdue = self.memo_db.get_overdue_memos()
        if overdue:
            print(f"\n⏰ {i18n.get('overdue_found', len(overdue))}")
            for memo in overdue[:5]:
                print(f"  • [ID: {memo['id']}] {memo['title']} - {memo['reminder_time']}")
            if len(overdue) > 5:
                print(f"  ... {i18n.get('more_skills', len(overdue)-5)}")
            print("  可以使用 /memos 查看所有备忘录")
        
        while True:
            try:
                print("\n" + "-"*50)
                user_input = input(i18n.get('input_prompt')).strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if user_input.startswith('/'):
                    result = self.process_command(user_input)
                    if result is False:  # 退出
                        break
                    continue
                
                # 处理普通对话
                if self.ai:
                    self.ai.reset_conversation()
                
                self.dialogue_in_progress = True
                self.history_manager.start_new_conversation(user_input[:50] + "...")
                
                print("\n" + "="*70)
                print(i18n.get('conversation_start'))
                print("="*70)
                
                current_response = user_input
                turn_count = 0
                
                try:
                    while self.dialogue_in_progress:
                        turn_count += 1
                        
                        response = self.ai.think_and_respond(current_response)
                        
                        if response is None or not self.dialogue_in_progress:
                            print(f"\n{i18n.get('conversation_ended')}")
                            break
                        
                        self.dialogue_history.append({
                            "timestamp": datetime.now().strftime(constants.DATETIME_FORMAT),
                            "turn": turn_count,
                            "speaker": "AI",
                            "response": response[:100] + "..." if len(response) > 100 else response
                        })
                        
                        current_response = """你好，我是你心里的回声，你仔细地想想是不是完成任务了，还有什么事情要做。
                        备忘录里还有什么事情吗？如果没有就结束对话吧。"""
                        
                        time.sleep(1)
                finally:
                    self.history_manager.end_current_conversation()
                    self.dialogue_in_progress = False
                    print(i18n.get('conversation_stats', turn_count))
                
            except KeyboardInterrupt:
                print(f"\n\n{i18n.get('user_interrupted')}")
                self.history_manager.end_current_conversation()
                break
            except Exception as e:
                print(f"\n{i18n.get('error_prefix')}{e}")
                import traceback
                traceback.print_exc()


# ==================== 命令行参数处理 ====================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='单AI智能体系统 - 与用户直接对话')
    
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    
    parser.add_argument('--check-memo', action='store_true', help='立即检查到期备忘录并退出')
    
    parser.add_argument('--memo-add', type=str, help='添加备忘录，格式: "标题|内容|提醒时间"')
    parser.add_argument('--memo-list', action='store_true', help='列出备忘录')
    parser.add_argument('--memo-complete', type=int, help='完成指定ID的备忘录')
    
    parser.add_argument('--start', type=str, help='开始新对话，指定初始消息')
    
    parser.add_argument('-d', '--debug', type=int, choices=[0, 1, 2, 3], default=None, help='调试级别')
    parser.add_argument('-c', '--config', type=str, help='指定配置文件路径')
    
    # 添加语言选项
    parser.add_argument('--lang', type=str, choices=['zh', 'en'], help='强制指定语言 (zh/en)')
    
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
                print(f"  • [ID: {memo['id']}] {memo['title']} (提醒: {memo['reminder_time']})")
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
                print(f"  [ID: {memo['id']}] {memo['title']}{overdue}")
        return True
    
    if args.memo_add:
        try:
            parts = args.memo_add.split('|')
            title = parts[0]
            content = parts[1] if len(parts) > 1 else ""
            reminder = parts[2] if len(parts) > 2 else None
            
            memo_id = manager.memo_db.add_memo(
                title=title,
                content=content,
                reminder_time=reminder,
                created_by="cli",
                source="cli"
            )
            print(i18n.get('memo_added', memo_id))
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


def handle_dialogue_commands(manager):
    """处理对话命令"""
    args = parse_args()
    
    if args.start:
        manager.add_ai()
        print(i18n.get('new_dialogue_start', args.start))
        # 这里可以实现 start_dialogue 方法
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
    
    # 确保 ~/.aibox 目录存在
    os.makedirs(constants.SAVE_DIR, exist_ok=True)
    
    # 确保 skills 目录存在
    os.makedirs(constants.SKILLS_DIR, exist_ok=True)
    
    Logger.init_file_logging()
    
    # 创建命令执行器 - 现在只使用本地执行器
    command_executor = SubprocessCommandExecutor()
    
    manager = SingleAIDialogueManager(
        debug_level=args.debug,
        command_executor=command_executor
    )
    
    if handle_check_commands(manager):
        return
    
    if handle_memo_commands(manager):
        return
    
    if handle_dialogue_commands(manager):
        return
    
    # 正常运行交互式对话
    manager.run()


if __name__ == "__main__":
    main()