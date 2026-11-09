"""硬件实验 ↔ 软件模拟映射图。

把论文两个硬件实验（干涉测速 testbed Fig.6、实机攻击演示 Fig.2/3/4）的
器件级信号链画在上方，对应的软件模拟模块画在下方，虚线箭头标注映射关系
与等效层级，并明确标出未模拟的部分。生成 figures/fig_hw_mapping.png。
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.family"] = ["Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

C_HW = "#dbeafe"      # 硬件盒
C_HW_EDGE = "#3b82f6"
C_SW = "#dcfce7"      # 软件盒
C_SW_EDGE = "#16a34a"
C_MAP = "#9ca3af"     # 映射箭头
C_MISS = "#fee2e2"    # 未模拟盒
C_MISS_EDGE = "#dc2626"


def _box(ax, x, y, w, h, text, fc, ec, fs=8.5):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0.6",
                                fc=fc, ec=ec, lw=1.4))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs)


def _arrow(ax, x1, y1, x2, y2, color="#475569", style="-", lw=1.6, ms=14):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=ms, color=color, lw=lw,
                                 linestyle=style, shrinkA=2, shrinkB=2))


def _panel_interferometer(ax):
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    ax.text(50, 97, "A. 干涉测速 testbed（论文 Fig.6/7）", ha="center",
            fontsize=13, weight="bold")
    # ---- 硬件行
    ax.text(3, 91, "论文硬件", fontsize=10, color=C_HW_EDGE, weight="bold",
            ha="left")
    _box(ax, 12, 80, 14, 13, "激光管\nPL202\n635 nm", C_HW, C_HW_EDGE)
    _box(ax, 28, 80, 13, 12, "分束器\nCCM1-BS013", C_HW, C_HW_EDGE)
    _box(ax, 48, 90, 15, 11, "固定镜 M0\n（本振束 $Y_{LO}$）", C_HW, C_HW_EDGE)
    _box(ax, 48, 70, 15, 11, "动镜 M1\n电机滑轨 v(t)", C_HW, C_HW_EDGE)
    _box(ax, 67, 80, 13, 12, "光电接收器\nOPT101", C_HW, C_HW_EDGE)
    _box(ax, 86, 80, 14, 12, "示波器\n+FFT → Δf", C_HW, C_HW_EDGE)
    _arrow(ax, 19, 80, 21.5, 80)
    _arrow(ax, 34.5, 80, 40.5, 88, color=C_HW_EDGE)
    _arrow(ax, 34.5, 80, 40.5, 72, color=C_HW_EDGE)
    _arrow(ax, 55.5, 88, 60.5, 82.5, color=C_HW_EDGE)
    _arrow(ax, 55.5, 72, 60.5, 77.5, color=C_HW_EDGE)
    _arrow(ax, 73.5, 80, 79, 80)

    # ---- 软件行
    ax.text(3, 40, "软件模拟", fontsize=10, color=C_SW_EDGE, weight="bold",
            ha="left")
    _box(ax, 14, 28, 15, 12, "$F_0=c/\\lambda$\n635 nm 载频", C_SW, C_SW_EDGE)
    _box(ax, 39, 28, 22, 15, "photodiode_output()\nPout 拍频公式\n"
        "（噪声 + 速度抖动）", C_SW, C_SW_EDGE)
    _box(ax, 65, 28, 22, 15, "extract_doppler_fft()\nFFT + 最高能量峰\n"
        "+ 抛物线插值", C_SW, C_SW_EDGE)
    _box(ax, 88, 28, 13, 12, "v̂ = Δf·λ/2\n→ 速度估计", C_SW, C_SW_EDGE, fs=7.5)
    _arrow(ax, 21.5, 28, 28, 28, color=C_SW_EDGE)
    _arrow(ax, 50, 28, 54, 28, color=C_SW_EDGE)
    _arrow(ax, 76, 28, 81.5, 28, color=C_SW_EDGE)

    # ---- 映射箭头（标注置于线旁，不压线）
    _arrow(ax, 48, 62, 42, 37, color=C_MAP, style="--")
    ax.text(24, 51, "公式级等效\n（全场混频验证\n残差 2.9e-3）", fontsize=7.5,
            ha="center", color="#6b7280")
    _arrow(ax, 86, 71.5, 68, 37, color=C_MAP, style="--")
    ax.text(86, 54, "算法级\n（相同处理）", fontsize=7.5, ha="right",
            color="#6b7280")

    # ---- 未模拟
    _box(ax, 50, 9, 88, 11,
         "未模拟（以论文 §IV-B1 公式替代）：真实光子传播 · 探测器电路响应 · "
         "实验室环境振动", C_MISS, C_MISS_EDGE, fs=8.5)


def _panel_lidar(ax):
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    ax.text(50, 97, "B. 实机攻击演示 → 攻击+检测闭环仿真（论文 Fig.2/3/4）",
            ha="center", fontsize=13, weight="bold")
    # ---- 硬件行
    ax.text(3, 91, "论文硬件", fontsize=10, color=C_HW_EDGE, weight="bold",
            ha="left")
    _box(ax, 14, 80, 18, 13, "受害 LiDAR\nYD X2L（自车）\n真实点云输出",
         C_HW, C_HW_EDGE)
    _box(ax, 41, 80, 22, 15, "攻击器（<60 美元，1.5 m 外）\n光电二极管(同步)"
         " + 延时 $\\tau_{spoof}$\n+ 激光管", C_HW, C_HW_EDGE)
    _box(ax, 65, 80, 17, 13, "假点注入\n点云出现假点簇\n（Fig.4b）", C_HW,
         C_HW_EDGE)
    _box(ax, 87, 80, 13, 13, "检测：论文\n未在实机演示", "#f1f5f9",
         "#94a3b8")
    _arrow(ax, 23, 80, 30, 80)
    _arrow(ax, 52, 80, 56.5, 80)
    _arrow(ax, 73.5, 80, 80.5, 80)

    # ---- 软件行
    ax.text(3, 38, "软件模拟", fontsize=10, color=C_SW_EDGE, weight="bold",
            ha="left")
    _box(ax, 10, 24, 14, 15, "build_scene()\n+ scan()\n360°光线投射", C_SW,
         C_SW_EDGE, fs=7.5)
    _box(ax, 27, 24, 16, 15, "式(2)注入\n$t_a=t_s+\\tau_{spoof}$\n"
        "先到先得替换", C_SW, C_SW_EDGE, fs=7.5)
    _box(ax, 45, 24, 18, 15, "式(5)(6)\nDoppler 合成\n合法 2v/c · 欺骗 v/c\n"
        "（噪声: 式(28)）", C_SW, C_SW_EDGE, fs=7)
    _box(ax, 63, 24, 14, 15, "锚点跟踪\n$(v_{Dop},v_{ToF})$\n逐目标配对",
         C_SW, C_SW_EDGE, fs=7)
    _box(ax, 81, 24, 15, 15, "T² 检测器\n(式 18/19)\n判决+滤除", C_SW,
         C_SW_EDGE, fs=7.5)
    _arrow(ax, 17, 24, 19, 24, color=C_SW_EDGE)
    _arrow(ax, 35, 24, 36, 24, color=C_SW_EDGE)
    _arrow(ax, 54, 24, 56, 24, color=C_SW_EDGE)
    _arrow(ax, 70, 24, 73.5, 24, color=C_SW_EDGE)

    # ---- 映射箭头（标注置于线旁，不压线）
    _arrow(ax, 14, 71, 10, 33, color=C_MAP, style="--")
    ax.text(21, 52, "模型级：\n测距噪声 3 cm\n1° 角分辨率", fontsize=7.5,
            ha="left", color="#6b7280")
    _arrow(ax, 41, 70, 28, 33, color=C_MAP, style="--")
    ax.text(36, 58, "公式级：\n延时 → 假距离", fontsize=7.5, ha="right",
            color="#6b7280")
    _arrow(ax, 65, 71, 47, 33, color=C_MAP, style="--")
    ax.text(71, 52, "信号的物理\n（单程 vs 往返）", fontsize=7.5, ha="left",
            color="#6b7280")
    _arrow(ax, 87, 71, 82, 33, color=C_MAP, style="--")
    ax.text(96, 52, "闭环检测\n（软件新增）", fontsize=7.5, ha="right",
            color="#6b7280")

    # ---- 未模拟
    _box(ax, 50, 8, 88, 10,
         "未模拟：商用 LiDAR 固件行为（首达判定近似为\u201c先到先得\u201d）· "
         "真实光噪声/杂散反射 · 大气衰减", C_MISS, C_MISS_EDGE, fs=8.5)


def _device_box(ax, x, y, w, h, title, impl, fc=C_HW, ec=C_HW_EDGE, fs=7.2,
                title_fs=8.5):
    """虚拟器件框：标题 + 框内实现说明（实现=代码/公式）。"""
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0.6", fc=fc, ec=ec, lw=1.6))
    ax.text(x, y + h / 2 - 3.2, title, ha="center", va="center",
            fontsize=title_fs, weight="bold")
    ax.text(x, y - 1.6, impl, ha="center", va="center", fontsize=fs,
            color="#166534", linespacing=1.5)


def _panel_virtual_interferometer(ax):
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    ax.text(50, 96, "A. 虚拟干涉测速 testbed（src/interferometer.py）",
            ha="center", fontsize=13, weight="bold")
    _device_box(ax, 10, 68, 16, 20, "虚拟激光管",
                "$F_0=c/\\lambda$\n635 nm\n$4.72\\times10^{14}$ Hz")
    _device_box(ax, 29, 68, 14, 20, "虚拟分束器",
                "两路复指数光场\n$Y_{LO},Y_M$\n（§IV-B1）")
    _device_box(ax, 50, 88, 19, 12, "虚拟固定镜 M0",
                "本振相位 $\\phi_{LO}$（随机常数）")
    _device_box(ax, 50, 48, 19, 15, "虚拟动镜 M1",
                "相位积分 $2\\pi\\frac{2}{\\lambda}\\int v\\,dt$\n"
                "电机滑轨 = 速度曲线 v(t)\n（含抖动，可时变）")
    _device_box(ax, 73, 68, 20, 24, "虚拟光电接收器",
                "$P_{out}=\\frac{A_M^2+A_{LO}^2}{2}$\n"
                "$+A_MA_{LO}\\cos\\Delta\\phi$\n"
                "+ 高斯噪声（SNR 可配）")
    _device_box(ax, 93, 68, 14, 24, "虚拟示波器\n+FFT",
                "rFFT · 去直流\n[2k,200k]Hz 取最高峰\n抛物线亚 bin 插值")
    _device_box(ax, 93, 38, 14, 11, "输出",
                "$\\Delta f\\!\\to\\!\\hat v=\\Delta f\\lambda/2$\n"
                "误差 p95 3.7%", fc=C_SW, ec=C_SW_EDGE)
    # 光束 / 电信号连线
    _arrow(ax, 18, 68, 22, 68); ax.text(20, 72, "光束", fontsize=7, ha="center")
    _arrow(ax, 36, 71, 41, 84, color=C_HW_EDGE)
    _arrow(ax, 36, 65, 41, 54, color=C_HW_EDGE)
    _arrow(ax, 59.5, 85, 64, 74, color=C_HW_EDGE)
    _arrow(ax, 59.5, 52, 64, 62, color=C_HW_EDGE)
    ax.text(61.5, 70, "合束", fontsize=7, ha="center")
    _arrow(ax, 83, 68, 86, 68); ax.text(84.5, 72, "电信号", fontsize=7,
                                        ha="center")
    _arrow(ax, 93, 56, 93, 44, color=C_SW_EDGE)
    # 拍频示意波形（接收器内部）
    tt = np.linspace(0, 1, 60)
    ax.plot(66 + 14 * tt, 62 + 1.8 * np.cos(2 * np.pi * 8 * tt),
            color="#7c3aed", lw=1.2)
    ax.text(73, 59.2, "拍频信号 @ Δf", fontsize=6.5, ha="center",
            color="#7c3aed")
    ax.text(50, 22, "全场混频+低通数值验证：Pout 公式残差 2.9e-3（仅低通滤波器通带下垂）",
            ha="center", fontsize=8.5, color="#475569")
    ax.text(50, 12, "对应论文器件：PL202 激光管 · CCM1-BS013 分束器 · M0/M1 反射镜 · "
            "OPT101 光电接收器 · 示波器", ha="center", fontsize=8,
            color="#6b7280")


def _panel_virtual_lidar(fig, gs, ax_scene, ax_impl):
    import numpy as np
    from . import simulator as sim

    # ---------------- 左：场景（用 scan() 第 0 帧真实数据渲染）
    ax_scene.set_aspect("equal")
    ax_scene.set_xlim(-16, 16.5); ax_scene.set_ylim(-7, 44)
    rng = np.random.default_rng(0)
    ego_speed, segs, attacks, anchors = sim.build_scene()
    ego = np.zeros(2)
    frame = sim.scan(rng, ego, ego_speed, segs, attacks)
    # 线段目标
    for seg in segs:
        ax_scene.plot([seg.p[0], seg.q[0]], [seg.p[1], seg.q[1]],
                      color="#64748b", lw=3, solid_capstyle="round")
    # 回波与光束
    for deg, (d, label, spf, _) in frame.items():
        th = np.deg2rad(deg)
        x, y = d * np.cos(th), d * np.sin(th)
        ax_scene.plot([0, x], [0, y], color="#94a3b8", lw=0.3, alpha=0.35)
        if spf:
            ax_scene.plot(x, y, "rx", ms=5, mew=1.4)
        elif label == "bike":
            ax_scene.plot(x, y, "b^", ms=4)
    # 自车 + LiDAR
    ax_scene.plot(0, 0, "s", color="#16a34a", ms=11)
    ax_scene.plot(0, 0, "o", color="#052e16", ms=4)
    ax_scene.annotate("自车 + 虚拟 2-D LiDAR\n(11 m/s, 1°×360°)",
                      xy=(0.4, 0.6), xytext=(-15.5, -4.5), fontsize=7.5,
                      arrowprops=dict(arrowstyle="->", color="#052e16", lw=1))
    # 攻击器
    atk_pos = attacks["static"]["pos"]
    ax_scene.plot(*attacks["ahead"]["attacker"], "s", color="#dc2626", ms=10)
    ax_scene.annotate("虚拟攻击器\n（光电二极管+延时+激光管）",
                      xy=tuple(attacks["ahead"]["attacker"]),
                      xytext=(7.5, 33), fontsize=7.5, color="#dc2626",
                      arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1))
    ax_scene.plot([attacks["ahead"]["attacker"][0], 0],
                  [attacks["ahead"]["attacker"][1], 0], ls="--", lw=1,
                  color="#dc2626", alpha=0.6)
    # 假目标标注
    for pos, name, xytext in [
            (atk_pos, "假静态墙（场景1）", (-15.5, 34)),
            (np.array([0, 12]), "前方假车（场景3）", (-15.5, 19)),
            (np.array([9, 0]), "侧方假目标（局限1）", (10.5, -4.5))]:
        ax_scene.annotate(name, xy=tuple(pos), xytext=xytext, fontsize=7.5,
                          color="#b91c1c",
                          arrowprops=dict(arrowstyle="->", color="#b91c1c",
                                          lw=0.9))
    ax_scene.annotate("自行车（动态合法）", xy=(2.5, 25), xytext=(6.5, 26.5),
                      fontsize=7.5, color="#1d4ed8",
                      arrowprops=dict(arrowstyle="->", color="#1d4ed8", lw=0.9))
    ax_scene.annotate("立柱", xy=(0, 20), xytext=(-4.5, 22.5), fontsize=7.5,
                      color="#475569",
                      arrowprops=dict(arrowstyle="->", color="#475569", lw=0.9))
    ax_scene.set_title("虚拟攻击场景（src/simulator.py 第 0 帧真实渲染）",
                       fontsize=10)
    ax_scene.set_xlabel("x (m)"); ax_scene.set_ylabel("y (m)")

    # ---------------- 右：器件实现说明
    ax_impl.set_xlim(0, 100); ax_impl.set_ylim(0, 100); ax_impl.axis("off")
    ax_impl.text(50, 97, "虚拟器件与实现方式", ha="center", fontsize=11,
                 weight="bold")
    _device_box(ax_impl, 50, 84, 88, 17, "虚拟 2-D LiDAR（替代 YD X2L）",
                "scan()：360 条光线 × 场景线段求交，最近交点=回波\n"
                "测距噪声 σ=3 cm · 每 0.1 s 一帧 · 替代真实 ToF 收发")
    _device_box(ax_impl, 50, 62, 88, 19, "虚拟攻击器（<60 美元三件套）",
                "光电二极管(同步)：攻击方向窗口 ±3°~4°\n"
                "延时器：式(2) $t_a=t_s+\\tau_{spoof}$ → 假距离 $d^{(spf)}$\n"
                "激光管：假距离 < 真回波距离 → 先到先得替换")
    _device_box(ax_impl, 50, 40, 88, 17, "虚拟 Doppler 信道（式 5/6）",
                "合法回波：$\\hat v_{Dop}=v_r$（往返 2×） · 欺骗回波：$\\hat v_{Dop}"
                "=\\frac{1}{2}v_r$（单程）\n噪声 σ：式(28)，K=47.75（论文锚点校准），SNR 可配")
    _device_box(ax_impl, 50, 18, 88, 17, "虚拟跟踪 + 检测（式 8/9、18/19）",
                "锚点方向逐帧取束 · 实际 Δt 差分得 $v_{ToF}$（遮挡不断档）\n"
                "$(v_{Dop},v_{ToF})\\times$前 20 帧 → Hotelling T² → 判决+滤除",
                fc=C_SW, ec=C_SW_EDGE)
    _arrow(ax_impl, 50, 75.5, 50, 71.5, color="#475569", ms=11)
    _arrow(ax_impl, 50, 52.5, 50, 48.5, color="#475569", ms=11)
    _arrow(ax_impl, 50, 31.5, 50, 27.5, color="#475569", ms=11)
    _arrow(ax_impl, 50, 9.5, 50, 5.5, color="#475569", ms=11)
    ax_impl.text(50, 2.5, "判决结果：5 合法目标全部通过 · 场景 1/3 假目标检出 · "
                "侧方同速假目标漏检（=论文自述局限）",
                ha="center", fontsize=7.5, color="#6b7280")


def plot_virtual_testbed(out_path):
    fig = plt.figure(figsize=(15, 13.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.25],
                          width_ratios=[1.05, 1.0])
    ax_a = fig.add_subplot(gs[0, :])
    _panel_virtual_interferometer(ax_a)
    ax_scene = fig.add_subplot(gs[1, 0])
    ax_impl = fig.add_subplot(gs[1, 1])
    _panel_virtual_lidar(fig, gs, ax_scene, ax_impl)
    fig.suptitle("仿真硬件原理图：虚拟器件及其实现方式", fontsize=15,
                 weight="bold", y=0.998)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_hw_mapping(out_path):
    fig, axes = plt.subplots(2, 1, figsize=(14, 12.5))
    _panel_interferometer(axes[0])
    _panel_lidar(axes[1])
    fig.suptitle("论文硬件实验 ↔ 软件模拟映射（等效层级标注）", fontsize=15,
                 weight="bold", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    import sys
    root = "figures"
    plot_hw_mapping(f"{root}/fig_hw_mapping.png")
    print(f"saved: {root}/fig_hw_mapping.png")
    plot_virtual_testbed(f"{root}/fig_virtual_testbed.png")
    print(f"saved: {root}/fig_virtual_testbed.png")
