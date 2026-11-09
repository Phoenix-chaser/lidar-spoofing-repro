"""硬件实验 ↔ 软件模拟映射图。

把论文两个硬件实验（干涉测速 testbed Fig.6、实机攻击演示 Fig.2/3/4）的
器件级信号链画在上方，对应的软件模拟模块画在下方，虚线箭头标注映射关系
与等效层级，并明确标出未模拟的部分。生成 figures/fig_hw_mapping.png。
"""
import os

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
    out = sys.argv[1] if len(sys.argv) > 1 else "figures/fig_hw_mapping.png"
    plot_hw_mapping(out)
    print(f"saved: {out}")
