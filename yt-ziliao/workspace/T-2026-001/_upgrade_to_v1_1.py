"""把 v1.0 materials.json 升级到 v1.1：追加 5 条 B 站视频直链条目。"""
import json

mat = json.load(open("/Users/fubo/Downloads/Gin-s-YouTuber-skills/yt-ziliao/workspace/T-2026-001/materials.json"))

# 更新 _meta
mat["_meta"]["schema_version"] = "yt-ziliao-materials-v1.1"
mat["_meta"]["generated_at"] = "2026-09-10T17:05:00+08:00"
mat["_meta"]["degraded"] = False
mat["_meta"]["degraded_reason_v1_1"] = "v1.1 B 站直链补强完成，11 条真直链，downgrade 状态解除"
mat["_meta"]["v1_1_added"] = "5 条 B 站真直链（V-07~V-11 BV 号格式）"
mat["_meta"]["_agents"].append("bilibili_search_v1_1")

# 5 条新视频（v1.1 唯一新增）
new_videos = [
    {
        "id": "V-07",
        "title": "史玉柱1997年巨人大厦资金链断裂崩盘现场镜头（《97年史玉柱崩塌实录》）",
        "url": "https://www.bilibili.com/video/BV1BW411r7Rx",
        "platform": "bilibili",
        "publish_date": "2020-05-27",
        "language": "zh",
        "type": "视频/纪录片式人物志",
        "authority": "中",
        "verification": "多方证实（UP主'图灵的猫'整合公开影像）",
        "stance": "中立",
        "key_facts": [
            "纪录片式一站式人物志 5小时55分",
            "覆盖巨人汉卡崛起→巨人大厦资金链断裂崩盘→欠债2.5亿→脑白金翻身→珠海首富重整"
        ],
        "quote": "5:55:47 完整时间线 一站式影像素材"
    },
    {
        "id": "V-08",
        "title": "风马牛年终秀 史玉柱自曝巨人大厦 欠债2.5亿成老赖",
        "url": "https://www.bilibili.com/video/BV1oz4y1k7oa",
        "platform": "bilibili",
        "publish_date": "2020-01-13",
        "language": "zh",
        "type": "视频/本人出镜",
        "authority": "中",
        "verification": "多方证实",
        "stance": "中立",
        "key_facts": [
            "史玉柱本人在风马牛年终秀上自述巨人大厦往事",
            "明确点出欠债2.5亿成老赖的亲历细节"
        ],
        "quote": "史玉柱本人出镜+亲历 2.5亿老赖"
    },
    {
        "id": "V-09",
        "title": "史玉柱访谈 当巨人大厦倒塌的时候是烂尾楼",
        "url": "https://www.bilibili.com/video/BV1gV4y1M7wV",
        "platform": "bilibili",
        "publish_date": "未知",
        "language": "zh",
        "type": "视频/访谈",
        "authority": "中",
        "verification": "多方证实",
        "stance": "中立",
        "key_facts": [
            "史玉柱亲述：巨人大厦倒塌时是烂尾楼盖了五层",
            "91年规划70层只盖五层——'当时还是膨胀了'"
        ],
        "quote": "亲述原话：'当时还是膨胀了'"
    },
    {
        "id": "V-10",
        "title": "遇见文和友 对话史玉柱 史大嘴开炮 毒舌点评中国互联网大佬",
        "url": "https://www.bilibili.com/video/BV1MB4y1G7Kn",
        "platform": "bilibili",
        "publish_date": "2022-09-14",
        "language": "zh",
        "type": "视频/长访谈",
        "authority": "中",
        "verification": "多方证实",
        "stance": "中立",
        "key_facts": [
            "2022年史玉柱本人出镜最新一期长访谈节目",
            "对谈主题：毒舌点评新浪/字节/网易/腾讯/阿里",
            "适合做'近年史玉柱观点/心境'章节的素材"
        ],
        "quote": "2022 史玉柱本人出镜最新长访谈"
    },
    {
        "id": "V-11",
        "title": "激荡四十年 大润发 史玉柱 巨人大厦06",
        "url": "https://www.bilibili.com/video/BV1LK4y1V7Kg",
        "platform": "bilibili",
        "publish_date": "未知",
        "language": "zh",
        "type": "视频/纪录片",
        "authority": "高",
        "verification": "多方证实",
        "stance": "中立",
        "key_facts": [
            "B站纪录片《激荡四十年》中史玉柱/巨人大厦专题切片",
            "含大润发合集（节目完整版时长未知）"
        ],
        "quote": "纪录片切片 权威信源"
    }
]

# 检查不重复
existing_ids = {it["id"] for it in mat["items"]}
for v in new_videos:
    if v["id"] not in existing_ids:
        mat["items"].append(v)

json.dump(mat, open("/Users/fubo/Downloads/Gin-s-YouTuber-skills/yt-ziliao/workspace/T-2026-001/materials.json", "w"),
          ensure_ascii=False, indent=2)
print(f"v1.1 materials.json 写入完成，总条目={len(mat['items'])}")
