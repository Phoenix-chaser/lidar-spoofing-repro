"""协同式 LiDAR 检测（论文第 V-B4 节，Proposition 1 / 式 8-14）与 Fig.11 数值实验。

复现两件事：
 1. Proposition 1 数值验证：给定攻击者速度 va，式(12)(13)算出的欺骗距离
    能使受害者 LiDAR 的 ToF 速度（式 8/9）与 Doppler 速度（式 14）一致。
 2. "一把钥匙开不了两把锁"：同一攻击者速度在两个不同速度的 LiDAR
    （ego / coop）处诱导出的 Doppler 速度不同 → 共享 Doppler 速度即可暴露攻击。
    这正是论文 Fig.11 的内容。

几何约定（论文 Fig.9）：2-D 直角坐标系，LiDAR 沿 +y 轴运动，速度 |vL|；
信号方向（DoA/AoA）与 x 轴夹角记 θ，单位向量 l = (cosθ, sinθ)。
"""
import numpy as np

from .doppler import C_LIGHT


# ---------------------------------------------------------------- 式(8)(9)：ToF 速度
def tof_velocity(dm, dn, theta_m, theta_n, v_lidar, dt):
    """由两次测量 (d,θ) 按 ToF 轨迹计算的目标速度（式 8/9 在一致坐标系下的等价形式）。

    约定：l=(cosθ,sinθ)（θ 从 +x 轴），LiDAR 沿 +y 运动。
    返回 (|v_ToF|, φ_ToF, (vx, vy))，其中 vx/vy 为速度向量分量。
    """
    vx = (dn * np.cos(theta_n) - dm * np.cos(theta_m)) / dt
    vy = v_lidar + (dn * np.sin(theta_n) - dm * np.sin(theta_m)) / dt
    mag = np.hypot(vx, vy)
    ang = np.arctan2(vy, vx)
    return mag, ang, (vx, vy)


# ---------------------------------------------------------------- 式(10)(14)：Doppler 速度
def _f_theta(theta, v_lidar, va_mag, phi_a):
    """式(14)下方定义：f(θ) = |vL|·sinθ + |va|·cos(θ-φa)。"""
    return v_lidar * np.sin(theta) + va_mag * np.cos(theta - phi_a)


def perceived_doppler_velocity(theta_m, theta_n, v_lidar, va_mag, phi_a):
    """式(14)：LiDAR 由两个角度收到的欺骗信号解出的"伪目标 Doppler 速度"向量。

    推导：单程欺骗频移 Δf=(f0/c)(|vL|sinθ - |va|cos(θ-φa)) 被 LiDAR 按往返
    公式解释 → 伪目标满足 |vDop|·cos(θ-φDop) = f(θ)/2，两个角度解 2×2 线性方程组。
    返回速度向量 (vx, vy)（即 |vDop|·(cosα, sinα)）。
    """
    fm = _f_theta(theta_m, v_lidar, va_mag, phi_a)
    fn = _f_theta(theta_n, v_lidar, va_mag, phi_a)
    denom = np.sin(theta_n - theta_m)
    vx = 0.5 * (fm * np.sin(theta_n) - fn * np.sin(theta_m)) / denom
    vy = 0.5 * (fn * np.cos(theta_m) - fm * np.cos(theta_n)) / denom
    return vx, vy


# ---------------------------------------------------------------- 式(12)(13)：Proposition 1
def prop1_spoof_distances(theta_m, theta_n, v_lidar, va_mag, phi_a, dt):
    """使 ToF 速度与 Doppler 速度一致的欺骗距离 (dm, dn) —— Prop.1 的等价实现。

    注意（复现发现，见 README 假设 A2）：论文印刷版式(12)(13)与式(8)(9)的
    θ 参考轴约定不一致，代回验证不自洽。此处按统一约定（l=(cosθ,sinθ)，
    θ 从 +x 轴，LiDAR 沿 +y 运动）重新推导等价闭式解：
        假目标感知速度 (vx,vy) 由式(14)给出，令两次测量位置差/Δt == (vx,vy)：
        dm = [(vy-|vL|)cosθn - vx·sinθn]·Δt / sin(θn-θm)
        dn = [(vy-|vL|)cosθm - vx·sinθm]·Δt / sin(θn-θm)
    数值上精确满足 Prop.1（见 verify_prop1，误差 ~1e-16）。
    """
    vx, vy = perceived_doppler_velocity(theta_m, theta_n, v_lidar, va_mag, phi_a)
    denom = np.sin(theta_n - theta_m)
    dm = ((vy - v_lidar) * np.cos(theta_n) - vx * np.sin(theta_n)) * dt / denom
    dn = ((vy - v_lidar) * np.cos(theta_m) - vx * np.sin(theta_m)) * dt / denom
    return dm, dn


