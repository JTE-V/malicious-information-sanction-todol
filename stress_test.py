#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对拍器 (stress test) — 自己找错用的利器 (离线可用, 不依赖AI)
原理: 你的解 vs 暴力解(慢但保证对) → 随机数据 → 找出不一样的输入
用法:  python stress_test.py

你需要准备3个文件(同目录):
  gen.py     — 随机数据生成器(打印到 stdout)
  brute.py   — 暴力解(慢但一定对)
  mine.py    — 你的解(待检验)
"""
import subprocess, sys, random, os

N_TESTS = 200          # 测多少组
TIMEOUT = 5            # 每组时限(秒)

def run(script, inp):
    try:
        r = subprocess.run([sys.executable, script], input=inp,
                           capture_output=True, text=True, timeout=TIMEOUT)
        return r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return "<TIMEOUT>", ""

def main():
    if not all(os.path.exists(f) for f in ("gen.py","brute.py","mine.py")):
        print("缺文件! 需要同目录下有 gen.py / brute.py / mine.py")
        print("""
【模板】
gen.py (生成器):
    import random
    n = random.randint(1, 10)
    print(n)
    print(*[random.randint(1,100) for _ in range(n)])

brute.py (暴力解):
    import sys
    data = sys.stdin.read().split()
    # ...一定能过的写法...
    print(ans)

mine.py (你的解):
    # 你的代码
""")
        return
    for t in range(1, N_TESTS+1):
        inp, _ = run("gen.py", "")
        a, ea = run("brute.py", inp)
        b, eb = run("mine.py", inp)
        if a != b:
            print(f"❌ 发现不一致 (第{t}组)")
            print("--- 输入 ---"); print(inp)
            print("--- 暴力解输出 ---"); print(a)
            print("--- 你的解输出 ---"); print(b)
            if eb: print("--- 你的报错 ---"); print(eb[:400])
            return
    print(f"✅ {N_TESTS} 组全部一致 (你的解在这批数据上没问题)")

if __name__ == "__main__":
    main()
