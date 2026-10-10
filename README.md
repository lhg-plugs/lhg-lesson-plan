<!-- About 简介（推送后填写到仓库 About 栏）：
小白一句话生成完整教案的 Claude Code 插件 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-lesson-plan
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, lesson-plan, teaching, education, curriculum -->

# lhg-lesson-plan：小白一句话 → 完整教案

> **一句话介绍**：给 AI 助手装上"课程设计专家"——一句话课程主题出发，经澄清、课标/考纲对齐、逆向设计（目标→评价→活动）、教案与课件大纲生成、13 条确定性规则审计，小白也能备出结构完整、目标可测的教案。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-lesson-plan
> /plugin install lhg-lesson-plan@lhg-plugs
> ```

## 它是什么

`lhg-lesson-plan` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **4 个命令**（小白入口）：`lesson-plan` 一句话生成完整教案，`syllabus` 课标对齐与目标分解，`activity` 课堂活动设计，`audit` 教案体检
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：课程设计总纲、课标对齐、活动设计、审计方法论
- **3 个专家 agent**：教案设计、活动设计、独立审计
- **2 个硬门 hooks**：commit 前教案审计拦截、写教案缺评价章节提醒（均可一键豁免）
- **13 条确定性自查规则**：纯 Python、零第三方依赖，秒级出结果

## 4 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-lesson-plan:lesson-plan` | 一句话 → 完整教案（澄清→课标对齐→目标→教案→活动→自查→交付） | `/lhg-lesson-plan:lesson-plan "初中生物光合作用"` |
| `/lhg-lesson-plan:syllabus` | 课标/考纲对齐：拆知识点、定可测目标、输出对照表 | `/lhg-lesson-plan:syllabus "牛顿第二定律"` |
| `/lhg-lesson-plan:activity` | 课堂活动设计：七要素方案 + 教师指令逐字稿 | `/lhg-lesson-plan:activity "光合作用" 实验` |
| `/lhg-lesson-plan:audit` | 教案体检（脚本 + 人工评审清单） | `/lhg-lesson-plan:audit ./my-lesson` |

## 质量分档

- **默认 = 极速档**：流程完整、评审轮次少，确定性审计必跑。适合日常备课。
- **`--quality` = 品质档**：在 `lesson-plan` 后加 `--quality`，增加独立审计复查、多轮打磨。**诚实说明**：品质档 token 消耗约为极速档的数倍，请确认接受再使用。

## 自查说明

自查 = 确定性脚本（机器）+ 人工评审清单（人）：

1. 先跑 `scripts/audit/lesson_audit.py`（13 条规则：知识点覆盖率、课时闭合、目标—活动对齐、术语一致、评价环节），零 LLM 成本；
2. 发现分三级：**blocker**（必须修，commit 前 hook 会拦截）、**warning**（修或写豁免理由）、**nit**（顺手修）；
3. 再按 `lhg-lp-audit` skill 的评审清单过一遍脚本抓不到的（目标可测性、活动可行性、时间现实性、评价闭环）。

blocker 清零才算备完；为清零改规则算作弊，不许。

## 目录结构

