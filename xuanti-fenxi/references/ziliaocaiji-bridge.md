# ziliaocaiji 桥接约定

> 触发条件：N2 资料就绪检查未通过、需要补采六章资料包时，必须先读本文件。
> 前置条件：用户环境中已安装 ziliaocaiji 技能。

## 一、职责边界

调用方技能（xuanti-fenxi）负责：
- 检测 ziliaocaiji 是否可用
- 传入选题主体与补采范围（缺失清单）
- 接收资料包就绪通知，继续 N2 就绪复检

被调用方技能（ziliaocaiji）负责：
- 全网多源搜索、可信度评分、六章报告生成
- 报告写入飞书文档、链接回填选题表「资料采集」字段、更新「资料完整度」

本技能明确不执行以下操作：
- 不代替 ziliaocaiji 做资料采集与报告生成
- 不直接操作任何搜索接口或飞书文档接口
- 不修改资料包内容（发现资料疑点只能记入分析卡盲区清单，回采仍走 ziliaocaiji）

## 二、依赖检测

检测方式：进入 N2 时检测 ziliaocaiji 是否已安装可用。

- 已安装 → 自动调补采（Q4 拍板：不问用户）
- 未安装 → 提醒用户安装；本次分析终止，输出缺失清单与"请先运行 ziliaocaiji 补采"的指引，主流程不硬跑

## 三、输入参数

| 参数名 | 类型 | 必填 | 取值范围/格式 | 说明 |
|---|---|---|---|---|
| topic_title | string | 是 | 精化后的选题标题 | 采集主体 |
| one_liner | string | 是 | 一句话描述 | 语义上下文 |
| missing_sections | array[string] | 否 | 六章章节名 | 已知缺失范围；缺省=全量采集 |
| urgency | enum | 否 | normal / high | normal；热点选题可 high |

## 四、输出结果

| 字段名 | 类型 | 存在条件 | 说明 |
|---|---|---|---|
| status | string | 始终 | success / partial / error |
| report_url | string | success | 六章报告飞书文档链接 |
| completeness | int | success | 资料完整度 0-100 |
| missing_after | array[string] | partial | 补采后仍缺的章节 |

## 五、异常处理

| 异常情况 | 处理方式 |
|---|---|
| ziliaocaiji 未安装 | 提醒安装 + 终止本次分析，输出缺失清单 |
| status = error / partial | 以 partial 的 missing_after 或全量缺失清单为准报「资料缺失」并**终止**（铁律：缺料不硬跑）；禁止本技能自行补采 |
| report_url 缺失但 status=success | 按异常上报用户，按 success 可信度存疑处理， completeness <60 一律不进入 N3 |
