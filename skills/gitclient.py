#!/usr/bin/env python3
"""
GitHub 搜索和访问工具 - 增强版
功能：搜索代码仓库、获取仓库信息、查看文件内容、搜索代码、克隆、拉取、推送等
特点：智能分页、内容截断、增量加载、完整的Git操作
"""

import json
import sys
import os
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
import time
import base64
import subprocess
import tempfile
import shutil
from pathlib import Path

# ==================== 配置 ====================

GITHUB_API_URL = "https://api.github.com"

# 如果需要认证，可以设置环境变量或配置文件
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GIT_USER_NAME = os.environ.get("GIT_USER_NAME", "AI Assistant")
GIT_USER_EMAIL = os.environ.get("GIT_USER_EMAIL", "ai@assistant.com")

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "AI-Assistant/1.0"
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

# 智能限制常量
DEFAULT_PER_PAGE = 5  # 默认每页数量
MAX_PER_PAGE = 10     # 最大每页数量
MAX_CONTENT_PREVIEW = 1000  # 内容预览最大字符数
MAX_LIST_PREVIEW = 20  # 列表预览最大项目数
MAX_STRING_LENGTH = 200  # 字符串字段最大长度

# 工作目录配置
WORKSPACE_DIR = os.environ.get("GIT_WORKSPACE", os.path.expanduser("~/.aibox/git_workspace"))


# ==================== 工具类 ====================

