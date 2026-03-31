#!/usr/bin/env python3
"""
扩展技能：Moonshot Kimi K2.5 大模型文本压缩工具
用于对话压缩、文本摘要、内容总结等任务
放置在 ~/.aibox/skills/moonshot_compressor.py
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime


class MoonshotCompressor:
    """Moonshot Kimi K2.5 压缩工具"""
    
    def __init__(self):
        self.api_key = self._get_api_key()
        self.base_url = "https://api.moonshot.cn/v1/chat/completions"
        self.timeout = 60
    
    def _get_api_key(self) -> str:
        """获取 API Key"""
        # 优先从环境变量获取
        api_key = os.environ.get("MOONSHOT_API_KEY")
        if api_key:
            return api_key
        
        # 从配置文件读取
        key_path = os.path.expanduser("~/.cert/moonshot.key")
        try:
            if os.path.exists(key_path):
                with open(key_path, "r") as f:
                    return f.read().strip()
        except Exception:
            pass
        
        return None
    
    def _read_file(self, filepath: str) -> tuple:
        """读取文件内容，返回 (成功标志, 内容或错误信息)"""
        try:
            abs_path = os.path.abspath(os.path.expanduser(filepath))
            
            if not os.path.exists(abs_path):
                return False, f"文件不存在: {abs_path}"
            
            if not os.path.isfile(abs_path):
                return False, f"路径不是文件: {abs_path}"
            
            # 检查文件大小（限制最大100MB）
            file_size = os.path.getsize(abs_path)
            if file_size > 100 * 1024 * 1024:
                return False, f"文件过大 ({file_size/1024/1024:.1f}MB)，超过100MB限制"
            
            # 尝试读取文件
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            content = None
            for encoding in encodings:
                try:
                    with open(abs_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                return False, f"无法解码文件，请检查文件编码"
            
            return True, content
            
        except Exception as e:
            return False, f"读取文件失败: {str(e)}"
    
    def _call_api(self, messages, max_tokens=800, temperature=1) -> str:
        """调用 Moonshot API"""
        if not self.api_key:
            return "❌ 错误：无法获取 Moonshot API Key"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "kimi-k2.5",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return f"❌ API 调用失败: HTTP {response.status_code}，内容：{response.text}"
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            return content
            
        except requests.exceptions.Timeout:
            return "❌ API 调用超时"
        except requests.exceptions.RequestException as e:
            return f"❌ API 请求失败: {str(e)}"
        except Exception as e:
            return f"❌ 调用错误: {str(e)}"
    
    def compress_file(self, filepath: str, max_length: int = 500, 
                      style: str = "summary") -> str:
        """
        压缩文件内容
        
        Args:
            filepath: 文件路径
            max_length: 最大输出长度（字符数）
            style: 压缩风格 - summary, concise, bullet, key_points, dialogue
        
        Returns:
            压缩后的文本
        """
        # 读取文件
        success, content = self._read_file(filepath)
        if not success:
            return f"❌ {content}"
        
        # 获取文件信息
        abs_path = os.path.abspath(os.path.expanduser(filepath))
        file_size = os.path.getsize(abs_path)
        file_size_kb = file_size / 1024
        
        # 根据风格选择压缩方法
        if style == "dialogue":
            result = self._compress_dialogue(content, max_length)
        elif style == "key_points":
            result = self._extract_important_info(content)
        else:
            result = self._compress_text(content, max_length, style)
        
        # 添加文件信息头
        header = f"📁 文件: {abs_path}\n📊 大小: {file_size_kb:.1f}KB ({file_size} 字节)\n"
        
        return header + "\n" + result
    
    def _compress_text(self, text: str, max_length: int = 500, 
                       style: str = "summary") -> str:
        """压缩文本内容"""
        system_prompts = {
            "summary": "你是一个专业的文本摘要助手。请将用户提供的文本进行智能压缩和总结，提取核心信息，保持原意。输出简洁、清晰。",
            "concise": "你是一个文本精简专家。请将用户提供的文本压缩到最精简的形式，只保留最核心的信息，去除冗余表达。",
            "bullet": "你是一个信息提取专家。请将用户提供的文本转换为要点列表形式，每个要点一行，使用 - 开头。"
        }
        
        system_prompt = system_prompts.get(style, system_prompts["summary"])
        
        user_prompt = f"""请压缩以下文本，输出长度控制在 {max_length} 字符以内：

{text}

