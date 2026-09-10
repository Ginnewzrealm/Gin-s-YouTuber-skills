# yt-jiaoben 更新日志

## 2026-09-10

### v0.5.1 — 交付改 03-脚本.md 推送（存储重构配套）

> 规格 docs/superpowers/specs/2026-09-10-storage-workspace-design.md。
> - 阶段6 交付：lark-doc 建 docx → lark-markdown 推 `03-脚本.md`（Part 3a A 稿 + Part 3b B 稿同文档两节，+create/+overwrite）
> - 本地主档=本技能 `workspace/<编号>/script-A.md` / `script-B.md`；飞书目标=core feishu_root + `<编号> <标题>/`
> - 删「脚本字数」回填（池内无此字段，存量矛盾修复）；回填只留「选题脚本链接」URL（空则填）
> - 英雄之旅/钩子六变体/CTA 两触点方法论零改动（双夹具结论不变）

（v0.5 及更早批次记录见 git 历史：8add316 v0.5 英雄之旅主线换轴等）

### v0.5.2 — Part 2 视频素材总表规范（优化轮）

- **Part 2 升级为"视频素材总表"**：镜头号 S## ↔ B 稿 [MM:SS-MM:SS] 块一一对应；列=镜头号/时间码/画面内容/来源网站/视频链接/片段位置/状态
- **三条硬规则**：①链接 curl 复核 200 才标 ✅；②状态三态（✅/⚠️待补/❌失效当场改写画面）；③只收视频，图文不进表（01b 已有，避免重复）
- material-to-visual.md §四同步：视频类进总表、图文类沿用凭证编号
- 用户按总表批量自下载素材，不再翻全文找链接
