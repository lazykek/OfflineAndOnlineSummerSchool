#!/usr/bin/env python3
"""Сборка Offline_iOS_Lecture в шаблон ЛШ2026 (presentation/Template.pptx).

Переносит контент исходной презентации слайд-в-слайд, используя backend
скилла presentation-review (lsh_builder.LshDeck). Отличия от replate.py:
- заголовок лекции попадает в плейсхолдер «Название презентации» титула;
- код-листинги идут на код-слайды (Menlo, автоподбор кегля);
- добавлены «Содержание» и шмуцтитулы по блокам 0-4;
- колонтитулы «Блок N · ...» и «N / 38» исходника не переносятся
  (в шаблоне своя нумерация и структура);
- перегруженные слайды «много буллетов + длинный код» разделены на два.
"""
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.expanduser("~/.agents/skills/presentation-review/scripts"))

from lsh_builder import (  # noqa: E402
    LshDeck, make_text_placeholder_sp, xml_escape,
    _shorten_heading, _heading_font_size, _code_font_size, _wrap,
    _render_inline_runs,
)

TEMPLATE = "presentation/Template.pptx"
OUTPUT = "presentation/Offline_iOS_Lecture_LSH.pptx"

# ---- Таблицы исходной презентации (Offline_iOS_Lecture.pptx) ---------------
# Извлечены программно из <a:tbl> исходных слайдов (scripts/_extract_tables.py)
# и захардкожены дословно, чтобы сборка не зависела от исходного файла.

TABLE_SRC_7 = [
    ['Механизм', 'Заголовки', 'Смысл'],
    ['Свежесть', 'Cache-Control: max-age=N · no-store · no-cache',
     'max-age — ответ свежий N секунд, в сеть не ходим; no-store — не сохранять вообще; no-cache — отдавать только после перепроверки'],
    ['Валидация', 'ETag ↔ If-None-Match', '«отпечаток» версии ресурса'],
    ['Валидация', 'Last-Modified ↔ If-Modified-Since', 'то же по дате — проще, но точность лишь 1 секунда'],
    ['Ответ сервера', '304 Not Modified / 200 + тело', '«не менялось, бери из кэша» / новая версия'],
]

TABLE_SRC_9 = [
    ['Политика', 'Поведение'],
    ['.useProtocolCachePolicy', 'по HTTP-заголовкам сервера — наш дефолт, пока есть сеть'],
    ['.reloadIgnoringLocalCacheData', 'всегда сеть, кэш игнорируется'],
    ['.returnCacheDataElseLoad', 'сначала кэш, сеть — если пусто'],
    ['.returnCacheDataDontLoad', 'только кэш, в сеть не ходить'],
]

TABLE_SRC_15 = [
    ['Механизм', 'Закрывает риск'],
    ['TTL', 'протухшие данные'],
    ['Версия схемы', 'несовместимый формат после обновления из App Store'],
    ['Очистка по событию (логаут)', 'чужие данные у пользователя B'],
]

TABLE_SRC_16 = [
    ['', 'Кэш', 'Источник правды'],
    ['Роль', 'фолбэк «если сеть упала»', 'первоисточник, читается всегда'],
    ['Природа данных', 'производные — можно потерять', 'данные пользователя — терять нельзя'],
    ['Папка', 'Library/Caches — ОС может удалить', 'Application Support — ОС не трогает, бэкапится'],
    ['Первый экран', 'сеть; кэш при ошибке', 'диск — сразу, без ожидания сети'],
    ['Обновление', 'следующий запрос в сеть', 'сеть обновляет фоном'],
]

TABLE_SRC_17 = [
    ['Папка', 'Назначение', 'ОС удаляет?', 'В бэкапе?'],
    ['Documents', 'пользовательские файлы, видны в Finder', 'нет', 'да'],
    ['Application Support', 'данные приложения — билет здесь', 'нет', 'да'],
    ['Library/Caches', 'URLCache, картинки — можно перекачать', 'да', 'нет'],
    ['tmp', 'временные файлы', 'да', 'нет'],
]

TABLE_SRC_21 = [
    ['Компонент', 'Роль'],
    ['NetworkMonitor', 'обёртка над NWPathMonitor — знает о появлении сети заранее, до попытки запроса'],
    ['OutboxItem', 'clientID (UUID) + действие + статус + счётчик ретраев'],
    ['OutboxStore', 'персистентная очередь (outbox.json) — переживает перезапуск'],
    ['OutboxProcessor', 'воркер: берёт pending, помечает inFlight, отправляет, ретраит с backoff'],
]

TABLE_SRC_27 = [
    ['Хранилище', 'Для чего', 'Чего нельзя'],
    ['Keychain', 'токены, пароли, ключи шифрования', 'большие объёмы данных'],
    ['UserDefaults', 'настройки, флаги', 'секреты/токены — это plain-text plist'],
    ['Documents / App Support', 'пользовательские данные, бэкапятся', 'временный кэш'],
    ['Caches / tmp', 'то, что можно перекачать', 'то, что нельзя потерять'],
    ['Core Data / SQLite', 'офлайн-датасеты', 'секреты без шифрования'],
]

TABLE_SRC_28 = [
    ['Папка', 'В бэкапе iCloud', 'ОС может удалить'],
    ['Documents', 'да', 'нет'],
    ['Application Support', 'да', 'нет'],
    ['Library/Caches', 'нет', 'да — под нехватку места'],
    ['tmp', 'нет', 'да — в любой момент'],
]

TABLE_SRC_30 = [
    ['Класс доступности', 'Когда ОС отдаёт секрет'],
    ['WhenUnlocked', 'только при разблокированном экране'],
    ['AfterFirstUnlock', 'после первой разблокировки после включения — доступен и в фоне'],
    ['+ суффикс ThisDeviceOnly', 'секрет не попадает в бэкап и не переезжает на другое устройство'],
]

TABLE_SRC_31 = [
    ['', 'UserDefaults', 'Keychain'],
    ['Физически', 'plain-text .plist в Library/Preferences', 'зашифрованная БД ОС'],
    ['Шифрование', 'нет', 'AES-256, ключи в Secure Enclave'],
    ['Бэкап', 'уезжает в iCloud как есть', 'с ThisDeviceOnly — не уезжает'],
    ['Что класть', 'настройки, флаги, имя пользователя', 'секреты: токены, пароли, ключи'],
]

TABLE_SRC_32 = [
    ['Политика LAPolicy', 'Что разрешает', 'Где используем'],
    ['.deviceOwnerAuthenticationWithBiometrics', 'только FaceID / TouchID', 'гейт на билет'],
    ['.deviceOwnerAuthentication', 'биометрия или пароль устройства', 'фолбэк (симулятор без биометрии)'],
]

TABLE_SRC_34 = [
    ['Токен', 'Класс / ACL', 'Чтение'],
    ['accessToken (коммит 6)', 'AfterFirstUnlockThisDeviceOnly', 'без биометрии — нужен фоновому outbox'],
    ['paymentToken (коммит 7)', 'SecAccessControl(.biometryCurrentSet)', 'только через FaceID на уровне ОС'],
]


def _code_font_size_wide(code_lines):
    """Кегль кода под зону L6 этого шаблона (~12.2\" ширины): при 14pt
    Menlo влезает ~100 символов в строку, поэтому пороги мягче, чем в
    _code_font_size скилла (тот калиброван под 75 символов)."""
    n = len(code_lines)
    longest = max((len(l) for l in code_lines), default=0)
    if n <= 12 and longest <= 75:
        return 16
    if n <= 20 and longest <= 95:
        return 14
    return 12


# ---- Подсветка синтаксиса (Swift + безвредно для XML/псевдосхем) -----------

SWIFT_KEYWORDS = {
    "let", "var", "func", "class", "final", "private", "if", "else",
    "guard", "return", "try", "await", "async", "throws", "throw",
    "catch", "do", "for", "while", "in", "as", "is", "nil", "true",
    "false", "self", "import", "struct", "enum", "extension", "static",
    "public", "case", "switch", "default",
}

COLOR_DEFAULT = "1F1F24"
COLOR_COMMENT = "2E7D32"
COLOR_STRING = "C41A16"
COLOR_NUMBER = "1C00CF"
COLOR_KEYWORD = "AD3DA4"
COLOR_TYPE = "3E8087"

_WORD_OR_NUM_RE = re.compile(r"\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_]*")
_STRING_RE = re.compile(r'"[^"]*"')


def _highlight_plain(text):
    """Токены вне строк/комментариев: числа, ключевые слова, типы.
    Возвращает список (text, color, bold)."""
    out = []
    pos = 0
    for m in _WORD_OR_NUM_RE.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], COLOR_DEFAULT, False))
        tok = m.group(0)
        if tok[0].isdigit():
            out.append((tok, COLOR_NUMBER, False))
        elif tok in SWIFT_KEYWORDS:
            out.append((tok, COLOR_KEYWORD, True))
        elif "A" <= tok[0] <= "Z":
            out.append((tok, COLOR_TYPE, False))
        else:
            out.append((tok, COLOR_DEFAULT, False))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], COLOR_DEFAULT, False))
    return out


def _highlight_line(line):
    """Строка кода → список (text, color, bold). Порядок: комментарий,
    строковые литералы, остальное (числа/ключевые слова/типы)."""
    runs = []
    comment = None
    cut = line.find("//")
    if cut != -1:
        comment = line[cut:]
        line = line[:cut]
    pos = 0
    for m in _STRING_RE.finditer(line):
        if m.start() > pos:
            runs.extend(_highlight_plain(line[pos:m.start()]))
        runs.append((m.group(0), COLOR_STRING, False))
        pos = m.end()
    if pos < len(line):
        runs.extend(_highlight_plain(line[pos:]))
    if comment is not None:
        runs.append((comment, COLOR_COMMENT, False))
    # Склейка соседних токенов с одинаковым стилем — меньше XML.
    merged = []
    for text, color, bold in runs:
        if merged and merged[-1][1] == color and merged[-1][2] == bold:
            merged[-1][0] += text
        else:
            merged.append([text, color, bold])
    return [(t, c, b) for t, c, b in merged if t]


