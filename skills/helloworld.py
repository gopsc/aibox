#!/usr/bin/env python3
"""
扩展技能: hello_world
描述: 你好世界测试技能 - 用于测试技能系统的基本功能，支持JSON参数传递和调试信息输出

这是一个标准的扩展技能模板，实现了必需的三个接口：
--description : 返回技能描述
--parameters  : 返回参数定义（JSON Schema格式）
--execute     : 执行技能逻辑
"""

import json
import sys
import argparse
from datetime import datetime


def get_description():
    """返回技能描述"""
    return """你好世界测试技能 - 用于测试技能系统的基本功能，支持JSON参数传递和调试信息输出"""


def get_parameters():
    """返回参数定义（JSON Schema格式）"""
    return {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "要显示的消息内容",
                "default": "你好，世界！"
            },
            "repeat": {
                "type": "integer",
                "description": "重复次数",
                "default": 1
            }
        },
        "required": []
    }


def parse_args(args_str):
    """
    解析参数，支持两种格式：
    1. 标准JSON格式：{"message": "你好，世界！", "repeat": 1}
    2. 系统工具嵌套格式：{"args": "{\"message\": \"你好，世界！\", \"repeat\": 1}"}
    
    这个函数专门用于测试JSON嵌套解析功能
    """
    try:
        # 首先尝试直接解析
        parsed = json.loads(args_str)
        
        # 输出调试信息
        print(f"[DEBUG] 原始参数: {args_str}", file=sys.stderr)
        print(f"[DEBUG] 解析后类型: {type(parsed).__name__}", file=sys.stderr)
        print(f"[DEBUG] 解析后内容: {parsed}", file=sys.stderr)
        
        # 检查是否是系统工具传递的嵌套格式
        if isinstance(parsed, dict) and "args" in parsed:
            print(f"[DEBUG] 检测到系统工具嵌套格式", file=sys.stderr)
            # 系统工具格式，需要再次解析args字段
            try:
                nested_args = json.loads(parsed["args"])
                print(f"[DEBUG] 嵌套参数解析成功: {nested_args}", file=sys.stderr)
                return nested_args
            except json.JSONDecodeError:
                # 如果args不是JSON字符串，直接返回args的值
                print(f"[DEBUG] args字段不是JSON，直接返回: {parsed['args']}", file=sys.stderr)
                return {"message": parsed["args"]}
        
        print(f"[DEBUG] 标准JSON格式，直接返回", file=sys.stderr)
        return parsed
    except json.JSONDecodeError as e:
        # 如果解析失败，返回默认参数
        print(f"[DEBUG] 参数解析错误: {e}", file=sys.stderr)
        return {"message": "默认参数", "repeat": 1}


def execute(**kwargs):
    """
    执行技能逻辑
    
    参数:
        **kwargs: 根据 get_parameters 定义的参数
    
    返回:
        str: 执行结果
    """
    # 在这里实现技能的具体逻辑
    message = kwargs.get("message", "你好，世界！")
    repeat = kwargs.get("repeat", 1)
    
    result = f"你好世界技能执行成功！\n"
    result += f"消息内容: {message}\n"
    result += f"重复次数: {repeat}\n"
    result += f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    result += f"技能说明: 你好世界测试技能 - 用于测试技能系统的基本功能，支持JSON参数传递和调试信息输出\n"
    result += f"支持的参数格式:\n"
    result += f"  1. 标准JSON格式: {{\"message\": \"你好，世界！\", \"repeat\": 1}}\n"
    result += f"  2. 系统工具嵌套格式: {{\"args\": \"{{\\\"message\\\": \\\"你好，世界！\\\", \\\"repeat\\\": 1}}\"}}\n"
    
    # 根据重复次数输出消息
    for i in range(repeat):
        result += f"输出 {i+1}: {message}\n"
    
    return result


def main():
    """命令行接口 - 必须实现 --description, --parameters, --execute"""
    parser = argparse.ArgumentParser(description='扩展技能: hello_world')
    parser.add_argument('--description', action='store_true', help='返回技能描述')
    parser.add_argument('--parameters', action='store_true', help='返回参数定义（JSON格式）')
    parser.add_argument('--execute', action='store_true', help='执行技能')
    parser.add_argument('--args', type=str, default='{}', help='执行参数（JSON格式）')
    
    args = parser.parse_args()
    
    if args.description:
        print(get_description())
    elif args.parameters:
        print(json.dumps(get_parameters(), ensure_ascii=False))
    elif args.execute:
        try:
            # 使用参数解析函数，支持嵌套JSON
            kwargs = parse_args(args.args)
            result = execute(**kwargs)
            print(result)
        except Exception as e:
            print(f"执行错误: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()