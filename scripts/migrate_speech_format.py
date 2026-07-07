#!/usr/bin/env python3
"""One-time migration: split LECTURE_SPEECH into [НА СЛАЙДЕ] vs [РЕЧЬ]."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEECH = ROOT / "LECTURE_SPEECH.md"

SLIDE_MARKER = re.compile(r"`\[СЛАЙД:\s*([^\]]+)\]`")
COMMIT = re.compile(r"`?\[КОММИТ\s*\d+\]`?")
META = re.compile(r"^`?\[(КОД|ПАУЗА|ВОПРОС)")


def is_table_line(s: str) -> bool:
    return s.strip().startswith("|")


def is_bullet(s: str) -> bool:
    return s.strip().startswith("- ")


def is_blockquote(s: str) -> bool:
    return s.strip().startswith(">")


def extract_bold_thesis(s: str) -> str | None:
    m = re.search(r"\*\*(.+?)\*\*", s)
    if not m:
        return None
    bold = m.group(1).strip()
    # whole line is mostly the thesis
    rest = re.sub(r"\*\*.+?\*\*", "", s).strip(" .:—–-")
    if len(rest) < 40 and len(bold) >= 12:
        return bold
    if s.strip().startswith("**") and s.strip().endswith("**"):
        return bold
    return None


def split_chunk(lines: list[str]) -> tuple[list[str], list[str]]:
    slide: list[str] = []
    speech: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue
        if META.search(stripped) or COMMIT.search(stripped):
            i += 1
            continue
        if stripped.startswith("```"):
            block = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            if i < len(lines):
                block.append(lines[i])
                i += 1
            slide.extend(block)
            continue
        if is_table_line(stripped):
            while i < len(lines) and (lines[i].strip().startswith("|") or lines[i].strip() == ""):
                if lines[i].strip():
                    slide.append(lines[i])
                i += 1
            continue
        if is_bullet(stripped):
            slide.append(stripped)
            i += 1
            continue
        if is_blockquote(stripped):
            slide.append(stripped.lstrip("> ").strip())
            i += 1
            continue
        if thesis := extract_bold_thesis(stripped):
            slide.append(thesis)
            speech.append(stripped)
            i += 1
            continue
        # ASCII diagram line (arrow flow, tree)
        if stripped.startswith(("Лента ", "Картинки ", "Баланс ", "Билет ", "├", "└", "│")) or "→" in stripped:
            slide.append(stripped)
            i += 1
            continue
        speech.append(line)
        i += 1

    return slide, speech


def migrate(text: str) -> str:
    if "[НА СЛАЙДЕ]" in text:
        return text  # already migrated

    out: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = SLIDE_MARKER.search(line)
        if m and line.strip().startswith("`[СЛАЙД"):
            out.append(line)
            i += 1
            chunk: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if SLIDE_MARKER.search(nxt) and nxt.strip().startswith("`[СЛАЙД"):
                    break
                if re.match(r"^## ", nxt) or nxt.strip() == "---":
                    break
                chunk.append(nxt)
                i += 1
            slide_lines, speech_lines = split_chunk(chunk)
            if slide_lines:
                out.append("")
                out.append("[НА СЛАЙДЕ]")
                out.extend(slide_lines)
            if speech_lines:
                out.append("")
                out.append("[РЕЧЬ]")
                out.extend(speech_lines)
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def main() -> None:
    original = SPEECH.read_text(encoding="utf-8")
    # Update header
    header = """# Полная речь лекции: «Превращаем онлайн-приложение в отказоустойчивое»

> **Два слоя:** `[НА СЛАЙДЕ]` → попадает в Keynote (тезисы, таблицы, код, схемы). `[РЕЧЬ]` → проговариваешь сам, на слайдах этого нет.
> Пометки: `[СЛАЙД: …]` — заголовок слайда · `[КОММИТ N]` — переключить коммит · `[КОД]` — сниппет на слайде · `[ПАУЗА]` / `[ВОПРОС В ЗАЛ]`.

"""
    body = original.split("---", 1)[-1] if original.startswith("# ") else original
    if original.startswith("# "):
        body = original.split("---", 1)[1] if "---" in original[100:] else original

    # Keep content after first --- 
    idx = original.find("\n---\n")
    content = original[idx + 5 :] if idx != -1 else original
    migrated = migrate(content)
    SPEECH.write_text(header + "---\n\n" + migrated.lstrip(), encoding="utf-8")
    print(f"✓ Migrated {SPEECH}")


if __name__ == "__main__":
    main()
