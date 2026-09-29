---
layout: post
title: sigmoid、softmax、softplus：三个函数其实是同一家人
date: 2026-09-29
categories: [技术]
description: 从 logsumexp 这个共同的根出发理解三个函数：softmax 是它的梯度、softplus 是它的一元版本、sigmoid 是 softmax 在 K=2 时的特例，以及由此得到的数值稳定写法。
---

这三个函数总是挤在同一段代码里：

```python
log_p = F.log_softmax(logits, dim=-1)   # 里面是 softmax
loss  = -F.logsigmoid(logit)            # 里面是 sigmoid 与 softplus
```

这不是巧合。它们**不是三个并列的知识点，而是同一个东西的三个切面**——那个共同的根叫 logsumexp。这篇文章先把三个函数各自讲清楚，然后把它们之间的关系网摊开，最后给出实现时的数值稳定写法。

## 一、先看结论

| 函数 | 定义 | 值域 | 导函数 |
| --- | --- | --- | --- |
| sigmoid | $$\sigma(z)=\dfrac{1}{1+e^{-z}}$$ | $$(0,1)$$ | $$\sigma(z)\big(1-\sigma(z)\big)$$ |
| softmax | $$\mathrm{softmax}(z)_i=\dfrac{e^{z_i}}{\sum_j e^{z_j}}$$ | 概率单纯形 | 雅可比 $$p_i(\delta_{ij}-p_j)$$ |
| softplus | $$\zeta(z)=\log(1+e^{z})$$ | $$(0,\infty)$$ | $$\sigma(z)$$ |

注意一个容易被含混过去的区别：**sigmoid 和 softmax 输出的是概率，softplus 输出的不是概率**——它的值域是 $$(0,\infty)$$，是一个非负的量。softplus 的重要性不在于"把得分变成概率"，而在于它是前两个函数的**底座**：它是 logsumexp 的一元情形，而且它的导数恰好就是 sigmoid。

## 二、sigmoid：二分类的概率

### 定义与形状

$$
\sigma(z)=\frac{1}{1+e^{-z}}=\frac{e^{z}}{1+e^{z}}
\tag{1}
$$

输入是任意实数 $$z$$，输出落在 $$(0,1)$$ 开区间上，严格单调递增。

$$
\begin{aligned}
z &: \quad -3 \quad\ -1 \quad\quad 0 \quad\quad 1 \quad\quad 2 \quad\quad 3\\
\sigma(z) &: \ 0.047 \ \ 0.269 \ \ 0.500 \ \ 0.731 \ \ 0.881 \ \ 0.953
\end{aligned}
\tag{2}
$$

这个形状是 S 形的：两端饱和（梯度趋近 0），中间近似线性，在 $$z=0$$ 处斜率为最大。

### 三条好用的性质

**对称性。** 直接通分即可验证：

$$
\sigma(-z)=1-\sigma(z)
\tag{3}
$$

所以 $$\sigma(0)=0.5$$，函数图像关于点 $$(0,\tfrac12)$$ 中心对称。

**导数。** 这是它当年被选中的主要原因——导数可以只用自己表示。记 $$\sigma=\sigma(z)$$：

$$
\frac{d\sigma}{dz}=\frac{e^{-z}}{(1+e^{-z})^{2}}=\sigma(1-\sigma)
\tag{4}
$$

**它的反函数就是 logit。** 这一步是理解后面 softmax 与 logsumexp 的钥匙，先把式子写出来：

$$
\log\frac{\sigma(z)}{1-\sigma(z)}=z
\tag{5}
$$

左边就是**对数几率**（log-odds）：事件概率与对立事件概率之比再取对数。所以 sigmoid 是"对数几率 → 概率"，logit 是"概率 → 对数几率"，两者互为反函数。

### 用处

二分类的输出层；各种门控（LSTM/GRU 的门、注意力里的掩蔽）；以及作为"把任意实数压到 0–1"的通用开关。

## 三、softmax：多分类的概率

### 定义

$$
\mathrm{softmax}(z)_i=\frac{e^{z_i}}{\sum_{j=1}^{K}e^{z_j}}
\tag{6}
$$

输入是 $$K$$ 维向量（就是 logits），输出也是 $$K$$ 维：**每个分量落在 $$(0,1)$$，全部加起来等于 1**——也就是落在概率单纯形上。

语言模型的下一个 token 分布就是它：logits 的形状是 `[batch, seq_len, vocab_size]`，对最后一维做 softmax 就得到词表上的概率分布。

### 平移不变性：只有差起作用

