#!/bin/bash
# appimage-packager.sh - 简单的AppImage打包工具

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
${GREEN}AppImage 打包工具${NC}
${BLUE}════════════════════════════════${NC}

${YELLOW}用法:${NC}
    $0 [选项] <可执行文件> [输出名称]

${YELLOW}选项:${NC}
    -h, --help              显示帮助信息
    -i, --icon <文件>       指定图标文件 (PNG格式)
    -d, --data <目录>       包含数据文件目录
    -n, --name <名称>       应用程序名称
    -v, --version <版本>    设置版本号
    -t, --terminal          在终端中运行

${YELLOW}示例:${NC}
    $0 ./myapp                      # 基本打包
    $0 -i icon.png ./myapp          # 带图标
    $0 -d data/ ./myapp MyApp       # 包含数据文件
    $0 -t ./cli-tool                # 命令行工具

${BLUE}════════════════════════════════${NC}
EOF
}

# 创建默认图标
create_default_icon() {
    local icon_path="$1"
    mkdir -p "$(dirname "$icon_path")"
    
    # 创建一个简单的1x1像素PNG图标
    echo -ne '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x05\x01\x00\x00\x00\x00IEND\xaeB`\x82' > "$icon_path"
}

# 创建AppRun脚本
create_apprun() {
    local app_dir="$1"
    local exec_name="$2"
    local terminal="$3"
    
    cat > "$app_dir/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$LD_LIBRARY_PATH"
export XDG_DATA_DIRS="$HERE/usr/share:$XDG_DATA_DIRS"

exec "$HERE/usr/bin/EXEC_NAME" "$@"
EOF
    
    # 替换可执行文件名
    sed -i "s/EXEC_NAME/$exec_name/g" "$app_dir/AppRun"
    chmod +x "$app_dir/AppRun"
}

# 收集动态库依赖
collect_dependencies() {
    local executable="$1"
    local lib_dir="$2"
    
    echo -e "${YELLOW}收集动态库依赖...${NC}"
    
    mkdir -p "$lib_dir"
    local count=0
    
    # 使用ldd获取依赖
    ldd "$executable" 2>/dev/null | grep "=> /" | awk '{print $3}' | while read -r lib; do
        if [ -f "$lib" ] && [ ! -f "$lib_dir/$(basename "$lib")" ]; then
            cp -f "$lib" "$lib_dir/" 2>/dev/null && {
                echo "  ✓ $(basename "$lib")"
                count=$((count + 1))
            }
        fi
    done
    
    echo -e "${GREEN}✓ 已收集 $count 个库${NC}"
}

