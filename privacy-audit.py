#!/usr/bin/env python3
"""发布前隐私审计：确认公开仓库不含真实项目/人员等敏感词。

用法（仓库根目录执行）:
    python3 privacy-audit.py
    python3 privacy-audit.py --repo /path/to/clone

行为:
  1. FAIL(退出码1): 任一 blocklist 词命中 git 已跟踪文件（词条支持 `exact:` 前缀做整词/整串精确匹配，防"小张"类常见字误报）
  2. FAIL(退出码1): blocklist 文件本身被 git 跟踪（防泄密清单自己先被 commit 上去）
  3. INFO: 报告 6 位以上小数坐标出现位置（行政区中心等公开数据允许，人工确认）

blocklist 格式（每行一个词，`#` 注释，`exact:` 前缀=词边界整词匹配，前后不得是词字符/汉字）:
    项目甲          # 子串模式（默认）
    exact:小李      # 整词模式：命中"小李，"、"小李 你好"，不命中"小李子词典"
"""
import argparse, os, re, subprocess, sys

BLOCKLIST = ".private-blocklist.txt"

def git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    args = ap.parse_args()
    root = os.path.abspath(args.repo)

    # 1) blocklist 文件自身必须不被跟踪
    tracked_bl = git(root, "ls-files", "--error-unmatch", BLOCKLIST).returncode == 0
    if tracked_bl:
        print(f"FAIL: {BLOCKLIST} 已被 git 跟踪 — 泄密清单本身入库，立即 git rm --cached")
        sys.exit(1)

    if not os.path.exists(os.path.join(root, BLOCKLIST)):
        print(f"SKIP: 未找到 {BLOCKLIST}，跳过词表检查（建议创建，参考脚本头注释格式）")
        sys.exit(0)

    # 2) 读词表
    exacts, substrings = [], []
    for line in open(os.path.join(root, BLOCKLIST), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"): continue
        (exacts if line.startswith("exact:") else substrings).append(line.removeprefix("exact:"))

    # 3) 用 git grep 只扫已跟踪文件（.git/ 与未跟踪文件天然排除）
    hits = []          # (词, 文件:行)
    coord_info = []    # 高精度坐标 INFO
    files = git(root, "ls-files").stdout.splitlines()
    for f in files:
        try:
            content = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for w in exacts:
            # 词边界整词匹配：前后不得是词字符（含汉字），避免"小叶"命中"小叶紫檀"类误报
            pat = re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)")
            for i, ln in enumerate(content.splitlines(), 1):
                if pat.search(ln): hits.append((f"exact:{w}", f"{f}:{i}"))
        for w in substrings:
            if w in content:
                for i, ln in enumerate(content.splitlines(), 1):
                    if w in ln: hits.append((w, f"{f}:{i}"))
        for i, ln in enumerate(content.splitlines(), 1):
            # 中国经度 73-135 为三位整数（如 120.130396），须允许 2-3 位整数部分
            if re.search(r"[0-9]{2,3}\.[0-9]{6,}\s*,\s*[0-9]{2,3}\.[0-9]{6,}", ln):
                coord_info.append(f"{f}:{i}  {ln.strip()[:60]}")

    # 4) 汇总
    ok = True
    if hits:
        ok = False
        print(f"FAIL: 发现 {len(hits)} 处敏感词命中（已跟踪文件）:")
        for w, loc in sorted(set(hits)): print(f"  [{w}] {loc}")
    else:
        print(f"PASS: 词表 {len(exacts)+len(substrings)} 项（精确{len(exacts)}/子串{len(substrings)}）零命中")

    if coord_info:
        print(f"INFO: {len(coord_info)} 处高精度坐标（行政区中心等公开数据可放行，需人工确认）:")
        for c in coord_info: print(f"  {c}")
    else:
        print("INFO: 无高精度坐标")

    print(f"\n结果: {'全部通过' if ok and not tracked_bl else '存在违规'}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()