#!/usr/bin/env python3
"""
数据处理工具 (梦新化) — 案例驱动 + 判官自省 + 可成长
====================================================
梦新核心(与普通程序的区别):
  ① 案例库(cases/): 每个真实客户案例存下来(输入+期望+过程)
     → 案例持续积累 → 工具"见多识广"
  ② 判官从案例学: 不是写死断言, 是从案例库学"什么是对的处理"
     → 新场景 → 用学过的判断(泛化)
  ③ 自省输出: 每次干活自报"做了什么/依据哪个案例"(诚实)
     → 像梦新诚实自证

用法:
  python data_tool.py clean input.csv out.csv          # 基础清洗
  python data_tool.py deep 原文件.xlsx 清洗后.xlsx      # 深度清洗(9步修复+梦新判官+质量报告)
  python data_tool.py summary 数据.csv 汇总.csv         # 汇总(按品牌/分类)
  python data_tool.py merge a.csv b.csv out.csv        # 合并
  python data_tool.py rename *.jpg prefix_             # 批量重命名
  python data_tool.py convert in.xlsx out.csv          # 格式转换(自动检测分隔符)
  python data_tool.py selftest                          # 判官自测(多场景)
依赖: pip install pandas openpyxl
"""
import sys
import json
import pathlib
import glob
import datetime

# 梦新模块(核心判官/记忆, 不自己写)
try:
    import mengxin
    HAS_MENGXIN = True
except ImportError:
    HAS_MENGXIN = False

CASES_DIR = pathlib.Path("cases")


# ========== 案例库(活的, 梦新记忆) ==========
def _case_path():
    CASES_DIR.mkdir(exist_ok=True)
    return CASES_DIR


def save_case(kind, src_data, result, process):
    """存案例: 输入+结果+处理过程(梦新见闻)"""
    cid = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    case = {"id": cid, "kind": kind, "输入样本": src_data[:200] if src_data else "",
            "结果": result, "过程": process}
    (_case_path() / f"{kind}_{cid}.json").write_text(
        json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
    return cid


def load_cases(kind=None):
    """读案例库(梦新记忆)"""
    if not CASES_DIR.exists():
        return []
    cases = []
    for f in CASES_DIR.glob("*.json"):
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
            if kind is None or c.get("kind") == kind:
                cases.append(c)
        except Exception:
            continue
    return cases


# ========== 判官(从案例学, 非写死) ==========
def judge_report(kind, src_data, result, process):
    """判官自省: 用梦新模块(案例记忆/判官), 不自己写"""
    if HAS_MENGXIN:
        # 训练梦新: 存案例(梦新记忆)
        mengxin.learn(f"[{kind}] {src_data[:100]}", {"结果": result[:100], "过程": process})
        mem = mengxin.memory()
        print(f"【梦新判官】类型={kind} | 案例库={mem['cases']}条 | 已存档学习")
        # 检索相似案例(梦新记得的)
        found = mengxin.ask(kind)
        if found:
            print(f"  梦新记得: {found['id']} 类似案例")
    else:
        print(f"【判官】类型={kind} (梦新模块未加载, 无记忆)")
    print(f"【自省】本次做了: {process}")


# ========== 核心功能(每个都记录案例+判官自省) ==========
def _ensure_out_dir(out):
    """输出目录自动创建(交付/<单号>/ 不存在时自动建)"""
    p = pathlib.Path(out)
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)