$$
\mathrm{softmax}(z+c\mathbf{1})=\mathrm{softmax}(z)
\tag{7}
$$

分子分母同时乘上 $$e^{c}$$，约掉了。这条性质有两层意义：

**第一层，概念上的。** 给所有 logit 加同一个常数，概率分布完全不变。所以 logits 的**绝对数值没有意义，只有彼此之间的差有意义**。这也解释了为什么模型输出的 logits 可以是任意大或任意小的数。

**第二层，工程上的。** 这正是数值稳定写法的依据——既然平移不变，那就可以放心减去最大值，见第六节。

### 温度

$$
\mathrm{softmax}(z/T)_i=\frac{e^{z_i/T}}{\sum_j e^{z_j/T}}
\tag{8}
$$

$$T$$ 是温度。$$T\to 0^{+}$$ 时分布塌缩成 one-hot（只挑最大的那个）；$$T\to\infty$$ 时趋于均匀分布；$$T=1$$ 就是标准 softmax。所以"把 logits 乘一个系数"和"调温度"是同一件事——乘 $$\beta>0$$ 等价于把温度除以 $$\beta$$。

### K = 2 时它退化成 sigmoid

这是三者关系的第一个接口。取只有两项的 softmax，看第一项：

$$
\mathrm{softmax}([z_w,z_l])_w=\frac{e^{z_w}}{e^{z_w}+e^{z_l}}=\frac{1}{1+e^{-(z_w-z_l)}}=\sigma(z_w-z_l)
\tag{9}
$$

**只差一个"差"。** 所以 sigmoid 不是什么独立的函数，它就是 softmax 在 $$K=2$$ 时的特例；反过来说，softmax 是 sigmoid 在多类别上的推广。

这也给了一个实用推论：二分类问题里"用 sigmoid 输出一个概率"和"用两个 logit 做 softmax 取第一项"，数学上完全等价——前者省一半参数，因为 sigmoid 隐含地把另一个 logit 固定成了 0。

### 雅可比矩阵

如果需要 softmax 的导数（比如手写反向传播），结果是这个形式（记 $$p=\mathrm{softmax}(z)$$）：

$$
\frac{\partial p_i}{\partial z_j}=p_i\big(\delta_{ij}-p_j\big)
\tag{10}
$$

$$\delta_{ij}$$ 是 Kronecker delta（$$i=j$$ 时为 1，否则为 0）。写成矩阵就是 $$\mathrm{diag}(p)-pp^{\top}$$，是一个对称的半负定矩阵——这对应着 softmax 的"平移不变"：沿全 1 方向 $$p$$ 的导数为零。

## 四、softplus：光滑版的 ReLU

### 定义与形状

$$
\zeta(z)=\log(1+e^{z})
\tag{11}
$$

值域 $$(0,\infty)$$，严格单调递增，处处光滑。

它的形状是 **ReLU 的光滑近似**：$$\mathrm{ReLU}(z)=\max(0,z)$$ 在 0 处有个折角，而 softplus 把那个折角抹圆了。两端的行为是：

$$
\zeta(z)\longrightarrow
\begin{cases}
0, & z\to-\infty\\[2pt]
z, & z\to+\infty
\end{cases}
\tag{12}
$$

在 $$z\to+\infty$$ 时 $$\zeta(z)=z+\log(1+e^{-z})\to z$$；在 $$z\to-\infty$$ 时 $$\zeta(z)\approx e^{z}\to 0$$。所以它确实是 ReLU 的一个"软化"，但在负半轴是指数衰减而不是精确的 0——意味着**梯度永远不会真的变成 0**，不会出现 ReLU 那种"死亡神经元"。

### 它的导数就是 sigmoid

$$
\frac{d\zeta}{dz}=\frac{e^{z}}{1+e^{z}}=\sigma(z)
\tag{13}
$$

这个关系是三者之间最直接的一条线。既然导数非负且恒在 $$(0,1)$$ 内，softplus 就是单调递增的，而且**梯度永远不消失也不爆炸**——上限恰好是 1。

反过来写，就得到积分关系（用 $$\zeta(-\infty)=0$$）：

$$
\int_{-\infty}^{z}\sigma(t)\,dt=\zeta(z)
\tag{14}
$$

也就是说：**softplus 是 sigmoid 的原函数**。这两个函数在微积分意义上是一对——这大概是它们总被放在一起的最深层原因。

### 用处

- 需要输出**正值参数**的地方，比如高斯分布的方差、标准差（$$e$$ 指数化太猛，softplus 更温和）
- 需要计算 $$\log(1+e^{z})$$ 的地方——这本身就是个常见子表达式
- 以及下面要说的：它其实是 logsumexp 的一元情形