压缩要求：
- 保留核心信息和关键细节
- 保持原文的主要结构和逻辑
- 语言简洁明了
- 不要添加原文中没有的信息"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        max_tokens = min(max_length * 2, 2000)
        
        return self._call_api(messages, max_tokens, temperature=1)
    
    def _compress_dialogue(self, dialogue_text: str, max_length: int = 800) -> str:
        """压缩对话内容"""
        system_prompt = """你是一个对话摘要专家。请将对话内容进行智能压缩和总结，提取对话的核心主题、关键问题和重要结论。输出格式清晰，便于后续参考。"""

        user_prompt = f"""请压缩以下对话内容，输出控制在 {max_length} 字符以内：

{dialogue_text}

压缩要求：
1. 提取对话的主要主题和讨论方向
2. 记录重要的用户需求和AI回复
3. 总结达成的共识或结论
4. 如有待办事项，需要列出
5. 保持对话的连贯性"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        max_tokens = min(max_length * 2, 2000)
        
        return self._call_api(messages, max_tokens, temperature=1)
    
    def _extract_important_info(self, text: str) -> str:
        """提取文本中的重要信息"""
        system_prompt = """你是一个信息提取专家。请从用户提供的文本中提取最重要的信息点，包括关键事实、数字、决策、行动项等。输出要点列表形式。"""

        user_prompt = f"""请从以下文本中提取最重要的信息：

{text}

请以要点列表形式输出，每个要点一行，使用 - 开头。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self._call_api(messages, max_tokens=1000, temperature=1)


def main():
    """主函数 - 处理命令行参数"""
    parser = argparse.ArgumentParser(description='Moonshot Kimi K2.5 文本压缩工具')
    
    # 标准接口参数
    parser.add_argument('--description', action='store_true', 
                        help='返回工具描述')
    parser.add_argument('--parameters', action='store_true', 
                        help='返回工具参数定义')
    parser.add_argument('--execute', action='store_true', 
                        help='执行工具')
    parser.add_argument('--args', type=str, default='{}',
                        help='工具参数（JSON格式）')
    
    args = parser.parse_args()
    
    # 返回描述信息
    if args.description:
        desc = """Moonshot Kimi K2.5 大模型文本压缩工具

功能：
- 压缩大文件内容（支持自动读取文件）
- 生成文本摘要和要点
- 对话内容压缩总结
- 提取关键信息

支持的文件格式：
- 文本文件 (.txt, .log, .md, .json, .py, .js, .html, .css 等)
- 自动检测文件编码（UTF-8, GBK, GB2312 等）
- 支持最大 100MB 的文件

压缩风格：
- summary: 生成文本摘要
- concise: 精简模式，去除冗余
- bullet: 转换为要点列表
- key_points: 提取关键信息点
- dialogue: 专门用于对话压缩

特点：
- 使用 Moonshot Kimi K2.5 模型
- 支持自定义输出长度
- 自动处理大文件"""
        print(desc)
        sys.exit(0)
    
    # 返回参数定义
    if args.parameters:
        parameters = {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "要压缩的文件路径（支持相对路径和绝对路径，支持 ~ 展开）"
                },
                "style": {
                    "type": "string",
                    "enum": ["summary", "concise", "bullet", "key_points", "dialogue"],
                    "description": "压缩风格：summary=摘要, concise=精简, bullet=要点列表, key_points=关键点, dialogue=对话压缩",
                    "default": "summary"
                },
                "max_length": {
                    "type": "integer",
                    "description": "最大输出长度（字符数）",
                    "default": 500
                }
            },
            "required": ["filepath"]
        }
        print(json.dumps(parameters, ensure_ascii=False))
        sys.exit(0)
    
    # 执行工具
    if args.execute:
        try:
            # 解析参数
            params = json.loads(args.args) if args.args else {}
            
            # 获取参数
            filepath = params.get("filepath")
            if not filepath:
                print("❌ 错误：需要提供 filepath 参数")
                sys.exit(1)
            
            style = params.get("style", "summary")
            max_length = params.get("max_length", 500)
            
            # 创建压缩器
            compressor = MoonshotCompressor()
            
            # 执行压缩
            result = compressor.compress_file(filepath, max_length, style)
            
            print(result)
            
        except json.JSONDecodeError as e:
            print(f"❌ 参数解析错误: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 执行错误: {e}")
            sys.exit(1)
        sys.exit(0)
    
    # 如果没有指定任何操作，显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()