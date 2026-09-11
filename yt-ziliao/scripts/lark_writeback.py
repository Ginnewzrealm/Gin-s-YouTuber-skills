#!/usr/bin/env python3
"""lark_writeback.py — 飞书回写三段式闭环（schema 前置 → 校验 → 写入 → 回读对账）

第一性原理：对不知道 schema 的系统写数据就是猜，猜必然试错，试错必然留残骸
（payload/payload_fix/payload_n9/payload_n9b……）。本脚本把「猜-试错」结构改为
「读 schema → 本地校验 → 一次写入 → 回读 diff」，闭环不到账不许宣称写成功。

用法：
    python3 scripts/lark_writeback.py <payload.json> [--record-id recXXX]
            [--base-token X] [--table-id Y] [--dry-run]

    payload.json 形如：{"update_records": {"recXXX": {"字段名": 值}}}
    （与 lark-cli +record-batch-update 的 --json 同构，兼容历史 payload 文件）

配置发现顺序：--base-token/--table-id 参数 > 技能 config.yaml 的 pool: 段。
schema 缓存：技能目录 runtime/schema_<table_id>.json（回写前强制刷新）。

退出码：0 = 写入且回读一致；1 = 校验失败/写入失败/回读不一致；2 = 用法/配置错误。
"""
import argparse
import json
import os
import re
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

re_md_link = re.compile(r"^\[([^\]]*)\]\((https?://[^)]+)\)$")

# 飞书字段类型码（API 原生）→ (接受值形态, 说明)
TYPE_MAP = {
    1: ("text", "文本"),
    2: ("number", "数字"),
    3: ("select", "单选"),
    4: ("multi_select", "多选"),
    5: ("datetime", "日期"),
    7: ("checkbox", "复选框"),
    11: ("user", "人员"),
    13: ("phone", "电话"),
    15: ("url", "超链接"),
    18: ("link", "单向关联"),
    100: ("formula", "公式"),
    21: ("lookup", "查找引用"),
    17: ("attachment", "附件"),
}
TYPE_NAME = {v[0]: k for k, v in TYPE_MAP.items()}

# 类型名 → 校验函数（返回 None 表示通过，否则返回错误描述）
def _is_id_array(v):
    return isinstance(v, list) and all(isinstance(x, dict) and "id" in x for x in v)


def validate_value(type_code, value, options):
    t = TYPE_MAP.get(type_code, (f"unknown_{type_code}", ""))[0]
    if t == "text" or t == "phone":
        return None if isinstance(value, str) else f"应为字符串，实为 {type(value).__name__}"
    if t == "number":
        return None if isinstance(value, (int, float)) and not isinstance(value, bool) else "应为数字"
    if t == "select":
        vals = value if isinstance(value, list) else [value]
        if not all(isinstance(x, str) for x in vals):
            return "单选应为字符串或单元素字符串数组"
        if options and not set(vals) <= set(options):
            return f"选项 {set(vals) - set(options)} 不在字段定义内"
        return None
    if t == "multi_select":
        if not (isinstance(value, list) and all(isinstance(x, str) for x in value)):
            return "多选应为字符串数组"
        if options and not set(value) <= set(options):
            return f"选项 {set(value) - set(options)} 不在字段定义内"
        return None
    if t == "datetime":
        ok = isinstance(value, int) or (
            isinstance(value, str) and len(value) >= 8 and value[:4].isdigit())
        return None if ok else "应为毫秒时间戳或 'YYYY-MM-DD HH:MM' 字符串"
    if t == "checkbox":
        return None if isinstance(value, bool) else "应为 true/false"
    if t in ("user", "link"):
        return None if _is_id_array(value) else '应为 [{"id": "..."}] 结构'
    if t == "url":
        ok = isinstance(value, dict) and "link" in value and "text" in value
        return None if ok else "URL 字段应为 {'text': ..., 'link': ...} 对象"
    if t in ("formula", "lookup", "attachment"):
        return f"{t} 为系统字段，禁止写入"
    return f"未知类型码 {type_code}，拒绝猜测，请先人工确认"


def run_lark(args):
    cmd = ["lark-cli"] + args + ["--format", "json"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])} 失败: {p.stderr.strip()[:300]}")
    out = p.stdout.strip()
    return json.loads(out) if out else {}


def fetch_schema(base_token, table_id):
    data = run_lark(["base", "+field-list", "--base-token", base_token,
                     "--table-id", table_id, "--limit", "200"])
    items = data.get("data", {}).get("fields") or data.get("data", {}).get("items") or []
    schema = {}
    for f in items:
        name = f.get("name") or f.get("field_name")
        ftype = f.get("type")
        if isinstance(ftype, str):
            if ftype == "select":  # lark-cli 将单/多选都报为 select，用 multiple 区分
                ftype = 4 if f.get("multiple") else 3
            else:
                ftype = TYPE_NAME.get(ftype, ftype)
        prop = f.get("property") or {}
        opts = [o.get("name") for o in (f.get("options") or prop.get("options") or [])] or None
        schema[name] = {"type": ftype, "options": opts}
    if not schema:
        raise RuntimeError(f"field-list 返回空 schema，请检查 base_token/table_id")
    os.makedirs(os.path.join(SKILL_DIR, "runtime"), exist_ok=True)
    cache = os.path.join(SKILL_DIR, "runtime", f"schema_{table_id}.json")
    with open(cache, "w", encoding="utf-8") as fp:
        json.dump(schema, fp, ensure_ascii=False, indent=2)
    return schema


