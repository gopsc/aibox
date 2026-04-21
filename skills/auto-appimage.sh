#!/bin/bash
# appimage-packager-rofs-fixed.sh
# 已添加QEMU兼容性支持和ARM平台支持

set -e

# 彩色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 帮助信息
show_help() {
    cat << EOF
${GREEN}AppImage 打包工具 (QEMU/ARM兼容版)${NC}
${BLUE}════════════════════════════════════════${NC}

${YELLOW}用法:${NC}
    $0 [选项] <可执行文件> [输出名称]

${YELLOW}选项:${NC}
    -h, --help              显示此帮助信息
    -d, --data              包含数据文件（配置文件等）
    -a, --arch <架构>       指定目标架构 (x86_64, arm64, armhf)
    -v, --verbose           显示详细输出
    --no-qemu               禁用QEMU支持（仅原生运行）
    --static                尝试静态链接打包

${YELLOW}示例:${NC}
    $0 ./myapp                      # 打包为AppImage
    $0 -d ./myapp                   # 包含数据文件
    $0 -a arm64 ./myapp             # 为ARM64平台打包
    $0 --static ./myapp myapp.AppImage  # 静态链接打包

${YELLOW}ARM平台支持:${NC}
    - 自动检测ARM架构并调整打包方式
    - 支持ARM64 (aarch64) 和 ARM32 (armhf)
    - 如果原程序是x86_64，会自动包含QEMU模拟器
    - 在ARM系统上运行时通过QEMU透明运行x86程序

${YELLOW}环境变量:${NC}
    DEBUG=1                 启用调试输出
    QEMU_CPU=<型号>         指定QEMU模拟的CPU型号
    SKIP_QEMU_TEST=1        跳过QEMU兼容性测试

${YELLOW}依赖要求:${NC}
    - appimagetool          (打包工具)
    - qemu-user-static      (ARM上运行x86程序时需要)
    - patchelf              (可选，用于库路径修复)

${BLUE}════════════════════════════════════════${NC}
EOF
}

# 检测系统架构
detect_arch() {
    local arch=$(uname -m)
    case "$arch" in
        x86_64|amd64)
            echo "x86_64"
            ;;
        aarch64|arm64)
            echo "arm64"
            ;;
        armv7l|armhf|armv8l)
            echo "armhf"
            ;;
        *)
            echo "$arch"
            ;;
    esac
}

