# course-plan 維護規則

輔大心理系畢業學分儀表板。單頁 HTML + JSON，無框架、無 build、無外部相依。

線上版：<https://tuanzilee.github.io/course-plan/>（公開）

## ⚠️ 分支與隱私（動手前務必先讀）

**這是公開 repo，`data/` 底下不得出現真實姓名、學號、原校校名、肄業紀錄等個資。**
`my-record.json` 的 `student` 只保留計算用得到的欄位（系所、入學身分、適用學年度、
修業年限、原校累計學分數）。抵免項目寫科目與學分即可，不要寫成績或原校校名。

檢查清單本身也不要寫出真實值——包括這份文件裡的範例指令。

分支狀態：

| 分支 | 用途 |
| :-- | :-- |
| `pages-main` | **工作分支**，`git push origin pages-main:main` 部署 |
| `main`（本機） | 早期含個資的歷史，僅本機保留，**永遠不要推上去** |

平常就待在 `pages-main` 上改。推之前先跑一次 `scripts/check-pii.sh`：有輸出就不要推。
要比對的真實值放在本機的 `.pii-patterns`（已列入 `.gitignore`，不會上傳）。

## 動手前先讀

- `README.md`：專案概觀與跑法
- 原始規定文件在 `~/Desktop/P. 進行中專案/FJU psy/00_學籍與規章/`
- 抵免申請文件在 `~/Desktop/P. 進行中專案/FJU psy/01_申請案/2026-08_學分抵免/`
- 每學期行政文件在 `~/Desktop/P. 進行中專案/FJU psy/02_修課/<學期>/_行政/`

## 三個 JSON 的職責

| 檔案 | 改動頻率 | 誰會動它 |
| :-- | :-- | :-- |
| `data/requirements.json` | 幾乎不動 | 學校改畢業規定、或釐清一個 `openQuestions` |
| `data/courses.json` | 每學年一次 | 新學年排課總表出來，更新 `offered` 與新課 |
| `data/my-record.json` | 常動 | 選課、抵免結果出爐、學期結束 |

## 常見維護動作

**抵免結果出爐** → 改 `my-record.json` 的 `transfer.items[].status`（`pending` → `approved` / `rejected`），
並把 `transfer.status` 改成 `settled`。之後 Plan A / Plan B 切換就只是歷史紀錄，不再影響數字。

**選課定案** → 把 `terms[].courses[]` 裡的 `status` 從 `planA` / `planB` / `tentative` 改成 `confirmed`，
沒選上的整筆刪掉。

**學期結束** → 把該學期的 `state` 從 `current` 改成 `done`，下一學期改成 `current`。

**新學年排課總表出來** → 用 `pdftotext -layout` 抽文字，更新 `courses.json` 的 `offered`
與各課 `prereq`（排課總表最後面的「R 課程擋修規定」是擋修的唯一權威來源）。
新出現的課要補進 `courses` 陣列；`courses.json` 沒有的課，`my-record.json` 的 `extraCourses` 可暫放。

## 寫資料時的規矩

- **全學年課程一律拆成上／下兩筆**，`code` 加 `-1` / `-2`，並填 `base` 指回原科目代碼。
  擋修條件寫 `base`（例如統計學 6 學分寫 `02222`），程式會自動對應。
- **`suggested` 是必修科目表的建議年級，`offered` 是排課總表的實際開課學期。**
  兩者不一致時不要自己改成一致——儀表板會提示這個落差，那是刻意的。
- **不確定的事寫進 `requirements.json` 的 `openQuestions`**，不要在程式碼裡假設。
  例如「57 取 45 能略過哪幾科」在系辦回覆前一律當成未知。
- 每筆資料盡量帶 `note` 說明來源或但書，日後回頭看才知道為什麼這樣填。

## 程式碼

`index.html` 一支檔案，分三段：CSS → 資料載入與計算 → 四個 view 函式。

- `compute()` 產出 `raw`（各桶原始學分）、`eff`（套上桶上限與溢流後）、`satisfied`（課號 → 來源）、`placements`
- `SPILL` 定義溢流鏈：系核心 → 系專選 → 選修專選 → 自由選修
- `checks()` 回傳警示陣列，新增檢查就加在這裡，`lv` 用 `err` / `warn` / `ok`

改介面不要引入框架或 CDN，維持「一個檔案雙擊就能看懂」。
