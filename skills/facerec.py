#!/usr/bin/env python3
"""人脸检测和识别工具 - 检测图像中的人脸并保存裁剪的人脸图像。"""

import os
import sys
import argparse
import cv2
import numpy as np
from datetime import datetime

try:
    import face_recognition
except ImportError:
    print("❌ 缺少依赖库: face_recognition。请运行: pip install face_recognition")
    sys.exit(1)


class FaceDetector:
    """人脸检测和识别工具"""
    
    def __init__(self):
        self.faces_dir = os.path.expanduser("~/.aibox/faces")
        self.known_faces_dir = os.path.expanduser("~/.aibox/known_faces")
        self._ensure_dirs()
        self.known_face_encodings = []
        self.known_face_names = []
        self._load_known_faces()
    
    def _ensure_dirs(self):
        os.makedirs(self.faces_dir, exist_ok=True)
        os.makedirs(self.known_faces_dir, exist_ok=True)
    
    def _load_known_faces(self):
        """加载已知人脸编码"""
        self.known_face_encodings = []
        self.known_face_names = []
        
        if os.path.exists(self.known_faces_dir):
            for filename in os.listdir(self.known_faces_dir):
                if filename.endswith(('.jpg', '.jpeg', '.png')):
                    filepath = os.path.join(self.known_faces_dir, filename)
                    try:
                        image = face_recognition.load_image_file(filepath)
                        encodings = face_recognition.face_encodings(image)
                        if encodings:
                            name = os.path.splitext(filename)[0]
                            self.known_face_encodings.append(encodings[0])
                            self.known_face_names.append(name)
                    except Exception as e:
                        print(f"加载已知人脸失败 {filename}: {e}", file=sys.stderr)
    
    def detect_faces(self, image_path: str, save_cropped: bool = True, 
                     recognize: bool = True, tolerance: float = 0.6) -> str:
        """检测图像中的人脸并保存裁剪的人脸"""
        try:
            if not os.path.exists(image_path):
                return f"❌ 错误：文件不存在 - {image_path}"
            
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return "📭 未检测到人脸"
            
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            results = []
            saved_files = []
            
            for i, (top, right, bottom, left) in enumerate(face_locations):
                face_data = {
                    "index": i + 1,
                    "position": {"top": top, "right": right, "bottom": bottom, "left": left},
                    "size": {"width": right - left, "height": bottom - top}
                }
                
                if recognize and self.known_face_encodings and i < len(face_encodings):
                    matches = face_recognition.compare_faces(
                        self.known_face_encodings, 
                        face_encodings[i], 
                        tolerance=tolerance
                    )
                    
                    if True in matches:
                        match_index = matches.index(True)
                        name = self.known_face_names[match_index]
                        face_data["name"] = name
                        face_data["match"] = True
                        
                        distances = face_recognition.face_distance(
                            self.known_face_encodings, 
                            face_encodings[i]
                        )
                        face_data["similarity"] = f"{1 - distances[match_index]:.3f}"
                    else:
                        face_data["name"] = "Unknown"
                        face_data["match"] = False
                else:
                    face_data["name"] = f"Face_{i+1}"
                    face_data["match"] = False
                
                if save_cropped:
                    image_array = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    
                    margin = 20
                    top_crop = max(0, top - margin)
                    bottom_crop = min(image_array.shape[0], bottom + margin)
                    left_crop = max(0, left - margin)
                    right_crop = min(image_array.shape[1], right + margin)
                    
                    face_crop = image_array[top_crop:bottom_crop, left_crop:right_crop]
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = face_data['name'].replace(' ', '_')
                    filename = f"{timestamp}_face_{i+1}_{safe_name}.jpg"
                    filepath = os.path.join(self.faces_dir, filename)
                    
                    cv2.imwrite(filepath, face_crop)
                    
                    face_data["saved_file"] = filename
                    saved_files.append(filename)
                
                results.append(face_data)
            
            output = []
            output.append(f"✅ 检测到 {len(face_locations)} 个人脸")
            output.append(f"📁 人脸图像保存位置: {self.faces_dir}")
            output.append("")
            
            for face in results:
                output.append(f"人脸 #{face['index']}:")
                output.append(f"  位置: 左={face['position']['left']}, 上={face['position']['top']}, "
                            f"右={face['position']['right']}, 下={face['position']['bottom']}")
                output.append(f"  大小: {face['size']['width']}x{face['size']['height']} 像素")
                output.append(f"  识别结果: {face['name']}")
                
                if 'similarity' in face:
                    output.append(f"  相似度: {face['similarity']}")
                
                if 'saved_file' in face:
                    output.append(f"  保存文件: {face['saved_file']}")
                
                output.append("")
            
            if saved_files:
                output.append("📋 保存的文件列表:")
                for f in saved_files:
                    output.append(f"  • {f}")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ 人脸检测失败: {str(e)}"
    
    def list_saved_faces(self, limit: int = 20) -> str:
        """列出已保存的人脸图像"""
        try:
            files = []
            if os.path.exists(self.faces_dir):
                for filename in sorted(os.listdir(self.faces_dir), reverse=True):
                    if filename.endswith(('.jpg', '.jpeg', '.png')):
                        files.append(filename)
                        if len(files) >= limit:
                            break
            
            if files:
                output = [f"📁 已保存的人脸图像 (最近 {len(files)} 张):"]
                for f in files:
                    output.append(f"  • {f}")
                output.append(f"\n📂 保存位置: {self.faces_dir}")
                return "\n".join(output)
            else:
                return "📭 尚未保存任何人脸图像"
        except Exception as e:
            return f"❌ 列出失败: {str(e)}"
    
    def list_known_faces(self) -> str:
        """列出已知人脸库中的人脸"""
        try:
            faces = []
            if os.path.exists(self.known_faces_dir):
                for filename in os.listdir(self.known_faces_dir):
                    if filename.endswith(('.jpg', '.jpeg', '.png')):
                        name = os.path.splitext(filename)[0]
                        faces.append(name)
            
            if faces:
                output = [f"👥 已知人脸库 (共 {len(faces)} 人):"]
                for name in faces:
                    output.append(f"  • {name}")
                output.append(f"\n📂 数据库位置: {self.known_faces_dir}")
                return "\n".join(output)
            else:
                return "📭 已知人脸库为空"
        except Exception as e:
            return f"❌ 列出失败: {str(e)}"
    
    def add_known_face(self, image_path: str, person_name: str) -> str:
        """添加已知人脸到数据库"""
        try:
            if not os.path.exists(image_path):
                return f"❌ 文件不存在: {image_path}"
            
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return "❌ 未检测到人脸，无法添加"
            
            if len(face_locations) > 1:
                return f"⚠️ 检测到 {len(face_locations)} 个人脸，请使用单人脸图片"
            
            filepath = os.path.join(self.known_faces_dir, f"{person_name}.jpg")
            
            if os.path.exists(filepath):
                os.remove(filepath)
            
            image_array = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            top, right, bottom, left = face_locations[0]
            
            margin = 20
            top_crop = max(0, top - margin)
            bottom_crop = min(image_array.shape[0], bottom + margin)
            left_crop = max(0, left - margin)
            right_crop = min(image_array.shape[1], right + margin)
            
            face_crop = image_array[top_crop:bottom_crop, left_crop:right_crop]
            cv2.imwrite(filepath, face_crop)
            
            self._load_known_faces()
            
            return f"✅ 已添加已知人脸: {person_name}\n📁 保存位置: {filepath}"
            
        except Exception as e:
            return f"❌ 添加失败: {str(e)}"
    
    def remove_known_face(self, person_name: str) -> str:
        """从已知人脸库中删除人脸"""
        try:
            filepath = os.path.join(self.known_faces_dir, f"{person_name}.jpg")
            
            if not os.path.exists(filepath):
                for filename in os.listdir(self.known_faces_dir):
                    if filename.endswith(('.jpg', '.jpeg', '.png')):
                        name = os.path.splitext(filename)[0]
                        if name.lower() == person_name.lower():
                            filepath = os.path.join(self.known_faces_dir, filename)
                            break
                else:
                    return f"❌ 未找到已知人脸: {person_name}"
            
            os.remove(filepath)
            self._load_known_faces()
            
            return f"✅ 已删除已知人脸: {person_name}"
            
        except Exception as e:
            return f"❌ 删除失败: {str(e)}"
    
    def get_face_info(self, person_name: str) -> str:
        """获取已知人脸信息"""
        try:
            filepath = os.path.join(self.known_faces_dir, f"{person_name}.jpg")
            
            if not os.path.exists(filepath):
                for filename in os.listdir(self.known_faces_dir):
                    if filename.endswith(('.jpg', '.jpeg', '.png')):
                        name = os.path.splitext(filename)[0]
                        if name.lower() == person_name.lower():
                            filepath = os.path.join(self.known_faces_dir, filename)
                            person_name = name
                            break
                else:
                    return f"❌ 未找到人脸: {person_name}"
            
            file_size = os.path.getsize(filepath)
            modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            output = []
            output.append(f"👤 人脸信息: {person_name}")
            output.append(f"📁 文件路径: {filepath}")
            output.append(f"📊 文件大小: {file_size} 字节 ({file_size/1024:.1f}KB)")
            output.append(f"🕐 最后修改: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ 获取人脸信息失败: {str(e)}"


def main():
    parser = argparse.ArgumentParser(
        description="人脸检测和识别工具 - 检测图像中的人脸并保存裁剪的人脸图像。",
        epilog="""
使用示例:
  # 检测人脸
  face-detector --action detect --image-path photo.jpg

  # 检测人脸（不保存裁剪）
  face-detector --action detect --image-path photo.jpg --no-save

  # 检测人脸（不进行识别）
  face-detector --action detect --image-path photo.jpg --no-recognize

  # 列出已保存的人脸图像
  face-detector --action list-faces --limit 10

  # 列出已知人脸库
  face-detector --action list-known

  # 添加已知人脸
  face-detector --action add-known --image-path face.jpg --person-name "张三"

  # 删除已知人脸
  face-detector --action remove-known --person-name "张三"

  # 查看人脸信息
  face-detector --action get-info --person-name "张三"

目录结构:
  ~/.aibox/faces/       - 人脸图像保存位置
  ~/.aibox/known_faces/ - 已知人脸数据库

需要安装:
  pip install face_recognition opencv-python
        """
    )
    
    parser.add_argument("--action", "-a", required=True,
        choices=["detect", "list-faces", "list-known", "add-known", "remove-known", "get-info"],
        help="操作类型")
    
    # 检测参数
    parser.add_argument("--image-path", "-i", help="图片文件路径")
    parser.add_argument("--no-save", action="store_true", help="不保存裁剪的人脸图像")
    parser.add_argument("--no-recognize", action="store_true", help="不进行人脸识别")
    parser.add_argument("--tolerance", "-t", type=float, default=0.6, help="识别容差（默认: 0.6）")
    
    # 列表参数
    parser.add_argument("--limit", "-l", type=int, default=20, help="列出文件数量限制（默认: 20）")
    
    # 已知人脸参数
    parser.add_argument("--person-name", "-n", help="人名标识")
    
    args = parser.parse_args()
    
    detector = FaceDetector()
    
    try:
        if args.action == "detect":
            if not args.image_path:
                print("❌ 需要提供 --image-path 参数")
                sys.exit(1)
            
            result = detector.detect_faces(
                image_path=args.image_path,
                save_cropped=not args.no_save,
                recognize=not args.no_recognize,
                tolerance=args.tolerance
            )
            print(result)
        
        elif args.action == "list-faces":
            print(detector.list_saved_faces(args.limit))
        
        elif args.action == "list-known":
            print(detector.list_known_faces())
        
        elif args.action == "add-known":
            if not args.image_path or not args.person_name:
                print("❌ 需要提供 --image-path 和 --person-name 参数")
                sys.exit(1)
            
            result = detector.add_known_face(args.image_path, args.person_name)
            print(result)
        
        elif args.action == "remove-known":
            if not args.person_name:
                print("❌ 需要提供 --person-name 参数")
                sys.exit(1)
            
            result = detector.remove_known_face(args.person_name)
            print(result)
        
        elif args.action == "get-info":
            if not args.person_name:
                print("❌ 需要提供 --person-name 参数")
                sys.exit(1)
            
            result = detector.get_face_info(args.person_name)
            print(result)
        
    except Exception as e:
        print(f"❌ 执行错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()