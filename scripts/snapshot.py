#!/usr/bin/env python3
"""Снимок листинга chuangmi-cdn -> snapshot.json (резерв, если CDN недоступен из браузера).
Тянет все объекты под product/, оставляет только .zip/.rar пакеты прошивок."""
import json, os, time, urllib.parse, urllib.request, datetime, sys

# ВНИМАНИЕ: листинг отдаёт только этот хост (xiaomi.com). Он расположен в Китае и
# может быть недоступен с egress-IP GitHub Actions (таймаут). Скрипт это переживает:
# при неудаче он НЕ трогает существующий snapshot.json и завершается успешно.
BASE = "https://cnbj2.fds.api.xiaomi.com/chuangmi-cdn"

def fetch_all(prefix="product/"):
    marker, objs, pages = "", [], 0
    while True:
        q = urllib.parse.urlencode({"prefix": prefix, "maxKeys": "1000", "marker": marker})
        req = urllib.request.Request(BASE + "?" + q, headers={"User-Agent": "snapshot-bot"})
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.load(r)
        objs.extend(d.get("objects", []))
        pages += 1
        if not d.get("truncated"):
            break
        marker = d.get("nextMarker") or ""
        if not marker or pages > 60:
            break
    return objs

def fetch_all_retry(attempts=3):
    last = None
    for i in range(1, attempts + 1):
        try:
            return fetch_all()
        except Exception as e:
            last = e
            print(f"попытка {i}/{attempts} не удалась: {e}", file=sys.stderr)
            time.sleep(3)
    raise last

def main():
    try:
        objs = fetch_all_retry()
    except Exception as e:
        print(f"WARN: CDN недоступен ({e}).", file=sys.stderr)
        if os.path.exists("snapshot.json"):
            print("Оставляю прежний snapshot.json без изменений.")
            return 0
        print("ERROR: и прежнего snapshot.json нет.", file=sys.stderr)
        return 1
    pkg = [
        {"name": o["name"], "size": o.get("size", 0), "uploadTime": o.get("uploadTime", 0)}
        for o in objs
        if o.get("name", "").lower().endswith((".zip", ".rar"))
    ]
    out = {
        "generated": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "count": len(pkg),
        "objects": pkg,
    }
    with open("snapshot.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"snapshot.json: {len(pkg)} packages, generated {out['generated']}")

if __name__ == "__main__":
    sys.exit(main())
