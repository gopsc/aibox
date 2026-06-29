#!/usr/bin/env python3
"""bing_search - 使用必应(Bing)搜索信息，一键获取标题、摘要和链接"""

import argparse
import re
import sys
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup


def search(keyword, num_results=5):
    """使用必应搜索并返回结果列表"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    url = f"https://cn.bing.com/search?q={quote(keyword)}&count={num_results}"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = "utf-8"
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ 请求失败: {e}", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Bing 搜索结果：class="b_algo"
    result_divs = soup.select(".b_algo")

    for div in result_divs:
        # 标题
        title_tag = div.select_one("h2 a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        # 链接
        link = title_tag.get("href", "")

        # 摘要
        abstract_tag = div.select_one(".b_caption p, .b_lineclamp2, .b_lineclamp3")
        abstract = ""
        if abstract_tag:
            abstract = abstract_tag.get_text(strip=True)

        results.append({"title": title, "link": link, "abstract": abstract})

        if len(results) >= num_results:
            break

    return results


def main():
    parser = argparse.ArgumentParser(
        description="bing_search - 使用必应(Bing)搜索信息，一键获取标题、摘要和链接",
        epilog="""
参数说明:
  keyword             搜索关键词（必填）
  -n, --num           返回结果条数，默认5条（最多20条）

使用示例:
  %(prog)s 天气                搜索"天气"
  %(prog)s C罗 -n 10           搜索"C罗"，返回10条结果
  %(prog)s "python教程" -n 3   搜索"python教程"，返回3条结果
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("keyword", nargs="?", help="搜索关键词")
    parser.add_argument("-n", "--num", type=int, default=5, help="返回结果条数（默认5条）")
    parser.add_argument("-v", "--version", action="version", version="bing_search v1.0 (Bing 后端)")

    args = parser.parse_args()

    if not args.keyword:
        parser.print_help()
        sys.exit(0)

    keyword = args.keyword.strip()
    num = min(max(args.num, 1), 20)

    print(f"🔍 必应搜索: {keyword}\n")
    results = search(keyword, num)

    if not results:
        print("😕 未找到相关结果")
        return

    for i, r in enumerate(results, 1):
        print(f"{'='*60}")
        print(f"  [{i}] {r['title']}")
        if r["abstract"]:
            abstract = r["abstract"]
            if len(abstract) > 150:
                abstract = abstract[:147] + "..."
            print(f"      {abstract}")
        print(f"      🔗 {r['link']}")
        print()

    print(f"--- 共找到 {len(results)} 条结果 ---")


if __name__ == "__main__":
    main()