class Deck(LshDeck):
    """add_code родителя не масштабирует заголовок (дефолт 54pt) —
    длинные заголовки код-слайдов вылезают за плейсхолдер. Копия метода
    с тем же подбором кегля заголовка, что в add_content, и с более
    мягким подбором кегля кода под широкую зону этого шаблона.

    add_agenda дополнен: в этом шаблоне «Содержание» (idx 10) и номера
    01..08 (idx 19..26) — тоже плейсхолдеры, их надо заполнять явно,
    иначе слайд остаётся без заголовка и нумерации."""

    # Геометрия layout 2: тексты idx 11,13,15,17 — левая колонка
    # (сверху вниз), 12,14,16,18 — правая; номера 19..22 — левая,
    # 23..26 — правая. Заполняем column-major: пункты 1-4 вниз по левой
    # колонке (01..04), 5-8 — по правой (05..08).
    AGENDA_SLOTS = [
        ("11", "19"), ("13", "20"), ("15", "21"), ("17", "22"),
        ("12", "23"), ("14", "24"), ("16", "25"), ("18", "26"),
    ]

    # Иллюстрации шмуцтитулов из demo-слайдов 3/4/5 шаблона:
    # layout_num → media-файл внутри Template.pptx.
    DIVIDER_MEDIA = {
        3: "ppt/media/image8.png",
        4: "ppt/media/image9.png",
        5: "ppt/media/image10.png",
    }

    # Кадрирование картинок шмуцтитулов — ДОСЛОВНО из demo-слайдов 3/4/5
    # Template.pptx (<a:srcRect> их <p:pic>). Без него растяжение PNG на
    # всю зону сжимает иллюстрацию по сравнению с шаблоном: отрицательные
    # поля расширяют кадр, положительные — срезают прозрачные отступы.
    DIVIDER_SRCRECT = {
        3: 'l="-12466" t="9403" r="-1" b="18502"',
        4: 'l="-5989" t="20381" r="-6362" b="22157"',
        5: 'l="-47156" r="-25198"',
    }

    def _patch_pic_srcrect(self, slide_num, srcrect_attrs, pic_id=100):
        """Вставляет <a:srcRect> в <p:pic> с данным id на уже собранном
        слайде (make_pic_sp скилла srcRect не поддерживает)."""
        path = f"ppt/slides/slide{slide_num}.xml"
        xml = self.files[path]
        was_bytes = isinstance(xml, bytes)
        if was_bytes:
            xml = xml.decode("utf-8")
        pattern = (
            rf'(<p:pic><p:nvPicPr><p:cNvPr id="{pic_id}"[^>]*/>.*?'
            rf'<a:blip r:embed="rId\d+"/>)<a:stretch><a:fillRect/></a:stretch>'
        )
        xml, n = re.subn(
            pattern,
            rf'\1<a:srcRect {srcrect_attrs}/><a:stretch/>',
            xml, count=1, flags=re.S,
        )
        if n:
            self.files[path] = xml.encode("utf-8") if was_bytes else xml

    def __init__(self, template_path):
        super().__init__(template_path)
        # Родитель уже удалил demo-слайды из self.files, но media остались;
        # читаем картинки напрямую из исходного архива шаблона.
        self._divider_images = {}
        with zipfile.ZipFile(template_path) as z:
            names = set(z.namelist())
            for layout_num, media_path in self.DIVIDER_MEDIA.items():
                if media_path in names:
                    self._divider_images[layout_num] = z.read(media_path)

    # Зона pic-плейсхолдера idx=12 в layout'ах 3/4/5 (взята из самого
    # Template.pptx — там демо-слайды кладут картинку РОВНО в эту рамку,
    # без aspect-fit: растягивают на всю ширину/высоту зоны). Родительский
    # LshDeck._layout_images() вместо этого вписывает картинку с
    # сохранением пропорций и центрирует с отступами — из-за внутренних
    # прозрачных полей в PNG-иконках это давало заметно МЕНЬШУЮ картинку,
    # чем в самом шаблоне. Поэтому здесь кладём картинку прямо в размер
    # зоны, как это делает сам шаблон.
    DIVIDER_IMG_ZONE = (6096000, 2708276, 5616575, 3600450)

    def add_quote(self, text, notes=""):
        """Переопределение родительского add_quote: плейсхолдер layout 12
        уже, чем контентная зона (9.55M EMU против 11.16M), а ручной
        перенос по 28 символов даёт рваные строки. Расширяем рамку до
        правого поля и отдаём текст одним абзацем — PowerPoint переносит
        сам по ширине рамки."""
        sp = (
            '<p:sp><p:nvSpPr>'
            '<p:cNvPr id="10" name="Текст 1"/>'
            '<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
            '<p:nvPr><p:ph type="body" idx="10"/></p:nvPr>'
            '</p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="515937" y="512763"/>'
            '<a:ext cx="11160125" cy="4200000"/></a:xfrm></p:spPr>'
            '<p:txBody><a:bodyPr/><a:lstStyle/>'
            f'<a:p><a:r><a:rPr lang="ru-RU"/><a:t>{xml_escape(text)}</a:t></a:r></a:p>'
            '</p:txBody></p:sp>'
        )
        self._add_slide(self.LAYOUT_QUOTE, [sp], notes=notes)

    def add_section_divider(self, title, number=None, notes="", images=None):
        # Родитель выбирает layout циклично по _divider_cursor — вычисляем
        # его заранее (не сдвигая курсор), чтобы подставить картинку,
        # соответствующую именно этому layout'у.
        layout_num = self.LAYOUT_DIVIDERS[
            self._divider_cursor % len(self.LAYOUT_DIVIDERS)
        ]
        if not images:
            data = self._divider_images.get(layout_num)
            if data:
                images = [{"data": data, "ext": "png"}]

        self._divider_cursor += 1
        sp_title = make_text_placeholder_sp(
            sp_id=10, ph_type="body", ph_idx="10",
            paragraphs=_wrap(title, 18, 2), name="Текст 1",
        )
        shapes = [sp_title]
        if number is not None:
            shapes.append(make_text_placeholder_sp(
                sp_id=11, ph_type="body", ph_idx="19",
                paragraphs=[f"{number:02d}"], name="Текст 2",
            ))

        img_specs = None
        imgs = [im for im in (images or []) if im.get("data")]
        if imgs:
            x, y, cx, cy = self.DIVIDER_IMG_ZONE
            img_specs = [{
                "data": imgs[0]["data"], "ext": imgs[0].get("ext", "png"),
                "x": x, "y": y, "cx": cx, "cy": cy,
            }]
        self._add_slide(layout_num, shapes, notes=notes, images=img_specs)
        # Кадрирование как в demo-слайде шаблона — иначе картинка «сжата».
        srcrect = self.DIVIDER_SRCRECT.get(layout_num)
        if img_specs and srcrect:
            self._patch_pic_srcrect(self._next_slide_num - 1, srcrect)

    def add_agenda(self, items, notes=""):
        shapes = [make_text_placeholder_sp(
            sp_id=9, ph_type="body", ph_idx="10",
            paragraphs=["Содержание"], name="Содержание",
        )]
        items = items[:8]
        # Балансируем колонки: при >4 пунктах левая получает ceil(n/2)
        # (для 5 пунктов — 3 слева, 2 справа), иначе всё в левой.
        left_count = (len(items) + 1) // 2 if len(items) > 4 else len(items)
        for i, item in enumerate(items):
            slot = i if i < left_count else 4 + (i - left_count)
            text_idx, num_idx = self.AGENDA_SLOTS[slot]
            shapes.append(make_text_placeholder_sp(
                sp_id=10 + i, ph_type="body", ph_idx=text_idx,
                paragraphs=_wrap(item, 22, 2),
                font_size_hundredths=1600,
                name=f"Текст {i + 1}",
            ))
            shapes.append(make_text_placeholder_sp(
                sp_id=30 + i, ph_type="body", ph_idx=num_idx,
                paragraphs=[f"{i + 1:02d}"],
                name=f"Номер {i + 1:02d}",
            ))
        self._add_slide(self.LAYOUT_AGENDA, shapes, notes=notes)

    def add_final(self, lines, notes=""):
        """Финал: контакты-textbox сужен, чтобы не заезжать под
        QR-плейсхолдер шаблона (x=10071100..11712575, y=512763..2154238).
        Сам декоративный QR-код шаблона (квадратный <p:pic> в правом
        верхнем углу) со слайда удаляется."""
        shapes = [make_text_placeholder_sp(
            sp_id=10, ph_type="body", ph_idx="10",
            paragraphs=["Спасибо за внимание"], name="Текст 1",
        )]
        if lines:
            shapes.append(self._make_free_textbox(
                sp_id=11,
                x=720000, y=1400000,
                cx=9168000, cy=1200000,
                paragraphs=lines,
                bullets=False,
                font_size_pt=18,
                name="Контакты",
                autofit=True,
            ))
        self._add_slide(self.LAYOUT_FINAL, shapes, notes=notes)
        self._strip_final_qr(self._next_slide_num - 1)

    def _strip_final_qr(self, slide_num):
        """Удаляет со слайда декоративный QR шаблона — квадратный <p:pic>
        размером 2008312×2008312 EMU в правом верхнем углу (rId остаётся
        в rels, это безвредно)."""
        path = f"ppt/slides/slide{slide_num}.xml"
        xml = self.files[path]
        was_bytes = isinstance(xml, bytes)
        if was_bytes:
            xml = xml.decode("utf-8")
        xml, n = re.subn(
            r'<p:pic(?:\s[^>]*)?>(?:(?!</p:pic>).)*?'
            r'<a:ext cx="2008312" cy="2008312"\s*/>(?:(?!</p:pic>).)*?</p:pic>',
            '', xml, count=1, flags=re.S,
        )
        if n:
            self.files[path] = xml.encode("utf-8") if was_bytes else xml

    def add_code(self, heading, code_lines, notes="", language=None,
                 subheading=None, bullets=None):
        shapes = []
        next_sp_id = 11
        if heading and heading.strip():
            clean_heading, tail = _shorten_heading(heading, max_len=50)
            if tail:
                notes = (tail + "\n" + notes).strip()
            shapes.append(make_text_placeholder_sp(
                sp_id=10, ph_type="body", ph_idx="15",
                paragraphs=[clean_heading],
                font_size_hundredths=_heading_font_size(clean_heading),
                name="Текст 1",
            ))

        ZONE_X = 515938
        ZONE_Y = 1500000
        ZONE_CX = 11160000
        ZONE_CY = 4900000

        if subheading and subheading.strip():
            SUB_Y = 1370000
            SUB_CY = 550000
            shapes.append(self._make_free_textbox(
                sp_id=next_sp_id,
                x=ZONE_X, y=SUB_Y, cx=ZONE_CX, cy=SUB_CY,
                paragraphs=_wrap(subheading.strip(), 80, 2),
                bullets=False, font_size_pt=18,
                name="Подзаголовок",
            ))
            next_sp_id += 1
            ZONE_Y = SUB_Y + SUB_CY + 91440
            ZONE_CY = 1500000 + 4900000 - ZONE_Y

        has_bullets = bool(bullets) and any(
            (b[0] if isinstance(b, tuple) else b).strip() for b in bullets
        )
        if has_bullets:
            BULLETS_CY = max(int(ZONE_CY * 0.30), 600000)
            shapes.append(self._make_free_textbox(
                sp_id=next_sp_id,
                x=ZONE_X, y=ZONE_Y, cx=ZONE_CX, cy=BULLETS_CY,
                paragraphs=bullets, bullets=True, font_size_pt=16,
                name="Пояснения",
            ))
            next_sp_id += 1
            ZONE_Y = ZONE_Y + BULLETS_CY + 91440
            ZONE_CY = max(ZONE_CY - BULLETS_CY - 91440, 800000)

        font_pt = _code_font_size_wide(code_lines)
        PAD = 137160
        # Высота блока по числу строк (~1.2 межстрочный: pt*12700*1.25).
        block_cy = min(
            len(code_lines) * font_pt * 15875 + 2 * PAD,
            ZONE_CY,
        )
        shapes.append(self._make_code_block_sp(
            sp_id=next_sp_id,
            x=ZONE_X, y=ZONE_Y, cx=ZONE_CX, cy=block_cy,
        ))
        next_sp_id += 1
        shapes.append(self._make_code_textbox(
            sp_id=next_sp_id,
            x=ZONE_X + PAD, y=ZONE_Y + PAD,
            cx=ZONE_CX - 2 * PAD, cy=block_cy - 2 * PAD,
            code_lines=list(code_lines),
            font_pt=font_pt,
        ))
        self._add_slide(self.LAYOUT_CONTENT, shapes, notes=notes)

    @staticmethod
    def _make_code_block_sp(sp_id, x, y, cx, cy):
        """Скруглённый прямоугольник-подложка под код (серо-голубой,
        без обводки). Идёт в shapes ПЕРЕД textbox кода — оказывается под ним."""
        return (
            f'<p:sp>'
            f'<p:nvSpPr>'
            f'<p:cNvPr id="{sp_id}" name="Подложка кода"/>'
            f'<p:cNvSpPr/>'
            f'<p:nvPr/>'
            f'</p:nvSpPr>'
            f'<p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="roundRect">'
            f'<a:avLst><a:gd name="adj" fmla="val 8000"/></a:avLst>'
            f'</a:prstGeom>'
            f'<a:solidFill><a:srgbClr val="D6DAE3"/></a:solidFill>'
            f'<a:ln><a:noFill/></a:ln>'
            f'</p:spPr>'
            f'<p:txBody>'
            f'<a:bodyPr/><a:lstStyle/>'
            f'<a:p><a:endParaRPr lang="ru-RU"/></a:p>'
            f'</p:txBody>'
            f'</p:sp>'
        )

    @staticmethod
    def _make_code_textbox(sp_id, x, y, cx, cy, code_lines, font_pt):
        """Textbox с кодом: каждая строка — набор <a:r> с подсветкой
        синтаксиса (Menlo, один кегль, разные цвета). Собран по образцу
        _make_free_textbox (mono-ветка), но с многоцветными ранами."""
        rpr_sz = f' sz="{font_pt * 100}"'
        pPr = '<a:pPr marL="0" indent="0"><a:buNone/></a:pPr>'
        ps = []
        for line in code_lines:
            line_str = str(line)
            if not line_str.strip():
                ps.append(f'<a:p>{pPr}<a:endParaRPr lang="ru-RU"{rpr_sz}/></a:p>')
                continue
            runs = []
            for text, color, bold in _highlight_line(line_str):
                b_attr = ' b="1"' if bold else ''
                runs.append(
                    f'<a:r><a:rPr lang="ru-RU"{rpr_sz}{b_attr}>'
                    f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
                    f'<a:latin typeface="Menlo"/></a:rPr>'
                    f'<a:t>{xml_escape(text)}</a:t></a:r>'
                )
            ps.append(f'<a:p>{pPr}{"".join(runs)}</a:p>')
        body = "".join(ps) or '<a:p><a:endParaRPr lang="ru-RU"/></a:p>'
        return (
            f'<p:sp>'
            f'<p:nvSpPr>'
            f'<p:cNvPr id="{sp_id}" name="Код"/>'
            f'<p:cNvSpPr txBox="1"/>'
            f'<p:nvPr/>'
            f'</p:nvSpPr>'
            f'<p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f'<a:noFill/>'
            f'</p:spPr>'
            f'<p:txBody>'
            f'<a:bodyPr wrap="square" rtlCol="0" anchor="t">'
            f'<a:normAutofit fontScale="100000" lnSpcReduction="0"/>'
            f'</a:bodyPr>'
            f'<a:lstStyle/>'
            f'{body}'
            f'</p:txBody>'
            f'</p:sp>'
        )

    # ---- Таблицы (стиль demo-слайда 16 шаблона) ------------------------

    HEADER_FILL_FIRST = "FFF9C1"   # жёлтая первая колонка header'а
    HEADER_FILL_REST = "F0EDFF"    # лавандовые остальные (точно из slide16)
    TABLE_TEXT_COLOR = "1F1F24"

    # ---- Палитра карточек/блоков (по образцу demo-слайда 16 шаблона) ----
    CARD_FILL = "F0EDFF"           # лавандовая заливка карточки
    CARD_LINE = "D9D2F5"           # тонкая рамка карточки
    CARD_TITLE_COLOR = "3B2C7F"    # фиолетовый заголовок карточки/акцент
    ACCENT_FILL = "FFF9C1"         # жёлтый акцентный блок (callout)

    @staticmethod
    def _table_cell(text, font_sz, bold, fill_xml, lnb_xml):
        b_attr = ' b="1"' if bold else ''
        if text and text.strip():
            content = (
                f'<a:r><a:rPr lang="ru-RU" sz="{font_sz}"{b_attr}>'
                f'<a:solidFill><a:srgbClr val="{Deck.TABLE_TEXT_COLOR}"/></a:solidFill>'
                f'<a:latin typeface="Arial"/><a:cs typeface="Arial"/></a:rPr>'
                f'<a:t>{xml_escape(text)}</a:t></a:r>'
            )
        else:
            content = f'<a:endParaRPr lang="ru-RU" sz="{font_sz}"/>'
        return (
            f'<a:tc><a:txBody><a:bodyPr/><a:lstStyle/>'
            f'<a:p><a:pPr algn="l"/>{content}</a:p></a:txBody>'
            f'<a:tcPr marL="72000" marR="0" marT="0" marB="0" anchor="ctr">'
            f'<a:lnL w="12700" cmpd="sng"><a:noFill/></a:lnL>'
            f'<a:lnR w="12700" cmpd="sng"><a:noFill/></a:lnR>'
            f'<a:lnT w="12700" cmpd="sng"><a:noFill/></a:lnT>'
            f'{lnb_xml}'
            f'{fill_xml}'
            f'</a:tcPr></a:tc>'
        )

    def _make_table_graphic_frame(self, sp_id, x, y, cx, header_row, body_rows,
                                  col_widths=None, compact=False, row_height=None):
        n_cols = max(len(header_row), *(len(r) for r in body_rows)) if body_rows else len(header_row)
        if compact:
            font_sz = 1300 if n_cols >= 4 else 1500
        else:
            font_sz = 1400 if n_cols >= 4 else 1600
        if col_widths and len(col_widths) == n_cols and sum(col_widths) > 0:
            total = sum(col_widths)
            widths = [cx * w // total for w in col_widths]
        else:
            widths = [cx // n_cols] * n_cols
        grid = "".join(f'<a:gridCol w="{w}"/>' for w in widths)

        lnb_none = '<a:lnB w="38100" cmpd="sng"><a:noFill/></a:lnB>'
        # Жёлтая линия-разделитель под каждой строкой тела (как в slide16).
        lnb_yellow = (
            '<a:lnB w="38100" cap="flat" cmpd="sng" algn="ctr">'
            f'<a:solidFill><a:srgbClr val="{self.HEADER_FILL_FIRST}"/></a:solidFill>'
            '<a:prstDash val="solid"/><a:round/>'
            '<a:headEnd type="none" w="med" len="med"/>'
            '<a:tailEnd type="none" w="med" len="med"/>'
            '</a:lnB>'
        )

        rows = []
        header_cells = []
        for c in range(n_cols):
            fill_color = self.HEADER_FILL_FIRST if c == 0 else self.HEADER_FILL_REST
            fill = f'<a:solidFill><a:srgbClr val="{fill_color}"/></a:solidFill>'
            text = header_row[c] if c < len(header_row) else ""
            header_cells.append(self._table_cell(text, font_sz, True, fill, lnb_none))
        rh = row_height or (500000 if compact else 600000)
        rows.append(f'<a:tr h="430000">{"".join(header_cells)}</a:tr>')
        for body_row in body_rows:
            cells = []
            for c in range(n_cols):
                text = body_row[c] if c < len(body_row) else ""
                cells.append(self._table_cell(text, font_sz, False, '<a:noFill/>', lnb_yellow))
            rows.append(f'<a:tr h="{rh}">{"".join(cells)}</a:tr>')
        total_cy = 430000 + rh * len(body_rows)

        return (
            f'<p:graphicFrame>'
            f'<p:nvGraphicFramePr>'
            f'<p:cNvPr id="{sp_id}" name="Таблица"/>'
            f'<p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr>'
            f'<p:nvPr/>'
            f'</p:nvGraphicFramePr>'
            f'<p:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{total_cy}"/></p:xfrm>'
            f'<a:graphic>'
            f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
            f'<a:tbl>'
            f'<a:tblPr firstRow="1" bandRow="1">'
            f'<a:tableStyleId>{{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}}</a:tableStyleId>'
            f'</a:tblPr>'
            f'<a:tblGrid>{grid}</a:tblGrid>'
            f'{"".join(rows)}'
            f'</a:tbl>'
            f'</a:graphicData>'
            f'</a:graphic>'
            f'</p:graphicFrame>'
        )

    def add_table(self, heading, header_row, body_rows, notes="", subheading=None,
                  col_widths=None, compact=False, row_height=None):
        """Слайд на LAYOUT_CONTENT: заголовок (как в add_content) +
        таблица в стиле demo-слайда 16 шаблона в контентной зоне."""
        shapes = []
        next_sp_id = 11
        if heading and heading.strip():
            clean_heading, tail = _shorten_heading(heading, max_len=50)
            if tail:
                notes = (tail + "\n" + notes).strip()
            shapes.append(make_text_placeholder_sp(
                sp_id=10, ph_type="body", ph_idx="15",
                paragraphs=[clean_heading],
                font_size_hundredths=_heading_font_size(clean_heading),
                name="Текст 1",
            ))

        ZONE_X = 515938
        ZONE_CX = 11160000
        TBL_Y = 1600000
        if subheading and subheading.strip():
            SUB_Y = 1370000
            SUB_CY = 550000
            shapes.append(self._make_free_textbox(
                sp_id=next_sp_id,
                x=ZONE_X, y=SUB_Y, cx=ZONE_CX, cy=SUB_CY,
                paragraphs=_wrap(subheading.strip(), 80, 2),
                bullets=False, font_size_pt=18,
                name="Подзаголовок",
            ))
            next_sp_id += 1
            TBL_Y = SUB_Y + SUB_CY + 91440

        shapes.append(self._make_table_graphic_frame(
            sp_id=next_sp_id,
            x=ZONE_X, y=TBL_Y, cx=ZONE_CX,
            header_row=header_row, body_rows=body_rows,
            col_widths=col_widths, compact=compact, row_height=row_height,
        ))
        self._add_slide(self.LAYOUT_CONTENT, shapes, notes=notes)

    # ---- Новые визуальные helpers (карточки / потоки / сравнения) ------

    @staticmethod
    def _fit_card_scale(cx, cy, title, lines, title_pt, body_pt,
                        max_scale=1.6, min_scale=0.7):
        """Подбирает масштаб кегля, чтобы текст заполнял карточку,
        но гарантированно помещался. Оценка — по числу строк с учётом
        переносов при данной ширине карточки. Дополнительно следит,
        чтобы самый длинный неразрывный токен (идентификаторы вроде
        .deviceOwnerAuthenticationWithBiometrics) влезал в строку целиком —
        PowerPoint не переносит слова по слогам и рвёт их на произвольном
        символе; при необходимости кегль уменьшается ниже 1.0."""
        import math
        avail_w_pt = max((cx - 2 * 109728) / 914400 * 72, 30)
        avail_h_pt = max((cy - 2 * 82296) / 914400 * 72, 20)

        def plain(s):
            return re.sub(r'[*`_]', '', str(s))

        def est_height(scale):
            h = 0.0
            if title and str(title).strip():
                tp = title_pt * scale
                cpl = max(int(avail_w_pt / (tp * 0.58)), 6)
                n = max(1, math.ceil(len(plain(title).strip()) / cpl))
                h += n * tp * 1.3
            for ln in (lines or []):
                bp = body_pt * scale
                s = plain(ln)
                if not s.strip():
                    h += bp * 1.3
                    continue
                cpl = max(int(avail_w_pt / (bp * 0.54)), 6)
                n = max(1, math.ceil(len(s) / cpl))
                h += n * bp * 1.3
            return h

        def token_overflows(scale):
            if title and str(title).strip():
                cpl = max(int(avail_w_pt / (title_pt * scale * 0.58)), 6)
                for tok in plain(title).split():
                    if len(tok) > cpl:
                        return True
            cpl = max(int(avail_w_pt / (body_pt * scale * 0.54)), 6)
            for ln in (lines or []):
                for tok in plain(ln).split():
                    if len(tok) > cpl:
                        return True
            return False

        scale = max_scale
        while scale > 1.0 and est_height(scale) > avail_h_pt:
            scale = round(scale - 0.05, 2)
        scale = max(scale, 1.0)
        # Понижаем и ниже 1.0, если иначе длинный токен порвётся посреди слова.
        while scale > min_scale and token_overflows(scale):
            scale = round(scale - 0.05, 2)
        return max(scale, min_scale)

    def _make_card_sp(self, sp_id, x, y, cx, cy, title, lines,
                      fill=None, line=None, title_color=None,
                      title_pt=18, body_pt=14, align="l", anchor="t",
                      autofit=True):
        """Скруглённая карточка-подложка с заголовком и строками текста.
        Стиль — светлые лавандовые блоки demo-слайда 16 шаблона.
        При autofit=True кегль автоматически увеличивается (до +60%),
        чтобы карточка не выглядела полупустой."""
        fill = fill or self.CARD_FILL
        line = line or self.CARD_LINE
        title_color = title_color or self.CARD_TITLE_COLOR
        if autofit:
            k = self._fit_card_scale(cx, cy, title, lines, title_pt, body_pt)
            title_pt = min(int(round(title_pt * k)), 30)
            body_pt = min(int(round(body_pt * k)), 24)
        ps = []
        if title and title.strip():
            ps.append(
                f'<a:p><a:pPr algn="{align}"/>'
                f'<a:r><a:rPr lang="ru-RU" sz="{title_pt * 100}" b="1">'
                f'<a:solidFill><a:srgbClr val="{title_color}"/></a:solidFill>'
                f'<a:latin typeface="Arial"/></a:rPr>'
                f'<a:t>{xml_escape(title.strip())}</a:t></a:r></a:p>'
            )
        # Если содержательных строк ≥ 2 — это перечисление: ставим маркер
        # перед каждой, иначе строки читаются как один слитный текст.
        content_lines = [str(l) for l in (lines or []) if str(l).strip()]
        use_bullets = len(content_lines) >= 2 and align == "l"
        for ln in (lines or []):
            ln_str = str(ln)
            if not ln_str.strip():
                ps.append(f'<a:p><a:endParaRPr lang="ru-RU" sz="{body_pt * 100}"/></a:p>')
                continue
            if use_bullets:
                ln_str = "•  " + ln_str
            runs = _render_inline_runs(ln_str, f' sz="{body_pt * 100}"', "Arial")
            ps.append(f'<a:p><a:pPr algn="{align}"/>{runs}</a:p>')
        body = "".join(ps) or '<a:p><a:endParaRPr lang="ru-RU"/></a:p>'
        return (
            f'<p:sp>'
            f'<p:nvSpPr>'
            f'<p:cNvPr id="{sp_id}" name="Карточка"/>'
            f'<p:cNvSpPr/>'
            f'<p:nvPr/>'
            f'</p:nvSpPr>'
            f'<p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="roundRect">'
            f'<a:avLst><a:gd name="adj" fmla="val 6000"/></a:avLst>'
            f'</a:prstGeom>'
            f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
            f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
            f'</p:spPr>'
            f'<p:txBody>'
            f'<a:bodyPr wrap="square" rtlCol="0" anchor="{anchor}" '
            f'lIns="109728" tIns="82296" rIns="109728" bIns="82296">'
            f'<a:normAutofit fontScale="100000" lnSpcReduction="0"/>'
            f'</a:bodyPr><a:lstStyle/>{body}'
            f'</p:txBody>'
            f'</p:sp>'
        )

    def _make_arrow_sp(self, sp_id, x, y, cx, cy, direction="right"):
        """Небольшая стрелка-коннектор МЕЖДУ карточками (не внутри текста)."""
        prst = "rightArrow" if direction == "right" else "downArrow"
        return (
            f'<p:sp><p:nvSpPr>'
            f'<p:cNvPr id="{sp_id}" name="Стрелка"/><p:cNvSpPr/><p:nvPr/>'
            f'</p:nvSpPr><p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>'
            f'<a:solidFill><a:srgbClr val="{self.CARD_TITLE_COLOR}"/></a:solidFill>'
            f'<a:ln><a:noFill/></a:ln>'
            f'</p:spPr>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/>'
            f'<a:p><a:endParaRPr lang="ru-RU"/></a:p></p:txBody>'
            f'</p:sp>'
        )

    def _make_labeled_arrow_sp(self, sp_id, x, y, cx, cy, label=None,
                               direction="right"):
        """Стрелка-ветка дерева решений: rightArrow/downArrow с подписью
        («да»/«нет») белым текстом внутри самой стрелки."""
        prst = "rightArrow" if direction == "right" else "downArrow"
        if label:
            para = (
                f'<a:p><a:pPr algn="ctr"/>'
                f'<a:r><a:rPr lang="ru-RU" sz="1100" b="1">'
                f'<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>'
                f'<a:latin typeface="Arial"/></a:rPr>'
                f'<a:t>{xml_escape(label)}</a:t></a:r></a:p>'
            )
        else:
            para = '<a:p><a:endParaRPr lang="ru-RU"/></a:p>'
        return (
            f'<p:sp><p:nvSpPr>'
            f'<p:cNvPr id="{sp_id}" name="Стрелка-ветка"/><p:cNvSpPr/><p:nvPr/>'
            f'</p:nvSpPr><p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>'
            f'<a:solidFill><a:srgbClr val="{self.CARD_TITLE_COLOR}"/></a:solidFill>'
            f'<a:ln><a:noFill/></a:ln>'
            f'</p:spPr>'
            f'<p:txBody>'
            f'<a:bodyPr lIns="0" tIns="0" rIns="0" bIns="0" anchor="ctr"/>'
            f'<a:lstStyle/>{para}</p:txBody>'
            f'</p:sp>'
        )

    def _make_branch_label_sp(self, sp_id, x, y, text):
        """Маленькая подпись ветки («да»/«нет») рядом со стрелкой вниз."""
        return (
            f'<p:sp><p:nvSpPr>'
            f'<p:cNvPr id="{sp_id}" name="Подпись ветки"/>'
            f'<p:cNvSpPr txBox="1"/><p:nvPr/>'
            f'</p:nvSpPr><p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/>'
            f'<a:ext cx="800000" cy="300000"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/>'
            f'</p:spPr>'
            f'<p:txBody>'
            f'<a:bodyPr lIns="0" tIns="0" rIns="0" bIns="0" anchor="ctr"/>'
            f'<a:lstStyle/>'
            f'<a:p><a:r><a:rPr lang="ru-RU" sz="1200" b="1">'
            f'<a:solidFill><a:srgbClr val="{self.CARD_TITLE_COLOR}"/></a:solidFill>'
            f'<a:latin typeface="Arial"/></a:rPr>'
            f'<a:t>{xml_escape(text)}</a:t></a:r></a:p>'
            f'</p:txBody></p:sp>'
        )

    def add_decision_tree_slide(self, heading, rows, subheading=None, notes=""):
        """Дерево решений в виде guard-chain: вопросы идут вниз по левой
        колонке, ветка-ответ уходит стрелкой вправо к жёлтому листу-результату,
        вторая ветка — стрелкой вниз к следующему вопросу.

        rows: list of dict:
          question: str — текст вопроса (лавандовая карточка слева);
          leaves: list of (label, title, lines) — правые ветки: подпись
                  стрелки, заголовок и строки жёлтого листа-результата;
          down_label: str | None — подпись стрелки вниз к следующему вопросу.
        """
        shapes = []
        head_sp, notes = self._heading_shape(heading, notes)
        if head_sp:
            shapes.append(head_sp)
        next_sp_id = 11

        ZONE_X = 515938
        ZONE_CX = 11160000
        ZONE_Y = 1620000
        ZONE_BOTTOM = 6430000

        if subheading and subheading.strip():
            sp, ZONE_Y = self._subheading_shape(next_sp_id, subheading, ZONE_X, ZONE_CX, 1370000)
            shapes.append(sp)
            next_sp_id += 1
            ZONE_Y = max(ZONE_Y, 2050000)

        n = len(rows)
        GAP = 360000
        row_h = (ZONE_BOTTOM - ZONE_Y - GAP * (n - 1)) // n
        Q_W = 3600000
        ARROW_W = 760000
        ARROW_H = 300000
        LEAF_X = ZONE_X + Q_W + ARROW_W
        LEAF_W = ZONE_X + ZONE_CX - LEAF_X

        for i, row in enumerate(rows):
            row_y = ZONE_Y + i * (row_h + GAP)
            arrow_y = row_y + (row_h - ARROW_H) // 2
            shapes.append(self._make_card_sp(
                sp_id=next_sp_id, x=ZONE_X, y=row_y, cx=Q_W, cy=row_h,
                title=row["question"], lines=[],
                title_pt=15, anchor="ctr", autofit=False,
            ))
            next_sp_id += 1

            leaves = row["leaves"]
            if len(leaves) == 1:
                label, title, lines = leaves[0]
                shapes.append(self._make_labeled_arrow_sp(
                    next_sp_id, ZONE_X + Q_W, arrow_y, ARROW_W, ARROW_H, label))
                next_sp_id += 1
                shapes.append(self._make_card_sp(
                    sp_id=next_sp_id, x=LEAF_X, y=row_y, cx=LEAF_W, cy=row_h,
                    title=title, lines=lines,
                    fill=self.ACCENT_FILL, line="E8DF8F",
                    title_pt=15, body_pt=13, anchor="ctr", autofit=False,
                ))
                next_sp_id += 1
            else:
                leaf_w = (LEAF_W - ARROW_W * (len(leaves) - 1)) // len(leaves)
                lx = ZONE_X + Q_W
                for label, title, lines in leaves:
                    shapes.append(self._make_labeled_arrow_sp(
                        next_sp_id, lx, arrow_y, ARROW_W, ARROW_H, label))
                    next_sp_id += 1
                    lx += ARROW_W
                    shapes.append(self._make_card_sp(
                        sp_id=next_sp_id, x=lx, y=row_y, cx=leaf_w, cy=row_h,
                        title=title, lines=lines,
                        fill=self.ACCENT_FILL, line="E8DF8F",
                        title_pt=15, body_pt=13, anchor="ctr", autofit=False,
                    ))
                    next_sp_id += 1
                    lx += leaf_w

            down = row.get("down_label")
            if down is not None and i < n - 1:
                qcx = ZONE_X + Q_W // 2
                ay = row_y + row_h + 30000
                ah = GAP - 60000
                shapes.append(self._make_labeled_arrow_sp(
                    next_sp_id, qcx - 120000, ay, 240000, ah, None, "down"))
                next_sp_id += 1
                shapes.append(self._make_branch_label_sp(
                    next_sp_id, qcx + 200000, ay + max((ah - 300000) // 2, 0), down))
                next_sp_id += 1

        self._add_slide(self.LAYOUT_CONTENT, shapes, notes=notes)

    def _heading_shape(self, heading, notes):
        """Общий заголовок content-слайда (body#15) + возможный tail в notes."""
        if not (heading and heading.strip()):
            return None, notes
        clean_heading, tail = _shorten_heading(heading, max_len=50)
        if tail:
            notes = (tail + "\n" + notes).strip()
        return make_text_placeholder_sp(
            sp_id=10, ph_type="body", ph_idx="15",
            paragraphs=[clean_heading],
            font_size_hundredths=_heading_font_size(clean_heading),
            name="Текст 1",
        ), notes

    def _subheading_shape(self, sp_id, subheading, zone_x, zone_cx, y):
        """Свободный подзаголовок под title. Возвращает (shape, new_y)."""
        SUB_CY = 550000
        sp = self._make_free_textbox(
            sp_id=sp_id, x=zone_x, y=y, cx=zone_cx, cy=SUB_CY,
            paragraphs=_wrap(subheading.strip(), 90, 2),
            bullets=False, font_size_pt=18, name="Подзаголовок",
        )
        return sp, y + SUB_CY + 91440

    def add_cards_slide(self, heading, cards, columns=None, subheading=None,
                        notes="", callout=None):
        """2–6 карточек с заголовком и 1–2 строками текста.

        cards: list of dict {"title": str, "lines": [str, ...]} или
               list of (title, lines).
        columns: сколько карточек в ряду (по умолчанию — по числу карточек,
                 максимум 3 в ряду).
        callout: опциональный нижний акцентный блок (жёлтый).
        """
        shapes = []
        head_sp, notes = self._heading_shape(heading, notes)
        if head_sp:
            shapes.append(head_sp)
        next_sp_id = 11

        ZONE_X = 515938
        ZONE_CX = 11160000
        ZONE_Y = 1620000
        ZONE_BOTTOM = 6450000

        if subheading and subheading.strip():
            sp, ZONE_Y = self._subheading_shape(next_sp_id, subheading, ZONE_X, ZONE_CX, 1370000)
            shapes.append(sp)
            next_sp_id += 1
            ZONE_Y = max(ZONE_Y, 2050000)

        norm = []
        for c in cards:
            if isinstance(c, dict):
                norm.append((c.get("title", ""), c.get("lines", [])))
            else:
                norm.append((c[0], c[1] if len(c) > 1 else []))
        n = len(norm)
        cols = columns or min(n, 3)
        cols = max(1, cols)
        rows = (n + cols - 1) // cols

        callout_cy = 0
        if callout:
            callout_cy = 760000
        cards_bottom = ZONE_BOTTOM - (callout_cy + 137160 if callout else 0)

        GAP = 228600
        col_w = (ZONE_CX - GAP * (cols - 1)) // cols
        row_h = (cards_bottom - ZONE_Y - GAP * (rows - 1)) // rows

        base_title_pt = 20 if n > 3 else 22
        base_body_pt = 16 if n > 3 else 18
        # Единый масштаб для всех карточек слайда: берём минимум по карточкам,
        # чтобы текст в блоках был одного кегля, а не «кто во что горазд».
        k = min(
            self._fit_card_scale(col_w, row_h, title, lines,
                                 base_title_pt, base_body_pt)
            for title, lines in norm
        ) if norm else 1.0
        uni_title_pt = min(int(round(base_title_pt * k)), 30)
        uni_body_pt = min(int(round(base_body_pt * k)), 24)
        for i, (title, lines) in enumerate(norm):
            r = i // cols
            c = i % cols
            cx0 = ZONE_X + c * (col_w + GAP)
            cy0 = ZONE_Y + r * (row_h + GAP)
            shapes.append(self._make_card_sp(
                sp_id=next_sp_id, x=cx0, y=cy0, cx=col_w, cy=row_h,
                title=title, lines=lines,
                title_pt=uni_title_pt, body_pt=uni_body_pt,
                anchor="ctr", autofit=False,
            ))
            next_sp_id += 1

        if callout:
            shapes.append(self._make_card_sp(
                sp_id=next_sp_id,
                x=ZONE_X, y=ZONE_BOTTOM - callout_cy, cx=ZONE_CX, cy=callout_cy,
                title=None, lines=[callout],
                fill=self.ACCENT_FILL, line="E8DF8F",
                body_pt=18, align="ctr", anchor="ctr",
            ))
            next_sp_id += 1

        self._add_slide(self.LAYOUT_CONTENT, shapes, notes=notes)

    def add_event_action_table(self, heading, rows, left_title="Событие",
                               right_title="Действие", third_title=None,
                               subheading=None, notes=""):
        """Замена inline-конструкций «A → B» на таблицу событие→действие.

        rows: list of tuples/lists с 2 или 3 элементами.
        """
        header = [left_title, right_title]
        if third_title:
            header.append(third_title)
        body = [list(r) for r in rows]
        self.add_table(heading, header, body, notes=notes, subheading=subheading)

    def add_flow_cards_slide(self, heading, steps, orientation="horizontal",
                             caption=None, subheading=None, notes=""):
        """Цепочка крупных этапов; стрелки — только МЕЖДУ карточками.

        steps: list of dict {"title": str, "lines": [str]} или (title, lines)
               или просто str.
        """
        shapes = []
        head_sp, notes = self._heading_shape(heading, notes)
        if head_sp:
            shapes.append(head_sp)
        next_sp_id = 11

        ZONE_X = 515938
        ZONE_CX = 11160000
        ZONE_Y = 1720000
        ZONE_BOTTOM = 6430000

        if subheading and subheading.strip():
            sp, ZONE_Y = self._subheading_shape(next_sp_id, subheading, ZONE_X, ZONE_CX, 1370000)
            shapes.append(sp)
            next_sp_id += 1
            ZONE_Y = max(ZONE_Y, 2050000)

        norm = []
        for s in steps:
            if isinstance(s, dict):
                norm.append((s.get("title", ""), s.get("lines", [])))
            elif isinstance(s, (tuple, list)):
                norm.append((s[0], s[1] if len(s) > 1 else []))
            else:
                norm.append((str(s), []))
        n = len(norm)

        caption_cy = 760000 if caption else 0
        area_bottom = ZONE_BOTTOM - (caption_cy + 137160 if caption else 0)

        if orientation == "horizontal":
            ARROW = 360000
            total_gap = ARROW * (n - 1)
            card_w = (ZONE_CX - total_gap) // n
            card_h = min(area_bottom - ZONE_Y, 2600000)
            card_y = ZONE_Y + (area_bottom - ZONE_Y - card_h) // 2
            # Кегль зависит от ширины карточки: чем меньше шагов в ряду,
            # тем крупнее текст, чтобы карточки не выглядели пустыми.
            flow_title_pt = 20 if n <= 3 else (18 if n == 4 else 17)
            flow_body_pt = 16 if n <= 3 else (16 if n == 4 else 15)
            # Единый масштаб для всех карточек цепочки — одинаковый кегль.
            k = min(
                self._fit_card_scale(card_w, card_h, title, lines,
                                     flow_title_pt, flow_body_pt)
                for title, lines in norm
            ) if norm else 1.0
            flow_title_pt = min(int(round(flow_title_pt * k)), 30)
            flow_body_pt = min(int(round(flow_body_pt * k)), 24)
            for i, (title, lines) in enumerate(norm):
                cx0 = ZONE_X + i * (card_w + ARROW)
                shapes.append(self._make_card_sp(
                    sp_id=next_sp_id, x=cx0, y=card_y, cx=card_w, cy=card_h,
                    title=title, lines=lines,
                    title_pt=flow_title_pt, body_pt=flow_body_pt,
                    anchor="t", autofit=False,
                ))
                next_sp_id += 1
                if i < n - 1:
                    ax = cx0 + card_w + int(ARROW * 0.12)
                    aw = int(ARROW * 0.76)
                    ah = 240000
                    ay = card_y + (card_h - ah) // 2
                    shapes.append(self._make_arrow_sp(next_sp_id, ax, ay, aw, ah, "right"))
                    next_sp_id += 1
        else:
            ARROW = 200000
            total_gap = ARROW * (n - 1)
            card_h = (area_bottom - ZONE_Y - total_gap) // n
            for i, (title, lines) in enumerate(norm):
                cy0 = ZONE_Y + i * (card_h + ARROW)
                shapes.append(self._make_card_sp(
                    sp_id=next_sp_id, x=ZONE_X, y=cy0, cx=ZONE_CX, cy=card_h,
                    title=title, lines=lines, title_pt=20, body_pt=16,
                    anchor="ctr",
                ))
                next_sp_id += 1
                if i < n - 1:
                    aw = 300000
                    ah = int(ARROW * 0.8)
                    ax = ZONE_X + (ZONE_CX - aw) // 2
                    ay = cy0 + card_h + int(ARROW * 0.1)
                    shapes.append(self._make_arrow_sp(next_sp_id, ax, ay, aw, ah, "down"))
                    next_sp_id += 1

        if caption:
            shapes.append(self._make_card_sp(
                sp_id=next_sp_id,
                x=ZONE_X, y=ZONE_BOTTOM - caption_cy, cx=ZONE_CX, cy=caption_cy,
                title=None, lines=[caption],
                fill=self.ACCENT_FILL, line="E8DF8F",
                body_pt=18, align="ctr", anchor="ctr",
            ))
            next_sp_id += 1

        self._add_slide(self.LAYOUT_CONTENT, shapes, notes=notes)

    def add_compare_cards(self, heading, columns, subheading=None,
                          notes="", callout=None):
        """Две-три большие колонки сравнения.

        columns: list of dict {"title": str, "lines": [str], "highlight": bool}.
        """
        shapes = []
        head_sp, notes = self._heading_shape(heading, notes)
        if head_sp:
            shapes.append(head_sp)
        next_sp_id = 11

        ZONE_X = 515938
        ZONE_CX = 11160000
        ZONE_Y = 1720000
        ZONE_BOTTOM = 6430000

        if subheading and subheading.strip():
            sp, ZONE_Y = self._subheading_shape(next_sp_id, subheading, ZONE_X, ZONE_CX, 1370000)
            shapes.append(sp)
            next_sp_id += 1
            ZONE_Y = max(ZONE_Y, 2050000)

        callout_cy = 800000 if callout else 0
        area_bottom = ZONE_BOTTOM - (callout_cy + 137160 if callout else 0)

        n = len(columns)
        GAP = 274320
        col_w = (ZONE_CX - GAP * (n - 1)) // n
        col_h = area_bottom - ZONE_Y
        for i, col in enumerate(columns):
            cx0 = ZONE_X + i * (col_w + GAP)
            hl = col.get("highlight")
            shapes.append(self._make_card_sp(
                sp_id=next_sp_id, x=cx0, y=ZONE_Y, cx=col_w, cy=col_h,
                title=col.get("title", ""), lines=col.get("lines", []),
                fill=self.ACCENT_FILL if hl else self.CARD_FILL,
                line="E8DF8F" if hl else self.CARD_LINE,
                title_pt=22, body_pt=17,
            ))
            next_sp_id += 1

        if callout:
            shapes.append(self._make_card_sp(
                sp_id=next_sp_id,
                x=ZONE_X, y=ZONE_BOTTOM - callout_cy, cx=ZONE_CX, cy=callout_cy,
                title=None, lines=[callout],
                fill=self.ACCENT_FILL, line="E8DF8F",
                body_pt=18, align="ctr", anchor="ctr",
            ))
            next_sp_id += 1

        self._add_slide(self.LAYOUT_CONTENT, shapes, notes=notes)

    def add_callout_grid(self, heading, callout, items, subheading=None, notes=""):
        """Один акцентный тезис (крупный жёлтый блок) + 2–4 поясняющих блока.

        items: list of dict {"title": str, "lines": [str]} или (title, lines).
        """
        shapes = []
        head_sp, notes = self._heading_shape(heading, notes)
        if head_sp:
            shapes.append(head_sp)
        next_sp_id = 11

        ZONE_X = 515938
        ZONE_CX = 11160000
        ZONE_Y = 1620000
        ZONE_BOTTOM = 6450000

        if subheading and subheading.strip():
            sp, ZONE_Y = self._subheading_shape(next_sp_id, subheading, ZONE_X, ZONE_CX, 1370000)
            shapes.append(sp)
            next_sp_id += 1
            ZONE_Y = max(ZONE_Y, 2050000)

        # Верхний акцентный блок
        CALLOUT_CY = 1150000
        shapes.append(self._make_card_sp(
            sp_id=next_sp_id, x=ZONE_X, y=ZONE_Y, cx=ZONE_CX, cy=CALLOUT_CY,
            title=None, lines=[callout],
            fill=self.ACCENT_FILL, line="E8DF8F",
            body_pt=22, align="ctr", anchor="ctr",
        ))
        next_sp_id += 1

        grid_y = ZONE_Y + CALLOUT_CY + 205740
        norm = []
        for it in items:
            if isinstance(it, dict):
                norm.append((it.get("title", ""), it.get("lines", [])))
            else:
                norm.append((it[0], it[1] if len(it) > 1 else []))
        n = len(norm)
        cols = n if n <= 2 else (n + 1) // 2 if n == 3 else 2
        cols = min(n, 4) if n <= 2 else (3 if n == 3 else 2)
        rows = (n + cols - 1) // cols
        GAP = 228600
        col_w = (ZONE_CX - GAP * (cols - 1)) // cols
        row_h = (ZONE_BOTTOM - grid_y - GAP * (rows - 1)) // rows
        for i, (title, lines) in enumerate(norm):
            r = i // cols
            c = i % cols
            cx0 = ZONE_X + c * (col_w + GAP)
            cy0 = grid_y + r * (row_h + GAP)
            shapes.append(self._make_card_sp(
                sp_id=next_sp_id, x=cx0, y=cy0, cx=col_w, cy=row_h,
                title=title, lines=lines, title_pt=20, body_pt=16,
            ))
            next_sp_id += 1

        self._add_slide(self.LAYOUT_CONTENT, shapes, notes=notes)


def _jpeg_size(data):
    """(width, height) из JPEG по SOF-маркеру, без Pillow."""
    i = 2
    n = len(data)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD9:
            i += 2
            continue
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h = int.from_bytes(data[i + 5:i + 7], "big")
            w = int.from_bytes(data[i + 7:i + 9], "big")
            return w, h
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return None


def add_title_slide(deck, title_text, name, position, subtitle,
                    photo_path=None):
    """Титул: название лекции в body#10 (кегль под длину), имя/должность в
    body#11, подзаголовок свободным textbox. Если передан photo_path —
    фото спикера кладётся в квадратную зону pic-плейсхолдера #12
    (центр-кроп через srcRect); иначе остаётся пустой плейсхолдер."""
    from lsh_builder import xml_escape
    # Layout задаёт фиксированный межстрочный интервал 51pt (под кегль
    # 54pt). Для названия в 28pt перебиваем его в pPr на 34pt, иначе
    # между строками получается огромный зазор.
    title_sp = (
        '<p:sp><p:nvSpPr>'
        '<p:cNvPr id="9" name="Название презентации"/>'
        '<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
        '<p:nvPr><p:ph type="body" idx="10"/></p:nvPr>'
        '</p:nvSpPr><p:spPr/>'
        '<p:txBody><a:bodyPr/><a:lstStyle/>'
        '<a:p><a:pPr><a:lnSpc><a:spcPts val="3400"/></a:lnSpc></a:pPr>'
        f'<a:r><a:rPr lang="ru-RU" sz="2800"/><a:t>{xml_escape(title_text)}</a:t></a:r>'
        '</a:p></p:txBody></p:sp>'
    )
    shapes = [
        title_sp,
        make_text_placeholder_sp(
            sp_id=10, ph_type="body", ph_idx="11",
            paragraphs=[name, position], name="Имя и должность",
        ),
    ]

    photo_data = None
    if photo_path and os.path.exists(photo_path):
        with open(photo_path, "rb") as f:
            photo_data = f.read()
    if photo_data is None:
        # Пустой pic-плейсхолдер, чтобы в PowerPoint осталась зона
        # «Место для фотографии спикера».
        shapes.append(make_text_placeholder_sp(
            sp_id=12, ph_type="pic", ph_idx="12",
            paragraphs=[], name="Фото спикера",
        ))

    if subtitle:
        shapes.append(deck._make_free_textbox(
            sp_id=13, x=515938, y=4700000, cx=9000000, cy=300000,
            paragraphs=[subtitle], bullets=False, font_size_pt=16,
            name="Подзаголовок",
        ))

    img_specs = None
    if photo_data is not None:
        # Квадратная зона фото спикера — как в demo-слайде 1 шаблона.
        img_specs = [{
            "data": photo_data, "ext": "jpeg",
            "x": 515938, "y": 4978382, "cx": 1366855, "cy": 1366855,
            "name": "Фото спикера",
        }]
    deck._add_slide(deck.LAYOUT_TITLE, shapes, images=img_specs)

    if photo_data is not None:
        # Центр-кроп до квадрата, чтобы фото не сплющилось в рамке 1:1.
        size = _jpeg_size(photo_data)
        if size:
            w, h = size
            if h > w:
                cut = (h - w) * 100000 // (2 * h)
                srcrect = f't="{cut}" b="{cut}"'
            elif w > h:
                cut = (w - h) * 100000 // (2 * w)
                srcrect = f'l="{cut}" r="{cut}"'
            else:
                srcrect = None
            if srcrect:
                deck._patch_pic_srcrect(deck._next_slide_num - 1, srcrect)


def main():
    deck = Deck(TEMPLATE)

    # ---- Титул + содержание -------------------------------------------
    add_title_slide(
        deck,
        title_text="Back to Offline: как избавиться от интернет-зависимости",
        name="Илья Черкасов",
        position="мобильный разработчик в Финтехе",
        subtitle="Offline-режим, отказоустойчивость и безопасность данных в iOS",
        photo_path="/Users/ilia-ch/Downloads/photo_2026-07-07 17.13.48.jpeg",
    )

    deck.add_agenda([
        "Введение и проблема",
        "Кэширование и инвалидация",
        "Offline-first",
        "Безопасность и хранение",
        "Итоги",
    ])

    # ==== Блок 0 · Введение и проблема ==================================
    deck.add_section_divider("Введение и проблема", 1)

    deck.add_content("О себе и том, что у меня болит", [
        "Не люблю стоять в очереди",
        "Не люблю грузить билеты на концерты несколько раз",
        "Болит, когда не продают прохладительные напитки",
        "Болит, когда надо оплачивать через QR в подвале",
    ])

    # commit 1 · LIVE DEMO — только функционал приложения (спец: слайд 5)
    deck.add_cards_slide(
        "Стартовая точка разработки",
        cards=[
            {"title": "Лента", "lines": ["посты и картинки"]},
            {"title": "Билет с QR", "lines": ["посадочный / пропускной сценарий"]},
            {"title": "Баланс", "lines": ["финансовое состояние пользователя"]},
        ],
        columns=3,
        subheading="commit 1 · LIVE DEMO",
        callout="Коммит 1: online-only, пока сеть есть — всё выглядит нормально",
        notes=(
            "Демонстрирую функционал: лента, билет с QR, баланс. Затем выключаем "
            "сеть и видим один из трёх вариантов: белый экран, бесконечный спиннер "
            "или «Нет соединения, попробуйте позже» — хотя данные уже могли лежать на телефоне."
        ),
    )

    # Новый слайд 6 · Откуда данные демо-приложения
    deck.add_table(
        "Откуда данные демо-приложения",
        ["Область", "Источник", "Что важно для лекции"],
        [
            ["Лента / профиль", "JSONPlaceholder",
             "fake REST API, GET-ответы с Cache-Control и ETag; баланс и билет — один эндпоинт GET /users/1"],
            ["Картинки", "Lorem Picsum",
             "стабильный seed по id поста, 302-редирект на CDN"],
            ["Билет / баланс / QR", "клиентская сборка из профиля",
             "JSONPlaceholder не отдаёт кошельковые данные; payload в Ticket.qrPayload, QR рисуется на экране"],
        ],
        col_widths=[3, 3, 7],
        subheading="Демо специально устроено так, чтобы показать HTTP-кэш, редиректы и local-first хранение",
        notes=(
            "Настоящего «кошелькового» бэкенда нет: два публичных mock-сервиса + "
            "клиентская сборка билета/баланса/QR.\n"
            "JSONPlaceholder — GET-ответы с Cache-Control и ETag (пригодится в блоке URLCache).\n"
            "Lorem Picsum — 302 на CDN (вернёмся при кэше картинок).\n"
            "Баланс — сумма по формуле от user.id; билет — рейс/место/гейт от id; QR собирается локально."
        ),
    )

    # Слайд 7 · Сеть — ненадёжный внешний ресурс (жирный заголовок, без «а не данность»)
    deck.add_callout_grid(
        "Сеть — ненадёжный внешний ресурс",
        callout="«Попробуйте позже» = приложение перекладывает проблему на пользователя, а не offline-режим",
        items=[
            {"title": "Где ломается сеть",
             "lines": ["метро · самолёт · лифт · роуминг · стадион · плохой Wi-Fi"]},
            {"title": "Вывод",
             "lines": ["сеть отваливается постоянно", "проектируем отказ как норму, а не исключение"]},
        ],
        notes=(
            "Главный тезис всей лекции: сеть — ненадёжный внешний ресурс.\n"
            "«Попробуйте позже» — не offline-режим, а признание зависимости от внешнего ресурса.\n"
            "Если проектируем от «сеть обычно есть», получаем приложение, которое «обычно работает»."
        ),
    )

    # Слайд 8 · Роудмап — центрированные flow-карточки
    deck.add_flow_cards_slide(
        "Роудмап развития приложения",
        steps=[
            {"title": "Online-Only", "lines": ["без интернета — белый экран или ошибка"]},
            {"title": "Кэш для чтения", "lines": ["показываем уже загруженное"]},
            {"title": "Offline-First", "lines": ["локальные данные — источник правды"]},
        ],
        orientation="horizontal",
        caption="Отказоустойчивость — это ступени: насколько приложение переживает пропадание сети",
        notes=(
            "Online-Only — без интернета белый экран или ошибка.\n"
            "Кэш для чтения — показываем уже загруженное, но не полагаемся как на данные пользователя.\n"
            "Offline-First — локальные данные = источник правды, сеть только синхронизирует."
        ),
    )

    # ==== Блок 1 · Кэширование и инвалидация ============================
    deck.add_section_divider("Кэширование и инвалидация", 2)

    deck.add_cards_slide(
        "URLCache",
        cards=[
            {"title": "Прослойка",
             "lines": ["между кодом и сетью", "система сама решает: сеть или сохранённый ответ"]},
            {"title": "Два уровня",
             "lines": ["Memory — RAM, пока запущено приложение",
                       "Disk — переживает перезапуск, Library/Caches (ОС вправе вычистить)"]},
            {"title": "Кто управляет",
             "lines": ["не клиент, а сервер — через HTTP-заголовки"]},
        ],
        columns=3,
        subheading="commit 2",
        callout="Кэшем управляет сервер через HTTP-заголовки; старые записи вытесняются автоматически",
        notes=(
            "URLCache — прослойка между кодом и сетью, прозрачно для session.data(for:).\n"
            "Memory живёт пока запущено приложение; Disk лежит в Library/Caches — запомните папку.\n"
            "Главное: кэшем управляет сервер через HTTP-заголовки."
        ),
    )

    deck.add_code("URLCache — подключение", [
        'let cache = URLCache(',
        '    memoryCapacity: 16 * 1024 * 1024,   // RAM: живёт пока запущено приложение',
        '    diskCapacity: 128 * 1024 * 1024,    // диск: Library/Caches',
        '    diskPath: "api-cache"',
        ')',
        '',
        'let config = URLSessionConfiguration.default',
        'config.urlCache = cache',
        'config.requestCachePolicy = .useProtocolCachePolicy',
    ])

    deck.add_table(
        "Свежесть и валидация кэша",
        TABLE_SRC_7[0], TABLE_SRC_7[1:],
        notes=(
            "1. «Ответ ещё свежий?» — да → из кэша мгновенно: ноль трафика, минимум задержки\n"
            "2. «Несвежий (stale) — можно дёшево перепроверить?» — да → условный запрос: «не менялось» или новая версия\n"
            "Условные заголовки (If-None-Match и др.) URLSession подставляет сам — вручную писать не нужно"
        ),
    )

    deck.add_decision_tree_slide(
        "Дерево решений URLCache",
        rows=[
            {"question": "Есть ответ в кэше?",
             "leaves": [("нет", "Идём в сеть",
                         ["ответ сохраняем, если заголовки разрешают"])],
             "down_label": "да"},
            {"question": "Ответ ещё свежий (max-age не истёк)?",
             "leaves": [("да", "Отдаём из кэша",
                         ["в сеть не ходим — ноль трафика"])],
             "down_label": "нет"},
            {"question": "Есть ETag / Last-Modified?",
             "leaves": [("нет", "Полный запрос в сеть",
                         ["как будто кэша и не было"])],
             "down_label": "да"},
            {"question": "Сервер ответил 304 Not Modified?",
             "leaves": [
                 ("да", "Тело берём из кэша", ["скачали только заголовки"]),
                 ("нет", "200 — новая версия", ["обновляем тело в кэше"]),
             ]},
        ],
        subheading="Это стандарт HTTP (RFC 9110/9111), а не фишка URLSession — так же работают браузер, curl и OkHttp",
        notes=(
            "Пример: GET /posts → max-age=43200 + ETag. Через 5 минут — из кэша; "
            "через 13 часов — If-None-Match → 304 → тело из кэша.\n"
            "Нет сети + stale = ошибка URLSession (перепроверить не у кого) — нужен ручной offline fallback."
        ),
    )

    deck.add_table(
        "RequestCachePolicy — 4 политики",
        TABLE_SRC_9[0], TABLE_SRC_9[1:],
    )

    deck.add_code(
        "Офлайн-фолбэк поверх URLCache",
        [
            'do {',
            '    let (data, response) = try await session.data(for: request)  // сеть + автокэш',
            '    return Fetched(value: try decode(data), dataSource: .network)',
            '} catch {',
            '    // офлайн: достаём последний ответ, даже если по HTTP он протух',
            '    if let cached = cache.cachedResponse(for: request),',
            '       let value = try? decode(cached.data) as T {',
            '        return Fetched(value: value, dataSource: .offlineCache)',
            '    }',
            '    throw APIError.transport(error)',
            '}',
        ],
        bullets=[
            "Online: обычный запрос через session — dataSource = .network",
            "Ошибка сети: достаём cachedResponse — dataSource = .offlineCache",
            "«Данные от вчера» лучше белого экрана; источник данных показываем в UI через dataSource",
        ],
    )

    deck.add_cards_slide(
        "А что с картинками?",
        cards=[
            {"title": "Их много и они тяжёлые",
             "lines": ["аватары, обложки", "QR/штрихкоды билетов"]},
            {"title": "Должны работать offline",
             "lines": ["показываться мгновенно и без сети"]},
            {"title": "NSCache для RAM",
             "lines": ["автоочистка под давлением памяти", "не Dictionary — руками не чистим"]},
        ],
        columns=3,
        callout="NSCache — не Dictionary: ОС сама выкинет картинки, если приложению не хватает RAM",
        notes=(
            "Картинок много и они тяжёлые; аватары, обложки, QR/штрихкоды должны показываться "
            "мгновенно и офлайн.\nБазовый инструмент для памяти — NSCache, чистится под давлением памяти."
        ),
    )

    deck.add_table(
        "Подводный камень с редиректами",
        ["Шаг", "URL", "Что происходит"],
        [
            ["1. Запрос приложения", "picsum seed URL", "приложение знает только исходный адрес"],
            ["2. Ответ сервиса", "302 Found", "сервис переносит на CDN"],
            ["3. Финальный ответ", "fastly CDN URL", "JPEG сохраняется под финальным адресом"],
            ["4. Повторный offline-поиск", "picsum seed URL", "промах: ключ другой → cache miss"],
        ],
        col_widths=[4, 4, 6],
        subheading="Код редиректа не видит: URLSession сама уходит на CDN, но URLCache сохраняет ответ под финальным URL — а ищем мы по исходному → промах",
        notes=(
            "Многие CDN (и picsum.photos) отдают картинку через 302 на финальный URL.\n"
            "URLCache сохраняет под финальным URL, а ищем по исходному → cache miss.\n"
            "Аналогия: заказали на «склад A», курьер перенёс на «склад B» — приходите на A: «у нас нет»."
        ),
    )

    deck.add_cards_slide(
        "Решение — файловый кэш картинок",
        cards=[
            {"title": "L1 · NSCache", "lines": ["RAM", "авто-эвикция под память"]},
            {"title": "L2 · Диск", "lines": ["файловый кэш в Library/Caches"]},
            {"title": "L3 · Сеть", "lines": ["если промах в L1 и L2", "кладём в оба уровня"]},
            {"title": "Ключ файла", "lines": ["SHA256(исходного URL)", "ищем по адресу, который знает приложение, — редирект больше не ломает поиск"]},
        ],
        columns=2,
        callout="clearCache() чистит RAM и Library/Caches разом — понадобится при логауте",
        notes=(
            "Для картинок отключаем URLCache и делаем свой файловый кэш: ключ = SHA256(исходный URL).\n"
            "Индексируем по адресу, который видит приложение, а не по тому, куда увёл редирект.\n"
            "Три уровня: NSCache (RAM) → диск → сеть."
        ),
    )

    deck.add_code("ImageLoader — три уровня кэша", [
        'final class ImageLoader {',
        '    private let memory = NSCache<NSURL, UIImage>()   // L1: RAM, авто-эвикция',
        '    let diskCacheURL: URL                            // L2: Library/Caches',
        '',
        '    func image(for url: URL) async throws -> UIImage {',
        '        if let hit = memory.object(forKey: url as NSURL) { return hit }   // L1',
        '        if let image = loadFromDisk(for: url) {                           // L2',
        '            memory.setObject(image, forKey: url as NSURL); return image',
        '        }',
        '        let (data, _) = try await session.data(from: url)                 // L3',
        '        let image = UIImage(data: data)!',
        '        saveToDisk(data, for: url)   // ключ файла = SHA256(исходного URL)',
        '        memory.setObject(image, forKey: url as NSURL)',
        '        return image',
        '    }',
        '}',
    ])

    deck.add_cards_slide(
        "CacheManager: три механизма инвалидации",
        cards=[
            {"title": "TTL",
             "lines": ["срок жизни записи задаёт приложение",
                       "своя проверка актуальности поверх HTTP (в URLCache срок диктует сервер)"]},
            {"title": "Версия схемы",
             "lines": ["константа cacheSchemaVersion",
                       "сменили формат модели → старый кэш сброшен на старте"]},
            {"title": "Очистка по событию",
             "lines": ["логаут / смена пользователя"]},
        ],
        columns=3,
        subheading="commit 3 · как не показать протухшее и не допустить утечки чужих данных",
        callout="cache-then-network: кэш мгновенно, свежее — фоном; честно сообщаем актуальность данных",
        notes=(
            "CacheManager — единая точка управления жизненным циклом кэша.\n"
            "TTL — второй, наш уровень контроля актуальности поверх HTTP.\n"
            "Версия схемы — одна строчка против класса багов после обновления из App Store.\n"
            "cache-then-network по духу — stale-while-revalidate."
        ),
    )

    deck.add_event_action_table(
        "Очистка при логауте",
        rows=[
            ["login A", "лента/картинки A кэшируются", "—"],
            ["logout A", "чужие данные могут остаться", "clearAll() чистит все слои"],
            ["login B", "B не должен видеть данные A", "стартует с чистого кэша"],
        ],
        left_title="Событие", right_title="Риск", third_title="Что чистим",
        subheading="Единая точка очистки: один clearAll() — HTTP-ответы, TTL-метаданные, картинки RAM+диск",
        notes=(
            "clearAll(): urlCache.removeAllCachedResponses(); UserDefaults (TTL); "
            "ImageLoader.shared.clearCache().\n"
            "SessionStore.logout() дёргает единую точку — чужие данные не утекут.\n"
            "Корнер-кейс: A залогинился, лента закэшировалась, A вышел, зашёл B — видит данные A. "
            "Семейный телефон, рабочий планшет, демо-устройство находят в проде постоянно."
        ),
    )

    deck.add_table(
        "Итог блока 1",
        TABLE_SRC_15[0], TABLE_SRC_15[1:],
        subheading="Кэш без стратегии инвалидации — это не оптимизация, а отложенный баг или утечка",
        notes=(
            "Убираем любой механизм из трёх — получим баги\n"
            "У некоторых данных свой срок годности, не совпадающий со сроком жизни кэша — платёжный токен, билет, баланс"
        ),
    )

    # ==== Блок 2 · Offline-first ========================================
    deck.add_section_divider("Offline-first", 3)

    deck.add_table(
        "Кэш vs источник правды",
        TABLE_SRC_16[0], TABLE_SRC_16[1:],
        subheading="commit 4",
        notes=(
            "Переворачиваем парадигму: локальное хранилище — источник правды, сеть лишь синхронизирует его\n"
            "Для билета фолбэк-кэш недопустим: ОС вычистит Caches под нехватку места — пассажир останется без QR на стойке"
        ),
    )

    deck.add_table(
        "Папки песочницы",
        TABLE_SRC_17[0], TABLE_SRC_17[1:],
    )

    deck.add_code(
        "LocalStore: Codable + JSON-файл",
        [
            'final class LocalStore {   // Codable + файлы в Application Support',
            '    func save<T: Encodable>(_ value: T, forKey key: String) {',
            '        guard let data = try? JSONEncoder().encode(value) else { return }',
            '        try? data.write(to: fileURL(key), options: .atomic)',
            '    }',
            '',
            '    func load<T: Decodable>(forKey key: String) -> T? {',
            '        guard let data = try? Data(contentsOf: fileURL(key)) else { return nil }',
            '        return try? JSONDecoder().decode(T.self, from: data)',
            '    }',
            '}',
        ],
        bullets=[
            "Правило: можно перекачать из сети → Caches; нельзя потерять → Application Support / Documents",
            "Один билет → простой generic-стор: Codable + JSON-файл; много данных → SQLite / Core Data / SwiftData",
        ],
    )

    deck.add_flow_cards_slide(
        "Local-first поток билета",
        steps=[
            {"title": "loadLocal", "lines": ["билет с диска — мгновенно, в авиарежиме"]},
            {"title": "Показать билет", "lines": ["QR сразу на экране"]},
            {"title": "Обновить из сети", "lines": ["фоном, не блокируя UI"]},
            {"title": "Обновить LocalStore", "lines": ["источник правды остаётся свежим"]},
            {"title": "Честный статус", "lines": ["актуально / обновляем / офлайн"]},
        ],
        orientation="horizontal",
        caption="Экран ошибки — только при первом запуске без локальной копии; иначе билет показывается всегда",
        notes=(
            "loadLocal — билет с диска практически мгновенно, работает в авиарежиме.\n"
            "Обновление из сети — метод refreshFromNetwork: фоном тихо обновляем "
            "источник правды, экран не блокируем.\n"
            "Честный статус синхронизации (актуально / обновляем / офлайн) соблюдает "
            "честность из блока 1."
        ),
    )

    deck.add_code("TicketRepository", [
        'final class TicketRepository {',
        '    // мгновенно с диска — работает в авиарежиме',
        '    func loadLocal() -> Ticket? { store.load(forKey: ticketKey) }',
        '',
        '    // в фоне обновляем ИСТОЧНИК ПРАВДЫ, не блокируя UI',
        '    func refreshFromNetwork() async throws -> Ticket {',
        '        let result: Fetched<RemoteUser> = try await client.get(.user(id: 1))',
        '        let ticket = Ticket(user: result.value)',
        '        store.save(ticket, forKey: ticketKey)',
        '        return ticket',
        '    }',
        '',
        '    // при логауте персональные данные не остаются на устройстве',
        '    func clearLocal() { store.remove(forKey: ticketKey) }',
        '}',
    ])

    deck.add_callout_grid(
        "QR строится из локального payload",
        callout="QR рисуется из локально сохранённого payload, а не из живого ответа сервера",
        items=[
            {"title": "Работает полностью offline",
             "lines": ["посадку можно пройти без сети"]},
            {"title": "Сеть — только для свежести",
             "lines": ["держит локальную копию актуальной"]},
            {"title": "Почему не URLCache",
             "lines": ["раньше билет жил в памяти ViewModel и «случайно» брался из URLCache — а его ОС может вычистить в любой момент"]},
        ],
        notes=(
            "QR-код строится из локально сохранённого payload, а не из живого ответа сервера.\n"
            "Посадку можно пройти полностью офлайн; сеть нужна лишь чтобы держать копию свежей.\n"
            "На кэш полагаться нельзя — это кэш, его вычистят."
        ),
    )

    deck.add_compare_cards(
        "Итог: кэш vs источник правды",
        columns=[
            {"title": "Кэш",
             "lines": ["отвечает: что показать, если сеть упала",
                       "производное — можно потерять"]},
            {"title": "Источник правды", "highlight": True,
             "lines": ["данные всегда здесь, локально; сеть — лишь механизм обновления",
                       "билет, баланс, черновики → Application Support"]},
        ],
        callout="Для билета, баланса, черновиков — только источник правды, и в Application Support, а не в Caches",
        notes=(
            "Кэш отвечает на вопрос «что показать, если сеть упала».\n"
            "Источник правды: данные всегда локально, сеть лишь обновляет."
        ),
    )

    deck.add_flow_cards_slide(
        "Outbox — идея",
        steps=[
            {"title": "Действие offline", "lines": ["лайк / отметка / форма без немедленного запроса"]},
            {"title": "Локальная очередь", "lines": ["действие пишется на диск (pending)"]},
            {"title": "Optimistic UI", "lines": ["UI реагирует сразу, не блокируется"]},
            {"title": "Воркер доставляет", "lines": ["сеть вернулась → POST → отправлено"]},
        ],
        orientation="horizontal",
        subheading="commit 5",
        caption="Проблема: в наивном приложении действие = немедленный запрос, без сети оно теряется",
        notes=(
            "Пользователь не только читает — он действует. Outbox: действие сначала в локальную "
            "очередь, UI оптимистичен, доставкой занимается фоновый воркер.\n"
            "Компоненты — на следующем слайде."
        ),
    )

    deck.add_table(
        "Компоненты outbox",
        TABLE_SRC_21[0], TABLE_SRC_21[1:],
    )

    deck.add_code(
        "Идемпотентность",
        [
            '// clientID генерируется ОДИН раз при постановке в очередь…',
            'let item = OutboxItem(clientID: UUID(), action: action, retryCount: 0)',
            '',
            '// …и не меняется между ретраями',
            'let _: PostResponse = try await api.post(',
            '    .posts, body: payload,',
            '    idempotencyKey: item.clientID.uuidString   // → заголовок Idempotency-Key',
            ')',
        ],
        bullets=[
            "Без ключа: ответ потерялся, клиент повторяет — два лайка или две оплаты",
            "С ключом: сервер видит «этот clientID уже обрабатывал» и не задваивает",
            "clientID — UUID: генерируется один раз и НЕ меняется между ретраями; летит в Idempotency-Key",
        ],
        notes=(
            "Сценарий: лайк отправлен, сервер применил, ответ потерялся по дороге — "
            "клиент думает «не дошло» и повторяет.\n"
            "В демо JSONPlaceholder ключ не дедуплицирует — реализована клиентская "
            "половина контракта; серверную обеспечивает бэкенд."
        ),
    )

    deck.add_flow_cards_slide(
        "Сценарий демо outbox",
        steps=[
            {"title": "Airplane Mode", "lines": ["тап «лайк»", "в Настройках «в очереди: 1»"]},
            {"title": "Relaunch (офлайн)", "lines": ["убить и перезапустить", "очередь на месте — с диска"]},
            {"title": "Network returns", "lines": ["NWPathMonitor ловит переход", "воркер отправляет, очередь пустеет"]},
        ],
        orientation="horizontal",
        subheading="LIVE DEMO · outbox переживает офлайн и перезапуск приложения",
        caption="Пользователь не сделал ничего особенного — всё произошло само",
        notes=(
            "1. Airplane Mode → тап «лайк» → «в очереди: 1».\n"
            "2. Убить и перезапустить (офлайн) → очередь прочитана с диска.\n"
            "3. Выключить Airplane Mode → воркер сам отправляет → очередь пустеет."
        ),
    )

    deck.add_cards_slide(
        "Дополнительные offline-кейсы",
        cards=[
            {"title": "Карты и маршруты", "lines": ["заранее скачанный регион"]},
            {"title": "Loyalty barcode", "lines": ["штрихкод карты лояльности на кассе"]},
            {"title": "Offline content", "lines": ["книги, подкасты, курсы с синхронизацией прогресса"]},
            {"title": "Черновики", "lines": ["переживают закрытие приложения"]},
        ],
        columns=2,
        callout="Везде три идеи: локальный источник правды · честная индикация актуальности · очередь на запись",
        notes=(
            "Куда ещё прикладывается offline: карты, loyalty barcode, offline content, черновики.\n"
            "Везде одни и те же три идеи."
        ),
    )

    # ==== Блок 3 · Безопасность и хранение ==============================
    deck.add_section_divider("Безопасность и хранение", 4)

    deck.add_quote(
        "Без модели угроз любые советы по безопасности — карго-культ",
        notes=(
            "«Шифруйте всё» звучит солидно, но не отвечает на вопрос «от кого».\n"
            "Нельзя «защититься вообще» — можно защититься от конкретного противника."
        ),
    )

    deck.add_cards_slide(
        "От кого защищаемся",
        cards=[
            {"title": "Вор телефона",
             "lines": ["физический доступ к устройству"]},
            {"title": "Бэкап в iCloud / iTunes",
             "lines": ["секреты могут уехать на другое устройство"]},
            {"title": "Jailbreak",
             "lines": ["ослабленная песочница"]},
            {"title": "Чужие глаза",
             "lines": ["коллега, ребёнок, камера над плечом"]},
            {"title": "Логаут",
             "lines": ["ОС защищает лишь периметр",
                       "внутри контейнера всё наше: папка, класс доступности, очистка"]},
            {"title": "Компрометация сетевого канала",
             "lines": ["перехват трафика: MITM, недоверенный Wi-Fi"]},
        ],
        columns=3,
        callout="Под каждый сценарий — свой инструмент, а не «шифруйте всё»",
        notes=(
            "Модель угроз мобильного приложения: вор телефона (физический доступ), "
            "бэкап iCloud/iTunes (секреты уезжают на другое устройство), jailbreak "
            "(ослабленная песочница), чужие глаза (коллега, ребёнок, камера над плечом), "
            "логаут, компрометация сетевого канала.\n"
            "Про логаут: песочница защищает периметр (снаружи внутрь), но всё, что "
            "происходит внутри контейнера — выбор директории, класс доступности, полнота "
            "и надёжность очистки — целиком наша зона ответственности; любая ошибка здесь "
            "бьёт напрямую по нам, подстраховки со стороны ОС уже нет.\n"
            "Под каждый сценарий — свой инструмент защиты."
        ),
    )

    deck.add_table(
        "Карта хранилищ",
        TABLE_SRC_27[0], TABLE_SRC_27[1:],
        notes=(
            "UserDefaults — открытый текст: физически это .plist в Library/Preferences\n"
            "UserDefaults видно в бэкапе, его открывает текстовый редактор. Любой токен там — секрет, отданный наружу"
        ),
    )

    deck.add_table(
        "Папки песочницы + бэкап",
        TABLE_SRC_28[0], TABLE_SRC_28[1:],
        subheading="Точечное исключение файла из бэкапа — URLResourceValues.isExcludedFromBackup (например, большой скачанный датасет)",
        notes=(
            "isExcludedFromBackup — исключить конкретный файл из бэкапа (например, большой скачанный датасет)\n"
            "Выбор папки — это и надёжность, и безопасность: билеты и черновики ≠ кэш, они должны лежать в правильном месте"
        ),
    )

    deck.add_event_action_table(
        "Keychain — зачем и как",
        rows=[
            ["Логин", "save", "сохранить access token"],
            ["Старт приложения", "read", "восстановить сессию после перезапуска"],
            ["Логаут", "delete", "удалить секрет с устройства"],
        ],
        left_title="Событие", right_title="Метод KeychainStore", third_title="Зачем",
        subheading="commit 6 · зашифрованное хранилище ОС (AES-256, Secure Enclave); только для маленьких секретов",
        notes=(
            "Первый настоящий секрет — access token после логина. По карте хранилищ место одно — Keychain: "
            "AES-256, ключи в Secure Enclave.\n"
            "API старый и сишный (SecItemAdd, SecItemCopyMatching) — обёрнут в KeychainStore: save/read/delete.\n"
            "Только для маленьких секретов — токенов и ключей, не больших объёмов данных."
        ),
    )

    deck.add_code("KeychainStore", [
        'final class KeychainStore {',
        '    func save(_ data: Data, account: String) throws {',
        '        var query: [CFString: Any] = [',
        '            kSecClass: kSecClassGenericPassword,   // класс для app-токенов',
        '            kSecAttrService: service, kSecAttrAccount: account,',
        '            kSecValueData: data,',
        '            kSecAttrAccessible: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]',
        '        let status = SecItemAdd(query as CFDictionary, nil)',
        '        guard status == errSecSuccess else {',
        '            throw KeychainError.unexpectedStatus(status)',
        '        }',
        '    }',
        '    // read uses SecItemCopyMatching; delete uses SecItemDelete',
        '}',
    ])

    deck.add_table(
        "Классы доступности",
        TABLE_SRC_30[0], TABLE_SRC_30[1:],
        subheading="Наш выбор — AfterFirstUnlockThisDeviceOnly: обе части названия выбраны осознанно",
        notes=(
            "AfterFirstUnlock — outbox-воркеру из блока 2 нужно слать запросы с токеном в фоне, без участия пользователя\n"
            "ThisDeviceOnly — в модели угроз есть «бэкап в iCloud»: компрометация бэкапа не должна означать компрометацию токена"
        ),
    )

    deck.add_table(
        "UserDefaults vs Keychain",
        TABLE_SRC_31[0], TABLE_SRC_31[1:],
        subheading="LIVE DEMO",
        notes=(
            "Кнопка пишет токен в UserDefaults → открываем Library/Preferences/<bundle>.plist — токен виден глазами. Рядом токен в Keychain — так просто не достать\n"
            "Имя пользователя намеренно в UserDefaults — это не секрет. Токен — только в Keychain\n"
            "Безопасность — не «всё шифровать», а «класть каждый тип данных в правильное место»\n"
            "Файлы шифрует Data Protection при блокировке, ключи — в Secure Enclave"
        ),
    )

    deck.add_table(
        "FaceID — гейт, а не шифрование",
        TABLE_SRC_32[0], TABLE_SRC_32[1:],
        col_widths=[8, 5, 5], compact=True,
        subheading="commit 7",
        notes=(
            "Данные билета уже на диске и зашифрованы Data Protection — FaceID их не расшифровывает\n"
            "Он решает один вопрос: показать данные пользователю или нет\n"
            "Замок на двери, не сейф. Сейф — Secure Enclave и Keychain"
        ),
    )

    deck.add_cards_slide(
        "FaceID на TicketView vs payment token",
        cards=[
            {"title": "Билет — гейт в UI (охраняет приложение)",
             "lines": ["данные уже на диске; FaceID лишь решает — показать или нет",
                       "ушли в фон → экран билета снова блокируется"]},
            {"title": "Платёжный токен — гейт в ОС (охраняет Keychain)",
             "lines": ["SecAccessControl (.biometryCurrentSet)",
                       "биометрию требует сам Keychain через Secure Enclave — "
                       "секрет физически не отдаётся без живого FaceID"]},
            {"title": "CurrentSet vs Any",
             "lines": ["biometryAny: добавили новое лицо — секрет всё ещё читается",
                       "biometryCurrentSet: биометрия сменилась — секрет недоступен"]},
        ],
        columns=3,
        subheading="Два уровня защиты: UI-гейт можно обойти багом в приложении, Keychain ACL — нельзя",
        callout="Билет охраняет код приложения, платёжный токен — сама ОС; для платёжных данных — только .biometryCurrentSet",
        notes=(
            "Ключевой контраст слайда: билет и платёжный токен защищены на разных уровнях.\n"
            "Билет: UI-гейт, приложение само вызывает FaceID и решает, показывать ли экран; "
            "реблокировка при уходе в фон — гейт, а не «разблокировал один раз навсегда».\n"
            "Платёжный токен: гейт на уровне ОС — приложение не вызывает проверку само, "
            "её запрашивает Keychain через Secure Enclave; секрет физически не отдаётся без живого FaceID. "
            "Сильнее, чем «нарисовали замок поверх экрана».\n"
            ".biometryAny: добавили новое лицо — секрет читается. .biometryCurrentSet: становится "
            "недоступен. Для платёжных данных — только CurrentSet."
        ),
    )

    deck.add_code("SecAccessControl: .biometryCurrentSet", [
        'let access = SecAccessControlCreateWithFlags(',
        '    kCFAllocatorDefault,',
        '    kSecAttrAccessibleWhenUnlockedThisDeviceOnly,',
        '    .biometryCurrentSet,        // 🔑 не .biometryAny',
        '    &error',
        ')',
        'query[kSecAttrAccessControl] = access   // секрет привязан к текущей биометрии',
        '',
        '// чтение: FaceID-промпт показывает сам Keychain через Secure Enclave',
        'query[kSecUseAuthenticationContext] = LAContext()',
        'SecItemCopyMatching(query as CFDictionary, &result)',
    ])

    deck.add_table(
        "accessToken и paymentToken",
        TABLE_SRC_34[0], TABLE_SRC_34[1:],
        col_widths=[5, 8, 7], compact=True,
        notes=(
            "Два секрета — две политики, потому что требования разные: фоновые запросы vs платёж\n"
            "logout удаляет оба — в той же единой точке очистки, что мы завели в блоке 1"
        ),
    )

    deck.add_cards_slide(
        "Не забыть про Info.plist",
        cards=[
            {"title": "Что добавить",
             "lines": ["ключ NSFaceIDUsageDescription и понятный пользователю текст"]},
            {"title": "Что будет без ключа",
             "lines": ["обращение к FaceID приводит к crash, а не к обычной ошибке"]},
            {"title": "Где проверить",
             "lines": ["Info.plist проекта", "smoke-test на устройстве с биометрией"]},
        ],
        columns=3,
        subheading="NSFaceIDUsageDescription — обязательный ключ; текст должен объяснять пользователю, зачем FaceID",
        callout="<key>NSFaceIDUsageDescription</key> · <string>Подтвердите личность, чтобы открыть билет и платёжные данные</string>",
        notes=(
            "Без ключа обращение к FaceID не «вернёт ошибку», а крашит приложение.\n"
            "Проверяйте не только наличие ключа, но и текст: пользователь должен понимать, "
            "зачем приложение просит FaceID — билет, оплата или чувствительные данные."
        ),
    )

    # ==== Блок 4 · Итоги ================================================
    deck.add_section_divider("Итоги", 5)

    deck.add_cards_slide(
        "Типичные ошибки",
        cards=[
            {"title": "✗", "lines": ["протухший кэш без индикации"]},
            {"title": "✗", "lines": ["токены в UserDefaults"]},
            {"title": "✗", "lines": ["билеты в Library/Caches"]},
            {"title": "✗", "lines": ["FaceID только в UI, без привязки к Keychain"]},
            {"title": "✗", "lines": ["не чистят всё при логауте"]},
            {"title": "✗", "lines": ["«попробуйте позже» выдаётся за offline-режим"]},
        ],
        columns=3,
        notes=(
            "Грабли: протухший кэш без индикации; токены в UserDefaults; билеты в Caches; "
            "FaceID только в UI; забывают чистить при логауте; «попробуйте позже» как офлайн."
        ),
    )

    deck.add_cards_slide(
        "Чек-лист отказоустойчивого приложения",
        cards=[
            {"title": "✓", "lines": ["локальный источник правды; сеть только синхронизирует"]},
            {"title": "✓", "lines": ["у кэша — TTL, версия схемы, очистка при логауте"]},
            {"title": "✓", "lines": ["честно показываем актуальность данных"]},
            {"title": "✓", "lines": ["запись без сети — в outbox с идемпотентностью"]},
            {"title": "✓", "lines": ["секреты — только Keychain с правильным классом"]},
            {"title": "✓", "lines": ["файлы — в правильных папках; критичное вне бэкапа"]},
            {"title": "✓", "lines": ["чувствительное — за FaceID; платёжные токены к биометрии"]},
            {"title": "✓", "lines": ["офлайн-токены оплаты — срок, лимит, подпись"]},
        ],
        columns=4,
        notes="Финальный чек-лист — можно сфотографировать. Все восемь пунктов сохранены.",
    )

    deck.add_quote(
        "Сеть ненадёжна. Данные живут локально. Пользователю всегда говорим правду о том, что он видит.",
    )

    deck.add_final([
        "Отказоустойчивость — не фича, которую прикручивают в конце, а способ мышления",
        "Постройте приложение так — и авиарежим перестанет быть проблемой",
    ])

    deck.save(OUTPUT)
    print(f"OK: {OUTPUT} — {deck._next_slide_num - 1} слайдов")


if __name__ == "__main__":
    main()
