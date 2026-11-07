"""统计检测框架 —— 论文第 VI 节的软件复现。

内容：
  1. 样本生成：{x_Dop}n 与 {x_ToF}n，二维随机向量 x=[v, a]（速度, 加速度），
     按"欺骗信号比例 p"混合合法/欺骗样本（论文第 VI-D 节设置）。
  2. 检验统计量：
     - 式(17)：仅速度的两样本 t 检验（基线）
     - 式(18)(19)：联合 [v,a] 的 Hotelling T² 检验（主方法）
  3. 经验功效 / 经验显著性水平（第一类错误）的蒙特卡洛估计。

关键建模假设（论文未完全给出的细节，见 README）：
  A4  欺骗样本按场景改变 {v_Dop, v_ToF} 的均值结构（场景1: μD=2μT；场景2:
      μD=0, μT≠0；场景3: μD≠0, μT=0，均为论文原文），合法样本两者相同；
      混合后均值差 |μ̄D - μ̄T| = p·v_rel，与论文"p 越小两均值越接近、
      所需样本越多"的叙述一致。
  A5  加速度维度：均值在 H0/Ha 下相同（论文的加速机制是"速度谱展宽"，
      属信号级现象，样本级模型中以噪声维度体现，见 README 讨论）。
  A6  ToF 测量误差：论文设 v_ToF/a_ToF 误差率 3%（按真实相对运动幅值的
      比例噪声）；Doppler 估计噪声按式(28)（常数未印全，幅度 K 经锚点校准）。
"""
import numpy as np
from scipy import stats

# ---------------- 论文第 VI-D 节给出的实验设置 ----------------
ROAD_CONDITIONS = {
    # 路况: (车速 v m/s, 加速度 a m/s²)   —— 论文 VI-D-1
    "highway": (33.0, 0.5),
    "ramp": (20.0, 1.5),
    "city": (11.0, 5.0),
}
REL_SPEED_RATIO = 0.5   # "受害者 LiDAR 的相对速度设为路况车速的 50%"（VI-D-1）
TOF_ERR_RATE = 0.03     # v_ToF / a_ToF 误差率 3%（VI-D-3）
SIGNAL_LEN_N = 256      # 式(28) 的信号采样长度 N
SNR_LEVELS = (1e-6, 1e-5, 1e-4)   # 论文 VI-D-3 的三档 SNR

# 式(28) 常数部分按论文印出值（σv²∝3/(SNR·2π²N²)，σa²∝45/(SNR·2π²N⁴)）；
# 总幅度 NOISE_SCALE_K 经论文锚点校准（§VI-F：最差条件 n=50 达 power 0.9）。
# 校准：二分搜索 K 使 min_samples(city, 场景1, p=0.1, SNR=1e-4) = 50，
# 得 K=47.75（解析估计 ≈49，一致）；两个论文锚点（F1 0.923 / 0.97）同时命中。
# 重新校准可运行 power_analysis.calibrate_noise_scale()。
NOISE_SCALE_K = 47.75


def relative_motion(road: str):
    """该路况下 LiDAR 相对目标的 (v_rel, a_rel)。"""
    v_road, a_road = ROAD_CONDITIONS[road]
    return REL_SPEED_RATIO * v_road, a_road


def doppler_noise_std(snr: float, k: float = None):
    """式(28)：MLE 多普勒速度/加速度估计标准差。"""
    if k is None:
        k = NOISE_SCALE_K if NOISE_SCALE_K is not None else 1.0
    sigma_v = np.sqrt(k * 3.0 / (snr * 2.0 * np.pi ** 2 * SIGNAL_LEN_N ** 2))
    sigma_a = np.sqrt(k * 45.0 / (snr * 2.0 * np.pi ** 2 * SIGNAL_LEN_N ** 4))
    return sigma_v, sigma_a


# 三个攻击场景的欺骗样本速度均值 (μ_vD_spoof, μ_vT_spoof)（论文 VI-C 原文关系）
SCENARIO_MEANS = {
    1: lambda v, a: (2.0 * v, v),   # 场景1: Ha: μDop = 2μToF（静态攻击者伪造静态物）
    2: lambda v, a: (0.0, v),       # 场景2: Ha: μDop = 0, μToF ≠ 0（同速移动攻击者）
    3: lambda v, a: (v, 0.0),       # 场景3: Ha: μDop ≠ 0, μToF = 0（伪造近距随车目标）
}


