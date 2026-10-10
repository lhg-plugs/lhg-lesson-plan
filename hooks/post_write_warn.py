#!/usr/bin/env python3
"""lhg-lesson-plan 硬门②：写教案 Markdown 后，若缺评价设计章节则提醒。

触发：PostToolUse / Write|Edit。只检查本次写入的单个文件：
  - 非 .md 文件 → 直接放行；
  - 内容不像教案（含"教学目标"或"教案"关键词才判）→ 直接放行；
  - 有"## 评价设计"且内容充实 → 放行；
  - 否则输出 additionalContext 提醒（不拦截，只提醒一次）。

逃生方式：LHG_LP_HOOKS_OFF=1（本次 hook 不触发）。
设计原则：只提醒、不拦截；内部出错 fail-open；零第三方依赖。
"""

import json
import os
import sys


def main() -> int:
    if os.environ.get("LHG_LP_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # fail-open

    tool_input = payload.get("tool_input", {}) or {}
    path = tool_input.get("file_path", "") or ""
    if not path.lower().endswith((".md", ".markdown")):
        return 0

    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return 0  # 读不到文件：fail-open

    # 不像教案：不打扰
    if "教学目标" not in text and "教案" not in text:
        return 0

    # 有评价设计且内容充实：放行
    if "## 评价设计" in text:
        tail = text.split("## 评价设计", 1)[1]
        # 取到下一个 ## 为止
        nxt = tail.find("\n## ")
        body = (tail[:nxt] if nxt >= 0 else tail).strip()
        if len(body) >= 20:
            return 0

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "提醒：这份教案（%s）缺少充实的「## 评价设计」章节。"
                "逆向设计要求每个教学目标都有对应的检测方式，"
                "建议补上随堂检测/作业设计后再交付；"
                "审计规则 LP-EVAL-001 会把缺评价判为 blocker。"
                % os.path.basename(path)
            ),
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
