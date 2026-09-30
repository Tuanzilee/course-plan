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
| `data/syllabus.json` | 每學期一次 | 新學期課綱出來，重建各科逐週進度 |
| `data/study-log.json` | 常動 | **不要手改**，跑 `scripts/scan-notes.py` 產生 |

## 學習紀錄（錄音／產出／繳交）

筆記本體永遠在 `~/Desktop/P. 進行中專案/FJU psy/02_修課/<學期>/`，
**這個 repo 是公開的，絕對不要把筆記內容搬進來**。`study-log.json` 只存三個 boolean
與相對檔名。

三個階段對應 hai 的實際流程：

| 階段 | 是什麼 | 怎麼判斷 |
| :-- | :-- | :-- |
| 錄音 | Plaud 的 Highlights／Summary／transcript 進資料夾 | 自動（檔名） |
| 產出 | 自己做的 TTS 口語稿、總結、反思、講義 | 自動（檔名）＋手動補 |
| 繳交 | TronClass 上的測驗、討論、互評、作業 | **只能手動**，檔案系統看不到 |

手動紀錄寫在 `<學期>/_學習紀錄.md`，格式就是在冒號後面補週次：

```
## 認知神經科學導論
產出：1 2 3
繳交：1 2
```

自動與手動取**聯集**，掃得到的不用重複記。

### 課名比對

檔名常用簡稱（「AI 應用課」對正式課名「AI時代的AI心理學應用」），所以
`syllabus.json` 每科可以加 `aliases`。比對時會忽略空白、長的課名優先，
否則「心理學實驗法」會被「心理學」搶走。新學期若出現對不到的簡稱，加進 `aliases` 就好。

檔名缺 `W##` 或對不到課名的檔案會列在 `meta.skipped`，掃描時也會印出警告——
**要主動告訴 hai 哪幾個檔沒被算到**，不要默默略過。

### hai 說「更新學習紀錄」時要做的事

```bash
cd ~/Desktop/course && python3 scripts/scan-notes.py
```

然後回報：掃到幾科幾週、有沒有 skipped、完成率變化，接著 commit + push
（`git push origin pages-main:main`）。

**絕對不要幫 hai 填 `_學習紀錄.md` 的內容。**那是她的實際紀錄，
代填等於捏造。測試要用 `--root=` 指到別的資料夾。

## 程式碼

`index.html` 一支檔案，分三段：CSS → 資料載入與計算 → 四個 view 函式。

- `compute()` 產出 `raw`（各桶原始學分）、`eff`（套上桶上限與溢流後）、`satisfied`（課號 → 來源）、`placements`
- `SPILL` 定義溢流鏈：系核心 → 系專選 → 選修專選 → 自由選修
- `checks()` 回傳警示陣列，新增檢查就加在這裡，`lv` 用 `err` / `warn` / `ok`

改介面不要引入框架或 CDN，維持「一個檔案雙擊就能看懂」。

**拖曳一律用 pointer events，不要用 HTML5 drag and drop。** HTML5 DnD 在觸控裝置上
完全無效，手機會變成拖不動。逐週進度的欄位排序就是這樣踩過一次坑。做法：
`pointerdown` 記起點 →「橫向位移 > 8px 且大於垂直位移」才判定為拖曳（讓垂直捲動優先）
→ `elementFromPoint` 找落點 → `pointerup` 套用。CSS 加 `touch-action: pan-y`，
不要用 `setPointerCapture`（事件掛在 window 上本來就收得到，捕獲反而讓落點判斷變複雜）。
表格比畫面寬時，記得做拖到邊緣自動橫向捲動，否則搆不到看不見的欄位。