class GitHubTool:
    """GitHub搜索和访问工具 - 增强版"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.last_request_time = 0
        self.rate_limit_remaining = 0
        self.rate_limit_reset = 0
        
        # 确保工作目录存在
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
    
    def _rate_limit_wait(self):
        """简单的速率限制处理"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < 1.0:
            time.sleep(1.0 - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Dict = None, method: str = "GET", 
                     data: Dict = None) -> Dict:
        """发送HTTP请求"""
        self._rate_limit_wait()
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=30)
            elif method.upper() == "PATCH":
                response = self.session.patch(url, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=30)
            else:
                return {"error": f"不支持的HTTP方法: {method}"}
            
            # 记录剩余请求次数
            remaining = response.headers.get('X-RateLimit-Remaining')
            reset = response.headers.get('X-RateLimit-Reset')
            if remaining:
                self.rate_limit_remaining = int(remaining)
            if reset:
                self.rate_limit_reset = int(reset)
            
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                return {
                    "error": "GitHub API速率限制已达到",
                    "rate_limited": True,
                    "reset_time": reset
                }
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    if 'message' in error_data:
                        error_msg = error_data['message']
                except:
                    pass
            
            return {
                "error": error_msg,
                "status_code": getattr(e.response, 'status_code', 500)
            }
    
    def _truncate_string(self, text: Optional[str], max_length: int = MAX_STRING_LENGTH) -> str:
        """智能截断字符串"""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    def _format_result(self, data: Any, summary: str = None) -> Dict:
        """统一格式化返回结果"""
        result = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        if summary:
            result["summary"] = summary
        return result
    
    def _format_error(self, error: str, details: Dict = None) -> Dict:
        """统一格式化错误"""
        result = {
            "success": False,
            "error": error
        }
        if details:
            result["details"] = details
        return result
    
    def _run_git_command(self, repo_path: str, command: List[str], 
                        timeout: int = 60) -> Dict:
        """
        运行git命令
        
        Args:
            repo_path: 仓库路径
            command: git命令列表（不包含'git'）
            timeout: 超时时间（秒）
        """
        try:
            full_command = ["git"] + command
            result = subprocess.run(
                full_command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}  # 禁用交互式提示
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"命令执行超时（{timeout}秒）"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_auth_url(self, repo_url: str) -> str:
        """获取带认证的仓库URL"""
        if not GITHUB_TOKEN:
            return repo_url
        
        # 对于HTTPS URL，插入token
        if repo_url.startswith("https://"):
            return repo_url.replace("https://", f"https://{GITHUB_TOKEN}@")
        
        return repo_url
    
    # ==================== 新增：Git操作 ====================
    
    def clone_repository(self, repo_full_name: str, branch: str = None,
                        target_dir: str = None, depth: int = 1) -> Dict:
        """
        克隆GitHub仓库到本地
        
        Args:
            repo_full_name: 仓库全名 (如 "owner/repo")
            branch: 要克隆的分支（默认为仓库默认分支）
            target_dir: 目标目录（默认为 ~/.aibox/git_workspace/owner_repo）
            depth: 克隆深度（1表示浅克隆，0表示完整克隆）
        """
        # 构建目标路径
        if not target_dir:
            safe_name = repo_full_name.replace("/", "_").replace("\\", "_")
            target_dir = os.path.join(WORKSPACE_DIR, safe_name)
        
        # 检查目录是否已存在
        if os.path.exists(target_dir):
            return self._format_error(
                f"目标目录已存在: {target_dir}",
                {"suggestion": "使用 pull_repository 拉取更新，或指定不同的 target_dir"}
            )
        
        # 构建克隆URL
        clone_url = f"https://github.com/{repo_full_name}.git"
        auth_url = self._get_auth_url(clone_url)
        
        # 构建克隆命令
        cmd = ["clone"]
        if depth > 0:
            cmd.extend(["--depth", str(depth)])
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([auth_url, target_dir])
        
        # 执行克隆
        result = self._run_git_command(WORKSPACE_DIR, cmd)
        
        if result["success"]:
            # 获取仓库信息
            repo_info = self.get_repository(repo_full_name)
            repo_data = repo_info.get("data", {}) if repo_info.get("success") else {}
            
            return self._format_result({
                "repository": repo_full_name,
                "local_path": target_dir,
                "branch": branch or repo_data.get("default_branch", "main"),
                "clone_depth": depth,
                "message": f"成功克隆到: {target_dir}"
            })
        else:
            # 清理可能创建的空目录
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            
            return self._format_error(
                f"克隆失败: {result.get('stderr') or result.get('error')}"
            )
    
    def pull_repository(self, repo_path: str, branch: str = None,
                       rebase: bool = False) -> Dict:
        """
        拉取远程仓库更新
        
        Args:
            repo_path: 本地仓库路径
            branch: 要拉取的分支（默认为当前分支）
            rebase: 是否使用rebase而不是merge
        """
        if not os.path.exists(repo_path):
            return self._format_error(f"仓库路径不存在: {repo_path}")
        
        # 检查是否是git仓库
        git_check = self._run_git_command(repo_path, ["rev-parse", "--git-dir"])
        if not git_check["success"]:
            return self._format_error(f"路径不是有效的Git仓库: {repo_path}")
        
        # 获取当前分支
        if not branch:
            branch_result = self._run_git_command(repo_path, ["branch", "--show-current"])
            if branch_result["success"] and branch_result["stdout"]:
                branch = branch_result["stdout"]
        
        # 执行拉取
        cmd = ["pull"]
        if rebase:
            cmd.append("--rebase")
        cmd.append("origin")
        if branch:
            cmd.append(branch)
        
        result = self._run_git_command(repo_path, cmd)
        
        if result["success"]:
            return self._format_result({
                "repository": repo_path,
                "branch": branch,
                "output": result["stdout"],
                "message": "成功拉取更新"
            })
        else:
            return self._format_error(
                f"拉取失败: {result.get('stderr') or result.get('error')}"
            )
    
    def push_repository(self, repo_path: str, branch: str = None,
                       force: bool = False, set_upstream: bool = False) -> Dict:
        """
        推送本地更改到远程仓库
        
        Args:
            repo_path: 本地仓库路径
            branch: 要推送的分支（默认为当前分支）
            force: 是否强制推送
            set_upstream: 是否设置上游分支
        """
        if not os.path.exists(repo_path):
            return self._format_error(f"仓库路径不存在: {repo_path}")
        
        # 检查是否是git仓库
        git_check = self._run_git_command(repo_path, ["rev-parse", "--git-dir"])
        if not git_check["success"]:
            return self._format_error(f"路径不是有效的Git仓库: {repo_path}")
        
        # 获取当前分支
        if not branch:
            branch_result = self._run_git_command(repo_path, ["branch", "--show-current"])
            if branch_result["success"] and branch_result["stdout"]:
                branch = branch_result["stdout"]
        
        # 检查是否有未提交的更改
        status_result = self._run_git_command(repo_path, ["status", "--porcelain"])
        if status_result["success"] and status_result["stdout"]:
            return self._format_error(
                "存在未提交的更改，请先提交",
                {"suggestion": "使用 commit_changes 提交更改"}
            )
        
        # 执行推送
        cmd = ["push"]
        if force:
            cmd.append("--force")
        if set_upstream:
            cmd.append("--set-upstream")
        cmd.append("origin")
        if branch:
            cmd.append(branch)
        
        result = self._run_git_command(repo_path, cmd)
        
        if result["success"]:
            return self._format_result({
                "repository": repo_path,
                "branch": branch,
                "output": result["stdout"],
                "message": "成功推送到远程仓库"
            })
        else:
            return self._format_error(
                f"推送失败: {result.get('stderr') or result.get('error')}"
            )
    
    def commit_changes(self, repo_path: str, message: str,
                      files: List[str] = None, all_files: bool = False) -> Dict:
        """
        提交本地更改
        
        Args:
            repo_path: 本地仓库路径
            message: 提交消息
            files: 要提交的文件列表（相对于仓库根目录）
            all_files: 是否提交所有更改（包括新文件）
        """
        if not os.path.exists(repo_path):
            return self._format_error(f"仓库路径不存在: {repo_path}")
        
        # 检查是否是git仓库
        git_check = self._run_git_command(repo_path, ["rev-parse", "--git-dir"])
        if not git_check["success"]:
            return self._format_error(f"路径不是有效的Git仓库: {repo_path}")
        
        # 配置用户信息（如果未配置）
        self._run_git_command(repo_path, ["config", "user.name", GIT_USER_NAME])
        self._run_git_command(repo_path, ["config", "user.email", GIT_USER_EMAIL])
        
        # 添加文件
        if all_files:
            add_result = self._run_git_command(repo_path, ["add", "-A"])
        elif files:
            add_result = self._run_git_command(repo_path, ["add"] + files)
        else:
            # 默认添加所有更改（不包括新文件）
            add_result = self._run_git_command(repo_path, ["add", "-u"])
        
        if not add_result["success"]:
            return self._format_error(
                f"添加文件失败: {add_result.get('stderr') or add_result.get('error')}"
            )
        
        # 检查是否有更改需要提交
        status_result = self._run_git_command(repo_path, ["status", "--porcelain"])
        if not status_result["stdout"]:
            return self._format_result({
                "repository": repo_path,
                "message": "没有需要提交的更改"
            })
        
        # 提交更改
        commit_result = self._run_git_command(repo_path, ["commit", "-m", message])
        
        if commit_result["success"]:
            # 解析提交信息
            commit_info = {}
            if commit_result["stdout"]:
                lines = commit_result["stdout"].split("\n")
                for line in lines:
                    if "changed" in line or "insertion" in line or "deletion" in line:
                        commit_info["summary"] = line.strip()
            
            return self._format_result({
                "repository": repo_path,
                "commit_message": message,
                "commit_info": commit_info,
                "output": commit_result["stdout"],
                "message": "成功提交更改"
            })
        else:
            return self._format_error(
                f"提交失败: {commit_result.get('stderr') or commit_result.get('error')}"
            )
    
    def create_branch(self, repo_path: str, branch_name: str,
                     source_branch: str = None, checkout: bool = True) -> Dict:
        """
        创建新分支
        
        Args:
            repo_path: 本地仓库路径
            branch_name: 新分支名称
            source_branch: 源分支（默认为当前分支）
            checkout: 是否切换到新分支
        """
        if not os.path.exists(repo_path):
            return self._format_error(f"仓库路径不存在: {repo_path}")
        
        # 检查是否是git仓库
        git_check = self._run_git_command(repo_path, ["rev-parse", "--git-dir"])
        if not git_check["success"]:
            return self._format_error(f"路径不是有效的Git仓库: {repo_path}")
        
        # 获取最新代码
        self._run_git_command(repo_path, ["fetch", "--all"])
        
        # 创建分支
        if source_branch:
            # 从指定分支创建
            branch_result = self._run_git_command(
                repo_path, ["branch", branch_name, f"origin/{source_branch}"]
            )
        else:
            # 从当前分支创建
            branch_result = self._run_git_command(repo_path, ["branch", branch_name])
        
        if not branch_result["success"]:
            return self._format_error(
                f"创建分支失败: {branch_result.get('stderr') or branch_result.get('error')}"
            )
        
        # 切换分支
        if checkout:
            checkout_result = self._run_git_command(repo_path, ["checkout", branch_name])
            if not checkout_result["success"]:
                return self._format_error(
                    f"切换分支失败: {checkout_result.get('stderr') or checkout_result.get('error')}"
                )
        
        return self._format_result({
            "repository": repo_path,
            "branch": branch_name,
            "source_branch": source_branch or "current",
            "checked_out": checkout,
            "message": f"成功创建分支: {branch_name}"
        })
    
    def list_branches(self, repo_path: str, remote: bool = False) -> Dict:
        """
        列出仓库分支
        
        Args:
            repo_path: 本地仓库路径
            remote: 是否列出远程分支
        """
        if not os.path.exists(repo_path):
            return self._format_error(f"仓库路径不存在: {repo_path}")
        
        # 检查是否是git仓库
        git_check = self._run_git_command(repo_path, ["rev-parse", "--git-dir"])
        if not git_check["success"]:
            return self._format_error(f"路径不是有效的Git仓库: {repo_path}")
        
        cmd = ["branch"]
        if remote:
            cmd.append("-r")
        
        result = self._run_git_command(repo_path, cmd)
        
        if result["success"]:
            branches = []
            for line in result["stdout"].split("\n"):
                if line:
                    # 移除前导空格和*
                    branch = line.strip().replace("* ", "").strip()
                    is_current = "*" in line
                    branches.append({
                        "name": branch,
                        "current": is_current,
                        "remote": remote
                    })
            
            return self._format_result({
                "repository": repo_path,
                "branches": branches
            })
        else:
            return self._format_error(
                f"列出分支失败: {result.get('stderr') or result.get('error')}"
            )
    
    def get_status(self, repo_path: str) -> Dict:
        """
        获取仓库状态
        
        Args:
            repo_path: 本地仓库路径
        """
        if not os.path.exists(repo_path):
            return self._format_error(f"仓库路径不存在: {repo_path}")
        
        # 检查是否是git仓库
        git_check = self._run_git_command(repo_path, ["rev-parse", "--git-dir"])
        if not git_check["success"]:
            return self._format_error(f"路径不是有效的Git仓库: {repo_path}")
        
        # 获取状态
        status_result = self._run_git_command(repo_path, ["status", "--porcelain"])
        
        # 获取当前分支
        branch_result = self._run_git_command(repo_path, ["branch", "--show-current"])
        current_branch = branch_result["stdout"] if branch_result["success"] else "unknown"
        
        # 解析状态
        changes = []
        if status_result["success"] and status_result["stdout"]:
            for line in status_result["stdout"].split("\n"):
                if line:
                    status_code = line[:2].strip()
                    file_path = line[3:].strip()
                    
                    # 解析状态码
                    if status_code == "M":
                        status = "modified"
                    elif status_code == "A":
                        status = "added"
                    elif status_code == "D":
                        status = "deleted"
                    elif status_code == "R":
                        status = "renamed"
                    elif status_code == "C":
                        status = "copied"
                    elif status_code == "U":
                        status = "updated"
                    elif status_code == "?":
                        status = "untracked"
                    else:
                        status = "changed"
                    
                    changes.append({
                        "file": file_path,
                        "status": status,
                        "code": line[:2]
                    })
        
        # 获取远程状态
        remote_result = self._run_git_command(
            repo_path, ["rev-list", "--count", "HEAD...@{u}", "--left-right"]
        )
        
        ahead_behind = {"ahead": 0, "behind": 0}
        if remote_result["success"] and remote_result["stdout"]:
            parts = remote_result["stdout"].strip().split("\t")
            if len(parts) == 2:
                ahead_behind["ahead"] = int(parts[0])
                ahead_behind["behind"] = int(parts[1])
        
        return self._format_result({
            "repository": repo_path,
            "branch": current_branch,
            "has_changes": len(changes) > 0,
            "changes": changes[:MAX_LIST_PREVIEW],  # 限制返回数量
            "total_changes": len(changes),
            "ahead_behind": ahead_behind
        })
    
    def delete_local_repo(self, repo_path: str, confirm: bool = False) -> Dict:
        """
        删除本地仓库
        
        Args:
            repo_path: 本地仓库路径
            confirm: 确认删除
        """
        if not confirm:
            return self._format_error(
                "需要确认删除操作",
                {"suggestion": "设置 confirm=True 以确认删除"}
            )
        
        if not os.path.exists(repo_path):
            return self._format_error(f"仓库路径不存在: {repo_path}")
        
        try:
            shutil.rmtree(repo_path)
            return self._format_result({
                "repository": repo_path,
                "message": "成功删除本地仓库"
            })
        except Exception as e:
            return self._format_error(f"删除失败: {str(e)}")
    
    def list_local_repos(self) -> Dict:
        """列出所有已克隆的本地仓库"""
        repos = []
        
        if os.path.exists(WORKSPACE_DIR):
            for item in os.listdir(WORKSPACE_DIR):
                item_path = os.path.join(WORKSPACE_DIR, item)
                git_dir = os.path.join(item_path, ".git")
                
                if os.path.isdir(item_path) and os.path.exists(git_dir):
                    # 获取远程URL
                    remote_result = self._run_git_command(
                        item_path, ["config", "--get", "remote.origin.url"]
                    )
                    
                    remote_url = remote_result["stdout"] if remote_result["success"] else "unknown"
                    
                    # 获取当前分支
                    branch_result = self._run_git_command(
                        item_path, ["branch", "--show-current"]
                    )
                    current_branch = branch_result["stdout"] if branch_result["success"] else "unknown"
                    
                    repos.append({
                        "name": item,
                        "path": item_path,
                        "remote_url": remote_url,
                        "current_branch": current_branch,
                        "last_modified": datetime.fromtimestamp(
                            os.path.getmtime(item_path)
                        ).isoformat()
                    })
        
        return self._format_result({
            "workspace": WORKSPACE_DIR,
            "repositories": repos
        })
    
    # ==================== 原有功能（保持兼容）====================
    
    def search_repositories(self, query: str, sort: str = "stars", 
                           order: str = "desc", per_page: int = DEFAULT_PER_PAGE, 
                           page: int = 1) -> Dict:
        """搜索GitHub代码仓库 - 支持分页"""
        per_page = min(per_page, MAX_PER_PAGE)
        
        url = f"{GITHUB_API_URL}/search/repositories"
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page,
            "page": page
        }
        
        result = self._make_request(url, params)
        
        if "error" in result:
            return self._format_error(result["error"])
        
        items = []
        for repo in result.get("items", []):
            items.append({
                "name": repo.get("full_name"),
                "description": self._truncate_string(repo.get("description", "无描述")),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language"),
                "updated_at": self._format_date_short(repo.get("updated_at")),
                "owner": repo.get("owner", {}).get("login"),
                "url": repo.get("html_url"),
                "clone_url": repo.get("clone_url"),
                "ssh_url": repo.get("ssh_url")
            })
        
        total_count = result.get("total_count", 0)
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        
        return self._format_result(
            data=items,
            summary=f"找到 {total_count} 个仓库，当前显示第 {page} 页（共 {total_pages} 页）"
        )
    
    def get_repository(self, repo_full_name: str, include_stats: bool = False) -> Dict:
        """获取GitHub仓库详细信息"""
        url = f"{GITHUB_API_URL}/repos/{repo_full_name}"
        repo = self._make_request(url)
        
        if "error" in repo:
            return self._format_error(repo["error"])
        
        result = {
            "name": repo.get("full_name"),
            "description": self._truncate_string(repo.get("description", "无描述")),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "watchers": repo.get("watchers_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "language": repo.get("language"),
            "created_at": self._format_date_short(repo.get("created_at")),
            "updated_at": self._format_date_short(repo.get("updated_at")),
            "license": repo.get("license", {}).get("name") if repo.get("license") else None,
            "default_branch": repo.get("default_branch", "main"),
            "homepage": repo.get("homepage"),
            "topics": repo.get("topics", [])[:5],
            "private": repo.get("private", False),
            "url": repo.get("html_url"),
            "clone_url": repo.get("clone_url"),
            "ssh_url": repo.get("ssh_url"),
            "has_wiki": repo.get("has_wiki", False),
            "size": repo.get("size", 0)
        }
        
        if include_stats:
            languages = self.get_languages(repo_full_name)
            if languages.get("success"):
                result["languages"] = languages["data"]
            
            readme = self.get_readme(repo_full_name, preview_only=True)
            if readme.get("success"):
                result["readme_preview"] = readme["data"].get("content_preview")
        
        return self._format_result(result)
    
    def get_readme(self, repo_full_name: str, branch: str = None, 
                  preview_only: bool = True, max_length: int = MAX_CONTENT_PREVIEW) -> Dict:
        """获取README文件"""
        url = f"{GITHUB_API_URL}/repos/{repo_full_name}/readme"
        params = {}
        if branch:
            params["ref"] = branch
        
        result = self._make_request(url, params)
        
        if "error" in result:
            return self._format_error(f"无法获取README: {result.get('error')}")
        
        content = result.get("content", "")
        if not content:
            return self._format_error("README内容为空")
        
        try:
            content = content.replace("\n", "")
            decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
            
            if preview_only:
                return self._format_result({
                    "name": result.get("name"),
                    "content_preview": decoded[:max_length] + "..." if len(decoded) > max_length else decoded,
                    "size": result.get("size", 0),
                    "full_content_available": len(decoded) > max_length
                })
            else:
                return self._format_result({
                    "name": result.get("name"),
                    "content": decoded,
                    "size": result.get("size", 0)
                })
                
        except Exception as e:
            return self._format_error(f"README内容解码失败: {str(e)}")
    
    def search_code(self, query: str, repo: str = None, path: str = None,
                   language: str = None, extension: str = None,
                   per_page: int = DEFAULT_PER_PAGE, page: int = 1) -> Dict:
        """搜索代码内容"""
        per_page = min(per_page, MAX_PER_PAGE)
        
        url = f"{GITHUB_API_URL}/search/code"
        
        q = query
        if repo:
            q += f" repo:{repo}"
        if path:
            q += f" path:{path}"
        if language:
            q += f" language:{language}"
        if extension:
            q += f" extension:{extension}"
        
        params = {
            "q": q,
            "per_page": per_page,
            "page": page
        }
        
        result = self._make_request(url, params)
        
        if "error" in result:
            return self._format_error(result["error"])
        
        items = []
        for item in result.get("items", []):
            items.append({
                "name": item.get("name"),
                "path": item.get("path"),
                "repository": item.get("repository", {}).get("full_name"),
                "url": item.get("html_url")
            })
        
        total_count = result.get("total_count", 0)
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        
        return self._format_result(
            data=items,
            summary=f"找到 {total_count} 个文件，当前显示第 {page} 页（共 {total_pages} 页）"
        )
    
    def list_contents(self, repo_full_name: str, path: str = "", 
                     branch: str = None, max_items: int = MAX_LIST_PREVIEW) -> Dict:
        """列出目录内容"""
        url = f"{GITHUB_API_URL}/repos/{repo_full_name}/contents/{path}"
        params = {}
        if branch:
            params["ref"] = branch
        
        result = self._make_request(url, params)
        
        if "error" in result:
            return self._format_error(result["error"])
        
        if isinstance(result, dict) and result.get("type") == "file":
            content = result.get("content", "")
            if content:
                try:
                    content = content.replace("\n", "")
                    decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                    return self._format_result({
                        "type": "file",
                        "name": result.get("name"),
                        "path": result.get("path"),
                        "size": result.get("size", 0),
                        "content_preview": decoded[:MAX_CONTENT_PREVIEW] + "..." if len(decoded) > MAX_CONTENT_PREVIEW else decoded
                    })
                except Exception as e:
                    return self._format_error(f"文件内容解码失败: {str(e)}")
        
        items = []
        for item in result[:max_items]:
            items.append({
                "name": item.get("name"),
                "type": item.get("type"),
                "path": item.get("path"),
                "size": item.get("size") if item.get("type") == "file" else None
            })
        
        result_data = {
            "type": "dir",
            "path": path,
            "total_items": len(result),
            "items": items
        }
        
        if len(result) > max_items:
            result_data["note"] = f"显示前 {max_items} 个项目"
        
        return self._format_result(result_data)
    
    def get_file_content(self, repo_full_name: str, file_path: str,
                        branch: str = None, preview: bool = True) -> Dict:
        """获取文件内容"""
        result = self.list_contents(repo_full_name, file_path, branch)
        return result
    
    def get_issues(self, repo_full_name: str, state: str = "open",
                  sort: str = "updated", direction: str = "desc",
                  labels: List[str] = None, since: str = None,
                  per_page: int = DEFAULT_PER_PAGE, page: int = 1) -> Dict:
        """获取Issues列表"""
        per_page = min(per_page, MAX_PER_PAGE)
        
        url = f"{GITHUB_API_URL}/repos/{repo_full_name}/issues"
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
            "page": page
        }
        
        if labels:
            params["labels"] = ",".join(labels)
        if since:
            params["since"] = since
        
        result = self._make_request(url, params)
        
        if "error" in result:
            return self._format_error(result["error"])
        
        items = []
        for issue in result:
            if "pull_request" in issue:
                continue
            
            items.append({
                "number": issue.get("number"),
                "title": self._truncate_string(issue.get("title")),
                "state": issue.get("state"),
                "user": issue.get("user", {}).get("login"),
                "created_at": self._format_date_short(issue.get("created_at")),
                "comments": issue.get("comments", 0),
                "labels": [label.get("name") for label in issue.get("labels", [])[:3]],
                "url": issue.get("html_url")
            })
        
        return self._format_result(
            data=items,
            summary=f"第 {page} 页，共 {len(items)} 个Issues"
        )
    
    def get_pull_requests(self, repo_full_name: str, state: str = "open",
                         sort: str = "updated", direction: str = "desc",
                         per_page: int = DEFAULT_PER_PAGE, page: int = 1) -> Dict:
        """获取Pull Requests列表"""
        per_page = min(per_page, MAX_PER_PAGE)
        
        url = f"{GITHUB_API_URL}/repos/{repo_full_name}/pulls"
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
            "page": page
        }
        
        result = self._make_request(url, params)
        
        if "error" in result:
            return self._format_error(result["error"])
        
        items = []
        for pr in result:
            items.append({
                "number": pr.get("number"),
                "title": self._truncate_string(pr.get("title")),
                "state": pr.get("state"),
                "user": pr.get("user", {}).get("login"),
                "created_at": self._format_date_short(pr.get("created_at")),
                "comments": pr.get("comments", 0),
                "commits": pr.get("commits", 0),
                "changed_files": pr.get("changed_files", 0),
                "url": pr.get("html_url")
            })
        
        return self._format_result(
            data=items,
            summary=f"第 {page} 页，共 {len(items)} 个PR"
        )
    
    def get_languages(self, repo_full_name: str, limit: int = 5) -> Dict:
        """获取语言统计"""
        url = f"{GITHUB_API_URL}/repos/{repo_full_name}/languages"
        result = self._make_request(url)
        
        if "error" in result:
            return self._format_error(result["error"])
        
        total_bytes = sum(result.values())
        
        items = []
        for lang, bytes_count in list(result.items())[:limit]:
            percentage = (bytes_count / total_bytes) * 100 if total_bytes > 0 else 0
            items.append({
                "language": lang,
                "percentage": round(percentage, 1)
            })
        
        return self._format_result(items)
    
    def get_rate_limit(self) -> Dict:
        """获取速率限制状态"""
        url = f"{GITHUB_API_URL}/rate_limit"
        result = self._make_request(url)
        
        if "error" in result:
            return self._format_error(result["error"])
        
        resources = result.get("resources", {})
        core = resources.get("core", {})
        search = resources.get("search", {})
        
        return self._format_result({
            "core": {
                "limit": core.get("limit"),
                "remaining": core.get("remaining"),
                "reset": self._format_timestamp(core.get("reset"))
            },
            "search": {
                "limit": search.get("limit"),
                "remaining": search.get("remaining"),
                "reset": self._format_timestamp(search.get("reset"))
            }
        })
    
    def _format_date_short(self, date_str: Optional[str]) -> Optional[str]:
        """格式化短日期"""
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d")
        except:
            return date_str
    
    def _format_timestamp(self, timestamp: Optional[int]) -> Optional[str]:
        """格式化时间戳"""
        if not timestamp:
            return None
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(timestamp)


