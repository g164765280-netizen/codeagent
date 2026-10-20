# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

"""结构化记忆档案（项目记忆 + 用户画像）。

设计参考：
- Cline Memory Bank（六文件收敛为五文件骨架）
- Hermes Agent 的 USER.md（用户画像，有界策展）
- Mem0 的 Extract-and-Update 四元决策（APPEND / REWRITE / NOOP）

三类记忆：
  1. 项目档案   <project>/.codeagent/memory-bank/  五文件
  2. 用户画像   ~/.codeagent/memory/USER.md        一个文件
  3. 散点记忆   现有 auto_memory.py，本模块不动它

更新机制：
  - Agent 主循环 turn 末（agent.py 挂点）调用 update_from_turn()
  - LLM 输出指令块（非 JSON，容错解析），每条指令指定 file + action + content
  - 每文件硬行数上限，REWRITE 超限时截断兜底
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

BANK_DIRNAME = "memory-bank"

# 文件名 → 行数上限
BANK_FILES: dict[str, int] = {
    "brief.md": 40,
    "architecture.md": 60,
    "tech.md": 40,
    "active.md": 60,
    "progress.md": 80,
}

# 用户画像
PROFILE_FILENAME = "USER.md"
PROFILE_MAX_LINES = 50

# 档案更新节流：每 N 个 turn 才做一次增量更新（避免每轮双倍 side-call）
BANK_UPDATE_TURN_INTERVAL = 2

# ---------------------------------------------------------------------------
# LLM 调用辅助（复用 auto_memory 的裸调用模式）
# ---------------------------------------------------------------------------


async def _llm_call(client: Any, prompt: str, system: str) -> str:
    """非流式语义的裸 LLM 调用：收集 TextDelta 文本。失败返回空串。"""
    from codeagent.conversation import ConversationManager, Message
    from codeagent.tools.base import StreamEnd, TextDelta

    conv = ConversationManager()
    conv.history = [Message(role="user", content=prompt)]
    collected = ""
    try:
        async for event in client.stream(conv, system=system):
            if isinstance(event, TextDelta):
                collected += event.text
            elif isinstance(event, StreamEnd):
                pass
    except Exception as e:
        logger.debug("[memory-bank] llm call failed: %s", e)
        return ""
    return collected.strip()


# ---------------------------------------------------------------------------
# 指令块解析：FILE / ACTION / CONTENT
# ---------------------------------------------------------------------------


def _parse_instructions(text: str) -> list[dict[str, str]]:
    """解析 LLM 输出的指令块序列。

    格式（每块以 === 分隔）：
        FILE: active.md
        ACTION: APPEND
        CONTENT:
        <多行内容>

    容错：大小写不敏感、块边界缺失时也能解析出最后一块。
    """
    instructions: list[dict[str, str]] = []
    if not text or text.strip().upper() in ("NONE", "NOOP", "[]"):
        return instructions

    blocks = [b for b in text.split("\n===") if "FILE:" in b.upper()]
    for block in blocks:
        lines = block.splitlines()
        cur: dict[str, str] = {}
        content_start = -1
        for i, line in enumerate(lines):
            upper = line.strip().upper()
            if upper.startswith("FILE:"):
                cur["file"] = line.split(":", 1)[1].strip()
            elif upper.startswith("ACTION:"):
                cur["action"] = line.split(":", 1)[1].strip().upper()
            elif upper.startswith("CONTENT:"):
                content_start = i + 1
                break
        if content_start >= 0 and cur.get("file") and cur.get("action"):
            content = "\n".join(lines[content_start:]).strip()
            cur["content"] = content
            instructions.append(cur)
    return instructions


def _apply_line_limit(content: str, max_lines: int) -> str:
    """硬行数上限兜底：超限保留前 max_lines 行。"""
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content
    return "\n".join(lines[:max_lines])


# ---------------------------------------------------------------------------
# 项目档案（MemoryBank）
# ---------------------------------------------------------------------------


class MemoryBank:
    """项目记忆档案：五文件结构化全貌。"""

    def __init__(self, project_root: str) -> None:
        self._root = Path(project_root).resolve()
        self._dir = self._root / ".codeagent" / BANK_DIRNAME
        self._last_update_turn = 0

    # ---------------- 读写 ----------------

    def is_initialized(self) -> bool:
        return (self._dir / "brief.md").is_file()

    def _read(self, name: str) -> str:
        try:
            return (self._dir / name).read_text(encoding="utf-8")
        except OSError:
            return ""

    def _write(self, name: str, content: str) -> None:
        max_lines = BANK_FILES[name]
        bounded = _apply_line_limit(content, max_lines)
        self._dir.mkdir(parents=True, exist_ok=True)
        (self._dir / name).write_text(bounded, encoding="utf-8")

    def _apply_instruction(self, ins: dict[str, str]) -> bool:
        name = ins["file"]
        if name not in BANK_FILES:
            return False
        action = ins["action"]
        content = ins.get("content", "")
        if not content:
            return False
        if action == "APPEND":
            old = self._read(name)
            merged = old.rstrip() + "\n\n" + content if old.strip() else content
            self._write(name, merged)
            return True
        if action == "REWRITE":
            self._write(name, content)
            return True
        return False  # NOOP / 未知动作

    # ---------------- 初始化 ----------------

    def _project_context(self) -> str:
        """收集项目概览素材：文件树 + README/CODEAGENT.md/pyproject 摘要。"""
        tree_lines: list[str] = []
        skip = {".git", ".venv", "node_modules", "__pycache__", ".codeagent", ".pytest_cache", "dist", "build"}
        for dirpath, dirnames, filenames in os.walk(self._root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            depth = len(Path(dirpath).relative_to(self._root).parts)
            if depth > 2:
                dirnames[:] = []
                continue
            for f in sorted(filenames)[:30]:
                rel = Path(dirpath).relative_to(self._root) / f
                tree_lines.append(str(rel))
        tree = "\n".join(tree_lines[:200])

        sections = [f"## File tree (top levels)\n{tree}"]
        for fname in ("README.md", "CODEAGENT.md", "pyproject.toml", "package.json"):
            p = self._root / fname
            if p.is_file():
                try:
                    body = p.read_text(encoding="utf-8")[:3000]
                    sections.append(f"## {fname}\n{body}")
                except OSError:
                    pass
        return "\n\n".join(sections)

    async def initialize(self, client: Any) -> bool:
        """首次生成五文件初稿。返回是否成功。"""
        if self.is_initialized():
            return True
        prompt = (
            "You are initializing a project memory bank for an AI coding agent. "
            "Based on the project materials below, generate FIVE markdown files.\n\n"
            "Output each file as an instruction block, exactly in this format:\n"
            "FILE: brief.md\n"
            "ACTION: REWRITE\n"
            "CONTENT:\n"
            "<markdown content>\n"
            "===\n"
            "FILE: architecture.md\n"
            "ACTION: REWRITE\n"
            "CONTENT:\n"
            "<markdown content>\n"
            "===\n"
            "(repeat for tech.md, active.md, progress.md)\n\n"
            "File purposes:\n"
            "- brief.md (<=40 lines): what this project IS and why it exists — goals, scope\n"
            "- architecture.md (<=60 lines): how it is structured — modules, layers, data flow\n"
            "- tech.md (<=40 lines): tech stack, dependencies, environment, constraints\n"
            "- active.md (<=60 lines): CURRENT work focus — what is being built/changed right now\n"
            "- progress.md (<=80 lines): milestones done, pending work, known issues\n\n"
            "Rules:\n"
            "- Factual and concise; write for a future agent session that needs to orient fast\n"
            "- Use bullet points, absolute dates (YYYY-MM-DD), file paths\n"
            "- Content in the same language as the project materials\n"
            "- active.md / progress.md may be brief stubs if the project is early-stage\n\n"
            f"Project materials:\n\n{self._project_context()}"
        )
        out = await _llm_call(client, prompt, "You are a memory bank initializer.")
        applied = 0
        for ins in _parse_instructions(out):
            if self._apply_instruction(ins):
                applied += 1
        if applied >= 3:
            logger.info("[memory-bank] initialized %d files in %s", applied, self._dir)
            return True
        logger.debug("[memory-bank] initialization failed (%d files)", applied)
        return False

    # ---------------- 增量更新 ----------------

    async def update_from_turn(
        self, client: Any, conversation: Any, turn_no: int
    ) -> None:
        """turn 末增量更新档案。带节流与并发保护。"""
        if not self.is_initialized():
            return
        if turn_no - self._last_update_turn < BANK_UPDATE_TURN_INTERVAL:
            return
        if getattr(self, "_updating", False):
            return
        self._updating = True
        try:
            self._last_update_turn = turn_no
            await self._do_update(client, conversation)
        except Exception as e:
            logger.debug("[memory-bank] update failed: %s", e)
        finally:
            self._updating = False

    async def _do_update(self, client: Any, conversation: Any) -> None:
        # 会话尾部（最近 10 条消息）
        recent = conversation.history[-10:]
        conv_lines = []
        for msg in recent:
            if msg.role == "user" and msg.content:
                conv_lines.append(f"[user]: {msg.content[:300]}")
            elif msg.role == "assistant" and msg.content:
                conv_lines.append(f"[assistant]: {msg.content[:300]}")
        if not conv_lines:
            return

        current_state = "\n\n".join(
            f"### {name}\n{self._read(name)}" for name in BANK_FILES
        )
        prompt = (
            "You maintain a project memory bank. Update it based on the latest session activity.\n\n"
            "Output ONLY the files that need changes, each as an instruction block:\n"
            "FILE: active.md\n"
            "ACTION: APPEND  (or REWRITE / NOOP)\n"
            "CONTENT:\n"
            "<new lines for APPEND, or full replacement for REWRITE>\n"
            "===\n\n"
            "Update policy:\n"
            "- active.md: APPEND when the work focus changed (<=10 lines each append); "
            "REWRITE (<=60 lines) when it exceeds the limit or the old focus is obsolete\n"
            "- progress.md: APPEND completed milestones (<=10 lines); keep newest first is NOT required\n"
            "- brief.md / architecture.md / tech.md: REWRITE only on fundamental changes\n"
            "- Most turns should produce NO instructions — output NONE when nothing meaningful changed\n\n"
            f"Current memory bank:\n\n{current_state}\n\n"
            f"Latest session activity:\n{''.join(conv_lines)}"
        )
        out = await _llm_call(client, prompt, "You are a memory bank updater.")
        for ins in _parse_instructions(out):
            self._apply_instruction(ins)

    # ---------------- 注入 ----------------

    def load_context(self) -> str:
        """恒定注入块：active + progress 全文 + 其余文件头部。"""
        if not self.is_initialized():
            return ""
        sections = []
        for name in ("active.md", "progress.md"):
            body = self._read(name).strip()
            if body:
                sections.append(f"### {name}\n{body}")
        for name in ("brief.md", "architecture.md", "tech.md"):
            body = self._read(name).strip()
            if body:
                head = "\n".join(body.splitlines()[:15])
                sections.append(f"### {name}\n{head}")
        if not sections:
            return ""
        return (
            "# projectMemoryBank\n"
            "Structured project memory (current focus, progress, overview). "
            "Use it to orient before exploring the codebase.\n\n"
            + "\n\n".join(sections)
        )

    def status_line(self) -> str:
        if not self.is_initialized():
            return "memory-bank: 未初始化"
        return f"memory-bank: {len(BANK_FILES)} files @ {self._dir}"


# ---------------------------------------------------------------------------
# 用户画像（UserProfile）
# ---------------------------------------------------------------------------

_PROFILE_SKELETON = """# USER PROFILE

