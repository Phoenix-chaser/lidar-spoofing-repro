"""功效分析 —— 论文第 VI-D/E/F 节（Fig.13、Fig.14、F1 锚点）的复现。

  1. calibrate_noise_scale(): 校准式(28)噪声幅度 K，使最差条件
     (场景1, city, p=0.1, SNR=1e-4) 的最小样本量 = 50，对齐论文 §VI-F
     "setting the sample size to 50 is sufficient ... F1 0.923 in the worst case"。
     （采用与论文式(21)-(27)一致的 fractional 均值模型，见 README 假设 A4）
  2. min_samples(): 搜索达到目标功效 (0.9) 所需最小样本量 n。
  3. fig13_data(): 欺骗比例 p ∈ [0.1, 1] 扫描（SNR=1e-4）—— 复现 Fig.13。
  4. fig14_data(): SNR ∈ {1e-6, 1e-5, 1e-4} 扫描（p=0.1）—— 复现 Fig.14。
  5. anchor_checks(): F1=0.923 / 0.97 锚点验证、H0 显著性水平检查、
     以及物理忠实的 bernoulli 混合模型对比。
"""
import numpy as np

from . import detection as det

ALPHA = 0.05          # 论文：第一类错误 α=0.05
TARGET_POWER = 0.9    # 论文：功效 0.9（即 β=0.1）


# ---------------------------------------------------------------- 校准
def calibrate_noise_scale(rng, target_n=50, attack=1, road="city", p=0.1,
                          snr=1e-4, trials=3000, k_lo=1.0, k_hi=400.0, iters=14):
    """二分法校准式(28)噪声幅度 K（最小样本量随 K 单调递增）。"""
    def min_n(k):
        return min_samples(rng, road, attack, p, snr, alpha=ALPHA,
                           target=TARGET_POWER, trials=trials, k=k,
                           n_max=8 * target_n)
    lo, hi = k_lo, k_hi
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if min_n(mid) > target_n:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------- 最小样本量搜索
def min_samples(rng, road, attack, p, snr, alpha=ALPHA, target=TARGET_POWER,
                trials=2000, n_min=4, n_max=30000, k=None, rel_tol=0.01,
                model="fractional"):
    """搜索达到目标功效的最小样本量 n（粗几何网格定位 + 整数二分细化）。"""
    def power(n):
        return det.empirical_reject_rate(rng, n, road, attack, p, snr,
                                         alpha=alpha, trials=trials, k=k,
                                         model=model)

    # 1) 粗网格找上界
    grid = sorted({int(round(x)) for x in np.geomspace(n_min, n_max, 50)})
    lo, hi = None, None
    prev = n_min - 1
    for n in grid:
        if n < n_min:
            continue
        if power(n) >= target:
            hi, lo = n, prev
            break
        prev = n
    if hi is None:
        return n_max   # 达到 n_max 仍未达标（封顶，结果中标注）

    # 2) 整数二分（功效关于 n 单调不减），大 n 时按相对精度收步
    step = max(1, int(rel_tol * hi))
    while hi - lo > step:
        mid = (lo + hi) // 2
        if mid <= n_min:
            break
        if power(mid) >= target:
            hi = mid
        else:
            lo = mid
    # 3) 高精度确认（消除搜索阶段 MC 噪声）
    while power(hi) < target:
        hi += step
    return hi


# ---------------------------------------------------------------- Fig.13 / Fig.14 数据
def fig13_data(rng, k, proportions=None, snr=1e-4, roads=("highway", "ramp", "city"),
               attacks=(1, 2, 3), trials=2000, model="fractional"):
    """Fig.13：不同欺骗信号比例 p 下的最小样本量（SNR=1e-4）。"""
    proportions = proportions if proportions is not None else \
        [round(x, 1) for x in np.arange(0.1, 1.01, 0.1)]
    rows = []
    for attack in attacks:
        for road in roads:
            for p in proportions:
                n = min_samples(rng, road, attack, p, snr, alpha=ALPHA,
                                target=TARGET_POWER, trials=trials, k=k,
                                model=model)
                rows.append((attack, road, p, snr, n))
    return rows


def fig14_data(rng, k, snrs=None, p=0.1, roads=("highway", "ramp", "city"),
               attacks=(1, 2, 3), trials=1500, model="fractional"):
    """Fig.14：不同 SNR 下的最小样本量（p=0.1）。"""
    snrs = snrs if snrs is not None else list(det.SNR_LEVELS)
    rows = []
    for attack in attacks:
        for road in roads:
            for snr in snrs:
                n = min_samples(rng, road, attack, p, snr, alpha=ALPHA,
                                target=TARGET_POWER, trials=trials, k=k,
                                n_max=100000, model=model)
                rows.append((attack, road, p, snr, n))
    return rows


# ---------------------------------------------------------------- 锚点验证
def anchor_checks(rng, k, n=50, trials=8000):
    """验证论文 §VI-E/F 的数值锚点，并给出 bernoulli 模型对比。"""
    out = {}
    # F1 公式（均衡类）：α=0.05, β=0.1 → 0.923（论文数值）
    out["F1_formula(a=0.05,b=0.1)"] = det.f1_score(0.05, 0.1)

    # ---- fractional 模型（论文机制）----
    # 锚点1：最差条件 n=50 → power≈0.9 → F1≈0.923
    power_worst = det.empirical_reject_rate(
        rng, n, "city", 1, 0.1, 1e-4, alpha=ALPHA, trials=trials, k=k)
    out["[fractional] power(city,atk1,p=0.1,snr=1e-4,n=50)"] = power_worst
    out["[fractional] F1_worst(p=0.1)"] = det.f1_score(ALPHA, 1 - power_worst)
    # 锚点2：p=0.4, SNR=1e-4, n=50 → F1≈0.97（三种路况）
    for road in det.ROAD_CONDITIONS:
        pw = det.empirical_reject_rate(
            rng, n, road, 1, 0.4, 1e-4, alpha=ALPHA, trials=trials, k=k)
        out[f"[fractional] F1_{road}(p=0.4,n=50)"] = det.f1_score(ALPHA, 1 - pw)

    # ---- H0 显著性水平检查：经验 α 应≈0.05 ----
    for road in det.ROAD_CONDITIONS:
        out[f"size_H0({road},n=50)"] = det.empirical_reject_rate(
            rng, n, road, None, 0.0, 1e-4, alpha=ALPHA, trials=trials, k=k)

    # ---- 基线对比：仅速度的 t 检验（式17）在最差条件下 ----
    out["power_ttest(city,atk1,p=0.1,snr=1e-4,n=50)"] = det.empirical_reject_rate(
        rng, n, "city", 1, 0.1, 1e-4, alpha=ALPHA, trials=trials, k=k,
        test="ttest")

    # ---- bernoulli 模型对比（物理忠实的间歇欺骗，含混合方差）----
    pw_b = det.empirical_reject_rate(
        rng, n, "city", 1, 0.1, 1e-4, alpha=ALPHA, trials=trials, k=k,
        model="bernoulli")
    out["[bernoulli] power(city,atk1,p=0.1,snr=1e-4,n=50)"] = pw_b
    out["[bernoulli] F1(p=0.1,n=50)"] = det.f1_score(ALPHA, 1 - pw_b)
    n_bernoulli = min_samples(rng, "city", 1, 0.1, 1e-4, alpha=ALPHA,
                              target=TARGET_POWER, trials=3000, k=k,
                              model="bernoulli")
    out["[bernoulli] min_samples(city,atk1,p=0.1,snr=1e-4)"] = n_bernoulli
    return out
