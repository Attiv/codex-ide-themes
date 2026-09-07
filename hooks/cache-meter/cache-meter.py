#!/usr/bin/env python3
"""Codex Stop hook — 每次用户提问结束后打印「缓存/用量/金额」摘要。

数据来源:Codex 会话 rollout JSONL 中的 event_msg.token_count。
last_token_usage 是最近一次「模型请求」，不是整个用户问答；
total_token_usage 是整个会话线程的累计值。本脚本会按 turn_id 汇总
当前用户提问内部触发的所有模型请求，避免把「最近请求」误标成「本轮」。

金额:按 $CODEX_HOME/hooks/prices.json 里的每百万 token 价格估算(美元):
  {
    "models": {
      "gpt-6-astra": {"input_per_m": 0.0, "output_per_m": 0.0,
                      "cache_read_per_m": 0.0, "cache_write_per_m": 0.0}
    }
  }
CODEX_HOME 默认是 ~/.codex。某模型价格全部为 0(或未配置)时，
会明确提示价格尚未配置；示例不包含真实模型单价。

输出:stdout 输出 {"systemMessage": "<多行文本>"} —— Codex TUI 会自动换行显示。
没有可用数据或会话不可读时静默退出(不输出)。请配置 10 秒 hook 超时。
"""

import json
import os
import sys
from datetime import datetime

CODEX_HOME = os.path.expanduser(os.environ.get("CODEX_HOME") or "~/.codex")
PRICES_FILE = os.path.join(CODEX_HOME, "hooks", "prices.json")
CONFIG_FILE = os.path.join(CODEX_HOME, "config.toml")


def human(n):
    n = int(n or 0)
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        s = f"{n / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{s}K"
    s = f"{n / 1_000_000:.2f}".rstrip("0").rstrip(".")
    return f"{s}M"


def load_prices():
    try:
        with open(PRICES_FILE) as fh:
            return json.load(fh)
    except Exception:
        return {}


def model_cost(price, usage):
    """按价格表估算一次 usage 的成本(美元)。价格 0/缺失时返回 None。"""
    if not price or not usage:
        return None
    inn = usage.get("input_tokens") or 0
    cached = usage.get("cached_input_tokens") or 0
    cw = usage.get("cache_write_input_tokens") or 0
    # Responses API 的 output_tokens 已包含 reasoning_output_tokens，后者只是明细子集。
    # 因此这里不能再把推理 token 加一次。
    out = usage.get("output_tokens") or 0
    pi = price.get("input_per_m") or 0
    po = price.get("output_per_m") or 0
    pc = price.get("cache_read_per_m") or 0
    pw = price.get("cache_write_per_m") or 0
    if not any((pi, po, pc, pw)):
        return None
    # input_tokens 是输入总量；缓存命中和缓存写入都是其中的分项。
    fresh_in = max(0, inn - cached - cw)
    return (fresh_in * pi + cached * pc + cw * pw + out * po) / 1_000_000


def current_local_timestamp(now=None):
    """返回 Hook 生成摘要时的本机时间。"""
    return (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")


def fmt_cost(usd):
    if usd is None:
        return None
    if usd >= 0.01:
        return f"${usd:.3f}"
    return f"${usd * 1000:.1f}m"  # 不足 1 分钱用毫美元


def find_transcript(payload):
    """优先用 hook payload 的 transcript_path;否则按 session_id 匹配 rollout
    文件名(rollout-<ts>-<session_id>.jsonl)。不猜测其他会话，避免串账。"""
    tp = payload.get("transcript_path")
    if isinstance(tp, str) and tp and os.path.isfile(tp):
        return tp
    sid = payload.get("session_id", "")
    base = os.path.join(CODEX_HOME, "sessions")
    if isinstance(sid, str) and sid and os.path.isdir(base):
        for root, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".jsonl"):
                    continue
                p = os.path.join(root, fn)
                if fn.endswith(f"-{sid}.jsonl"):
                    return p
    return None


def reverse_json_lines(path, block_size=64 * 1024):
    """从文件尾部反向迭代 JSON 行。

    不再只读取末尾固定 2 MiB。长会话里最近的 ``turn_context`` 可能离文件尾
    很远；旧实现因此找不到模型名，价格表无法命中，金额段就会消失。
    """
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        pos = fh.tell()
        remainder = b""
        while pos > 0:
            read_size = min(block_size, pos)
            pos -= read_size
            fh.seek(pos)
            data = fh.read(read_size) + remainder
            lines = data.split(b"\n")
            remainder = lines[0]
            for raw in reversed(lines[1:]):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    yield json.loads(raw.decode("utf-8", "replace"))
                except Exception:
                    continue
        raw = remainder.strip()
        if raw:
            try:
                yield json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                pass


def configured_model():
    """会话里极端情况下没有 turn_context 时，退回 config.toml 的 model。"""
    try:
        import tomllib

        with open(CONFIG_FILE, "rb") as fh:
            value = tomllib.load(fh).get("model")
        return value if isinstance(value, str) and value else None
    except Exception:
        return None


