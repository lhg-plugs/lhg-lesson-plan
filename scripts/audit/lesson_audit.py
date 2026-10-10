#!/usr/bin/env python3
"""lhg-lesson-plan 确定性教案审计：13 条规则，零第三方依赖。

扫描目标目录的 Markdown 教案（约定见下），输出 JSON 与人类可读报告；
有 blocker 时以 exit code 2 退出，warning 仅以 exit code 1 退出（供 hooks 与 CI 使用）。

用法：
    python3 lesson_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

教案 Markdown 约定（审计脚本识别的结构）：
  - `# 标题`，首段引用块注明课时，如 `> 课时：45分钟 | 学段：初中 | 学科：生物`
  - `## 课标对齐`：课标/考纲依据说明
  - `## 教学目标`：编号列表，每条可标注认知层级，如 `1. （理解）能用自己的话解释……`
  - `## 知识点清单`：无序列表，每行一个知识点
  - `## 教学环节`：`### 环节名（N分钟）` 子章节，正文含 `覆盖知识点：A、B` 声明
  - `## 评价设计`：课堂评价/作业设计

规则文案均为本项目原创（思路受教学设计常识与布鲁姆目标分类启发，
未复制任何第三方原文）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-lesson-plan/lesson-audit"

SKIP_DIRS = {".git", "__pycache__", "node_modules", "dist", "build", "vendor"}
SCAN_EXTS = {".md", ".markdown"}

# 认知层级（由低到高）
LEVELS = ["识记", "理解", "应用", "分析", "评价", "创造"]
HIGH_LEVELS = {"应用", "分析", "评价", "创造"}

# 可观察行为动词（按层级）
OBSERVABLE_VERBS = {
    "识记": ["说出", "列举", "复述", "背诵", "识别", "默写"],
    "理解": ["解释", "说明", "举例", "概述", "描述", "区分", "阐述"],
    "应用": ["运用", "计算", "操作", "解决", "完成"],
    "分析": ["分析", "比较", "对比", "分类"],
    "评价": ["评价", "判断", "论证", "辩护"],
    "创造": ["设计", "创作", "编写", "提出", "构建", "制作"],
}
ALL_OBSERVABLE = sorted({v for vs in OBSERVABLE_VERBS.values() for v in vs})
# 不可观察动词（出现在目标动词位置即判 LP-OBJ-001）
UNOBSERVABLE = ["了解", "理解", "掌握", "知道", "体会", "感受", "熟悉", "领会"]

# 高阶活动关键词（支撑应用及以上层级的活动）
HIGH_ACTIVITIES = ["实验", "探究", "讨论", "辩论", "小组", "项目", "案例",
                   "设计", "制作", "角色扮演", "游戏", "调研", "实测"]
# 讲授类动词（活动类型单一性判断用）
LECTURE_VERBS = ["讲授", "讲解", "讲述", "演示", "板书"]
ACTIVITY_VERBS = LECTURE_VERBS + ["提问", "讨论", "实验", "练习", "游戏",
                                  "探究", "辩论", "展示", "互评", "抢答"]

TIME_TOLERANCE = 2        # 环节总和与课时总长允许误差（分钟）
SINGLE_PHASE_RATIO = 0.6  # 单环节占比超过此值报 warning
KP_SUFFIX_RE = re.compile(r"(的(概念|定义|含义|意义))$")
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
SUBSECTION_RE = re.compile(r"^###\s+(.+?)\s*$")
MINUTES_RE = re.compile(r"[（(]\s*(\d+)\s*(分钟|min)\s*[)）]")
TOTAL_MINUTES_RE = re.compile(r"课时[：:]\s*(\d+)\s*(分钟|min)?")


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line",
                 "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line,
                 snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


class Rule:
    def __init__(self, rule_id, severity, category, title):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title

    def check(self, doc, findings):
        raise NotImplementedError


class Doc:
    """解析后的教案文档。"""

    def __init__(self, path, lines):
        self.path = path
        self.lines = lines
        self.sections = {}   # 二级标题 -> [(行号, 文本)]
        self.subsections = []  # [(环节名, 分钟数|None, 起始行号, 文本)]
        self._parse()

    def _parse(self):
        cur = None
        for i, ln in enumerate(self.lines):
            m = SECTION_RE.match(ln)
            if m:
                cur = m.group(1).strip()
                self.sections.setdefault(cur, []).append((i + 1, ln))
                continue
            if cur is not None:
                self.sections[cur].append((i + 1, ln))
        # 解析教学环节子章节
        segs = self.sections.get("教学环节", [])
        cur_name, cur_min, cur_start, buf = None, None, 0, []
        for lineno, ln in segs:
            m = SUBSECTION_RE.match(ln)
            if m:
                if cur_name is not None:
                    self.subsections.append(
                        (cur_name, cur_min, cur_start, "\n".join(buf)))
                title = m.group(1).strip()
                mm = MINUTES_RE.search(title)
                cur_min = int(mm.group(1)) if mm else None
                cur_name = MINUTES_RE.sub("", title).strip()
                cur_start = lineno
                buf = []
            elif cur_name is not None:
                buf.append(ln)
        if cur_name is not None:
            self.subsections.append(
                (cur_name, cur_min, cur_start, "\n".join(buf)))

    def section_text(self, name):
        return "\n".join(ln for _, ln in self.sections.get(name, []))

    def total_minutes(self):
        for _, ln in self.sections.get("", []) + \
                self.sections.get(self._first_h1_section(), []):
            m = TOTAL_MINUTES_RE.search(ln)
            if m:
                return int(m.group(1))
        # 回退：在全文前 20 行找课时声明
        for ln in self.lines[:20]:
            m = TOTAL_MINUTES_RE.search(ln)
            if m:
                return int(m.group(1))
        return None

    def _first_h1_section(self):
        return ""  # 占位：课时声明在全文前 20 行扫描即可

    def knowledge_points(self):
        out = []
        for lineno, ln in self.sections.get("知识点清单", []):
            m = re.match(r"^\s*[-*+]\s+(.+?)\s*$", ln)
            if m:
                out.append((lineno, m.group(1).strip()))
        return out

    def objectives(self):
        out = []
        for lineno, ln in self.sections.get("教学目标", []):
            m = re.match(r"^\s*(?:\d+[.)、]|\d+\s*)\s*(.+?)\s*$", ln)
            if m and len(m.group(1)) > 3:
                out.append((lineno, m.group(1).strip()))
        return out


def kp_core(kp):
    return KP_SUFFIX_RE.sub("", kp).strip()


def collect_files(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext.lower() in SCAN_EXTS:
                out.append(os.path.join(root, f))
    return sorted(out)


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, encoding="gbk", errors="ignore") as f:
            return f.read()


def coverage_map(doc):
    """知识点 -> 覆盖它的环节名列表。显式声明优先，子串匹配兜底。"""
    phase_text = {name: text for name, _, _, text in doc.subsections}
    result = {}
    for _, kp in doc.knowledge_points():
        core = kp_core(kp)
        covered = []
        for name, _, _, text in doc.subsections:
            declared = re.findall(r"覆盖知识点[：:](.+)", text)
            hit = False
            for d in declared:
                parts = re.split(r"[、，,；;]", d)
                if any(core in p or kp in p for p in parts if p.strip()):
                    hit = True
                    break
            if not hit and (core and core in text):
                hit = True
            if hit:
                covered.append(name)
        result[kp] = covered
    return result


# ---------------- 规则注册表 ----------------
RULES = []


def rule(rule_id, severity, category, title):
    def deco(cls):
        RULES.append(Rule(rule_id, severity, category, title))
        RULES[-1].check = cls().check
        return cls
    return deco


@rule("LP-COV-001", "blocker", "覆盖率", "知识点未被任何教学环节覆盖")
class CovUncovered:
    def check(self, doc, findings):
        if not doc.subsections or not doc.knowledge_points():
            return
        cmap = coverage_map(doc)
        for kp, phases in cmap.items():
            if not phases:
                findings.append(Finding(
                    "LP-COV-001", "blocker", "覆盖率",
                    "知识点未被任何教学环节覆盖", doc.path, 0, kp,
                    "知识点「%s」在「知识点清单」中声明，但没有任何教学环节覆盖它。"
                    "请补充对应环节，或从清单中删除该知识点。" % kp))


@rule("LP-COV-002", "warning", "覆盖率", "知识点仅被导入/小结环节浅层覆盖")
class CovShallow:
    def check(self, doc, findings):
        if not doc.subsections or not doc.knowledge_points():
            return
        shallow = {"导入", "小结", "小结与作业", "课堂小结"}
        cmap = coverage_map(doc)
        for kp, phases in cmap.items():
            if phases and all(p in shallow for p in phases):
                findings.append(Finding(
                    "LP-COV-002", "warning", "覆盖率",
                    "知识点仅被导入/小结环节浅层覆盖", doc.path, 0, kp,
                    "知识点「%s」只在%s出现，没有进入新授/练习等实质环节，"
                    "学生可能只听过名字没真学会。" % (kp, "、".join(phases))))


@rule("LP-TIME-001", "blocker", "课时", "环节时长总和不等于课时总长")
class TimeMismatch:
    def check(self, doc, findings):
        total = doc.total_minutes()
        if total is None or not doc.subsections:
            return
        parts = [(n, m) for n, m, _, _ in doc.subsections if m is not None]
        if not parts:
            return
        s = sum(m for _, m in parts)
        if abs(s - total) > TIME_TOLERANCE:
            findings.append(Finding(
                "LP-TIME-001", "blocker", "课时",
                "环节时长总和不等于课时总长", doc.path, 0,
                "环节总和 %d 分钟 / 课时 %d 分钟" % (s, total),
                "各环节（%s）时长加总为 %d 分钟，与课时总长 %d 分钟相差超过 %d 分钟，"
                "课堂一定拖堂或提前下课，请调整。" % (
                    " + ".join("%s%d分钟" % p for p in parts), s, total,
                    TIME_TOLERANCE)))


@rule("LP-TIME-002", "warning", "课时", "单个环节占比超过 60%")
class TimeSingle:
    def check(self, doc, findings):
        total = doc.total_minutes()
        if total is None:
            return
        for name, minutes, lineno, _ in doc.subsections:
            if minutes is not None and minutes / total > SINGLE_PHASE_RATIO:
                findings.append(Finding(
                    "LP-TIME-002", "warning", "课时",
                    "单个环节占比超过 60%", doc.path, lineno, name,
                    "环节「%s」%d 分钟，占课时 %d 分钟的 %.0f%%，"
                    "结构失衡，学生注意力难以维持，建议拆分。" % (
                        name, minutes, total, minutes / total * 100)))


@rule("LP-TIME-003", "warning", "课时", "教学环节未标注时长")
class TimeMissing:
    def check(self, doc, findings):
        for name, minutes, lineno, _ in doc.subsections:
            if minutes is None:
                findings.append(Finding(
                    "LP-TIME-003", "warning", "课时",
                    "教学环节未标注时长", doc.path, lineno, name,
                    "环节「%s」没有标注分钟数（如「### %s（10分钟）」），"
                    "无法校验课时闭合。" % (name, name)))


@rule("LP-ALIGN-001", "warning", "对齐", "高阶教学目标缺少高阶活动支撑")
class AlignHighLevel:
    def check(self, doc, findings):
        objs = doc.objectives()
        if not objs or not doc.subsections:
            return
        phase_text = "\n".join(t for _, _, _, t in doc.subsections)
        has_high_act = any(k in phase_text for k in HIGH_ACTIVITIES)
        for lineno, text in objs:
            lv = None
            for cand in LEVELS:
                if cand in text:
                    lv = cand
                    break
            if lv in HIGH_LEVELS and not has_high_act:
                findings.append(Finding(
                    "LP-ALIGN-001", "warning", "对齐",
                    "高阶教学目标缺少高阶活动支撑", doc.path, lineno, text[:40],
                    "目标「%s……」属于「%s」层级，但教学环节中没有实验/探究/讨论/"
                    "辩论/项目等高阶活动支撑，纯讲授达不到该层级。" % (
                        text[:20], lv)))


@rule("LP-TERM-001", "warning", "术语", "知识点清单内术语表述不统一")
class TermDup:
    def check(self, doc, findings):
        def term_key(kp):
            # 只归一"的/之"与"概念/定义"后缀："X的概念"=="X概念"，
            # 但"X的意义"/"X的场所"视为不同知识点，不合并。
            k = re.sub(r"[的之]", "", kp)
            k = re.sub(r"(概念|定义)$", "", k)
            return k.strip()

        kps = doc.knowledge_points()
        seen = {}
        for lineno, kp in kps:
            key = term_key(kp)
            if key in seen and seen[key] != kp:
                findings.append(Finding(
                    "LP-TERM-001", "warning", "术语",
                    "知识点清单内术语表述不统一", doc.path, lineno, kp,
                    "「%s」与「%s」实为同一知识点、表述不一致，"
                    "请统一为一种写法，全教案保持一致。" % (seen[key], kp)))
            else:
                seen.setdefault(key, kp)


@rule("LP-EVAL-001", "blocker", "评价", "缺少评价环节")
class EvalMissing:
    def check(self, doc, findings):
        text = doc.section_text("评价设计")
        # 去掉标题行后看实质内容长度
        body = "\n".join(
            ln for _, ln in doc.sections.get("评价设计", [])
            if not SECTION_RE.match(ln)).strip()
        if len(body) < 20:
            findings.append(Finding(
                "LP-EVAL-001", "blocker", "评价",
                "缺少评价环节", doc.path, 0, "## 评价设计",
                "没有「## 评价设计」章节或内容不足 20 字。"
                "逆向设计要求先定评价：每个教学目标都要有对应的检测方式，"
                "否则无法判断学生是否学会。"))


@rule("LP-SYLL-001", "warning", "课标", "缺少课标/考纲对齐声明")
class SyllMissing:
    def check(self, doc, findings):
        body = "\n".join(
            ln for _, ln in doc.sections.get("课标对齐", [])
            if not SECTION_RE.match(ln)).strip()
        if len(body) < 10:
            findings.append(Finding(
                "LP-SYLL-001", "warning", "课标",
                "缺少课标/考纲对齐声明", doc.path, 0, "## 课标对齐",
                "没有「## 课标对齐」章节或内容不足 10 字。"
                "请写明依据的课标/考纲版本；不确定的写「需核实」，不许编条款号。"))


@rule("LP-OBJ-001", "warning", "目标", "教学目标缺少可观察行为动词")
class ObjVerb:
    def check(self, doc, findings):
        for lineno, text in doc.objectives():
            if not any(v in text for v in ALL_OBSERVABLE):
                bad = [w for w in UNOBSERVABLE if w in text]
                findings.append(Finding(
                    "LP-OBJ-001", "warning", "目标",
                    "教学目标缺少可观察行为动词", doc.path, lineno, text[:40],
                    "目标「%s……」%s。目标动词必须可观察、可测"
                    "（说出/解释/设计/评价……），「了解/掌握/理解」不可观察，请改写。" % (
                        text[:20],
                        "用了不可观察动词「%s」" % "、".join(bad) if bad else
                        "没有可观察行为动词")))


@rule("LP-OBJ-002", "warning", "目标", "教学目标未标注认知层级")
class ObjLevel:
    def check(self, doc, findings):
        for lineno, text in doc.objectives():
            if not any("（%s）" % lv in text or "(%s)" % lv in text or
                       lv in text for lv in LEVELS):
                findings.append(Finding(
                    "LP-OBJ-002", "warning", "目标",
                    "教学目标未标注认知层级", doc.path, lineno, text[:40],
                    "目标「%s……」未标注认知层级（识记/理解/应用/分析/评价/创造），"
                    "层级决定活动选型，不标注容易导致目标与活动不对齐。" % text[:20]))


@rule("LP-OBJ-003", "nit", "目标", "教学目标数量过多")
class ObjTooMany:
    def check(self, doc, findings):
        objs = doc.objectives()
        if len(objs) > 6:
            findings.append(Finding(
                "LP-OBJ-003", "nit", "目标",
                "教学目标数量过多", doc.path, 0, "共 %d 条目标" % len(objs),
                "一节课 %d 条目标，贪多嚼不烂，建议合并或拆成两节课。" % len(objs)))


@rule("LP-ACT-001", "warning", "活动", "课堂活动类型单一")
class ActSingle:
    def check(self, doc, findings):
        if not doc.subsections:
            return
        phase_text = "\n".join(t for _, _, _, t in doc.subsections)
        found = [v for v in ACTIVITY_VERBS if v in phase_text]
        if found and all(v in LECTURE_VERBS for v in found):
            findings.append(Finding(
                "LP-ACT-001", "warning", "活动",
                "课堂活动类型单一", doc.path, 0, "仅含：%s" % "、".join(found),
                "教学环节的活动动词只有讲授类（%s），整节课都是老师讲，"
                "建议按目标层级加入问答/练习/实验/讨论等活动。" % "、".join(found)))


def audit_file(path):
    text = read_text(path)
    doc = Doc(path, text.split("\n"))
    findings = []
    for r in RULES:
        try:
            r.check(doc, findings)
        except Exception as e:  # 单条规则出错不影响整体：fail-open 思想
            sys.stderr.write("rule %s error: %s\n" % (r.rule_id, e))
    return findings


def main():
    ap = argparse.ArgumentParser(description="lhg-lesson-plan 教案审计")
    ap.add_argument("--target", required=True, help="教案目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"],
                    default="nit",
                    help="低于此级别的发现不影响退出码（默认 nit，即 warning 也会以 exit 1 退出）")
    args = ap.parse_args()

    files = collect_files(args.target)
    findings = []
    for p in files:
        findings.extend(audit_file(p))

    order = {"blocker": 0, "warning": 1, "nit": 2}
    findings.sort(key=lambda f: (order[f.severity], f.file, f.line))

    summary = {
        "tool": TOOL, "version": VERSION,
        "files_scanned": len(files),
        "rules_run": len(RULES),
        "blocker": sum(1 for f in findings if f.severity == "blocker"),
        "warning": sum(1 for f in findings if f.severity == "warning"),
        "nit": sum(1 for f in findings if f.severity == "nit"),
    }

    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [f.to_dict() for f in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("教案审计报告  (%s)" % TOOL)
        print("扫描文件：%d  规则数：%d" % (
            summary["files_scanned"], summary["rules_run"]))
        print("blocker：%d  warning：%d  nit：%d" % (
            summary["blocker"], summary["warning"], summary["nit"]))
        print("=" * 60)
        for f in findings:
            print("[%s] %s  %s:%s" % (
                f.severity.upper(), f.rule_id, f.file, f.line or "-"))
            print("  %s" % f.title)
            print("  %s" % f.detail.replace("\n", " ")[:160])

    sev_exit = {"blocker": 2, "warning": 1, "nit": 0}
    threshold = {"blocker": 2, "warning": 1, "nit": 0}[args.fail_on]
    code = 0
    for f in findings:
        if sev_exit[f.severity] >= threshold:
            code = max(code, sev_exit[f.severity])
    sys.exit(code)


if __name__ == "__main__":
    main()
