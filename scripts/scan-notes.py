#!/usr/bin/env python3
"""掃描課程資料夾，產生 data/study-log.json。

只記錄「這堂課的預習／課堂／複習產物有沒有做出來」與相對檔名，
不讀取也不儲存任何筆記內容——這個 repo 是公開的。

用法：
    python3 scripts/scan-notes.py            # 掃描並寫入 data/study-log.json
    python3 scripts/scan-notes.py --dry-run  # 只印出結果不寫檔
"""
import json, os, re, sys, datetime, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
NOTES_ROOT = os.path.expanduser("~/Desktop/P. 進行中專案/FJU psy/02_修課")
SKIP_DIRS = {"_行政", "_課本", "_課綱", "_封存"}
# 講義產製過程的中間輸出，不是獨立產物，別重複計入
SKIP_SUBDIRS = {"pdf-check", "TTS", "tmp", "工作檔"}

# 檔名關鍵字 → 階段。順序有意義：複習講義也含「講義」，必須先比對。
STAGES = [
    ("複習", ("複習講義", "複習筆記", "課後整理")),
    ("課堂", ("課堂筆記", "錄音重點", "疑問清單", "Plaud")),
    ("預習", ("預習講義", "課前講義", "講義")),
]


def norm(s):
    """macOS 檔名是 NFD，JSON 裡的課名是 NFC，比對前先統一。"""
    return unicodedata.normalize("NFC", s)


def stage_of(filename):
    f = norm(filename)
    for stage, keys in STAGES:
        if any(k in f for k in keys):
            return stage
    return None


def load_name_map(term):
    """課名 → 課號。以 syllabus.json 為主，my-record.json 的 name 覆寫為輔。"""
    syl = json.load(open(os.path.join(REPO, "data/syllabus.json"), encoding="utf-8"))
    rec = json.load(open(os.path.join(REPO, "data/my-record.json"), encoding="utf-8"))
    m = {}
    for code, c in syl["courses"].items():
        m[norm(c["name"])] = code
        m[norm(c["name"].replace("（上）", "").replace("（下）", ""))] = code
    for t in rec["terms"]:
        if t["id"] != term:
            continue
        for e in t.get("courses", []):
            if e.get("name"):
                m[norm(e["name"])] = e["code"]
    return m


def scan(term):
    root = os.path.join(NOTES_ROOT, term)
    if not os.path.isdir(root):
        sys.exit(f"找不到資料夾：{root}")
    name_map = load_name_map(term)
    courses, unknown = {}, []

    for subject in sorted(os.listdir(root)):
        sub_path = os.path.join(root, subject)
        if not os.path.isdir(sub_path) or subject in SKIP_DIRS or subject.startswith("."):
            continue
        code = name_map.get(norm(subject))
        if not code:
            unknown.append(subject)
            continue

        weeks = {}
        for dirpath, dirnames, filenames in os.walk(sub_path):
            dirnames[:] = [d for d in dirnames
                           if not d.startswith(".")
                           and d not in SKIP_SUBDIRS
                           and not d.startswith("rendered")]
            rel = os.path.relpath(dirpath, sub_path)
            m = re.search(r"W(\d{1,2})", norm(rel if rel != "." else ""))
            for fn in filenames:
                if fn.startswith("."):
                    continue
                wk = m.group(1) if m else (re.search(r"W(\d{1,2})", norm(fn)) or [None, None])[1]
                if not wk:
                    continue
                st = stage_of(fn)
                if not st:
                    continue
                w = weeks.setdefault(str(int(wk)),
                                     {"預習": False, "課堂": False, "複習": False, "files": []})
                w[st] = True
                p = norm(os.path.relpath(os.path.join(dirpath, fn), sub_path))
                w["files"].append(f"{norm(subject)}/{p}")

        if weeks:
            for w in weeks.values():
                w["files"] = sorted(set(w["files"]))
            courses[code] = dict(sorted(weeks.items(), key=lambda kv: int(kv[0])))

    return {
        "meta": {
            "term": term,
            "scanned": datetime.date.today().isoformat(),
            "root": f"FJU psy/02_修課/{term}",
            "note": "由 scripts/scan-notes.py 產生。只記錄產物是否存在與相對檔名，不含筆記內容。",
            "stages": ["預習", "課堂", "複習"],
            "unmatchedFolders": unknown,
        },
        "courses": courses,
    }


if __name__ == "__main__":
    term = next((a for a in sys.argv[1:] if a.isdigit()), "1151")
    data = scan(term)
    n = sum(len(w) for w in data["courses"].values())
    done = sum(1 for w in data["courses"].values() for x in w.values()
               if x["預習"] and x["課堂"] and x["複習"])
    print(f"掃到 {len(data['courses'])} 科、{n} 個週次，三階段都齊的有 {done} 個")
    if data["meta"]["unmatchedFolders"]:
        print("對不到課號的資料夾：", "、".join(data["meta"]["unmatchedFolders"]))
    if "--dry-run" in sys.argv:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        out = os.path.join(REPO, "data/study-log.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("已寫入", os.path.relpath(out, REPO))
