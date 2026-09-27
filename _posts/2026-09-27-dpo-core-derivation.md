---
layout: post
title: DPO 的核心推导：从 KL 正则化目标到直接偏好优化
date: 2026-09-27
categories: [技术]
description: 把 DPO 从 RLHF 的 KL 正则化目标一步步推出来：闭式最优策略、奖励的对数比反解、Bradley–Terry 下配分函数相消，以及梯度为什么等于按误差加权的 pairwise SFT。
---

DPO（Direct Preference Optimization）的论文结论只有一个式子，看起来像是一个"拍出来的"损失函数：

$$\mathcal{L}_{\mathrm{DPO}}=-\,\mathbb{E}\left[\log\sigma\!\left(\beta\log\frac{\pi_{\theta}(y_w\mid x)}{\pi_{\mathrm{ref}}(y_w\mid x)}-\beta\log\frac{\pi_{\theta}(y_l\mid x)}{\pi_{\mathrm{ref}}(y_l\mid x)}\right)\right]$$

但它不是拍出来的。它是从「带 KL 约束的奖励最大化」出发，经过四步等价变形推出来的，而每一步都恰好消掉一个障碍：

| 步骤 | 操作 | 消掉的东西 |
| --- | --- | --- |
| 一 | 逐 prompt 对 KL 正则化目标求拉格朗日 | **RL** —— 最优策略有闭式解，不需要采样迭代 |
| 二 | 把奖励反解成策略与参考策略的对数比 | **独立的奖励模型** |
| 三 | 代入 Bradley–Terry，同 prompt 的常数相消 | **配分函数** $$Z(x)$$ |
| 四 | 在偏好数据上做极大似然 | 剩下的只有可计算的 log 概率 |

这篇文章把这四步完整推一遍，然后看梯度的形状，最后说清楚这套推导依赖什么假设、在哪里会失效。

## 一、设定与符号

| 符号 | 含义 |
| --- | --- |
| $$x$$ | 提示（prompt） |
| $$y$$ | 回答，是一个完整序列 $$y=(y_1,\dots,y_T)$$ |
| $$\mathcal{D}$$ | 数据分布（第三步之后是偏好数据集） |
| $$\pi_{\theta}$$ | 正在训练的策略，即语言模型本身 |
| $$\pi_{\mathrm{ref}}$$ | 参考策略，通常是 SFT 后的模型，**训练中冻结** |
| $$r(x,y)$$ | 奖励函数 |
| $$\beta>0$$ | KL 正则强度（它有两个身份，见第九节） |
| $$y_w,\ y_l$$ | 一对偏好中的胜者（winner）与败者（loser） |

约定：概率 $$\pi(y\mid x)=\prod_{t=1}^{T}\pi(y_t\mid x,y_{<t})$$ 是整条回答的概率，第 $$t$$ 个 token 的分布以提示和前文为条件。

## 二、起点：RLHF 要解的问题

RLHF 的第一阶段（SFT）之后，标准做法是解这样一个优化问题：

$$
\max_{\pi}\ \mathbb{E}_{x\sim\mathcal{D}}\left[\ \mathbb{E}_{y\sim\pi(\cdot\mid x)}\big[r(x,y)\big]-\beta\,\mathrm{KL}\big(\pi(\cdot\mid x)\,\big\|\,\pi_{\mathrm{ref}}(\cdot\mid x)\big)\right]
\tag{1}
$$

$$\mathrm{KL}$$ 项写成期望，整个目标可以合并成一个式子：

