#!/usr/bin/env python3
"""摄像头拍照工具 - 获取相机设备列表、选择指定相机拍照、保存照片。"""

import os
import sys
import argparse
from pathlib import Path
import time

try:
    import cv2
except ImportError:
    print("❌ 缺少依赖库: opencv-python。请运行: pip install opencv-python")
    sys.exit(1)

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
            ret, frame = cap.read()
            if ret:
                height, width = frame.shape[:2]
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
        if value >= 0:
            info["properties"][prop_name] = value
    
    ret, frame = cap.read()
    if ret:
        height, width = frame.shape[:2]
        info["current_resolution"] = f"{width}x{height}"
        info["channels"] = frame.shape[2] if len(frame.shape) > 2 else 1
    
    cap.release()
    
    if sys.platform.startswith('linux'):
        dev_path = f"/dev/video{camera_id}"
        if os.path.exists(dev_path):
            info["device_path"] = dev_path
    
    return info


def capture_photo(camera_id=0, save_path=None, resolution=None, wait_time=1):
    """调用指定摄像头拍照"""
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        return None, f"无法打开摄像头 #{camera_id}，请检查摄像头连接", None, None
    
    if resolution:
        try:
            width, height = map(int, resolution.lower().replace('x', ' ').split())
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        except:
            pass
    
    time.sleep(wait_time)
    
    for _ in range(5):
        cap.read()
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return None, "拍照失败，无法获取图像帧", None, None
    
    actual_height, actual_width = frame.shape[:2]
    
    if save_path is None:
        ensure_camera_dir()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"camera_{camera_id}_{timestamp}.jpg"
        save_path = os.path.join(CAMERA_DIR, filename)
    else:
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
    
    if not os.path.splitext(save_path)[1]:
        save_path += '.jpg'
    
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
    
    photos = []
    for f in os.listdir(CAMERA_DIR):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
            filepath = os.path.join(CAMERA_DIR, f)
            mtime = os.path.getmtime(filepath)
            size = os.path.getsize(filepath)
            photos.append((mtime, f, size))
    
    photos.sort(reverse=True)
    
    if not photos:
        return f"摄像头照片目录中没有照片: {CAMERA_DIR}"
    
    result = [f"📸 最近的摄像头照片 (共 {len(photos)} 个):"]
    for i, (mtime, fname, size) in enumerate(photos[:limit], 1):
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        
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
    parser = argparse.ArgumentParser(
        description="摄像头拍照工具 - 获取相机设备列表、选择指定相机拍照、保存照片。",
        epilog="""
使用示例:
  # 列出所有可用摄像头
  camera --action list

  # 查看摄像头详细信息
  camera --action info --camera-id 0

  # 拍照（自动生成文件名）
  camera --action capture --camera-id 0

  # 拍照并指定分辨率
  camera --action capture --camera-id 0 --resolution "1920x1080"

  # 拍照并自定义文件名
  camera --action capture --camera-id 0 --filename "my_photo"

  # 拍照并等待3秒预热
  camera --action capture --camera-id 0 --wait-time 3

  # 列出最近的照片
  camera --action list-photos --limit 5

照片保存位置:
  ~/.aibox/camera/
  自动命名格式: camera_{摄像头ID}_{YYYYMMDD_HHMMSS}.jpg

需要安装:
  pip install opencv-python
        """
    )
    
    parser.add_argument("--action", "-a", required=True,
        choices=["list", "info", "capture", "list-photos"],
        help="操作类型")
    
    # 摄像头参数
    parser.add_argument("--camera-id", "-c", type=int, default=0,
        help="摄像头ID（默认: 0）")
    
    parser.add_argument("--resolution", "-r",
        help="照片分辨率，格式: 宽度x高度（如 1920x1080）")
    
    parser.add_argument("--wait-time", "-w", type=float, default=1,
        help="等待摄像头预热时间（秒，默认: 1）")
    
    parser.add_argument("--filename", "-f",
        help="自定义文件名（不含路径，自动保存到默认目录）")
    
    parser.add_argument("--limit", "-l", type=int, default=10,
        help="列出照片时的数量限制（默认: 10）")
    
    args = parser.parse_args()
    
    # 执行操作
    try:
        if args.action == "list":
            print("🔍 正在扫描摄像头设备...")
            cameras = list_cameras(10)
            print(format_camera_list(cameras))
            
            if cameras:
                print(f"\n💡 使用建议:")
                print(f"  要使用摄像头 #{cameras[0]['id']} 拍照，请执行:")
                print(f"    camera --action capture --camera-id {cameras[0]['id']}")
                print(f"  要查看摄像头详细信息，请执行:")
                print(f"    camera --action info --camera-id {cameras[0]['id']}")
        
        elif args.action == "list-photos":
            result = list_recent_photos(args.limit)
            print(result)
        
        elif args.action == "info":
            print(f"🔍 正在获取摄像头 #{args.camera_id} 的详细信息...")
            
            info = get_camera_info(args.camera_id)
            if not info:
                print(f"❌ 无法打开摄像头 #{args.camera_id}，请检查设备是否存在")
                sys.exit(1)
            
            print(f"📷 摄像头 #{args.camera_id} 详细信息:")
            if "device_path" in info:
                print(f"  设备路径: {info['device_path']}")
            print(f"  当前分辨率: {info.get('current_resolution', '未知')}")
            if "channels" in info:
                print(f"  色彩通道: {info['channels']}")
            
            if info["properties"]:
                print(f"\n  支持设置的属性:")
                for name, value in info["properties"].items():
                    print(f"    {name}: {value}")
            
            print(f"\n💡 要拍照请执行:")
            print(f"  camera --action capture --camera-id {args.camera_id}")
        
        elif args.action == "capture":
            ensure_camera_dir()
            
            if args.filename:
                save_path = os.path.join(CAMERA_DIR, args.filename)
            else:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(CAMERA_DIR, f"camera_{args.camera_id}_{timestamp}.jpg")
            
            print(f"📸 正在使用摄像头 #{args.camera_id} 拍照...")
            if args.resolution:
                print(f"  请求分辨率: {args.resolution}")
            print(f"  预热时间: {args.wait_time}秒")
            print(f"  保存目录: {CAMERA_DIR}")
            
            image_path, error, width, height = capture_photo(
                camera_id=args.camera_id,
                save_path=save_path,
                resolution=args.resolution,
                wait_time=args.wait_time
            )
            
            if error:
                print(f"❌ {error}")
                sys.exit(1)
            
            print(f"✅ 拍照成功!")
            print(f"  📷 实际分辨率: {width}x{height}")
            print(f"  💾 保存路径: {image_path}")
            
            if os.path.exists(image_path):
                file_size = os.path.getsize(image_path)
                if file_size < 1024:
                    size_str = f"{file_size}B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size/1024:.1f}KB"
                else:
                    size_str = f"{file_size/1024/1024:.1f}MB"
                print(f"  📦 文件大小: {size_str}")
            
            photos = [f for f in os.listdir(CAMERA_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            print(f"  📁 该目录共有 {len(photos)} 张照片")
        
    except Exception as e:
        print(f"❌ 执行错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()