## Tech Preferences
- (to be learned)

## Working Habits
- (to be learned)

## Feedback History
- (to be learned)
"""


class UserProfile:
    """跨项目用户画像：~/.codeagent/memory/USER.md，有界策展式维护。"""

    def __init__(self) -> None:
        try:
            self._path = Path.home() / ".codeagent" / "memory" / PROFILE_FILENAME
        except RuntimeError:
            self._path = None

    # ---------------- 读写 ----------------

    def exists(self) -> bool:
        return self._path is not None and self._path.is_file()

    def _read(self) -> str:
        if self._path is None:
            return ""
        try:
            return self._path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def _write(self, content: str) -> None:
        if self._path is None:
            return
        bounded = _apply_line_limit(content, PROFILE_MAX_LINES)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(bounded, encoding="utf-8")

    def ensure_initialized(self) -> bool:
        """骨架文件不存在时写入空骨架（无需 LLM）。"""
        if self.exists():
            return True
        if self._path is None:
            return False
        try:
            self._write(_PROFILE_SKELETON)
            return True
        except OSError:
            return False

    # ---------------- 增量更新 ----------------

    async def update_from_turn(self, client: Any, conversation: Any) -> None:
        if not self.exists():
            self.ensure_initialized()
            return
        if getattr(self, "_updating", False):
            return
        self._updating = True
        try:
            await self._do_update(client, conversation)
        except Exception as e:
            logger.debug("[user-profile] update failed: %s", e)
        finally:
            self._updating = False

    async def _do_update(self, client: Any, conversation: Any) -> None:
        recent = conversation.history[-10:]
        conv_lines = []
        for msg in recent:
            if msg.role == "user" and msg.content:
                conv_lines.append(f"[user]: {msg.content[:200]}")
            elif msg.role == "assistant" and msg.content:
                conv_lines.append(f"[assistant]: {msg.content[:200]}")
        if not conv_lines:
            return

        current = self._read()
        prompt = (
            "You maintain a USER PROFILE that persists across all the user's projects. "
            "Update it based on the latest session activity.\n\n"
            "The profile captures ONLY stable, cross-project traits:\n"
            "- Tech preferences (languages, frameworks, styles the user favors)\n"
            "- Working habits (language, verbosity, review style, workflow preferences)\n"
            "- Feedback history (corrections the user made to the agent — these matter most)\n\n"
            "Output an instruction block if an update is warranted:\n"
            "FILE: USER.md\n"
            "ACTION: REWRITE  (the profile is small — always full rewrite, <=50 lines)\n"
            "CONTENT:\n"
            "<full updated profile>\n\n"
            "Preserve existing learned facts. Merge new signals in. Remove stale items. "
            "If nothing cross-project-worthy happened, output NONE.\n"
            "Never store project-specific facts here (those go to project memory).\n\n"
            f"Current profile:\n\n{current}\n\n"
            f"Latest session activity:\n{''.join(conv_lines)}"
        )
        out = await _llm_call(client, prompt, "You are a user profile updater.")
        for ins in _parse_instructions(out):
            if ins.get("file", "").endswith(PROFILE_FILENAME) and ins.get("action") == "REWRITE":
                self._write(ins.get("content", ""))
                break

    # ---------------- 注入 ----------------

    def load_context(self) -> str:
        body = self._read().strip()
        if not body or "(to be learned)" in body:
            return ""
        return (
            "# userProfile\n"
            "Stable cross-project traits of the current user. "
            "Adapt your responses to these preferences.\n\n" + body
        )
