#!/usr/bin/env python3
"""
AES-CBC/GCM 命令行加解密工具 - 支持文本和文件的加密解密，支持批量处理
"""

import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import os
import sys
import json
import argparse
from pathlib import Path

# 定义分块大小（64MB）
CHUNK_SIZE = 64 * 1024 * 1024


class AESCli:
    """AES命令行加解密工具"""

    def __init__(self, mode='CBC'):
        """
        初始化AES工具
        :param mode: 加密模式 'CBC' 或 'GCM'
        """
        self.mode = mode
        self.key = None
        self.iv = None

    def set_key_iv(self, key_hex, iv_hex):
        """
        设置密钥和IV/Nonce
        :param key_hex: 十六进制密钥字符串
        :param iv_hex: 十六进制IV/Nonce字符串
        """
        try:
            if not key_hex:
                raise ValueError("密钥不能为空")
            if not iv_hex:
                raise ValueError("IV/Nonce不能为空")

            self.key = bytes.fromhex(key_hex)
            self.iv = bytes.fromhex(iv_hex)

            if len(self.key) not in [16, 24, 32]:
                raise ValueError(f"密钥长度必须为16、24或32字节，当前为{len(self.key)}字节")

            if self.mode == "CBC" and len(self.iv) != 16:
                raise ValueError(f"CBC模式IV长度必须为16字节，当前为{len(self.iv)}字节")
            elif self.mode == "GCM" and len(self.iv) != 12:
                raise ValueError(f"GCM模式Nonce长度必须为12字节，当前为{len(self.iv)}字节")

            return True
        except ValueError as e:
            print(f"错误: {e}")
            return False

    def generate_random_key(self, key_size=16):
        """生成随机密钥"""
        if key_size not in [16, 24, 32]:
            print(f"错误: 密钥大小必须为16、24或32，当前为{key_size}")
            return None

        self.key = get_random_bytes(key_size)
        key_hex = self.key.hex()
        print(f"已生成 {key_size} 字节随机密钥: {key_hex}")
        return key_hex

    def generate_random_iv(self):
        """生成随机IV或Nonce"""
        if self.mode == "CBC":
            iv_size = 16
            label = "IV"
        else:  # GCM
            iv_size = 12
            label = "Nonce"

        self.iv = get_random_bytes(iv_size)
        iv_hex = self.iv.hex()
        print(f"已生成 {iv_size} 字节随机{label}: {iv_hex}")
        return iv_hex

    def encrypt_text(self, plaintext):
        """加密文本"""
        if not self.key or not self.iv:
            raise ValueError("请先设置密钥和IV/Nonce")

        if self.mode == "CBC":
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            ciphertext = cipher.encrypt(pad(plaintext.encode('utf-8'), AES.block_size))
            encrypted = base64.b64encode(ciphertext).decode('utf-8')
        else:  # GCM
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=self.iv)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
            # 存储格式: ciphertext + tag
            combined = ciphertext + tag
            encrypted = base64.b64encode(combined).decode('utf-8')

        return encrypted

    def decrypt_text(self, encrypted_text):
        """解密文本"""
        if not self.key or not self.iv:
            raise ValueError("请先设置密钥和IV/Nonce")

        combined = base64.b64decode(encrypted_text)

        if self.mode == "CBC":
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            decrypted = unpad(cipher.decrypt(combined), AES.block_size)
        else:  # GCM
            # 分离ciphertext和tag (最后16字节是tag)
            if len(combined) < 16:
                raise ValueError("密文格式无效：缺少认证标签")
            tag = combined[-16:]
            ciphertext = combined[:-16]
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=self.iv)
            decrypted = cipher.decrypt_and_verify(ciphertext, tag)

        return decrypted.decode('utf-8')

    def encrypt_file(self, input_path, output_path, delete_source=False):
        """加密文件"""
        if not self.key or not self.iv:
            raise ValueError("请先设置密钥和IV/Nonce")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")

        file_size = os.path.getsize(input_path)
        print(f"开始加密文件: {input_path} ({self._format_size(file_size)})")

        if self.mode == "CBC":
            self._encrypt_file_cbc(input_path, output_path)
        else:  # GCM
            self._encrypt_file_gcm(input_path, output_path)

        print(f"文件加密完成，保存到: {output_path}")

        if delete_source:
            try:
                os.remove(input_path)
                print(f"已删除源文件: {input_path}")
            except Exception as e:
                print(f"警告: 删除源文件失败: {e}")

    def _encrypt_file_cbc(self, input_path, output_path):
        """CBC模式加密文件"""
        with open(input_path, 'rb') as infile:
            file_data = infile.read()

        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        ciphertext = cipher.encrypt(pad(file_data, AES.block_size))

        with open(output_path, 'wb') as outfile:
            # 写入IV + 密文
            outfile.write(self.iv + ciphertext)

    def _encrypt_file_gcm(self, input_path, output_path):
        """GCM模式加密文件"""
        with open(input_path, 'rb') as infile:
            file_data = infile.read()

        cipher = AES.new(self.key, AES.MODE_GCM, nonce=self.iv)
        ciphertext, tag = cipher.encrypt_and_digest(file_data)

        with open(output_path, 'wb') as outfile:
            # 写入IV + 密文 + tag
            outfile.write(self.iv + ciphertext + tag)

    def decrypt_file(self, input_path, output_path, delete_source=False):
        """解密文件"""
        if not self.key or not self.iv:
            raise ValueError("请先设置密钥和IV/Nonce")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")

        file_size = os.path.getsize(input_path)
        print(f"开始解密文件: {input_path} ({self._format_size(file_size)})")

        if self.mode == "CBC":
            self._decrypt_file_cbc(input_path, output_path)
        else:  # GCM
            self._decrypt_file_gcm(input_path, output_path)

        print(f"文件解密完成，保存到: {output_path}")

        if delete_source:
            try:
                os.remove(input_path)
                print(f"已删除加密文件: {input_path}")
            except Exception as e:
                print(f"警告: 删除加密文件失败: {e}")

    def _decrypt_file_cbc(self, input_path, output_path):
        """CBC模式解密文件"""
        with open(input_path, 'rb') as infile:
            file_iv = infile.read(16)
            ciphertext = infile.read()

        cipher = AES.new(self.key, AES.MODE_CBC, file_iv)
        decrypted_data = unpad(cipher.decrypt(ciphertext), AES.block_size)

        with open(output_path, 'wb') as outfile:
            outfile.write(decrypted_data)

    def _decrypt_file_gcm(self, input_path, output_path):
        """GCM模式解密文件"""
        with open(input_path, 'rb') as infile:
            file_iv = infile.read(12)
            remaining = infile.read()

            if len(remaining) < 16:
                raise ValueError("加密文件格式无效：缺少认证标签")

            tag = remaining[-16:]
            ciphertext = remaining[:-16]

        cipher = AES.new(self.key, AES.MODE_GCM, nonce=file_iv)
        decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)

        with open(output_path, 'wb') as outfile:
            outfile.write(decrypted_data)

    def batch_encrypt(self, files, delete_source=False, recursive=False):
        """批量加密文件"""
        total = len(files)
        success = 0
        failed = []

        print(f"\n开始批量加密 {total} 个文件...")

        for i, input_file in enumerate(files, 1):
            try:
                if not os.path.exists(input_file):
                    failed.append(f"{input_file} (文件不存在)")
                    continue

                output_file = self._generate_encrypt_filename(input_file)
                print(f"[{i}/{total}] 加密: {input_file}")

                self.encrypt_file(input_file, output_file, delete_source)
                success += 1

            except Exception as e:
                failed.append(f"{input_file} ({str(e)})")
                print(f"  ✗ 失败: {e}")

        self._print_batch_result("批量加密", success, len(failed), failed)

    def batch_decrypt(self, files, delete_source=False, recursive=False):
        """批量解密文件"""
        total = len(files)
        success = 0
        failed = []

        print(f"\n开始批量解密 {total} 个文件...")

        for i, input_file in enumerate(files, 1):
            try:
                if not os.path.exists(input_file):
                    failed.append(f"{input_file} (文件不存在)")
                    continue

                output_file = self._generate_decrypt_filename(input_file)
                print(f"[{i}/{total}] 解密: {input_file}")

                self.decrypt_file(input_file, output_file, delete_source)
                success += 1

            except Exception as e:
                failed.append(f"{input_file} ({str(e)})")
                print(f"  ✗ 失败: {e}")

        self._print_batch_result("批量解密", success, len(failed), failed)

    def _generate_encrypt_filename(self, input_file):
        """生成加密输出文件名"""
        if input_file.endswith('.encrypted'):
            return input_file
        else:
            return f"{input_file}.encrypted"

    def _generate_decrypt_filename(self, encrypted_file):
        """生成解密输出文件名"""
        if encrypted_file.endswith('.encrypted'):
            return encrypted_file[:-10]
        else:
            return f"{encrypted_file}.decrypted"

    def _print_batch_result(self, operation, success, fail_count, failed_files):
        """打印批量处理结果"""
        print(f"\n{operation}完成:")
        print(f"  成功: {success} 个文件")
        print(f"  失败: {fail_count} 个文件")

        if failed_files:
            print("\n失败的文件:")
            for f in failed_files[:20]:
                print(f"  - {f}")
            if len(failed_files) > 20:
                print(f"  ... 还有 {len(failed_files) - 20} 个文件")

    @staticmethod
    def _format_size(size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def save_key_iv(self, filepath):
        """保存密钥和IV到JSON文件"""
        if not self.key and not self.iv:
            print("警告: 没有可保存的密钥或IV")
            return False

        data = {
            "mode": self.mode,
            "key": self.key.hex() if self.key else "",
            "iv": self.iv.hex() if self.iv else "",
            "key_size": len(self.key) if self.key else 0,
            "description": f"AES-{self.mode}密钥和{'IV' if self.mode == 'CBC' else 'Nonce'}"
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"密钥和IV已保存到: {filepath}")
        return True

    def load_key_iv(self, filepath):
        """从JSON文件加载密钥和IV"""
        if not os.path.exists(filepath):
            print(f"错误: 文件不存在: {filepath}")
            return False

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 加载加密模式
        if 'mode' in data and data['mode'] in ['CBC', 'GCM']:
            self.mode = data['mode']
            print(f"加载加密模式: {self.mode}")

        # 加载密钥
        if 'key' in data and data['key']:
            key_hex = data['key']
            self.key = bytes.fromhex(key_hex)
            print(f"加载密钥: {len(self.key)} 字节")

        # 加载IV
        if 'iv' in data and data['iv']:
            iv_hex = data['iv']
            self.iv = bytes.fromhex(iv_hex)
            label = 'IV' if self.mode == 'CBC' else 'Nonce'
            print(f"加载{label}: {len(self.iv)} 字节")

        print(f"密钥和IV已从 {filepath} 加载")
        return True


def collect_files(paths, pattern=None, recursive=False):
    """收集文件列表"""
    files = []

    for path in paths:
        if os.path.isfile(path):
            files.append(os.path.abspath(path))
        elif os.path.isdir(path):
            if recursive:
                for root, dirs, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(root, filename)
                        if pattern is None or filename.endswith(pattern):
                            files.append(os.path.abspath(filepath))
            else:
                for filename in os.listdir(path):
                    filepath = os.path.join(path, filename)
                    if os.path.isfile(filepath):
                        if pattern is None or filename.endswith(pattern):
                            files.append(os.path.abspath(filepath))

    return files


def main():
    parser = argparse.ArgumentParser(
        description='AES-CBC/GCM 命令行加解密工具 - 支持文本和文件的加密解密，支持批量处理',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 生成随机密钥和IV
  aes-crypto --gen-key
  aes-crypto --gen-iv

  # 文本加解密
  aes-crypto --key <密钥hex> --iv <IV/Nonce hex> --encrypt-text "Hello World"
  aes-crypto --key <密钥hex> --iv <IV/Nonce hex> --decrypt-text "<密文base64>"

  # 文件加解密
  aes-crypto --key <密钥hex> --iv <IV/Nonce hex> --encrypt-file input.txt
  aes-crypto --key <密钥hex> --iv <IV/Nonce hex> --decrypt-file input.txt.encrypted

  # 批量加解密
  aes-crypto --key <密钥hex> --iv <IV/Nonce hex> --batch-encrypt file1.txt file2.txt
  aes-crypto --key <密钥hex> --iv <IV/Nonce hex> --batch-decrypt *.encrypted

  # 保存和加载密钥
  aes-crypto --key <密钥hex> --iv <IV/Nonce hex> --save-key keys.json
  aes-crypto --load-key keys.json --encrypt-file input.txt

  # 使用GCM模式
  aes-crypto --mode GCM --gen-key --key-size 32
  aes-crypto --mode GCM --key <密钥hex> --iv <Nonce hex> --encrypt-file input.txt

  # 从文件读取密钥
  aes-crypto --key-file key.txt --iv <IV/Nonce hex> --encrypt-file input.txt

参数说明:
  --mode CBC|GCM          加密模式 (默认: CBC)
  --key KEY               十六进制密钥 (16/24/32字节)
  --iv IV                 十六进制IV/Nonce (CBC:16字节, GCM:12字节)
  --key-file FILE         从文件读取密钥
  --load-key FILE         从JSON文件加载密钥和IV
  --save-key FILE         保存密钥和IV到JSON文件
  --gen-key               生成随机密钥
  --gen-iv                生成随机IV/Nonce
  --key-size {16,24,32}   密钥大小 (默认: 16)
  --encrypt-text TEXT     加密文本
  --decrypt-text TEXT     解密文本 (base64编码)
  --encrypt-file FILE     加密文件
  --decrypt-file FILE     解密文件
  --output / -o OUTPUT    输出文件路径
  --batch-encrypt PATH    批量加密文件或文件夹
  --batch-decrypt PATH    批量解密文件或文件夹
  --delete-source         加密/解密后删除源文件
  --recursive / -r        递归处理文件夹
        """
    )

    # 模式选择
    parser.add_argument('--mode', choices=['CBC', 'GCM'], default='CBC',
                       help='加密模式 (默认: CBC)')

    # 密钥和IV设置
    parser.add_argument('--key', help='十六进制密钥 (16/24/32字节)')
    parser.add_argument('--iv', help='十六进制IV/Nonce (CBC:16字节, GCM:12字节)')
    parser.add_argument('--key-file', help='从文件读取密钥')
    parser.add_argument('--load-key', help='从JSON文件加载密钥和IV')
    parser.add_argument('--save-key', help='保存密钥和IV到JSON文件')

    # 密钥生成
    parser.add_argument('--gen-key', action='store_true', help='生成随机密钥')
    parser.add_argument('--gen-iv', action='store_true', help='生成随机IV/Nonce')
    parser.add_argument('--key-size', type=int, choices=[16, 24, 32], default=16,
                       help='密钥大小 (默认: 16)')

    # 文本操作
    parser.add_argument('--encrypt-text', help='加密文本')
    parser.add_argument('--decrypt-text', help='解密文本 (base64编码)')

    # 文件操作
    parser.add_argument('--encrypt-file', help='加密文件')
    parser.add_argument('--decrypt-file', help='解密文件')
    parser.add_argument('--output', '-o', help='输出文件路径')

    # 批量操作
    parser.add_argument('--batch-encrypt', nargs='+', metavar='PATH',
                       help='批量加密文件或文件夹')
    parser.add_argument('--batch-decrypt', nargs='+', metavar='PATH',
                       help='批量解密文件或文件夹')
    parser.add_argument('--delete-source', action='store_true',
                       help='加密/解密后删除源文件')
    parser.add_argument('--recursive', '-r', action='store_true',
                       help='递归处理文件夹')

    args = parser.parse_args()

    # 创建AES工具实例
    aes = AESCli(mode=args.mode)

    # 处理密钥加载
    if args.load_key:
        if not aes.load_key_iv(args.load_key):
            sys.exit(1)

    # 处理密钥文件
    if args.key_file:
        try:
            with open(args.key_file, 'r') as f:
                args.key = f.read().strip()
        except Exception as e:
            print(f"错误: 读取密钥文件失败: {e}")
            sys.exit(1)

    # 设置密钥和IV
    if args.key:
        if args.iv is None and not aes.iv:
            print("错误: 需要同时提供密钥和IV/Nonce")
            sys.exit(1)

        if args.iv:
            if not aes.set_key_iv(args.key, args.iv):
                sys.exit(1)
        elif aes.iv:
            # 从加载的密钥文件中获取IV
            try:
                aes.key = bytes.fromhex(args.key)
                if len(aes.key) not in [16, 24, 32]:
                    print(f"错误: 密钥长度必须为16、24或32字节，当前为{len(aes.key)}字节")
                    sys.exit(1)
            except ValueError:
                print("错误: 密钥格式无效，需要十六进制字符串")
                sys.exit(1)

    # 生成密钥
    if args.gen_key:
        key_hex = aes.generate_random_key(args.key_size)
        if key_hex is None:
            sys.exit(1)

    # 生成IV
    if args.gen_iv:
        iv_hex = aes.generate_random_iv()
        if iv_hex is None:
            sys.exit(1)

    # 保存密钥
    if args.save_key:
        if not aes.save_key_iv(args.save_key):
            sys.exit(1)

    # 如果只是生成密钥，到这里就结束了
    if args.gen_key or args.gen_iv:
        if not (args.encrypt_text or args.decrypt_text or
                args.encrypt_file or args.decrypt_file or
                args.batch_encrypt or args.batch_decrypt or args.save_key):
            return

    # 检查密钥和IV是否已设置
    if not aes.key or not aes.iv:
        if args.encrypt_text or args.decrypt_text or \
           args.encrypt_file or args.decrypt_file or \
           args.batch_encrypt or args.batch_decrypt:
            print("错误: 请先设置密钥和IV/Nonce (使用 --key 和 --iv 或 --load-key)")
            sys.exit(1)

    try:
        # 文本加密
        if args.encrypt_text:
            encrypted = aes.encrypt_text(args.encrypt_text)
            print(encrypted)

        # 文本解密
        elif args.decrypt_text:
            decrypted = aes.decrypt_text(args.decrypt_text)
            print(decrypted)

        # 文件加密
        elif args.encrypt_file:
            input_file = args.encrypt_file
            output_file = args.output or aes._generate_encrypt_filename(input_file)
            aes.encrypt_file(input_file, output_file, args.delete_source)

        # 文件解密
        elif args.decrypt_file:
            input_file = args.decrypt_file
            output_file = args.output or aes._generate_decrypt_filename(input_file)
            aes.decrypt_file(input_file, output_file, args.delete_source)

        # 批量加密
        elif args.batch_encrypt:
            files = collect_files(args.batch_encrypt, recursive=args.recursive)
            if not files:
                print("错误: 没有找到要加密的文件")
                sys.exit(1)

            # 过滤掉已加密的文件
            files = [f for f in files if not f.endswith('.encrypted')]
            if not files:
                print("错误: 所有文件都已加密 (.encrypted)")
                sys.exit(1)

            print(f"找到 {len(files)} 个文件需要加密")
            aes.batch_encrypt(files, args.delete_source, args.recursive)

        # 批量解密
        elif args.batch_decrypt:
            files = collect_files(args.batch_decrypt, pattern='.encrypted', recursive=args.recursive)
            if not files:
                print("错误: 没有找到 .encrypted 文件")
                sys.exit(1)

            print(f"找到 {len(files)} 个文件需要解密")
            aes.batch_decrypt(files, args.delete_source, args.recursive)

        # 没有指定操作
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
