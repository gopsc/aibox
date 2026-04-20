#!/usr/bin/env python3
"""系统信息工具 - 获取系统运行时间、CPU、内存、磁盘、网络等状态信息。"""

import sys
import argparse
import platform
import datetime
import os

try:
    import psutil
except ImportError:
    print("❌ 缺少依赖库: psutil。请运行: pip install psutil")
    sys.exit(1)


def get_system_info():
    """获取系统基本信息"""
    return {
        "系统": platform.system(),
        "主机名": platform.node(),
        "版本": platform.version(),
        "架构": platform.machine(),
        "处理器": platform.processor() or "未知",
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
    swap = psutil.swap_memory()
    return {
        "总内存": f"{mem.total / (1024**3):.2f} GB",
        "可用内存": f"{mem.available / (1024**3):.2f} GB",
        "已用内存": f"{mem.used / (1024**3):.2f} GB",
        "内存使用率": f"{mem.percent}%",
        "交换分区总大小": f"{swap.total / (1024**3):.2f} GB" if swap.total > 0 else "无",
        "交换分区使用率": f"{swap.percent}%" if swap.total > 0 else "无"
    }


def get_disk_info(path="/"):
    """获取磁盘信息"""
    try:
        disk = psutil.disk_usage(path)
        return {
            "路径": path,
            "总空间": f"{disk.total / (1024**3):.2f} GB",
            "已用空间": f"{disk.used / (1024**3):.2f} GB",
            "可用空间": f"{disk.free / (1024**3):.2f} GB",
            "使用率": f"{disk.percent}%"
        }
    except Exception as e:
        return {"错误": f"无法获取磁盘信息: {str(e)}"}


def get_all_disks():
    """获取所有磁盘分区信息"""
    partitions = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "挂载点": part.mountpoint,
                "文件系统": part.fstype,
                "总空间": f"{usage.total / (1024**3):.2f} GB",
                "已用空间": f"{usage.used / (1024**3):.2f} GB",
                "可用空间": f"{usage.free / (1024**3):.2f} GB",
                "使用率": f"{usage.percent}%"
            })
        except:
            continue
    return partitions


def get_process_info():
    """获取进程信息"""
    return {
        "进程总数": len(psutil.pids()),
        "运行中进程": sum(1 for p in psutil.process_iter(['status']) if p.info['status'] == 'running'),
        "睡眠进程": sum(1 for p in psutil.process_iter(['status']) if p.info['status'] == 'sleeping')
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


def get_temperature_info():
    """获取温度信息（仅部分系统支持）"""
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return {"信息": "温度传感器信息不可用"}
        
        result = {}
        for name, entries in temps.items():
            for entry in entries:
                result[f"{name}"] = f"{entry.current}°C"
                if hasattr(entry, 'high') and entry.high:
                    result[f"{name}_警告阈值"] = f"{entry.high}°C"
                break
        return result
    except:
        return {"信息": "温度传感器信息不可用"}


def get_battery_info():
    """获取电池信息（仅笔记本）"""
    try:
        battery = psutil.sensors_battery()
        if not battery:
            return {"信息": "电池信息不可用（可能是台式机）"}
        
        return {
            "电量百分比": f"{battery.percent}%",
            "充电中": "是" if battery.power_plugged else "否",
            "剩余时间": str(datetime.timedelta(seconds=battery.secsleft)) if battery.secsleft != -1 else "未知"
        }
    except:
        return {"信息": "电池信息不可用"}


def format_output(data, output_format="text"):
    """格式化输出"""
    if output_format == "json":
        import json
        return json.dumps(data, ensure_ascii=False, indent=2)
    else:
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"\n📁 {key}:")
                for k, v in value.items():
                    lines.append(f"   {k}: {v}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="系统信息工具 - 获取系统运行时间、CPU、内存、磁盘、网络等状态信息。",
        epilog="""
使用示例:
  # 获取系统基本信息
  sysinfo --info system

  # 获取CPU信息
  sysinfo --info cpu

  # 获取内存信息
  sysinfo --info memory

  # 获取指定磁盘信息
  sysinfo --info disk --disk-path /home

  # 获取所有磁盘分区
  sysinfo --info disks

  # 获取所有信息（文本格式）
  sysinfo --info all

  # 获取所有信息（JSON格式）
  sysinfo --info all --format json

  # 获取系统负载
  sysinfo --info load

  # 获取温度信息
  sysinfo --info temperature

  # 获取电池信息
  sysinfo --info battery

  # 组合多个信息
  sysinfo --info cpu --info memory --info disk
        """
    )
    
    # 支持多个info参数
    parser.add_argument("--info", "-i", action="append", 
        choices=["system", "uptime", "cpu", "memory", "disk", "disks", "process", 
                 "network", "load", "temperature", "battery", "all"],
        help="要获取的信息类型（可多次使用）")
    
    parser.add_argument("--disk-path", "-d", type=str, default="/", 
        help="磁盘检查路径（用于disk信息）")
    
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text", 
        help="输出格式（默认: text）")
    
    args = parser.parse_args()
    
    # 如果没有指定任何info，显示帮助
    if not args.info:
        parser.print_help()
        return
    
    # 收集信息
    result = {}
    info_types = args.info
    
    if "all" in info_types:
        info_types = ["system", "uptime", "cpu", "memory", "disk", "disks", "process", "network", "load", "temperature", "battery"]
    
    for info_type in info_types:
        if info_type == "system":
            result["系统信息"] = get_system_info()
        elif info_type == "uptime":
            result["运行时间"] = get_uptime()
        elif info_type == "cpu":
            result["CPU信息"] = get_cpu_info()
        elif info_type == "memory":
            result["内存信息"] = get_memory_info()
        elif info_type == "disk":
            result[f"磁盘信息({args.disk_path})"] = get_disk_info(args.disk_path)
        elif info_type == "disks":
            result["所有磁盘分区"] = get_all_disks()
        elif info_type == "process":
            result["进程信息"] = get_process_info()
        elif info_type == "network":
            result["网络信息"] = get_network_info()
        elif info_type == "load":
            result["系统负载"] = get_load_average()
        elif info_type == "temperature":
            result["温度信息"] = get_temperature_info()
        elif info_type == "battery":
            result["电池信息"] = get_battery_info()
    
    # 输出结果
    print(format_output(result, args.format))


if __name__ == "__main__":
    main()