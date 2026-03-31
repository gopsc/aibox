#!/usr/bin/env python3
"""
摄像头拍照工具
功能：获取相机设备列表、选择指定相机拍照、保存照片到 ~/.aibox/camera 目录
支持流式输出结果
"""

import os
import sys
import json
import argparse
from pathlib import Path
import cv2
import time
import re

# 定义默认的截图保存目录
CAMERA_DIR = os.path.expanduser("~/.aibox/camera")

def ensure_camera_dir():
    """确保摄像头照片保存目录存在"""
    os.makedirs(CAMERA_DIR, exist_ok=True)
    return CAMERA_DIR

def list_cameras(max_test=10):
    """列出可用的摄像头设备"""
    available_cameras = []
    
    for i in range(max_test):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # 获取摄像头信息
            ret, frame = cap.read()
            if ret:
                height, width = frame.shape[:2]
                # 尝试获取更详细的摄像头信息
                backend = cap.getBackendName()
                
                camera_info = {
                    "id": i,
                    "resolution": f"{width}x{height}",
                    "backend": backend,
                    "status": "可用"
                }
                
                # 在Linux系统上尝试获取设备路径
                if sys.platform.startswith('linux'):
                    dev_path = f"/dev/video{i}"
                    if os.path.exists(dev_path):
                        camera_info["device_path"] = dev_path
                        
                        # 尝试通过udevadm获取更多信息（如果有权限）
                        try:
                            import subprocess
                            result = subprocess.run(
                                ['udevadm', 'info', '--query=property', '--name', dev_path],
                                capture_output=True, text=True, timeout=2
                            )
                            if result.returncode == 0:
                                for line in result.stdout.split('\n'):
                                    if 'ID_MODEL=' in line:
                                        camera_info["model"] = line.split('=')[1].strip()
                                    elif 'ID_VENDOR=' in line:
                                        camera_info["vendor"] = line.split('=')[1].strip()
                        except:
                            pass
                
                available_cameras.append(camera_info)
            cap.release()
        else:
            cap.release()
    
    return available_cameras

def get_camera_info(camera_id):
    """获取指定摄像头的详细信息"""
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        return None
    
    info = {
        "id": camera_id,
        "properties": {}
    }
    
    # 获取各种摄像头属性
    properties = [
        (cv2.CAP_PROP_FRAME_WIDTH, "width"),
        (cv2.CAP_PROP_FRAME_HEIGHT, "height"),
        (cv2.CAP_PROP_FPS, "fps"),
        (cv2.CAP_PROP_BRIGHTNESS, "brightness"),
        (cv2.CAP_PROP_CONTRAST, "contrast"),
        (cv2.CAP_PROP_SATURATION, "saturation"),
        (cv2.CAP_PROP_HUE, "hue"),
        (cv2.CAP_PROP_GAIN, "gain"),
        (cv2.CAP_PROP_EXPOSURE, "exposure"),
        (cv2.CAP_PROP_FOCUS, "focus"),
        (cv2.CAP_PROP_AUTO_EXPOSURE, "auto_exposure"),
        (cv2.CAP_PROP_AUTO_WB, "auto_white_balance"),
        (cv2.CAP_PROP_WB_TEMPERATURE, "white_balance_temperature"),
    ]
    
    for prop_id, prop_name in properties:
        value = cap.get(prop_id)
        if value >= 0:  # OpenCV返回负数表示不支持该属性
            info["properties"][prop_name] = value
    
    # 测试读取一帧
    ret, frame = cap.read()
    if ret:
        height, width = frame.shape[:2]
        info["current_resolution"] = f"{width}x{height}"
        info["channels"] = frame.shape[2] if len(frame.shape) > 2 else 1
    
    cap.release()
    
    # 在Linux系统上添加设备路径
    if sys.platform.startswith('linux'):
        dev_path = f"/dev/video{camera_id}"
        if os.path.exists(dev_path):
            info["device_path"] = dev_path
    
    return info

def capture_photo(camera_id=0, save_path=None, resolution=None, wait_time=1):
    """
    调用指定摄像头拍照
    
    Args:
        camera_id: 摄像头ID（默认0）
        save_path: 保存路径（None时自动生成到默认目录）
        resolution: 分辨率设置，如"1920x1080"（None时使用默认）
        wait_time: 等待摄像头预热的时间（秒）
    
    Returns:
        (保存路径, 错误信息, 宽度, 高度)
    """
    # 初始化摄像头
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        return None, f"无法打开摄像头 #{camera_id}，请检查摄像头连接", None, None
    
    # 如果指定了分辨率，尝试设置
    if resolution:
        try:
            width, height = map(int, resolution.lower().replace('x', ' ').split())
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        except:
            pass  # 分辨率格式错误时忽略
    
    # 等待摄像头预热，让自动曝光等稳定下来
    time.sleep(wait_time)
    
    # 丢弃前几帧，让摄像头适应光线
    for _ in range(5):
        cap.read()
    
    # 拍照
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return None, "拍照失败，无法获取图像帧", None, None
    
    # 获取实际的分辨率
    actual_height, actual_width = frame.shape[:2]
    
    # 确定保存路径
    if save_path is None:
        # 如果没有指定路径，使用默认目录和自动生成的文件名
        ensure_camera_dir()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"camera_{camera_id}_{timestamp}.jpg"
        save_path = os.path.join(CAMERA_DIR, filename)
    else:
        # 如果指定了路径，确保目录存在
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
    
    # 确保路径有扩展名
    if not os.path.splitext(save_path)[1]:
        save_path += '.jpg'
    
    # 保存图片
    cv2.imwrite(save_path, frame)
    return save_path, None, actual_width, actual_height

