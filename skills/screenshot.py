#!/usr/bin/env python3
"""
截图工具 - 截取计算机桌面并保存
支持：截取整个屏幕、截取特定窗口、延迟截图
保存路径：~/.aibox/screenshot/ 以时间字符串命名的文件

# 方法1: 安装 scrot（推荐）
sudo apt-get install scrot  # Debian/Ubuntu
# 或
sudo yum install scrot      # CentOS/RHEL

# 方法2: 安装 gnome-screenshot
sudo apt-get install gnome-screenshot

# 方法3: 安装 ImageMagick
sudo apt-get install imagemagick
"""

import argparse
import json
import os
import sys
import time
import platform
import subprocess
from datetime import datetime
from pathlib import Path

# ==================== 配置常量 ====================

# 截图保存目录
SCREENSHOT_DIR = os.path.expanduser("~/.aibox/screenshot")

# 支持的操作系统
SUPPORTED_SYSTEMS = ['Windows', 'Linux', 'Darwin']  # Darwin 是 macOS

# ==================== 辅助函数 ====================

def ensure_screenshot_dir():
    """确保截图目录存在"""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    return SCREENSHOT_DIR

def get_timestamp_filename(prefix="screenshot", extension="png"):
    """生成基于时间戳的文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"

def get_system():
    """获取当前操作系统"""
    return platform.system()

def check_system_support():
    """检查当前操作系统是否支持"""
    system = get_system()
    if system not in SUPPORTED_SYSTEMS:
        return False, f"不支持的操作系统: {system}，支持的系统: {', '.join(SUPPORTED_SYSTEMS)}"
    return True, system

# ==================== 各平台截图实现 ====================

def take_screenshot_windows(output_path, delay=0, window_title=None):
    """
    Windows平台截图
    使用 PowerShell 的 .NET 方法
    """
    if delay > 0:
        time.sleep(delay)
    
    try:
        # PowerShell 脚本 - 截取屏幕
        ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bounds = $screen.Bounds

$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size)

# 如果有窗口标题，尝试截取特定窗口（简化版，实际需要更复杂的Win32 API）
# 这里简化处理，仍然截取全屏

$bitmap.Save("{output_path}", [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()

Write-Output "截图已保存: {output_path}"
'''
        
        # 执行 PowerShell 脚本
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            return True, f"截图成功: {output_path}"
        else:
            error_msg = result.stderr if result.stderr else "未知错误"
            return False, f"截图失败: {error_msg}"
            
    except subprocess.TimeoutExpired:
        return False, "截图超时"
    except Exception as e:
        return False, f"截图错误: {str(e)}"

def take_screenshot_linux(output_path, delay=0, window_title=None):
    """
    Linux平台截图
    尝试多种截图工具: scrot, gnome-screenshot, import (ImageMagick)
    """
    if delay > 0:
        time.sleep(delay)
    
    # 检查可用的截图工具
    tools = []
    
    # 检查 scrot
    if subprocess.run(["which", "scrot"], capture_output=True).returncode == 0:
        tools.append(("scrot", ["scrot", "-z", output_path]))
    
    # 检查 gnome-screenshot
    if subprocess.run(["which", "gnome-screenshot"], capture_output=True).returncode == 0:
        tools.append(("gnome-screenshot", ["gnome-screenshot", "-f", output_path]))
    
    # 检查 import (ImageMagick)
    if subprocess.run(["which", "import"], capture_output=True).returncode == 0:
        tools.append(("import", ["import", "-window", "root", output_path]))
    
    if not tools:
        return False, "未找到截图工具，请安装 scrot, gnome-screenshot 或 ImageMagick"
    
    # 尝试每个工具
    for tool_name, cmd in tools:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and os.path.exists(output_path):
                return True, f"截图成功 (使用 {tool_name}): {output_path}"
        except:
            continue
    
    return False, "所有截图工具都失败了"

def take_screenshot_macos(output_path, delay=0, window_title=None):
    """
    macOS平台截图
    使用 screencapture 命令
    """
    if delay > 0:
        time.sleep(delay)
    
    try:
        # 检查 screencapture 命令
        if subprocess.run(["which", "screencapture"], capture_output=True).returncode != 0:
            return False, "未找到 screencapture 命令"
        
        # 构建命令
        cmd = ["screencapture"]
        
        # 如果有窗口标题，尝试截取特定窗口
        if window_title:
            # 注意：screencapture 的窗口选择比较复杂，这里简化处理
            # 实际可能需要使用 -l 参数和窗口ID
            cmd.extend(["-w"])  # 允许选择窗口
        
        # 静音模式
        cmd.append("-x")
        
        # 输出文件
        cmd.append(output_path)
        
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            return True, f"截图成功: {output_path}"
        else:
            error_msg = result.stderr if result.stderr else "未知错误"
            return False, f"截图失败: {error_msg}"
            
    except subprocess.TimeoutExpired:
        return False, "截图超时"
    except Exception as e:
        return False, f"截图错误: {str(e)}"

# ==================== 截图函数 ====================

def take_screenshot(output_dir=None, filename=None, delay=0, window_title=None):
    """
    截取屏幕截图
    
    Args:
        output_dir: 输出目录，默认使用 SCREENSHOT_DIR
        filename: 文件名，默认使用时间戳
        delay: 延迟秒数
        window_title: 要截取的窗口标题（如果支持）
    
    Returns:
        (success, message, filepath)
    """
    # 检查系统支持
    supported, system = check_system_support()
    if not supported:
        return False, system, None
    
    # 确定输出目录
    if output_dir:
        save_dir = output_dir
    else:
        save_dir = ensure_screenshot_dir()
    
    # 确定文件名
    if filename:
        filepath = os.path.join(save_dir, filename)
    else:
        filepath = os.path.join(save_dir, get_timestamp_filename())
    
    # 根据系统选择截图方法
    if system == 'Windows':
        success, message = take_screenshot_windows(filepath, delay, window_title)
    elif system == 'Linux':
        success, message = take_screenshot_linux(filepath, delay, window_title)
    elif system == 'Darwin':  # macOS
        success, message = take_screenshot_macos(filepath, delay, window_title)
    else:
        return False, f"不支持的操作系统: {system}", None
    
    if success:
        return True, message, filepath
    else:
        return False, message, None

# ==================== 命令行接口 ====================

def cmd_description():
    """输出工具描述"""
    description = """截图工具 - 截取计算机桌面并保存

