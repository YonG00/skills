#!/usr/bin/env python3
"""仓库自检：Markdown 渲染缺陷 / 内部链接 / 提示词与 SKILL 的同步。

用法：
    python3 scripts/check.py          # 全部检查
    python3 scripts/check.py render   # 只查渲染缺陷
    python3 scripts/check.py links    # 只查链接
    python3 scripts/check.py sync     # 只查提示词同步

退出码：0 = 全部通过；1 = 有失败项。

为什么要这个脚本：
  1. **CJK 加粗渲染**——`**核心问题：**既然` 这类写法在多数 Markdown 渲染器里
     不会变粗，而是原样显示星号。原因：闭合的 `**` 前面是标点、后面紧跟中日韩
     文字时，不满足 CommonMark 的"右翼"条件。这个错误光靠肉眼很难发现，
     本仓库已经反复犯过 4 次。
  2. **提示词过期**——`prompts/*.md` 是各自 `SKILL.md` 的派生副本。改了 skill
     忘了改提示词不会报任何错，只会让模型悄悄按旧规则走。
  3. **内部链接**——文件移动后容易留下死链。
"""

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ─────────────────────────── 通用 ───────────────────────────

def iter_md():
    """所有受检的 markdown 文件（跳过 .git 等）。"""
    return sorted(
        p for p in ROOT.rglob("*.md")
        if ".git" not in p.parts and "node_modules" not in p.parts
    )


def strip_code_context(text: str) -> str:
    """去掉围栏代码块与行内代码，保留行号（逐行处理时用不到，这里给整段用）。"""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def is_punct(ch: str) -> bool:
    """Unicode 标点或符号（CommonMark 的 punctuation 定义含 P* 与 S*）。"""
    return unicodedata.category(ch)[0] in ("P", "S")


# ─────────────────── 检查 1：CJK 加粗渲染缺陷 ───────────────────

BOLD = re.compile(r"\*\*([^*\n]+?)\*\*")


def check_render(verbose: bool = True) -> list[str]:
    """闭合的 `**` 前是标点、后紧跟非空白非标点时，无法闭合 → 原样显示星号。

    需排除两类"看起来一样但没问题"的情况：
      · 开标记（`。**核心…` 里的 `**` 是开标记，本来就合法）
      · 代码上下文（围栏块里展示反例是**故意的**）
    """
    bad: list[str] = []
    for path in iter_md():
        in_fence = False
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.match(r"^\s*```", raw):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            line = re.sub(r"`[^`\n]*`", "", raw)  # 行内代码内的字面量不算
            for m in BOLD.finditer(line):
                inner = m.group(1)
                nxt = line[m.end():m.end() + 1]
                if not nxt or not inner:
                    continue  # 行尾 = 后面是换行（空白），安全
                if is_punct(inner[-1]) and not nxt.isspace() and not is_punct(nxt):
                    bad.append(
                        f"{path.relative_to(ROOT)}:{lineno}  "
                        f"…{line[max(0, m.start() - 10):m.end() + 8]}…"
                    )
    if verbose:
        print(f"[render] 检查 {len(list(iter_md()))} 个文件")
        for b in bad:
            print(f"  ✗ {b}")
        if bad:
            print("   修法：闭合 `**` 后紧跟中文时补一个空格")
        else:
            print("  ✓ 无 CJK 加粗渲染缺陷")
    return bad


# ─────────────────────── 检查 2：内部链接 ───────────────────────

LINK = re.compile(r"\]\(([^)#]+?\.md)\)")


def check_links(verbose: bool = True) -> list[str]:
    bad: list[str] = []
    for path in iter_md():
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                bad.append(f"{path.relative_to(ROOT)} -> {target}")
    if verbose:
        print(f"[links] 检查 {len(list(iter_md()))} 个文件")
        for b in bad:
            print(f"  ✗ {b}")
        if not bad:
            print("  ✓ 内部链接全部可解析")
    return bad


# ───────────────── 检查 3：提示词 ↔ SKILL 同步 ─────────────────

# 每份提示词必须出现的关键词，对应 SKILL.md 里的硬规则。
# 提示词改了也要同步更新这里；关键词缺失 = 提示词落后于 skill。
SYNC_RULES = {
    "prompts/technical-course-private-tutor.md": [
        "复合疑问", "拍点计数", "缺一不可", "小检查",
        "高中生", "补一个空格", "标签行",
    ],
    "prompts/conversation-synthesis.md": [
        "判断变化", "守恒", "以什么形式进", "表格保留",
        "作者提示语", "第一人称", "没必要结尾升级", "不强制", "缺来源",
    ],
    "prompts/zhihu-question-mining.md": [
        "转写核对", "存疑则合", "占位标签", "没说过",
        "一个核心矛盾", "我看到", "具体对象", "再拆",
    ],
}

# 每个 skill 目录至少要有这些文件
REQUIRED = {
    "technical-course-private-tutor": [
        "SKILL.md", "README.md", "CHANGELOG.md",
        "references/section-splitting.md",
    ],
    "conversation-synthesis": [
        "SKILL.md", "README.md", "CHANGELOG.md",
        "references/conversation-to-outline.md",
    ],
    "zhihu-question-mining": [
        "SKILL.md", "README.md", "CHANGELOG.md",
        "references/topic-splitting.md", "references/transcript-fidelity.md",
    ],
}


def check_sync(verbose: bool = True) -> list[str]:
    bad: list[str] = []
    if verbose:
        print("[sync] 提示词关键词")
    for rel, keywords in SYNC_RULES.items():
        path = ROOT / rel
        if not path.exists():
            bad.append(f"{rel} 不存在")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [k for k in keywords if k not in text]
        if missing:
            bad.append(f"{rel} 缺少关键词：{missing}")
            if verbose:
                print(f"  ✗ {rel} → 缺 {missing}")
        elif verbose:
            print(f"  ✓ {rel}")

    if verbose:
        print("[sync] skill 目录完整性")
    for skill, files in REQUIRED.items():
        for f in files:
            if not (ROOT / skill / f).exists():
                bad.append(f"{skill}/{f} 缺失")
                if verbose:
                    print(f"  ✗ {skill}/{f} 缺失")
    if verbose and not any("缺失" in b for b in bad):
        print("  ✓ 各 skill 目录必需文件齐全")
    return bad


# ─────────────────────────── 入口 ───────────────────────────

def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    results: list[str] = []
    if which in ("all", "render"):
        results += check_render()
    if which in ("all", "links"):
        results += check_links()
    if which in ("all", "sync"):
        results += check_sync()

    print()
    if results:
        print(f"FAILED — {len(results)} 项")
        return 1
    print("ALL PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
