#!/bin/sh
# 推上公開 repo 前的個資檢查。
# 真實比對值放在同層目錄的 .pii-patterns（每行一個，已列入 .gitignore）。
# 有任何輸出就不要推。
cd "$(dirname "$0")/.." || exit 1
[ -f .pii-patterns ] || { echo "找不到 .pii-patterns，先建立再跑"; exit 2; }
grep -rInf .pii-patterns . --exclude-dir=.git --exclude=.pii-patterns \
  && { echo "^^^ 發現個資，不要推"; exit 1; }
echo "PII clean"
