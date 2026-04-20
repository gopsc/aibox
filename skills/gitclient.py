#!/usr/bin/env python3
"""GitHub 仓库管理工具 - 搜索、克隆、推送、拉取、提交等完整Git操作。"""

import sys
import os
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Optional
import time
import base64
import subprocess
import shutil
from pathlib import Path

# ==================== 配置 ====================

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GIT_USER_NAME = os.environ.get("GIT_USER_NAME", "AI Assistant")
GIT_USER_EMAIL = os.environ.get("GIT_USER_EMAIL", "ai@assistant.com")
WORKSPACE_DIR = os.environ.get("GIT_WORKSPACE", os.path.expanduser("~/.aibox/git_workspace"))

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "AI-Assistant/1.0"
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

# 智能限制常量
DEFAULT_PER_PAGE = 5
MAX_PER_PAGE = 10
MAX_CONTENT_PREVIEW = 1000
MAX_LIST_PREVIEW = 20
MAX_STRING_LENGTH = 200


# ==================== GitHub工具类 ====================

class GitHubTool:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.last_request_time = 0
        os.makedirs(WORKSPACE_DIR, exist_ok=True)

    def _rate_limit_wait(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < 1.0:
            time.sleep(1.0 - time_since_last)
        self.last_request_time = time.time()

    def _make_request(self, url: str, params: Dict = None, method: str = "GET") -> Dict:
        self._rate_limit_wait()
        try:
            if method == "GET":
                response = self.session.get(url, params=params, timeout=30)
            else:
                response = self.session.post(url, json=params, timeout=30)
            response.raise_for_status()
            return response.json() if response.content else {}
        except Exception as e:
            return {"error": str(e)}

    def _truncate(self, text: str, max_len: int = MAX_STRING_LENGTH) -> str:
        if not text:
            return ""
        return text[:max_len] + "..." if len(text) > max_len else text

    def _format_date(self, date_str: str) -> str:
        if not date_str:
            return ""
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d")
        except:
            return date_str

    def _run_git(self, repo_path: str, cmd: List[str]) -> Dict:
        try:
            result = subprocess.run(
                ["git"] + cmd, cwd=repo_path, capture_output=True,
                text=True, timeout=60, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}
            )
            return {"success": result.returncode == 0, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _auth_url(self, repo_url: str) -> str:
        if GITHUB_TOKEN and repo_url.startswith("https://"):
            return repo_url.replace("https://", f"https://{GITHUB_TOKEN}@")
        return repo_url

    # ==================== 搜索功能 ====================

    def search_repos(self, query: str, sort: str = "stars", per_page: int = DEFAULT_PER_PAGE, page: int = 1) -> str:
        url = f"{GITHUB_API_URL}/search/repositories"
        result = self._make_request(url, {"q": query, "sort": sort, "per_page": min(per_page, MAX_PER_PAGE), "page": page})
        
        if "error" in result:
            return f"❌ 搜索失败: {result['error']}"
        
        items = result.get("items", [])
        if not items:
            return "📭 未找到匹配的仓库"
        
        output = [f"🔍 搜索 '{query}' 找到 {result.get('total_count', 0)} 个仓库 (第{page}页):\n"]
        for repo in items[:MAX_LIST_PREVIEW]:
            output.append(f"  📦 {repo.get('full_name')}")
            output.append(f"     ⭐ {repo.get('stargazers_count', 0)} | 🍴 {repo.get('forks_count', 0)} | 📝 {repo.get('language', '未知')}")
            output.append(f"     📖 {self._truncate(repo.get('description', '无描述'))}")
            output.append(f"     🔗 {repo.get('html_url')}\n")
        return "\n".join(output)

    def get_repo(self, repo: str) -> str:
        url = f"{GITHUB_API_URL}/repos/{repo}"
        result = self._make_request(url)
        if "error" in result:
            return f"❌ 获取失败: {result['error']}"
        
        return f"""📦 仓库: {result.get('full_name')}
📖 描述: {self._truncate(result.get('description', '无描述'))}
⭐ Stars: {result.get('stargazers_count', 0)} | 🍴 Forks: {result.get('forks_count', 0)} | 👁️ Watchers: {result.get('watchers_count', 0)}
📝 语言: {result.get('language', '未知')}
🌿 默认分支: {result.get('default_branch', 'main')}
📅 更新: {self._format_date(result.get('updated_at'))}
🔗 URL: {result.get('html_url')}
📥 克隆: {result.get('clone_url')}"""

    def get_readme(self, repo: str, branch: str = None) -> str:
        url = f"{GITHUB_API_URL}/repos/{repo}/readme"
        params = {"ref": branch} if branch else {}
        result = self._make_request(url, params)
        
        if "error" in result or not result.get("content"):
            return "❌ 无法获取README"
        
        import base64
        content = base64.b64decode(result["content"].replace("\n", "")).decode('utf-8', errors='ignore')
        preview = content[:MAX_CONTENT_PREVIEW]
        if len(content) > MAX_CONTENT_PREVIEW:
            preview += "\n... (内容过长，已截断)"
        
        return f"📖 README ({result.get('name')}):\n\n{preview}"

    # ==================== Git操作 ====================

    def clone(self, repo: str, branch: str = None, depth: int = 1) -> str:
        safe_name = repo.replace("/", "_")
        target_dir = os.path.join(WORKSPACE_DIR, safe_name)
        
        if os.path.exists(target_dir):
            return f"⚠️ 仓库已存在: {target_dir}\n💡 使用 pull 命令拉取更新"
        
        clone_url = self._auth_url(f"https://github.com/{repo}.git")
        cmd = ["clone"]
        if depth > 0:
            cmd.extend(["--depth", str(depth)])
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([clone_url, target_dir])
        
        result = self._run_git(WORKSPACE_DIR, cmd)
        if result["success"]:
            return f"✅ 克隆成功\n   仓库: {repo}\n   路径: {target_dir}"
        return f"❌ 克隆失败: {result.get('stderr', result.get('error', '未知错误'))}"

    def pull(self, repo_path: str, branch: str = None) -> str:
        if not os.path.exists(repo_path):
            return f"❌ 路径不存在: {repo_path}"
        
        if not branch:
            br = self._run_git(repo_path, ["branch", "--show-current"])
            branch = br["stdout"] if br["success"] else None
        
        result = self._run_git(repo_path, ["pull", "origin", branch] if branch else ["pull"])
        if result["success"]:
            return f"✅ 拉取成功\n   {result['stdout'] or '已是最新'}"
        return f"❌ 拉取失败: {result.get('stderr', result.get('error'))}"

    def push(self, repo_path: str, branch: str = None, force: bool = False) -> str:
        if not os.path.exists(repo_path):
            return f"❌ 路径不存在: {repo_path}"
        
        if not branch:
            br = self._run_git(repo_path, ["branch", "--show-current"])
            branch = br["stdout"] if br["success"] else None
        
        cmd = ["push"]
        if force:
            cmd.append("--force")
        if branch:
            cmd.extend(["origin", branch])
        
        result = self._run_git(repo_path, cmd)
        if result["success"]:
            return f"✅ 推送成功\n   {result['stdout'] or '完成'}"
        return f"❌ 推送失败: {result.get('stderr', result.get('error'))}"

    def commit(self, repo_path: str, message: str, all_files: bool = False) -> str:
        if not os.path.exists(repo_path):
            return f"❌ 路径不存在: {repo_path}"
        
        self._run_git(repo_path, ["config", "user.name", GIT_USER_NAME])
        self._run_git(repo_path, ["config", "user.email", GIT_USER_EMAIL])
        
        add_cmd = ["add", "-A"] if all_files else ["add", "-u"]
        add_result = self._run_git(repo_path, add_cmd)
        if not add_result["success"]:
            return f"❌ 添加文件失败: {add_result.get('stderr')}"
        
        status = self._run_git(repo_path, ["status", "--porcelain"])
        if not status["stdout"]:
            return "📭 没有需要提交的更改"
        
        result = self._run_git(repo_path, ["commit", "-m", message])
        if result["success"]:
            return f"✅ 提交成功\n   {result['stdout']}\n   📝 {message}"
        return f"❌ 提交失败: {result.get('stderr', result.get('error'))}"

    def status(self, repo_path: str) -> str:
        if not os.path.exists(repo_path):
            return f"❌ 路径不存在: {repo_path}"
        
        branch = self._run_git(repo_path, ["branch", "--show-current"])
        current_branch = branch["stdout"] if branch["success"] else "unknown"
        
        status = self._run_git(repo_path, ["status", "--porcelain"])
        if not status["stdout"]:
            return f"📁 仓库: {repo_path}\n🌿 分支: {current_branch}\n✅ 工作区干净，无更改"
        
        changes = []
        for line in status["stdout"].split("\n"):
            if line:
                code = line[:2].strip()
                file_path = line[3:].strip()
                status_map = {"M": "修改", "A": "新增", "D": "删除", "?": "未跟踪"}
                changes.append(f"   {status_map.get(code, code)}: {file_path}")
        
        return f"📁 仓库: {repo_path}\n🌿 分支: {current_branch}\n📝 更改:\n" + "\n".join(changes[:20])

    def branches(self, repo_path: str, remote: bool = False) -> str:
        if not os.path.exists(repo_path):
            return f"❌ 路径不存在: {repo_path}"
        
        cmd = ["branch", "-r"] if remote else ["branch"]
        result = self._run_git(repo_path, cmd)
        if result["success"]:
            branches = [b.strip().replace("* ", "") for b in result["stdout"].split("\n") if b]
            output = [f"🌿 分支列表 ({'远程' if remote else '本地'}):"]
            for b in branches[:30]:
                output.append(f"   {b}")
            return "\n".join(output)
        return f"❌ 获取分支失败: {result.get('stderr')}"

    def list_local(self) -> str:
        repos = []
        if os.path.exists(WORKSPACE_DIR):
            for item in os.listdir(WORKSPACE_DIR):
                item_path = os.path.join(WORKSPACE_DIR, item)
                if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, ".git")):
                    branch = self._run_git(item_path, ["branch", "--show-current"])
                    repos.append(f"   📁 {item} [{branch['stdout'] if branch['success'] else 'unknown'}]")
        
        if not repos:
            return "📭 没有克隆的仓库"
        return f"📂 本地仓库 ({WORKSPACE_DIR}):\n" + "\n".join(repos)

    def delete(self, repo_path: str, confirm: bool = False) -> str:
        if not confirm:
            return "⚠️ 需要确认删除，请添加 --confirm 参数"
        if not os.path.exists(repo_path):
            return f"❌ 路径不存在: {repo_path}"
        try:
            shutil.rmtree(repo_path)
            return f"✅ 已删除: {repo_path}"
        except Exception as e:
            return f"❌ 删除失败: {e}"


