#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成数学资源库页面。

写成 math/index.html 这个 Jekyll 页面，复用站点自身的布局（导航、页脚、
styles.css、深浅色切换），所以它看起来和站点其它页面一致，而不是独立文档。

刻意保持零依赖：只用标准库，数据源是 math/data/library.py。
公式写成 LaTeX，交给站点已装的 MathJax 渲染；因为输出是 .html（不经 kramdown），
所以这里直接用 \\( ... \\) 行内、\\[ ... \\] 行间。

用法：python math/generate_math.py
输出：<repo-root>/math/index.html
"""
from __future__ import annotations

import html
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
OUT = HERE / "index.html"

sys.dont_write_bytecode = True          # 不要在 math/data 下留下 __pycache__
sys.path.insert(0, str(HERE / "data"))
import library  # noqa: E402

TOPICS = library.TOPICS
ENTRIES = library.ENTRIES


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def rich(s) -> str:
    """先转义，再支持最小行内标记：**粗体** 与 `代码`。

    输出是 .html 页（不经过 kramdown），所以这两个标记必须在这里处理，
    否则页面上会原样显示星号和反引号。
    """
    out = esc(s)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def plain_text(s) -> str:
    """去掉标记、用于搜索索引。"""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", str(s))
    t = re.sub(r"`([^`]+)`", r"\1", t)
    return t


# ------------------------------------------------------------------ 样式
STYLE = """<style>
.ml-lead{color:var(--muted);max-width:780px;margin:-26px 0 30px;font-size:1.02rem;line-height:1.8}
.ml-bar{display:flex;flex-wrap:wrap;gap:14px 26px;align-items:center;justify-content:space-between;
  padding:16px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.ml-bar input[type=search]{flex:1 1 240px;max-width:400px;padding:9px 12px;font:inherit;font-size:.9rem;
  color:inherit;background:var(--surface);border:1px solid var(--line);border-radius:6px}
.ml-bar input[type=search]:focus{outline:none;border-color:var(--accent)}
.ml-bar .filters{flex-wrap:wrap;row-gap:8px}
.ml-count{color:var(--muted);font-size:.82rem;margin:14px 0 0}
.ml-list{display:grid;gap:18px;margin-top:20px}
.ml-card{border:1px solid var(--line);border-radius:10px;background:var(--surface);padding:20px 22px}
.ml-card[hidden]{display:none}
.ml-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.ml-head h2{font-size:1.16rem;margin:0;font-weight:600}
.ml-head .ml-en{color:var(--muted);font-size:.82rem}
.ml-tag{margin-left:auto;font-size:.72rem;color:var(--accent);border:1px solid var(--accent);
  border-radius:999px;padding:2px 9px;white-space:nowrap}
.ml-sym{display:grid;grid-template-columns:auto 1fr;gap:3px 16px;margin:15px 0 0;font-size:.9rem}
.ml-sym dt{margin:0}
.ml-sym dd{margin:0;color:var(--muted)}
.ml-formula{margin:16px 0;padding:12px 14px;border:1px solid var(--line);border-radius:8px;
  background:var(--bg);overflow-x:auto}
.ml-plain{font-size:.95rem;line-height:1.78;margin:0 0 12px}
.ml-pit{list-style:none;padding:0;margin:0 0 12px;font-size:.88rem;line-height:1.72;color:var(--muted)}
.ml-pit li{padding-left:15px;position:relative}
.ml-pit li::before{content:"\\00b7";position:absolute;left:3px;color:var(--accent)}
.ml-where{font-size:.88rem;line-height:1.72;margin:0 0 10px;padding:10px 13px;border-radius:6px;
  background:var(--accent-soft)}
.ml-rel{font-size:.8rem;color:var(--muted);margin:0}
.ml-rel a{border-bottom:1px solid var(--line)}
.ml-rel a:hover{color:var(--accent);border-color:var(--accent)}
.ml-nohit{color:var(--muted);font-size:.9rem;padding:22px 0;display:none}
.ml-nohit[hidden]{display:none}
.ml-meta{color:var(--muted);font-size:.8rem;margin-top:40px;line-height:1.7}
@media (max-width:700px){.ml-sym{grid-template-columns:1fr;gap:2px}
  .ml-sym dd{margin:0 0 7px}.ml-card{padding:16px}.ml-tag{margin-left:0}}
</style>"""

SCRIPT = """<script>
(function () {
  var box = document.getElementById('ml-q');
  var list = document.getElementById('ml-list');
  if (!box || !list) return;
  var cards = [].slice.call(list.querySelectorAll('.ml-card'));
  var countEl = document.getElementById('ml-count');
  var nohit = document.getElementById('ml-nohit');
  var btns = [].slice.call(document.querySelectorAll('[data-ml-topic]'));
  var topic = 'all';
  function apply() {
    var q = box.value.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (c) {
      var okTopic = topic === 'all' || c.getAttribute('data-topic') === topic;
      var okQ = !q || (c.getAttribute('data-search') || '').indexOf(q) !== -1;
      var show = okTopic && okQ;
      if (show) { c.removeAttribute('hidden'); shown++; } else { c.setAttribute('hidden', ''); }
    });
    countEl.textContent = '显示 ' + shown + ' / ' + cards.length + ' 条';
    if (nohit) { if (shown === 0) { nohit.removeAttribute('hidden'); } else { nohit.setAttribute('hidden', ''); } }
  }
  box.addEventListener('input', apply);
  btns.forEach(function (b) {
    b.addEventListener('click', function () {
      btns.forEach(function (x) { x.classList.remove('active'); });
      b.classList.add('active');
      topic = b.getAttribute('data-ml-topic');
      apply();
    });
  });
  apply();
})();
</script>"""


def search_index(e: dict) -> str:
    parts = [e.get("term", ""), e.get("en", ""), plain_text(e.get("plain", ""))]
    for pair in e.get("symbols", []):
        # 逐项过 plain_text，否则符号说明里的 ** 与反引号会漏进属性
        parts.extend(plain_text(x) for x in pair)
    parts.extend(plain_text(p) for p in e.get("pitfalls", []))
    parts.append(plain_text(e.get("where", "")))
    parts.append(next((name for tid, name in TOPICS if tid == e.get("topic")), ""))
    return " ".join(parts).lower()


def render_entry(e: dict, term_of: dict) -> str:
    topic_name = next((n for t, n in TOPICS if t == e.get("topic")), "")
    p = [f'<article class="ml-card" id="{esc(e["id"])}" '
         f'data-topic="{esc(e.get("topic", ""))}" '
         f'data-search="{esc(search_index(e))}">']
    p.append('<div class="ml-head">')
    p.append(f'<h2>{rich(e["term"])}</h2>')
    if e.get("en"):
        p.append(f'<span class="ml-en">{esc(e["en"])}</span>')
    p.append(f'<span class="ml-tag">{esc(topic_name)}</span>')
    p.append('</div>')

    if e.get("symbols"):
        p.append('<dl class="ml-sym">')
        for sym, desc in e["symbols"]:
            # 符号里可能有 < > 等字符（如 y_{<t}），必须转义；浏览器会解码回来，
            # MathJax 读到的仍是原始 LaTeX。
            p.append(f'<dt>\\({esc(sym)}\\)</dt><dd>{rich(desc)}</dd>')
        p.append('</dl>')

    if e.get("formula"):
        p.append(f'<div class="ml-formula">\\[ {esc(e["formula"])} \\]</div>')

    if e.get("plain"):
        p.append(f'<p class="ml-plain">{rich(e["plain"])}</p>')

    if e.get("pitfalls"):
        p.append('<ul class="ml-pit">')
        for it in e["pitfalls"]:
            p.append(f'<li>{rich(it)}</li>')
        p.append('</ul>')

    if e.get("where"):
        p.append(f'<p class="ml-where">{rich(e["where"])}</p>')

    rel = [r for r in e.get("related", []) if r in term_of]
    if rel:
        links = "、".join(f'<a href="#{esc(r)}">{esc(term_of[r])}</a>' for r in rel)
        p.append(f'<p class="ml-rel">相关：{links}</p>')

    p.append('</article>')
    return "\n      ".join(p)


def build() -> str:
    term_of = {e["id"]: e["term"] for e in ENTRIES}
    counts = {t: sum(1 for e in ENTRIES if e.get("topic") == t) for t, _ in TOPICS}

    p = ['<main class="page container">']
    p.append('  <p class="eyebrow">MATH NOTES</p>')
    p.append('  <h1>数学资源库</h1>')
    p.append('  <p class="ml-lead">把做研究时反复要查的概念、符号和公式集中放在这里。'
             '每条只讲三件事：<strong>它是什么</strong>、<strong>公式长什么样</strong>、'
             '<strong>容易在哪里想错</strong>，最后一句说明它在你手上的工作里出现在哪。'
             '公式由 MathJax 渲染，可直接选中复制。</p>')

    p.append('  <div class="ml-bar">')
    p.append('    <input id="ml-q" type="search" placeholder="搜索术语、符号、解释…" '
             'aria-label="搜索" autocomplete="off">')
    p.append('    <div class="filters" role="group" aria-label="主题筛选">')
    p.append(f'      <button class="filter active" type="button" data-ml-topic="all">'
             f'全部 {len(ENTRIES)}</button>')
    for tid, name in TOPICS:
        p.append(f'      <button class="filter" type="button" data-ml-topic="{esc(tid)}">'
                 f'{esc(name)} {counts[tid]}</button>')
    p.append('    </div>')
    p.append('  </div>')
    p.append('  <p class="ml-count" id="ml-count"></p>')
    p.append('  <p class="ml-nohit" id="ml-nohit" hidden>没有匹配的条目，换个关键词试试。</p>')

    p.append('  <div class="ml-list" id="ml-list">')
    for tid, _name in TOPICS:
        for e in ENTRIES:
            if e.get("topic") != tid:
                continue
            p.append('      ' + render_entry(e, term_of))
    p.append('  </div>')

    p.append('  <p class="ml-meta">本页由 <code>math/generate_math.py</code> 生成，'
             '内容源是 <code>math/data/library.py</code>（唯一真值）。'
             '要增删条目请改数据文件后重新生成，不要手改本页。</p>')
    p.append('</main>')

    front = ("---\n"
             "layout: default\n"
             "title: 数学资源库 | veuxuncafe\n"
             "description: 研究常用概念、符号与公式的速查库：定义、公式、常见误解，以及在偏好优化工作里的位置。\n"
             "---\n")
    return front + STYLE + "\n" + "\n".join(p) + "\n" + SCRIPT + "\n"


def check() -> list:
    """生成前的自检：id 唯一、引用存在、主题合法、无 Liquid 定界符。"""
    bad = []
    ids = [e["id"] for e in ENTRIES]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        bad.append(f"重复的 id: {dup}")
    valid_topics = {t for t, _ in TOPICS}
    for e in ENTRIES:
        if e.get("topic") not in valid_topics:
            bad.append(f"{e['id']}: 主题 {e.get('topic')!r} 不在 TOPICS 里")
        for r in e.get("related", []):
            if r not in set(ids):
                bad.append(f"{e['id']}: related 指向不存在的 id {r!r}")
        for field in ("term", "formula", "plain", "where"):
            if not e.get(field):
                bad.append(f"{e['id']}: 缺少字段 {field}")
        if "{{" in e.get("formula", "") or "{%" in e.get("formula", ""):
            bad.append(f"{e['id']}: 公式里含 Liquid 定界符")
    return bad


def math_check(page: str) -> list:
    bad = []
    if page.count("\\(") != page.count("\\)"):
        bad.append(f"行内定界符不配对: \\( x{page.count(chr(92)+'(')} / \\) x{page.count(chr(92)+')')}")
    if page.count("\\[") != page.count("\\]"):
        bad.append(f"行间定界符不配对: \\[ x{page.count(chr(92)+'[')} / \\] x{page.count(chr(92)+']')}")
    return bad


def main() -> int:
    problems = check()
    if problems:
        print("数据自检未通过：", file=sys.stderr)
        for x in problems:
            print("  -", x, file=sys.stderr)
        return 1

    page = build()

    # Liquid 会把 {{ 与 {% 当模板；宁可不写盘，也不要上线一个坏页面。
    if "{{" in page or "{%" in page:
        print("拒绝写入：输出里含 Liquid 定界符", file=sys.stderr)
        return 2

    mproblems = math_check(page)
    if mproblems:
        print("公式定界符自检未通过：", file=sys.stderr)
        for x in mproblems:
            print("  -", x, file=sys.stderr)
        return 3

    OUT.write_text(page, encoding="utf-8", newline="\n")
    n_cards = page.count('class="ml-card"')
    print(f"wrote {OUT.relative_to(REPO_ROOT)} ({len(page)} bytes, {n_cards} 条)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
