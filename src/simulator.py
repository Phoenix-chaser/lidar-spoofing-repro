"""2-D LiDAR 仿真 + 欺骗攻击注入 + 检测闭环（论文 Fig.3/4 攻击演示的软件模拟）。

链路（与论文对应）：
  场景光线投射（合法回波） → 式(2) ToF 欺骗注入（伪造 dspoof 处的假点）
  → 式(5)(6) 逐点合成 Doppler（合法=2×相对径向速度，欺骗=1×）
  → 逐目标锚点跟踪采样 (v_Dop, v_ToF)（对应论文式 8/9 的目标级跟踪）
  → Hotelling T² 检测器（式 18/19）判决 → 输出"检测前 vs 滤除后"点云

约定（与其余模块一致）：θ 从 +x 轴起，l=(cosθ, sinθ)，自车沿 +y 运动。

跟踪说明：真实 LiDAR/论文式(8)(9) 跟踪的是"同一目标点随运动变角"，而非
固定波束角（固定角扫过无限长墙面时命中点沿墙滑动，ToF 与 Doppler 将不再
对应同一点）。因此本仿真按每个目标的锚点方向逐帧取束、跨帧差分得 v_ToF，
对合法目标两估计量天然一致（v_ego·l − v_obj·l），对欺骗目标呈现 2:1 失配。
"""
import numpy as np
from scipy import stats

from . import detection as det


# ---------------------------------------------------------------- 几何工具
def _ray_segment(px, py, dx, dy, x1, y1, x2, y2):
    """射线 p+t·d 与线段的最近交点距离（无交点返回 +inf）。"""
    ex, ey = x2 - x1, y2 - y1
    denom = dx * ey - dy * ex
    if abs(denom) < 1e-12:
        return np.inf
    t = ((x1 - px) * ey - (y1 - py) * ex) / denom
    s = ((x1 - px) * dy - (y1 - py) * dx) / denom
    if t > 1e-6 and -1e-9 <= s <= 1 + 1e-9:
        return t
    return np.inf


def _ang_diff(a, b):
    """角度差（度）归一到 [0, 180]。"""
    return abs((a - b + 180.0) % 360.0 - 180.0)


class Segment:
    """场景中的目标（线段）：label + 可选速度向量（动态目标）。"""

    def __init__(self, x1, y1, x2, y2, label, velocity=(0.0, 0.0)):
        self.p = np.array([x1, y1], float)
        self.q = np.array([x2, y2], float)
        self.label = label
        self.v = np.array(velocity, float)

    def advance(self, dt):
        self.p = self.v * dt + self.p
        self.q = self.v * dt + self.q


# ---------------------------------------------------------------- 场景
def build_scene():
    """自车 (0,0) 沿 +y 以 11 m/s（city 路况）运动；360° 2-D LiDAR。

    合法目标：前方墙、左右侧墙、路边立柱、横穿自行车（动态，检验不误报）。
    欺骗目标（对应论文三类攻击模型中的两类 + 一个自述局限）：
      fake_static  静态假墙块（静态攻击者）—— 攻击场景 1（预期可检出）
      fake_ahead   路边攻击者伪造"正前方恒距假车"—— 攻击场景 3（预期可检出）
      fake_beside  与自车同速、保持正侧方的假目标 —— 相对径向速度≈0，
                   论文 §VII-D 局限 1（预期不可检出，如实展示）
    """
    ego_speed = 11.0
    segs = [
        Segment(-12, 60, 12, 60, "front_wall"),
        Segment(-12, -2, -12, 60, "left_wall"),
        Segment(12, -2, 12, 60, "right_wall"),
        Segment(-0.3, 19.5, 0.3, 20.5, "pillar"),
        Segment(2.3, 24.7, 2.7, 25.3, "bike", velocity=(1.2, 0.0)),
    ]
    attacks = {
        "static": dict(pos=np.array([-2.0, 30.0]), win=np.deg2rad(3.0),
                       label="fake_static"),
        "ahead": dict(attacker=np.array([6.0, 20.0]), fake_theta=90.0,
                      win=np.deg2rad(2.0), fake_dist=12.0, label="fake_ahead"),
        "beside": dict(theta=0.0, win=np.deg2rad(1.0), dist=9.0,
                       label="fake_beside"),
    }
    # 各目标锚点（世界坐标；bike 随时间移动；fake_ahead/beside 随自车移动）
    def anchors(t, ego_xy):
        return {
            "front_wall": np.array([0.0, 60.0]),
            "left_wall": np.array([-12.0, 30.0]),
            "right_wall": np.array([12.0, 35.0]),
            "pillar": np.array([0.0, 20.0]),
            "bike": np.array([2.5 + 1.2 * t, 25.0]),
            "fake_static": np.array([-2.0, 30.0]),
            "fake_ahead": ego_xy + np.array([0.0, 12.0]),
            "fake_beside": ego_xy + np.array([9.0, 0.0]),
        }
    return ego_speed, segs, attacks, anchors


