#!/usr/bin/env python3
"""
系统信息工具 - 获取系统状态信息
功能：获取系统运行时间、CPU使用率、内存使用情况、磁盘使用情况等
"""

import sys
import json
import argparse
import platform
import psutil
import datetime
import os


def get_system_info():
    """获取系统基本信息"""
    return {
        "系统": platform.system(),
        "主机名": platform.node(),
        "版本": platform.version(),
        "架构": platform.machine(),
        "处理器": platform.processor(),
        "Python版本": platform.python_version()
    }


def get_uptime():
    """获取系统运行时间"""
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    now = datetime.datetime.now()
    uptime = now - boot_time
    
    days = uptime.days
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    seconds = uptime.seconds % 60
    
    return {
        "启动时间": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
        "运行时间": f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒"
    }


def get_cpu_info():
    """获取CPU信息"""
    return {
        "物理核心数": psutil.cpu_count(logical=False),
        "逻辑核心数": psutil.cpu_count(logical=True),
        "使用率": f"{psutil.cpu_percent(interval=1)}%",
        "频率": f"{psutil.cpu_freq().current:.2f} MHz" if psutil.cpu_freq() else "未知"
    }


def get_memory_info():
    """获取内存信息"""
    mem = psutil.virtual_memory()
    return {
        "总内存": f"{mem.total / (1024**3):.2f} GB",
        "可用内存": f"{mem.available / (1024**3):.2f} GB",
        "已用内存": f"{mem.used / (1024**3):.2f} GB",
        "使用率": f"{mem.percent}%"
    }


def get_disk_info(path="/"):
    """获取磁盘信息"""
    disk = psutil.disk_usage(path)
    return {
        "路径": path,
        "总空间": f"{disk.total / (1024**3):.2f} GB",
        "已用空间": f"{disk.used / (1024**3):.2f} GB",
        "可用空间": f"{disk.free / (1024**3):.2f} GB",
        "使用率": f"{disk.percent}%"
    }


def get_process_count():
    """获取进程数量"""
    return {
        "进程数": len(psutil.pids())
    }


def get_network_info():
    """获取网络信息"""
    net = psutil.net_io_counters()
    return {
        "发送数据": f"{net.bytes_sent / (1024**2):.2f} MB",
        "接收数据": f"{net.bytes_recv / (1024**2):.2f} MB",
        "发送包数": net.packets_sent,
        "接收包数": net.packets_recv
    }


def get_load_average():
    """获取系统负载（仅Unix系统）"""
    if hasattr(os, 'getloadavg'):
        load1, load5, load15 = os.getloadavg()
        cpu_count = psutil.cpu_count()
        return {
            "1分钟负载": f"{load1:.2f} (每核心: {load1/cpu_count:.2f})",
            "5分钟负载": f"{load5:.2f} (每核心: {load5/cpu_count:.2f})",
            "15分钟负载": f"{load15:.2f} (每核心: {load15/cpu_count:.2f})"
        }
    else:
        return {"信息": "系统负载信息在Windows上不可用"}


def format_output(data, format_type="text"):
    """格式化输出"""
    if format_type == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    else:
        lines = []
        for key, value in data.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='系统信息工具 - 获取系统状态信息')
    
    # 定义所有参数
    parser.add_argument('--description', action='store_true', help='获取工具描述')
    parser.add_argument('--parameters', action='store_true', help='获取参数定义')
    parser.add_argument('--execute', action='store_true', help='执行工具')
    parser.add_argument('--args', type=str, help='JSON格式的参数')
    
    # 添加具体的操作参数
    parser.add_argument('--info', choices=['system', 'uptime', 'cpu', 'memory', 'disk', 'process', 'network', 'load', 'all'], 
                       help='要获取的信息类型')
    parser.add_argument('--disk-path', type=str, default='/', help='磁盘检查路径（用于disk信息）')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='输出格式')
    
    args = parser.parse_args()
    
    # 处理 --description 参数
    if args.description:
        description = """系统信息扩展工具 - 获取系统的各种状态信息
支持的操作：
- system: 系统基本信息（操作系统、主机名、版本等）
- uptime: 系统运行时间
- cpu: CPU信息（核心数、使用率、频率）
- memory: 内存使用情况
- disk: 磁盘使用情况
- process: 进程数量
- network: 网络流量统计
- load: 系统负载（仅Unix系统）
- all: 所有信息

示例：
  --info system          # 获取系统基本信息
  --info cpu             # 获取CPU信息
  --info memory          # 获取内存信息
  --info disk --disk-path /home  # 获取指定磁盘信息
  --info all --format json       # 获取所有信息，JSON格式"""
        print(description)
        return
    
    # 处理 --parameters 参数
    if args.parameters:
        parameters = {
            "type": "object",
            "properties": {
                "info": {
                    "type": "string",
                    "enum": ["system", "uptime", "cpu", "memory", "disk", "process", "network", "load", "all"],
                    "description": "要获取的信息类型"
                },
                "disk_path": {
                    "type": "string",
                    "description": "磁盘检查路径（当info为disk时使用）",
                    "default": "/"
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "json"],
                    "description": "输出格式",
                    "default": "text"
                }
            },
            "required": ["info"]
        }
        print(json.dumps(parameters, ensure_ascii=False))
        return
    
    # 处理 --execute 参数
    if args.execute and args.args:
        try:
            # 解析参数
            params = json.loads(args.args)
            info_type = params.get('info', 'all')
            disk_path = params.get('disk_path', '/')
            output_format = params.get('format', 'text')
            
            # 收集信息
            result = {}
            
            if info_type == 'system' or info_type == 'all':
                result['系统信息'] = get_system_info()
            
            if info_type == 'uptime' or info_type == 'all':
                result['运行时间'] = get_uptime()
            
            if info_type == 'cpu' or info_type == 'all':
                result['CPU信息'] = get_cpu_info()
            
            if info_type == 'memory' or info_type == 'all':
                result['内存信息'] = get_memory_info()
            
            if info_type == 'disk' or info_type == 'all':
                result['磁盘信息'] = get_disk_info(disk_path)
            
            if info_type == 'process' or info_type == 'all':
                result['进程信息'] = get_process_count()
            
            if info_type == 'network' or info_type == 'all':
                result['网络信息'] = get_network_info()
            
            if info_type == 'load' or info_type == 'all':
                result['系统负载'] = get_load_average()
            
            # 输出结果
            if output_format == 'json':
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                for category, data in result.items():
                    print(f"\n【{category}】")
                    for key, value in data.items():
                        print(f"  {key}: {value}")
            
        except json.JSONDecodeError as e:
            print(f"❌ 参数解析错误: {e}")
        except ImportError as e:
            print(f"❌ 缺少依赖库: {e}。请安装 psutil: pip install psutil")
        except Exception as e:
            print(f"❌ 执行错误: {e}")
    
    else:
        # 如果没有指定任何参数，显示帮助
        parser.print_help()


if __name__ == "__main__":
    main()