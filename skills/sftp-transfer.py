#!/usr/bin/env python3
"""
sftp-transfer - 基于SFTP协议的文件上传/下载工具

支持从远程SSH服务器上传和下载文件，支持密码和密钥认证方式。
"""

import argparse
import os
import sys
import stat
import getpass

try:
    import paramiko
except ImportError:
    print("错误：需要 paramiko 库，请执行: pip install paramiko", file=sys.stderr)
    sys.exit(1)


def build_parser():
    parser = argparse.ArgumentParser(
        description="sftp-transfer - 基于SFTP协议的文件上传/下载工具",
        epilog="""
参数说明:
  连接参数:
    --host          SSH服务器主机名或IP地址 (必填)
    --port          SSH服务器端口号，默认 22
    -u, --username  SSH登录用户名 (必填)
    -p, --password  SSH登录密码 (如不提供则交互式输入)
    --key            SSH私钥文件路径 (用于密钥认证)

  操作参数:
    --upload  LOCAL REMOTE   上传：本地文件/目录 -> 远程服务器路径
    --download REMOTE LOCAL  下载：远程服务器文件/目录 -> 本地路径
    -r, --recursive         递归传输目录
    -v, --verbose           显示详细信息

使用示例:
  1. 上传文件（密码认证）:
     sftp-transfer --host 192.168.1.100 -u root -p mypass --upload /tmp/test.txt /root/

  2. 下载文件（密钥认证）:
     sftp-transfer --host 192.168.1.100 -u root --key ~/.ssh/id_rsa \\
         --download /root/test.txt /tmp/

  3. 递归上传目录:
     sftp-transfer --host 192.168.1.100 -u user -p pass -r \\
         --upload ./mydir /home/user/mydir

  4. 下载目录:
     sftp-transfer --host 192.168.1.100 -u user -p pass -r \\
         --download /home/user/backup ./backup

  5. 交互式输入密码:
     sftp-transfer --host 127.0.0.1 -u qing --upload ./file.txt /tmp/
     (此时会提示输入密码)
        """
    )
    # 连接参数
    parser.add_argument('--host', required=True, help='SSH服务器主机名或IP地址')
    parser.add_argument('--port', type=int, default=22, help='SSH服务器端口号，默认22')
    parser.add_argument('-u', '--username', required=True, help='SSH登录用户名')
    parser.add_argument('-p', '--password', help='SSH登录密码（如不提供则交互式输入）')
    parser.add_argument('--key', help='SSH私钥文件路径（用于密钥认证）')

    # 操作参数
    parser.add_argument('--upload', nargs=2, metavar=('LOCAL', 'REMOTE'),
                        help='上传：本地文件/目录 -> 远程服务器路径')
    parser.add_argument('--download', nargs=2, metavar=('REMOTE', 'LOCAL'),
                        help='下载：远程服务器文件/目录 -> 本地路径')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='递归传输目录')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细信息')
    return parser


def log(verbose, msg):
    if verbose:
        print(f"[SFTP] {msg}")


def get_password(args):
    """获取密码：优先从命令行参数获取，否则交互式输入"""
    if args.password:
        return args.password
    return getpass.getpass(f"请输入 {args.username}@{args.host} 的密码: ")


