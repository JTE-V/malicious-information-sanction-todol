#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRC 信息收集 v2 — 只读GET探测 + 软404自动识别
用法: python src_recon.py https://target
红线: 仅用于 SRC 授权范围内目标; 只读GET
改进(2026-09-12): 加内容hash软404检测(对付SPA/前端路由假阳性)
"""
import sys, urllib.request, urllib.error, hashlib, concurrent.futures, ssl, random, string

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0"}

PATHS = [
    "/.git/config", "/.git/HEAD", "/.svn/entries", "/.hg/hgrc",
    "/www.zip", "/web.zip", "/backup.zip", "/backup.sql", "/db.sql",
    "/index.php.bak", "/index.php~", "/index.jsp.bak", "/wwwroot.rar",
    "/robots.txt", "/sitemap.xml", "/phpinfo.php", "/info.php",
    "/config.php.bak", "/config.inc.php", "/db.ini", "/.env",
    "/WEB-INF/web.xml", "/.DS_Store", "/crossdomain.xml",
    "/admin/", "/manage/", "/login", "/admin/login.php",
    "/log/", "/logs/", "/access.log", "/error.log",
    "/uploads/", "/upload/", "/files/", "/data/", "/temp/",
]

def fetch(url, want_body=True, maxb=4096):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=10, context=ctx)
        return (r.status, r.read(maxb))
    except urllib.error.HTTPError as e:
        return (e.code, b"")
    except Exception:
        return None

def main():
    if len(sys.argv) < 2:
        print("用法: python src_recon.py https://target")
        return
    base = sys.argv[1].rstrip("/")
    print(f"=== 信息收集: {base} ===\n")

    # 1) 软404基线: 3个随机路径
    print("[1] 建立软404基线(3个随机路径)...")
    soft = set()
    for _ in range(3):
        rp = "/" + "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        r = fetch(base + rp)
        if r:
            soft.add((r[0], hashlib.md5(r[1]).hexdigest()))
            print(f"    {rp[:16]} → [{r[0]}] {len(r[1])}B")
    if len(soft) == 1:
        print("    ⚠️ 该站疑似 SPA/前端路由(所有路径同响应) → 路径探测可能无效")
    print()

    # 2) 探测
    print(f"[2] 探测 {len(PATHS)} 个敏感路径...")
    hits = []
    def probe(p):
        r = fetch(base + p)
        if not r:
            return None
        code, body = r
        if (code, hashlib.md5(body).hexdigest()) in soft:
            return (p, 0, 0, b"[SOFT-404]", True)   # 软404
        return (p, code, len(body), body[:120], False)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(probe, PATHS):
            if not r:
                continue
            p, code, n, head, is_soft = r
            if is_soft:
                continue
            mark = "🔴" if code == 200 and n > 0 else "🟡"
            print(f"  {mark} [{code}] {base}{p} ({n}B)")
            if code == 200 and n > 0 and head:
                print(f"        {head.decode('utf-8','ignore').replace(chr(10),' ')[:90]}")
            hits.append((base + p, code))

    print(f"\n[3] 真命中 {len(hits)} 个")
    if not hits:
        print("    → 无敏感文件泄露(此站该方向干净)")
        print("    → 下一步: 若是SPA, 测API端点; 或换目标(传统网站更易出洞)")
    print("    提醒: 200=可访问(看内容确认) / 401,403=存在但需权限")

if __name__ == "__main__":
    main()