def draw_samples(rng, n, road, attack=None, p=0.0, snr=1e-4, trials=1, k=None,
                 model="fractional"):
    """生成 {x_Dop}n、{x_ToF}n 二维样本，shape=(trials, n, 2)，维度 [v, a]。

    attack=None 生成 H0（无攻击）样本；否则按场景生成 Ha 样本。
    欺骗比例 p 的两种建模（README 假设 A4）：
      - "fractional"（默认，对应论文式(21)-(27)的功效分析机制）：
        所有样本 i.i.d.，均值 = (1-p)·合法均值 + p·欺骗均值，无混合方差。
        可同时复现论文 §VI-E/F 的两个锚点（n=50→F1 0.923；p=0.4→F1 0.97）。
      - "bernoulli"（物理忠实）：每个样本独立地以概率 p 为欺骗信号，
        引入混合方差 p(1-p)·v²，低 p 时所需样本量显著增大（对比实验用）。
    """
    v_rel, a_rel = relative_motion(road)
    sv_d, sa_d = doppler_noise_std(snr, k)
    sv_t = TOF_ERR_RATE * v_rel
    sa_t = TOF_ERR_RATE * a_rel
    legit_mean = np.array([v_rel, a_rel])

    if attack is None or p == 0.0:
        mean_d = mean_t = np.broadcast_to(legit_mean, (trials, n, 2))
    elif model == "fractional":
        mv_d, mv_t = SCENARIO_MEANS[attack](v_rel, a_rel)
        mu_d = (1 - p) * legit_mean + p * np.array([mv_d, a_rel])
        mu_t = (1 - p) * legit_mean + p * np.array([mv_t, a_rel])
        mean_d = np.broadcast_to(mu_d, (trials, n, 2))
        mean_t = np.broadcast_to(mu_t, (trials, n, 2))
    elif model == "bernoulli":
        mv_d, mv_t = SCENARIO_MEANS[attack](v_rel, a_rel)
        mu_d = np.array([mv_d, a_rel])
        mu_t = np.array([mv_t, a_rel])
        spoofs = rng.random((trials, n)) < p
        mean_d = np.where(spoofs[..., None], mu_d, legit_mean)
        mean_t = np.where(spoofs[..., None], mu_t, legit_mean)
    else:
        raise ValueError(f"unknown model: {model}")

    x_d = rng.normal(np.asarray(mean_d, dtype=float), [sv_d, sa_d])
    x_t = rng.normal(np.asarray(mean_t, dtype=float), [sv_t, sa_t])
    return x_d, x_t


def _cov_batch(x):
    """逐 trial 的样本协方差，x: (trials, n, dim) -> (trials, dim, dim)。"""
    xc = x - x.mean(axis=1, keepdims=True)
    return np.einsum("tni,tnj->tij", xc, xc) / (x.shape[1] - 1)


def hotelling_t2_batch(x_d, x_t, alpha=0.05):
    """式(18)(19)：Hotelling T² 检验（批量向量化）。

    复现说明（README 假设 A7）：论文式(18)印出的系数 [Spooled/n]⁻¹ 使统计量
    为标准 T² 的 2 倍，与其式(19)临界值（恰为标准两样本 Hotelling 的精确
    零分布 ((4n-4)/(2n-3))·F_{2,2n-3}）不匹配，直接使用会令检验尺寸膨胀到
    ~0.22。此处取标准形式：
        T² = (n/2)·d̄ᵀ·Spooled⁻¹·d̄，d̄ = x̄Dop - x̄ToF，
        Spooled = (S_D²+S_T²)/2（论文定义，协方差不等时仍渐近一致）。
    """
    n = x_d.shape[1]
    d_bar = x_d.mean(axis=1) - x_t.mean(axis=1)
    s_pooled = 0.5 * (_cov_batch(x_d) + _cov_batch(x_t))
    t2 = 0.5 * n * np.einsum("ti,tij,tj->t", d_bar, np.linalg.inv(s_pooled), d_bar)
    crit = (4 * n - 4) / (2 * n - 3) * stats.f.ppf(1 - alpha, 2, 2 * n - 3)
    return t2, t2 > crit


def t_test_batch(x_d, x_t, alpha=0.05):
    """式(17)：仅速度分量的两样本 t 检验（基线方法）。"""
    n = x_d.shape[1]
    v_d, v_t = x_d[..., 0], x_t[..., 0]
    m_diff = np.abs(v_d.mean(axis=1) - v_t.mean(axis=1))
    s1, s2 = v_d.std(axis=1, ddof=1), v_t.std(axis=1, ddof=1)
    s_pooled = np.sqrt((s1 ** 2 + s2 ** 2) / 2.0)
    t_stat = m_diff / (s_pooled * np.sqrt(2.0 / n))
    crit = stats.t.ppf(1 - alpha / 2, n - 1)
    return t_stat, t_stat > crit


TESTS = {"hotelling": hotelling_t2_batch, "ttest": t_test_batch}


def empirical_reject_rate(rng, n, road, attack, p, snr,
                          alpha=0.05, trials=2000, test="hotelling", k=None,
                          model="fractional"):
    """蒙特卡洛估计拒绝率：attack=None 时即第一类错误（经验 α），否则即功效。

    大 n 时按内存预算自适应分块（每块 ≤ ~128MB 的样本数组）。
    """
    test_fn = TESTS[test]
    # 每 trial 样本元素数 ≈ n×2维×2组；预算 1.6e7 个 float64 (~128MB)
    chunk = int(np.clip(4_000_000 // max(n, 1), 64, 4096))
    rejected = 0
    done = 0
    while done < trials:
        m = min(chunk, trials - done)
        x_d, x_t = draw_samples(rng, n, road, attack, p, snr, trials=m, k=k,
                                model=model)
        rejected += int(test_fn(x_d, x_t, alpha)[1].sum())
        done += m
    return rejected / done


def f1_score(alpha: float, beta: float) -> float:
    """由 (α, β) 计算 F1（假设正负类均衡，与论文 §VI-E 的 0.923 对应）。"""
    return 2.0 * (1.0 - beta) / (2.0 * (1.0 - beta) + alpha + beta)