def connect_sftp(args, password):
    """建立SSH连接并返回SFTP客户端"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {
        'hostname': args.host,
        'port': args.port,
        'username': args.username,
        'timeout': 15,
    }

    if args.key:
        connect_kwargs['key_filename'] = args.key
        if password:
            connect_kwargs['password'] = password
    else:
        connect_kwargs['password'] = password

    log(args.verbose, f"正在连接 {args.username}@{args.host}:{args.port} ...")
    client.connect(**connect_kwargs)
    log(args.verbose, "连接成功！")

    sftp = client.open_sftp()
    return client, sftp


def ensure_remote_dir(sftp, remote_path, verbose):
    """确保远程目录存在，递归创建"""
    parts = remote_path.rstrip('/').split('/')
    current = ''
    for part in parts:
        if not part:
            continue
        current += '/' + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            log(verbose, f"  创建远程目录: {current}")
            sftp.mkdir(current)


def upload_file(sftp, local_path, remote_path, verbose):
    """上传单个文件"""
    remote_dir = os.path.dirname(remote_path)
    if remote_dir:
        ensure_remote_dir(sftp, remote_dir, verbose)
    log(verbose, f"  上传: {local_path} -> {remote_path}")
    sftp.put(local_path, remote_path)


def upload_dir(sftp, local_dir, remote_dir, verbose):
    """递归上传目录"""
    ensure_remote_dir(sftp, remote_dir, verbose)
    for item in os.listdir(local_dir):
        local_item = os.path.join(local_dir, item)
        remote_item = os.path.join(remote_dir, item)
        if os.path.isdir(local_item):
            log(verbose, f"  进入目录: {local_item}")
            upload_dir(sftp, local_item, remote_item, verbose)
        else:
            upload_file(sftp, local_item, remote_item, verbose)


def download_file(sftp, remote_path, local_path, verbose):
    """下载单个文件"""
    local_dir = os.path.dirname(local_path)
    if local_dir and not os.path.exists(local_dir):
        os.makedirs(local_dir, exist_ok=True)
    log(verbose, f"  下载: {remote_path} -> {local_path}")
    sftp.get(remote_path, local_path)


def download_dir(sftp, remote_dir, local_dir, verbose):
    """递归下载目录"""
    if not os.path.exists(local_dir):
        os.makedirs(local_dir, exist_ok=True)
        log(verbose, f"  创建本地目录: {local_dir}")

    for item in sftp.listdir(remote_dir):
        remote_item = os.path.join(remote_dir, item).replace('\\', '/')
        local_item = os.path.join(local_dir, item)
        try:
            attr = sftp.stat(remote_item)
            if stat.S_ISDIR(attr.st_mode):
                log(verbose, f"  进入目录: {remote_item}")
                download_dir(sftp, remote_item, local_item, verbose)
            else:
                download_file(sftp, remote_item, local_item, verbose)
        except Exception as e:
            print(f"  警告: 无法处理 {remote_item}: {e}", file=sys.stderr)


def main():
    parser = build_parser()
    args = parser.parse_args()

    # 检查操作参数
    if not args.upload and not args.download:
        parser.print_help()
        print("\n错误：必须指定 --upload 或 --download 操作", file=sys.stderr)
        sys.exit(1)

    if args.upload and args.download:
        print("错误：不能同时指定 --upload 和 --download", file=sys.stderr)
        sys.exit(1)

    # 获取密码
    password = get_password(args)

    # 建立连接
    try:
        client, sftp = connect_sftp(args, password)
    except Exception as e:
        print(f"错误：连接失败 - {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.upload:
            local_path, remote_path = args.upload
            remote_path = remote_path.replace('\\', '/')

            if os.path.isdir(local_path):
                if not args.recursive:
                    print("错误：本地路径是目录，请使用 -r 参数递归上传", file=sys.stderr)
                    sys.exit(1)
                upload_dir(sftp, local_path, remote_path, args.verbose)
            else:
                # 如果远程路径以/结尾，追加文件名
                if remote_path.endswith('/'):
                    remote_path = remote_path + os.path.basename(local_path)
                upload_file(sftp, local_path, remote_path, args.verbose)

            print(f"✅ 上传完成: {local_path} -> {remote_path}")

        elif args.download:
            remote_path, local_path = args.download
            remote_path = remote_path.replace('\\', '/')

            try:
                attr = sftp.stat(remote_path)
                is_dir = stat.S_ISDIR(attr.st_mode)
            except FileNotFoundError:
                print(f"错误：远程路径不存在: {remote_path}", file=sys.stderr)
                sys.exit(1)

            if is_dir:
                if not args.recursive:
                    print("错误：远程路径是目录，请使用 -r 参数递归下载", file=sys.stderr)
                    sys.exit(1)
                download_dir(sftp, remote_path, local_path, args.verbose)
            else:
                if os.path.isdir(local_path):
                    local_path = os.path.join(local_path, os.path.basename(remote_path))
                download_file(sftp, remote_path, local_path, args.verbose)

            print(f"✅ 下载完成: {remote_path} -> {local_path}")

    except Exception as e:
        print(f"错误：传输失败 - {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        sftp.close()
        client.close()
        log(args.verbose, "连接已关闭")


if __name__ == '__main__':
    main()
