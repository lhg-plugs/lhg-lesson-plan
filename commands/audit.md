---
description: 教案体检：跑确定性审计脚本 + 人工评审清单，输出 blocker/warning/nit 分级报告。
argument-hint: [教案目录] [--fix]
---

# /lhg-lesson-plan:audit —— 教案体检

用户输入在 `$ARGUMENTS` 中：`[教案目录] [--fix]`。目录缺省为当前目录。

## 流程（加载 lhg-lp-audit 全程指导）

### 1. 跑脚本

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/lesson_audit.py --target <目录> --format text
```

记下 blocker / warning / nit 的数量与明细（含文件、行号、规则说明）。

### 2. 分级与修复

- blocker：逐条修。`--fix` 缺省即自动修（最小改动原则）；修一条用脚本复查一条。
- 修不掉的（如需用户提供真实学情、学校特殊要求）→ 列入"需人工处理"，不许为清零改规则。
- warning：修掉或写豁免理由；nit：顺手修。

### 3. 人工评审

按 `lhg-lp-audit` 第 5 节清单执行脚本抓不到的项：

- 目标可测性：目标里的"达成标准"真能在一节课里测出来吗？
- 活动可行性：教具、分组、纪律，真实课堂能不能跑起来？
- 时间现实性：新授环节有没有留"学生卡壳"的缓冲？
- 评价闭环：评价设计测的和目标说的是同一件事吗？

### 4. 输出报告

按 `lhg-lp-audit` 第 6 节模板输出自查报告，结论写清"通过 / 不通过"。

## 硬规则

- 有 blocker 就说"通过" → 不许。
- 为清零改脚本规则或阈值 → 这是作弊，不许。
- 教案里出现编造的课标条款编号 → 标 blocker，打回核实。
