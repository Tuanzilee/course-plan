#!/usr/bin/env python3
"""掃描課程資料夾，產生 data/study-log.json。

只記錄「這堂課的預習／課堂／複習產物有沒有做出來」與相對檔名，
不讀取也不儲存任何筆記內容——這個 repo 是公開的。

檔名就是紀錄。三個欄位從檔名解析，跟放在哪個資料夾無關：

    20260915_人格心理學_W02_預習講義.pdf
             ~~~~~~~~~~ ~~~ ~~~~~~~~
             科目        週次  階段

所以扁平放（全部丟在同一個資料夾）或巢狀放（科目/W01_主題/）都能掃，
不需要為了這支腳本搬檔案。科目在檔名裡找不到時，才退而用最上層資料夾名。

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

# 檔名關鍵字 → 階段。順序有意義：「複習講義」也含「講義」，必須先比對複習。
STAGES = [
    ("複習", ("複習講義", "複習筆記", "課後整理")),
    ("課堂", ("課堂筆記", "錄音重點", "疑問清單", "Plaud")),
    ("預習", ("預習講義", "課前講義", "講義")),
]


def norm(s):
    """macOS 檔名是 NFD，JSON 裡的課名是 NFC，比對前先統一。"""
    return unicodedata.normalize("NFC", s)


def stage_of(name):
    n = norm(name)
    for stage, keys in STAGES:
        if any(k in n for k in keys):
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


def subject_in(text, names_by_len):
    """在字串裡找課名。長的先比，避免「心理學實驗法」被「心理學」搶走。"""
    t = norm(text)
    for name in names_by_len:
        if name in t:
            return name
    return None


def scan(term, notes_root=None):
    root = os.path.join(notes_root or NOTES_ROOT, term)
    if not os.path.isdir(root):
        sys.exit(f"找不到資料夾：{root}")
    name_map = load_name_map(term)
    names_by_len = sorted(name_map, key=len, reverse=True)

    courses, skipped = {}, []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".")
                       and d not in SKIP_DIRS
                       and d not in SKIP_SUBDIRS
                       and not d.startswith("rendered")]
        rel_dir = os.path.relpath(dirpath, root)
        top = "" if rel_dir == "." else norm(rel_dir).split(os.sep)[0]
        if top in SKIP_DIRS:
            continue

        for fn in filenames:
            if fn.startswith("."):
                continue
            fn_n = norm(fn)
            stage = stage_of(fn_n)
            if not stage:
                continue

            wk = re.search(r"W(\d{1,2})", fn_n) or re.search(r"W(\d{1,2})", norm(rel_dir))
            # 科目先從檔名找，找不到再看資料夾路徑
            subj = subject_in(fn_n, names_by_len) or subject_in(rel_dir, names_by_len)
            if not wk or not subj:
                skipped.append({"file": fn_n,
                                "reason": "檔名缺週次 W##" if not wk else "檔名對不到課名"})
                continue

            code = name_map[subj]
            w = courses.setdefault(code, {}).setdefault(
                str(int(wk.group(1))), {"預習": False, "課堂": False, "複習": False, "files": []})
            w[stage] = True
            w["files"].append(norm(os.path.relpath(os.path.join(dirpath, fn), root)))

    for weeks in courses.values():
        for w in weeks.values():
            w["files"] = sorted(set(w["files"]))
    courses = {c: dict(sorted(w.items(), key=lambda kv: int(kv[0]))) for c, w in courses.items()}

    return {
        "meta": {
            "term": term,
            "scanned": datetime.date.today().isoformat(),
            "root": f"FJU psy/02_修課/{term}",
            "note": "由 scripts/scan-notes.py 產生。只記錄產物是否存在與相對檔名，不含筆記內容。",
            "stages": ["預習", "課堂", "複習"],
            "skipped": skipped,
        },
        "courses": courses,
    }


if __name__ == "__main__":
    term = next((a for a in sys.argv[1:] if a.isdigit()), "1151")
    root = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--root=")), None)
    data = scan(term, root)
    n = sum(len(w) for w in data["courses"].values())
    done = sum(1 for w in data["courses"].values() for x in w.values()
               if x["預習"] and x["課堂"] and x["複習"])
    print(f"掃到 {len(data['courses'])} 科、{n} 個週次，三階段都齊的有 {done} 個")
    for s in data["meta"]["skipped"]:
        print(f"  ⚠ 略過 {s['file']}：{s['reason']}")
    if "--dry-run" in sys.argv:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        out = os.path.join(REPO, "data/study-log.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("已寫入", os.path.relpath(out, REPO))
