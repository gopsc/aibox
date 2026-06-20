#!/usr/bin/env python3
"""
ADS1256: Linux SPI 读取 TI ADS1256 24位 ΔΣ ADC 的命令行工具
"""

import spidev
import os
import sys
import argparse
import time


# ============================================================
# ADS1256 寄存器地址
# ============================================================
ADS1256_REG_STATUS = 0x00
ADS1256_REG_MUX    = 0x01
ADS1256_REG_ADCON  = 0x02
ADS1256_REG_DRATE  = 0x03
ADS1256_REG_IO     = 0x04
ADS1256_REG_OFC0   = 0x05
ADS1256_REG_OFC1   = 0x06
ADS1256_REG_OFC2   = 0x07
ADS1256_REG_FSC0   = 0x08
ADS1256_REG_FSC1   = 0x09
ADS1256_REG_FSC2   = 0x0A

# ============================================================
# ADS1256 命令
# ============================================================
ADS1256_CMD_WAKEUP   = 0x00
ADS1256_CMD_RDATA    = 0x01
ADS1256_CMD_RDATAC   = 0x03
ADS1256_CMD_SDATAC   = 0x0F
ADS1256_CMD_RREG     = 0x10
ADS1256_CMD_WREG     = 0x50
ADS1256_CMD_SELFCAL  = 0xF0
ADS1256_CMD_SELFOCAL = 0xF1
ADS1256_CMD_SELFGCAL = 0xF2
ADS1256_CMD_SYSOCAL  = 0xF3
ADS1256_CMD_SYSGCAL  = 0xF4
ADS1256_CMD_SYNC     = 0xFC
ADS1256_CMD_STANDBY  = 0xFD
ADS1256_CMD_RESET    = 0xFE

# ============================================================
# 数据速率 (DRATE 寄存器值)
# ============================================================
DRATE_MAP = {
    30000: 0xF0, 15000: 0xE0, 7500: 0xD0, 3750: 0xC0,
    2000: 0xB0,  1000: 0xA0,  500: 0x90,  100: 0x80,
    60: 0x70,    50: 0x60,    30: 0x50,    25: 0x40,
    15: 0x30,    10: 0x20,    5: 0x10,
}

# ============================================================
# PGA 增益
# ============================================================
PGA_MAP = {1: 0x00, 2: 0x01, 4: 0x02, 8: 0x03, 16: 0x04, 32: 0x05, 64: 0x06}

VREF = 2.5  # 参考电压


# ============================================================
# SPI 接口类 (基于 spidev)
# ============================================================
class SpiDev:
    def __init__(self, device="/dev/spidev0.0", speed=1920000):
        self.device = device
        self.speed = speed
        self.spi = None
        self._bus = None
        self._cs = None

    def _parse_device(self):
        """从设备路径解析 bus 和 cs, 如 /dev/spidev0.0 -> (0, 0)"""
        base = os.path.basename(self.device)  # spidev0.0
        parts = base.replace("spidev", "").split(".")
        return int(parts[0]), int(parts[1])

    def open(self):
        self._bus, self._cs = self._parse_device()
        self.spi = spidev.SpiDev()
        self.spi.open(self._bus, self._cs)
        self.spi.mode = 1          # SPI 模式 1: CPOL=0, CPHA=1
        self.spi.bits_per_word = 8
        self.spi.max_speed_hz = self.speed

        # 读取验证
        print(f"SPI 初始化: {self.device}, 模式={self.spi.mode}, "
              f"位数={self.spi.bits_per_word}, 速度={self.spi.max_speed_hz} Hz",
              file=sys.stderr)

    def transfer(self, tx_data, rx_len=None):
        """SPI 全双工传输"""
        if rx_len is None:
            rx_len = len(tx_data)

        # spidev.xfer2 返回接收到的字节
        rx = self.spi.xfer2(list(tx_data), self.speed, 1)  # 1 = SPI_MODE_1
        # 如果 rx_len 大于发送长度，补充虚拟字节
        if rx_len > len(tx_data):
            extra = self.spi.xfer2([0xFF] * (rx_len - len(tx_data)), self.speed, 1)
            rx.extend(extra)
        return list(rx[:rx_len])

    def write_byte(self, byte):
        self.spi.xfer2([byte], self.speed, 1)
        # 不需要接收

    def read_byte(self):
        rx = self.spi.xfer2([0xFF], self.speed, 1)
        return rx[0]

    def close(self):
        if self.spi:
            self.spi.close()
            self.spi = None