def format_camera_list(cameras):
    """格式化相机列表输出"""
    if not cameras:
        return "❌ 未找到可用的摄像头设备"
    
    lines = ["📷 可用摄像头设备:"]
    for cam in cameras:
        model_info = ""
        if "model" in cam:
            model_info = f" ({cam.get('vendor', '')} {cam['model']})".strip()
        
        dev_path = cam.get("device_path", f"Camera #{cam['id']}")
        lines.append(f"  [{cam['id']}] {dev_path}{model_info}")
        lines.append(f"      分辨率: {cam['resolution']}, 后端: {cam['backend']}")
    
    return "\n".join(lines)

def list_recent_photos(limit=10):
    """列出最近的摄像头照片"""
    ensure_camera_dir()
    
    if not os.path.exists(CAMERA_DIR):
        return f"摄像头照片目录不存在: {CAMERA_DIR}"
    
    # 获取所有图片文件
    photos = []
    for f in os.listdir(CAMERA_DIR):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
            filepath = os.path.join(CAMERA_DIR, f)
            mtime = os.path.getmtime(filepath)
            size = os.path.getsize(filepath)
            photos.append((mtime, f, size))
    
    # 按修改时间排序（最新的在前）
    photos.sort(reverse=True)
    
    if not photos:
        return f"摄像头照片目录中没有照片: {CAMERA_DIR}"
    
    result = [f"📸 最近的摄像头照片 (共 {len(photos)} 个):"]
    for i, (mtime, fname, size) in enumerate(photos[:limit], 1):
        # 格式化时间
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        
        # 格式化大小
        if size < 1024:
            size_str = f"{size}B"
        elif size < 1024 * 1024:
            size_str = f"{size/1024:.1f}KB"
        else:
            size_str = f"{size/1024/1024:.1f}MB"
        
        result.append(f"  {i}. {fname} - {dt} ({size_str})")
    
    if len(photos) > limit:
        result.append(f"  ... 还有 {len(photos) - limit} 个文件")
    
    return "\n".join(result)

