#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逆向导构消元 (Reverse-Guided Structural Elimination) — 通用版
核心: 从"整体统计异常"反推"局部缺失/错误"的位置

用法:
  python reverse_locate.py zeros.txt          # 零点数据找漏检
  python reverse_locate.py data.csv --col 3   # 数值列找异常/缺失

原理:
  1. 建立"期望趋势"(局部平滑/理论主项)
  2. 算残差 → 找超阈值的段(异常)
  3. 在异常段内细查(间隔/密度) → 定位缺失点
"""
import sys, pathlib, numpy as np

def load_numbers(path, col=None):
    vals = []
    for ln in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        try:
            if col is not None:
                parts = ln.replace(",", " ").split()
                vals.append(float(parts[col]))
            else:
                vals.append(float(ln))   # 整行须为数字
        except (ValueError, IndexError):
            pass
    return np.array(vals)

def locate_gaps(x, label="数据"):
    """从间隔异常反推缺失位置"""
    if len(x) < 10:
        print("数据太少"); return
    d = np.diff(x)
    # 局部期望间隔(小窗口滑动中位数 — 应对"间隔随t单调变化")
    w = 50
    exp = np.array([np.median(d[max(0,i-w):i+w+1]) for i in range(len(d))])
    ratio = d/exp
    idx = np.where(ratio > 2.5)[0]   # 间隔超期望2.5倍 = 可疑缺失
    print(f"=== 逆向导构消元: {label} ===")
    print(f"样本: {len(x)} | 局部期望间隔(中位): {np.median(exp):.4f}")
    print(f"可疑缺失点: {len(idx)} 处")
    for i in idx[:15]:
        miss = int(round(ratio[i])) - 1
        print(f"  x≈{x[i]:.4f}: 间隔{d[i]:.4f}(期望{exp[i]:.4f}, {ratio[i]:.1f}倍)"
              f" → 疑似缺 {miss} 个")
    print(f"\n结论: {'发现缺口(建议细查)' if len(idx) else '间隔均匀, 无缺口'}")
    return idx

def locate_outliers(x, label="数据"):
    """从残差反推异常点"""
    if len(x) < 20:
        print("数据太少"); return
    # 局部均值趋势
    w = max(5, len(x)//30)
    trend = np.convolve(x, np.ones(w)/w, mode="same")
    resid = x - trend
    sd = np.std(resid)
    idx = np.where(np.abs(resid) > 4*sd)[0]
    print(f"=== 异常定位: {label} ===")
    print(f"残差std={sd:.4f} | 超4σ异常点: {len(idx)} 处")
    for i in idx[:15]:
        print(f"  #{i} x={x[i]:.4f} (残差{resid[i]:+.4f}, {resid[i]/sd:+.1f}σ)")



def locate_steps(x, label="数据", win=10000, jump=-1.5):
    """累积偏差台阶法(最准): 找"一步跳"而非"缓变"
    —— 适用于"累积型"数据(计数/零点/事件流)
    思路: 自然波动是小步(±0.5); 缺失会让累积量"一步跳"
    """
    if len(x) < win*2:
        print(f"{label}: 数据不足(需>{win*2})"); return
    vals=[]
    for n in range(win, len(x)+1, win):
        vals.append((n, x[n-1], n))     # (n, t, 累积计数)
    print(f"=== 累积台阶法: {label} ===")
    print(f"{'n':>9}{'Δcount':>9}{'Δ/win':>9}")
    prev=None
    susp=[]
    for n, t, c in vals:
        if prev is not None:
            d = c-prev
            rate = d/win
            mark = ""
            if rate < 0.90:              # 该段计数率明显低于1(应为1)
                mark = " ← 疑似缺失"
                susp.append(n)
            print(f"{n:>9}{d:>9}{rate:>9.3f}{mark}")
        prev=c
    print("可疑段: " + str(len(susp)) + " 处 " + str(susp[:10]))
    print("判读: 计数率恒为1是正常; 明显<1 = 该段有缺失")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit()
    path = sys.argv[1]
    col = None
    if "--col" in sys.argv:
        col = int(sys.argv[sys.argv.index("--col")+1])
    x = np.sort(load_numbers(path, col))
    locate_gaps(x, pathlib.Path(path).name)
    print()
    locate_outliers(x, pathlib.Path(path).name)
