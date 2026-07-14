#!/bin/bash

# qing_famer - 检查土壤温湿度的技能
# 基于 ADS1115 读取土壤湿度（通道0，百分比）和土壤温度（通道1，映射-20~80°C）

show_help() {
    cat <<EOF
检查土壤温湿度 - 通过ADS1115读取土壤湿度(百分比)和土壤温度(°C)

用法: qing_famer [选项]

选项:
  -h, --help   显示帮助信息

说明:
  读取 ADS1115 通道0 的湿度百分比和通道1 的温度值（映射到 -40~80°C 范围）

示例:
  qing_famer            # 显示当前的土壤温湿度
  qing_famer --help     # 显示帮助信息
EOF
    exit 0
}

# 解析参数
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
fi

# 测量土壤湿度（通道0，百分比显示）
H=$(ads1115 -p 0 -c 0 --percent)
echo "测量土壤湿度：${H}"

# 测量土壤温度（通道1，映射到 -20~80°C）
T=$(ads1115 -p 0 -c 1 --map=-40,80)
echo "测量土壤温度：${T}"
