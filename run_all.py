#!/usr/bin/env python3
"""一键复现论文全部软件可复现结果：

  1. 多普勒模型自检（式 3-6、15）
  2. Proposition 1 数值验证 + "两把锁"演示（式 8-14）
  3. Fig.11 复现（协同 LiDAR Doppler 速度差异）   → figures/fig11.png + results/fig11.csv
  4. H0 显著性水平检验（经验 α ≈ 0.05）
  5. Fig.13 复现（最小样本量 vs 欺骗比例）        → figures/fig13.png + results/fig13.csv
  6. Fig.14 复现（最小样本量 vs SNR）             → figures/fig14.png + results/fig14.csv
  7. F1 锚点验证（0.923 / 0.97）+ bernoulli 对比  → results/anchors.txt

用法:  python3 run_all.py [--quick]
  --quick: 减少蒙特卡洛 trial 数，用于快速冒烟测试（结果精度略降）。
"""
import argparse
import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import cooperative
from src.detection import f1_score
from src import detection as det
from src.doppler import sanity_report
from src import power_analysis as pa

ROOT = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(ROOT, "figures")
RES_DIR = os.path.join(ROOT, "results")

PHI_LABELS = {np.pi / 2: "π/2", np.pi / 3: "π/3", np.pi / 4: "π/4", 0.0: "0"}
ROAD_LABELS = {"highway": "highway (v=33,a=0.5)",
               "ramp": "ramp (v=20,a=1.5)", "city": "city (v=11,a=5)"}
ROAD_STYLE = {"highway": "o-", "ramp": "s--", "city": "^-."}


def step1_doppler(log):
    log("=" * 70)
    log("步骤 1：多普勒模型自检（式 3-6、15）")
    log("=" * 70)
    for line in sanity_report().splitlines():
        log("  " + line)


def step2_prop1(log):
    log("")
    log("=" * 70)
    log("步骤 2：Proposition 1 数值验证（式 8-14）")
    log("=" * 70)
    r = cooperative.verify_prop1()
    log(f"  欺骗距离: dm={r['dm']:.4f} m, dn={r['dn']:.4f} m（均为正，物理合理）")
    log(f"  ToF 速度向量     = {np.round(r['tof_velocity_vec'], 6)}")
    log(f"  Doppler 速度向量 = {np.round(r['doppler_velocity_vec'], 6)}")
    log(f"  相对误差 = {r['relative_error']:.2e}  → Prop.1 精确成立")
    d = cooperative.two_locks_demo()
    log(f"  [两把锁演示] 同一攻击者速度 va=({d['va'][0]:.0f} m/s, "
        f"{np.rad2deg(d['va'][1]):.0f}°):")
    log(f"    ego-LiDAR (2 m/s) 感知伪目标速度 = {np.round(d['doppler_velocity_ego'], 3)}")
    log(f"    coop-LiDAR (3 m/s) 感知伪目标速度 = {np.round(d['doppler_velocity_coop'], 3)}")
    log(f"    差异范数 = {d['difference_norm']:.3f} m/s ≠ 0 → 共享 Doppler 速度即可暴露攻击")