# ---------------------------------------------------------------- 单次扫描
def scan(rng, ego_xy, ego_speed, segs, attacks, dist_noise=0.03):
    """一次 360° 扫描：合法回波 + 式(2)欺骗注入。

    返回 {角度(整数度): (d_meas, label, is_spoofed, v_r_true)}，
    其中 v_r_true 为该回波对应物理点的真实相对径向速度（Doppler 真值，
    往返/单程的 2:1 因子在跟踪阶段施加，噪声也彼处施加）。
    欺骗回波"先到先得"：假点距离小于真回波时替换之（论文 ToF 欺骗机理）。
    """
    out = {}
    ego_v = np.array([0.0, ego_speed])
    for deg in range(360):
        theta = np.deg2rad(deg)
        l = np.array([np.cos(theta), np.sin(theta)])
        best_d, best_label, best_obj_v = np.inf, None, np.zeros(2)
        for seg in segs:
            d = _ray_segment(ego_xy[0], ego_xy[1], l[0], l[1],
                             seg.p[0], seg.p[1], seg.q[0], seg.q[1])
            if d < best_d:
                best_d, best_label, best_obj_v = d, seg.label, seg.v

        is_spoofed, v_r_true = False, 0.0
        for name, atk in attacks.items():
            if name == "beside":    # 与自车同速保持正侧方：固定 θ、固定距离
                if _ang_diff(deg, np.rad2deg(atk["theta"])) <= np.rad2deg(atk["win"]):
                    best_d, best_label = atk["dist"], atk["label"]
                    is_spoofed, v_r_true = True, 0.0
            elif name == "ahead":    # 攻击场景 3：正前方恒距假车（路边攻击者发射）
                if _ang_diff(deg, atk["fake_theta"]) <= np.rad2deg(atk["win"]):
                    dir_a = np.arctan2(atk["attacker"][1] - ego_xy[1],
                                       atk["attacker"][0] - ego_xy[0])
                    l_a = np.array([np.cos(dir_a), np.sin(dir_a)])
                    best_d, best_label = atk["fake_dist"], atk["label"]
                    # Doppler 来自攻击者单程信号：相对径向速度按攻击者方向计
                    is_spoofed, v_r_true = True, float(ego_v @ l_a)
            else:                    # 静态假物（攻击场景 1）
                dir_f = np.degrees(np.arctan2(atk["pos"][1] - ego_xy[1],
                                              atk["pos"][0] - ego_xy[0]))
                if _ang_diff(deg, dir_f) <= np.rad2deg(atk["win"]):
                    best_d = float(np.linalg.norm(atk["pos"] - ego_xy))
                    best_label = atk["label"]
                    is_spoofed, v_r_true = True, float(ego_v @ l)
            if is_spoofed:
                break

        if not np.isfinite(best_d):
            continue
        if not is_spoofed:
            v_r_true = float((ego_v - best_obj_v) @ l)
        out[deg] = (best_d + rng.normal(0.0, dist_noise),
                    best_label, is_spoofed, v_r_true)
    return out


