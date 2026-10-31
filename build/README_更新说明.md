# 单词站增量更新说明（Leo in Bali · v.zdc.sh.cn）

> 核心原则：**旧的不动，只加新的。** 已上线的旧词条（id、内容、顺序）、旧章节、旧音频、浏览器里的学习进度（localStorage：`wsv2-anki` / `wsx-prefs` / `wsx-learned` / `wsv2-theme`）一律不改。唯一新增的键是 `wsx-last`（上次读到的章/段，`{c,p,t}`），故事页只**读** `wsv2-anki` 来算「已掌握」，从不写。新词只追加：分配新 id、写进新章节、生成新音频。

## 目录
```
site/                    网站本体（与仓库 site/ 对应）
build/
  update.py              一键流水线：对比 → 生成数据 → 插入新章节 → 改 Anki 排序 → 生成音频 → 打包
  diff.py                只做对比（新增 / 删除 / 变动）
  chapters.py            解析并校验故事源文件
  chapters/chNN.txt      新章节故事源文件（人工/AI 写）
  verify.py              验证旧内容未变 + 无头 Chrome 截图
  postbuild.py           站点后处理（update.py 结尾自动调用，幂等，可单独重跑）：
    navfix.py            章节导航：上一章/下一章、目录抽屉可滚动、继续阅读（记到段落，键 wsx-last）
    header.py            v2 柔和配色（三页）+ 故事页新头部（继续阅读 / 最新补充 / 已掌握 / 设置面板），数字按 words.json 重算
    noquiz.py            去掉每章末尾的填空小测、页面末尾的「说明」区和目录里的「说明」链接（10/24 用户反馈多余）
    cachefix.py          data/words.js、bounds.js 加 ?v=内容哈希，更新后不用强刷
  check_highlight.py     朗读逐词高亮与音频时间对齐的回归测试
  shots_pr2.py           去掉小测/说明前后的手机对比截图
  verify_v2.py           头部 + 导航 + 配色回归测试（手机/桌面 × 日间/夜间）
  shots_header.py        头部截图（手机夜间/日间、设置面板、桌面）
  README_更新说明.md     本文件
```

## 每次更新的步骤
1. **拿到新总表 CSV**（列：`#,单词,音标,中文,主题,高频,出现次数,出现日期,来源,笔记线索`，日期用 ` / ` 分隔）。
2. **对比**：`python3 build/diff.py 新总表.csv site/data/words.json diff.json`
   - 匹配按「单词文本」（去 HTML 实体、合并空格、忽略大小写），**不按 # 序号**（总表每次可能重排序号）。
   - 输出新增 / 变动（日期、主题、中文）/ 删除。变动和删除只报告，不改旧卡。
3. **写新章节**：在 `build/chapters/` 新建 `ch70.txt`、`ch71.txt`…（章号接着上次最大章号），格式：
   ```
   # 70 | ① 性格与情绪 | English Title | 中文标题
   P: 英文段落，目标词写成 {出现形式|CSV序号}，如 Leo felt {overwhelmed|101}.
   Z: 对应中文段落
   W: 101 | /ˌoʊvərˈwelmd/ | 短释义(高亮下方的小字) | 搭配1; 搭配2
   X: 工作场景例句 | 中文
   X: 生活·巴厘岛例句 | 中文
   ```
   - 每章约 20 词、4–6 段、A2–B1；人物：Leo / Sonia / Kenji / Ana / Pak Made / Ketut / Warren（10/23 新增：澳洲室友，前厨师）。
   - 只标注本批新词；{…|序号} 用**本次 CSV 的 # 列**。
   - 校验：`python3 build/chapters.py diff.json` → 必须 `covered N / N`、`missing 0`。
   - 已经在线上的章节会被自动跳过，旧章节文件不用删。
   - 生成的章节只有：标题区 + 故事段落 + 本章词表（+ 运行时加的上一章/下一章）。**不生成填空小测，也不加「说明」**；章节文件里不需要写小测题或说明。