# ==================== 工具接口实现 ====================

def print_description():
    """打印工具描述"""
    description = """GitHub 搜索和访问工具（增强版）

功能特性：
1. 搜索GitHub代码仓库（支持分页）
2. 获取仓库详细信息（支持按需加载）
3. 查看README文件（支持预览模式）
4. 搜索代码内容（支持分页）
5. 浏览仓库目录结构
6. 查看文件内容（支持预览）
7. 获取Issues列表（支持分页）
8. 获取Pull Requests列表（支持分页）
9. 获取语言统计
10. 获取贡献者列表（支持分页）
11. 获取Releases信息（支持分页）
12. 查看API速率限制状态
13. 克隆仓库 - clone_repository
14. 拉取更新 - pull_repository
15. 推送代码 - push_repository
16. 提交更改 - commit_changes
17. 创建分支 - create_branch
18. 列出分支 - list_branches
19. 查看状态 - get_status
20. 列出本地仓库 - list_local_repos

21. 删除本地仓库 - delete_local_repo


环境变量配置：
- GITHUB_TOKEN: GitHub访问令牌（必需用于推送操作）
- GIT_USER_NAME: Git用户名（默认: "AI Assistant"）
- GIT_USER_EMAIL: Git邮箱（默认: "ai@assistant.com"）
- GIT_WORKSPACE: 工作目录（默认: ~/.aibox/git_workspace）
"""
    print(description)


