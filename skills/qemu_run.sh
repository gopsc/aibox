#!/bin/bash
# qemu_run_proper.sh

APPIMAGE="$1"
shift

if [[ ! -f "$APPIMAGE" ]]; then
    echo "错误: 文件不存在: $APPIMAGE" >&2
    exit 1
fi

echo "=== 运行AppImage ==="
echo "文件: $(basename "$APPIMAGE")"

# 创建临时目录
TEMP_DIR=$(mktemp -d)
cp ${APPIMAGE} ${TEMP_DIR}
cd "$TEMP_DIR"

# 提取AppImage
echo "提取AppImage..."
qemu-x86_64 "$APPIMAGE" --appimage-extract 2>/dev/null || {
    echo "提取失败" >&2
    exit 1
}

cd squashfs-root
HERE="$PWD"

echo "提取目录: $HERE"

# 查找可执行文件（不输出额外信息）
find_executable() {
    local dir="$1"
    local app_name=$(basename "$APPIMAGE" .AppImage)
    
    # 1. 尝试与AppImage同名的程序
    if [[ -x "$dir/usr/bin/$app_name" ]]; then
        echo "$dir/usr/bin/$app_name"
        return 0
    fi
    
    # 2. 查找usr/bin下的第一个可执行文件
    if [[ -d "$dir/usr/bin" ]]; then
        for prog in "$dir/usr/bin"/*; do
            if [[ -x "$prog" ]]; then
                echo "$prog"
                return 0
            fi
        done
    fi
    
    # 3. 查找AppRun
    if [[ -x "$dir/AppRun" ]]; then
        echo "$dir/AppRun"
        return 0
    fi
    
    return 1
}

# 静默查找可执行文件
EXECUTABLE=$(find_executable "$HERE" 2>/dev/null)

if [[ -z "$EXECUTABLE" ]] || [[ ! -f "$EXECUTABLE" ]]; then
    echo "错误: 未找到可执行文件" >&2
    echo "目录内容:" >&2
    ls -la "$HERE" >&2
    if [[ -d "$HERE/usr/bin" ]]; then
        echo "usr/bin内容:" >&2
        ls -la "$HERE/usr/bin" >&2
    fi
    exit 1
fi

echo "可执行文件: $EXECUTABLE"
echo "文件类型: $(file -b "$EXECUTABLE" 2>/dev/null || echo "无法识别")"

# 运行程序
ARCH=$(uname -m)

if [[ "$ARCH" == "x86_64" ]]; then
    echo "原生x86_64系统，直接运行..."
    exec "$EXECUTABLE" "$@"
else
    echo "ARM系统 ($ARCH)，使用QEMU..."
    
    # 确保lib64目录
    if [[ ! -d "$HERE/lib64" ]] && [[ -f "$HERE/usr/lib/ld-linux-x86-64.so.2" ]]; then
        mkdir -p "$HERE/lib64"
        cp "$HERE/usr/lib/ld-linux-x86-64.so.2" "$HERE/lib64/" 2>/dev/null
    fi
    
    # 直接使用QEMU运行
    exec qemu-x86_64 -L "$HERE" "$EXECUTABLE" "$@"
fi
