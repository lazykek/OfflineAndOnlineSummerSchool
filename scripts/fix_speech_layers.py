#!/usr/bin/env python3
"""Fix LECTURE_SPEECH.md: wrap orphan prose in [РЕЧЬ], add slide bullets."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEECH = ROOT / "LECTURE_SPEECH.md"

SLIDE = re.compile(r"(`?\[СЛАЙД:\s*([^\]]+)\]`?)")
META = re.compile(r"^`?\[(КОММИТ|КОД|ПАУЗА|ВОПРОС)")
SECTION = re.compile(r"^## ")

# title fragment → bullets for [НА СЛАЙДЕ] when slide would be empty
SLIDE_BULLETS: dict[str, list[str]] = {
    "три ступени": [
        "online-only — без сети: ошибка / белый экран",
        "кэш для чтения — показать загруженное, не источник правды",
        "offline-first — локальные данные + синхронизация",
    ],
    "карта лекции": [
        "Блок 1 — кэш + инвалидация",
        "Блок 2 — offline-first, билет, outbox",
        "Блок 3 — Keychain, песочница, FaceID",
        "Блок 4 — итоги, BLE, чек-лист",
    ],
    "Сеть — это ненадёжный": [
        "Сеть — ненадёжный внешний ресурс, а не данность",
    ],
    "Два вопроса кэша": [
        "1. Ответ ещё свежий? → из кэша, 0 RTT",
        "2. Stale, но можно проверить? → conditional request (ETag / Last-Modified)",
    ],
    "RFC 9110": [
        "Freshness + validation — стандарт HTTP, не «магия Apple»",
    ],
    "таймлайн": [
        "1-й запрос → сеть → кэш",
        "2-й (fresh) → кэш",
        "После max-age → revalidate → 304 или новый body",
        "Offline → stale-if-error / наш fallback",
    ],
    "Картинки — отдельная": [
        "ImageLoader: memory → disk → network",
        "URLCache в ImageLoader отключён (urlCache = nil)",
    ],
    "редиректы": [
        "302: URLCache ключ = финальный URL",
        "Запрос по A, кэш под B → промах",
    ],
    "Кэш vs источник": [
        "Кэш — «что показать, если сеть упала»",
        "Источник правды — «данные всегда локально»",
    ],
    "QR строится": [
        "QR из локального qrPayload, не из live API",
        "Посадка возможна полностью офлайн",
    ],
    "идемпотентность": [
        "clientRequestId — повторная отправка безопасна",
        "Outbox: at-least-once → сервер дедуплицирует",
    ],
    "сценарий демо outbox": [
        "Лайк офлайн → optimistic UI",
        "Outbox → sync при появлении сети",
    ],
    "offline-кейсы": [
        "Silent push / BGAppRefresh — фоновая синхронизация",
        "NWPathMonitor — реакция на сеть",
    ],
    "модели угроз": [
        "Без модели угроз советы = карго-культ",
    ],
    "Info.plist": [
        "NSFaceIDUsageDescription",
        "UIBackgroundModes (remote-notification) — опционально",
    ],
    "финальная мысль": [
        "Сеть ненадёжна · данные локально · правда в UI",
    ],
    "Итог блока 1": [
        "Кэш ≠ источник правды → Application Support, не Caches",
    ],
    "Итог блока 2": [
        "Кэш — «что показать, если сеть упала»",
        "Источник правды — «данные всегда локально»",
    ],
    "мостик к блоку 2": [
        "Кэш помогает читать → нужен локальный источник правды",
    ],
    "BLE": [
        "Оплата терминалу без интерната у пользователя",
        "BLE / NFC — канал; криптография — отдельный слой",
    ],
}


def bullets_for_title(title: str) -> list[str] | None:
    for key, bullets in SLIDE_BULLETS.items():
        if key.lower() in title.lower():
            return bullets
    return None


def is_prose_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if META.match(s) or SECTION.match(s) or s in ("---", "[НА СЛАЙДЕ]", "[РЕЧЬ]"):
        return False
    if SLIDE.search(s):
        return False
    if s.startswith(">"):
        return False
    return True


def fix(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = SLIDE.search(line)
        if m and line.strip().startswith(("`[СЛАЙД", "[СЛАЙД")):
            out.append(line)
            i += 1
            chunk: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if SLIDE.search(nxt) and nxt.strip().startswith(("`[СЛАЙД", "[СЛАЙД")):
                    break
                if SECTION.match(nxt) or nxt.strip() == "---":
                    break
                chunk.append(nxt)
                i += 1

            na: list[str] = []
            rech: list[str] = []
            mode: str | None = None
            for cl in chunk:
                s = cl.strip()
                if s == "[НА СЛАЙДЕ]":
                    mode = "na"
                    continue
                if s == "[РЕЧЬ]":
                    mode = "rech"
                    continue
                if mode == "na":
                    if cl.strip():
                        na.append(cl)
                elif mode == "rech":
                    if cl.strip():
                        rech.append(cl)
                elif is_prose_line(cl):
                    rech.append(cl)
                elif cl.strip():
                    na.append(cl)

            na = [x for x in na if x.strip()]
            rech = [x for x in rech if x.strip()]
            title = m.group(2)
            if not na:
                injected = bullets_for_title(title)
                if injected:
                    na = [f"- {b}" for b in injected]

            if na:
                out.append("")
                out.append("[НА СЛАЙДЕ]")
                out.extend(na)
            if rech:
                out.append("")
                out.append("[РЕЧЬ]")
                out.extend(rech)
            continue

        out.append(line)
        i += 1

    return re.sub(r"\n{3,}", "\n\n", "\n".join(out))


def main() -> None:
    text = SPEECH.read_text(encoding="utf-8")
    fixed = fix(text)
    SPEECH.write_text(fixed, encoding="utf-8")
    print(f"✓ Fixed layers in {SPEECH}")


if __name__ == "__main__":
    main()
