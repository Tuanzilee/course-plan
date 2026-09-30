#!/usr/bin/env python3
"""掃描課程資料夾與手動紀錄檔，產生 data/study-log.json。

只記錄「這堂課的三個階段做完了沒」與相對檔名，
不讀取也不儲存任何筆記內容——這個 repo 是公開的。

三個階段：

    錄音  Plaud 的 Highlights／Summary／transcript 進資料夾了
    產出  自己做的東西寫完了（TTS 口語稿、總結、反思、報告）
    繳交  課堂要求的都交了（TronClass 上的測驗、討論、互評）

「錄音」靠檔名自動偵測，「產出」部分自動、「繳交」完全手動——
因為那些在 TronClass 上交，電腦資料夾裡看不到。
手動紀錄寫在 <學期>/_學習紀錄.md，格式：

    ## 認知神經科學導論
    產出：1 2 3
    繳交：1 2

自動與手動是聯集，掃得到的不用重複記。

用法：
    python3 scripts/scan-notes.py            # 掃描並寫入 data/study-log.json
    python3 scripts/scan-notes.py --dry-run  # 只印出結果不寫檔
"""
import json, os, re, sys, datetime, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
NOTES_ROOT = os.path.expanduser("~/Desktop/P. 進行中專案/FJU psy/02_修課")
LOG_FILE = "_學習紀錄.md"
SKIP_DIRS = {"_行政", "_課本", "_課綱", "_封存"}
SKIP_SUBDIRS = {"pdf-check", "tmp", "工作檔"}

STAGES = ["錄音", "產出", "繳交"]

# 自動偵測的檔名關鍵字。繳交沒有——那在 TronClass 上，檔案系統看不到。
AUTO = [
    ("錄音", ("-Highlights", "-Summary", "-transcript", "Plaud")),
    ("產出", ("TTS", "口語稿", "總結", "反思", "預習講義", "複習講義")),
]


def norm(s):
    """macOS 檔名是 NFD，JSON 裡的課名是 NFC，比對前先統一。"""
    return unicodedata.normalize("NFC", s)


def squash(s):
    """比對課名時忽略空白與全形空白——實際檔名常有「AI 時代」這種夾空白的寫法。"""
    return re.sub(r"[\s\u3000]+", "", norm(s))


def stage_of(name):
    n = norm(name)
    for stage, keys in AUTO:
        if any(k.lower() in n.lower() for k in keys):
            return stage
    return None


def load_name_map(term):
    """課名 → 課號。以 syllabus.json 為主，my-record.json 的 name 覆寫為輔。"""
    syl = json.load(open(os.path.join(REPO, "data/syllabus.json"), encoding="utf-8"))
    rec = json.load(open(os.path.join(REPO, "data/my-record.json"), encoding="utf-8"))
    m = {}

    def put(name, code):
        if name:
            m[squash(name)] = code

    for code, c in syl["courses"].items():
        put(c["name"], code)
        put(c["name"].replace("（上）", "").replace("（下）", ""), code)
        for a in c.get("aliases", []):
            put(a, code)
    for t in rec["terms"]:
        if t["id"] != term:
            continue
        for e in t.get("courses", []):
            put(e.get("name"), e["code"])
    return m


def subject_in(text, names_by_len):
    """在字串裡找課名或別名。長的先比，避免「心理學實驗法」被「心理學」搶走。"""
    t = squash(text)
    for name in names_by_len:
        if name in t:
            return name
    return None


def blank_week():
    w = {s: False for s in STAGES}
    w["files"] = []
    return w


def read_manual(root, name_map, names_by_len):
    """讀 _學習紀錄.md。回傳 {課號: {週次: set(階段)}}。"""
    path = os.path.join(root, LOG_FILE)
    if not os.path.isfile(path):
        return {}, None
    out, code = {}, None
    for line in open(path, encoding="utf-8"):
        line = norm(line).strip()
        if line.startswith("##"):
            subj = subject_in(line.lstrip("# ").strip(), names_by_len)
            code = name_map.get(subj) if subj else None
            continue
        m = re.match(r"^(%s)\s*[:：]\s*(.*)$" % "|".join(STAGES), line)
        if not m or not code:
            continue
        stage, rest = m.group(1), m.group(2)
        for wk in re.findall(r"\d+", rest):
            out.setdefault(code, {}).setdefault(str(int(wk)), set()).add(stage)
    return out, path


def scan(term, notes_root=None):
    root = os.path.join(notes_root or NOTES_ROOT, term)
    if not os.path.isdir(root):
        sys.exit(f"找不到資料夾：{root}")
    name_map = load_name_map(term)
    names_by_len = sorted(name_map, key=len, reverse=True)

    courses, skipped = {}, []

    # 1) 檔名自動偵測
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".")
                       and d not in SKIP_DIRS
                       and d not in SKIP_SUBDIRS
                       and not d.startswith("rendered")]
        rel_dir = os.path.relpath(dirpath, root)
        if norm(rel_dir).split(os.sep)[0] in SKIP_DIRS:
            continue

        for fn in filenames:
            if fn.startswith(".") or fn == LOG_FILE:
                continue
            fn_n = norm(fn)
            stage = stage_of(fn_n)
            if not stage:
                continue
            wk = (re.search(r"[Ww](\d{1,2})", fn_n)
                  or re.search(r"[Ww](\d{1,2})", norm(rel_dir)))
            subj = subject_in(fn_n, names_by_len) or subject_in(rel_dir, names_by_len)
            if not wk or not subj:
                skipped.append({"file": fn_n,
                                "reason": "檔名缺週次 W##" if not wk else "對不到課名"})
                continue
            w = courses.setdefault(name_map[subj], {}).setdefault(
                str(int(wk.group(1))), blank_week())
            w[stage] = True
            w["files"].append(norm(os.path.relpath(os.path.join(dirpath, fn), root)))

    # 2) 手動紀錄，與自動偵測取聯集
    manual, log_path = read_manual(root, name_map, names_by_len)
    for code, weeks in manual.items():
        for wk, stages in weeks.items():
            w = courses.setdefault(code, {}).setdefault(wk, blank_week())
            for s in stages:
                w[s] = True

    for weeks in courses.values():
        for w in weeks.values():
            w["files"] = sorted(set(w["files"]))
    courses = {c: dict(sorted(w.items(), key=lambda kv: int(kv[0]))) for c, w in courses.items()}

    return {
        "meta": {
            "term": term,
            "scanned": datetime.date.today().isoformat(),
            "root": f"FJU psy/02_修課/{term}",
            "note": "由 scripts/scan-notes.py 產生。只記錄階段是否完成與相對檔名，不含筆記內容。",
            "stages": STAGES,
            "manualFile": LOG_FILE if log_path else None,
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
               if all(x[s] for s in STAGES))
    print(f"掃到 {len(data['courses'])} 科、{n} 個週次，三階段都齊的有 {done} 個")
    if not data["meta"]["manualFile"]:
        print(f"  ⚠ 找不到 {LOG_FILE}，繳交與部分產出無法計入")
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
