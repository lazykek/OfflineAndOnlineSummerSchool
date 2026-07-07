#!/usr/bin/env python3
"""Одноразовый скрипт: извлекает таблицы из исходной презентации и печатает
их как Python-литералы для вставки в build_lsh_presentation.py.

ВНИМАНИЕ: список SLIDES ниже относится к СТАРОЙ presentation/Offline_iOS_Lecture.pptx,
а НЕ к LSH-колоде из build_lsh_presentation.py. После ревизии (разделение старого
слайда 5 на два и перенумерация 6→7 и далее) номера слайдов LSH-колоды сдвинулись,
но здесь их менять НЕ нужно — источник этих таблиц (Offline_iOS_Lecture.pptx) не
перенумеровывался. Если запускаете скрипт заново, сверяйтесь именно с исходником."""
import zipfile
from xml.etree import ElementTree as ET

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
SRC = "presentation/Offline_iOS_Lecture.pptx"
SLIDES = [7, 9, 15, 16, 17, 21, 27, 28, 30, 31, 32, 34]

with zipfile.ZipFile(SRC) as z:
    for n in SLIDES:
        root = ET.fromstring(z.read(f"ppt/slides/slide{n}.xml"))
        tbls = root.findall(f".//{{{A}}}tbl")
        print(f"# ---- src slide {n}: {len(tbls)} table(s) ----")
        for tbl in tbls:
            rows = []
            for tr in tbl.findall(f"{{{A}}}tr"):
                row = []
                for tc in tr.findall(f"{{{A}}}tc"):
                    texts = [t.text or "" for t in tc.iter(f"{{{A}}}t")]
                    row.append("".join(texts))
                rows.append(row)
            print(f"TABLE_SRC_{n} = [")
            for row in rows:
                print(f"    {row!r},")
            print("]")
        print()
