"""干涉测速 testbed 仿真 —— 论文 §IV-B（Fig.6/7）的纯软件复现。

论文用 ThorLabs 光学干涉 testbed（635nm 激光、分束器、固定镜 M0、电机滑轨
上的动镜 M1、OPT101 光电接收器）证明"可从激光信号提取多普勒频移"。其
信号模型论文已完整给出（§IV-B1）：

    本振束   YLO = ALO·e^{-j(2πf0·t + φLO)}
    调制束   YM  = AM ·e^{-j(2π(f0±Δf)·t + φM)}，  Δf = (2v/c)·f0 = 2v/λ
    光电探测器（低通滤除光学载频后）：
            Pout = AM²/2 + ALO²/2 + AM·ALO·cos(2πΔf·t + φM − φLO) + 噪声

即输出为频率 Δf 的拍频信号；FFT 取最高能量峰 → Δf → v̂ = Δf·λ/2。

本模块：
  1. verify_full_field_mixing(): 用玩具载频数值验证上述 Pout 公式（全场混频+低通）
  2. photodiode_output(): 按公式生成拍频信号（含噪声与速度抖动）
  3. extract_doppler_fft(): FFT 提取 Δf（滤直流、抛物线亚_bin插值、最高峰规则）
  4. run_fig7(): 复现论文 Fig.7(a)(b) 两个案例与数值对照
"""
import numpy as np

from .doppler import C_LIGHT

LASER_WAVELENGTH = 635e-9          # 论文 ThorLabs PL202：635 nm
F0 = C_LIGHT / LASER_WAVELENGTH    # 光学载频 ≈ 4.72e14 Hz


# ---------------------------------------------------------------- 公式数值验证
def verify_full_field_mixing(f_toy=2e6, delta_f=23622.0, fs=16e6,
                             duration=1e-3, seed=0):
    """玩具载频下的全场混频验证：|YLO+YM|² 低通后 == 论文 Pout 公式。

    真实 f0≈4.7e14 Hz 无法采样，但混频+低通的数学与载频无关，
    用 2 MHz 玩具载频即可精确验证论文 §IV-B1 的推导。
    """
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, duration, 1.0 / fs)
    phi_lo, phi_m = rng.uniform(0, 2 * np.pi, 2)
    a_lo, a_m = 1.0, 0.8
    y_lo = a_lo * np.exp(1j * (2 * np.pi * f_toy * t + phi_lo))
    y_m = a_m * np.exp(1j * (2 * np.pi * (f_toy + delta_f) * t + phi_m))
    full_field_power = np.abs(y_lo + y_m) ** 2
    # 数字低通：多拍点滑动平均，滤除 2f_toy 与 (2f_toy+Δf) 分量
    k = int(fs / f_toy) * 4
    kernel = np.ones(k) / k
    lpf = np.convolve(full_field_power, kernel, mode="same")
    # |E|² 低通后 = A_LO²+A_M² + 2·A_LO·A_M·cos(2πΔf·t + φM−φLO)
    # （论文 Pout 为其一半，属光电探测器响应系数约定，频率结构完全一致）
    analytic = (a_lo ** 2 + a_m ** 2) + 2 * a_lo * a_m * np.cos(
        2 * np.pi * delta_f * t + phi_m - phi_lo)
    edge = slice(2 * k, len(t) - 2 * k)          # 跳过卷积边缘
    err = np.max(np.abs(lpf[edge] - analytic[edge])) / np.max(np.abs(analytic))
    return {"max_relative_error": float(err),
            "note": "论文 Pout 与 |E|² 低通结果仅差全局 1/2 幅度系数"}


# ---------------------------------------------------------------- 信号生成与提取
def photodiode_output(t, v_of_t, a_lo=1.0, a_m=0.8, wavelength=LASER_WAVELENGTH,
                      snr_db=30.0, seed=None):
    """按论文 Pout 公式生成光电探测器输出（基带拍频 + 噪声）。

    v_of_t: 镜面速度（m/s），可为数组（时变）或标量；
    时变速度用相位积分 2π·(2/λ)·∫v dt 保证瞬时频率=(2/λ)v(t)。
    """
    rng = np.random.default_rng(seed)
    v = np.broadcast_to(np.asarray(v_of_t, float), t.shape)
    phase = 2 * np.pi * (2.0 / wavelength) * np.cumsum(v) * (t[1] - t[0])
    beat = a_lo * a_m * np.cos(phase + 0.3)
    dc = (a_lo ** 2 + a_m ** 2) / 2
    sig_power = np.mean(beat ** 2)
    noise_std = np.sqrt(sig_power / (10 ** (snr_db / 10.0)))
    return dc + beat + rng.normal(0.0, noise_std, len(t))