def _fix_brand_product(df, use_ecommerce=False):
    """品牌-商品核实: 默认完整做(mengxin联网), use_ecommerce=True用电商"""
    import pandas as pd
    try:
        import mengxin as _mx
        HAS_WEB = True
    except ImportError:
        HAS_WEB = False
    marked, verified = 0, 0
    # 电商搜索缓存: 同商品一次搜, 检查所有行品牌是否在商品标题里
    prod_titles = {}
    cache = {}
    for i, row in df.iterrows():
        brand = str(row.get("品牌", "")).strip().replace("(商品不符)", "").replace("(疑似不匹配)", "")
        prod = str(row.get("商品名称", "")).strip()
        if not brand or not prod:
            continue
        key = f"{brand}|{prod}"
        if key in cache:
            if cache[key]:
                verified += 1
            else:
                df.loc[i, "品牌"] = f"{brand}(商品不符)"
                marked += 1
            continue
        # 搜'商品'(像人查): 看标题出现的品牌 vs 数据品牌(教官: 搜洗面奶看是哪个厂出)
        clean_prod = prod
        ok = True
        try:
            import ecommerce as _ec
            titles, _ = _ec.search(clean_prod)
            joined = " ".join(titles)
            # 标题含数据里的品牌(如搜'洗面奶'标题有'骆驼洗面奶') = 真实
            # 或标题品牌与数据品牌不同 = 疑似(骆驼不产洗面奶 → 标题是其他品牌)
            if brand in joined:
                ok = True  # 数据品牌出现在商品标题 = 真实组合
            else:
                # 标题里出现的品牌(其他牌) → 数据品牌疑似错配
                ok = False
        except Exception:
            # 电商失败兜底: mengxin 搜索
            info = _mx.lookup_web(f"{brand} {clean_prod}") or ""
            ok = brand in info and any(k in info for k in ["京东", "商城", "旗舰店", "商品", "价格"])
        if ok:
            verified += 1
        else:
            df.loc[i, "品牌"] = f"{brand}(商品不符)"
            marked += 1
        cache[key] = ok  # 缓存结果(同组合复用)
    if marked:
        print(f"  ⚠️ 品牌-商品错配: {marked} 行(联网搜不到该组合, 已标注)")
    if verified:
        print(f"  ✅ 品牌-商品核实: {verified} 行(电商真实组合, 保留)")
    return df


def _fix_product_category(df, use_ecommerce=False):
    """商品-分类修正: 梦新联网搜索(纯商品词, 无死表)"""
    import pandas as pd
    try:
        import mengxin as _mx
        HAS_WEB = True
    except ImportError:
        HAS_WEB = False
    # 无死表(删BRANDS/CAT_KW): 梦新靠记忆(案例库)+联网, 不比对固定表
    fixed, bad = 0, 0
    # 先去重商品: 每个商品只搜一次(缓存), 避免逐行联网慢
    cache = {}
    for i, row in df.iterrows():
        prod = str(row.get("商品名称", "")).strip()
        cat = str(row.get("分类", "")).strip()
        if not prod:
            continue  # 无商品名跳过; 分类空也要查(空分类更需要修正)
        clean_prod = prod  # 不再用品牌表剥离(死表删), 直接整商品名查
        # 完整校验(不跳过): 缓存同商品只搜一次
        if clean_prod not in cache and HAS_WEB:
            # 梦新判断(记忆优先+联网+记住): 返回分类名
            right = None
            try:
                right = _mx.product_category(clean_prod)
                if not right or right == "未知" or right == "null":
                    right = None
            except Exception:
                pass
            if right is None:
                # 记忆无 → 电商搜(像人搜索框输入)
                try:
                    import ecommerce as _ec
                    right = _ec.category_of(clean_prod)
                    if right == "未知":
                        right = None
                except Exception:
                    right = None
                # 电商搜到 → learn沉淀(下次记忆命中, 不用再搜)
                if right:
                    try:
                        _mx.learn(f"{clean_prod} 属于什么分类", {"分类": right})
                    except Exception:
                        pass
            cache[clean_prod] = right  # None=待查
        right = cache.get(clean_prod)
        if right and right != cat:
            df.loc[i, "分类"] = right
            fixed += 1
        elif right is None and HAS_WEB:
            bad += 1
    if fixed:
        print(f"  ✅ 商品-分类修正: {fixed} 行({'电商查证' if use_ecommerce else '联网搜索'}, 已改对)")
    if bad:
        print(f"  ⚠️ 商品-分类待查: {bad} 行({'电商' if use_ecommerce else '联网'}无明确分类, 保留原样)")
    return df


