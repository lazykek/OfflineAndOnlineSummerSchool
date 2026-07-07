#!/usr/bin/env python3
"""Enrich [НА СЛАЙДЕ] blocks with clearer context — not spoken prose."""

from __future__ import annotations

import re
from pathlib import Path

SPEECH = Path(__file__).resolve().parents[1] / "LECTURE_SPEECH.md"

# slide title fragment → full [НА СЛАЙДЕ] body (without markers)
ENHANCEMENTS: dict[str, str] = {
    "демо — типичная ошибка": """\
- Online-only: без сети приложение не работает
- Три паттерна: белый экран · бесконечный спиннер · «Нет соединения»
- Live demo на устройстве (коммит 1)""",

    "Сеть — это ненадёжный": """\
- **Сеть — ненадёжный внешний ресурс, а не данность**
- Метро · самолёт · лифт · роуминг · стадион · плохой Wi-Fi
- «Сеть обычно есть» → «app обычно работает»""",

    "карта лекции": """\
- **Блок 1** — URLCache + инвалидация (TTL, logout, dataSource)
- **Блок 2** — offline-first: LocalStore, билет, Outbox
- **Блок 3** — Keychain, песочница, FaceID
- **Блок 4** — итоги, BLE, чек-лист""",

    "URLCache — почти бесплатный": """\
- `URLCache` — встроенный HTTP-кэш Foundation
- Подключаем в `APIClient`: `GET /posts`, `GET /users/1`
- Memory 16 MB + Disk 128 MB · код запроса не меняется""",

    "схема — твой код": """\
- Код: `session.data(for: request)` — не знает про кэш
- `URLSession` → `URLCache?` → свежий? из кэша : сеть
- Online: сеть + автосохранение · Offline: наш `cachedResponse(for:)` fallback""",

    "подключение URLCache": """\
- **Memory** — быстро, пока app запущен
- **Disk** — переживает перезапуск, `Library/Caches`
- `.useProtocolCachePolicy` — честно по HTTP-заголовкам
```swift
let cache = URLCache(
    memoryCapacity: 16 * 1024 * 1024,
    diskCapacity: 128 * 1024 * 1024,
    diskPath: "api-cache"
)
let config = URLSessionConfiguration.default
config.urlCache = cache
config.requestCachePolicy = .useProtocolCachePolicy
```""",

    "RFC 9110": """\
- `ETag`, `Cache-Control`, `304` — **протокол HTTP**, не фишка Apple
- То же в браузере, curl, OkHttp
- **RFC 9110** (Semantics) + **RFC 9111** (Caching), 2022
- Стандарт описывает обмен; как сервер считает ETag — его решение""",

    "таймлайн на нашем API": """\
- **API:** `GET /posts` · jsonplaceholder · `max-age=43200` + `ETag`
- **T0** — первый запрос → сеть → JSON + ETag в URLCache
- **T+5 мин** — fresh → кэш, 0 RTT, сеть не трогаем
- **T+13 ч** — stale → `If-None-Match` → `304` → тело из кэша
- **Offline** — stale + нет сети → `URLSession` throws → `cachedResponse(for:)` в APIClient""",

    "requestCachePolicy": """\
- `.useProtocolCachePolicy` — дефолт: по `Cache-Control` / `ETag`
- `.reloadIgnoringLocalCacheData` — всегда сеть, кэш игнор
- `.returnCacheDataElseLoad` — кэш если есть, иначе сеть
- `.returnCacheDataDontLoad` — только кэш, offline-only
- **Наш паттерн:** online → `.useProtocolCachePolicy` · offline → `cachedResponse(for:)`
```swift
} catch {
    if let cached = cache.cachedResponse(for: request),
       let value = try? decode(cached.data) as T {
        return Fetched(value: value, dataSource: .offlineCache)
    }
    throw APIError.transport(error)
}
```""",

    "Картинки — отдельная": """\
- **Почему не URLCache API:** много картинок · тяжёлые · picsum = 302-редирект
- **ImageLoader:** L1 `NSCache` (RAM) → L2 disk (`SHA256` seed-URL) → L3 сеть
- `urlCache = nil` — свой кэш с ключом по **исходному** URL поста
- **Цель:** обложки ленты мгновенно и офлайн""",

    "Подводный камень: редиректы": """\
- `picsum.photos/seed/42` → **302** → `fastly.picsum.photos/…/237.jpg`
- URLCache сохраняет ответ под **финальным** URL (B)
- App ищет по **исходному** seed-URL (A) → **промах**
- **Симптом:** online первая загрузка OK · offline / relaunch — картинки пропали""",

    "Итог блока 1 — инвалидация": """\
- Кэш без инвалидации = отложенный баг или утечка данных
- Logout A → пользователь B не видит кэш A
- **Кэш ≠ источник правды** → билет в Application Support, не Caches""",

    "Итог блока 2 — кэш vs источник": """\
- **Кэш:** «что показать, если сеть упала?»
- **Источник правды:** «данные всегда локально; сеть = синхронизация»
- Билет · баланс · черновики → `Application Support`, не `Caches`""",

    "🔑 «Очистка при логауте": """\
- **Сценарий утечки:** A залогинился → кэш · A logout → B видит данные A
- `clearAll()` — единая точка: URLCache + TTL + ImageLoader
- `logout()` позже добавит Keychain + LocalStore + Outbox
```swift
func clearAll() {
    urlCache.removeAllCachedResponses()
    UserDefaults.standard.removeObject(forKey: timestampKey)
    ImageLoader.shared.clearCache()
}
```""",

    "гейт на TicketView": """\
- FaceID — **гейт доступа**, не шифрование (данные уже на диске)
- `.background` → `isUnlocked = false` — реблокировка, не «один раз навсегда»
- Payment token: `SecAccessControl(.biometryCurrentSet)` — чтение только через FaceID
```swift
.onChange(of: scenePhase) { _, newPhase in
    if newPhase == .background { isUnlocked = false }
}
```""",

    "антипример вживую": """\
- **UserDefaults** = plain `.plist` — токен виден без защиты
- **Keychain** = AES-256 + Secure Enclave
- Имя пользователя → UserDefaults OK · access token → только Keychain
```swift
// Гейт билета — только биометрия, без фолбэка на пароль
func authenticate(reason: String) async -> Result<Void, BiometricError> {
    ctx.localizedFallbackTitle = ""
    // evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, …)
}
```""",

    "мостик к блоку 2": """\
- TTL / schemaVersion / logout — управляют **кэшем** (можно потерять)
- Билет · баланс · payment token — **нельзя** «случайно потерять»
- Нужен LocalStore: диск = главное, сеть = синхронизация""",

    "Кэsh vs источник правды": "",  # typo guard
    "Кэш vs источник правды": """\
- **Блок 1:** сеть главная, кэш — фолбэк при ошибке
- **Блок 2:** диск главный, сеть обновляет в фоне
| | Кэш (коммиты 2–3) | LocalStore (коммит 4) |
|---|---|---|
| **Роль** | фолбэк «если сеть упала» | первоисточник, читается всегда |
| **Природа** | производные, можно потерять | данные пользователя |
| **Папка** | `Library/Caches` (ОС может удалить) | `Application Support` (не трогают) |
| **Поток** | сеть → показать, кэш при ошибке | диск → сразу, сеть в фоне |""",

    "CacheManager — единая точка": """\
- **Три механизма:** URLCache + TTL в UserDefaults + ImageLoader
- `dataSource`: `.network` · `.staleCache(age:)` · `.offlineCache` — честный UI
- `saveTimestamp` после сетевого ответа · `isStale` по TTL · `clearAll()` — один вызов
```swift
enum DataSource: Equatable {
    case network
    case staleCache(age: TimeInterval)
    case offlineCache
}
func clearAll() {
    urlCache.removeAllCachedResponses()
    UserDefaults.standard.removeObject(forKey: timestampKey)
    ImageLoader.shared.clearCache()
}
```""",

    "QR строится из локального": """\
- `Ticket.qrPayload` — JSON на клиенте, сохраняется в LocalStore
- QRView рисует из **локального** payload, не из live API
- Посадка полностью офлайн · сеть только обновляет копию""",

    "компоненты outbox": """\
- **NetworkMonitor** — `NWPathMonitor`, знаем о сети до HTTP-запроса
- **OutboxStore** — персистентная очередь на LocalStore
- **OutboxProcessor** — enqueue → optimistic UI → retry + backoff → markSent
```swift
func enqueue(_ action: OutboxAction) {
    outbox.enqueue(action)
    if monitor.isOnline { Task { await processQueue() } }
}
// Idempotency-Key: item.clientID.uuidString
```""",

    "идемпотентность": """\
- `clientID` (UUID) — один на действие, **не меняется** при retry
- `Idempotency-Key` в POST → сервер дедуплицирует
- At-least-once доставка: потерянный ответ ≠ повторная операция
- Без ключа: двойной лайк · двойная оплата""",

    "сценарий демо outbox": """\
- Airplane Mode ON → лайк → UI optimistic · «в очереди: 1»
- Kill app → relaunch offline → очередь на диске
- Airplane Mode OFF → `NWPathMonitor` → auto sync → очередь пуста""",

    "доп. offline-кейсы": """\
- Карты: регион скачан заранее · штрихкод на кассе
- «Download for offline» + sync прогресса
- Silent push / BGAppRefresh — подтянуть свежие данные
- Везде: local truth + honest UI + write queue""",

    "Без модели угроз": """\
- **Без модели угроз советы = карго-культ**
- Нельзя «защититься вообще» — только от конкретного противника
- Дальше: карта хранилищ под каждую угрозу""",

    "не забыть Info.plist": """\
- `NSFaceIDUsageDescription` — **без него FaceID = crash**
- `UIBackgroundModes: remote-notification` — опционально, silent push""",

    "Оффлайн-оплата по BLE": """\
- Пользователь **без сети** · терминал офлайн · оплата BLE/NFC
- Online: сервер → подписанные payment tokens → Keychain (FaceID)
- Offline: терминал проверяет подпись · лимиты срока/суммы
- Транзакции → Outbox → sync при появлении сети""",

    "финальная мысль": """\
- Отказоустойчивость — **способ мышления**, не фича «в конце»
- Сеть ненадёжна · данные локально · UI говорит правду
- Постройте так — и авиарежим перестанет быть проблемой""",

    "Как ломается кэш при 302": """\
- **Запрос:** `GET picsum.photos/seed/42/200/120`
- **Ответ:** `302 Found` → `Location: fastly.picsum.photos/…/237.jpg`
- URLSession следует редиректу → `200` + JPEG (2 HTTP-запроса)
- URLCache запоминает ключ **финального** URL, не seed""",

    "склад A / склад B": """\
- Заказали на «склад A», доставили на «склад B» — ищем на A → «нет»
- **Решение:** disk cache, ключ = SHA256(**исходного** seed-URL)
- L1 NSCache → L2 disk → L3 сеть · `urlCache = nil` в ImageLoader""",
}