## 五、它们其实是同一个东西

到这里可以把关系网摊开了。先引入那个共同的根：

$$
\mathrm{logsumexp}(z)=\log\sum_{j=1}^{K}e^{z_j}
\tag{15}
$$

它是"先指数、再求和、再取对数"，是 softmax 的对数域的兄弟——它保证不溢出、也不下溢（见第六节）。现在看三件事。

### 第一件：softmax 是 logsumexp 的梯度

$$
\frac{\partial}{\partial z_i}\mathrm{logsumexp}(z)=\frac{e^{z_i}}{\sum_j e^{z_j}}=\mathrm{softmax}(z)_i
\tag{16}
$$

**softmax 就是 logsumexp 的梯度。** 这个事实在推导 softmax 回归的梯度、以及各种"log 域"算法时会反复用到。

### 第二件：softplus 是 logsumexp 的一元版本

把 $$0$$ 补进向量里，取 $$K=2$$：

$$
\mathrm{logsumexp}([0,\,z])=\log(1+e^{z})=\zeta(z)
\tag{17}
$$

所以 softplus 不需要单独理解——它就是 logsumexp 在"一个维度加上一个 0"时的样子。

### 第三件：于是 sigmoid 自动也是

把 (9) 和 (17) 拼起来：

$$
\sigma(z)=\mathrm{softmax}([0,z])_1=\frac{\partial}{\partial z}\,\zeta(z)
\tag{18}
$$

### 一张关系表

| 关系 | 式子 | 说法 |
| --- | --- | --- |
| softmax ↔ logsumexp | $$\mathrm{softmax}=\nabla\,\mathrm{logsumexp}$$ | 求导 |
| softplus ↔ logsumexp | $$\zeta(z)=\mathrm{logsumexp}([0,z])$$ | 一元特例 |
| softplus ↔ sigmoid | $$\zeta'(z)=\sigma(z)$$ | 求导 / 积分 |
| softmax ↔ sigmoid | $$\mathrm{softmax}([z_w,z_l])_w=\sigma(z_w-z_l)$$ | $$K=2$$ 特例 |
| softmax ↔ softplus | $$\sigma(z)=\mathrm{softmax}([0,z])_1$$ | 两条线合流 |

**一句话总结：根是 logsumexp。softmax 是它的梯度，softplus 是它补一个 0 之后的一元版本，sigmoid 是 softmax 在 K = 2 时的特例，同时又是 softplus 的导数。**

### 还有一条 log 域的恒等式

在写损失函数时，真正用到的往往是"概率的对数"，而它可以直接由 logsumexp 表示：

$$
\log\mathrm{softmax}(z)_i=z_i-\mathrm{logsumexp}(z)
\tag{19}
$$

把它和二元情形并排看，会发现形式完全一样：

$$
\log\sigma(z)=z-\zeta(z)=-\zeta(-z)
\tag{20}
$$

对照着读：(19) 里的 $$\mathrm{logsumexp}(z)$$ 扮演的正是 (20) 里 $$\zeta(z)$$ 的角色——因为 $$\zeta(z)=\mathrm{logsumexp}([0,z])$$。**同一个公式，二元版和多元版只差一个 logsumexp。**

(20) 里那个 $$-\zeta(-z)$$ 的写法特别重要，它就是代码里 `logsigmoid` 的实现原理，也是 DPO 损失能写得稳定的原因。

## 六、数值稳定：其实只有一件事

三个函数都涉及 $$e^{z}$$，而浮点数上 $$e^{z}$$ 在 $$z\gtrsim 709$$ 时溢出成 `inf`、在 $$z\lesssim-745$$ 时下溢成 `0`。所以每个函数都有一份"稳定写法"，但它们的思路是同一个：**想办法把指数项挪到非正区间，再用 log 域的恒等式把挪走的量补回来。**

**softmax** —— 用平移不变性 (7) 减去最大值：

$$
\mathrm{softmax}(z)=\mathrm{softmax}(z-\max_j z_j)
$$

减完之后最大的指数是 $$e^{0}=1$$，其余都 $$\le 1$$，不可能溢出。分母至少是 1，也不会下溢到 0。

**logsumexp** —— 同样减最大值，但要把减掉的量加回去：

$$
\mathrm{logsumexp}(z)=\max_j z_j+\log\sum_j e^{\,z_j-\max_j z_j}
$$

**sigmoid** —— 直接算 $$e^{-z}$$ 在 $$z$$ 很负时会溢出，所以分两支：