def has_usage(u):
    """这个 token_count 是否包含可统计的模型用量。"""
    if not u:
        return False
    return any(
        u.get(k) or 0
        for k in (
            "input_tokens",
            "cached_input_tokens",
            "cache_write_input_tokens",
            "output_tokens",
        )
    )


def sum_usages(usages):
    """对多次模型请求的 usage 逐字段求和。"""
    keys = (
        "input_tokens",
        "cached_input_tokens",
        "cache_write_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "total_tokens",
    )
    result = {k: 0 for k in keys}
    found = False
    for usage in usages:
        if not has_usage(usage):
            continue
        found = True
        for key in keys:
            result[key] += usage.get(key) or 0
    return result if found else None


def token_usage_snapshot(path):
    """返回 (最近请求, 本次提问, 会话累计, 请求数, 模型)。

    一次用户提问可能因工具调用、命令执行和自动继续而产生很多次
    模型请求。同一次提问在上下文压缩后可能出现多个 turn_context，
    但 turn_id 保持不变，所以要一直回溯到上一个不同的 turn_id。
    """
    last = thread_total = None
    model = None
    current_turn_key = None
    context_seq = 0
    turn_usages = []

    # 顺序扫描虽然比只读文件尾部多做一点 I/O，但能准确判断最后
    # 一个 turn_id 的起点，也不会把上一次提问的 token 误算进来。
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            try:
                d = json.loads(raw)
            except Exception:
                continue
            pl = d.get("payload") or {}

            if d.get("type") == "turn_context":
                turn_id = pl.get("turn_id")
                if turn_id is None:
                    context_seq += 1
                    turn_key = ("legacy", context_seq)
                else:
                    turn_key = ("turn_id", turn_id)
                if turn_key != current_turn_key:
                    current_turn_key = turn_key
                    turn_usages = []
                model = pl.get("model") or model
                continue

            if d.get("type") != "event_msg" or pl.get("type") != "token_count":
                continue
            info = pl.get("info") or {}
            usage = info.get("last_token_usage")
            if has_usage(usage):
                last = usage
            if info.get("total_token_usage"):
                thread_total = info["total_token_usage"]
            if usage:
                turn_usages.append(usage)

    turn_total = sum_usages(turn_usages)
    request_count = sum(1 for usage in turn_usages if has_usage(usage))
    return last, turn_total, thread_total, request_count, model or configured_model()


def fmt_usage_lines(u, indent="  "):
    if not u:
        return []
    inn = u.get("input_tokens") or 0
    cached = u.get("cached_input_tokens") or 0
    cw = u.get("cache_write_input_tokens") or 0
    out = u.get("output_tokens") or 0
    rsn = u.get("reasoning_output_tokens") or 0
    pct = f"{cached * 100 // inn}%" if inn else "-"
    uncached = max(0, inn - cached - cw)
    input_detail = f"缓存命中 {human(cached)}，{pct}；未缓存 {human(uncached)}"
    if cw:
        input_detail += f"；缓存写入 {human(cw)}"
    output_detail = f"输出：{human(out)}"
    if rsn:
        output_detail += f"（含推理 {human(rsn)}）"
    return [
        f"{indent}输入：{human(inn)}（{input_detail}）",
        f"{indent}{output_detail}",
    ]


def main(raw=None):
    try:
        raw = sys.stdin.read() if raw is None else raw
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    if not isinstance(payload, dict):
        return

    path = find_transcript(payload)
    if not path:
        sys.exit(0)

    try:
        last, turn_total, _thread_total, request_count, model = token_usage_snapshot(path)
    except (OSError, ValueError, TypeError, AttributeError):
        return  # 会话文件可能被删除、正在写入，或格式已变化。
    if not last or not turn_total:
        sys.exit(0)  # 还没有任何 usage,静默

    lines = ["📊 Codex 用量（Token，不是提问次数）"]
    lines.append(f"本次提问：内部调用模型 {request_count} 次")
    lines.extend(fmt_usage_lines(turn_total))
    if request_count > 1:
        lines.append("最近一次模型请求：")
        lines.extend(fmt_usage_lines(last))

    # 金额只显示「本次提问」，不再把最近模型请求误标为本轮。
    # 这是本地 token * API 单价的理论值，不是账户账单或订阅扣费。
    prices = load_prices()
    price = (prices.get("models") or {}).get(model or "") if isinstance(prices, dict) else None
    c_turn = model_cost(price, turn_total)
    if c_turn is not None:
        lines.append(f"💰 按 API 单价估算：本次提问 {fmt_cost(c_turn)}（非账户实扣）")
    elif model:
        lines.append(f"💰 API 单价估算：未配置 {model} 的价格")
    if model:
        lines.append(f"模型：{model}")
    lines.append(f"时间：{current_local_timestamp()}")

    print(json.dumps({"systemMessage": "\n".join(lines)}, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
