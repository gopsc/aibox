#!/usr/bin/env python3
"""
一个基于python-nmap的局域网Ping扫描工具
"""
import argparse
import sys
import socket

def scan_network(network="192.168.1.0/24", timeout=3, verbose=False):
    """使用nmap -sn模式扫描局域网"""
    try:
        import nmap
    except ImportError:
        print("❌ 错误：缺少 python-nmap 库，请执行: pip install python-nmap")
        sys.exit(1)

    nm = nmap.PortScanner()
    arguments = f"-sn -T{4 if timeout > 3 else 3} --max-rtt-timeout={timeout * 1000}ms"
    if verbose:
        arguments += " -v"

    print(f"🔍 正在扫描网段: {network}")
    print(f"⏱️  超时设置: {timeout}秒")
    print(f"{'📋 详细模式: 开启' if verbose else '📋 详细模式: 关闭'}")
    print("-" * 50)

    try:
        result = nm.scan(hosts=network, arguments=arguments)
    except Exception as e:
        print(f"❌ 扫描失败: {e}")
        print("💡 提示：请确保已安装 nmap (sudo apt install nmap) 并有足够权限")
        sys.exit(1)

    alive_hosts = []
    for host in nm.all_hosts():
        if nm[host].state() == "up":
            alive_hosts.append(host)
            hostname = ""
            try:
                hostname = socket.gethostbyaddr(host)[0]
            except (socket.herror, socket.gaierror):
                hostname = "(未知)"
            
            mac = ""
            try:
                if 'mac' in nm[host]['addresses']:
                    mac = nm[host]['addresses']['mac']
            except (KeyError, TypeError):
                pass

            line = f"✅ {host}"
            if verbose:
                if hostname and hostname != "(未知)":
                    line += f"  [{hostname}]"
                if mac:
                    line += f"  MAC: {mac}"
            print(line)

    print("-" * 50)
    print(f"📊 扫描完成！共发现 {len(alive_hosts)} 台在线主机")
    return alive_hosts


def main():
    parser = argparse.ArgumentParser(
        description="基于python-nmap的局域网Ping扫描工具，快速发现局域网在线设备",
        epilog="""
参数说明:
  -n NETWORK   指定扫描网段 (默认: 192.168.1.0/24)
               支持格式: 192.168.1.0/24, 192.168.1.1-254, 192.168.1.1
  -t TIMEOUT   超时时间，单位秒 (默认: 3)
  -v           详细输出模式，显示MAC地址和主机名
  --help       显示本帮助信息

使用示例:
  nmapskills                          # 扫描默认网段 192.168.1.0/24
  nmapskills -n 10.0.0.0/24          # 扫描 10.0.0.0/24 网段
  nmapskills -n 192.168.1.1-100      # 扫描 192.168.1.1 到 192.168.1.100
  nmapskills -n 192.168.1.0/24 -t 5   # 扫描并设置5秒超时
  nmapskills -n 192.168.1.0/24 -v     # 详细模式扫描
        """
    )

    parser.add_argument("-n", default="192.168.1.0/24",
                        help="指定扫描网段 (默认: 192.168.1.0/24)")
    parser.add_argument("-t", type=int, default=3,
                        help="超时时间，单位秒 (默认: 3)")
    parser.add_argument("-v", action="store_true",
                        help="详细输出模式，显示MAC地址和主机名")

    args = parser.parse_args()

    scan_network(network=args.n, timeout=args.t, verbose=args.v)


if __name__ == "__main__":
    main()