# ---------------------------------------------------------------- 闭环
def run_closed_loop(n_scans=50, scan_period=0.1, snr=1e-4, alpha=0.05,
                    seed=123, tol_deg=3.0, win=20):
    """完整闭环：仿真 → 攻击 → Doppler 合成 → 逐目标 T² 判决。

    win: 检验窗口（每个目标取前 win 个样本，即"接近段"）。论文 §VII-D-2
    假设相邻测量间相对速度近似恒定（匀速模型），均值一致性检验应在短窗口
    内进行；若用整条通过轨迹（vr 从 +11 扫到 −11），共同的轨迹方差会稀释
    2:1 失配（实测 T² 从数百降到 ~5）。
    """
    rng = np.random.default_rng(seed)
    ego_speed, segs, attacks, anchors = build_scene()
    sigma_dop, _ = det.doppler_noise_std(snr)          # 式(28)，K=47.75
    ego_xy = np.zeros(2)
    scans = []
    for k in range(n_scans):
        scans.append((ego_xy.copy(), scan(rng, ego_xy, ego_speed, segs, attacks)))
        for seg in segs:
            seg.advance(scan_period)
        ego_xy = ego_xy + np.array([0.0, ego_speed * scan_period])

    # ---- 锚点跟踪：每帧取最接近锚点方向、label 匹配的光束；
    #      v_ToF 用两次实际采样之间的时间差分（遮挡断档时不出离群值）
    per_track, prev_d = {}, {}
    for k, (pos, frame) in enumerate(scans):
        t = k * scan_period
        for label, P in anchors(t, pos).items():
            a_dir = np.degrees(np.arctan2(P[1] - pos[1], P[0] - pos[0])) % 360.0
            cands = [d0 for d0, (dd, lb, sp, vr) in frame.items()
                     if lb == label and _ang_diff(d0, a_dir) <= tol_deg]
            if not cands:
                continue
            ang = min(cands, key=lambda a: _ang_diff(a, a_dir))
            d_meas, _, is_spoofed, v_r_true = frame[ang]
            if label in prev_d:
                dt = t - prev_d[label][0]
                v_tof = (prev_d[label][1] - d_meas) / dt
                v_tof += rng.normal(0.0, 0.03 * abs(v_tof))
                # 式(5)(6)：合法(往返)=v_r_true；欺骗(单程)被按往返解释=½·v_r_true
                v_dop = (0.5 * v_r_true if is_spoofed else v_r_true) \
                    + rng.normal(0.0, sigma_dop)
                tr = per_track.setdefault(label, {"vd": [], "vt": []})
                tr["vd"].append(v_dop)
                tr["vt"].append(v_tof)
            prev_d[label] = (t, d_meas)

    # ---- T² 判决（式 18/19）；每目标取前 win 个样本（接近段，准匀速）；
    #      加速度维取各自速度序列的相邻差分
    results = {}
    for label, tr in per_track.items():
        m = min(len(tr["vd"]), len(tr["vt"]), win)
        if m < 10:
            continue
        vd = np.asarray(tr["vd"][:m])
        vt = np.asarray(tr["vt"][:m])
        ad = np.diff(vd) / scan_period
        at = np.diff(vt) / scan_period
        x_d = np.stack([vd[1:], ad], axis=1)[None, :, :]
        x_t = np.stack([vt[1:], at], axis=1)[None, :, :]
        t2, reject = det.hotelling_t2_batch(x_d, x_t, alpha)
        n = m - 1
        crit = (4 * n - 4) / (2 * n - 3) * stats.f.ppf(1 - alpha, 2, 2 * n - 3)
        results[label] = {"n": m, "T2": float(t2[0]), "crit": float(crit),
                          "reject": bool(reject[0]),
                          "truth_spoofed": label.startswith("fake")}
    return results, scans


def summarize(results):
    """输出判决表 + 正确率。"""
    n_corr = sum(1 for r in results.values()
                 if r["reject"] == r["truth_spoofed"])
    lines = [f"{'目标':14s} {'样本数':>5s} {'T²':>10s} {'临界值':>8s} "
             f"{'判决':>5s} {'真实':>5s} {'正确':>4s}"]
    for label, r in sorted(results.items()):
        verdict = "欺骗" if r["reject"] else "合法"
        truth = "欺骗" if r["truth_spoofed"] else "合法"
        ok = "✓" if r["reject"] == r["truth_spoofed"] else "✗"
        lines.append(f"{label:14s} {r['n']:5d} {r['T2']:10.1f} {r['crit']:8.1f} "
                     f"{verdict:>4s} {truth:>4s} {ok:>3s}")
    lines.append(f"判决正确率: {n_corr}/{len(results)}（fake_beside 为论文"
                 "§VII-D 自述局限 1 的如实展示：相对径向速度≈0 时不可检）")
    return "\n".join(lines), n_corr, len(results)