功能：
- 截取整个屏幕
- 支持延迟截图
- 支持指定窗口（部分平台）
- 自动保存在 ~/.aibox/screenshot/ 目录
- 文件名自动添加时间戳

参数说明：
- output_dir: 输出目录（可选，默认 ~/.aibox/screenshot/）
- filename: 文件名（可选，默认自动生成时间戳文件名）
- delay: 延迟秒数（可选，默认0）
- window_title: 要截取的窗口标题（可选，部分平台支持）

示例：
{"output_dir": "~/Desktop", "delay": 3}  # 3秒后截图保存到桌面
{"filename": "test.png"}  # 立即截图保存为 test.png
{"delay": 5, "window_title": "浏览器"}  # 5秒后尝试截取浏览器窗口
"""
    return description

def cmd_parameters():
    """输出参数定义（JSON Schema格式）"""
    parameters = {
        "type": "object",
        "properties": {
            "output_dir": {
                "type": "string",
                "description": "截图保存目录，默认 ~/.aibox/screenshot/"
            },
            "filename": {
                "type": "string",
                "description": "文件名，默认自动生成时间戳文件名"
            },
            "delay": {
                "type": "integer",
                "description": "延迟秒数，截图前等待的时间",
                "default": 0,
                "minimum": 0,
                "maximum": 60
            },
            "window_title": {
                "type": "string",
                "description": "要截取的窗口标题（部分平台支持，Linux/macOS可能有效）"
            },
            "list_screenshots": {
                "type": "boolean",
                "description": "列出最近的截图文件",
                "default": False
            },
            "limit": {
                "type": "integer",
                "description": "列出截图时的数量限制",
                "default": 10,
                "minimum": 1,
                "maximum": 100
            }
        }
    }
    return parameters

def list_recent_screenshots(limit=10):
    """列出最近的截图文件"""
    save_dir = ensure_screenshot_dir()
    
    if not os.path.exists(save_dir):
        return f"截图目录不存在: {save_dir}"
    
    # 获取所有截图文件
    screenshots = []
    for f in os.listdir(save_dir):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            filepath = os.path.join(save_dir, f)
            mtime = os.path.getmtime(filepath)
            size = os.path.getsize(filepath)
            screenshots.append((mtime, f, size))
    
    # 按修改时间排序（最新的在前）
    screenshots.sort(reverse=True)
    
    if not screenshots:
        return f"截图目录中没有截图文件: {save_dir}"
    
    result = [f"📸 最近的截图 (共 {len(screenshots)} 个):"]
    for i, (mtime, fname, size) in enumerate(screenshots[:limit], 1):
        # 格式化时间
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        # 格式化大小
        if size < 1024:
            size_str = f"{size}B"
        elif size < 1024 * 1024:
            size_str = f"{size/1024:.1f}KB"
        else:
            size_str = f"{size/1024/1024:.1f}MB"
        
        result.append(f"  {i}. {fname} - {dt} ({size_str})")
    
    if len(screenshots) > limit:
        result.append(f"  ... 还有 {len(screenshots) - limit} 个文件")
    
    return "\n".join(result)

def cmd_execute(args_json):
    """执行截图操作"""
    try:
        # 解析参数
        args = json.loads(args_json) if args_json else {}
        
        # 检查是否是列出截图
        if args.get("list_screenshots", False):
            limit = args.get("limit", 10)
            result = list_recent_screenshots(limit)
            return json.dumps({
                "success": True,
                "message": result
            }, ensure_ascii=False)
        
        # 截图参数
        output_dir = args.get("output_dir")
        filename = args.get("filename")
        delay = args.get("delay", 0)
        window_title = args.get("window_title")
        
        # 执行截图
        success, message, filepath = take_screenshot(
            output_dir=output_dir,
            filename=filename,
            delay=delay,
            window_title=window_title
        )
        
        if success:
            # 获取文件信息
            file_size = os.path.getsize(filepath) if filepath and os.path.exists(filepath) else 0
            
            # 获取截图目录中的文件列表（用于上下文）
            save_dir = ensure_screenshot_dir()
            screenshots = [f for f in os.listdir(save_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            recent_count = len(screenshots)
            
            return json.dumps({
                "success": True,
                "message": message,
                "filepath": filepath,
                "filename": os.path.basename(filepath) if filepath else None,
                "file_size": file_size,
                "file_size_str": f"{file_size/1024:.1f}KB" if file_size > 0 else "0KB",
                "timestamp": datetime.now().isoformat(),
                "directory": save_dir,
                "total_screenshots": recent_count
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "success": False,
                "message": message
            }, ensure_ascii=False)
            
    except json.JSONDecodeError:
        return json.dumps({
            "success": False,
            "message": f"参数解析错误: {args_json}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"执行错误: {str(e)}"
        }, ensure_ascii=False)

# ==================== 主入口 ====================

def main():
    """主函数 - 处理命令行参数"""
    parser = argparse.ArgumentParser(description='截图工具')
    parser.add_argument('--description', action='store_true', help='输出工具描述')
    parser.add_argument('--parameters', action='store_true', help='输出参数定义')
    parser.add_argument('--execute', action='store_true', help='执行工具')
    parser.add_argument('--args', type=str, help='参数JSON字符串')
    
    args = parser.parse_args()
    
    if args.description:
        print(cmd_description())
    elif args.parameters:
        print(json.dumps(cmd_parameters(), ensure_ascii=False, indent=2))
    elif args.execute:
        result = cmd_execute(args.args)
        print(result)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()