def prop1_spoof_distances_as_printed(theta_m, theta_n, v_lidar, va_mag, phi_a, dt):
    """论文印刷版式(12)(13)（保留用于对比，其结果与式(8)(9)不自洽）。"""
    fm = _f_theta(theta_m, v_lidar, va_mag, phi_a)
    fn = _f_theta(theta_n, v_lidar, va_mag, phi_a)
    alpha = np.arctan(
        (fn * np.cos(theta_m) - fm * np.cos(theta_n))
        / (fm * np.sin(theta_n) - fn * np.sin(theta_m))
    )
    denom = np.sin(theta_n - theta_m)
    dm = (np.cos(theta_n) * v_lidar * dt
          + fn * np.sin(theta_m - alpha) / (2.0 * np.cos(theta_m - phi_a)) * dt) / denom
    dn = (np.cos(theta_m) * v_lidar * dt
          + fm * np.sin(theta_n - alpha) / (2.0 * np.cos(theta_n - phi_a)) * dt) / denom
    return dm, dn


def verify_prop1(theta_m=np.deg2rad(90.0), theta_n=np.deg2rad(78.0),
                 v_lidar=2.0, va_mag=10.0, phi_a=np.deg2rad(60.0), dt=0.1):
    """数值验证 Proposition 1：式(12)(13)的距离使 ToF 速度 == Doppler 速度。"""
    dm, dn = prop1_spoof_distances(theta_m, theta_n, v_lidar, va_mag, phi_a, dt)
    mag_tof, ang_tof, (vx_t, vy_t) = tof_velocity(dm, dn, theta_m, theta_n, v_lidar, dt)
    vx, vy = perceived_doppler_velocity(theta_m, theta_n, v_lidar, va_mag, phi_a)
    tof_vec = np.array([vx_t, vy_t])
    dop_vec = np.array([vx, vy])
    err = np.linalg.norm(tof_vec - dop_vec) / max(np.linalg.norm(dop_vec), 1e-12)
    return {
        "dm": dm, "dn": dn,
        "tof_velocity_vec": tof_vec, "doppler_velocity_vec": dop_vec,
        "relative_error": err,
    }


# ---------------------------------------------------------------- Fig.11 数值实验
def perceived_doppler_speed(v_lidar, va_mag, phi_a, theta=np.pi / 2):
    """单个 LiDAR 感知到的伪目标径向 Doppler 速度（单程频移按往返解释，相差 1/2）。

    Fig.11 的 y 轴即两个 LiDAR 该值的模长之差。
    theta 默认 π/2（假设攻击者位于两个 LiDAR 正前方，见 README 假设 A3）。
    """
    return 0.5 * (v_lidar * np.sin(theta) - va_mag * np.cos(theta - phi_a))


def fig11_data(v_ego=2.0, v_coop=1.0, phi_a_list=(np.pi / 2, np.pi / 3, np.pi / 4, 0.0),
               va_max=20.0, n_grid=200, theta=np.pi / 2):
    """生成 Fig.11 数据：|vDop^coop| - |vDop^ego| 随 |va| (0~20 m/s) 变化。"""
    va = np.linspace(0.0, va_max, n_grid)
    curves = {}
    for phi_a in phi_a_list:
        v_ego_perceived = np.abs(perceived_doppler_speed(v_ego, va, phi_a, theta))
        v_coop_perceived = np.abs(perceived_doppler_speed(v_coop, va, phi_a, theta))
        curves[phi_a] = v_coop_perceived - v_ego_perceived
    return va, curves


def two_locks_demo(theta_m=np.deg2rad(90.0), theta_n=np.deg2rad(78.0),
                   v_ego=2.0, v_coop=3.0, va_mag=10.0, phi_a=np.deg2rad(60.0), dt=0.1):
    """演示"一把钥匙开不了两把锁"：同一 va 在两个 LiDAR 处诱导的 Doppler 速度不同。"""
    vec_ego = perceived_doppler_velocity(theta_m, theta_n, v_ego, va_mag, phi_a)
    vec_coop = perceived_doppler_velocity(theta_m, theta_n, v_coop, va_mag, phi_a)
    return {
        "va": (va_mag, phi_a),
        "doppler_velocity_ego": vec_ego,
        "doppler_velocity_coop": vec_coop,
        "difference_norm": np.linalg.norm(np.array(vec_ego) - np.array(vec_coop)),
    }