def plot_closed_loop(results, scans, out_path, scan_idx=10):
    """检测前 vs 检测后 点云对比图（自车坐标系，深色 LiDAR 显示器风格）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    import matplotlib.transforms as mtransforms

    plt.rcParams["font.family"] = ["Noto Sans CJK SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    BG, GRID, LEGIT, BIKE, SPOOF = "#0b1220", "#243247", "#4ade80", "#60a5fa", "#f87171"
    ego_xy, frame = scans[scan_idx]
    rejected = {lb for lb, r in results.items() if r["reject"]}
    panels = [("Under attack（欺骗点已注入）", False),
              ("After T² detection（欺骗轨迹已滤除）", True)]
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 6.8), sharex=True, sharey=True)
    for ax, (title, filtered) in zip(axes, panels):
        ax.set_facecolor(BG)
        for r_ in (5, 10, 20, 30, 40):
            ax.add_patch(plt.Circle(ego_xy, r_, fill=False, ec=GRID, lw=0.8,
                                    ls="--"))
        ax.axhline(ego_xy[1], color=GRID, lw=0.6)
        ax.axvline(ego_xy[0], color=GRID, lw=0.6)
        for deg, (d, label, spf, _) in frame.items():
            if filtered and label in rejected:
                continue
            th = np.deg2rad(deg)
            x = ego_xy[0] + d * np.cos(th)
            y = ego_xy[1] + d * np.sin(th)
            if spf:
                ax.plot(x, y, "x", color=SPOOF, ms=8, mew=2)
            elif label == "bike":
                ax.plot(x, y, "^", color=BIKE, ms=7)
            else:
                ax.plot(x, y, "o", color=LEGIT, ms=3.4,
                        markeredgecolor="none")
        if filtered:
            miss_xy = (ego_xy[0] + 9.0, ego_xy[1])
            ax.annotate("残留欺骗点 = 侧方假目标\n（论文局限1：相对速度≈0，未检出）",
                        xy=miss_xy, xytext=(ego_xy[0] + 12, ego_xy[1] - 14),
                        fontsize=11.5, color="#fca5a5", zorder=9,
                        arrowprops=dict(arrowstyle="->", color="#fca5a5",
                                        lw=1.3),
                        bbox=dict(boxstyle="round,pad=0.3", fc="#0b1220",
                                  ec="#f87171", lw=0.7, alpha=0.85))
        tr = (mtransforms.Affine2D().rotate_deg(0).translate(*ego_xy)
              + ax.transData)
        ax.add_patch(Rectangle((ego_xy[0] - 1.0, ego_xy[1] - 1.8), 2.0, 3.6,
                               fc="#166534", ec=LEGIT, lw=2, transform=tr,
                               zorder=6))
        ax.add_patch(Circle((ego_xy[0], ego_xy[1] + 0.5), 0.5, fc="#bbf7d0",
                            ec="#052e16", lw=1.4, zorder=7))
        ax.set_title(title, fontsize=14)
        ax.set_xlabel("x (m)", fontsize=12.5)
        ax.set_aspect("equal")
        ax.tick_params(colors="#94a3b8", labelsize=10.5)
        for sp in ax.spines.values():
            sp.set_color("#334155")
    axes[0].set_ylabel("y (m)", fontsize=12.5)
    handles = [
        plt.Line2D([], [], marker="x", ls="", color=SPOOF, ms=9, mew=2,
                   label="欺骗点（注入）"),
        plt.Line2D([], [], marker="^", ls="", color=BIKE, ms=8,
                   label="自行车（动态合法）"),
        plt.Line2D([], [], marker="o", ls="", color=LEGIT, ms=6,
                   label="合法静态点云"),
        plt.Line2D([], [], marker="s", ls="", color="#4ade80", ms=10,
                   markeredgecolor="#052e16", markeredgewidth=1.5,
                   label="自车 + LiDAR"),
    ]
    axes[0].legend(handles=handles, fontsize=11.5, loc="upper left",
                   facecolor="#0f172a", edgecolor="#334155",
                   labelcolor="#e2e8f0")
    fig.suptitle(f"闭环仿真（第 {scan_idx} 帧）：2-D LiDAR + 式(2)欺骗注入 + "
                 "式(5)(6)多普勒 + Hotelling T² 滤除", fontsize=16,
                 weight="bold")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
