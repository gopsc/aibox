#!/usr/bin/env python3
"""
扩展技能：人脸检测和识别工具
用于检测图像中的人脸并保存裁剪后的人脸图像
放置在 ~/.aibox/skills/face_detector.py
"""

import os
import sys
import json
import argparse
import cv2
import face_recognition
import numpy as np
from datetime import datetime
from typing import List, Optional


class FaceDetector:
    """人脸检测和识别工具"""
    
    def __init__(self):
        # 人脸图像保存目录
        self.faces_dir = os.path.expanduser("~/.aibox/faces")
        # 已知人脸数据库目录
        self.known_faces_dir = os.path.expanduser("~/.aibox/known_faces")
        self._ensure_dirs()
        self.known_face_encodings = []
        self.known_face_names = []
        self._load_known_faces()
    
    def _ensure_dirs(self):
        """确保目录存在"""
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
                            # 文件名作为人名（去掉扩展名）
                            name = os.path.splitext(filename)[0]
                            self.known_face_encodings.append(encodings[0])
                            self.known_face_names.append(name)
                    except Exception as e:
                        print(f"加载已知人脸失败 {filename}: {e}", file=sys.stderr)
    
    def detect_faces(self, image_path: str, save_cropped: bool = True, 
                     recognize: bool = True, tolerance: float = 0.6) -> str:
        """
        检测图像中的人脸并保存裁剪的人脸
        """
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
                    
                    # 添加一点边距
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
            output.append(f"📁 已知人脸数据库: {self.known_faces_dir}")
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
    
    def list_saved_faces(self, limit: int = 20) -> List[str]:
        """列出已保存的人脸图像"""
        try:
            files = []
            if os.path.exists(self.faces_dir):
                for filename in sorted(os.listdir(self.faces_dir), reverse=True):
                    if filename.endswith(('.jpg', '.jpeg', '.png')):
                        files.append(filename)
                        if len(files) >= limit:
                            break
            return files
        except Exception:
            return []
    
    def list_known_faces(self) -> List[str]:
        """列出已知人脸库中的人脸"""
        try:
            faces = []
            if os.path.exists(self.known_faces_dir):
                for filename in os.listdir(self.known_faces_dir):
                    if filename.endswith(('.jpg', '.jpeg', '.png')):
                        name = os.path.splitext(filename)[0]
                        faces.append(name)
            return faces
        except Exception:
            return []
    
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
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{person_name}.jpg"
            filepath = os.path.join(self.known_faces_dir, filename)
            
            # 如果已存在同名文件，先删除
            if os.path.exists(filepath):
                os.remove(filepath)
            
            image_array = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            top, right, bottom, left = face_locations[0]
            
            # 添加一点边距
            margin = 20
            top_crop = max(0, top - margin)
            bottom_crop = min(image_array.shape[0], bottom + margin)
            left_crop = max(0, left - margin)
            right_crop = min(image_array.shape[1], right + margin)
            
            face_crop = image_array[top_crop:bottom_crop, left_crop:right_crop]
            cv2.imwrite(filepath, face_crop)
            
            # 重新加载已知人脸
            self._load_known_faces()
            
            return f"✅ 已添加已知人脸: {person_name}\n📁 保存位置: {filepath}"
            
        except Exception as e:
            return f"❌ 添加失败: {str(e)}"
    
    def remove_known_face(self, person_name: str) -> str:
        """从已知人脸库中删除人脸"""
        try:
            filepath = os.path.join(self.known_faces_dir, f"{person_name}.jpg")
            
            if not os.path.exists(filepath):
                # 尝试查找匹配的文件（不区分大小写）
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
    
    def get_face_info(self, person_name: str) -> Optional[str]:
        """获取已知人脸信息"""
        try:
            filepath = os.path.join(self.known_faces_dir, f"{person_name}.jpg")
            
            if not os.path.exists(filepath):
                # 尝试查找匹配的文件
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
    """主函数 - 处理命令行参数"""
    parser = argparse.ArgumentParser(description='人脸检测和识别工具')
    
    parser.add_argument('--description', action='store_true', help='返回工具描述')
    parser.add_argument('--parameters', action='store_true', help='返回工具参数定义')
    parser.add_argument('--execute', action='store_true', help='执行工具')
    parser.add_argument('--args', type=str, default='{}', help='工具参数（JSON格式）')
    
    args = parser.parse_args()
    
    # 返回描述信息
    if args.description:
        desc = """人脸检测和识别工具

功能：
- 检测图像中的人脸
- 自动裁剪并保存人脸图像
- 人脸识别（需要已知人脸库）
- 添加/删除已知人脸到数据库
- 列出已保存的人脸图像
- 查看已知人脸信息

目录结构：
- 人脸图像保存位置: ~/.aibox/faces/
- 已知人脸数据库: ~/.aibox/known_faces/

支持的操作：
- detect: 检测图像中的人脸并保存
- list_faces: 列出已保存的人脸图像
- list_known: 列出已知人脸库
- add_known: 添加已知人脸到数据库
- remove_known: 从数据库中删除已知人脸
- get_info: 获取已知人脸信息"""
        print(desc)
        sys.exit(0)
    
    # 返回参数定义
    if args.parameters:
        parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["detect", "list_faces", "list_known", "add_known", "remove_known", "get_info"],
                    "description": "操作类型"
                },
                "image_path": {
                    "type": "string",
                    "description": "图片文件路径（用于detect和add_known操作）"
                },
                "person_name": {
                    "type": "string",
                    "description": "人名标识（用于add_known、remove_known、get_info操作）"
                },
                "save_cropped": {
                    "type": "boolean",
                    "description": "是否保存裁剪的人脸图像",
                    "default": True
                },
                "recognize": {
                    "type": "boolean",
                    "description": "是否进行人脸识别",
                    "default": True
                },
                "limit": {
                    "type": "integer",
                    "description": "列出文件数量限制",
                    "default": 20
                }
            },
            "required": ["action"]
        }
        print(json.dumps(parameters, ensure_ascii=False, separators=(',', ':')))
        sys.exit(0)
    
    # 执行工具
    if args.execute:
        try:
            params = json.loads(args.args) if args.args else {}
            action = params.get("action", "detect")
            detector = FaceDetector()
            
            if action == "detect":
                image_path = params.get("image_path")
                if not image_path:
                    print("❌ 错误：需要提供 image_path 参数")
                    sys.exit(1)
                
                save_cropped = params.get("save_cropped", True)
                recognize = params.get("recognize", True)
                
                result = detector.detect_faces(image_path, save_cropped, recognize)
                print(result)
                
            elif action == "list_faces":
                limit = params.get("limit", 20)
                files = detector.list_saved_faces(limit)
                if files:
                    print(f"📁 已保存的人脸图像 (最近 {len(files)} 张):")
                    for f in files:
                        print(f"  • {f}")
                    print(f"\n📂 保存位置: {detector.faces_dir}")
                else:
                    print("📭 尚未保存任何人脸图像")
                    
            elif action == "list_known":
                faces = detector.list_known_faces()
                if faces:
                    print(f"👥 已知人脸库 (共 {len(faces)} 人):")
                    for name in faces:
                        print(f"  • {name}")
                    print(f"\n📂 数据库位置: {detector.known_faces_dir}")
                else:
                    print("📭 已知人脸库为空")
                    
            elif action == "add_known":
                image_path = params.get("image_path")
                person_name = params.get("person_name")
                
                if not image_path or not person_name:
                    print("❌ 错误：需要提供 image_path 和 person_name 参数")
                    sys.exit(1)
                
                result = detector.add_known_face(image_path, person_name)
                print(result)
                
            elif action == "remove_known":
                person_name = params.get("person_name")
                
                if not person_name:
                    print("❌ 错误：需要提供 person_name 参数")
                    sys.exit(1)
                
                result = detector.remove_known_face(person_name)
                print(result)
                
            elif action == "get_info":
                person_name = params.get("person_name")
                
                if not person_name:
                    print("❌ 错误：需要提供 person_name 参数")
                    sys.exit(1)
                
                result = detector.get_face_info(person_name)
                print(result)
                
            else:
                print(f"❌ 未知操作: {action}")
                sys.exit(1)
            
        except json.JSONDecodeError as e:
            print(f"❌ 参数解析错误: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 执行错误: {e}")
            sys.exit(1)
        sys.exit(0)
    
    parser.print_help()


if __name__ == "__main__":
    main()