# ============================================================
# ADS1256 控制类
# ============================================================
class ADS1256:
    def __init__(self, spi, pga=2, drate=1000):
        self.spi = spi
        self.pga = pga
        self.drate = drate
        self.pga_reg = PGA_MAP.get(pga, 0x01)

    def wait_drdy(self):
        time.sleep(0.0001)  # 100us 模拟等待

    def reset(self):
        self.spi.write_byte(ADS1256_CMD_RESET)
        time.sleep(0.001)
        self.spi.write_byte(ADS1256_CMD_WAKEUP)
        time.sleep(0.001)

    def write_reg(self, reg, value):
        self.spi.write_byte(ADS1256_CMD_WREG | reg)
        self.spi.write_byte(0x00)  # 1 byte
        self.spi.write_byte(value)

    def read_reg(self, reg):
        self.spi.write_byte(ADS1256_CMD_RREG | reg)
        self.spi.write_byte(0x00)
        return self.spi.read_byte()

    def set_channel(self, pos, neg=0x08):
        """设置输入通道, neg=0x08 表示 AINCOM (单端模式)"""
        mux = ((pos & 0x07) << 4) | (neg & 0x07)
        self.write_reg(ADS1256_REG_MUX, mux)
        time.sleep(0.00001)

    def init(self):
        print("初始化 ADS1256...", file=sys.stderr)

        # 复位
        self.reset()
        time.sleep(0.01)

        # STATUS: ACAL=1 (自动校准), ORDER=0 (MSB), BUFEN=0
        self.write_reg(ADS1256_REG_STATUS, 0x14)

        # MUX: 默认 AIN0 + AINCOM
        self.set_channel(0, 0x08)

        # ADCON: PGA 增益
        self.write_reg(ADS1256_REG_ADCON, self.pga_reg)

        # DRATE: 数据速率
        drate_val = DRATE_MAP.get(self.drate, 0xA0)
        self.write_reg(ADS1256_REG_DRATE, drate_val)

        # 自校准
        print("自校准中...", file=sys.stderr)
        self.spi.write_byte(ADS1256_CMD_SELFCAL)
        time.sleep(0.5)  # 等待校准完成 (~400ms @ 1000SPS)

        # 验证寄存器
        status = self.read_reg(ADS1256_REG_STATUS)
        mux    = self.read_reg(ADS1256_REG_MUX)
        adcon  = self.read_reg(ADS1256_REG_ADCON)
        drate  = self.read_reg(ADS1256_REG_DRATE)
        print(f"寄存器: STATUS=0x{status:02X}, MUX=0x{mux:02X}, "
              f"ADCON=0x{adcon:02X}, DRATE=0x{drate:02X}", file=sys.stderr)
        print("ADS1256 初始化完成!", file=sys.stderr)

    def read_data(self):
        """单次读取 24 位数据, 返回有符号整数值"""
        self.wait_drdy()
        self.spi.write_byte(ADS1256_CMD_RDATA)
        buf = self.spi.transfer([0xFF, 0xFF, 0xFF], 3)

        # 组合 24 位
        value = (buf[0] << 16) | (buf[1] << 8) | buf[2]

        # 符号扩展 (24 位 -> 32 位)
        if value & 0x800000:
            value |= 0xFF000000

        # Python 中转为有符号
        if value >= 0x80000000:
            value -= 0x100000000

        return value

    def raw_to_voltage(self, raw):
        """将原始值转换为电压"""
        return raw * VREF / (1 << 23) / self.pga

    def read_channel(self, ch):
        """读取指定单端通道"""
        self.set_channel(ch, 0x08)  # AINch vs AINCOM
        time.sleep(0.00001)

        self.spi.write_byte(ADS1256_CMD_SYNC)
        time.sleep(0.00001)
        self.spi.write_byte(ADS1256_CMD_WAKEUP)

        # 等待转换完成 (1000SPS = 1ms)
        time.sleep(0.002)

        return self.read_data()

    def read_diff(self, pos, neg):
        """读取差分通道"""
        self.set_channel(pos, neg)
        time.sleep(0.00001)

        self.spi.write_byte(ADS1256_CMD_SYNC)
        time.sleep(0.00001)
        self.spi.write_byte(ADS1256_CMD_WAKEUP)

        time.sleep(0.002)

        return self.read_data()

    def scan_all(self):
        """扫描所有 8 个单端通道"""
        results = []
        for ch in range(8):
            raw = self.read_channel(ch)
            volts = self.raw_to_voltage(raw)
            results.append((ch, raw, volts))
        return results