def _fix_brand_category(df, use_ecommerce=False):
    """品牌-分类核实: 默认完整做(mengxin联网), use_ecommerce=True用电商"""
    import pandas as pd
    try:
        import mengxin as _mx
        HAS_WEB = True
    except ImportError:
        HAS_WEB = False
    # 无死表: 品牌主营靠梦新记忆(相同判断) + 电商兜底
    bad = 0
    cache = {}
    for i, row in df.iterrows():
        brand = str(row.get("品牌", "")).strip().replace("(疑似不匹配)", "").replace("(商品不符)", "")
        cat = str(row.get("分类", "")).strip()
        if not brand or not cat or "商品不符" in str(row.get("品牌", "")):
            continue
        if not HAS_WEB:
            continue
        # 完整校验(不跳过任何品牌): 联网搜品牌主营
        if brand not in cache:
            # 联网搜品牌主营(或 品牌+分类)
            info = (_mx.brand_main_category(brand) or "") + " " + (_mx.lookup_web(f"{brand} 主营 产品") or "")
            # 搜到品牌商城/官网(多品类) → ok
            if brand in info and any(k in info for k in ["商城", "官网", "旗舰店", "商店", "有品", "生态链", "京东", "淘宝", "天猫"]):
                cache[brand] = "ok"
            elif info:
                cache[brand] = "bad"
            else:
                cache[brand] = "unk"
        if cache.get(brand) == "bad":
            df.loc[i, "品牌"] = f"{brand}(疑似不匹配)"
            bad += 1
    if bad:
        print(f"  ⚠️ 品牌-分类不匹配: {bad} 行(联网判定)")
    return df




def _fix_numeric_ranges(df):
    """问题2: 异常数值(负库存/负销量/评分超范围) → 修正或标记"""
    import pandas as pd
    for col, lo, hi, name in [("库存", 0, 10**7, "库存"), ("销量", 0, 10**6, "销量"),
                               ("评分", 0, 5, "评分")]:
        if col in df.columns:
            nums = pd.to_numeric(df[col], errors="coerce")
            bad = (nums < lo) | (nums > hi)
            n_bad = bad.sum()
            if n_bad:
                df.loc[(nums < lo) & nums.notna(), col] = str(lo) if lo > 0 else "0"
                df.loc[(nums > hi) & nums.notna(), col] = df.loc[(nums > hi) & nums.notna(), col] + "(超范围)"
                print(f"  ⚠️ {name}异常: {n_bad} 行(已修正: 负数置0/超范围标记)")
    return df