```
lhg-lesson-plan/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 4 个命令：lesson-plan / syllabus / activity / audit
├── skills/                  # 4 个平台中立 skill（lhg-lp-design/syllabus/activity/audit）
├── agents/                  # 3 个专家 agent（lesson-designer / activity-designer / plan-auditor）
├── hooks/                   # 2 个硬门（commit 前审计拦截 / 缺评价提醒）+ 豁免说明
├── scripts/audit/           # 13 条确定性自查规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你要备一节新课/公开课/赛课，只有主题一句话时 → 用 `/lhg-lesson-plan:lesson-plan`
- 你写了教案但不确定目标是否可测、时间是否闭合时 → 跑 `/lhg-lesson-plan:audit`
- 课堂活动总觉得"干"，想加互动但不知道怎么设计时 → 用 `/lhg-lesson-plan:activity`
- 你是新老师，想学一套"不会翻车"的备课流程时 → 它的 skill 方法论就是备课清单

**什么时候不用：**

- 你只需要一套现成的教案模板填空 → 本插件是"设计 + 自查"流程，模板去网上找更快
- 你的课完全不需要对齐任何课标/考纲（如兴趣班、纯讲座）→ syllabus 命令可以跳过，只用 activity/audit
- 你希望 AI 自由发挥、不接受任何硬门 → 它的 commit 拦截和缺评价提醒会让你烦（可关，但那就别装它）

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack) | 小白一句话 → 高质量全栈应用 | `/plugin install lhg-fullstack@lhg-plugs` |
| [lhg-video-edit](https://github.com/lhg-plugs/lhg-video-edit) | 一句话把口播素材剪成爆款短视频（+口播脚本子命令） | `/plugin install lhg-video-edit@lhg-plugs` |
| [lhg-wechat-article](https://github.com/lhg-plugs/lhg-wechat-article) | 公众号写作专家：选题到排版一气呵成 | `/plugin install lhg-wechat-article@lhg-plugs` |
| [lhg-xiaohongshu](https://github.com/lhg-plugs/lhg-xiaohongshu) | 小红书种草专家：卖点到爆款笔记一键生成 | `/plugin install lhg-xiaohongshu@lhg-plugs` |
| [lhg-resume](https://github.com/lhg-plugs/lhg-resume) | 简历优化专家：ATS诊断到模拟面试一条龙 | `/plugin install lhg-resume@lhg-plugs` |
| [lhg-ppt](https://github.com/lhg-plugs/lhg-ppt) | PPT制作专家：述职融资答辩一键成稿 | `/plugin install lhg-ppt@lhg-plugs` |
| [lhg-excel](https://github.com/lhg-plugs/lhg-excel) | 表格数据专家：清洗透视图表一条龙 | `/plugin install lhg-excel@lhg-plugs` |
| [lhg-thesis](https://github.com/lhg-plugs/lhg-thesis) | 毕业论文助手：开题到盲审的写作流水线 | `/plugin install lhg-thesis@lhg-plugs` |
| [lhg-miniprogram](https://github.com/lhg-plugs/lhg-miniprogram) | 小程序开发专家：一句话生成微信小程序 | `/plugin install lhg-miniprogram@lhg-plugs` |
| [lhg-contract](https://github.com/lhg-plugs/lhg-contract) | 合同审查助手：风险条款标红+修改建议 | `/plugin install lhg-contract@lhg-plugs` |
| [lhg-geo](https://github.com/lhg-plugs/lhg-geo) | AI搜索优化专家：品牌在AI回答里的可见度 | `/plugin install lhg-geo@lhg-plugs` |
| [lhg-poster](https://github.com/lhg-plugs/lhg-poster) | 海报设计专家：一句话生成手机端海报 | `/plugin install lhg-poster@lhg-plugs` |
| [lhg-shopify](https://github.com/lhg-plugs/lhg-shopify) | 独立站建站专家：高转化店铺一键搭建 | `/plugin install lhg-shopify@lhg-plugs` |
| [lhg-fiction](https://github.com/lhg-plugs/lhg-fiction) | 网文写作专家：大纲到逐章+人设一致性检测 | `/plugin install lhg-fiction@lhg-plugs` |
| [lhg-drama-script](https://github.com/lhg-plugs/lhg-drama-script) | 短剧剧本专家：分集大纲到单集剧本 | `/plugin install lhg-drama-script@lhg-plugs` |
| [lhg-lit-review](https://github.com/lhg-plugs/lhg-lit-review) | 文献综述专家：框架到引用校验一条龙 | `/plugin install lhg-lit-review@lhg-plugs` |
| [lhg-salary-talk](https://github.com/lhg-plugs/lhg-salary-talk) | 薪酬谈判专家：策略到话术演练 | `/plugin install lhg-salary-talk@lhg-plugs` |
| [lhg-biz-report](https://github.com/lhg-plugs/lhg-biz-report) | 商业分析专家：数据到图文报告一键生成 | `/plugin install lhg-biz-report@lhg-plugs` |
| [lhg-study-abroad](https://github.com/lhg-plugs/lhg-study-abroad) | 留学文书专家：PS推荐信多轮打磨 | `/plugin install lhg-study-abroad@lhg-plugs` |
| [lhg-meal-plan](https://github.com/lhg-plugs/lhg-meal-plan) | 营养食谱专家：测算到一周食谱+采购单 | `/plugin install lhg-meal-plan@lhg-plugs` |
| [lhg-lesson-plan](https://github.com/lhg-plugs/lhg-lesson-plan) | 课程设计专家：一句话生成完整教案+课堂活动 | `/plugin install lhg-lesson-plan@lhg-plugs` |
| [lhg-dashboard](https://github.com/lhg-plugs/lhg-dashboard) | 数据看板专家：指标体系到图表规范一键生成 | `/plugin install lhg-dashboard@lhg-plugs` |
| *（后续插件在此追加，保持表格格式一致）* | | |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、13 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-lesson-plan/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