$$
\max_{\pi}\ \mathbb{E}_{x\sim\mathcal{D}}\ \mathbb{E}_{y\sim\pi(\cdot\mid x)}\left[\,r(x,y)-\beta\log\frac{\pi(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}\,\right]
\tag{2}
$$

这两项在拔河：第一项要高奖励，第二项不许偏离参考策略太远。两个极端先记住——当 $$\beta\to\infty$$ 时最优解就是 $$\pi_{\mathrm{ref}}$$ 本身；当 $$\beta\to 0$$ 时目标退化成纯奖励最大化，最优策略会塌缩到 $$\arg\max_y r(x,y)$$ 上。

(2) 是后面一切推导的起点。

## 三、第一步：最优策略有闭式解

注意 (2) 里对 $$\pi$$ 的依赖是**逐 prompt 解耦**的：$$x$$ 的分布不涉及 $$\pi$$，而 KL 项也是在每个 $$x$$ 上单独算的。所以可以把 $$x$$ 固定，问题变成在概率单纯形上最大化：

$$
\max_{\pi(\cdot\mid x)}\ \sum_{y}\pi(y\mid x)\left[\,r(x,y)-\beta\log\frac{\pi(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}\,\right]
\quad\text{s.t.}\quad\sum_{y}\pi(y\mid x)=1
\tag{3}
$$

### 为什么可以直接用拉格朗日

目标函数里 $$-\beta\sum_y \pi\log\pi$$ 是负熵，在单纯形上**严格凹**；剩下的是关于 $$\pi$$ 的线性项，不破坏凹性。约束集是凸的单纯形。凹目标 + 凸约束意味着 KKT 条件既必要又充分，驻点就是唯一的全局最优——所以下面这步不是启发式，是真解。

拉格朗日函数（$$\lambda$$ 是对每个 $$x$$ 单独取的乘子）：

$$
\mathcal{L}(\pi,\lambda)=\sum_{y}\pi(y\mid x)\left[r(x,y)-\beta\log\frac{\pi(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}\right]+\lambda\left(1-\sum_{y}\pi(y\mid x)\right)
\tag{4}
$$

对 $$\pi(y\mid x)$$ 求偏导。注意 $$\frac{\partial}{\partial\pi}\big[\pi\log\pi\big]=\log\pi+1$$，而 $$\log\pi_{\mathrm{ref}}(y\mid x)$$ 对 $$\pi$$ 是常数：

$$
\frac{\partial\mathcal{L}}{\partial\pi(y\mid x)}=r(x,y)-\beta\left(\log\frac{\pi(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}+1\right)-\lambda=0
\tag{5}
$$

解出对数比：

$$
\log\frac{\pi(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}=\frac{r(x,y)-\lambda}{\beta}-1
\tag{6}
$$

指数化回去：

$$
\pi(y\mid x)=\pi_{\mathrm{ref}}(y\mid x)\exp\!\left(\frac{r(x,y)}{\beta}\right)\cdot\underbrace{\exp\!\left(-1-\frac{\lambda}{\beta}\right)}_{\text{constant in }y}
\tag{7}
$$

### 那个常数是什么

(7) 里剩下的因子只跟 $$\lambda$$ 有关，而 $$\lambda$$ 是**为满足归一化约束而选的**——它对 $$y$$ 是常数。既然它不含 $$y$$，就由归一化条件定死：把所有 $$y$$ 的概率加起来等于 1，立刻得到

$$
\pi^{*}(y\mid x)=\frac{1}{Z(x)}\,\pi_{\mathrm{ref}}(y\mid x)\exp\!\left(\frac{r(x,y)}{\beta}\right),
\qquad
Z(x)=\sum_{y}\pi_{\mathrm{ref}}(y\mid x)\exp\!\left(\frac{r(x,y)}{\beta}\right)
\tag{8}
$$

代回去验证：$$\sum_y \pi^*(y\mid x)=\frac{1}{Z(x)}\sum_y\pi_{\mathrm{ref}}(y\mid x)e^{r/\beta}=1$$，成立。

### 读出三件事

**第一，这是玻尔兹曼分布。** (8) 就是「先验 $$\pi_{\mathrm{ref}}$$ 按 $$e^{r/\beta}$$ 重加权、再归一化」。$$\beta$$ 是温度：越小越尖锐，越靠近 $$\arg\max_y r$$；越大越平，越靠近 $$\pi_{\mathrm{ref}}$$。

**第二，出现了一个算不出来的量。** $$Z(x)=\sum_y \pi_{\mathrm{ref}}(y\mid x)e^{r(x,y)/\beta}$$ 要对**所有可能的回答**求和。语言模型的一个回答可能长达上千 token，序列空间是指数级的——这个和无法穷举、也无法采样估计得准。**这是第一个障碍，先记住它，第三步它会自己消失。**

**第三，这一步已经把 RL 消掉了。** PPO 那套流程之所以要迭代采样，是因为（它认为）最优策略没有闭式解。但对 (1) 这个特定目标，(8) 就是最优策略的解析表达式，只是它依赖未知的 $$r$$。第二步正是从这里切入的。

## 四、第二步：把奖励反解成策略的对数比

把 (8) 两边取对数、移项：

$$
r(x,y)=\beta\log\frac{\pi^{*}(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}+\beta\log Z(x)
\tag{9}
$$

这是整个 DPO 最关键的一次视角转换。它的读法是：

> **奖励不是独立于策略的另一个东西。给定最优策略，奖励可以被它反解出来。**

(9) 右边的第一项只涉及策略和参考策略，是**可计算**的；只有 $$\beta\log Z(x)$$ 不可计算。于是定义**隐式奖励**（implicit reward），也就是把 $$\beta\log Z(x)$$ 丢掉之后剩下的部分：

$$
\hat{r}_{\theta}(x,y)=\beta\log\frac{\pi_{\theta}(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}
\tag{10}
$$

**丢掉 $$\beta\log Z(x)$$ 不是近似，而是一次合法的规范化。** 原因是下面这个对称性。

### 规范对称性：奖励只在同一条 prompt 内可识别

考虑给奖励整体加上一个只依赖 $$x$$ 的函数 $$f(x)$$：

$$
r'(x,y)=r(x,y)+f(x)\quad\Longrightarrow\quad Z'(x)=e^{f(x)/\beta}Z(x)\quad\Longrightarrow\quad \pi^{*}\ \text{unchanged}
\tag{11}
$$

第一步：$$Z'(x)=\sum_y\pi_{\mathrm{ref}}e^{(r+f)/\beta}=e^{f(x)/\beta}Z(x)$$。第二步：代回 (8)，分子分母上的 $$e^{f(x)/\beta}$$ 约掉，$$\pi^{*}$$ 完全不变。同理，偏好概率 (12) 里也只会出现奖励差，同样不变。

所以：**奖励函数永远无法被唯一识别**，能识别的只有同一条 prompt 下不同回答之间的奖励差。$$\beta\log Z(x)$$ 恰好就是一个 $$x$$ 的函数，它落在"不可识别"的那一部分里——丢掉它，信息没有任何损失。这在物理里叫规范自由度，在统计里叫位置参数不可识别，说的是同一件事。

## 五、第三步：代入 Bradley–Terry，配分函数相消

到这一步我们有了一个可计算的奖励 (10)，但还没有把它和**我们能拿到的数据**（人类偏好）连起来。桥梁是 Bradley–Terry（BT）模型：

$$
\Pr(y_w\succ y_l\mid x)=\sigma\big(r(x,y_w)-r(x,y_l)\big),
\qquad
\sigma(z)=\frac{1}{1+e^{-z}}
\tag{12}
$$

BT 的来源很短：假设人类对某个回答的"感知奖励"是 $$\hat r(x,y)=r(x,y)+\epsilon$$，$$\epsilon$$ 是独立同分布的 logistic 噪声，那么

$$
\Pr\big(\hat r(x,y_w)>\hat r(x,y_l)\big)=\Pr\big(\epsilon_l-\epsilon_w<r_w-r_l\big)=\sigma(r_w-r_l)
$$

也就是把人类偏好的随机性简化成一个潜标量加一层 logistic 噪声。

### 关键的一步：代入并观察

把 (9) 代入 (12)，注意 $$y_w$$ 和 $$y_l$$ **共享同一个 $$x$$**：

$$
\Pr(y_w\succ y_l\mid x)=\sigma\Big(
\underbrace{\beta\log\frac{\pi^{*}(y_w\mid x)}{\pi_{\mathrm{ref}}(y_w\mid x)}+\beta\log Z(x)}_{r(x,y_w)}
-
\underbrace{\beta\log\frac{\pi^{*}(y_l\mid x)}{\pi_{\mathrm{ref}}(y_l\mid x)}+\beta\log Z(x)}_{r(x,y_l)}
\Big)
\tag{13}
$$

$$\beta\log Z(x)$$ 在两项里是**同一个数**，直接对消：

$$
\Pr(y_w\succ y_l\mid x)=\sigma\!\left(
\beta\log\frac{\pi^{*}(y_w\mid x)}{\pi_{\mathrm{ref}}(y_w\mid x)}
-
\beta\log\frac{\pi^{*}(y_l\mid x)}{\pi_{\mathrm{ref}}(y_l\mid x)}
\right)
\tag{14}
$$

**这是全篇最漂亮的一步。** 那个指数级不可计算的 $$Z(x)$$ 之所以消失，原因很朴素：它只依赖 $$x$$，而一对偏好天然共享同一个 $$x$$。偏好是"同题内比较"，任何同题的常数都会被差掉。

这也说明 (9) 里那个"丢掉 $$\beta\log Z(x)$$"的动作不是权宜之计——**在这个损失函数里它本来就不出现**。

## 六、第四步：DPO 损失函数

现在 (14) 里的偏好概率只含策略。把它当成似然，在偏好数据集上做极大似然估计，取负号变成损失：

$$
\mathcal{L}_{\mathrm{DPO}}(\pi_{\theta})=-\,\mathbb{E}_{(x,y_w,y_l)\sim\mathcal{D}}\!\left[
\log\sigma\!\left(
\beta\log\frac{\pi_{\theta}(y_w\mid x)}{\pi_{\mathrm{ref}}(y_w\mid x)}
-
\beta\log\frac{\pi_{\theta}(y_l\mid x)}{\pi_{\mathrm{ref}}(y_l\mid x)}
\right)
\right]
\tag{15}
$$

把括号里的标量单独命名会更清楚：

$$
\Delta_{\theta}(x,y_w,y_l)=\log\frac{\pi_{\theta}(y_w\mid x)}{\pi_{\mathrm{ref}}(y_w\mid x)}-\log\frac{\pi_{\theta}(y_l\mid x)}{\pi_{\mathrm{ref}}(y_l\mid x)},
\qquad
\mathcal{L}_{\mathrm{DPO}}=-\,\mathbb{E}\big[\log\sigma(\beta\,\Delta_{\theta})\big]
\tag{16}
$$

**到这一步，奖励模型、采样、RL 循环全都没有了。** 剩下的就是一个二分类形状的损失：让 $$\pi_{\theta}$$ 相对 $$\pi_{\mathrm{ref}}$$ 更偏好 $$y_w$$ 而不是 $$y_l$$，偏离用 $$\beta$$ 控温。

### 数值稳定

$$\log\sigma(z)=-\log(1+e^{-z})=-\mathrm{softplus}(-z)$$。当 $$z$$ 很负时直接算 $$\sigma(z)$$ 会下溢到 0，再取对数就是 $$-\infty$$。实践中始终用 `log_sigmoid` / `softplus` 形式的原语，不要写 `log(sigmoid(z))`。

### 实现只需要四个 log 概率

$$
\Delta_{\theta}=\underbrace{\log\pi_{\theta}(y_w\mid x)}_{\text{trainable}}-\underbrace{\log\pi_{\mathrm{ref}}(y_w\mid x)}_{\text{precomputed}}-\log\pi_{\theta}(y_l\mid x)+\log\pi_{\mathrm{ref}}(y_l\mid x)
$$

参考模型的四项里有两项不随训练变化，可以提前算好存盘。核心代码就是一个 logsigmoid：

```python
import torch.nn.functional as F

def dpo_loss(pi_logp_w, pi_logp_l, ref_logp_w, ref_logp_l, beta=0.1):
    # 每个输入都是「整条回答的 log 概率之和」，形状 [batch]
    implicit_w = beta * (pi_logp_w - ref_logp_w)   # r_hat(x, y_w)
    implicit_l = beta * (pi_logp_l - ref_logp_l)   # r_hat(x, y_l)
    logits = implicit_w - implicit_l               # beta * Delta
    return -F.logsigmoid(logits).mean()
```

## 七、第五步：梯度的形状，以及它为什么是加权 SFT

对 (15) 求 $$\theta$$ 的梯度。记 $$u=\beta\Delta_{\theta}=\hat r_{\theta}(x,y_w)-\hat r_{\theta}(x,y_l)$$，损失是 $$-\log\sigma(u)$$。用两个基本事实：

$$
\frac{d}{dz}\big[-\log\sigma(z)\big]=-\big(1-\sigma(z)\big)=-\sigma(-z),
\qquad
\nabla_{\theta}\log\frac{\pi_{\theta}(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}=\nabla_{\theta}\log\pi_{\theta}(y\mid x)
$$

第二式成立是因为 $$\pi_{\mathrm{ref}}$$ 冻结、与 $$\theta$$ 无关。注意 $$\sigma(-u)=\sigma\big(\hat r_{\theta}(x,y_l)-\hat r_{\theta}(x,y_w)\big)$$，于是

$$
\nabla_{\theta}\mathcal{L}_{\mathrm{DPO}}
=
-\,\beta\,\mathbb{E}\Big[
\underbrace{\sigma\big(\hat r_{\theta}(x,y_l)-\hat r_{\theta}(x,y_w)\big)}_{\text{weight}}
\Big(\nabla_{\theta}\log\pi_{\theta}(y_w\mid x)-\nabla_{\theta}\log\pi_{\theta}(y_l\mid x)\Big)
\Big]
\tag{17}
$$

逐项读这个式子：

- **括号里**是"提高 $$y_w$$ 的概率、压低 $$y_l$$ 的概率"，形状和对比学习、pairwise 排序损失一模一样。
- **权重**是模型当前"把输家排得比赢家高多少"的 sigmoid。

权重的行为很关键。如果模型当前已经强烈偏好 $$y_w$$（$$\hat r_w\gg\hat r_l$$），那 $$\hat r_l-\hat r_w$$ 很负，权重 $$\to 0$$，这个样本几乎不再产生梯度；如果模型把顺序搞反了（$$\hat r_l>\hat r_w$$），权重趋近 1，全量更新。并且权重有上界（$$\le 1$$），所以 DPO 不会被个别样本的极端错误带爆。

**所以 DPO 的梯度就是"按当前隐式奖励错得多离谱"加权的 pairwise SFT。** 这也从梯度角度解释了为什么不需要显式奖励模型：奖励模型在 PPO 流程里的作用是给样本打分、算优势；在 DPO 里，这个"打分"已经被策略自己的对数比 $$\hat r_{\theta}$$ 接管了。

回头看第九节的坑 1 会有个有意思的推论：**DPO 的梯度只依赖奖励差**，与 (17) 里只出现 $$\hat r_{\theta}$$ 的差一致——这正是规范对称性在梯度层面的体现。

## 八、为什么这套变形是"等价"的

上面是从"设最优策略为 $$\pi^*$$"推出来的。要确认 DPO 真的解了原问题，把链条反过来读一遍：

1. 假设真实偏好确实由某个奖励 $$r^*$$ 经 BT 模型 (12) 生成；
2. 假设 (1) 的最优策略 $$\pi^*$$ 落在参数化族 $$\{\pi_{\theta}\}$$ 内（**可实现性假设**）；
3. 那么 (15) 的全局最优 $$\theta$$ 满足 $$\pi_{\theta}=\pi^*$$，也就是它同时是 (1) 的解——因为 (15) 就是 (1) 的解代入 BT 似然后的等价重写，而 BT 似然的极大化是相合的。

而且此时 (10) 给出的 $$\hat r_{\theta}$$ 就是 $$r^*$$ 的一个同题等价版本，**可以直接当奖励模型用**：论文里验证了用它做 Best-of-$$n$$ 重排、或者反过来喂给 PPO，效果都成立。

### 与 PPO-RLHF 的关系

| | PPO-RLHF | DPO |
| --- | --- | --- |
| 流程 | 拟合奖励模型 → 用 RL 优化 (1) | 直接在偏好上拟合策略 |
| 目标函数 | (1) | (15)（(1) 的等价重写） |
| 需要的模型 | 策略 + 参考 + 奖励 + 价值（4 个） | 策略 + 参考（2 个） |
| 数据 | 可用无标注 prompt 在线采样 | 固定的离线偏好对 |
| 主要不稳定源 | RL 的采样、优势估计、超参 | 基本没有 RL 循环 |

也就是说，(8) 那个闭式解把"奖励模型 + RL"这条两阶段流水线**压成了单阶段监督学习**。省掉的不是一个工程环节，而是一整类不稳定性。

### 代价是什么

**DPO 不能探索。** 它只用固定的离线偏好对，不会像 PPO 那样拿任意无标注 prompt 去在线采样、发现自己不知道的东西。这是"用闭式解换掉 RL"的实质代价，也是后续一大批工作（在线 DPO、迭代式 DPO 等）想补回来的东西。

## 九、几个必须知道的坑

**1. $$\beta$$ 有两个身份，且无法分别识别。** 在 (1) 里它是 KL 正则强度；在 (12) 里 BT 的温度被默认固定为 1，而奖励的**整体尺度**又不可识别——把 $$r$$ 乘上常数 $$c$$、同时把 $$\beta$$ 乘上 $$c$$，所有式子的数值结果完全不变。所以真正有意义的量不是 $$\beta$$，而是"**每单位奖励允许多少 nats 的 KL 偏离**"，$$\beta$$ 与 BT 温度无法分开辨识。调 $$\beta$$ 时要知道你在同时动这两件事。

**2. $$\pi_{\mathrm{ref}}$$ 必须覆盖数据的支持集。** (9) 成立要求 $$r$$ 有限时 $$\pi_{\mathrm{ref}}(y\mid x)>0$$。若参考策略给某个回答的概率为 0，对数比就是 $$-\infty/+\infty$$，式子没有定义。这正是"必须先 SFT 再 DPO"的原因——$$\pi_{\mathrm{ref}}$$ 至少得是能给人类回答分配非零概率的模型。

**3. 长度是被利用的对象，不是无关变量。** $$\log\pi(y\mid x)$$ 是**逐 token 求和**，不是平均。所以一条更长的回答天然有更极端的对数比，隐式奖励 (10) 会系统性地与长度相关；DPO 常见的"越训越长/越短"现象就出在这里。要抑制的话，得显式做长度归一化或加长度正则，光调 $$\beta$$ 治不了根。

**4. 似然位移（likelihood displacement）。** (15) 只约束 $$y_l$$ 的**相对**概率被压低，并没有约束 $$y_w$$ 的绝对概率必须上升。实践中经常观察到一个反直觉现象：$$y_w$$ 和 $$y_l$$ 的绝对概率**同时下降**，只是 $$y_l$$ 降得更多。这是目标函数本身的性质，不是实现 bug。

**5. $$Z(x)$$ 只是在对消中被消灭，没有被算出来。** 一旦你需要 (10) 的**绝对值**——比如跨 prompt 比较奖励、或者想把 $$\hat r_{\theta}$$ 当成一个全局奖励模型去用——那个不知道的 $$\beta\log Z(x)$$ 就会回来。同题内比较时它无害，跨题比较时它是未知偏置。

**6. 上限是 BT 假设。** 人类偏好的噪声不独立、偏好关系不传递（A 优于 B、B 优于 C、C 优于 A 是常见的）、还有位置偏见。BT 把这些压缩成一个潜标量加 logistic 噪声。DPO 的成败上限就卡在这个建模选择上，而不是卡在算法细节上。

## 十、一页总结

从 (1) 出发，四步变形，每步消掉一个障碍：

1. **闭式最优策略**（第 3 节）：固定 $$x$$，目标严格凹 + 约束凸，KKT 给出 (8)。消掉 RL —— 不需要采样迭代就能写出最优策略，代价是它依赖未知的 $$r$$ 和一个算不出的 $$Z(x)$$。
2. **奖励的反解**（第 4 节）：由 (9) 看出 $$\hat r_{\theta}=\beta\log(\pi_{\theta}/\pi_{\mathrm{ref}})$$ 就是奖励。消掉奖励模型 —— 策略自己就是奖励的载体；丢掉的 $$\beta\log Z(x)$$ 落在规范自由度里。
3. **BT 下相消**（第 5 节）：偏好共享同一个 $$x$$，所以 $$\beta\log Z(x)$$ 在差里消失。消掉配分函数 —— 这是全篇的技术核心。
4. **极大似然**（第 6 节）：得到 (15)，只剩四个可算的 log 概率。

梯度 (17) 说明它训练时在做什么：以"当前隐式奖励错得多离谱"为权重，提高胜者概率、压低败者概率。

**一句话复述 DPO：** (1) 的最优策略有闭式解，于是可以把策略本身当作奖励的表示，直接在人类偏好上做监督学习——而这一步之所以可能，是因为偏好是同题内比较，让那个不可计算的配分函数恰好相消。

## 参考资料

- Rafailov et al., *Direct Preference Optimization: Your Language Model is Secretly a Reward Model*, NeurIPS 2023. arXiv:2305.18290
- Christiano et al., *Deep Reinforcement Learning from Human Preferences*, NeurIPS 2017.（BT 模型用于人类偏好的来源）
- Ouyang et al., *Training language models to follow instructions with human feedback*, NeurIPS 2022.（InstructGPT，PPO-RLHF 的标准流程）
- Azar et al., *A General Theoretical Paradigm to Understand Learning from Human Preferences*, AISTATS 2024.（IPO，讨论 BT 假设的替代方案）