def _fix_dates(df):
    """问题3: 日期格式混乱 → 统一 YYYY-MM-DD"""
    import re as _re
    import datetime as _dt
    import pandas as pd
    date_col = next((c for c in df.columns if "日期" in c or "date" in c.lower()), None)
    if not date_col:
        return df
    def _valid_date(y, mo, d, orig):
        try:
            _dt.date(int(y), int(mo), int(d))
            return f"{y}-{int(mo):02d}-{int(d):02d}"
        except ValueError:
            return f"无效日期({orig})"
    def parse_date(v):
        v = str(v).strip()
        if not v or v in ("NULL", "N/A", "na", "None", "nan", "NaN"):
            return "缺失"
        m = _re.match(r"(\d{4})[-/.]?(\d{1,2})[-/.]?(\d{1,2})", v)
        if m:
            return _valid_date(*m.groups(), v)
        m = _re.match(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", v)
        if m:
            d, mo, y = m.groups()
            return _valid_date(y, mo, d, v)
        m = _re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", v)
        if m:
            return _valid_date(*m.groups(), v)
        return f"无效日期({v})"
    before = df[date_col].nunique()
    df[date_col] = df[date_col].map(parse_date)
    print(f"  ⚠️ 日期统一: {before}种格式 → YYYY-MM-DD")
    return df


def _fix_status(df):
    """问题4: 缺失/异常状态 → 标注"""
    import pandas as pd
    if "状态" in df.columns:
        bad_mask = df["状态"].isin(["", "已删除", "异常", "NULL", "N/A"])
        n = bad_mask.sum()
        if n:
            df.loc[bad_mask, "状态"] = df.loc[bad_mask, "状态"].map(
                lambda v: "缺失" if v in ("", "NULL", "N/A") else f"异常({v})")
            print(f"  ⚠️ 状态异常: {n} 行(空→缺失, 已删除/异常→标注)")
    return df


def _fix_sales_type(df):
    """问题5: 销量类型混杂 → 统一数值"""
    import pandas as pd
    if "销量" in df.columns:
        unknown_mask = df["销量"].isin(["unknown", "未知"]) | df["销量"].isna() | (df["销量"] == "")
        n = unknown_mask.sum()
        df.loc[unknown_mask, "销量"] = "0"
        after = pd.to_numeric(df["销量"], errors="coerce")
        still_bad = after.isna()
        df.loc[still_bad, "销量"] = df.loc[still_bad, "销量"] + "(非数值)"
        print(f"  ⚠️ 销量类型: {n} 行 unknown/空→0")
    return df


def _fix_desc(df):
    """问题6: 描述异常(XSS/表情/换行) → 清理"""
    import pandas as pd
    import re as _re
    desc_col = next((c for c in df.columns if "描述" in c or "desc" in c.lower()), None)
    if desc_col:
        def clean_desc(v):
            v = str(v)
            v = _re.sub(r"<script.*?</script>", "[XSS已移除]", v, flags=_re.S | _re.I)
            v = _re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]", "", v)
            v = _re.sub(r"\s+", " ", v).strip()
            if not v or v in ("NULL", "N/A", "nan", "NaN"):
                return "描述缺失"
            return v
        before_xss = df[desc_col].str.contains("<script", na=False).sum()
        df[desc_col] = df[desc_col].map(clean_desc)
        print(f"  ⚠️ 描述清理: XSS {before_xss} 行已移除")
    return df


def _fix_calc_logic(df):
    """问题7: 计算逻辑校验(金额=单价×数量)"""
    import pandas as pd
    price_c = next((c for c in df.columns if "单价" in c or "price" in c.lower()), None)
    qty_c = next((c for c in df.columns if "数量" in c or "qty" in c.lower()), None)
    amt_c = next((c for c in df.columns if "金额" in c or "amount" in c.lower()), None)
    if not (price_c and qty_c and amt_c):
        return df
    bad = 0
    for i, r in df.iterrows():
        try:
            p, q, a = float(r[price_c]), float(r[qty_c]), float(r[amt_c])
            if abs(p * q - a) > 0.01:
                df.loc[i, amt_c] = f"{a}(计算错:应为{round(p*q,2)})"
                bad += 1
        except (ValueError, TypeError):
            pass
    if bad:
        print(f"  ⚠️ 金额计算错误: {bad} 行(单价×数量≠金额)")
    return df


