#!/usr/bin/env python3
"""你好世界测试技能 - 用于测试技能系统的基本功能。"""

import sys
import argparse
from datetime import datetime


def execute(message: str = "你好，世界！", repeat: int = 1, verbose: bool = False) -> str:
    """
    执行技能逻辑
    
    Args:
        message: 要显示的消息内容
        repeat: 重复次数
        verbose: 是否显示详细调试信息
    
    Returns:
        执行结果字符串
    """
    result_lines = []
    
    # 构建结果
    result_lines.append("✅ 你好世界技能执行成功！")
    result_lines.append(f"📝 消息内容: {message}")
    result_lines.append(f"🔢 重复次数: {repeat}")
    result_lines.append(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if verbose:
        result_lines.append("")
        result_lines.append("🔧 调试信息:")
        result_lines.append(f"   - 技能名称: hello-world")
        result_lines.append(f"   - 参数格式: 标准命令行参数")
        result_lines.append(f"   - 消息长度: {len(message)} 字符")
    
    result_lines.append("")
    result_lines.append("📤 输出内容:")
    
    # 根据重复次数输出消息
    for i in range(repeat):
        result_lines.append(f"   [{i+1}] {message}")
    
    return "\n".join(result_lines)


def main():
    parser = argparse.ArgumentParser(
        description="你好世界测试技能 - 用于测试技能系统的基本功能。",
        epilog="""
使用示例:
  # 使用默认参数
  hello-world

  # 自定义消息
  hello-world --message "Hello, World!"

  # 自定义消息和重复次数
  hello-world --message "测试消息" --repeat 3

  # 显示详细调试信息
  hello-world --message "调试模式" --repeat 2 --verbose

  # 查看帮助
  hello-world --help
        """
    )
    
    parser.add_argument("--message", "-m", type=str, default="你好，世界！",
        help="要显示的消息内容（默认: 你好，世界！）")
    
    parser.add_argument("--repeat", "-r", type=int, default=1,
        help="重复次数（默认: 1）")
    
    parser.add_argument("--verbose", "-v", action="store_true",
        help="显示详细调试信息")
    
    args = parser.parse_args()
    
    # 参数验证
    if args.repeat < 1:
        print("❌ 错误: repeat 参数必须大于等于 1", file=sys.stderr)
        sys.exit(1)
    
    if args.repeat > 100:
        print("⚠️ 警告: repeat 参数过大（最大100），将限制为100", file=sys.stderr)
        args.repeat = 100
    
    # 执行技能
    try:
        result = execute(
            message=args.message,
            repeat=args.repeat,
            verbose=args.verbose
        )
        print(result)
    except Exception as e:
        print(f"❌ 执行错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()