4. **运行流水线**（需要 `pip install edge-tts`，联网）：
   ```
   python3 build/update.py --csv 新总表.csv --base 当前线上site目录 --batch 11/06 --out out --audio-cache audio_cache
   ```
   - `--batch` 是批次标签，会显示成「新 11/06」徽标和 Anki 里的「11/06 新增（N）」筛选项。
   - 音频（美式 Ava、英式 Sonia）缓存在 `audio_cache/`，中断后**重跑同一命令即可续跑**，已生成的不会重做；脚本拒绝覆盖任何已有的旧音频。
   - 没有被任何章节覆盖的新词不会上线，会列在 `out/need_story_TODO.txt`。
   - 加 `--no-audio` 可以先快速预览页面。
   - 流水线最后会自动跑 `build/postbuild.py out/site`：头部的章数、词数、「最新补充」批次与章节范围、说明里的覆盖统计都按新数据重算；最新一批 = 最后一个带 `data-bt` 的章节，卡片在批次日期后 30 天自动隐藏；绿色下划线只标最新一批（运行时加 class，不改章节 HTML）。
5. **验证**：`python3 build/verify.py 当前线上site目录 out/site shots/` → 应显示 `ALL PASS`。会检查：旧词条逐字段相同、旧章节 HTML 逐字节相同（比较时忽略已去掉的小测）、旧音频逐字节相同、旧卡 id 与新卡顺序不变、学习/复习队列不变、localStorage 键不变（只允许新增 `wsx-last`），并截桌面/手机 × 日间/夜间图。
   再跑 `python3 build/verify_v2.py 当前线上site目录 out/site shots/v2` 检查头部、设置面板、章节切换、配色 → `ALL PASS`（如果线上 site 还带小测，加 `--chapters-modified`）。
   朗读高亮：`python3 build/check_highlight.py 当前线上site目录 out/site` → `ALL PASS`。
6. **部署**（现在走 GitHub PR：Ethan 开 PR → 张烨合并 → 部署）：`out/deploy/` 里只有变动和新增的文件（3 个 html + data/ + 新音频），按原目录结构覆盖上传到服务器网站根目录即可；旧音频不需要重新上传。上传后浏览器强制刷新一次。
7. **提交仓库**：把 `out/site/` 同步回仓库 `site/`，`build/` 一起提交。下次更新时 `--base` 指向新的 `site/`。

## Anki 新卡顺序规则
- 「新卡顺序 = 最新新增优先，其余按故事章节」（原来的 story 模式，值不变）：
  1. 带批次标签（`bt`）的新词先出，按**最后一次课堂日期**从新到旧（`lk`），同一天再按章节、id；
  2. 旧词完全保持原来的顺序（章节 → id）。
- 筛选：「全部批次 / 10/23 新增（298）」，与主题、★、NEW 筛选叠加；清除筛选会一并清除。
- 日期排序键 `lk`：默认学期从 9 月开始（9–12 月早于次年 1–8 月），跨年时用 `--year-start-month` 调整。
- 旧存档里没有 `bt` 设置会自动补默认值，不会丢进度。

## 新词条字段（追加在 words.json 的 W 里）
沿用旧字段 `w p z t s g n d b k x h ss sf sh c new`，额外：`bt`（批次）、`ld`（最后课堂日期）、`lk`（排序键）、`cid`（当时 CSV 的 # 序号，仅供对照）。`new` 设为 0，保证原来的「只看 NEW」筛选结果不变。

## 10/30 批次记录
- 新增 323 词（站内 id 1366–1688），第 70–86 章（17 章）；旧 1365 词、69 章、旧音频和 Anki 卡片 id/顺序均未改动。
- 新词的「笔记线索」（板书位置等）不进弹窗：生成 CSV 时新行该列留空，弹窗只显示音标、释义、搭配和例句。
- 旧词在 10/26–10/30 课上又出现的日期没有回写（避免改动旧卡片）。
