#!/usr/bin/env python3
"""
视觉理解工具 - 理解图片内容
功能：传入图片路径和提示词，调用豆包多模态模型理解图片内容并生成回复
支持流式输出结果
"""

import os
import sys
import json
import base64
import argparse
import requests

# 豆包API配置
DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DOUBAO_MODEL = "doubao-seed-2-0-pro-260215"  # 使用支持视觉的模型

def get_api_key():
    """获取豆包API密钥"""
    key_path = os.path.expanduser("~/.cert/doubao.key")
    try:
        with open(key_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        return None

def encode_image_to_base64(image_path):
    """将图片编码为base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def analyze_image(image_path, prompt, stream=False):
    """调用豆包API分析图片"""
    api_key = get_api_key()
    if not api_key:
        return "错误：无法读取API密钥，请确保 ~/.cert/doubao.key 文件存在"
    
    if not os.path.exists(image_path):
        return f"错误：图片文件不存在 - {image_path}"
    
    # 编码图片
    try:
        base64_image = encode_image_to_base64(image_path)
    except Exception as e:
        return f"错误：无法读取图片文件 - {str(e)}"
    
    # 准备请求数据
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]
    
    payload = {
        "model": DOUBAO_MODEL,
        "messages": messages,
        "stream": stream,
        "max_tokens": 4096,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            DOUBAO_API_URL,
            headers=headers,
            json=payload,
            stream=stream,
            timeout=60
        )
        
        if response.status_code != 200:
            return f"API请求失败 (HTTP {response.status_code}): {response.text}"
        
        if stream:
            return response
        else:
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "无返回内容")
            
    except Exception as e:
        return f"API调用错误: {str(e)}"

def main():
    """主函数 - 处理命令行参数并执行"""
    parser = argparse.ArgumentParser(description='视觉理解工具')
    
    # 扩展工具必需的参数
    parser.add_argument('--description', action='store_true', help='返回工具描述')
    parser.add_argument('--parameters', action='store_true', help='返回工具参数定义')
    parser.add_argument('--execute', action='store_true', help='执行工具')
    parser.add_argument('--args', type=str, help='执行参数（JSON格式）')
    
    args = parser.parse_args()
    
    # 处理 --description 参数
    if args.description:
        print("""视觉理解工具 - 理解图片内容
功能：传入图片路径和提示词，调用豆包多模态模型理解图片内容并生成回复
支持流式输出结果
需要安装：requests""")
        return 0
    
    # 处理 --parameters 参数
    if args.parameters:
        parameters = {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "图片文件路径（支持绝对路径或相对路径）"
                },
                "prompt": {
                    "type": "string",
                    "description": "提示词，告诉AI要看什么、理解什么"
                },
                "stream": {
                    "type": "boolean",
                    "description": "是否流式输出结果",
                    "default": True
                }
            },
            "required": ["image_path", "prompt"]
        }
        print(json.dumps(parameters, ensure_ascii=False))
        return 0
    
    # 处理 --execute 参数
    if args.execute and args.args:
        try:
            kwargs = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"参数解析错误: {e}"}))
            return 1
        
        image_path = kwargs.get("image_path")
        prompt = kwargs.get("prompt")
        stream = kwargs.get("stream", True)
        
        if not image_path or not prompt:
            missing = []
            if not image_path: missing.append("image_path")
            if not prompt: missing.append("prompt")
            print(json.dumps({"error": f"缺少必需参数: {', '.join(missing)}"}))
            return 1
        
        # 展开用户目录
        image_path = os.path.expanduser(image_path)
        
        # 调用豆包API
        result = analyze_image(image_path, prompt, stream)
        
        if stream and not isinstance(result, str):
            # 流式输出
            try:
                for line in result.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            
                            if "content" in delta and delta["content"]:
                                print(delta["content"], end="", flush=True)
                                
                        except json.JSONDecodeError:
                            continue
                
                print()  # 最后换行
                
            except Exception as e:
                print(json.dumps({"error": str(e)}))
                return 1
        else:
            # 非流式输出
            print(result)
        
        return 0
    
    # 如果没有参数或参数错误，显示帮助
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())