# ============================================================
# 主程序
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="ADS1256: Linux SPI 读取 TI ADS1256 24位 ΔΣ ADC 的命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
参数说明:
  -d, --device    SPI 设备路径                (默认: /dev/spidev0.0)
  -s, --speed     SPI 时钟频率 (Hz)           (默认: 1920000)
  -m, --mode      工作模式: single/diff/scan   (默认: single)
  -c, --channel   单端通道号 0-7              (默认: 0)
  --pos           差分正端 0-7                (默认: 0)
  --neg           差分负端 0-7                (默认: 1)
  -p, --pga       PGA 增益 1/2/4/8/16/32/64   (默认: 2)
  -r, --drate     数据速率 SPS                (默认: 1000)
                  可选: 5,10,15,25,30,50,60,100,500,1000,
                  2000,3750,7500,15000,30000
  -n, --count     采样次数                    (默认: 1)
  --avg           输出均值 (多采样时)
  -o, --output    输出格式: raw/voltage/both  (默认: both)

使用示例:
  # 读取 AIN0 单端通道
  ads1256 -c 0

  # 读取 AIN0 差分 AIN1
  ads1256 -m diff --pos 0 --neg 1

  # 扫描所有 8 个通道
  ads1256 -m scan

  # 设置 PGA=1, 速率为 30SPS, 采样 10 次并输出均值
  ads1256 -c 0 -p 1 -r 30 -n 10 --avg

  # 指定 SPI 设备
  ads1256 -d /dev/spidev0.1 -s 1000000 -c 3