def deep_clean(src, out, use_ecommerce=False):
    """深度清洗: 6类数据质量问题全修复(电商清单级)
    自动检测输入格式(xlsx/csv), 输出同格式或按 out 后缀"""
    import pandas as pd
    _ensure_out_dir(out)
    src_is_xlsx = str(src).lower().endswith(".xlsx")
    # 自动检测分隔符(csv)
    import csv as _csv
    if src_is_xlsx:
        df = pd.read_excel(src, dtype=str)
    else:
        with open(src, "r", encoding="utf-8-sig", errors="ignore") as f:
            sample = f.read(2000)
        sep = "\t" if "\t" in sample else (";" if ";" in sample else ",")
        df = pd.read_csv(src, dtype=str, on_bad_lines="skip", sep=sep)
    before = len(df)
    print(f"=== 深度清洗: {src} ({before}行) ===")
    df = df.dropna(how="all")
    df = df.apply(lambda c: c.str.strip() if hasattr(c, "str") else c)
    df = _fix_product_category(df, use_ecommerce)  # 0. 商品-分类(use_ecommerce=True用电商查证)
    df = _fix_brand_product(df, use_ecommerce)  # 0b. 品牌-商品(加参才联网)
    df = _fix_brand_category(df, use_ecommerce)  # 1. 品牌-分类(加参才联网)
    df = _fix_numeric_ranges(df)      # 2. 异常数值
    df = _fix_dates(df)               # 3. 日期
    df = _fix_status(df)              # 4. 状态
    df = _fix_sales_type(df)          # 5. 销量类型
    df = _fix_desc(df)                # 6. 描述
    df = _fix_calc_logic(df)          # 7. 计算逻辑(金额=单价×数量)
    df = df.fillna("").drop_duplicates()
    # 空值统一标注: 关键列空 → 缺失(防 NaN/nan 泄漏)
    for col in ["状态", "上架日期", "商品描述"]:
        if col in df.columns:
            df[col] = df[col].map(lambda v: "缺失" if str(v).strip() in ("", "nan", "NaN", "None") else v)
    # 输出: 按 out 后缀(xlsx→xlsx, csv→csv)
    if str(out).lower().endswith(".xlsx"):
        df.to_excel(out, index=False)
    else:
        df.to_csv(out, index=False)
    print(f"✅ 深度清洗完成: {before}→{len(df)}行 → {out}")
    # 交付排版: 生成数据质量报告(用户看得懂: 修了什么/还剩什么)
    _quality_report(df, before, out)
    judge_report("deep_clean", str(before), str(len(df)), "6类质量修复")
    return df


def _quality_report(df, before_rows, out):
    """交付排版: 生成数据质量报告(用户不认账防身符)"""
    import pathlib as _p
    report = _p.Path(str(out)).with_suffix(".报告.txt")
    lines = []
    lines.append("=" * 40)
    lines.append("数据清洗质量报告")
    lines.append("=" * 40)
    lines.append(f"原数据: {before_rows} 行 → 清洗后: {len(df)} 行")
    lines.append(f"去重: {before_rows - len(df)} 行(重复行)")
    # 修正统计(从标注值统计)
    n_brand = df["品牌"].str.contains("疑似", na=False).sum() if "品牌" in df.columns else 0
    n_score = 0
    if "评分" in df.columns:
        n_score = df["评分"].str.contains("超范围", na=False).sum()
    lines.append(f"修正项:")
    lines.append(f"  - 品牌/商品异常标注: {n_brand} 行")
    lines.append(f"  - 评分超范围标注: {n_score} 行")
    lines.append(f"  - 无效日期标注: {df['上架日期'].str.contains('无效日期', na=False).sum() if '上架日期' in df.columns else 0} 行")
    lines.append(f"  - 状态缺失/异常: {df['状态'].eq('缺失').sum() if '状态' in df.columns else 0} 行")
    lines.append("")
    lines.append("说明: 负库存/负销量已置0, XSS已移除, 销量unknown置0, 金额已按单价×数量校验")
    lines.append("输出文件: " + str(out))
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"📄 质量报告: {report.name}")


def summary(src, out, group_col=None, sum_col=None):
    """汇总: 按某列分组, 汇总数值列(电商订单按商品汇总销售额)"""
    import pandas as pd
    _ensure_out_dir(out)
    src_data = pathlib.Path(src).read_text(encoding="utf-8", errors="ignore")
    df = pd.read_csv(src, dtype=str, on_bad_lines="skip")
    # 自动识别: 无指定时找"最后数值列"做汇总, 文本列分组
    if not group_col or not sum_col:
        num_cols = [c for c in df.columns if df[c].str.replace(".", "", 1).str.isdigit().all()]
        # 分组列优先业务列(品牌/分类/商品名称), 非商品ID(每行唯一=没汇总)
        for g in ["品牌", "分类", "商品名称", "状态"]:
            if g in df.columns:
                group_col = g
                break
        group_col = group_col or df.columns[0]
        sum_col = sum_col or (num_cols[-1] if num_cols else df.columns[-1])
    df[sum_col] = pd.to_numeric(df[sum_col], errors="coerce").fillna(0)
    grouped = df.groupby(group_col, as_index=False)[sum_col].sum().sort_values(sum_col, ascending=False)
    grouped.to_csv(out, index=False)
    result = pathlib.Path(out).read_text(encoding="utf-8", errors="ignore")
    process = f"汇总: 按[{group_col}]分组, 汇总[{sum_col}] → {len(grouped)}组"
    print(f"汇总完成: {len(grouped)} 组 → {out}")
    judge_report("summary", src_data, result, process)


