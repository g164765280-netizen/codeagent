# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

"""memory/bank.py 的单元测试：指令解析、行数上限、注入组装。"""
from __future__ import annotations

from pathlib import Path

import pytest

from codeagent.memory.bank import (
    BANK_FILES,
    PROFILE_MAX_LINES,
    MemoryBank,
    UserProfile,
    _apply_line_limit,
    _parse_instructions,
)


# ---------------------------------------------------------------------------
# 指令块解析
# ---------------------------------------------------------------------------


class TestParseInstructions:
    def test_none(self):
        assert _parse_instructions("") == []
        assert _parse_instructions("NONE") == []
        assert _parse_instructions("NOOP") == []

    def test_single_append(self):
        text = (
            "FILE: active.md\n"
            "ACTION: APPEND\n"
            "CONTENT:\n"
            "- 2026-10-20: 实现 memory-bank 模块"
        )
        ins = _parse_instructions(text)
        assert len(ins) == 1
        assert ins[0]["file"] == "active.md"
        assert ins[0]["action"] == "APPEND"
        assert "memory-bank" in ins[0]["content"]

    def test_multiple_blocks(self):
        text = (
            "FILE: active.md\n"
            "ACTION: APPEND\n"
            "CONTENT:\n"
            "line A\n"
            "===\n"
            "FILE: progress.md\n"
            "ACTION: REWRITE\n"
            "CONTENT:\n"
            "# Progress\n"
            "- done item"
        )
        ins = _parse_instructions(text)
        assert len(ins) == 2
        assert ins[1]["action"] == "REWRITE"

    def test_lowercase_and_multiline_content(self):
        text = (
            "file: tech.md\n"
            "action: append\n"
            "content:\n"
            "first line\n"
            "second line\n"
            "third line"
        )
        ins = _parse_instructions(text)
        assert len(ins) == 1
        assert ins[0]["action"] == "APPEND"
        assert ins[0]["content"].count("\n") == 2

    def test_garbage_ignored(self):
        text = "random text without structure"
        assert _parse_instructions(text) == []


# ---------------------------------------------------------------------------
# 行数上限
# ---------------------------------------------------------------------------


class TestLineLimit:
    def test_within_limit(self):
        content = "\n".join(f"line {i}" for i in range(10))
        assert _apply_line_limit(content, 40) == content

    def test_over_limit_truncated(self):
        content = "\n".join(f"line {i}" for i in range(100))
        result = _apply_line_limit(content, 40)
        assert len(result.splitlines()) == 40
        assert result.startswith("line 0")


# ---------------------------------------------------------------------------
# MemoryBank 文件读写
# ---------------------------------------------------------------------------


@pytest.fixture
def bank(tmp_path: Path) -> MemoryBank:
    return MemoryBank(str(tmp_path))


class TestMemoryBank:
    def test_not_initialized(self, bank: MemoryBank):
        assert bank.is_initialized() is False
        assert bank.load_context() == ""

    def test_apply_and_load(self, bank: MemoryBank):
        bank._apply_instruction({
            "file": "brief.md", "action": "REWRITE",
            "content": "# Brief\nAI coding assistant in terminal.",
        })
        bank._apply_instruction({
            "file": "active.md", "action": "REWRITE",
            "content": "# Active\n- building memory bank",
        })
        assert bank.is_initialized() is True

        ctx = bank.load_context()
        assert "# projectMemoryBank" in ctx
        assert "brief.md" in ctx
        assert "active.md" in ctx
        assert "building memory bank" in ctx

    def test_append_merges(self, bank: MemoryBank):
        bank._apply_instruction({
            "file": "progress.md", "action": "REWRITE", "content": "# Progress\n- v0.1",
        })
        bank._apply_instruction({
            "file": "progress.md", "action": "APPEND", "content": "- v0.2 done",
        })
        body = bank._read("progress.md")
        assert "- v0.1" in body
        assert "- v0.2 done" in body

    def test_line_limit_enforced_on_write(self, bank: MemoryBank):
        long_content = "\n".join(f"row {i}" for i in range(200))
        bank._apply_instruction({
            "file": "brief.md", "action": "REWRITE", "content": long_content,
        })
        limit = BANK_FILES["brief.md"]
        assert len(bank._read("brief.md").splitlines()) == limit

    def test_unknown_file_rejected(self, bank: MemoryBank):
        assert bank._apply_instruction({
            "file": "evil.md", "action": "REWRITE", "content": "x",
        }) is False
        assert bank._apply_instruction({
            "file": "brief.md", "action": "DELETE", "content": "x",
        }) is False

    def test_update_throttle(self, bank: MemoryBank):
        # 手动初始化
        bank._apply_instruction({
            "file": "brief.md", "action": "REWRITE", "content": "b",
        })

        class _Conv:
            history = []

        class _Client:
            async def stream(self, *a, **k):
                raise AssertionError("should not be called (throttled)")

        import asyncio
        # turn 0 → turn 1 在节流窗口内，不应触发 LLM 调用，也不应推进节流水位
        asyncio.run(bank.update_from_turn(_Client(), _Conv(), turn_no=1))
        assert bank._last_update_turn == 0
        # turn 2 达到间隔（2 - 0 >= 2），水位推进（conversation 为空 → 无 LLM 调用）
        asyncio.run(bank.update_from_turn(_Client(), _Conv(), turn_no=2))
        assert bank._last_update_turn == 2

    def test_update_skips_uninitialized(self, bank: MemoryBank):
        class _Conv:
            history = []

        class _Client:
            async def stream(self, *a, **k):
                raise AssertionError("should not be called (uninitialized)")

        import asyncio
        asyncio.run(bank.update_from_turn(_Client(), _Conv(), turn_no=99))


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------


class TestUserProfile:
    def test_ensure_initialized(self, tmp_path, monkeypatch):
        profile = UserProfile()
        monkeypatch.setattr(profile, "_path", tmp_path / "USER.md")
        assert profile.exists() is False
        assert profile.ensure_initialized() is True
        assert profile.exists() is True
        # 空骨架不注入
        assert profile.load_context() == ""

    def test_load_after_content(self, tmp_path, monkeypatch):
        profile = UserProfile()
        p = tmp_path / "USER.md"
        monkeypatch.setattr(profile, "_path", p)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            "# USER PROFILE\n\n## Tech Preferences\n- prefers Python\n",
            encoding="utf-8",
        )
        ctx = profile.load_context()
        assert "# userProfile" in ctx
        assert "prefers Python" in ctx

    def test_update_parses_rewrite(self, tmp_path, monkeypatch):
        import asyncio
        profile = UserProfile()
        monkeypatch.setattr(profile, "_path", tmp_path / "USER.md")
        profile.ensure_initialized()

        from codeagent.tools.base import TextDelta

        class _Client:
            async def stream(self, *a, **k):
                yield TextDelta(
                    "FILE: USER.md\nACTION: REWRITE\nCONTENT:\n"
                    "# USER PROFILE\n\n## Tech Preferences\n- likes concise answers\n"
                )

        class _Msg:
            def __init__(self, role, content):
                self.role = role
                self.content = content

        class _Conv:
            history = [_Msg("user", "回答请简洁一点")]

        asyncio.run(profile.update_from_turn(_Client(), _Conv()))
        body = profile._read()
        assert "likes concise answers" in body
        assert len(body.splitlines()) <= PROFILE_MAX_LINES
