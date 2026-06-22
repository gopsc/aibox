#!/usr/bin/env python3
"""hello-world - 一个简单的 Hello World 测试技能"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="hello-world - 一个简单的 Hello World 测试技能，支持自定义名字、语言和重复次数",
        epilog="""
参数说明:
  --name NAME     指定名字（默认: World）
  --count COUNT   重复输出次数（默认: 1）
  --lang LANG     输出语言，可选: zh（中文）, en（英文）, both（双语，默认）

使用示例:
  %(prog)s
  %(prog)s --name DeepSeek
  %(prog)s --name qing --count 3
  %(prog)s --name 张三 --lang zh
  %(prog)s --name Alice --lang en
  %(prog)s --name 助手 --count 2 --lang both
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--name", type=str, default="World", help="指定名字（默认: World）")
    parser.add_argument("--count", type=int, default=1, help="重复输出次数（默认: 1）")
    parser.add_argument("--lang", type=str, default="both", choices=["zh", "en", "both"],
                        help="输出语言: zh（中文）, en（英文）, both（双语，默认）")

    args = parser.parse_args()

    if args.count < 1:
        print("错误: --count 必须大于等于 1", file=sys.stderr)
        sys.exit(1)

    for i in range(args.count):
        prefix = f"[{i + 1}/{args.count}] " if args.count > 1 else ""

        outputs = []
        if args.lang in ("zh", "both"):
            outputs.append(f"你好，{args.name}！")
        if args.lang in ("en", "both"):
            outputs.append(f"Hello {args.name}!")

        print(f"{prefix}{'  '.join(outputs)}")


if __name__ == "__main__":
    main()