def step3_fig11(log):
    log("")
    log("=" * 70)
    log("步骤 3：Fig.11 复现 —— 协同 LiDAR 的 Doppler 速度差")
    log("=" * 70)
    combos = [(2.0, 1.0), (2.0, 3.0), (2.0, 4.0), (2.0, 2.0)]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True, sharey=True)
    rows = []
    for ax, (v_ego, v_coop) in zip(axes.flat, combos):
        va, curves = cooperative.fig11_data(v_ego, v_coop)
        for phi_a, y in curves.items():
            ax.plot(va, y, label=rf"$\varphi_a$={PHI_LABELS[phi_a]}")
            for x, yy in zip(va[::40], y[::40]):
                rows.append((v_ego, v_coop, PHI_LABELS[phi_a], x, yy))
        ax.axhline(0.0, color="gray", lw=0.8)
        ax.set_title(rf"$|v_L^{{ego}}|$={v_ego:.0f}, $|v_L^{{coop}}|$={v_coop:.0f} m/s")
        ax.grid(alpha=0.3)
        if v_ego == v_coop:
            detectable = "不可检测（速度相同）"
        else:
            detectable = "可检测（差 ≠ 0）"
        log(f"  ego={v_ego:.0f}, coop={v_coop:.0f} m/s → {detectable}")
    for ax in axes[1, :]:
        ax.set_xlabel(r"attacker speed $|v_a|$ (m/s)")
    for ax in axes[:, 0]:
        ax.set_ylabel(r"$|v_{Dop}^{coop}| - |v_{Dop}^{ego}|$ (m/s)")
    axes[0, 0].legend(fontsize=9)
    fig.suptitle("Fig.11 reproduction: cooperative-LiDAR Doppler velocity difference "
                 "(attacker ahead, $\\theta$=90°)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig11.png"), dpi=150)
    plt.close(fig)
    with open(os.path.join(RES_DIR, "fig11.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["v_ego", "v_coop", "phi_a", "va_mag", "doppler_diff"])
        w.writerows(rows)
    log(f"  已保存 figures/fig11.png 与 results/fig11.csv")


def step4_size(log, k, trials):
    log("")
    log("=" * 70)
    log("步骤 4：H0 显著性水平检验（经验 α 应 ≈ 0.05）")
    log("=" * 70)
    rng = np.random.default_rng(2024)
    for road in det.ROAD_CONDITIONS:
        size_h = det.empirical_reject_rate(rng, 50, road, None, 0.0, 1e-4,
                                           trials=trials, k=k)
        size_t = det.empirical_reject_rate(rng, 50, road, None, 0.0, 1e-4,
                                           trials=trials, k=k, test="ttest")
        log(f"  {road:8s}: Hotelling T² = {size_h:.4f}   t 检验 = {size_t:.4f}")


def step5_fig13(log, k, trials):
    log("")
    log("=" * 70)
    log("步骤 5：Fig.13 复现 —— 最小样本量 vs 欺骗比例（SNR=1e-4）")
    log("=" * 70)
    rows = pa.fig13_data(np.random.default_rng(31), k, trials=trials)
    with open(os.path.join(RES_DIR, "fig13.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["attack", "road", "spoofed_proportion", "snr", "min_samples"])
        w.writerows(rows)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, attack in zip(axes, (1, 2, 3)):
        for road in det.ROAD_CONDITIONS:
            xs = [r[2] for r in rows if r[0] == attack and r[1] == road]
            ys = [r[4] for r in rows if r[0] == attack and r[1] == road]
            ax.plot(xs, ys, ROAD_STYLE[road], label=ROAD_LABELS[road], ms=5)
        ax.set_title(f"attack scenario {attack}")
        ax.set_xlabel("spoofed signal proportion $p$")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("min #samples for power 0.9")
    axes[0].legend(fontsize=8)
    fig.suptitle("Fig.13 reproduction: samples needed vs spoofed proportion (SNR=1e-4, α=0.05)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig13.png"), dpi=150)
    plt.close(fig)
    for road in det.ROAD_CONDITIONS:
        pts = {r[2]: r[4] for r in rows if r[0] == 1 and r[1] == road}
        line = ", ".join(f"p={p:g}:{n}" for p, n in sorted(pts.items()))
        log(f"  attack1 {road:8s}: {line}")
    log("  已保存 figures/fig13.png 与 results/fig13.csv")


def step6_fig14(log, k, trials):
    log("")
    log("=" * 70)
    log("步骤 6：Fig.14 复现 —— 最小样本量 vs SNR（p=0.1）")
    log("=" * 70)
    rows = pa.fig14_data(np.random.default_rng(41), k, trials=max(800, trials // 2))
    with open(os.path.join(RES_DIR, "fig14.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["attack", "road", "spoofed_proportion", "snr", "min_samples"])
        w.writerows(rows)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, attack in zip(axes, (1, 2, 3)):
        for road in det.ROAD_CONDITIONS:
            xs = [r[3] for r in rows if r[0] == attack and r[1] == road]
            ys = [r[4] for r in rows if r[0] == attack and r[1] == road]
            ax.plot(xs, ys, ROAD_STYLE[road], label=ROAD_LABELS[road], ms=5)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"attack scenario {attack}")
        ax.set_xlabel("SNR")
        ax.grid(alpha=0.3, which="both")
    axes[0].set_ylabel("min #samples for power 0.9")
    axes[0].legend(fontsize=8)
    fig.suptitle("Fig.14 reproduction: samples needed vs SNR (p=0.1, α=0.05, log-log)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig14.png"), dpi=150)
    plt.close(fig)
    for road in det.ROAD_CONDITIONS:
        pts = {r[3]: r[4] for r in rows if r[0] == 1 and r[1] == road}
        line = ", ".join(f"SNR={s:g}:{n}" for s, n in sorted(pts.items()))
        log(f"  attack1 {road:8s}: {line}")
    log("  已保存 figures/fig14.png 与 results/fig14.csv")


def step7_anchors(log, k, trials):
    log("")
    log("=" * 70)
    log("步骤 7：论文数值锚点验证（§VI-E/F）")
    log("=" * 70)
    out = pa.anchor_checks(np.random.default_rng(51), k, trials=max(4000, trials // 2))
    with open(os.path.join(RES_DIR, "anchors.txt"), "w") as f:
        for key, val in out.items():
            f.write(f"{key} = {val}\n")
    for key, val in out.items():
        log(f"  {key} = {val:.4f}" if isinstance(val, float) else f"  {key} = {val}")
    log("")
    log("  对照论文：α=0.05, β=0.1 → F1=0.923（式验算）")
    log("           p=0.4, SNR=1e-4, n=50 → F1=0.97（论文 §VI-F）")
    log("  bernoulli 对比说明见 README 假设 A4：间歇欺骗引入混合方差，")
    log("  低比例下所需样本量大于论文的总体均值模型（更保守、物理更忠实）。")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="快速冒烟测试")
    args = parser.parse_args()
    os.makedirs(FIG_DIR, exist_ok=True)
    os.makedirs(RES_DIR, exist_ok=True)
    trials = 1500 if args.quick else 6000

    t0 = time.time()
    log = print
    log(f"LiDAR 欺骗检测（IoT-J 2024）软件复现  {'[QUICK]' if args.quick else ''}")
    log(f"噪声幅度 K = {det.NOISE_SCALE_K}（锚点校准值，见 README）")

    step1_doppler(log)
    step2_prop1(log)
    step3_fig11(log)
    step4_size(log, det.NOISE_SCALE_K, trials)
    step5_fig13(log, det.NOISE_SCALE_K, trials)
    step6_fig14(log, det.NOISE_SCALE_K, trials)
    step7_anchors(log, det.NOISE_SCALE_K, trials)

    log("")
    log(f"全部完成，总耗时 {time.time() - t0:.1f}s；图表在 figures/，数据在 results/")


if __name__ == "__main__":
    main()
