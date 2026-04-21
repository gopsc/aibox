#!/usr/bin/env python3
"""截图工具 - 截取计算机桌面并保存。"""

import argparse
import os
import sys
import time
import platform
import subprocess
from datetime import datetime

# ==================== 配置常量 ====================

SCREENSHOT_DIR = os.path.expanduser("~/.aibox/screenshot")
SUPPORTED_SYSTEMS = ['Windows', 'Linux', 'Darwin']


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


# ==================== 各平台截图实现 ====================

def take_screenshot_windows(output_path, delay=0):
    """Windows平台截图"""
    if delay > 0:
        time.sleep(delay)
    
    try:
        ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bounds = $screen.Bounds

$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size)

$bitmap.Save("{output_path}", [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()

Write-Output "截图已保存: {output_path}"
'''
        
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


def take_screenshot_linux(output_path, delay=0):
    """Linux平台截图"""
    if delay > 0:
        time.sleep(delay)
    
    tools = []
    
    if subprocess.run(["which", "scrot"], capture_output=True).returncode == 0:
        tools.append(("scrot", ["scrot", "-z", output_path]))
    
    if subprocess.run(["which", "gnome-screenshot"], capture_output=True).returncode == 0:
        tools.append(("gnome-screenshot", ["gnome-screenshot", "-f", output_path]))
    
    if subprocess.run(["which", "import"], capture_output=True).returncode == 0:
        tools.append(("import", ["import", "-window", "root", output_path]))
    
    if not tools:
        return False, "未找到截图工具，请安装 scrot, gnome-screenshot 或 ImageMagick"
    
    for tool_name, cmd in tools:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and os.path.exists(output_path):
                return True, f"截图成功 (使用 {tool_name}): {output_path}"
        except:
            continue
    
    return False, "所有截图工具都失败了"


def take_screenshot_macos(output_path, delay=0):
    """macOS平台截图"""
    if delay > 0:
        time.sleep(delay)
    
    try:
        if subprocess.run(["which", "screencapture"], capture_output=True).returncode != 0:
            return False, "未找到 screencapture 命令"
        
        cmd = ["screencapture", "-x", output_path]
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

def take_screenshot(output_dir=None, filename=None, delay=0):
    """截取屏幕截图"""
    system = get_system()
    
    if system not in SUPPORTED_SYSTEMS:
        return False, f"不支持的操作系统: {system}，支持的系统: {', '.join(SUPPORTED_SYSTEMS)}", None
    
    if output_dir:
        save_dir = output_dir
    else:
        save_dir = ensure_screenshot_dir()
    
    os.makedirs(save_dir, exist_ok=True)
    
    if filename:
        filepath = os.path.join(save_dir, filename)
    else:
        filepath = os.path.join(save_dir, get_timestamp_filename())
    
    if system == 'Windows':
        success, message = take_screenshot_windows(filepath, delay)
    elif system == 'Linux':
        success, message = take_screenshot_linux(filepath, delay)
    elif system == 'Darwin':
        success, message = take_screenshot_macos(filepath, delay)
    else:
        return False, f"不支持的操作系统: {system}", None
    
    if success:
        return True, message, filepath
    else:
        return False, message, None


def list_recent_screenshots(limit=10):
    """列出最近的截图文件"""
    save_dir = ensure_screenshot_dir()
    
    if not os.path.exists(save_dir):
        return f"截图目录不存在: {save_dir}"
    
    screenshots = []
    for f in os.listdir(save_dir):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            filepath = os.path.join(save_dir, f)
            mtime = os.path.getmtime(filepath)
            size = os.path.getsize(filepath)
            screenshots.append((mtime, f, size))
    
    screenshots.sort(reverse=True)
    
    if not screenshots:
        return f"截图目录中没有截图文件: {save_dir}"
    
    result = [f"📸 最近的截图 (共 {len(screenshots)} 个):"]
    for i, (mtime, fname, size) in enumerate(screenshots[:limit], 1):
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        
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


# ==================== 命令行接口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="截图工具 - 截取计算机桌面并保存。",
        epilog="""
使用示例:
  # 立即截图（自动生成文件名）
  screenshot

  # 3秒后截图
  screenshot --delay 3

  # 截图并指定文件名
  screenshot --filename "my_screenshot.png"

  # 截图并保存到指定目录
  screenshot --output-dir "~/Desktop"

  # 列出最近的截图
  screenshot --list --limit 5

  # 5秒后截图并保存到桌面
  screenshot --delay 5 --output-dir "~/Desktop"

截图保存位置:
  ~/.aibox/screenshot/
  自动命名格式: screenshot_YYYYMMDD_HHMMSS.png

支持的截图工具:
  Linux:   scrot, gnome-screenshot, ImageMagick
  macOS:   screencapture (系统自带)
  Windows: PowerShell .NET (系统自带)
        """
    )
    
    parser.add_argument("--output-dir", "-o", help="截图保存目录（默认: ~/.aibox/screenshot/）")
    parser.add_argument("--filename", "-f", help="文件名（默认: 自动生成时间戳文件名）")
    parser.add_argument("--delay", "-d", type=int, default=0, help="延迟秒数（默认: 0）")
    parser.add_argument("--list", "-l", action="store_true", help="列出最近的截图文件")
    parser.add_argument("--limit", "-n", type=int, default=10, help="列出截图时的数量限制（默认: 10）")
    
    args = parser.parse_args()
    
    # 列出截图
    if args.list:
        print(list_recent_screenshots(args.limit))
        return
    
    # 执行截图
    try:
        success, message, filepath = take_screenshot(
            output_dir=args.output_dir,
            filename=args.filename,
            delay=args.delay
        )
        
        if success:
            print(f"✅ {message}")
            
            if filepath and os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                if file_size < 1024:
                    size_str = f"{file_size}B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size/1024:.1f}KB"
                else:
                    size_str = f"{file_size/1024/1024:.1f}MB"
                print(f"📦 文件大小: {size_str}")
            
            # 显示目录中的截图总数
            save_dir = args.output_dir if args.output_dir else SCREENSHOT_DIR
            save_dir = os.path.expanduser(save_dir)
            if os.path.exists(save_dir):
                screenshots = [f for f in os.listdir(save_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                print(f"📁 该目录共有 {len(screenshots)} 张截图")
        else:
            print(f"❌ {message}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 执行错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()