def print_parameters():
    """打印参数定义（JSON Schema格式）"""
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": [
                    # 搜索功能
                    "search_repos", "get_repo", "get_readme", "search_code",
                    "list_contents", "get_file", "get_issues", "get_pulls",
                    "get_languages", "get_rate_limit",
                    
                    # Git操作（新增）
                    "clone_repository", "pull_repository", "push_repository",
                    "commit_changes", "create_branch", "list_branches",
                    "get_status", "list_local_repos", "delete_local_repo"
                ]
            },
            
            # 原有参数
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "repo": {
                "type": "string",
                "description": "仓库全名，格式：owner/repo"
            },
            "file": {
                "type": "string",
                "description": "文件路径"
            },
            "path": {
                "type": "string",
                "description": "目录路径"
            },
            "branch": {
                "type": "string",
                "description": "分支名"
            },
            "language": {
                "type": "string",
                "description": "编程语言"
            },
            "per_page": {
                "type": "integer",
                "description": "每页数量（最大10）",
                "minimum": 1,
                "maximum": 10,
                "default": 5
            },
            "page": {
                "type": "integer",
                "description": "页码",
                "minimum": 1,
                "default": 1
            },
            
            # Git操作参数
            "repo_path": {
                "type": "string",
                "description": "本地仓库路径"
            },
            "target_dir": {
                "type": "string",
                "description": "克隆目标目录"
            },
            "depth": {
                "type": "integer",
                "description": "克隆深度（1=浅克隆，0=完整克隆）",
                "default": 1
            },
            "message": {
                "type": "string",
                "description": "提交消息"
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要提交的文件列表"
            },
            "all_files": {
                "type": "boolean",
                "description": "是否提交所有更改（包括新文件）",
                "default": False
            },
            "branch_name": {
                "type": "string",
                "description": "新分支名称"
            },
            "source_branch": {
                "type": "string",
                "description": "源分支"
            },
            "checkout": {
                "type": "boolean",
                "description": "创建后是否切换到新分支",
                "default": True
            },
            "remote": {
                "type": "boolean",
                "description": "是否列出远程分支",
                "default": False
            },
            "force": {
                "type": "boolean",
                "description": "是否强制推送",
                "default": False
            },
            "set_upstream": {
                "type": "boolean",
                "description": "是否设置上游分支",
                "default": False
            },
            "rebase": {
                "type": "boolean",
                "description": "拉取时是否使用rebase",
                "default": False
            },
            "confirm": {
                "type": "boolean",
                "description": "确认删除操作",
                "default": False
            }
        },
        "required": ["action"]
    }
    print(json.dumps(parameters, indent=2, ensure_ascii=False))