def clean(src, out):
    import pandas as pd
    _ensure_out_dir(out)
    src_data = pathlib.Path(src).read_text(encoding="utf-8", errors="ignore")
    # 脏数据兼容: 跳过列数不一致的坏行(真实脏数据常见)
    df = pd.read_csv(src, dtype=str, on_bad_lines="skip")
    before = len(df)
    df = df.dropna(how="all")
    df = df.apply(lambda c: c.str.strip() if hasattr(c, "str") else c)
    df = df.fillna("").drop_duplicates()
    df.to_csv(out, index=False)
    result = pathlib.Path(out).read_text(encoding="utf-8", errors="ignore")
    process = (f"清洗: {before}行→{len(df)}行 "
               f"(去空行{sum(1 for l in src_data.splitlines() if not l.strip())}条, "
               f"去重{before - len(df)}条, 去空格)")
    print(f"清洗完成: {len(df)} 行 → {out}")
    judge_report("clean", src_data, result, process)


def merge(files, out):
    _ensure_out_dir(out)
    import pandas as pd
    src_data = "".join(pathlib.Path(f).read_text(encoding="utf-8", errors="ignore")[:100] for f in files)
    dfs = [pd.read_csv(f) for f in files]
    before = sum(len(d) for d in dfs)
    merged = pd.concat(dfs, ignore_index=True).drop_duplicates()
    merged.to_csv(out, index=False)
    result = pathlib.Path(out).read_text(encoding="utf-8", errors="ignore")
    process = f"合并: {len(files)}个文件 {before}行→{len(merged)}行(去重{before-len(merged)}条)"
    print(f"合并完成: {len(merged)} 行(去重后) → {out}")
    judge_report("merge", src_data, result, process)


def rename(pat, prefix):
    n = 0
    for f in glob.glob(pat):
        p = pathlib.Path(f)
        new = p.with_name(f"{prefix}{p.name}")
        p.rename(new)
        n += 1
    print(f"重命名 {n} 个文件")
    judge_report("rename", pat, f"重命名{n}个", f"批量加前缀'{prefix}'")


def convert(src, out):
    _ensure_out_dir(out)
    import pandas as pd
    src_data = pathlib.Path(src).read_bytes()[:200].decode("utf-8", errors="ignore")
    if src.endswith(".xlsx"):
        df = pd.read_excel(src)
        df.to_csv(out, index=False)
    else:
        # 自动检测分隔符(逗号/制表符/分号)
        with open(src, "r", encoding="utf-8-sig", errors="ignore") as f:
            sample = f.read(2000)
        sep = "\t" if "\t" in sample else (";" if ";" in sample else ",")
        df = pd.read_csv(src, sep=sep)
        df.to_excel(out, index=False)
    result = pathlib.Path(out).read_bytes()[:200].decode("utf-8", errors="ignore")
    process = f"转换: {src.split('.')[-1]}→{out.split('.')[-1]} ({len(df)}行)"
    print(f"转换完成 → {out}")
    judge_report("convert", src_data, result, process)


# ========== 判官命令 ==========