def extract_doppler_fft(signal, fs, f_min=2e3, f_max=200e3):
    """FFT 提取多普勒频移：去直流 → |FFT|² → 限定频带内取最高峰 → 抛物线插值。"""
    spec = np.abs(np.fft.rfft(signal - signal.mean())) ** 2
    freqs = np.fft.rfftfreq(len(signal), 1.0 / fs)
    band = (freqs >= f_min) & (freqs <= f_max)
    idx = np.argmax(spec * band)
    # 抛物线亚 bin 插值
    if 0 < idx < len(spec) - 1:
        a, b, c = spec[idx - 1], spec[idx], spec[idx + 1]
        denom = a - 2 * b + c
        shift = 0.5 * (a - c) / denom if abs(denom) > 0 else 0.0
    else:
        shift = 0.0
    df = freqs[1] - freqs[0]
    return (idx + shift) * df, spec, freqs


def velocity_from_doppler(delta_f, wavelength=LASER_WAVELENGTH):
    """v̂ = Δf·λ/2（往返多普勒）。"""
    return delta_f * wavelength / 2.0


# ---------------------------------------------------------------- Fig.7 复现
def run_fig7(fs=400e3, duration=0.25, snr_db=30.0, seed=7):
    """复现论文 Fig.7 两案例并做数值对照。

    返回 dict：
      case_a: v=0.75 cm/s（干净镜面运动）→ 单峰
      case_b: v̄=1.55 cm/s，叠加低速段（论文图 b 出现双峰、取最高能量峰）
      paper_check: 由论文实测 Δf 反推 v̂，量化其 ~3% 速度误差声明
    """
    t = np.arange(0.0, duration, 1.0 / fs)
    rng = np.random.default_rng(seed)

    # ---- Fig.7(a)：v = 0.75 cm/s
    v_a = 0.75e-2
    sig_a = photodiode_output(t, v_a, snr_db=snr_db, seed=rng.integers(1e9))
    df_a, spec_a, freqs = extract_doppler_fft(sig_a, fs)
    vhat_a = velocity_from_doppler(df_a)

    # ---- Fig.7(b)：标称 v̄ = 1.55 cm/s；前 60% 时间 v̄，后 40% 时间较低速
    #      （对应论文"随机噪声与目标微动造成多峰，取最高能量峰"）
    v_b_bar = 1.55e-2
    v_b = np.where(t < 0.6 * duration, v_b_bar, 1.10e-2)
    sig_b = photodiode_output(t, v_b, snr_db=snr_db, seed=rng.integers(1e9))
    df_b, spec_b, _ = extract_doppler_fft(sig_b, fs)
    vhat_b = velocity_from_doppler(df_b)

    # ---- 论文数值反推：Δf_paper → v̂，验证其 "~3% 速度检测误差"
    paper = [
        # (论文 Fig.7 标注的 Δf kHz, 论文标称速度 cm/s)
        (24.10e3, 0.75e-2),
        (48.72e3, 1.55e-2),
    ]
    paper_check = []
    for df_p, v_p in paper:
        v_hat = velocity_from_doppler(df_p)
        paper_check.append({
            "paper_delta_f_hz": df_p, "paper_v": v_p,
            "implied_v": v_hat,
            "rel_err_vs_stated": abs(v_hat - v_p) / v_p,
            "theory_delta_f_hz": 2.0 * v_p / LASER_WAVELENGTH,
        })

    return {
        "case_a": {"v_true": v_a, "delta_f": df_a, "v_hat": vhat_a,
                   "err": abs(vhat_a - v_a) / v_a, "spec": spec_a, "freqs": freqs},
        "case_b": {"v_true": v_b_bar, "delta_f": df_b, "v_hat": vhat_b,
                   "err": abs(vhat_b - v_b_bar) / v_b_bar, "spec": spec_b,
                   "freqs": freqs},
        "paper_check": paper_check,
    }


def mc_error_stats(n_trials=200, v_true=1.55e-2, jitter_frac=0.02,
                   fs=400e3, duration=0.25, snr_db=30.0, seed=11):
    """蒙特卡洛：速度估计误差统计（含镜面速度抖动 + 噪声），对应论文 ~3% 声明。"""
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, duration, 1.0 / fs)
    errs = []
    for _ in range(n_trials):
        v = v_true * (1.0 + rng.normal(0.0, jitter_frac))
        sig = photodiode_output(t, v, snr_db=snr_db, seed=rng.integers(1e9))
        df, _, _ = extract_doppler_fft(sig, fs)
        errs.append((velocity_from_doppler(df) - v_true) / v_true)
    errs = np.array(errs)
    return {"mean_abs_err": float(np.mean(np.abs(errs))),
            "p95_abs_err": float(np.percentile(np.abs(errs), 95)),
            "std": float(errs.std())}