def load_config(base_token, table_id):
    if base_token and table_id:
        return base_token, table_id
    cfg_path = os.path.join(SKILL_DIR, "config.yaml")
    if os.path.exists(cfg_path):
        for line in open(cfg_path, encoding="utf-8"):
            if "base_token:" in line and not base_token:
                base_token = line.split(":", 1)[1].strip()
            if "table_id:" in line and not table_id:
                table_id = line.split(":", 1)[1].strip()
    if not base_token or not table_id:
        raise RuntimeError("缺少 base_token/table_id：传参或在 config.yaml pool: 段配置")
    return base_token, table_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("payload", help="payload.json（update_records 结构）")
    ap.add_argument("--record-id", help="单记录快捷方式（payload 里只有一条时可省略）")
    ap.add_argument("--base-token")
    ap.add_argument("--table-id")
    ap.add_argument("--dry-run", action="store_true", help="只校验不写入")
    a = ap.parse_args()

    payload = json.load(open(a.payload, encoding="utf-8"))
    records = payload.get("update_records", payload)
    if not isinstance(records, dict) or not records:
        print("payload 为空或结构不对（需要 update_records 映射）", file=sys.stderr)
        return 2
    if a.record_id and "update_records" not in payload:
        records = {a.record_id: records}

    try:
        base_token, table_id = load_config(a.base_token, a.table_id)
        schema = fetch_schema(base_token, table_id)
    except RuntimeError as e:
        print(f"❌ 配置/schema 阶段失败：{e}", file=sys.stderr)
        return 1

    # —— 阶段 2：本地校验（不过不出栈，不产生任何写入）——
    errors = []
    for rid, fields in records.items():
        for fname, val in fields.items():
            fdef = schema.get(fname)
            if not fdef:
                errors.append(f"[{rid}] 字段「{fname}」不存在于表 schema——禁止猜字段名")
                continue
            err = validate_value(fdef["type"], val, fdef["options"])
            if err:
                errors.append(f"[{rid}] 字段「{fname}」({TYPE_MAP.get(fdef['type'], ('?',))[0]}): {err}")
    if errors:
        print("❌ 校验失败（未产生任何写入），逐项修正后重跑：")
        for e in errors:
            print("  -", e)
        return 1
    print(f"✅ schema 校验通过（{sum(len(f) for f in records.values())} 字段 × {len(records)} 记录）")

    # 单选规范化：lark-cli 约定 select 收数组（单选为单元素数组），统一在此归一
    for rid, fields in records.items():
        for fname, val in fields.items():
            if schema[fname]["type"] == 3 and isinstance(val, str):
                fields[fname] = [val]

    if a.dry_run:
        print("--dry-run：校验通过即止，未写入")
        return 0

    # —— 阶段 3：一次写入 ——
    try:
        run_lark(["base", "+record-batch-update", "--base-token", base_token,
                  "--table-id", table_id, "--json", json.dumps({"update_records": records})])
    except RuntimeError as e:
        print(f"❌ 写入失败：{e}", file=sys.stderr)
        return 1

    # —— 阶段 4：回读对账（闭环：HTTP 200 ≠ 字段值正确）——
    failed = False
    for rid, fields in records.items():
        data = run_lark(["base", "+record-get", "--base-token", base_token,
                         "--table-id", table_id, "--record-id", rid, "--format", "json"])
        dd = data.get("data", {})
        cols, rows = dd.get("fields") or [], dd.get("data") or []
        if not cols or not rows:
            print(f"❌ 回读结构异常（{list(dd.keys())}），无法对账，人工排查", file=sys.stderr)
            return 1
        rec = dict(zip(cols, rows[0]))
        for fname, want in fields.items():
            got = rec.get(fname)
            # text 字段存 URL 时飞书渲染为 [text](url) markdown，剥壳再比
            if isinstance(got, str):
                m = re_md_link.match(got)
                if m:
                    got = m.group(2)
            ok = got == want or (isinstance(want, str) and got == [want]) \
                 or (isinstance(got, list) and len(got) == 1 and got[0] == want) \
                 or (isinstance(got, (int, float)) and isinstance(want, (int, float))
                     and abs(got - want) < 1e-9)
            if not ok:
                failed = True
                print(f"❌ 回读不一致 [{rid}].{fname}: 期望 {want!r} 实得 {got!r}")
    if failed:
        print("回读对账未过——远端状态与意图不符，禁止宣称写成功，人工排查", file=sys.stderr)
        return 1
    print("✅ 回读对账一致——写入已闭环确认")
    return 0


if __name__ == "__main__":
    sys.exit(main())