# 主程序
main() {
    # 默认参数
    ICON_FILE=""
    DATA_DIR=""
    APP_NAME=""
    APP_VERSION="1.0"
    TERMINAL=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -i|--icon)
                ICON_FILE="$2"
                shift 2
                ;;
            -d|--data)
                DATA_DIR="$2"
                shift 2
                ;;
            -n|--name)
                APP_NAME="$2"
                shift 2
                ;;
            -v|--version)
                APP_VERSION="$2"
                shift 2
                ;;
            -t|--terminal)
                TERMINAL=true
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
    
    EXECUTABLE="$1"
    OUTPUT_NAME="${2:-$(basename "$EXECUTABLE" .AppImage)}"
    
    # 检查可执行文件
    if [[ ! -f "$EXECUTABLE" ]]; then
        echo -e "${RED}错误: 文件不存在: $EXECUTABLE${NC}"
        exit 1
    fi
    
    if [[ ! -x "$EXECUTABLE" ]]; then
        echo -e "${YELLOW}添加执行权限...${NC}"
        chmod +x "$EXECUTABLE"
    fi
    
    # 设置应用程序名称
    if [[ -z "$APP_NAME" ]]; then
        APP_NAME="$OUTPUT_NAME"
    fi
    
    echo -e "${BLUE}════════════════════════════════${NC}"
    echo -e "${GREEN}AppImage 打包工具${NC}"
    echo -e "${BLUE}════════════════════════════════${NC}"
    echo "程序: $(basename "$EXECUTABLE")"
    echo "输出: $OUTPUT_NAME.AppImage"
    echo "名称: $APP_NAME"
    echo "版本: $APP_VERSION"
    echo ""
    
    # 清理旧文件
    rm -rf AppDir "${OUTPUT_NAME}.AppImage"
    
    # 步骤1: 创建目录结构
    echo -e "${YELLOW}[1/6] 创建目录结构...${NC}"
    mkdir -p AppDir/usr/bin
    mkdir -p AppDir/usr/lib
    mkdir -p AppDir/usr/share/applications
    mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps
    
    # 步骤2: 复制可执行文件
    echo -e "${YELLOW}[2/6] 复制可执行文件...${NC}"
    EXEC_NAME=$(basename "$EXECUTABLE")
    cp "$EXECUTABLE" "AppDir/usr/bin/$EXEC_NAME"
    echo -e "${GREEN}✓ 已复制: $EXEC_NAME${NC}"
    
    # 步骤3: 收集动态库
    collect_dependencies "$EXECUTABLE" "AppDir/usr/lib"
    
    # 步骤4: 处理数据文件
    if [[ -n "$DATA_DIR" ]] && [[ -d "$DATA_DIR" ]]; then
        echo -e "${YELLOW}[3/6] 复制数据文件...${NC}"
        cp -r "$DATA_DIR"/* "AppDir/usr/share/$APP_NAME/" 2>/dev/null || true
        echo -e "${GREEN}✓ 已复制数据文件${NC}"
    fi
    
    # 步骤5: 处理图标
    echo -e "${YELLOW}[4/6] 设置图标...${NC}"
    if [[ -n "$ICON_FILE" ]] && [[ -f "$ICON_FILE" ]]; then
        cp "$ICON_FILE" "AppDir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
        cp "$ICON_FILE" "AppDir/$APP_NAME.png"
        echo -e "${GREEN}✓ 使用自定义图标${NC}"
    else
        create_default_icon "AppDir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
        create_default_icon "AppDir/$APP_NAME.png"
        echo -e "${YELLOW}⚠ 使用默认图标${NC}"
    fi
    cp "AppDir/$APP_NAME.png" "AppDir/.DirIcon"
    
    # 步骤6: 创建桌面文件
    echo -e "${YELLOW}[5/6] 创建桌面文件...${NC}"
    TERMINAL_FLAG="$([ "$TERMINAL" = true ] && echo "true" || echo "false")"
    cat > "AppDir/usr/share/applications/$APP_NAME.desktop" << EOF
[Desktop Entry]
Version=$APP_VERSION
Type=Application
Name=$APP_NAME
Comment=$APP_NAME application
Exec=$EXEC_NAME
Icon=$APP_NAME
Terminal=$TERMINAL_FLAG
Categories=Utility;
StartupNotify=false
EOF
    ln -sf usr/share/applications/$APP_NAME.desktop "AppDir/"
    
    # 步骤7: 创建AppRun
    echo -e "${YELLOW}[6/6] 创建AppRun...${NC}"
    create_apprun "AppDir" "$EXEC_NAME" "$TERMINAL"
    
    # 步骤8: 打包AppImage
    echo -e "\n${YELLOW}打包AppImage...${NC}"
    
    if command -v appimagetool >/dev/null 2>&1; then
        OUTPUT_FILE="${OUTPUT_NAME}.AppImage"
        appimagetool --no-appstream AppDir "$OUTPUT_FILE" 2>&1 | grep -v "WARNING" | grep -v "gpg" || true
        
        if [[ -f "$OUTPUT_FILE" ]]; then
            chmod +x "$OUTPUT_FILE"
            echo -e "\n${GREEN}════════════════════════════════${NC}"
            echo -e "${GREEN}✅ 打包成功！${NC}"
            echo -e "${GREEN}════════════════════════════════${NC}"
            echo "📦 输出: $(realpath "$OUTPUT_FILE")"
            echo "📏 大小: $(du -h "$OUTPUT_FILE" | cut -f1)"
            echo ""
            echo "🚀 运行: ./$OUTPUT_FILE"
            
            # 清理
            rm -rf AppDir
        else
            echo -e "${RED}❌ 打包失败${NC}"
            exit 1
        fi
    else
        echo -e "${RED}错误: 未找到 appimagetool${NC}"
        echo ""
        echo "请下载 appimagetool:"
        echo "  wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        echo "  chmod +x appimagetool-x86_64.AppImage"
        echo "  sudo mv appimagetool-x86_64.AppImage /usr/local/bin/appimagetool"
        exit 1
    fi
}

# 运行主程序
main "$@"
