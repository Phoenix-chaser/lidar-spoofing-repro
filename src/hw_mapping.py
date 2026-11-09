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


def _box(ax, x, y, w, h, text, fc, ec, fs=10):
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
            fontsize=15, weight="bold")
    # ---- 硬件行
    ax.text(3, 91, "论文硬件", fontsize=12, color=C_HW_EDGE, weight="bold",
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
    ax.text(3, 40, "软件模拟", fontsize=12, color=C_SW_EDGE, weight="bold",
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
    ax.text(24, 51, "公式级等效\n（全场混频验证\n残差 2.9e-3）", fontsize=11.5,
            ha="center", color="#6b7280")
    _arrow(ax, 86, 71.5, 68, 37, color=C_MAP, style="--")
    ax.text(86, 54, "算法级\n（相同处理）", fontsize=11.5, ha="right",
            color="#6b7280")

    # ---- 未模拟
    _box(ax, 50, 9, 88, 11,
         "未模拟（以论文 §IV-B1 公式替代）：真实光子传播 · 探测器电路响应 · "
         "实验室环境振动", C_MISS, C_MISS_EDGE, fs=12)


def _panel_lidar(ax):
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    ax.text(50, 97, "B. 实机攻击演示 → 攻击+检测闭环仿真（论文 Fig.2/3/4）",
            ha="center", fontsize=15, weight="bold")
    # ---- 硬件行
    ax.text(3, 91, "论文硬件", fontsize=12, color=C_HW_EDGE, weight="bold",
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
        "（噪声: 式(28)）", C_SW, C_SW_EDGE, fs=9)
    _box(ax, 63, 24, 14, 15, "锚点跟踪\n$(v_{Dop},v_{ToF})$\n逐目标配对",
         C_SW, C_SW_EDGE, fs=9)
    _box(ax, 81, 24, 15, 15, "T² 检测器\n(式 18/19)\n判决+滤除", C_SW,
         C_SW_EDGE, fs=7.5)
    _arrow(ax, 17, 24, 19, 24, color=C_SW_EDGE)
    _arrow(ax, 35, 24, 36, 24, color=C_SW_EDGE)
    _arrow(ax, 54, 24, 56, 24, color=C_SW_EDGE)
    _arrow(ax, 70, 24, 73.5, 24, color=C_SW_EDGE)

    # ---- 映射箭头（标注置于线旁，不压线）
    _arrow(ax, 14, 71, 10, 33, color=C_MAP, style="--")
    ax.text(21, 52, "模型级：\n测距噪声 3 cm\n1° 角分辨率", fontsize=9.5,
            ha="left", color="#6b7280")
    _arrow(ax, 41, 70, 28, 33, color=C_MAP, style="--")
    ax.text(31, 63, "公式级：\n延时 → 假距离", fontsize=11.5, ha="right",
            color="#6b7280")
    _arrow(ax, 65, 71, 47, 33, color=C_MAP, style="--")
    ax.text(73, 52, "信号的物理\n（单程 vs 往返）", fontsize=11.5, ha="left",
            color="#6b7280")
    _arrow(ax, 87, 71, 82, 33, color=C_MAP, style="--")
    ax.text(96, 52, "闭环检测\n（软件新增）", fontsize=11.5, ha="right",
            color="#6b7280")

    # ---- 未模拟
    _box(ax, 50, 8, 88, 10,
         "未模拟：商用 LiDAR 固件行为（首达判定近似为\u201c先到先得\u201d）· "
         "真实光噪声/杂散反射 · 大气衰减", C_MISS, C_MISS_EDGE, fs=12)


def _device_box(ax, x, y, w, h, title, impl, fc=C_HW, ec=C_HW_EDGE, fs=11.5,
                title_fs=13.5):
    """虚拟器件框：标题 + 框内实现说明（实现=代码/公式）。"""
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0.6", fc=fc, ec=ec, lw=1.8))
    ax.text(x, y + h / 2 - 3.8, title, ha="center", va="center",
            fontsize=title_fs, weight="bold")
    ax.text(x, y - 2.2, impl, ha="center", va="center", fontsize=fs,
            color="#166534", linespacing=1.7)


def _panel_virtual_interferometer(ax):
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    ax.text(50, 96, "A. 虚拟干涉测速 testbed（src/interferometer.py）",
            ha="center", fontsize=18, weight="bold")
    _device_box(ax, 10, 66, 17, 24, "虚拟激光管",
                "$F_0=c/\\lambda$\n635 nm\n$4.72\\times10^{14}$ Hz")
    _device_box(ax, 30, 66, 15, 24, "虚拟分束器",
                "两路复指数光场\n$Y_{LO},Y_M$\n（§IV-B1）")
    _device_box(ax, 51, 88, 20, 12, "虚拟固定镜 M0",
                "本振相位 $\\phi_{LO}$（随机常数）")
    _device_box(ax, 51, 43, 21, 20, "虚拟动镜 M1",
                "相位积分 $2\\pi\\frac{2}{\\lambda}\\int v\\,dt$\n"
                "电机滑轨 = 速度曲线 v(t)\n（含抖动，可时变）")
    _device_box(ax, 74, 66, 21, 26, "虚拟光电接收器",
                "$P_{out}=\\frac{A_M^2+A_{LO}^2}{2}$\n"
                "$+A_MA_{LO}\\cos\\Delta\\phi$\n"
                "+ 高斯噪声（SNR 可配）")
    _device_box(ax, 92.5, 66, 13, 26, "虚拟示波器\n+FFT",
                "rFFT · 去直流\n[2k,200k]Hz\n取最高峰\n抛物线插值")
    _device_box(ax, 92.5, 36, 14, 12, "输出",
                "$\\Delta f\\!\\to\\!\\hat v=\\Delta f\\lambda/2$\n"
                "误差 p95 3.7%", fc=C_SW, ec=C_SW_EDGE)
    # 光束 / 电信号连线
    _arrow(ax, 18.5, 66, 22.5, 66, lw=2)
    ax.text(20.5, 71.5, "光束", fontsize=11.5, ha="center")
    _arrow(ax, 37.5, 69, 42, 84, color=C_HW_EDGE, lw=2)
    _arrow(ax, 37.5, 63, 42, 54, color=C_HW_EDGE, lw=2)
    _arrow(ax, 61, 84, 66, 73, color=C_HW_EDGE, lw=2)
    _arrow(ax, 61, 48, 66, 60, color=C_HW_EDGE, lw=2)
    ax.text(63.5, 68, "合束", fontsize=11.5, ha="center")
    _arrow(ax, 84.5, 66, 86, 66, lw=2)
    ax.text(85.3, 71, "电信号", fontsize=11.5, ha="center")
    _arrow(ax, 92.5, 53, 92.5, 42.5, color=C_SW_EDGE, lw=2)
    # 拍频示意波形（接收器内部）
    tt = np.linspace(0, 1, 80)
    ax.plot(64 + 18 * tt, 46.5 + 2.4 * np.cos(2 * np.pi * 9 * tt),
            color="#7c3aed", lw=1.8)
    ax.text(73, 41.5, "拍频信号 @ Δf", fontsize=11, ha="center",
            color="#7c3aed")
    ax.text(50, 20, "全场混频 + 低通数值验证：Pout 公式残差 2.9e-3"
            "（仅低通滤波器通带下垂）",
            ha="center", fontsize=13, color="#475569")
    ax.text(50, 10, "对应论文器件：PL202 激光管 · CCM1-BS013 分束器 · "
            "M0/M1 反射镜 · OPT101 光电接收器 · 示波器",
            ha="center", fontsize=12, color="#6b7280")


# ---------------- 深色雷达/LiDAR 显示器风格场景 ----------------
SC_BG = "#0b1220"        # 场景底色
SC_GRID = "#243247"      # 距离环
SC_BEAM = "#38bdf8"      # 光束
SC_LEGIT = "#4ade80"     # 合法点云
SC_BIKE = "#60a5fa"      # 动态目标
SC_SPOOF = "#f87171"     # 欺骗点
SC_TEXT = "#e2e8f0"      # 标注文字


def _draw_car(ax, x, y, heading_deg=90.0):
    """画一个简易俯视车形 + 车顶 LiDAR。"""
    from matplotlib.patches import Rectangle, Circle
    import matplotlib.transforms as mtransforms
    tr = mtransforms.Affine2D().rotate_deg(heading_deg - 90).translate(x, y) + ax.transData
    body = Rectangle((-1.0, -1.8), 2.0, 3.6, fc="#166534", ec="#4ade80",
                     lw=2.0, transform=tr, zorder=6)
    ax.add_patch(body)
    lidar = Circle((0, 0.5), 0.5, fc="#bbf7d0", ec="#052e16", lw=1.4,
                   transform=tr, zorder=7)
    ax.add_patch(lidar)


def _draw_virtual_scene(ax_scene):
    from . import simulator as sim
    from matplotlib.patches import Wedge

    # ---------------- 左：场景（scan() 第 0 帧真实数据，深色雷达风格）
    ax_scene.set_facecolor(SC_BG)
    ax_scene.set_aspect("equal")
    ax_scene.set_xlim(-17, 17); ax_scene.set_ylim(-8, 45)
    for s in ax_scene.spines.values():
        s.set_color("#334155")
    ax_scene.tick_params(colors="#94a3b8", labelsize=10.5)
    rng = np.random.default_rng(0)
    ego_speed, segs, attacks, anchors = sim.build_scene()
    ego = np.zeros(2)
    frame = sim.scan(rng, ego, ego_speed, segs, attacks)

    # 距离环 + 十字线
    for r in (10, 20, 30, 40):
        ring = plt.Circle((0, 0), r, fill=False, ec=SC_GRID, lw=0.9, ls="--")
        ax_scene.add_patch(ring)
        ax_scene.text(r * np.cos(np.deg2rad(105)), r * np.sin(np.deg2rad(105)),
                      f"{r} m", fontsize=11, color="#cbd5e1", ha="center",
                      va="center", zorder=9,
                      bbox=dict(boxstyle="round,pad=0.18", fc=SC_BG,
                                ec="none", alpha=0.75))
    ax_scene.axhline(0, color=SC_GRID, lw=0.6)
    ax_scene.axvline(0, color=SC_GRID, lw=0.6)

    # 场景线段（墙体/立柱/自行车）
    for seg in segs:
        ax_scene.plot([seg.p[0], seg.q[0]], [seg.p[1], seg.q[1]],
                      color="#94a3b8", lw=4, solid_capstyle="round",
                      alpha=0.95, zorder=3)

    # 光束 + 回波
    for deg, (d, label, spf, _) in frame.items():
        th = np.deg2rad(deg)
        x, y = d * np.cos(th), d * np.sin(th)
        ax_scene.plot([0, x], [0, y], color=SC_BEAM, lw=0.45, alpha=0.14,
                      zorder=1)
        if spf:
            ax_scene.plot(x, y, "x", color=SC_SPOOF, ms=8, mew=2, zorder=5)
        elif label == "bike":
            ax_scene.plot(x, y, "^", color=SC_BIKE, ms=7, zorder=5)
        else:
            ax_scene.plot(x, y, "o", color=SC_LEGIT, ms=3.2,
                          markeredgecolor="none", zorder=4)

    # 三类欺骗注入的攻击窗口扇形（红色）
    wedges = [
        (np.degrees(np.arctan2(*attacks["static"]["pos"][::-1])),
         np.rad2deg(attacks["static"]["win"]), 34, "注入窗口"),
        (attacks["ahead"]["fake_theta"], np.rad2deg(attacks["ahead"]["win"]),
         14, None),
        (attacks["beside"]["theta"], np.rad2deg(attacks["beside"]["win"]),
         10.5, None),
    ]
    for center_deg, halfw, r, lab in wedges:
        w = Wedge((0, 0), r, center_deg - halfw, center_deg + halfw,
                  fc=SC_SPOOF, alpha=0.30, ec="#fca5a5", lw=1.2, ls="--", zorder=2)
        ax_scene.add_patch(w)

    # 自车（车形 + LiDAR + 速度矢量）
    _draw_car(ax_scene, 0, 0)
    ax_scene.annotate("", xy=(0, 7.5), xytext=(0, 3.2),
                      arrowprops=dict(arrowstyle="-|>", color="#4ade80", lw=2))
    ax_scene.text(0.9, 6.0, "11 m/s", fontsize=12, color="#4ade80",
                  weight="bold", zorder=9)

    # 标注
    def note(text, xy, xytext, color):
        ax_scene.annotate(text, xy=xy, xytext=xytext, fontsize=11.5, color=color,
                          arrowprops=dict(arrowstyle="->", color=color, lw=1.4),
                          zorder=9,
                          bbox=dict(boxstyle="round,pad=0.3", fc=SC_BG,
                                    ec=color, lw=0.7, alpha=0.85))

    note("自车 + 虚拟 2-D LiDAR\n1°×360°，0.1 s/帧", (1.4, 1.9), (-16.5, -6),
         "#4ade80")
    note("虚拟攻击器\n（<60 美元三件套）",
         tuple(attacks["ahead"]["attacker"]), (6.2, 37), "#f87171")
    note("假静态墙\n（场景1）", tuple(attacks["static"]["pos"]), (-16.2, 33),
         "#f87171")
    note("前方假车\n（场景3）", (0, 12), (-16.2, 20.5), "#f87171")
    note("侧方假目标\n（局限1）", (9, 0), (10.8, -6), "#f87171")
    note("自行车\n（动态合法）", (2.5, 25), (6.8, 28.5), "#60a5fa")
    note("立柱", (0, 20), (-5.2, 23.5), "#fde68a")
    note("红扇形 = 欺骗注入\n角窗口（式2）", (np.cos(np.deg2rad(93.8)) * 24,
         np.sin(np.deg2rad(93.8)) * 24), (-16.2, 12.5), "#fca5a5")

    ax_scene.set_title("虚拟攻击场景（scan() 第 0 帧真实渲染）\n"
                       "红色扇形 = 式(2)欺骗注入的角窗口", fontsize=13.5,
                       color="#0f172a")
    ax_scene.set_xlabel("x (m)", fontsize=12)
    ax_scene.set_ylabel("y (m)", fontsize=12)

def _draw_virtual_impl(ax_impl):
    # 器件实现说明（独立面板）
    ax_impl.set_xlim(0, 100); ax_impl.set_ylim(0, 100); ax_impl.axis("off")
    ax_impl.text(50, 97, "虚拟器件与实现方式", ha="center", fontsize=16,
                 weight="bold")
    _device_box(ax_impl, 50, 83, 90, 18, "虚拟 2-D LiDAR（替代 YD X2L）",
                "scan()：360 条光线 × 场景线段求交，最近交点 = 回波\n"
                "测距噪声 σ = 3 cm · 0.1 s/帧 · 替代真实 ToF 收发")
    _device_box(ax_impl, 50, 60, 90, 20, "虚拟攻击器（<60 美元三件套）",
                "光电二极管(同步)：攻击方向窗口 ±3°~4°（红色扇形）\n"
                "延时器：式(2) $t_a=t_s+\\tau_{spoof}$ → 假距离 $d^{(spf)}$\n"
                "激光管：假距离 < 真回波距离 → 先到先得替换")
    _device_box(ax_impl, 50, 37, 90, 18, "虚拟 Doppler 信道（式 5/6）",
                "合法回波 $\\hat v_{Dop}=v_r$（往返 2×）· "
                "欺骗回波 $=\\frac{1}{2}v_r$（单程）\n"
                "噪声 σ：式(28)，K = 47.75（论文锚点校准），SNR 可配")
    _device_box(ax_impl, 50, 14, 90, 18, "虚拟跟踪 + 检测（式 8/9、18/19）",
                "锚点方向逐帧取束 · 实际 Δt 差分得 $v_{ToF}$（遮挡不断档）\n"
                "$(v_{Dop},v_{ToF})\\times$ 前 20 帧 → Hotelling T² → 判决+滤除",
                fc=C_SW, ec=C_SW_EDGE)
    _arrow(ax_impl, 50, 73.5, 50, 70.5, color="#475569", ms=13, lw=2)
    _arrow(ax_impl, 50, 49.5, 50, 46.5, color="#475569", ms=13, lw=2)
    _arrow(ax_impl, 50, 27.5, 50, 23.5, color="#475569", ms=13, lw=2)
    ax_impl.text(50, 1.5, "判决：5 合法目标全部通过 · 场景 1/3 假目标检出 · "
                "侧方同速假目标漏检（= 论文自述局限）",
                ha="center", fontsize=12, color="#6b7280")


def plot_virtual_testbed(out_path):
    fig = plt.figure(figsize=(18, 16.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.3],
                          width_ratios=[1.08, 1.0])
    ax_a = fig.add_subplot(gs[0, :])
    _panel_virtual_interferometer(ax_a)
    ax_scene = fig.add_subplot(gs[1, 0])
    ax_impl = fig.add_subplot(gs[1, 1])
    _draw_virtual_scene(ax_scene)
    _draw_virtual_impl(ax_impl)
    fig.suptitle("仿真硬件原理图：虚拟器件及其实现方式", fontsize=17,
                 weight="bold", y=0.998)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
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


def _save_fig(fig, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_panels(figdir):
    """单面板小图（GitHub README 内嵌用：图窄 → 同字号显示更大）。"""
    fig, ax = plt.subplots(figsize=(10.8, 6.6))
    _panel_interferometer(ax)
    fig.tight_layout()
    _save_fig(fig, f"{figdir}/fig_map_interferometer.png")

    fig, ax = plt.subplots(figsize=(10.8, 6.6))
    _panel_lidar(ax)
    fig.tight_layout()
    _save_fig(fig, f"{figdir}/fig_map_attack.png")

    fig, ax = plt.subplots(figsize=(10.8, 7.8))
    _panel_virtual_interferometer(ax)
    fig.tight_layout()
    _save_fig(fig, f"{figdir}/fig_virtual_interferometer.png")

    fig, ax = plt.subplots(figsize=(9.6, 9.8))
    _draw_virtual_scene(ax)
    fig.tight_layout()
    _save_fig(fig, f"{figdir}/fig_virtual_scene.png")

    fig, ax = plt.subplots(figsize=(10.8, 7.4))
    _draw_virtual_impl(ax)
    fig.tight_layout()
    _save_fig(fig, f"{figdir}/fig_virtual_impl.png")


if __name__ == "__main__":
    import sys
    root = "figures"
    plot_hw_mapping(f"{root}/fig_hw_mapping.png")
    print(f"saved: {root}/fig_hw_mapping.png")
    plot_virtual_testbed(f"{root}/fig_virtual_testbed.png")
    print(f"saved: {root}/fig_virtual_testbed.png")
    plot_panels(root)
    print("saved: 5 panel figures")
