"""多普勒频移模型 —— 论文第 IV 节（式 3-6、15）的软件复现。

论文核心洞察：
  合法回波经历"往返"双程，其多普勒频移约为单程欺骗信号的 2 倍：
      合法信号（往返）:  Δf   = ((c+v)/(c-v) - 1) · f0        ≈ (2v/c) · f0   (式 5)
      欺骗信号（单程）:  Δfa  = (c/(c-va) - 1) · f0            ≈ (va/c) · f0   (式 6)
  该 2 倍差异是所有检测机制（第 V、VI 节）的物理基础。
"""
import numpy as np

C_LIGHT = 3e8            # 光速 (m/s)，论文取 3×10^8
F0_TYPICAL = C_LIGHT / 905e-9   # 典型 905nm LiDAR 载频（论文未给 f0，仅用于数值演示）


def doppler_shift_legit(f0: float, v: float) -> float:
    """式(5)：合法回波（往返）的多普勒频移。v 为 LiDAR 与目标的相对径向速度。"""
    return ((C_LIGHT + v) / (C_LIGHT - v) - 1.0) * f0


def doppler_shift_legit_approx(f0: float, v: float) -> float:
    """式(5)的近似：Δf ≈ (2v/c)·f0（v << c）。"""
    return 2.0 * v / C_LIGHT * f0


def doppler_shift_spoof(f0: float, va: float) -> float:
    """式(6)：欺骗信号（单程）的多普勒频移。va 为 LiDAR 与攻击者的相对径向速度。"""
    return (C_LIGHT / (C_LIGHT - va) - 1.0) * f0


def doppler_shift_spoof_approx(f0: float, va: float) -> float:
    """式(6)的近似：Δfa ≈ (va/c)·f0。"""
    return va / C_LIGHT * f0


def spoof_tx_frequency(v_spoof: float, va: float, f0: float) -> float:
    """式(15)：攻击模型 3 中，攻击者为伪造合法多普勒特征所需的发射频率。

    v_spoof: 想伪造的假目标相对径向速度
    va:      LiDAR 与攻击者之间的真实相对径向速度
    """
    return (C_LIGHT + 2.0 * v_spoof) / (C_LIGHT + va) * f0


def sanity_report() -> str:
    """自检：验证"合法=2×欺骗"的核心性质与式(15)的自洽性。"""
    f0 = F0_TYPICAL
    v = 10.0  # m/s 相对径向速度（远小于 c）
    legit = doppler_shift_legit(f0, v)
    spoof = doppler_shift_spoof(f0, v)
    lines = [
        f"f0 = {f0:.3e} Hz (905nm)",
        f"v = {v} m/s 时：合法(往返)频移 = {legit:.1f} Hz，欺骗(单程)频移 = {spoof:.1f} Hz，"
        f"比值 = {legit / spoof:.4f}（应≈2）",
        f"精确式与近似式偏差：合法 {abs(legit - doppler_shift_legit_approx(f0, v)) / legit:.2e}，"
        f"欺骗 {abs(spoof - doppler_shift_spoof_approx(f0, v)) / spoof:.2e}",
    ]
    # 式(15)自洽：攻击者以 fa 发射，接收频率 fa(1+va/c) 应恰为 f0(1+2v*/c)，
    # 即 LiDAR 收到的频移与"伪造目标以 v* 相对运动"的合法往返频移完全一致
    v_spoof, va = 5.0, 8.0
    fa = spoof_tx_frequency(v_spoof, va, f0)
    rx_shift = fa * (1.0 + va / C_LIGHT) - f0       # 论文一阶模型：Δfa=(fa/c)·va
    rx_expect = doppler_shift_legit_approx(f0, v_spoof)
    lines.append(
        f"式(15)自洽：伪造 v*={v_spoof} m/s, 攻击者相对速度 va={va} m/s → "
        f"fa={fa:.6e} Hz，LiDAR 收到频移 {rx_shift:.1f} Hz vs 期望合法频移 {rx_expect:.1f} Hz，"
        f"相对误差 {abs(rx_shift - rx_expect) / abs(rx_expect):.2e}"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    print(sanity_report())