def replace_na_block(text: str, title_fragment: str, new_body: str) -> str:
    if not new_body.strip():
        return text
    pattern = (
        rf"(`\[СЛАЙД:[^\]]*{re.escape(title_fragment)}[^\]]*\]`\s*\n\n)"
        rf"\[НА СЛАЙДЕ\]\s*\n.*?"
        rf"(?=\n\[РЕЧЬ\])"
    )
    repl = rf"\1[НА СЛАЙДЕ]\n{new_body.strip()}\n"
    new, n = re.subn(pattern, repl, text, count=1, flags=re.DOTALL)
    if n:
        return new
    # slide without [НА СЛАЙДЕ] yet — insert after marker
    pattern2 = (
        rf"(`\[СЛАЙД:[^\]]*{re.escape(title_fragment)}[^\]]*\]`\s*\n\n)"
        rf"(?=\[РЕЧЬ\]|[^\[]|\|)"
    )
    return re.sub(pattern2, rf"\1[НА СЛАЙДЕ]\n{new_body.strip()}\n\n", text, count=1, flags=re.DOTALL)


def structural_fixes(text: str) -> str:
    # карта лекции — wrong bullets from bad auto-inject
    text = replace_na_block(text, "карта лекции", ENHANCEMENTS["карта лекции"])

    # Add structure app slide if missing
    if "структура приложения" not in text:
        insert = """
`[КОММИТ 1]` `[СЛАЙД: структура приложения — лента, билет, баланс]`

[НА СЛАЙДЕ]
- **Лента** · **Билет + QR** · **Баланс** — три экрана кошелька
- Коммит 1 · всё грузится из сети · online-only

[РЕЧЬ]
Вот наша отправная точка. Это кошелёк: онлайн-лента, билет с QR-кодом, баланс. Всё грузится напрямую из сети. Красиво работает — пока есть интернет.
"""
        text = text.replace(
            "Вот наша отправная точка.\n`[СЛАЙД: «Откуда данные",
            insert.strip() + "\n`[СЛАЙД: «Откуда данные",
        )

    # URLCache intro — wrap orphan bullets
    text = re.sub(
        r"(`\[КОММИТ 2\]` `\[СЛАЙД: «URLCache — почти бесплатный HTTP-кэш»]`\s*\n\n)"
        r"- URLCache — встроенный.*?\n- Прослойка.*?\n\n"
        r"Первый и самый",
        r"\1[НА СЛАЙДЕ]\n"
        + ENHANCEMENTS["URLCache — почти бесплатный"].strip()
        + "\n\n[РЕЧЬ]\nПервый и самый",
        text,
        count=1,
        flags=re.DOTALL,
    )

    # Split merged URLSession / подключение slides
    old = """`[СЛАЙД: схема — твой код → URLSession → [URLCache?] → сеть]`

[НА СЛАЙДЕ]
`[КОД]` `[СЛАЙД: подключение URLCache]`

[РЕЧЬ]
Идея простая."""
    new = """`[СЛАЙД: схема — твой код → URLSession → [URLCache?] → сеть]`

[НА СЛАЙДЕ]
""" + ENHANCEMENTS["схема — твой код"].strip() + """

[РЕЧЬ]
Идея простая."""
    if old in text:
        text = text.replace(old, new)

    # Move URLCache code block to подключение slide
    code_block = """```swift
let cache = URLCache(
    memoryCapacity: 16 * 1024 * 1024,   // 16 MB RAM
    diskCapacity: 128 * 1024 * 1024,    // 128 MB disk
    diskPath: "api-cache"
)
let config = URLSessionConfiguration.default
config.urlCache = cache
config.requestCachePolicy = .useProtocolCachePolicy
```"""
    if "`[СЛАЙД: подключение URLCache]`" not in text:
        text = text.replace(
            "Идея простая. `URLCache` — это прослойка",
            "`[КОД]` `[СЛАЙД: подключение URLCache]`\n\n[НА СЛАЙДЕ]\n"
            + ENHANCEMENTS["подключение URLCache"].strip()
            + "\n\n[РЕЧЬ]\nИдея простая. `URLCache` — это прослойка",
            1,
        )
        text = text.replace(code_block + "\n", "", 1)

    # Кэш vs — wrap table in [НА СЛАЙДЕ]
    old_cache = """`[КОММИТ 4]` `[СЛАЙД: «Кэш vs источник правды»]`

| | Кэш (коммиты 2–3) | LocalStore (коммит 4) |
|---|---|---|
| Роль | фолбэк «если сеть упала» | первоисточник, читается всегда |
| Природа данных | производные, можно потерять | данные пользователя |
| Папка | `Library/Caches` (ОС может удалить) | `Library/Application Support` (ОС не трогает, бэкапится) |
| Поток | сеть → показать, кэш при ошибке | диск → показать сразу, сеть обновляет в фоне |

В первом блоке"""
    new_cache = """`[КОММИТ 4]` `[СЛАЙД: «Кэш vs источник правды»]`

[НА СЛАЙДЕ]
""" + ENHANCEMENTS["Кэш vs источник правды"].strip() + """

[РЕЧЬ]
В первом блоке"""
    if old_cache in text:
        text = text.replace(old_cache, new_cache, 1)

    # Legacy: rename second summary slide if old marker remains
    marker = "`[СЛАЙД: фраза-вывод]`"
    if marker in text:
        first = text.find(marker)
        second = text.find(marker, first + len(marker))
        if second != -1:
            text = (
                text[:second]
                + "`[СЛАЙД: Итог блока 2 — кэш vs источник правды]`"
                + text[second + len(marker) :]
            )
        text = text.replace(marker, "`[СЛАЙД: Итог блока 1 — инвалидация кэша]`", 1)

    return text


def main() -> None:
    text = SPEECH.read_text(encoding="utf-8")
    text = structural_fixes(text)
    for fragment, body in ENHANCEMENTS.items():
        if body.strip():
            text = replace_na_block(text, fragment, body)
    SPEECH.write_text(text, encoding="utf-8")
    print(f"✓ Enhanced slide context in {SPEECH}")


if __name__ == "__main__":
    main()
