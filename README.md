# LiDAR Spoofing Detection — Software Reproduction

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![numpy](https://img.shields.io/badge/numpy-%E2%89%A51.24-orange) ![scipy](https://img.shields.io/badge/scipy-%E2%89%A51.10-orange) ![status](https://img.shields.io/badge/reproduction-complete-brightgreen) ![deterministic](https://img.shields.io/badge/runs-deterministic-informational) ![license](https://img.shields.io/badge/license-MIT-green)

> **Paper**: Xueyang Hu, Tian Liu, Tao Shu, Diep N. Nguyen, *"Spoofing Detection for LiDAR in
> Autonomous Vehicles: A Physical-Layer Approach"*, **IEEE Internet of Things Journal**,
> Vol. 11, No. 11, pp. 20673–20689, June 2024. DOI: [10.1109/JIOT.2024.3371378](https://doi.org/10.1109/JIOT.2024.3371378)

**English summary** — This repository reproduces, in pure Python, every software-reproducible
result of the paper — including both of its hardware experiments, each replaced by an
equivalent simulation: (i) the Doppler-shift models (Eq. 3–6, 15); (ii) Proposition 1 (verified
to machine precision under a consistent coordinate convention); (iii) the cooperative-LiDAR
experiment (Fig. 11); (iv) the Hotelling T²/t-test detection framework (Eq. 17–19) and power
analysis (Figs. 13–14) with both reported F1 anchors (0.923 / 0.97) matched; (v) a closed-loop
2-D LiDAR simulation reproducing the spoofing-attack demo (Fig. 3/4) — attack scenarios 1 and 3
are detected, a co-speed abeam fake is missed exactly as the paper's own limitation predicts;
(vi) a DSP simulation of the interferometer testbed (Fig. 6/7) matching its measured Doppler
shifts. Monte-Carlo results are cross-validated against closed-form noncentral-F power (max
deviation 0.007). Four internal inconsistencies found in the paper's printed equations are
documented below (F1–F4). The paper has no official code; its authors state the main detection
results are computer-simulation based (§VII-B), so this reproduction is faithful in methodology.
中文说明见下文。

---

## 复现范围

| ✅ 已复现（全部软件） | 对应论文内容 |
|---|---|
| 多普勒频移模型（式 3–6、15） | 核心物理：合法 2× / 欺骗 1× |
| Proposition 1 数值验证（式 8–14） | 协同检测的理论基础 |
| Fig.11 协同式检测数值实验 | 攻击模型 2 检测 |
| t 检验 / Hotelling T²（式 17–19） + 功效分析 Fig.13/14、F1 锚点 | §VI 统计检测框架 |
| 非中心 F 解析功效交叉验证（新增） | 独立复核 |
| **攻击注入→检测滤除闭环仿真** | Fig. 3/4 实机攻击演示的软件等效（含论文攻击场景 1/3 与自述局限 1） |
| **干涉测速 testbed 仿真** | Fig. 6/7 的纯 DSP 复现（论文 §IV-B 信号模型，定量对齐其数值） |

论文两个硬件实验均已用软件等效覆盖；仅"实物本身"（商用 LiDAR 真被骗、真实光路）天然需要硬件。
论文作者在 §VII-B 自述其"主要性能评估为计算机仿真"，因此本复现与论文验证方法一致。

## 硬件实验 ↔ 软件模拟对照图

每个硬件器件对应的软件模块、等效层级（公式级 = 直接实现论文公式并验证；模型级 = 简化物理建模；算法级 = 相同数据处理）以及未模拟项（红框）：

面板 A —— 干涉 testbed（Fig.6/7）的映射：

![HW-SW mapping: interferometer](figures/fig_map_interferometer.png?v=7)

面板 B —— 实机攻击演示（Fig.2/3/4）的映射：

![HW-SW mapping: attack demo](figures/fig_map_attack.png?v=7)

**仿真硬件原理图**（虚拟器件 + 每个器件框内直接标注实现公式/函数）。拆为三张单图便于阅读；
组合版 `figures/fig_virtual_testbed.png`、`figures/fig_hw_mapping.png` 适合放进汇报 PPT：

① 虚拟干涉 testbed 器件链（框内 = 实现公式）：

![Virtual interferometer](figures/fig_virtual_interferometer.png?v=7)

② 虚拟攻击场景（`scan()` 第 0 帧真实渲染：光束、点云、攻击器与三类假目标）：

![Virtual attack scene](figures/fig_virtual_scene.png?v=7)

③ 虚拟器件实现方式（LiDAR / 攻击器 / Doppler 信道 / 跟踪+检测）：

![Virtual device implementations](figures/fig_virtual_impl.png?v=7)

器件级明细：

| 论文硬件（器件） | 软件对应 | 等效层级 |
|---|---|---|
| **干涉 testbed（Fig.6）** | `src/interferometer.py` | |
| 激光管 PL202（635nm） | `F0 = c/λ` 常量 | 参数级 |
| 分束器 + 固定镜 M0 + 动镜 M1（电机滑轨） | `photodiode_output()`：相位积分 2π(2/λ)∫v dt | 公式级（全场混频数值验证，残差 2.9e-3） |
| 光电接收器 OPT101 | Pout 拍频公式 + 噪声（SNR 可配） | 公式级 |
| 示波器 + FFT | `extract_doppler_fft()`（FFT + 最高能量峰 + 抛物线插值） | 算法级（与论文相同处理） |
| **实机攻击演示（Fig.2/3）** | `src/simulator.py` | |
| 受害 LiDAR YD X2L | `scan()`：360° 光线投射（1° 分辨率、测距噪声 3cm） | 模型级 |
| 攻击器三件套（光电二极管同步 + 延时 τspoof + 激光管，<60 美元） | 式(2)注入：t_a = t_s + τspoof，先到先得替换真实回波 | 公式级 |
| 激光传播的多普勒物理 | 式(5)(6)合成：合法 2v/c、欺骗 v/c + 式(28)噪声（K 锚点校准） | 公式级 |
| LiDAR 目标跟踪 | 锚点跟踪（v_Dop, v_ToF）逐目标配对 | 模型级 |
| 检测（论文未在实机演示） | T² 检测器闭环判决+滤除 | 软件新增（超出论文实机范围） |
| **未模拟项** | — | 真实光子传播、探测器电路、商用 LiDAR 固件（首达判定近似为"先到先得"）、环境杂散 |

## 快速开始

```bash
python3 run_all.py           # 完整精度，约 2–3 分钟，12 个步骤全部输出
python3 run_all.py --quick   # 快速冒烟，约 40 秒
```

依赖：`numpy`、`scipy`、`matplotlib`。固定随机种子，**两次运行结果逐行一致**（已验证）。

## 复现结果

### 1. Fig.11 — 协同式 LiDAR 检测（"一把钥匙开不了两把锁"）

同一攻击者速度在两个速度不同的 LiDAR 处诱导出不同的 Doppler 速度；当两 LiDAR 速度相同（子图 d）
时差恒为 0——与论文结论一致：协同检测要求参与 LiDAR 速度不同。

![Fig.11 reproduction](figures/fig11.png?v=7)

### 2. Fig.13 — 最小样本量 vs 欺骗比例（SNR=1e-4）

欺骗比例 p 越小，所需样本量越大，**p < 0.4 后急剧上升**（city：p=0.1 需 50 个样本，
p≥0.6 仅需 4 个）——复现论文正文对该图的关键描述。

![Fig.13 reproduction](figures/fig13.png?v=7)

### 3. Fig.14 — 最小样本量 vs SNR（p=0.1，log-log）

SNR 每降一个数量级，所需样本量约 ×10（city：51 → 477 → 4634），近似 n ∝ 1/SNR。

![Fig.14 reproduction](figures/fig14.png?v=7)

### 4. 与论文数值对照

| 项目 | 论文 | 本复现 | 状态 |
|---|---|---|---|
| 合法/欺骗多普勒频移比（式 5/6） | ≈2 | 2.0000 | ✅ |
| Proposition 1（ToF 速度 = Doppler 速度） | 成立 | 误差 1.5e-16 | ✅ |
| Fig.11：速度相同→不可检；不同→可检 | 成立 | (d) 全零；(a)–(c) 非零 | ✅ |
| F1 公式（α=0.05, β=0.1） | 0.923 | 0.9231 | ✅ |
| 最差条件所需样本量（场景1, city, p=0.1, SNR=1e-4） | 50 | **50** | ✅（校准锚点） |
| n=50 最差条件功效 → F1 | 0.923 | 0.902 → 0.924 | ✅ |
| p=0.4, SNR=1e-4, n=50 → F1 | 0.97 | 0.976 | ✅ |
| Fig.13 趋势（p↓→n↑，p<0.4 尤甚） | 成立 | city: 50/15/8/6/5/4 | ✅ |
| Fig.14 趋势（SNR↓→n↑） | 成立 | city: 51/477/4634 | ✅ |
| H0 经验显著性水平 | α=0.05 | 0.0485–0.0493 | ✅ |
| **解析功效 vs 蒙特卡洛（独立交叉验证）** | — | 最大偏差 0.007（MC 误差内） | ✅ 新增 |
| **闭环：合法目标不误报 / 协同欺骗检出** | — | 5 合法全过、场景 1/3 假目标全检出；侧方同速假目标漏检（= 论文自述局限 1） | ✅ 新增 |
| **干涉 testbed：Fig.7 数值** | 24.10 / 48.72 kHz，误差~3% | 23.62（理论）/ 48.82 kHz；MC 误差 p95 3.7% | ✅ 新增 |

完整数值见 `results/run_full.log`、`results/anchors.txt`、`results/analytic_check.csv`。

### 5. 闭环仿真（新增）—— 攻击注入 → 检测滤除

自写 2-D LiDAR 仿真器把论文 Fig.3/4 的实机攻击演示转为软件闭环：360° 扫描生成合法点云
→ 按式(2)注入欺骗点（ToF 欺骗，"先到先得"）→ 按式(5)(6)逐点合成 Doppler（合法 2× / 欺骗 1×，
噪声用式(28)校准模型）→ 目标级跟踪配对 (v_Dop, v_ToF) → 用式(18)(19)的 T² 检测器逐目标判决
→ 滤除被判欺骗的轨迹。左图为攻击中点云（红色 × 为注入的假点），右图为检测滤除后：

![Closed-loop simulation](figures/fig_closed_loop.png?v=7)

判决结果（多随机种子稳定）：

| 目标 | 类型 | T² | 判决 | 结果 |
|---|---|---|---|---|
| front/left/right wall、pillar（静止合法） | 合法 | 0–4.4 | 合法 | ✅ 不误报 |
| bike（横穿自行车，动态合法） | 合法 | 0.1 | 合法 | ✅ 动态目标不误报 |
| fake_static（场景 1：静态假墙） | 欺骗 | 546–1358 | 欺骗 | ✅ 检出 |
| fake_ahead（场景 3：正前方恒距假车） | 欺骗 | 48–64 | 欺骗 | ✅ 检出 |
| fake_beside（正侧方同速假目标） | 欺骗 | 0.5–2.8 | 合法 | ⚠️ 漏检 = 论文 §VII-D 局限 1 的如实复现 |

闭环实现中的两个关键建模点（都有论文依据）：
- **短窗口检验**：T² 取每个目标前 20 个样本的"接近段"，对应论文 §VII-D-2 的匀速假设；
  若用整条通过轨迹（相对速度从 +11 扫到 −11 m/s），共同的轨迹方差会把 2:1 失配稀释掉
  （实测 T² 从数百降到 ≈5）——均值一致性检验本质上是短时局部检验。
- **目标级跟踪**：ToF 与 Doppler 必须对准同一目标点（论文式 8/9 的跟踪思想）；固定波束角
  扫过无限长墙面时命中点沿墙滑动，会让两个估计量失配产生假象。

### 6. 干涉测速 testbed 仿真（新增）—— 论文 Fig. 6/7 的纯 DSP 复现

论文用 ThorLabs 光学干涉 testbed 证明"能从激光信号提取多普勒频移"。其信号模型
（§IV-B1 的 YLO/YM/Pout 公式）已完整给出，故无需硬件即可定量复现：

![Interferometer simulation](figures/fig_interferometer.png?v=7)

| 项目 | 论文 | 本仿真 | 状态 |
|---|---|---|---|
| Pout 拍频公式（全场混频+低通数值验证） | §IV-B1 | 残差 2.9e-3（=低通滤波器通带下垂） | ✅ |
| Fig.7(a)：v=0.75 cm/s 的 Δf | 24.10 kHz | 23.62 kHz（=理论值 2v/λ） | ✅ |
| Fig.7(b)：v̄=1.55 cm/s，双峰取最高 | 48.72 kHz | 48.82 kHz（理论 48.82） | ✅ |
| 速度估计误差 | "约 3%" | MC（2% 抖动+30dB 噪声）：均值 1.5%，p95 3.7% | ✅ |

数值差异的量化解释：由论文实测 Δf 反推 v̂=Δf·λ/2 得 0.765 / 1.547 cm/s，与其标称
0.75 / 1.55 偏差 2.0% / 0.2%——即论文 Fig.7(a) 的 24.10 kHz（理论 23.62）来自其
电机滑轨速度标定误差，而非模型偏差。

## 唯一自由参数：噪声幅度 K

论文式(28)的 MLE 方差常数印制不全（见 A3）。本复现以论文自己的锚点
（最差条件 n=50 达功效 0.9）校准总幅度，得 **K = 47.75**（二分校准 + 解析估计 ≈49 相互印证）。
校准后论文的两个 F1 锚点**同时命中**，且 Fig.13/14 曲线形状（对 p、SNR 的依赖）不依赖 K 的具体取值。
重新校准：`python3 -c "from src import power_analysis as pa; import numpy as np; print(pa.calibrate_noise_scale(np.random.default_rng(7)))"`

## 代码 ↔ 论文对照

| 代码 | 论文内容 |
|---|---|
| `src/doppler.py` | 式(3)–(6) 合法（往返，2×）/欺骗（单程）多普勒频移；式(15) 攻击模型 3 发射频率；自检脚本 |
| `src/cooperative.py` | 式(8)(9) ToF 速度；式(10)(14) Doppler 速度；式(12)(13) Prop.1 欺骗距离（修正版 + 原文版并存）；Fig.11 数据 |
| `src/detection.py` | 式(17) t 检验；式(18)(19) Hotelling T²（系数修正，见 F2）；§VI-D 样本生成设置；式(28) 噪声模型 |
| `src/power_analysis.py` | 最小样本量搜索；Fig.13/14；F1 锚点；K 校准；**非中心 F 解析功效**（交叉验证） |
| `src/simulator.py` | **闭环仿真**：2-D LiDAR 光线投射 + 式(2)攻击注入 + 式(5)(6)Doppler 合成 + 目标级跟踪 + T² 滤除（Fig.3/4 的软件模拟） |
| `src/interferometer.py` | **干涉 testbed 仿真**：§IV-B1 信号模型 + 全场混频验证 + FFT 提取 Δf + Fig.7 两案例复现（Fig.6/7 的软件模拟） |
| `run_all.py` | 一键复现 10 个步骤并出图 |

## 建模假设（论文未完全给出、需补全的部分）

- **A1 载频 f0**：论文未给，取 905 nm。只影响频移→速度换算演示，不影响检测统计。
- **A2 几何**：Fig.11 假设攻击者位于两协同 LiDAR 正前方（θ=90°）。论文未给出其具体 θ。
- **A3 式(28) 常数**：按印出形式实现（σv²∝3/(SNR·2π²N²)，σa²∝45/(SNR·2π²N⁴)），幅度 K 锚点校准（见上节）。
- **A4 欺骗比例模型**：默认 `fractional`（与论文式(21)–(27)的总体均值处理一致，δ=p·v_rel，无混合方差），可同时命中两个 F1 锚点；另实现 `bernoulli`（逐样本以概率 p 欺骗，物理忠实的间歇攻击），低 p 所需样本量显著更大（p=0.1 需 ≈145），说明论文该条件下偏乐观（见 F4）。
- **A5 加速度维度**：样本级模型中加速度均值在 H0/Ha 相同（仅作噪声维度）。论文"加速度展宽速度谱、仅靠速度不可靠"（§VI-B）是信号级现象，i.i.d. 高斯样本模型无法体现——因此当前模型中仅速度的 t 检验功效略高于 T²（0.948 vs 0.902），属模型简化的诚实结论，非对论文方法的否定。
- **A6 三攻击场景**：均值偏移模型下 \|δ\|=p·v_rel 对三场景相同，Fig.13/14 三场景曲线基本重合；场景间差异源自论文式(21)–(27)各自的非中心 F 结构，而该结构与正文矛盾（F3），无法从文本复原。
- **A7 T² 系数**：取标准两样本形式 (n/2)·d̄ᵀSp⁻¹d̄（见 F2）。

## 复现中发现的原文问题（可写入复现报告）

| # | 问题 | 证据与处理 |
|---|---|---|
| **F1** | 式(12)(13) 与式(8)(9) 坐标约定不一致 | 照原文代入验证：欺骗距离为负、Prop.1 不成立；统一坐标系（l=(cosθ,sinθ)）重推导后以 ~1e-16 成立。代码保留两版本可现场对比 |
| **F2** | 式(18) 统计量是标准 T² 的 2 倍 | 直接套用式(19)临界值 → 第一类错误实测 0.22；改标准形式后恢复 0.05。式(19)本身恰为标准零分布，印证式(18)系数笔误 |
| **F3** | 式(21)–(27) 与正文叙述矛盾 | 按其中心化推导，分离随 (1−p) 增大（p 越小越易检出），与正文/Fig.13 叙述相反；且式(21)自由度（5n−6）与二维统计量标准结果（2n−3）不符。复现采用与正文一致的模型 |
| **F4** | n=50 锚点在物理忠实模型下偏乐观 | 伯努利混合（间歇欺骗）下 p=0.1 需 ≈145 样本；论文隐含总体均值近似，未计混合方差 p(1−p)v² |

## 扩展方向

1. 序贯检验（SPRT）替代固定样本量检验——同错误率下更快检出；
2. 解析功效已实现（`analytic_power`），可进一步替代搜索得到精确最小 n；
3. Welch 校正 / bootstrap / 非参检验的稳健性对比（回应论文 §VII-D 自述局限）；
4. 接入真实欺骗点云（如 [LiDAR-Spoofing-Forensics-Datasets](https://github.com/Allenpandas/LiDAR-Spoofing-Forensics-Datasets)）做外部验证。

## 文件结构

```
lidar_spoofing_repro/
├── run_all.py              # 一键复现入口（10 步）
├── src/
│   ├── doppler.py          # 式(3)-(6)、(15)
│   ├── cooperative.py      # 式(8)-(14)、Prop.1、Fig.11
│   ├── detection.py        # 样本生成 + 式(17) + 式(18)(19)
│   ├── power_analysis.py   # Fig.13/14 + 锚点 + K 校准 + 解析验证
│   ├── simulator.py        # 闭环仿真（攻击注入 + 检测滤除）
│   └── interferometer.py   # 干涉 testbed 仿真（Fig.6/7）
├── figures/                # 复现图（fig11/13/14/closed_loop/interferometer）
└── results/                # CSV、锚点、交叉验证、完整日志
```