def execute_action(args_json: str):
    """执行工具操作"""
    try:
        params = json.loads(args_json)
    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "error": f"参数解析失败: {str(e)}"
        }, ensure_ascii=False))
        return
    
    action = params.get("action")
    if not action:
        print(json.dumps({
            "success": False,
            "error": "缺少 action 参数"
        }, ensure_ascii=False))
        return
    
    tool = GitHubTool()
    
    try:
        result = None
        
        # 原有功能
        if action == "search_repos":
            result = tool.search_repositories(
                query=params.get("query", ""),
                sort=params.get("sort", "stars"),
                per_page=params.get("per_page", DEFAULT_PER_PAGE),
                page=params.get("page", 1)
            )
        elif action == "get_repo":
            result = tool.get_repository(
                repo_full_name=params.get("repo", ""),
                include_stats=params.get("include_stats", False)
            )
        elif action == "get_readme":
            result = tool.get_readme(
                repo_full_name=params.get("repo", ""),
                branch=params.get("branch"),
                preview_only=params.get("preview_only", True)
            )
        elif action == "search_code":
            result = tool.search_code(
                query=params.get("query", ""),
                repo=params.get("repo"),
                language=params.get("language"),
                per_page=params.get("per_page", DEFAULT_PER_PAGE),
                page=params.get("page", 1)
            )
        elif action == "list_contents":
            result = tool.list_contents(
                repo_full_name=params.get("repo", ""),
                path=params.get("path", "")
            )
        elif action == "get_file":
            result = tool.get_file_content(
                repo_full_name=params.get("repo", ""),
                file_path=params.get("file", "")
            )
        elif action == "get_issues":
            result = tool.get_issues(
                repo_full_name=params.get("repo", ""),
                per_page=params.get("per_page", DEFAULT_PER_PAGE),
                page=params.get("page", 1)
            )
        elif action == "get_pulls":
            result = tool.get_pull_requests(
                repo_full_name=params.get("repo", ""),
                per_page=params.get("per_page", DEFAULT_PER_PAGE),
                page=params.get("page", 1)
            )
        elif action == "get_languages":
            result = tool.get_languages(params.get("repo", ""))
        elif action == "get_rate_limit":
            result = tool.get_rate_limit()
        
        # 新增Git操作
        elif action == "clone_repository":
            result = tool.clone_repository(
                repo_full_name=params.get("repo", ""),
                branch=params.get("branch"),
                target_dir=params.get("target_dir"),
                depth=params.get("depth", 1)
            )
        elif action == "pull_repository":
            result = tool.pull_repository(
                repo_path=params.get("repo_path", ""),
                branch=params.get("branch"),
                rebase=params.get("rebase", False)
            )
        elif action == "push_repository":
            result = tool.push_repository(
                repo_path=params.get("repo_path", ""),
                branch=params.get("branch"),
                force=params.get("force", False),
                set_upstream=params.get("set_upstream", False)
            )
        elif action == "commit_changes":
            result = tool.commit_changes(
                repo_path=params.get("repo_path", ""),
                message=params.get("message", ""),
                files=params.get("files"),
                all_files=params.get("all_files", False)
            )
        elif action == "create_branch":
            result = tool.create_branch(
                repo_path=params.get("repo_path", ""),
                branch_name=params.get("branch_name", ""),
                source_branch=params.get("source_branch"),
                checkout=params.get("checkout", True)
            )
        elif action == "list_branches":
            result = tool.list_branches(
                repo_path=params.get("repo_path", ""),
                remote=params.get("remote", False)
            )
        elif action == "get_status":
            result = tool.get_status(
                repo_path=params.get("repo_path", "")
            )
        elif action == "list_local_repos":
            result = tool.list_local_repos()
        elif action == "delete_local_repo":
            result = tool.delete_local_repo(
                repo_path=params.get("repo_path", ""),
                confirm=params.get("confirm", False)
            )
        else:
            result = {
                "success": False,
                "error": f"未知操作: {action}"
            }
        
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"执行错误: {str(e)}"
        }, ensure_ascii=False))


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='GitHub搜索和访问工具（增强版）')
    parser.add_argument('--description', action='store_true', help='显示工具描述')
    parser.add_argument('--parameters', action='store_true', help='显示参数定义')
    parser.add_argument('--execute', action='store_true', help='执行工具')
    parser.add_argument('--args', type=str, help='JSON格式的参数')
    
    args = parser.parse_args()
    
    if args.description:
        print_description()
    elif args.parameters:
        print_parameters()
    elif args.execute:
        if not args.args:
            print(json.dumps({
                "success": False,
                "error": "缺少 --args 参数"
            }, ensure_ascii=False))
            sys.exit(1)
        execute_action(args.args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()