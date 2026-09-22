---
layout: post
title: 用脚本生成"可验证"的 PPT：一份 python-pptx 实践清单
date: 2026-09-22
categories: [技术]
description: 从一份长报告生成 29 页中文汇报 PPT 的完整经验：中文排版、表格行高、文字溢出这三类坑，以及用 PowerPoint 自身度量做版式验证的方法。
---

用脚本生成 PPT 的难处不在"画出来"，而在**画出来之后不知道自己错在哪**。python-pptx 不会告诉你某段文字溢出了 0.3 英寸，也不会告诉你表格实际比声明的矮了一半。等你发现时，往往是在投影仪前。

这篇整理一套可复用的流程，以及我踩过的三类坑。

## 整体流程

把内容与排版分开，中间加一层校验：

```
源文档（Markdown）
   ↓  人工提炼：每页一个主张
内容结构（Python 数据）
   ↓  脚本渲染
.pptx
   ↓  第一层校验：用 python-pptx 读回几何，估算文字高度
   ↓  第二层校验：用 PowerPoint 自身度量真实文字高度
修正 → 重新生成
```

关键是**第二层校验必须存在**。第一层是估算，只能拦住明显错误；真实排版宽度、字体回退、表格行高的实际表现，只有渲染器自己知道。

## 坑 1：中文字体不会自动生效

`run.font.name = "微软雅黑"` 只写了 latin 字体，中文会走渲染器的回退，落到不知名字体上，行高和宽度全部对不上。

要显式写 East Asian 字体：

```python
from pptx.oxml.ns import qn

def set_ea_font(run, font="微软雅黑"):
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", font)
```

每个 run 都要调一次。这一步不做，后面所有的溢出估算都是错的。

## 坑 2：表格行高会被重新解释

这是最隐蔽的一个。我在脚本里写：

```python
shp = slide.shapes.add_table(nrows, ncols, left, top, width, height)
tbl.rows[0].height = Inches(0.35)   # 本意：每行 0.35 英寸
```

生成出来的文件看上去没问题，行高属性读回也确实是 0.35 英寸。**但 PowerPoint 打开时会重新计算**：它按实际字体度量取一个下限，然后按图形框总高重新分配。结果是一张 7 行的表从 2.45 英寸变成 17 英寸——直接顶穿页面，内容在放映时完全看不到。

两个要点：

1. **不要用 `add_table(..., height=0)`**。留 0 会让图形框保持一个异常巨大的默认高度；如果这个高度远大于"行数 × 行高"，PowerPoint 会把它当成真实高度。
2. **行高的下限由字号决定**，不是你想设多小就多小。实测大约 **字号(磅) × 1.55 / 72** 英寸。11 磅的字，每行至少约 0.24 英寸。

稳妥做法是**直接写 XML**，把行高与图形框高度同时设成同一个精确值：

```python
from pptx.util import Emu, Inches
from pptx.oxml.ns import qn

row_h = Emu(int(Inches(max(given, size * 1.55 / 72))))
tbl_el = shp._element.find(qn("a:graphic")).find(qn("a:graphicData")).find(qn("a:tbl"))
for tr in tbl_el.findall(qn("a:tr")):
    tr.set("h", str(int(row_h)))
shp._element.find(qn("p:xfrm")).find(qn("a:ext")).set("cy", str(int(row_h) * nrows))
```

顺便说一个诊断方法：**读回行高，换算成英寸，看它是否约等于"图形框高度 ÷ 行数"**。如果相等，说明行高被忽略了，PPT 是按框平分的。

## 坑 3：文字溢出要两层验证

**第一层：本地估算。** 按字符宽度粗算，够用但别太乐观：

```
每行容量 = 可用宽度 / (字号 / 72)
有效字符数 = 全角字符数 + 0.45 × 半角字符数
所需高度 = 行数 × 字号 × 行距 × 1.37 / 72
```

那个 1.37 是经验修正系数，来自中文字体实际行高，比标称行距大。**0.45** 是拉丁字符相对全角字符的宽度比。这两个值只在本机字体环境下准，换字体要重新标定。

**第二层：让 PowerPoint 自己量。** 把每个文本框的 `AutoSize` 打开，让 PowerPoint 把框缩放到刚好容纳文字，保存后读回高度：

```powershell
$pres = $ppt.Presentations.Open($path, $false, $false, $false)
foreach ($sl in $pres.Slides) { foreach ($sh in $sl.Shapes) {
  if ($sh.HasTextFrame -ne -1) { continue }
  if ($sh.TextFrame2.TextRange.Text.Trim().Length -eq 0) { continue }
  $sh.TextFrame2.AutoSize = 1     # 缩放到恰好容纳文字
} }
$pres.Save(); $pres.Close()
```

然后比较"需要的高度"与"原本声明的高度"。**注意两个陷阱**：

- 量之前先复制一份文件，别把正式稿改了；
- 如果同一页有坑 2 里那种"巨型图形框"，`AutoSize` 的读数也会被带偏。所以先把表格修对，再做这一步。

## 顺带几个小坑

| 现象 | 原因与处理 |
|---|---|
| 箭头位置飘 | 用旋转的三角形做箭头时，旋转后的外接矩形与预期不同。改成"矩形杆 + 三角头"两段拼，标签放在杆上方而不是压在杆上 |
| 保存报 `PermissionError` | 文件正被 PowerPoint 打开。别去结束进程，直接让脚本按 `_2`、`_3` 自动换名保存，并在输出里说明 |
| 文本锚点对不齐 | 文本框设 `MSO_ANCHOR.MIDDLE`，同时把 `margin_*` 全部置 0，再用 `space_after` 控制段距 |
| 中文在等宽字体里挤压 | 代码块用等宽字体时，仍要写 East Asian 字体，否则中文走回退字体，宽度比预期大 |

## 一个真实案例

上面坑 2 那个"17 英寸表格"，在生成阶段一切正常：脚本无报错，`python-pptx` 读回行高也正确。问题只在 PowerPoint 里存在。

发现它的方式不是肉眼——而是把每一页导出成 PNG 之后做逐页检查，配合上面第二层的度量。**这就是为什么必须有第二层校验：只在 python-pptx 里自查，这类错误会一直隐藏到放映现场。**

## 建议的脚本划分

```
build_deck.py     # 内容 + 渲染，纯 python-pptx
audit_layout.py   # 第一层：读回几何，查溢出/重叠/越界
measure.ps1       # 第二层：交给 PowerPoint 度量真实高度
```

三层职责分开之后，改文案只需要动 `build_deck.py`，校验永远跑同两条命令。一套 30 页的中文汇报，从改文案到确认版式干净，大概两分钟。

对长文档转汇报来说，这套流程最大的价值不是省时间，而是**让"版式正确"变成一个可验证的断言**，而不是靠翻页目测。