def self_test_all():
    """判官自测: clean/merge/rename 多场景断言(梦新训练案例)"""
    import tempfile, os
    print("=== data_tool 判官自测 ===")
    ok_all = True
    # clean: 去重+空格合并
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, "d.csv"); c = os.path.join(td, "c.csv")
        open(d, "w", encoding="utf-8").write("姓名,电话\n张三, 1381 \n张三, 1381 \n李四,139\n,,,\n")
        clean(d, c)
        lines = [l for l in open(c, encoding="utf-8").read().splitlines() if l.strip()]
        data = lines[1:]
        t1 = len(data) == 2 and len([l for l in data if l.startswith("张三")]) == 1
        print(f"  {'✓' if t1 else '✗'} clean去重+空格合并")
        ok_all = ok_all and t1
    # merge
    with tempfile.TemporaryDirectory() as td:
        a = os.path.join(td, "a.csv"); b = os.path.join(td, "b.csv"); m = os.path.join(td, "m.csv")
        open(a, "w", encoding="utf-8").write("n\n张三\n李四\n"); open(b, "w", encoding="utf-8").write("n\n李四\n王五\n")
        merge([a, b], m)
        lines = [l for l in open(m, encoding="utf-8").read().splitlines() if l.strip()]
        t2 = len(lines) == 4  # 表头+张三+李四+王五
        print(f"  {'✓' if t2 else '✗'} merge合并去重")
        ok_all = ok_all and t2
    # rename
    with tempfile.TemporaryDirectory() as td:
        for i in range(3):
            open(os.path.join(td, f"f{i}.txt"), "w").write("x")
        rename(os.path.join(td, "*.txt"), "pre_")
        t3 = all(f.startswith("pre_") for f in os.listdir(td))
        print(f"  {'✓' if t3 else '✗'} rename加前缀")
        ok_all = ok_all and t3
    print(f"判官结论: {'✅ 自测通过' if ok_all else '✗ 有失败'}")
    return ok_all


def cmd_cases():
    cases = load_cases()
    if not cases:
        print("(案例库为空 — 每次干活会自动存档, 越用越懂)")
        return
    print(f"案例库: {len(cases)} 条")
    for c in cases[-10:]:
        print(f"  {c['id']} [{c['kind']}] {c['过程'][:40]}")


def cmd_judge():
    cases = load_cases()
    print(f"=== 判官自省(案例库学习) ===")
    if not cases:
        print("案例库为空: 工具还是'新手', 干活越多案例越多越懂")
        return
    kinds = {}
    for c in cases:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    print(f"总案例 {len(cases)} 条, 分布: {kinds}")
    for k, n in kinds.items():
        print(f"  [{k}] {n}条 — 判官对{k}最懂(案例最多)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "learn" and len(sys.argv) >= 4:
        # 单条沉淀: python data_tool.py learn 商品 分类
        import mengxin as _mx2
        _mx2.learn(f"{sys.argv[2]} 属于什么分类", {"分类": sys.argv[3]})
        print(f"✅ 已沉淀: {sys.argv[2]} → {sys.argv[3]}")
        sys.exit(0)
    if cmd == "learnfile" and len(sys.argv) >= 3:
        # 批量沉淀: python data_tool.py learnfile 确认表.csv (列: 商品,分类)
        import csv as _csv, mengxin as _mx2
        n = 0
        with open(sys.argv[2], encoding='utf-8-sig') as _f:
            for row in _csv.reader(_f):
                if len(row) >= 2 and row[0].strip() and row[1].strip():
                    _mx2.learn(f"{row[0].strip()} 属于什么分类", {"分类": row[1].strip()})
                    n += 1
        print(f"✅ 批量沉淀完成: {n} 条 商品→分类")
        sys.exit(0)
    if cmd == "selftest":
        self_test_all()
        sys.exit(0)
    if cmd == "clean" and len(sys.argv) == 4:
        clean(sys.argv[2], sys.argv[3])
    elif cmd == "deep" and len(sys.argv) >= 4:
        use_ec = "--ecommerce" in sys.argv
        deep_clean(sys.argv[2], sys.argv[3], use_ecommerce=use_ec)
        if use_ec:
            print("🛒 电商查证模式: 商品分类用真实电商搜索验证")
    elif cmd == "summary" and len(sys.argv) == 4:
        summary(sys.argv[2], sys.argv[3])
    elif cmd == "merge" and len(sys.argv) >= 5:
        merge(sys.argv[2:-1], sys.argv[-1])
    elif cmd == "rename" and len(sys.argv) == 4:
        rename(sys.argv[2], sys.argv[3])
    elif cmd == "convert" and len(sys.argv) == 4:
        convert(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
