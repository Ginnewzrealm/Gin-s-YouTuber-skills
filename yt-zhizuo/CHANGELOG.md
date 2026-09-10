# yt-zhizuo 更新日志
## v0.2.0（2026-09-10）——存储契约重构：交付改 04-制作四件套.md 推送

> 规格 docs/superpowers/specs/2026-09-10-storage-workspace-design.md。
> - 交付：飞书 docx 单文档 → lark-markdown 推原生 `04-制作四件套.md`（+create/+overwrite，URL 不变；版本历史靠 drive +version-history）
> - 输出目录：core `dirs.briefs` → 本技能 `workspace/<编号>/briefs.md`（文件名固定）；删文档文件夹问答，飞书目标=core feishu_root
> - Part 2 宽表 9 列**不拆**（用户拍板）；四件内容/档案感/M0 配乐方法论零改动（11/11+模板自扫回归绿）

## v0.1.0（2026-09-09）——初版：制作四件套（TDD 全程：11 测试先行）

> 定位：翻译层，不是创作层。消费 yt-jiaoben 定稿 B 稿 → 一次出齐四件施工指令 →
> 扫描闸过检 → 飞书单文档（一节四部分+扫描报告）→ 回填选题表「制作四件套」字段。
> 形态：混合（开场/关键段露脸实拍 + 主体旁白无脸 B-Roll/AI 生成）。
> 工具链：自录+Adobe Podcast 修音 / 剪映国际版(Mac) / YouTube Audio Library（可升级 Epidemic Sound）。

| 件 | 内容 | 底座吸收 |
|---|---|---|
| ① 配音 brief | 标注体系（//停顿/粗体重音/[情绪]/<Speed>）+ WHY 提示（给动机不给指令）+ 分段录音参数 | voiceover-direction（clawfu，Anne Ganguzza 体系） |
| ② 分镜+B-Roll 清单（段级 B 版） | 段级分镜表：形态/画面/来源/prompt/连续性；B-Roll 逐条销号 | agentara video-storyboard 连续性规范 |
| ③ 剪辑 brief | 节奏断点（Hook 1.5-2.5s）+ 字幕（思源黑体 Heavy）+ Mac 剪映导出（4K H.264/-14 LUFS） | scripting-and-storyboarding（SCENE/纸上剪辑内核） |
| ④ 配乐提示 | 四阶段情绪板 + YT Audio Library 检索词 + 闪避规范 | social-media-skills 框架 |

- 机械闸 `scripts/scan_briefs.py`：四件节头齐 / 逐镜头有源 / 时间码连续+总时长对账 ±10% / AI 必带 prompt / 露脸必标机位景别；exit 0 才准入交付
- 铁律：零自研素材（三选一来源）、禁静默丢弃（销号制）、画面客观化、不改文案（回 jiaoben）、扫描不过不交付
- 无硬闸门：画面取舍由人在剪辑时定
- 测试：tests/test_scan_briefs.py 11 项（时间码解析/行解析/好件过/四种坏件拦/exit code）