def main():
    """主函数 - 处理命令行参数并执行"""
    parser = argparse.ArgumentParser(description='摄像头拍照工具')
    
    # 扩展工具必需的参数
    parser.add_argument('--description', action='store_true', 
                       help='返回工具描述')
    parser.add_argument('--parameters', action='store_true', 
                       help='返回工具参数定义（JSON格式）')
    parser.add_argument('--execute', action='store_true', 
                       help='执行工具')
    parser.add_argument('--args', type=str, 
                       help='执行参数（JSON格式）')
    
    args = parser.parse_args()
    
    # 处理 --description 参数
    if args.description:
        description = f"""摄像头拍照工具 - 获取相机设备列表、选择指定相机拍照、保存照片到指定位置

功能:
1. 列出所有可用的摄像头设备（使用list操作）
2. 查看指定摄像头的详细信息（使用info操作）
3. 使用指定摄像头拍照（使用capture操作）
4. 照片自动保存在 {CAMERA_DIR} 目录
5. 支持流式输出拍照进度
6. 支持列出最近的摄像头照片（使用list_photos操作）

需要安装: opencv-python

----------------
照片命名格式: camera_{{摄像头ID}}_{{时间戳}}.jpg
时间戳格式: YYYYMMDD_HHMMSS
"""
        print(description)
        return 0
    
    # 处理 --parameters 参数
    if args.parameters:
        parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["list", "info", "capture", "list_photos"]
                },
                "camera_id": {
                    "type": "integer",
                    "description": "摄像头ID（默认0）",
                    "default": 0
                },
                "resolution": {
                    "type": "string",
                    "description": "照片分辨率，格式：宽度x高度（如 1920x1080），不指定则使用摄像头默认"
                },
                "wait_time": {
                    "type": "number",
                    "description": "等待摄像头预热时间（秒，默认1秒）",
                    "default": 1
                },
                "filename": {
                    "type": "string",
                    "description": "自定义文件名（可选，不指定则自动生成时间戳文件名）"
                },
                "limit": {
                    "type": "integer",
                    "description": "列出照片时的数量限制（默认10）",
                    "default": 10
                },
                "stream": {
                    "type": "boolean",
                    "description": "是否流式输出进度信息",
                    "default": True
                }
            },
            "required": ["action"]
        }
        print(json.dumps(parameters, ensure_ascii=False))
        return 0
    
    # 处理 --execute 参数
    if args.execute and args.args:
        try:
            kwargs = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(f"❌ 参数解析错误: {e}")
            return 1
        
        action = kwargs.get("action")
        if not action:
            print("❌ 错误：缺少必需参数 'action'")
            return 1
        
        stream = kwargs.get("stream", True)
        
        # 流式输出处理
        def output_line(msg):
            if stream:
                print(msg, flush=True)
            else:
                # 非流式模式，收集到最终结果
                if not hasattr(output_line, 'lines'):
                    output_line.lines = []
                output_line.lines.append(msg)
        
        def get_final_output():
            if not stream and hasattr(output_line, 'lines'):
                return "\n".join(output_line.lines)
            return ""
        
        try:
            if action == "list":
                # 列出所有摄像头
                output_line("🔍 正在扫描摄像头设备...")
                cameras = list_cameras(10)
                result = format_camera_list(cameras)
                output_line(result)
                
                # 添加使用建议
                if cameras:
                    output_line("\n💡 使用建议:")
                    output_line(f"  要使用摄像头 #{cameras[0]['id']} 拍照，请执行 capture 操作")
                    output_line("  要查看摄像头详细信息，请执行 info 操作")
                
            elif action == "list_photos":
                # 列出最近的摄像头照片
                limit = kwargs.get("limit", 10)
                result = list_recent_photos(limit)
                output_line(result)
                
            elif action == "info":
                # 获取摄像头详细信息
                camera_id = kwargs.get("camera_id", 0)
                output_line(f"🔍 正在获取摄像头 #{camera_id} 的详细信息...")
                
                info = get_camera_info(camera_id)
                if not info:
                    output_line(f"❌ 无法打开摄像头 #{camera_id}，请检查设备是否存在")
                else:
                    output_line(f"📷 摄像头 #{camera_id} 详细信息:")
                    if "device_path" in info:
                        output_line(f"  设备路径: {info['device_path']}")
                    output_line(f"  当前分辨率: {info.get('current_resolution', '未知')}")
                    if "channels" in info:
                        output_line(f"  色彩通道: {info['channels']}")
                    
                    if info["properties"]:
                        output_line(f"\n  支持设置的属性:")
                        for name, value in info["properties"].items():
                            output_line(f"    {name}: {value}")
                    
                    output_line(f"\n💡 要拍照请执行 capture 操作")
                
            elif action == "capture":
                # 拍照
                camera_id = kwargs.get("camera_id", 0)
                filename = kwargs.get("filename")
                resolution = kwargs.get("resolution")
                wait_time = kwargs.get("wait_time", 1)
                
                # 确保保存目录存在
                ensure_camera_dir()
                
                # 确定保存路径
                if filename:
                    # 如果指定了文件名，使用指定文件名
                    save_path = os.path.join(CAMERA_DIR, filename)
                else:
                    # 否则自动生成带时间戳的文件名
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    save_path = os.path.join(CAMERA_DIR, f"camera_{camera_id}_{timestamp}.jpg")
                
                output_line(f"📸 正在使用摄像头 #{camera_id} 拍照...")
                if resolution:
                    output_line(f"  请求分辨率: {resolution}")
                output_line(f"  预热时间: {wait_time}秒")
                output_line(f"  保存目录: {CAMERA_DIR}")
                
                # 执行拍照
                image_path, error, width, height = capture_photo(
                    camera_id=camera_id,
                    save_path=save_path,
                    resolution=resolution,
                    wait_time=wait_time
                )
                
                if error:
                    output_line(f"❌ {error}")
                else:
                    output_line(f"✅ 拍照成功!")
                    output_line(f"  📷 实际分辨率: {width}x{height}")
                    output_line(f"  💾 保存路径: {image_path}")
                    
                    # 获取文件大小
                    if os.path.exists(image_path):
                        file_size = os.path.getsize(image_path)
                        if file_size < 1024:
                            size_str = f"{file_size}B"
                        elif file_size < 1024 * 1024:
                            size_str = f"{file_size/1024:.1f}KB"
                        else:
                            size_str = f"{file_size/1024/1024:.1f}MB"
                        output_line(f"  📦 文件大小: {size_str}")
                    
                    # 显示目录中的照片总数
                    photos = [f for f in os.listdir(CAMERA_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                    output_line(f"  📁 该目录共有 {len(photos)} 张照片")
                
            else:
                output_line(f"❌ 未知操作: {action}")
                return 1
            
            # 如果是非流式模式，输出最终结果
            if not stream:
                print(get_final_output())
            
            return 0
            
        except Exception as e:
            error_msg = f"❌ 执行错误: {str(e)}"
            if stream:
                print(error_msg, file=sys.stderr)
            else:
                print(error_msg)
            return 1
    
    # 如果没有参数或参数错误，显示帮助
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())