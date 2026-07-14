#!/usr/bin/env python3
"""
ADS1115: Linux I2C 读取 TI ADS1115 16位 ADC 的命令行工具
"""

import argparse
import sys
import time

# ============================================================
# ADS1115 寄存器地址
# ============================================================
ADS1115_REG_CONVERSION = 0x00
ADS1115_REG_CONFIG = 0x01
ADS1115_REG_LO_THRESH = 0x02
ADS1115_REG_HI_THRESH = 0x03

# ============================================================
# 配置寄存器 bit 定义 (16 位)
# ============================================================

# --- MUX 输入通道 ---
ADS1115_MUX_AIN0_AIN1 = 0x0000  # 差分: P=AIN0, N=AIN1 (默认)
ADS1115_MUX_AIN0_AIN3 = 0x1000  # 差分: P=AIN0, N=AIN3
ADS1115_MUX_AIN1_AIN3 = 0x2000  # 差分: P=AIN1, N=AIN3
ADS1115_MUX_AIN2_AIN3 = 0x3000  # 差分: P=AIN2, N=AIN3
ADS1115_MUX_AIN0_GND  = 0x4000  # 单端: AIN0
ADS1115_MUX_AIN1_GND  = 0x5000  # 单端: AIN1
ADS1115_MUX_AIN2_GND  = 0x6000  # 单端: AIN2
ADS1115_MUX_AIN3_GND  = 0x7000  # 单端: AIN3

# --- PGA 增益 (满量程范围) ---
ADS1115_PGA_6_144V = 0x0000  # ±6.144V  (1LSB=0.1875mV)
ADS1115_PGA_4_096V = 0x0200  # ±4.096V  (1LSB=0.125mV)
ADS1115_PGA_2_048V = 0x0400  # ±2.048V  (1LSB=0.0625mV) (默认)
ADS1115_PGA_1_024V = 0x0600  # ±1.024V  (1LSB=0.03125mV)
ADS1115_PGA_0_512V = 0x0800  # ±0.512V  (1LSB=0.015625mV)
ADS1115_PGA_0_256V = 0x0A00  # ±0.256V  (1LSB=0.0078125mV)

PGA_VALUES = [ADS1115_PGA_6_144V, ADS1115_PGA_4_096V, ADS1115_PGA_2_048V,
              ADS1115_PGA_1_024V, ADS1115_PGA_0_512V, ADS1115_PGA_0_256V]
PGA_FS = [6.144, 4.096, 2.048, 1.024, 0.512, 0.256]
PGA_NAMES = ["±6.144V", "±4.096V", "±2.048V", "±1.024V", "±0.512V", "±0.256V"]

# --- 数据速率 ---
ADS1115_DR_8SPS   = 0x0000  # 8 SPS
ADS1115_DR_16SPS  = 0x0020  # 16 SPS
ADS1115_DR_32SPS  = 0x0040  # 32 SPS
ADS1115_DR_64SPS  = 0x0060  # 64 SPS
ADS1115_DR_128SPS = 0x0080  # 128 SPS (默认)
ADS1115_DR_250SPS = 0x00A0  # 250 SPS
ADS1115_DR_475SPS = 0x00C0  # 475 SPS
ADS1115_DR_860SPS = 0x00E0  # 860 SPS

DR_VALUES = [ADS1115_DR_8SPS, ADS1115_DR_16SPS, ADS1115_DR_32SPS,
             ADS1115_DR_64SPS, ADS1115_DR_128SPS, ADS1115_DR_250SPS,
             ADS1115_DR_475SPS, ADS1115_DR_860SPS]
DR_NAMES = ["8 SPS", "16 SPS", "32 SPS", "64 SPS",
            "128 SPS", "250 SPS", "475 SPS", "860 SPS"]

# --- 比较器 ---
ADS1115_COMP_QUE_DISABLE = 0x0003

# --- 操作模式 ---
ADS1115_MODE_CONTINUOUS = 0x0000
ADS1115_MODE_SINGLE     = 0x0100