$$
\sigma(z)=
\begin{cases}
\dfrac{1}{1+e^{-z}}, & z\ge 0\\[8pt]
\dfrac{e^{z}}{1+e^{z}}, & z \lt 0
\end{cases}
$$

两支里指数项都非正，都安全。

**softplus** —— 直接算 $$\log(1+e^{z})$$ 在 $$z$$ 很大时会把 $$e^z$$ 先算成 `inf`。稳定形式是把 (12) 的渐近行为显式写进去：

$$
\zeta(z)=\max(z,0)+\log\!\big(1+e^{-|z|}\big)
\tag{21}
$$

验证一下：$$z\ge 0$$ 时它等于 $$z+\log(1+e^{-z})=\log(e^{z}+1)$$；$$z \lt 0$$ 时它等于 $$\log(1+e^{z})$$。两边都对上了，而指数项永远在 $$(-\infty,0]$$ 里。

**实践结论：这些都不用自己写。** PyTorch 里直接用内置的稳定原语：

```python
F.softmax(logits, dim=-1)       # 已减最大值
F.log_softmax(logits, dim=-1)   # log(softmax) 的稳定实现，不要写 log(softmax(x))
F.softplus(x)                   # 已用 (21) 的形式
F.logsigmoid(x)                 # = -softplus(-x)，不要写 torch.log(torch.sigmoid(x))
```

最后一条尤其要注意：`log(sigmoid(x))` 在 $$x$$ 很负时，`sigmoid(x)` 先下溢成 0，取对数就变成 `-inf`；而 `logsigmoid` 用 (20) 的恒等式永远算得出来。

## 七、回头看 DPO：三个函数各自出现在哪

这三个函数在同一篇推导里各司其职，正好可以当小结（详见[《DPO 的核心推导》]({{ '/posts/dpo-core-derivation/' | relative_url }})）：

| 位置 | 用到的函数 | 为什么 |
| --- | --- | --- |
| 最优策略 $$\pi^{*}(y\mid x)=\frac{1}{Z(x)}\pi_{\mathrm{ref}}\exp(\frac{r}{\beta})$$ | **softmax** | 这就是在回答空间上的 softmax，logits 是 $$\log\pi_{\mathrm{ref}}+r/\beta$$。所以说它是玻尔兹曼分布 |
| 偏好概率 $$\Pr(y_w\succ y_l\mid x)=\sigma(\cdot)$$ | **sigmoid** | 一对样本是二分类，正是 (9) 的 $$K=2$$ 情形 |
| 损失 $$-\log\sigma(\beta\Delta)$$ | **softplus** | 由 (20)，它等于 $$\zeta(-\beta\Delta)$$，这就是 `-F.logsigmoid` 的实现 |

也就是说，DPO 的损失函数可以直接写成 softplus：

$$
\mathcal{L}_{\mathrm{DPO}}=\mathbb{E}\Big[\zeta\big(-(\hat r_{\theta}(x,y_w)-\hat r_{\theta}(x,y_l))\big)\Big]
\tag{22}
$$

## 八、小结

- **sigmoid** $$\sigma(z)=\frac{1}{1+e^{-z}}$$：输出 $$(0,1)$$；$$\sigma(-z)=1-\sigma(z)$$；导数是 $$\sigma(1-\sigma)$$；反函数是 logit（对数几率）
- **softmax**：输出概率单纯形；**平移不变**，所以只有 logit 的差有意义；$$K=2$$ 时退化成 sigmoid；雅可比是 $$\mathrm{diag}(p)-pp^{\top}$$
- **softplus** $$\zeta(z)=\log(1+e^{z})$$：输出 $$(0,\infty)$$，是 ReLU 的光滑版；**导数是 sigmoid**，本身是 sigmoid 的原函数
- 三者的根是 **logsumexp**：softmax 是它的梯度，softplus 是它的一元特例，sigmoid 是两者的交汇
- 数值稳定只有一件事：**把指数项挪到非正区间**。实践里一律用 `log_softmax` / `logsumexp` / `softplus` / `logsigmoid` 这些内置原语

## 参考资料

- Bridle, *Probabilistic Interpretation of Feedforward Classification Network Outputs*, 1990.（sigmoid 与 softmax 的概率解释）
- Goodfellow, Bengio & Courville, *Deep Learning*, MIT Press 2016, 第 6.2.2 节（输出单元：sigmoid 与 softmax）与第 4 章（数值计算：上溢/下溢与 logsumexp）。
- Dugas et al., *Incorporating Second-Order Functional Knowledge for Better Option Pricing*, NeurIPS 2000.（softplus 作为光滑 ReLU 的出处）