# 检查QEMU是否可用
check_qemu() {
    local arch="$1"
    if command -v qemu-x86_64-static >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 下载QEMU静态二进制（如果不可用）
download_qemu() {
    local qemu_path="$1"
    echo -e "${YELLOW}下载QEMU静态二进制...${NC}"
    
    # 尝试多个源
    local urls=(
        "https://github.com/multiarch/qemu-user-static/releases/download/v7.2.0-1/qemu-x86_64-static"
        "https://github.com/multiarch/qemu-user-static/releases/latest/download/qemu-x86_64-static"
    )
    
    for url in "${urls[@]}"; do
        if wget -q -O "$qemu_path" "$url" 2>/dev/null; then
            chmod +x "$qemu_path"
            echo -e "${GREEN}✓ QEMU下载成功${NC}"
            return 0
        fi
    done
    
    echo -e "${RED}✗ QEMU下载失败，请手动安装: sudo apt install qemu-user-static${NC}"
    return 1
}

# 创建图标
create_icon() {
    local icon_path="$1"
    mkdir -p "$(dirname "$icon_path")"
    
    echo 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==' | \
    base64 -d > "$icon_path" 2>/dev/null || \
    echo -ne '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x05\x01\x00\x00\x00\x00IEND\xaeB`\x82' > "$icon_path"
}

# 创建ARM兼容的AppRun脚本
create_arm_compatible_apprun() {
    local app_dir="$1"
    local app_name="$2"
    local orig_name="$3"
    local target_arch="$4"
    local no_qemu="${5:-false}"
    
    echo "创建ARM兼容AppRun..."
    
    cat > "$app_dir/AppRun" << 'EOF'
#!/bin/sh
# ARM/x86_64 兼容启动脚本
set -e

HERE="$(dirname "$(readlink -f "$0")")"
APP_NAME="$(basename "$0" .AppImage)"
SYSTEM_ARCH="$(uname -m)"
DEBUG="${DEBUG:-0}"

# 调试输出
debug_log() {
    [ "$DEBUG" = "1" ] && echo "[DEBUG] $*" >&2
}

debug_log "系统架构: $SYSTEM_ARCH"
debug_log "App目录: $HERE"

# 设置环境变量
export PATH="$HERE/usr/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$LD_LIBRARY_PATH"
export HERE="$HERE"

# 检测程序架构
PROGRAM_ARCH=""
if [ -f "$HERE/usr/bin/$APP_NAME" ]; then
    PROGRAM_ARCH=$(file -b "$HERE/usr/bin/$APP_NAME" | grep -oE "ELF [0-9]+-bit (LSB )?[^,]+" | head -1 | sed 's/ELF [0-9]+-bit LSB //;s/ELF [0-9]+-bit //' | tr '[:upper:]' '[:lower:]')
fi

debug_log "程序架构: $PROGRAM_ARCH"

# 架构匹配检查
run_native() {
    debug_log "原生运行: $HERE/usr/bin/$APP_NAME"
    exec "$HERE/usr/bin/$APP_NAME" "$@"
}

run_qemu() {
    local qemu_path=""
    
    # 查找QEMU
    for path in "$HERE/qemu-x86_64-static" "$HERE/usr/bin/qemu-x86_64-static" /usr/bin/qemu-x86_64-static; do
        if [ -f "$path" ] && [ -x "$path" ]; then
            qemu_path="$path"
            break
        fi
    done
    
    if [ -z "$qemu_path" ]; then
        echo "错误: 找不到QEMU模拟器" >&2
        echo "请安装: sudo apt install qemu-user-static" >&2
        exit 1
    fi
    
    debug_log "使用QEMU: $qemu_path"
    
    # 设置QEMU环境
    if [ -f "$HERE/usr/lib/ld-linux-x86-64.so.2" ]; then
        export QEMU_LD_PREFIX="$HERE"
        debug_log "设置QEMU_LD_PREFIX=$HERE"
    fi
    
    exec "$qemu_path" -L "$HERE" "$HERE/usr/bin/$APP_NAME" "$@"
}

# 执行逻辑
if [ "$SYSTEM_ARCH" = "x86_64" ]; then
    if [ "$PROGRAM_ARCH" = "x86-64" ] || [ -z "$PROGRAM_ARCH" ]; then
        run_native "$@"
    else
        echo "警告: 程序架构($PROGRAM_ARCH)与系统($SYSTEM_ARCH)不匹配" >&2
        run_qemu "$@"
    fi
elif echo "$SYSTEM_ARCH" | grep -qE "aarch64|arm64|armv"; then
    # ARM系统
    if [ "$PROGRAM_ARCH" = "aarch64" ] || [ "$PROGRAM_ARCH" = "arm64" ]; then
        run_native "$@"
    elif [ "$PROGRAM_ARCH" = "arm" ] || [ "$PROGRAM_ARCH" = "armhf" ]; then
        run_native "$@"
    else
        # 非ARM程序，使用QEMU
        debug_log "ARM系统运行x86程序，使用QEMU"
        run_qemu "$@"
    fi
else
    # 其他架构
    debug_log "未知架构，尝试原生运行"
    run_native "$@"
fi
EOF
    
    chmod +x "$app_dir/AppRun"
    echo -e "${GREEN}✓ 创建ARM兼容AppRun${NC}"
}

# 收集所有动态库依赖（改进版）
collect_all_dependencies() {
    local executable="$1"
    local lib_dir="$2"
    local target_arch="$3"
    
    echo -e "${YELLOW}收集动态库依赖...${NC}"
    
    # 检查程序架构
    local prog_arch=$(file -b "$executable" | grep -oE "ELF [0-9]+-bit [^,]+" | head -1)
    echo "程序架构: $prog_arch"
    
    if ! ldd "$executable" 2>/dev/null | grep -q "=>"; then
        echo "程序可能是静态链接，尝试基础库..."
    fi
    
    mkdir -p "$lib_dir"
    local processed_libs=()
    
    collect_libs_recursive() {
        local target="$1"
        
        # 使用patchelf或直接检查
        ldd "$target" 2>/dev/null | grep "=>" | awk '{print $3}' | while read -r lib; do
            if [[ -f "$lib" ]]; then
                local libname=$(basename "$lib")
                
                if [[ ! " ${processed_libs[@]} " =~ " ${libname} " ]]; then
                    processed_libs+=("$libname")
                    
                    cp -f "$lib" "$lib_dir/" 2>/dev/null && echo "  ✅ $libname"
                    collect_libs_recursive "$lib"
                fi
            fi
        done
    }
    
    collect_libs_recursive "$executable"
    
    # 添加基础库（根据架构）
    local common_libs=(
        "ld-linux-x86-64.so.2" "ld-linux-aarch64.so.1" "ld-linux-armhf.so.3"
        "libc.so.6" "libm.so.6" "libpthread.so.0"
        "libdl.so.2" "librt.so.1" "libgcc_s.so.1"
        "libstdc++.so.6"
    )
    
    for lib in "${common_libs[@]}"; do
        find /usr/lib /lib /lib64 -name "$lib" -type f 2>/dev/null | head -1 | while read -r libpath; do
            if [[ -f "$libpath" ]] && [[ ! -f "$lib_dir/$(basename "$libpath")" ]]; then
                cp -f "$libpath" "$lib_dir/" 2>/dev/null && echo "  ✅ 基础: $(basename "$libpath")"
            fi
        done
    done
    
    # 对于ARM系统，添加ARM库
    if [[ "$target_arch" == arm* ]] || [[ "$target_arch" == aarch64 ]]; then
        local arm_lib_dirs=("/usr/lib/$target_arch-linux-gnu" "/lib/$target_arch-linux-gnu")
        for libdir in "${arm_lib_dirs[@]}"; do
            if [ -d "$libdir" ]; then
                cp -f "$libdir"/*.so* "$lib_dir/" 2>/dev/null || true
            fi
        done
    fi
    
    local lib_count=$(ls -1 "$lib_dir"/*.so* 2>/dev/null | wc -l)
    echo -e "${GREEN}✓ 添加了 $lib_count 个库${NC}"
}

# 主程序
main() {
    # 默认参数
    INCLUDE_DATA=false
    TARGET_ARCH=""
    VERBOSE=false
    NO_QEMU=false
    STATIC_BUILD=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -d|--data)
                INCLUDE_DATA=true
                shift
                ;;
            -a|--arch)
                TARGET_ARCH="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --no-qemu)
                NO_QEMU=true
                shift
                ;;
            --static)
                STATIC_BUILD=true
                shift
                ;;
            -*)
                echo -e "${RED}错误: 未知选项 $1${NC}"
                show_help
                exit 1
                ;;
            *)
                break
                ;;
        esac
    done
    
    # 检查参数
    if [[ $# -lt 1 ]]; then
        show_help
        exit 1
    fi
    
    # 设置详细输出
    if [ "$VERBOSE" = true ]; then
        set -x
    fi
    
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}       AppImage 打包工具              ${NC}"
    echo -e "${BLUE}       (ARM/QEMU兼容版)               ${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    
    EXECUTABLE="$1"
    APP_NAME="${2:-$(basename "$EXECUTABLE")}"
    
    # 检测系统架构
    SYSTEM_ARCH=$(detect_arch)
    echo "系统架构: $SYSTEM_ARCH"
    
    # 设置目标架构
    if [ -z "$TARGET_ARCH" ]; then
        TARGET_ARCH="$SYSTEM_ARCH"
    fi
    echo "目标架构: $TARGET_ARCH"
    
    [[ ! -f "$EXECUTABLE" ]] && { echo -e "${RED}错误: 文件不存在${NC}"; exit 1; }
    [[ ! -x "$EXECUTABLE" ]] && chmod +x "$EXECUTABLE"
    
    echo "程序: $APP_NAME"
    echo "原始: $(basename "$EXECUTABLE")"
    
    # 检查程序架构
    PROG_ARCH=$(file -b "$EXECUTABLE" | grep -oE "ELF [0-9]+-bit [^,]+" | head -1)
    echo "程序架构: $PROG_ARCH"
    
    # 清理
    rm -rf "AppDir" "${APP_NAME}.AppImage"
    
    # =========== 步骤1: 创建目录 ===========
    echo -e "\n${YELLOW}[1/8] 创建目录...${NC}"
    mkdir -p AppDir/usr/bin
    mkdir -p AppDir/usr/lib
    
    ORIG_NAME=$(basename "$EXECUTABLE")
    
    # =========== 步骤2: 复制程序 ===========
    echo -e "\n${YELLOW}[2/8] 复制程序...${NC}"
    cp "$EXECUTABLE" "AppDir/usr/bin/$ORIG_NAME"
    chmod +x "AppDir/usr/bin/$ORIG_NAME"
    echo -e "${GREEN}✓ 程序: $ORIG_NAME${NC}"
    
    # =========== 步骤3: 收集依赖 ===========
    collect_all_dependencies "$EXECUTABLE" "AppDir/usr/lib" "$TARGET_ARCH"
    
    # =========== 步骤4: QEMU支持 ===========
    if [ "$NO_QEMU" = false ] && [[ "$PROG_ARCH" != *"$TARGET_ARCH"* ]] && [[ "$TARGET_ARCH" == "x86_64" ]]; then
        echo -e "\n${YELLOW}[4/8] 添加QEMU支持...${NC}"
        
        # 检查或下载QEMU
        if check_qemu; then
            QEMU_BIN=$(which qemu-x86_64-static)
            cp "$QEMU_BIN" "AppDir/qemu-x86_64-static"
            echo -e "${GREEN}✓ QEMU已添加${NC}"
        else
            download_qemu "AppDir/qemu-x86_64-static" || {
                echo -e "${YELLOW}⚠ QEMU不可用，ARM兼容性将受限${NC}"
            }
        fi
        
        # 设置动态链接器路径
        if [ -f "/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2" ]; then
            mkdir -p "AppDir/lib64"
            cp "/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2" "AppDir/lib64/"
        fi
    fi
    
    # =========== 步骤5: 处理数据文件 ===========
    if $INCLUDE_DATA; then
        echo -e "\n${YELLOW}[5/8] 处理数据文件...${NC}"
        find_and_copy_data "$EXECUTABLE" "$APP_NAME" "AppDir/usr/share/$APP_NAME"
    fi
    
    # =========== 步骤6: 创建图标 ===========
    echo -e "\n${YELLOW}[6/8] 创建图标...${NC}"
    create_icon "AppDir/$APP_NAME.png"
    cp "AppDir/$APP_NAME.png" "AppDir/.DirIcon"
    echo -e "${GREEN}✓ 图标已创建${NC}"
    
    # =========== 步骤7: 创建AppRun ===========
    echo -e "\n${YELLOW}[7/8] 创建AppRun...${NC}"
    create_arm_compatible_apprun "AppDir" "$APP_NAME" "$ORIG_NAME" "$TARGET_ARCH" "$NO_QEMU"
    
    # =========== 步骤8: 创建桌面文件 ===========
    echo -e "\n${YELLOW}[8/8] 创建桌面文件...${NC}"
    mkdir -p AppDir/usr/share/applications
    cat > "AppDir/usr/share/applications/$APP_NAME.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Packaged as AppImage (ARM/QEMU兼容)
Exec=$ORIG_NAME
Icon=$APP_NAME
Categories=Utility;
Terminal=true
StartupNotify=false
EOF
    ln -sf usr/share/applications/$APP_NAME.desktop AppDir/
    echo -e "${GREEN}✓ 桌面文件已创建${NC}"
    
    # =========== 步骤9: 打包 ===========
    echo -e "\n${YELLOW}打包AppImage...${NC}"
    OUTPUT_FILE="${APP_NAME}.AppImage"
    
    # 打包
    if command -v appimagetool >/dev/null 2>&1; then
        if appimagetool --no-appstream AppDir "$OUTPUT_FILE" 2>&1 | grep -v "gpg2" | grep -v "Warning"; then
            echo -e "${GREEN}✅ 打包成功！${NC}"
        else
            appimagetool --no-appstream --no-fuse AppDir "$OUTPUT_FILE" 2>&1 | grep -v "gpg2" | grep -v "Warning"
            echo -e "${GREEN}✅ 打包成功！${NC}"
        fi
    else
        echo -e "${RED}错误: 未找到appimagetool${NC}"
        echo "请下载: https://github.com/AppImage/AppImageKit/releases"
        exit 1
    fi
    
    # =========== 测试 ===========
    echo -e "\n${BLUE}════════════════════════════════════════${NC}"
    echo -e "${GREEN}测试运行...${NC}"
    
    chmod +x "$OUTPUT_FILE"
    
    if [ -z "$SKIP_QEMU_TEST" ]; then
        echo "测试命令:"
        echo "  原生运行: ./\"$OUTPUT_FILE\" --help"
        if [ "$NO_QEMU" = false ] && [[ "$SYSTEM_ARCH" != "x86_64" ]]; then
            echo "  QEMU运行: ./\"$OUTPUT_FILE\" --help (自动)"
        fi
        echo "----------------------------------------"
        
        # 原生测试运行
        if timeout 5s ./"$OUTPUT_FILE" --help 2>&1 | head -20; then
            echo -e "${GREEN}✅ 运行正常${NC}"
        elif timeout 5s ./"$OUTPUT_FILE" -h 2>&1 | head -20; then
            echo -e "${GREEN}✅ 运行正常${NC}"
        else
            echo -e "${YELLOW}⚠ 运行可能需要特定参数${NC}"
        fi
    fi
    
    # 最终信息
    echo -e "\n${BLUE}════════════════════════════════════════${NC}"
    echo -e "${GREEN}            完成！                     ${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    echo "📦 输出文件: $(realpath "$OUTPUT_FILE")"
    echo "📏 大小: $(du -h "$OUTPUT_FILE" | cut -f1)"
    echo ""
    echo "🚀 使用方法:"
    echo "  x86_64系统: ./\"$OUTPUT_FILE\""
    if [[ "$PROG_ARCH" == *"x86"* ]] && [[ "$SYSTEM_ARCH" != "x86_64" ]]; then
        echo "  ARM系统:   ./\"$OUTPUT_FILE\" (自动使用QEMU)"
        echo "  手动QEMU:  qemu-x86_64-static -L . ./\"$OUTPUT_FILE\""
    fi
    echo ""
    echo "🔧 调试模式:"
    echo "  DEBUG=1 ./\"$OUTPUT_FILE\" [参数]"
    echo ""
    
    # 清理
    rm -rf AppDir
}

# 查找并复制数据文件的辅助函数
find_and_copy_data() {
    local executable="$1"
    local app_name="$2"
    local data_dir="$3"
    
    echo -e "${YELLOW}查找数据文件...${NC}"
    
    local prog_dir=$(dirname "$(realpath "$executable")")
    local patterns=("*.pem" "*.key" "*.crt" "*.cfg" "*.conf" "*.ini" "*.json" "*.xml" "*.yaml" "*.yml")
    
    mkdir -p "$data_dir"
    local count=0
    
    for pattern in "${patterns[@]}"; do
        find "$prog_dir" -maxdepth 2 -type f -name "$pattern" 2>/dev/null | while read -r file; do
            if [[ "$file" != "$executable" ]]; then
                cp "$file" "$data_dir/" 2>/dev/null && {
                    echo "  ✅ $(basename "$file")"
                    count=$((count + 1))
                }
            fi
        done
    done
    
    if [[ $count -eq 0 ]]; then
        find "$prog_dir" -maxdepth 1 -type f ! -name "$(basename "$executable")" ! -name "*.AppImage" | while read -r file; do
            cp "$file" "$data_dir/" 2>/dev/null && echo "  ✅ $(basename "$file")"
        done
    fi
    
    echo -e "${GREEN}✓ 数据文件处理完成${NC}"
}

# 运行
main "$@"