# ==================== 命令行解析 ====================

def main():
    parser = argparse.ArgumentParser(
        description="GitHub 仓库管理工具 - 搜索、克隆、推送、拉取、提交等完整Git操作。",
        epilog="""
使用示例:
  # 搜索仓库
  git-tool --action search_repos --query "python"

  # 获取仓库信息
  git-tool --action get_repo --repo "owner/repo"

  # 克隆仓库
  git-tool --action clone --repo "owner/repo" --branch main

  # 查看状态
  git-tool --action status --repo_path "/path/to/repo"

  # 提交更改
  git-tool --action commit --repo_path "/path/to/repo" --message "fix: bug修复" --all

  # 推送代码
  git-tool --action push --repo_path "/path/to/repo" --branch main

  # 拉取更新
  git-tool --action pull --repo_path "/path/to/repo"

  # 列出本地仓库
  git-tool --action list_local

  # 删除本地仓库
  git-tool --action delete --repo_path "/path/to/repo" --confirm

环境变量:
  GITHUB_TOKEN    GitHub访问令牌（推送必需）
  GIT_USER_NAME   Git用户名
  GIT_USER_EMAIL  Git邮箱
  GIT_WORKSPACE   工作目录（默认 ~/.aibox/git_workspace）
        """
    )
    
    parser.add_argument("--action", "-a", required=True, 
        choices=["search_repos", "get_repo", "get_readme", "clone", "pull", "push",
                 "commit", "status", "branches", "list_local", "delete"],
        help="操作类型")
    
    # 搜索参数
    parser.add_argument("--query", "-q", help="搜索关键词")
    parser.add_argument("--sort", default="stars", help="排序方式 (stars/forks/updated)")
    parser.add_argument("--per_page", "-n", type=int, default=5, help="每页数量 (1-10)")
    parser.add_argument("--page", "-p", type=int, default=1, help="页码")
    
    # 仓库参数
    parser.add_argument("--repo", "-r", help="仓库全名 (格式: owner/repo)")
    parser.add_argument("--branch", "-b", help="分支名")
    parser.add_argument("--depth", type=int, default=1, help="克隆深度 (1=浅克隆)")
    
    # Git操作参数
    parser.add_argument("--repo_path", help="本地仓库路径")
    parser.add_argument("--message", "-m", help="提交消息")
    parser.add_argument("--all", "-A", action="store_true", help="提交所有更改（包括新文件）")
    parser.add_argument("--force", "-f", action="store_true", help="强制推送")
    parser.add_argument("--remote", action="store_true", help="列出远程分支")
    parser.add_argument("--confirm", action="store_true", help="确认删除操作")
    
    args = parser.parse_args()
    
    tool = GitHubTool()
    
    # 执行操作
    if args.action == "search_repos":
        if not args.query:
            print("❌ 需要 --query 参数")
            sys.exit(1)
        print(tool.search_repos(args.query, args.sort, args.per_page, args.page))
    
    elif args.action == "get_repo":
        if not args.repo:
            print("❌ 需要 --repo 参数")
            sys.exit(1)
        print(tool.get_repo(args.repo))
    
    elif args.action == "get_readme":
        if not args.repo:
            print("❌ 需要 --repo 参数")
            sys.exit(1)
        print(tool.get_readme(args.repo, args.branch))
    
    elif args.action == "clone":
        if not args.repo:
            print("❌ 需要 --repo 参数")
            sys.exit(1)
        print(tool.clone(args.repo, args.branch, args.depth))
    
    elif args.action == "pull":
        if not args.repo_path:
            print("❌ 需要 --repo_path 参数")
            sys.exit(1)
        print(tool.pull(args.repo_path, args.branch))
    
    elif args.action == "push":
        if not args.repo_path:
            print("❌ 需要 --repo_path 参数")
            sys.exit(1)
        if not GITHUB_TOKEN:
            print("⚠️ 未设置 GITHUB_TOKEN，推送可能失败")
        print(tool.push(args.repo_path, args.branch, args.force))
    
    elif args.action == "commit":
        if not args.repo_path:
            print("❌ 需要 --repo_path 参数")
            sys.exit(1)
        if not args.message:
            print("❌ 需要 --message 参数")
            sys.exit(1)
        print(tool.commit(args.repo_path, args.message, args.all))
    
    elif args.action == "status":
        if not args.repo_path:
            print("❌ 需要 --repo_path 参数")
            sys.exit(1)
        print(tool.status(args.repo_path))
    
    elif args.action == "branches":
        if not args.repo_path:
            print("❌ 需要 --repo_path 参数")
            sys.exit(1)
        print(tool.branches(args.repo_path, args.remote))
    
    elif args.action == "list_local":
        print(tool.list_local())
    
    elif args.action == "delete":
        if not args.repo_path:
            print("❌ 需要 --repo_path 参数")
            sys.exit(1)
        print(tool.delete(args.repo_path, args.confirm))


if __name__ == "__main__":
    main()