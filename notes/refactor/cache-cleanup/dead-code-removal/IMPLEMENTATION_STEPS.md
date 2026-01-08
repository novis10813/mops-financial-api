# Implementation Steps: Dead Code Removal

## Checklist

### Phase 1: 刪除死程式碼
- [ ] 刪除 `app/services/cached_financial.py`

### Phase 2: 驗證
- [ ] 執行所有測試確認無 import 錯誤
- [ ] 確認 API 正常運作

### Phase 3: 提交
- [ ] Atomic commit

---

## Step-by-Step

### Step 1: 刪除檔案
```bash
rm app/services/cached_financial.py
```

### Step 2: 執行測試
```bash
uv run pytest tests/ -v
```

### Step 3: 提交
```bash
git add -A
git commit -m "refactor: remove unused cached_financial.py"
```