# --- 启动转换 ---
ADS1115_OS_START = 0x8000


class ADS1115:
    """ADS1115 16位ADC驱动"""

    def __init__(self, bus=1, address=0x48, pga_idx=2, dr_idx=4):
        """
        初始化 ADS1115

        :param bus: I2C 总线号 (默认1)
        :param address: I2C 设备地址 (默认0x48)
        :param pga_idx: PGA增益索引 0~5 (默认2 = ±2.048V)
        :param dr_idx: 数据速率索引 0~7 (默认4 = 128SPS)
        """
        self.address = address
        self.pga_idx = pga_idx if 0 <= pga_idx <= 5 else 2
        self.dr_idx = dr_idx if 0 <= dr_idx <= 7 else 4
        self.fs_voltage = PGA_FS[self.pga_idx]
        self.config = 0

        # 初始化 I2C
        try:
            from smbus2 import SMBus
            self.bus = SMBus(bus)
        except ImportError:
            print("错误: 需要 smbus2 库，请执行: pip install smbus2", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"错误: I2C 总线 /dev/i2c-{bus} 不存在", file=sys.stderr)
            print("提示: 确保已启用 I2C (sudo raspi-config -> Interface Options -> I2C)", file=sys.stderr)
            sys.exit(1)
        except PermissionError:
            print(f"错误: 无法访问 I2C 总线 /dev/i2c-{bus}，请将用户加入 i2c 组", file=sys.stderr)
            print("  sudo usermod -aG i2c $USER", file=sys.stderr)
            sys.exit(1)

        # 初始化配置
        self._init_device()

    def _write_word(self, reg, value):
        """向寄存器写入2字节 (大端)"""
        high = (value >> 8) & 0xFF
        low = value & 0xFF
        self.bus.write_i2c_block_data(self.address, reg, [high, low])

    def _read_word(self, reg):
        """从寄存器读取2字节 (大端)"""
        data = self.bus.read_i2c_block_data(self.address, reg, 2)
        return (data[0] << 8) | data[1]

    def _init_device(self):
        """初始化 ADS1115 配置"""
        self.config = (ADS1115_MUX_AIN0_GND |
                       PGA_VALUES[self.pga_idx] |
                       ADS1115_MODE_SINGLE |
                       DR_VALUES[self.dr_idx] |
                       ADS1115_COMP_QUE_DISABLE)
        self._write_word(ADS1115_REG_CONFIG, self.config)

    def read_single(self, channel):
        """
        读取单端通道 (单次转换)

        :param channel: 通道号 0~3 (对应 AIN0~AIN3)
        :return: 电压值 (V)
        """
        if channel < 0 or channel > 3:
            raise ValueError(f"通道号无效: {channel} (有效: 0~3)")

        # 设置通道并启动转换
        mux = ADS1115_MUX_AIN0_GND | (channel << 12)  # AINch-GND
        cfg = (self.config & ~0x7000) | mux | ADS1115_OS_START
        self._write_word(ADS1115_REG_CONFIG, cfg)
        self.config = cfg

        # 等待转换完成
        wait_ms = 1000 // (8 << self.dr_idx) + 3
        time.sleep(wait_ms / 1000.0)

        # 读取转换值
        raw = self._read_word(ADS1115_REG_CONVERSION)
        raw_signed = raw if raw < 32768 else raw - 65536

        # 转换为电压: V = raw * FS_VOLTAGE / 32768
        voltage = raw_signed * self.fs_voltage / 32768.0
        return voltage

    def read_diff(self, pos, neg):
        """
        读取差分通道 (单次转换)

        支持组合: (0,1), (0,3), (1,3), (2,3)
        :param pos: 正极通道 (0~3)
        :param neg: 负极通道 (0~3)
        :return: 电压值 (V)
        """
        mux_map = {
            (0, 1): ADS1115_MUX_AIN0_AIN1,
            (0, 3): ADS1115_MUX_AIN0_AIN3,
            (1, 3): ADS1115_MUX_AIN1_AIN3,
            (2, 3): ADS1115_MUX_AIN2_AIN3,
        }
        key = (pos, neg)
        if key not in mux_map:
            raise ValueError(f"不支持的差分组合: AIN{pos} - AIN{neg}，支持: 0-1, 0-3, 1-3, 2-3")

        mux = mux_map[key]
        cfg = (self.config & ~0x7000) | mux | ADS1115_OS_START
        self._write_word(ADS1115_REG_CONFIG, cfg)
        self.config = cfg

        # 等待转换完成
        wait_ms = 1000 // (8 << self.dr_idx) + 3
        time.sleep(wait_ms / 1000.0)

        raw = self._read_word(ADS1115_REG_CONVERSION)
        raw_signed = raw if raw < 32768 else raw - 65536

        voltage = raw_signed * self.fs_voltage / 32768.0
        return voltage

    def start_continuous(self, channel):
        """启动连续模式"""
        if channel < 0 or channel > 3:
            raise ValueError(f"通道号无效: {channel}")
        cfg = (self.config & ~0x7100 |
               (ADS1115_MUX_AIN0_GND | (channel << 12)) |
               ADS1115_MODE_CONTINUOUS |
               ADS1115_COMP_QUE_DISABLE)
        self._write_word(ADS1115_REG_CONFIG, cfg)
        self.config = cfg

    def read_continuous(self):
        """连续模式读数"""
        raw = self._read_word(ADS1115_REG_CONVERSION)
        raw_signed = raw if raw < 32768 else raw - 65536
        return raw_signed * self.fs_voltage / 32768.0

    def scan_all(self):
        """扫描所有单端通道"""
        results = {}
        ch_names = ["AIN0", "AIN1", "AIN2", "AIN3"]
        for ch in range(4):
            v = self.read_single(ch)
            results[ch_names[ch]] = v
        return results

    def print_config(self):
        """打印配置寄存器详情"""
        config = self._read_word(ADS1115_REG_CONFIG)
        mux = (config >> 12) & 0x07
        pga = (config >> 9) & 0x07
        mode = (config >> 8) & 0x01
        dr = (config >> 5) & 0x07
        comp = config & 0x03

        mux_names = {
            0: "AIN0-AIN1 (差分)",
            1: "AIN0-AIN3 (差分)",
            2: "AIN1-AIN3 (差分)",
            3: "AIN2-AIN3 (差分)",
            4: "AIN0-GND (单端)",
            5: "AIN1-GND (单端)",
            6: "AIN2-GND (单端)",
            7: "AIN3-GND (单端)",
        }

        print(f"\n===== ADS1115 寄存器 =====")
        print(f"  配置寄存器: 0x{config:04X}")
        print(f"  MUX: {mux} -> {mux_names.get(mux, '未知')}")
        if pga <= 5:
            print(f"  PGA: {pga} -> {PGA_NAMES[pga]} (满量程 {PGA_FS[pga]:.3f}V)")
        else:
            print(f"  PGA: {pga} -> 未知")
        print(f"  模式: {'单次' if mode else '连续'}")
        if dr <= 7:
            print(f"  速率: {dr} -> {DR_NAMES[dr]}")
        else:
            print(f"  速率: {dr} -> 未知")
        print(f"  比较器: {'禁用' if comp == 3 else '启用'}")

        # 读取阈值
        lo_raw = self._read_word(ADS1115_REG_LO_THRESH)
        hi_raw = self._read_word(ADS1115_REG_HI_THRESH)
        lo_signed = lo_raw if lo_raw < 32768 else lo_raw - 65536
        hi_signed = hi_raw if hi_raw < 32768 else hi_raw - 65536
        lo_v = lo_signed * self.fs_voltage / 32768.0
        hi_v = hi_signed * self.fs_voltage / 32768.0
        print(f"  阈值: LO={lo_signed} ({lo_v:.6f}V), HI={hi_signed} ({hi_v:.6f}V)")

    def close(self):
        """关闭 I2C 总线"""
        self.bus.close()


