"""从 HAR 文件提取 bx-ua / bx-umidtoken / bx-v / User-Agent 等反爬头，
追加到 bx_pool.json 池子里，给 qwen2API 网关随机轮换使用。

用法 1（命令行）:
    python add_bx_from_har.py "C:\\path\\to\\file.har"

用法 2（拖拽）:
    把 .har 文件直接拖到 add_bx_from_har.bat 上即可。

抓 HAR 的方法:
    1. 浏览器登 https://chat.qwen.ai
    2. F12 → 网络 → 勾选保留日志
    3. 发一条消息（任意内容）
    4. 右键网络面板 → 保存所有为 HAR
"""
import json
import sys
import os
from datetime import datetime

POOL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bx_pool.json")


def find_completions_entry(har: dict):
    """在 HAR 里找 chat/completions 请求条目。"""
    entries = har.get("log", {}).get("entries", [])
    for e in entries:
        url = e.get("request", {}).get("url", "")
        if "chat.qwen.ai" in url and "chat/completions" in url:
            return e
    return None


def extract_entry(har_path: str) -> dict | None:
    with open(har_path, "r", encoding="utf-8") as f:
        har = json.load(f)
    e = find_completions_entry(har)
    if not e:
        print(f"[!] HAR 里没找到 chat/completions 请求: {har_path}")
        return None
    hh = {h["name"]: h["value"] for h in e["request"].get("headers", [])}
    bx_ua = hh.get("bx-ua") or hh.get("Bx-Ua") or ""
    bx_umid = hh.get("bx-umidtoken") or hh.get("Bx-Umidtoken") or ""
    bx_v = hh.get("bx-v") or hh.get("Bx-V") or ""
    if not bx_ua or not bx_umid:
        print(f"[!] HAR 里 bx-ua / bx-umidtoken 为空，可能没抓到反爬头")
        return None
    return {
        "bx_ua": bx_ua,
        "bx_umidtoken": bx_umid,
        "bx_v": bx_v,
        "web_version": hh.get("Version", "0.2.57"),
        "timezone": hh.get("Timezone", ""),
        "user_agent": hh.get("User-Agent", ""),
        "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "note": f"from {os.path.basename(har_path)}",
    }


def load_pool() -> list:
    if not os.path.exists(POOL_PATH):
        return []
    with open(POOL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pool(pool: list):
    with open(POOL_PATH, "w", encoding="utf-8") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2:
        print("用法: python add_bx_from_har.py <HAR 文件路径>")
        print(f"\n当前池子: {POOL_PATH}")
        pool = load_pool()
        print(f"已有 {len(pool)} 条 bx 记录:")
        for i, e in enumerate(pool):
            print(f"  [{i}] {e.get('captured_at','?')}  bx_ua_len={len(e.get('bx_ua',''))}  note={e.get('note','')}")
        sys.exit(1)

    har_path = sys.argv[1]
    if not os.path.exists(har_path):
        print(f"[!] 文件不存在: {har_path}")
        sys.exit(1)

    entry = extract_entry(har_path)
    if not entry:
        sys.exit(1)

    pool = load_pool()
    # 去重：相同 bx_ua 不重复加
    if any(e.get("bx_ua") == entry["bx_ua"] for e in pool):
        print(f"[=] 这个 bx-ua 已经在池子里了，跳过")
    else:
        pool.append(entry)
        save_pool(pool)
        print(f"[+] 已追加新条目，池子现在共 {len(pool)} 条")
        print(f"    bx_ua_len={len(entry['bx_ua'])}  captured_at={entry['captured_at']}")

    print(f"\n网关会在 60 秒内自动重读池子（无需重启）。")


if __name__ == "__main__":
    main()
