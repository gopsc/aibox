#!/bin/bash
# qemu-run.sh - 修复库路径问题

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error_exit() {
    echo -e "${RED}错误: $1${NC}" >&2
    exit 1
}

detect_arch() {
    local appimage="$1"
    if file "$appimage" | grep -qi "aarch64\|ARM aarch64"; then
        echo "arm64"
    else
        echo "x86_64"
    fi
}

find_executable() {
    local dir="$1"
    
    # 优先查找ELF二进制文件
    for path in "usr/bin" "bin" ""; do
        if [[ -d "$dir/$path" ]]; then
            for prog in "$dir/$path"/*; do
                if [[ -f "$prog" ]] && [[ -x "$prog" ]]; then
                    if file "$prog" 2>/dev/null | grep -q "ELF.*executable"; then
                        echo "$prog"
                        return 0
                    fi
                fi
            done
        fi
    done
    
    [[ -x "$dir/AppRun" ]] && echo "$dir/AppRun"
    return 1
}

find_library_path() {
    local rootfs="$1"
    local lib_name="$2"
    
    # 在rootfs中查找库文件
    local lib_path=$(find "$rootfs" -name "$lib_name" 2>/dev/null | head -1)
    if [[ -n "$lib_path" ]]; then
        echo "$(dirname "$lib_path")"
        return 0
    fi
    return 1
}

run_appimage() {
    local appimage="$1"
    shift
    local args=("$@")
    
    appimage=$(realpath "$appimage")
    [[ ! -f "$appimage" ]] && error_exit "文件不存在"
    [[ ! -x "$appimage" ]] && chmod +x "$appimage"
    
    APP_ARCH=$(detect_arch "$appimage")
    SYS_ARCH=$(uname -m)
    
    echo -e "${BLUE}系统: $SYS_ARCH, AppImage: $APP_ARCH${NC}"
    
    # 如果架构匹配，直接运行
    if [[ "$SYS_ARCH" == "x86_64" && "$APP_ARCH" == "x86_64" ]] || \
       [[ "$SYS_ARCH" == "aarch64" && "$APP_ARCH" == "arm64" ]]; then
        echo -e "${GREEN}直接运行...${NC}"
        exec "$appimage" "${args[@]}"
    fi
    
    echo -e "${YELLOW}使用QEMU运行ARM64程序...${NC}"
    
    QEMU_BIN="qemu-aarch64-static"
    if ! command -v "$QEMU_BIN" &>/dev/null; then
        echo -e "${YELLOW}安装QEMU...${NC}"
        sudo apt update && sudo apt install -y qemu-user-static
    fi
    
    TEMP_DIR=$(mktemp -d)
    echo -e "${GREEN}临时目录: $TEMP_DIR${NC}"
    
    cd "$TEMP_DIR"
    cp "$appimage" .
    chmod +x "$(basename "$appimage")"
    
    echo -e "${YELLOW}提取AppImage...${NC}"
    if ! "$QEMU_BIN" "$(basename "$appimage")" --appimage-extract 2>&1; then
        error_exit "提取失败"
    fi
    
    cd squashfs-root
    ROOTFS="$PWD"
    
    EXECUTABLE=$(find_executable "$ROOTFS")
    if [[ -z "$EXECUTABLE" ]]; then
        error_exit "未找到可执行文件"
    fi
    
    echo -e "${GREEN}可执行文件: $(basename "$EXECUTABLE")${NC}"
    
    # 查找动态链接器
    LD_SO=$(find "$ROOTFS" -name "ld-linux-aarch64*.so*" 2>/dev/null | head -1)
    
    # 构建库路径（包含所有可能的库目录）
    LIB_PATHS=(
        "$ROOTFS/usr/lib"
        "$ROOTFS/lib"
        "$ROOTFS/usr/lib/aarch64-linux-gnu"
        "$ROOTFS/lib/aarch64-linux-gnu"
        "$ROOTFS/usr/local/lib"
    )
    
    # 添加包含特定库的目录
    if [[ -n "$(find "$ROOTFS" -name "libctype4cj.so" 2>/dev/null)" ]]; then
        local ctype_path=$(find "$ROOTFS" -name "libctype4cj.so" -exec dirname {} \; 2>/dev/null | head -1)
        if [[ -n "$ctype_path" ]]; then
            LIB_PATHS+=("$ctype_path")
        fi
    fi
    
    # 构建LD_LIBRARY_PATH
    LD_LIBRARY_PATH=""
    for path in "${LIB_PATHS[@]}"; do
        if [[ -d "$path" ]]; then
            LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:$path"
        fi
    done
    LD_LIBRARY_PATH="${LD_LIBRARY_PATH#:}"
    
    echo -e "${YELLOW}库路径: $LD_LIBRARY_PATH${NC}"
    
    # 设置QEMU环境变量
    export QEMU_LD_PREFIX="$ROOTFS"
    export QEMU_SET_ENV="LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
    
    echo -e "${BLUE}════════════════════════════════${NC}"
    echo -e "${GREEN}运行...${NC}"
    echo -e "${BLUE}════════════════════════════════${NC}"
    
    # 运行
    if [[ -n "$LD_SO" ]] && [[ -f "$LD_SO" ]]; then
        echo -e "${GREEN}使用动态链接器: $(basename "$LD_SO")${NC}"
        echo -e "${YELLOW}命令: $QEMU_BIN -L \"$ROOTFS\" -E LD_LIBRARY_PATH=\"$LD_LIBRARY_PATH\" \"$LD_SO\" \"$EXECUTABLE\" ${args[@]}${NC}"
        $QEMU_BIN -L "$ROOTFS" -E LD_LIBRARY_PATH="$LD_LIBRARY_PATH" "$LD_SO" "$EXECUTABLE" "${args[@]}"
    else
        echo -e "${YELLOW}未找到动态链接器，直接运行${NC}"
        $QEMU_BIN -L "$ROOTFS" -E LD_LIBRARY_PATH="$LD_LIBRARY_PATH" "$EXECUTABLE" "${args[@]}"
    fi
    
    local exit_code=$?
    
    # 清理
    cd /
    rm -rf "$TEMP_DIR"
    
    exit $exit_code
}

if [[ $# -lt 1 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    echo "用法: $0 <AppImage文件> [参数...]"
    echo "示例: $0 bot4cj.AppImage --help"
    exit 0
fi

run_appimage "$@"