def main():
    parser = argparse.ArgumentParser(
        description="Linux I2C 读取 TI ADS1115 16位 ADC 的命令行工具",
        epilog="""
参数说明:
  -b, --i2c-bus    I2C 总线号 (默认 1, 对应 /dev/i2c-1)
  -a, --address    I2C 设备地址 (默认 0x48)
  -p, --pga        PGA 增益索引 0~5 (默认 2=±2.048V)
                   0=±6.144V, 1=±4.096V, 2=±2.048V
                   3=±1.024V, 4=±0.512V, 5=±0.256V
  -r, --rate       数据速率索引 0~7 (默认 4=128SPS)
                   0=8, 1=16, 2=32, 3=64
                   4=128, 5=250, 6=475, 7=860 (SPS)
  -c, --channel    单端通道号 0~3 (读取 AIN0~AIN3)
  --diff           差分模式，格式 "pos,neg" 如 "0,1"
  --scan           扫描所有单端通道
  --continuous     连续读取模式
  -n, --count      读取次数 (默认 1)
  --delay          每次读取间隔毫秒 (默认 10ms)
  --config         显示配置寄存器详情

  --percent        输出基于 0-5V 范围的百分比 (0.00%~100.00%)
  --map            将 0-5V 百分比映射到自定义数值区间，格式 "min,max"
                   例: --map -20,80 表示 0V=-20, 5V=80
                   使用 --map 时自动启用百分比显示

使用示例:
  ads1115                                    # 读取 AIN0 (默认参数)
  ads1115 -c 2                               # 读取 AIN2
  ads1115 --scan                             # 扫描所有单端通道
  ads1115 -c 0 -n 5                          # 连续读 AIN0 5次
  ads1115 --diff 0,1                         # 差分模式 AIN0-AIN1
  ads1115 -a 0x49 -p 1 -r 6                 # 指定地址、PGA、速率
  ads1115 -c 0 --continuous -n 10           # 连续模式读10次
  ads1115 --config                           # 查看配置寄存器
  ads1115 --scan --config                    # 扫描并查看配置
  ads1115 -c 0 --percent                     # 读取 AIN0 并显示 0-5V 百分比
  ads1115 --scan --percent                   # 扫描所有通道并显示百分比
  ads1115 -c 0 --map -20,80                 # 将 0-5V 映射到 -20~80 区间
  ads1115 --scan --map 0,100                # 扫描并映射到 0~100 区间
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-b", "--i2c-bus", type=int, default=1, help="I2C 总线号 (默认 1)")
    parser.add_argument("-a", "--address", type=lambda x: int(x, 0), default=0x48, help="I2C 设备地址 (默认 0x48)")
    parser.add_argument("-p", "--pga", type=int, default=2, choices=range(0, 6), metavar="{0..5}", help="PGA 增益索引 0~5 (默认 2)")
    parser.add_argument("-r", "--rate", type=int, default=4, choices=range(0, 8), metavar="{0..7}", help="数据速率索引 0~7 (默认 4)")
    parser.add_argument("-c", "--channel", type=int, default=None, choices=range(0, 4), metavar="{0..3}", help="单端通道号 0~3")
    parser.add_argument("--diff", type=str, default=None, help='差分模式，格式 "pos,neg" 如 "0,1"')
    parser.add_argument("--scan", action="store_true", help="扫描所有单端通道")
    parser.add_argument("--continuous", action="store_true", help="连续读取模式")
    parser.add_argument("-n", "--count", type=int, default=1, help="读取次数 (默认 1)")
    parser.add_argument("--delay", type=int, default=10, help="每次读取间隔毫秒 (默认 10ms)")
    parser.add_argument("--config", action="store_true", help="显示配置寄存器详情")
    parser.add_argument("--percent", action="store_true", help="输出基于 0-5V 范围的百分比")
    parser.add_argument("--map", type=str, default=None, metavar="MIN,MAX",
                        help='将 0-5V 百分比映射到数值区间，格式 "min,max" 如 "-20,80"')

    args = parser.parse_args()

    # --- 解析 --map 参数 ---
    map_range = None
    if args.map is not None:
        try:
            parts = args.map.split(",")
            if len(parts) != 2:
                raise ValueError
            map_min, map_max = float(parts[0]), float(parts[1])
            if map_min == map_max:
                raise ValueError("映射区间两端不能相同")
            map_range = (map_min, map_max)
            args.percent = True  # --map 自动启用百分比显示
        except ValueError as e:
            err_msg = str(e) if str(e) != "" else "格式无效"
            print(f"错误: --map 参数无效 '{args.map}'，请使用 'min,max' 格式，如 '-20,80' ({err_msg})", file=sys.stderr)
            sys.exit(1)

    try:
        adc = ADS1115(bus=args.i2c_bus, address=args.address,
                      pga_idx=args.pga, dr_idx=args.rate)

        def pct(v):
            """返回 0-5V 百分比/映射后缀字符串"""
            if not args.percent:
                return ""
            p = v / 5.0 * 100.0
            suffix = f"  [{p:6.2f}%]"
            if map_range is not None:
                mapped = map_range[0] + (p / 100.0) * (map_range[1] - map_range[0])
                suffix += f"  (映射: {mapped:.2f})"
            return suffix

        has_action = False

        # --- 单端通道读取 ---
        if args.channel is not None and args.diff is None:
            has_action = True
            ch_names = ["AIN0", "AIN1", "AIN2", "AIN3"]
            ch_name = ch_names[args.channel]

            if args.continuous:
                print(f"连续模式读取 {ch_name} ({args.count} 次):")
                adc.start_continuous(args.channel)
                time.sleep(0.05)
                for i in range(args.count):
                    v = adc.read_continuous()
                    print(f"  [{i}] {ch_name}: {v:+.6f} V  ({v*1000:.3f} mV){pct(v)}")
                    if i < args.count - 1:
                        time.sleep(args.delay / 1000.0)
            else:
                print(f"读取 {ch_name} ({args.count} 次):")
                for i in range(args.count):
                    v = adc.read_single(args.channel)
                    print(f"  [{i}] {ch_name}: {v:+.6f} V  ({v*1000:.3f} mV){pct(v)}")
                    if i < args.count - 1:
                        time.sleep(args.delay / 1000.0)

        # --- 差分模式 ---
        if args.diff is not None:
            has_action = True
            try:
                parts = args.diff.split(",")
                if len(parts) != 2:
                    raise ValueError
                pos, neg = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                print(f"错误: 差分格式无效 '{args.diff}'，请使用 'pos,neg' 格式，如 '0,1'", file=sys.stderr)
                sys.exit(1)

            print(f"差分读取 AIN{pos} - AIN{neg} ({args.count} 次):")
            for i in range(args.count):
                v = adc.read_diff(pos, neg)
                print(f"  [{i}] AIN{pos}-AIN{neg}: {v:+.6f} V  ({v*1000:.3f} mV){pct(v)}")
                if i < args.count - 1:
                    time.sleep(args.delay / 1000.0)

        # --- 扫描所有单端通道 ---
        if args.scan:
            has_action = True
            print("\n===== 单端通道扫描 =====")
            results = adc.scan_all()
            for ch, v in results.items():
                print(f"  {ch}: {v:+.6f} V  ({v*1000:.3f} mV){pct(v)}")

        # --- 显示配置 ---
        if args.config:
            has_action = True
            adc.print_config()

        # --- 默认行为: 读 AIN0 ---
        if not has_action:
            v = adc.read_single(0)
            print(f"AIN0: {v:+.6f} V  ({v*1000:.3f} mV){pct(v)}")

    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'adc' in locals():
            adc.close()


if __name__ == "__main__":
    main()