"""
    )

    parser.add_argument("-d", "--device", default="/dev/spidev0.0",
                        help="SPI 设备路径 (默认: /dev/spidev0.0)")
    parser.add_argument("-s", "--speed", type=int, default=1920000,
                        help="SPI 时钟频率 Hz (默认: 1920000)")
    parser.add_argument("-m", "--mode", choices=["single", "diff", "scan"],
                        default="single", help="工作模式 (默认: single)")
    parser.add_argument("-c", "--channel", type=int, default=0, choices=range(8),
                        help="单端通道号 0-7 (默认: 0)")
    parser.add_argument("--pos", type=int, default=0, choices=range(8),
                        help="差分正端 0-7 (默认: 0)")
    parser.add_argument("--neg", type=int, default=1, choices=range(8),
                        help="差分负端 0-7 (默认: 1)")
    parser.add_argument("-p", "--pga", type=int, default=2,
                        choices=[1, 2, 4, 8, 16, 32, 64],
                        help="PGA 增益 (默认: 2)")
    parser.add_argument("-r", "--drate", type=int, default=1000,
                        help="数据速率 SPS (默认: 1000)")
    parser.add_argument("-n", "--count", type=int, default=1,
                        help="采样次数 (默认: 1)")
    parser.add_argument("--avg", action="store_true",
                        help="输出均值")
    parser.add_argument("-o", "--output", choices=["raw", "voltage", "both"],
                        default="both", help="输出格式 (默认: both)")

    args = parser.parse_args()

    # 验证 drate
    if args.drate not in DRATE_MAP:
        print(f"错误: 不支持的数据速率 {args.drate} SPS", file=sys.stderr)
        print(f"支持: {sorted(DRATE_MAP.keys())}", file=sys.stderr)
        sys.exit(1)

    # 验证 SPI 设备
    if not os.path.exists(args.device):
        print(f"错误: SPI 设备 {args.device} 不存在", file=sys.stderr)
        sys.exit(1)

    # 初始化 SPI
    spi = SpiDev(device=args.device, speed=args.speed)
    try:
        spi.open()
    except Exception as e:
        print(f"错误: SPI 初始化失败 - {e}", file=sys.stderr)
        sys.exit(1)

    # 初始化 ADS1256
    adc = ADS1256(spi, pga=args.pga, drate=args.drate)
    try:
        adc.init()
    except Exception as e:
        print(f"ADS1256 初始化失败: {e}", file=sys.stderr)
        spi.close()
        sys.exit(1)

    # 执行读取
    try:
        if args.mode == "scan":
            # 扫描所有通道
            results = adc.scan_all()
            print("\n===== 多通道扫描 =====")
            for ch, raw, volts in results:
                _print_result(ch, raw, volts, args.output)

        elif args.mode == "diff":
            # 差分模式
            pos, neg = args.pos, args.neg
            channel_label = f"AIN{pos}-AIN{neg}"
            raw_values = []
            for i in range(args.count):
                raw = adc.read_diff(pos, neg)
                raw_values.append(raw)
                volts = adc.raw_to_voltage(raw)
                _print_sample(i, raw, volts, args.output, channel_label)

            if args.count > 1 and args.avg:
                avg_raw = sum(raw_values) // len(raw_values)
                avg_volts = adc.raw_to_voltage(avg_raw)
                print(f"\n--- 均值 ---")
                _print_result(channel_label, avg_raw, avg_volts, args.output)

        else:
            # 单端模式
            ch = args.channel
            channel_label = f"AIN{ch}"
            raw_values = []
            for i in range(args.count):
                raw = adc.read_channel(ch)
                raw_values.append(raw)
                volts = adc.raw_to_voltage(raw)
                _print_sample(i, raw, volts, args.output, channel_label)

            if args.count > 1 and args.avg:
                avg_raw = sum(raw_values) // len(raw_values)
                avg_volts = adc.raw_to_voltage(avg_raw)
                print(f"\n--- 均值 ---")
                _print_result(channel_label, avg_raw, avg_volts, args.output)

    except Exception as e:
        print(f"读取错误: {e}", file=sys.stderr)
    finally:
        spi.close()


def _print_sample(index, raw, volts, output_format, label=""):
    if output_format == "raw":
        print(f"[{index}] {label}: raw={raw}")
    elif output_format == "voltage":
        print(f"[{index}] {label}: {_fmt_voltage(volts)}")
    else:
        print(f"[{index}] {label}: raw={raw:7d}, {_fmt_voltage(volts)}")


def _print_result(label, raw, volts, output_format):
    if output_format == "raw":
        print(f"  {label}: raw={raw}")
    elif output_format == "voltage":
        print(f"  {label}: {_fmt_voltage(volts)}")
    else:
        print(f"  {label}: raw={raw:7d}, {_fmt_voltage(volts)}")


def _fmt_voltage(volts):
    if abs(volts) >= 1.0:
        return f"电压 = {volts:+.6f} V"
    else:
        return f"电压 = {volts*1000:+.4f} mV"


if __name__ == "__main__":
    main()
