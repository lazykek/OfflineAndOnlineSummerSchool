# Лекция: «Превращаем онлайн-приложение в отказоустойчивое: offline-режим и безопасность данных в iOS»

> **Формат:** 90 минут, слайды + заранее заготовленные коммиты в репозитории.
> На презентации показываются важные куски кода и архитектурные подробности; живого кодинга нет.
> **Демо-приложение:** кошелёк с билетами и оплатой (аналог Wallet / транспортной карты) — онлайн-лента, билеты с QR, баланс, оплата по BLE, чувствительные данные.
> **Сквозная цель:** к концу лекции приложение работает в авиарежиме — показывает билеты, баланс, ленту и пускает по FaceID.

---

## Содержание

- [Структура коммитов](#структура-коммитов)
- [Блок 0. Введение и проблема (8 мин)](#блок-0-введение-и-проблема-8-мин)
- [Блок 1. Кэширование и инвалидация (22 мин)](#блок-1-кэширование-и-инвалидация-22-мин)
- [Блок 2. Offline-first (22 мин)](#блок-2-offline-first-22-мин)
- [Блок 3. Безопасность и хранение (28 мин)](#блок-3-безопасность-и-хранение-28-мин)
- [Блок 4. Итоги (10 мин)](#блок-4-итоги-10-мин)
- [Тайминг-сводка](#тайминг-сводка)
- [План Б при перерасходе времени](#план-б-при-перерасходе-времени)
- [Чек-лист отказоустойчивого приложения](#чек-лист-отказоустойчивого-приложения)

---

## Структура коммитов

7 атомарных коммитов, каждый — отдельная идея и отдельный слайд кода. На слайде показываются 1–2 ключевых файла, а не весь diff.

| № | Сообщение коммита | Блок | Что демонстрирует |
|---|---|---|---|
| 1 | `chore: online-only baseline` | 0 | Стартовая точка: всё падает без сети |
| 2 | `feat: cache feed and images` | 1 | `URLCache` + кэш картинок |
| 3 | `feat: cache invalidation with TTL and logout reset` | 1 | Инвалидация и очистка при логауте |
| 4 | `feat: local store and offline ticket` | 2 | Источник правды локально + offline-билет |
| 5 | `feat: outbox queue with idempotency` | 2 | Отложенные действия + `NWPathMonitor` |
| 6 | `feat: store token in Keychain` | 3 | Секреты в Keychain |
| 7 | `feat: FaceID gate for ticket and payment` | 3 | Биометрия + `SecAccessControl` |

---

## Блок 0. Введение и проблема (8 мин)

**Цель:** показать боль и задать модель мышления.

### Тезисы
- Антипример: выключаем интернет → белый экран / бесконечный спиннер / «Нет соединения».
- Главный тезис: **сеть — это ненадёжный внешний ресурс, а не данность.** Метро, самолёт, лифт, роуминг, плохой Wi-Fi.
- Спектр отказоустойчивости: `онлайн-only` → `кэш для чтения` → `offline-first`.
- Карта лекции и демо-цель: «к концу приложение работает в авиарежиме».

### Что показать
- 🎬 **Коммит 1** — стартовая точка: онлайн-only приложение (лента + билет + баланс), падает без сети.
- 🎥 Live demo: переключение в авиарежим на устройстве (коммит 1).

---

## Блок 1. Кэширование и инвалидация (22 мин)

**Цель:** научить показывать данные без сети и не показывать протухшее.

### 1.1. Кэш сетевых ответов (6 мин)
- `URLCache` и «честное» HTTP-кэширование почти бесплатно.
- Заголовки: `Cache-Control`, `ETag` / `If-None-Match`, `Last-Modified` / `If-Modified-Since`.
- Memory vs disk-кэш, `URLSessionConfiguration.requestCachePolicy`.

### 1.2. Кэш изображений (4 мин)
- `NSCache` (in-memory, авто-очистка под давлением памяти) vs дисковый кэш.
- Кейс: аватары, обложки, **QR/штрихкоды билетов**.
- Почему нельзя складывать картинки в `UserDefaults` без меры.

### 1.3. ⚠️ Инвалидация — ядро блока (12 мин)
- **TTL** — срок жизни записи.
- **Версионирование** — `version` / `updatedAt`, при несовпадении перезагрузка.
- **Cache-then-network** — мгновенно показать кэш, параллельно обновить.
- **Stale-while-revalidate** — показать старое + честная плашка «обновляем / данные от 14:30».
- **Инвалидация по событию** — полная очистка при логауте / смене пользователя.
- 🔑 **Акцент:** типичная утечка — вышел один юзер, зашёл другой, увидел чужие данные. **Чистим кэш при логауте.**

### Что показать
- 🎬 **Коммит 2** — кэш ленты + картинок.
- 🎬 **Коммит 3** — инвалидация (TTL + очистка при логауте).

---

## Блок 2. Offline-first (22 мин)

**Цель:** перейти от «кэш для чтения» к полноценной работе офлайн.

### 2.1. Локальное хранилище как источник правды (6 мин)
- Обзор: `Codable` + файлы, SQLite, Core Data, SwiftData — когда что выбирать.
- Источник правды = локальная база; сеть лишь синхронизирует.
- Что хранить: билеты, баланс (read-only снапшот), расписание, профиль.

### 2.2. Кейс «билет / посадочный талон офлайн» (6 мин)
- QR/штрихкод генерируется и хранится локально, валиден по времени.
- Где хранить (не в `Caches`!) и как защитить (см. блок 3).

### 2.3. Очередь отложенных действий — Outbox (10 мин)
- Действия (оплата отметки, лайк, отправка формы) пишутся локально и синхронизируются при появлении сети.
- **Идемпотентность:** client-side ID, чтобы не задвоить операцию при ретрае.
- Отслеживание сети: `NWPathMonitor` (Network framework).
- Конфликты, порядок применения, ретраи с backoff.

### Доп. offline-кейсы — упомянуть одним слайдом
- Карты/маршруты офлайн (заранее скачанный регион).
- Штрихкод карты лояльности на кассе.
- Контент «скачать для офлайна» (книги, подкасты, курсы) + синхронизация прогресса.
- Черновики, переживающие закрытие приложения.

### Что показать
- 🎬 **Коммит 4** — локальное хранилище + offline-билет.
- 🎬 **Коммит 5** — outbox-очередь.

---

## Блок 3. Безопасность и хранение (28 мин)

**Цель:** объяснить, ГДЕ и КАК хранить, исходя из модели угроз.

### 3.1. Модель угроз (4 мин)
- От кого защищаемся: другое приложение, вор телефона, бэкап в iCloud/iTunes, jailbreak, чужие глаза.
- Без модели угроз советы по безопасности = карго-культ.

### 3.2. Карта хранилищ и папки песочницы (10 мин)

| Хранилище | Для чего | Чего нельзя |
|---|---|---|
| **Keychain** | токены, пароли, ключи шифрования | большие объёмы данных |
| **UserDefaults** | настройки, флаги | секреты/токены (это plain в plist!) |
| **Files — Documents** | пользовательские данные для бэкапа | временный кэш |
| **Files — Caches/tmp** | то, что можно перекачать | то, что нельзя потерять |
| **Core Data / SQLite / SwiftData** | офлайн-датасет | секреты без шифрования |

**Папки песочницы:**
- `Documents`, `Library/Application Support`, `Library/Caches`, `tmp` — назначение каждой.
- Что попадает в бэкап iCloud, а что нет; флаг `isExcludedFromBackup`.
- Что система удаляет под нехватку места (`Caches`, `tmp`).
- 🔑 Почему билеты и черновики ≠ кэш и должны лежать в правильном месте.

### 3.3. Keychain и Data Protection (7 мин)
- Атрибуты доступности: `WhenUnlocked`, `AfterFirstUnlock`, `...ThisDeviceOnly` (чтобы секрет не уехал в бэкап на другое устройство).
- Data Protection — классы шифрования файлов при заблокированном устройстве.
- Secure Enclave — где реально живут ключи.

### 3.4. FaceID / Touch ID (7 мин)
- `LocalAuthentication` (`LAContext`) — гейт на вход / просмотр билета / подтверждение оплаты.
- `deviceOwnerAuthenticationWithBiometrics` vs `deviceOwnerAuthentication` (фолбэк на пароль устройства).
- Привязка к Keychain через `SecAccessControl` (`.biometryCurrentSet`) — данные становятся недоступны при добавлении нового лица/отпечатка.
- 🔑 **FaceID — это доступ (гейт), а не шифрование.** Шифрует Secure Enclave / Keychain.

### Что показать
- 🎬 **Коммит 6** — токен в Keychain.
- 🎬 **Коммит 7** — FaceID-гейт на билет/оплату.

---

## Блок 4. Итоги (10 мин)

- **BLE-оплата офлайн — только на словах, ~3 мин:**
  - предзагруженные подписанные токены, пока есть сеть;
  - срок жизни, лимиты по сумме/количеству, подпись сервера;
  - чтобы украденный телефон не означал бесконечную офлайн-оплату;
  - связь с предыдущими блоками: токены в Keychain, подтверждение через FaceID, транзакции через outbox.
- Чек-лист отказоустойчивого приложения (финальный слайд, см. ниже).
- Типичные ошибки: протухший кэш, секреты в `UserDefaults`, билеты в `Caches`, FaceID без привязки к Keychain, отсутствие очистки при логауте.
- Q&A (вопросы собираем в конец, чтобы не расплыть тайминг).

---

## Тайминг-сводка

| Блок | Тема | Время | Коммиты |
|---|---|---|---|
| 0 | Введение и проблема | 8 мин | 1 |
| 1 | Кэш + инвалидация | 22 мин | 2–3 |
| 2 | Offline-first | 22 мин | 4–5 |
| 3 | Безопасность и хранение | 28 мин | 6–7 |
| 4 | Итоги + BLE на словах | 10 мин | — |
| | **Итого** | **90 мин** | **7 коммитов** |

---

## План Б при перерасходе времени

Режем в этом порядке:
1. **Data Protection** (3.3) — до одного слайда.
2. **Глубина outbox** (2.3) — показать только идею + коммит, без разбора конфликтов.
3. **Кэш изображений** (1.2) — упомянуть одной фразой.

**Что НЕ резать ни при каких условиях** (смысловое ядро):
- Инвалидация кэша (1.3).
- Карта хранилищ + папки песочницы (3.2).
- Тезис «FaceID — гейт, а не шифрование» (3.4).

**Правила тайминга:**
- Q&A — только в конце, не внутри блоков.
- Демо переключения в авиарежим — live на устройстве (коммит 1).
- Буфер 5 минут держать за счёт блока 4.

---

## Чек-лист отказоустойчивого приложения

- [ ] Данные читаются из локального источника правды, сеть только синхронизирует.
- [ ] У кэша есть TTL/версия; есть стратегия инвалидации и очистка при логауте.
- [ ] Пользователю честно показывается актуальность данных («данные от …»).
- [ ] Действия без сети уходят в outbox с идемпотентностью.
- [ ] Секреты — только в Keychain с правильным классом доступности.
- [ ] Файлы лежат в правильных папках песочницы; критичное исключено из ненужного бэкапа.
- [ ] Чувствительные экраны/операции защищены FaceID, токены привязаны к биометрии.
- [ ] Офлайн-токены оплаты ограничены сроком, лимитом и подписью.

---

## Приложение A. Как работает URLCache (углублённо к блоку 1.1)

`URLCache` — встроенный в Foundation кэш HTTP-ответов, работающий **на уровне `URLSession`**, прозрачно для кода. Вы делаете обычный запрос, а система сама решает: отдать ответ из кэша или сходить в сеть, опираясь на HTTP-заголовки.

### Что хранит
Единица хранения — пара **запрос → ответ** (`CachedURLResponse`):
- `URLResponse` (заголовки, статус-код);
- тело ответа (`Data`);
- `userInfo` и политику хранения (`storagePolicy`).

Ключ — `URLRequest` (на практике Foundation ключует в основном по URL; вариативность по заголовкам — только через `Vary`, и поддержана слабо). По умолчанию кэшируются ответы на **GET** со статусом 200 (HTTP допускает и другие коды — 203, 301, 410, — но это краевые случаи).

### Два уровня: память и диск
```swift
let cache = URLCache(
    memoryCapacity: 16 * 1024 * 1024,   // 16 MB RAM
    diskCapacity: 128 * 1024 * 1024,    // 128 MB disk
    diskPath: "api-cache"
)
```
- **Memory** — быстрый кэш в RAM, живёт пока запущено приложение.
- **Disk** — переживает перезапуск; лежит в `Library/Caches` (ОС вправе вычистить под нехватку места — поэтому критичные данные туда нельзя).
- При превышении ёмкости старые записи вытесняются автоматически.

Подключение к сессии:
```swift
let config = URLSessionConfiguration.default
config.urlCache = cache
config.requestCachePolicy = .useProtocolCachePolicy
```

### Главное: кэшем управляет сервер через заголовки
`URLCache` следует HTTP-семантике, а не угадывает сам. Ключевая мысль: **не клиент решает, кэшировать или нет — это диктует сервер заголовками ответа, а клиент их исполняет.**

При наличии сохранённого ответа система задаёт два последовательных вопроса, за которые отвечают два разных механизма HTTP — **свежесть (freshness)** и **валидация (validation)**:
1. **«Ответ ещё свежий?»** Если да — отдаём из кэша мгновенно, в сеть не идём вообще (ноль трафика, ноль задержки).
2. **«Если уже не свежий (stale) — можно ли по-дешёвому перепроверить?»** Если да — делаем **условный запрос**: сервер либо отвечает «не менялось» коротким ответом без тела, либо присылает новую версию.

#### Заголовки свежести — «сколько можно не ходить в сеть»
Сервер кладёт их в **ответ**:
- **`Cache-Control: max-age=3600`** — основной механизм: ответ свежий 3600 секунд с момента получения. В это окно `URLSession` отдаёт его из кэша без сети.
- **`Cache-Control: no-store`** — «не сохранять вообще» (ни память, ни диск). Для чувствительных данных — балансы, персональные данные.
- **`Cache-Control: no-cache`** — обманчивое имя: это **не** «не кэшировать». Это «сохрани, но **никогда не отдавай без перепроверки** на сервере» (всегда условный запрос).
- **`Cache-Control: private` / `public`** — кэшировать только на клиенте / можно где угодно (включая прокси и CDN).
- **`Expires: <дата>`** — устаревший абсолютный аналог `max-age`; если есть оба, `max-age` побеждает.

#### Заголовки валидации — «как дёшево перепроверить устаревшее»
Когда свежесть истекла, выбрасывать кэш необязательно — сначала спрашиваем сервер «моя версия ещё актуальна?». Работают **парами** (сервер прислал в ответе → клиент шлёт в следующем запросе):
- **`ETag: "abc123"`** (ответ) ↔ **`If-None-Match: "abc123"`** (запрос) — «отпечаток»/версия ресурса. Точный механизм: реагирует на любое изменение байт.
- **`Last-Modified: <дата>`** (ответ) ↔ **`If-Modified-Since: <дата>`** (запрос) — то же по дате (разрешение 1 секунда, проще, но грубее).

Ответ сервера на условный запрос:
- **`304 Not Modified`** — «не менялось, бери из кэша». Тело не передаётся; `URLSession` сам достаёт тело из кэша и отдаёт тебе как обычный успех — в коде ты даже не видишь, что был 304.
- **`200 OK`** с новым телом и новым `ETag`/`Last-Modified` — ресурс изменился, вот свежая версия.

> `If-None-Match` / `If-Modified-Since` клиент подставляет **автоматически** при `.useProtocolCachePolicy` — вручную их формировать не нужно.

#### Откуда это: стандарт HTTP (а не «фича Apple»)
Кэширование и `ETag` — **не отдельный протокол и не изобретение Apple**, а часть HTTP. `URLSession` просто реализует общий стандарт; так же это работает в браузере, `curl`, OkHttp и любом HTTP-клиенте. `ETag` — это строка-«отпечаток» версии ресурса, которую сервер вычисляет по своим правилам (хэш тела, версия в БД, timestamp); стандарт описывает не *как* её считать, а **протокол обмена**: сервер прислал `ETag` → клиент запомнил → шлёт `If-None-Match` → сервер отвечает `304` или `200`.

Актуальные стандарты — **RFC 9110 «HTTP Semantics»** и **RFC 9111 «HTTP Caching»** (оба 2022; пришли на смену RFC 2616 и RFC 7230–7235).

| Что | Где описано |
|---|---|
| Заголовок `ETag` | RFC 9110, §8.8.3 |
| `Last-Modified` | RFC 9110, §8.8.2 |
| Условные запросы (общая глава) | RFC 9110, §13 |
| `If-None-Match` | RFC 9110, §13.1.2 |
| `If-Modified-Since` | RFC 9110, §13.1.3 |
| Статус `304 Not Modified` | RFC 9110, §15.4.5 |
| Кэширование, свежесть, `Cache-Control` | RFC 9111 (целиком) |

Почитать: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110) · [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111) · MDN: [ETag](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/ETag), [Conditional requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Conditional_requests), [HTTP caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching) · Apple: [URLCache](https://developer.apple.com/documentation/foundation/urlcache).

#### Дерево решений URLCache (при `.useProtocolCachePolicy`)
```
Есть ли в кэше ответ на этот запрос?
├─ Нет → идём в сеть, сохраняем (если заголовки разрешают)
└─ Да → Он ещё свежий (по max-age / Expires)?
        ├─ Да → отдаём из кэша, в сеть НЕ идём ✅ (быстро, без трафика)
        └─ Нет (stale) → Есть ETag / Last-Modified?
                ├─ Да → условный запрос (If-None-Match / If-Modified-Since)
                │       ├─ 304 → отдаём тело из кэша (трафик ~0) ✅
                │       └─ 200 → берём новый ответ, обновляем кэш
                └─ Нет → идём в сеть за полным ответом
```

#### Конкретный пример (наш API)
`jsonplaceholder.typicode.com` на GET `/posts` отвечает с `Cache-Control: max-age=43200` и `ETag`:
1. **Первый запрос** — сеть, сохраняем JSON + `ETag` + пометку «свежо 43200 сек».
2. **Через 5 минут** — ответ свежий → мгновенно из кэша, сети нет.
3. **Через 13 часов** — свежесть истекла → `URLSession` сам шлёт `If-None-Match` → сервер отвечает `304` → отдаётся тело из кэша.
4. **Нет сети совсем** — `session.data` бросит ошибку (stale + проверить нельзя), и срабатывает наш ручной offline-фолбэк (см. ниже).

Срок жизни в `URLCache` определяет **сервер**. Это отличие от нашего собственного TTL в `CacheManager` (блок 1.3), который не зависит от заголовков.

### Политики (`requestCachePolicy`)
- **`.useProtocolCachePolicy`** (дефолт, наш выбор) — строго по заголовкам.
- **`.reloadIgnoringLocalCacheData`** — всегда сеть, кэш игнорировать (так у нас сделаны картинки в `ImageLoader`).
- **`.returnCacheDataElseLoad`** — сначала кэш, сеть если пусто.
- **`.returnCacheDataDontLoad`** — только кэш, в сеть не ходить (явный offline-режим).

### Как используется в проекте
```swift
do {
    let (rawData, response) = try await session.data(for: request)   // online: сеть + автокэш
    try validate(response)
    cacheManager.saveTimestamp(for: endpoint.cacheKey)
    return Fetched(value: try decode(rawData), dataSource: .network)
} catch {
    if let cached = cache.cachedResponse(for: request),             // offline: ручной фолбэк
       let value = try? decode(cached.data) as T {
        let source = cacheManager.dataSource(for: endpoint.cacheKey, isNetworkAvailable: false)
        return Fetched(value: value, dataSource: source)
    }
    throw APIError.transport(error)
}
```
При `.useProtocolCachePolicy` система сама отдаст свежий кэш. Но если сети нет совсем — `session.data` бросает ошибку, и мы вручную достаём последний ответ через `cachedResponse(for:)`. Это offline-фолбэк: показать сохранённое, даже если по HTTP оно протухло. Источник данных фиксируется в `Fetched.dataSource` (`.network` / `.staleCache` / `.offlineCache`), а `isFromCache` — производное от него.

### Полезные операции
- `cache.cachedResponse(for:)` — достать вручную;
- `cache.storeCachedResponse(_:for:)` — положить вручную;
- `cache.removeCachedResponse(for:)` / `removeAllCachedResponses()` — инвалидация (второе вызываем в `CacheManager.clearAll()` при логауте).

### Ключевой код: свой дисковый кэш картинок (обход редиректа)
Вместо `URLCache` для картинок — явный файловый кэш с детерминированным ключом `SHA256(исходный URL)`, поэтому редирект на CDN не ломает попадание. Трёхуровневая схема: память → диск → сеть.
```swift
final class ImageLoader {
    private let memory = NSCache<NSURL, UIImage>()   // L1: RAM, авто-эвикция
    let diskCacheURL: URL                            // L2: Library/Caches/image-disk-cache

    func image(for url: URL) async throws -> UIImage {
        if let cached = memory.object(forKey: url as NSURL) { return cached }   // L1
        if let image = loadFromDisk(for: url) {                                 // L2
            memory.setObject(image, forKey: url as NSURL)
            return image
        }
        let (data, _) = try await session.data(from: url)                       // L3
        guard let image = UIImage(data: data) else { throw URLError(.cannotDecodeContentData) }
        saveToDisk(data, for: url)
        memory.setObject(image, forKey: url as NSURL)
        return image
    }

    // ключ файла = SHA256(absoluteString) — не зависит от 3xx-редиректа
    private func diskFileURL(for url: URL) -> URL {
        let digest = SHA256.hash(data: Data(url.absoluteString.utf8))
        let hex = digest.map { String(format: "%02x", $0) }.joined()
        return diskCacheURL.appendingPathComponent(hex)
    }
}
```

#### Редиректы (3xx) и URLCache — почему картинки ломают автокэш

Многие CDN (в т.ч. `picsum.photos` в демо) отдают картинку через **302** на финальный URL. `URLSession` следует редиректу прозрачно — в коде вы передаёте исходный URL, получаете `Data`, но внутри было два запроса.

**Как ломается `URLCache`:**
1. Запрос: `GET https://picsum.photos/seed/42/200/120`
2. Ответ: `302` → `Location: https://fastly.picsum.photos/.../237.jpg`
3. `URLSession` автоматически: `GET fastly.../237.jpg` → `200` + JPEG
4. **`URLCache` сохраняет** ответ под ключом **финального** URL (`fastly.../237.jpg`)
5. **Следующий поиск** идёт по **исходному** URL (`picsum.photos/seed/42/...`) → **cache miss**

```
Сохранили:  fastly.picsum.photos/.../237.jpg  →  JPEG
Ищем:       picsum.photos/seed/42/...         →  ❌ промах
```

Для `GET /posts` (JSONPlaceholder) редиректа нет — URL один и тот же, `URLCache` работает. Для картинок — нет.

**Почему `NSCache` в RAM не спасает:** ключ — исходный URL, вы кладёте сами. Проблема после перезапуска или офлайна, когда память пуста и остаётся только дисковый `URLCache` с «чужим» ключом.

**Решение в проекте:** для картинок `urlCache = nil` + свой дисковый кэш с `SHA256(исходный URL)` — индекс по адресу, который видит приложение, а не по URL после 302.

> «`URLCache` ключует ответ по URL запроса. CDN отдаёт 302 — сохранение и поиск расходятся. Свой кэш с ключом по **исходному** URL.»

### Подводные камни (для слайда)
1. **Редиректы (3xx):** см. разбор выше; для картинок — свой дисковый кэш с ключом по исходному URL.
2. **Только GET и корректные заголовки:** при `no-store` или отсутствии `Cache-Control`/`ETag` кэш может не работать как ожидается.
3. **`Library/Caches` нестабилен:** ОС удаляет под давлением диска — не для критичных данных (билет → отдельное хранилище, блок 2.1).
4. **POST не кэшируется** по умолчанию — для offline-записи нужен outbox (блок 2.3).

### Резюме
`URLCache` — «бесплатный» HTTP-кэш на уровне сессии: подключаете `urlCache`, и `URLSession` кэширует GET-ответы по заголовкам сервера. Поведением управляете через `requestCachePolicy`, а в offline вручную достаёте сохранённый ответ. Минусы — зависимость от заголовков, нюанс с редиректами и нестабильность дискового хранилища, поэтому для серьёзного offline дальше вводятся свой TTL, отдельный источник правды и outbox.

---

## Приложение B. Инвалидация кэша (углублённо к блоку 1.3)

**Самое главное в коммите 3 — управление актуальностью кэша, а не сам кэш.** Коммит 2 научил приложение *показывать* сохранённые данные офлайн. Коммит 3 отвечает на более сложный вопрос: **как не показать протухшее и не утечь чужие данные.** Это место, где чаще всего ошибаются — «положить в кэш» легко, «вовремя выкинуть» сложно.

В `CacheManager` появляется единая точка управления жизненным циклом кэша. Три механизма:

### 1. TTL (time-to-live)
У каждой записи есть «возраст»; данные старше порога (`cacheTTL`) считаются устаревшими.
- Реализован паттерн **stale-while-revalidate**: показать кэш сразу, а в фоне пойти за свежим.
- UI честно сообщает источник через `enum DataSource { network / staleCache / offlineCache }` и бейджи (`CacheBadge` / `StaleBadge` / `OfflineBadge`).
- Срок жизни определяет **приложение**, а не сервер — в отличие от `URLCache` (Приложение A), который зависит только от HTTP-заголовков.

```swift
enum DataSource: Equatable {
    case network
    case staleCache(age: TimeInterval)
    case offlineCache
}

// после успешного ответа из сети — запоминаем момент получения
func saveTimestamp(for key: String) {
    var timestamps = storedTimestamps()
    timestamps[key] = Date()
    if let data = try? JSONEncoder().encode(timestamps) {
        UserDefaults.standard.set(data, forKey: timestampKey)
    }
}

// возраст записи + наличие сети → откуда показываем данные
func dataSource(for key: String, isNetworkAvailable: Bool) -> DataSource {
    guard let savedAt = storedTimestamps()[key] else {
        return isNetworkAvailable ? .staleCache(age: .infinity) : .offlineCache
    }
    let age = Date().timeIntervalSince(savedAt)
    if !isNetworkAvailable { return .offlineCache }
    if age <= CacheManager.cacheTTL { return .offlineCache }
    return .staleCache(age: age)
}
```

### 2. Версионирование схемы
Константа `cacheSchemaVersion`: при смене версии модели данных весь старый кэш сбрасывается на старте приложения.
- Защита от «показали данные в формате, который мы больше не поддерживаем».
- На демо: достаточно изменить константу и перезапустить — кэш снесён.

### 3. Очистка при логауте — главный акцент
🔑 **Это безопасность, а не просто гигиена кэша.** Классическая утечка:
- пользователь A залогинился → лента/данные закэшировались;
- A вышел из аккаунта;
- зашёл пользователь B → **видит данные A из кэша**.

`CacheManager.clearAll()`, вызываемый из `SessionStore.logout()`, за один вызов чистит **все слои**: `URLCache` (HTTP-ответы), TTL-метаданные и кэш картинок (память + диск) через `ImageLoader.clearCache()`.
- Ключевая идея — **единая точка очистки**: невозможно забыть один из слоёв.

```swift
// CacheManager — единая точка очистки всех слоёв кэша
func clearAll() {
    urlCache.removeAllCachedResponses()                 // HTTP-ответы
    UserDefaults.standard.removeObject(forKey: timestampKey)  // TTL-метаданные
    ImageLoader.shared.clearCache()                     // картинки: RAM + диск
}

// SessionStore.logout() — дёргает единую точку
func logout() {
    currentUser = nil
    UserDefaults.standard.removeObject(forKey: userDefaultsKey)
    CacheManager.shared.clearAll()                      // ← чужие данные не утекут
    TicketRepository.shared.clearLocal()
}
```

### Почему это «ядро» лекции
Инвалидация кэша помечена как то, что **нельзя резать ни при каких условиях** (см. «План Б»). Причина: здесь возникают и баги (протухшие данные), и уязвимости (чужие данные после логаута).

### Одна фраза для слайда
> «Кэш без стратегии инвалидации — это не оптимизация, а отложенный баг или утечка. Самое важное — очистка при логауте через единую точку: вышел пользователь A — пользователь B не должен увидеть ничего из его данных.»

### Мостик к блоку 2
TTL / версия / логаут управляют **кэшем** (производные данные). Но для критичных пользовательских данных (билет) кэша недостаточно — там нужен полноценный источник правды (блок 2.1, коммит 4).

---

## Приложение C. LocalStore как источник правды (углублённо к блоку 2.1)

**Основная идея коммита 4 — смена парадигмы: локальное хранилище становится источником правды, а сеть лишь синхронизирует его.** Это качественный скачок относительно кэша (коммиты 2–3).

### Кэш vs источник правды

| | Кэш (коммиты 2–3) | LocalStore (коммит 4) |
|---|---|---|
| Роль | фолбэк «если сеть упала» | первоисточник, читается всегда |
| Природа данных | производные (можно потерять) | данные пользователя |
| Папка | `Library/Caches` (ОС может удалить) | `Library/Application Support` (ОС не трогает, бэкапится) |
| Поток | сеть → показать, кэш только при ошибке | диск → показать сразу, сеть обновляет в фоне |

🔑 Для билета фолбэк-кэш недопустим: систему может вычистить `Caches` под нехватку места → пассажир останется без QR на стойке. Поэтому билет хранится как источник правды.

### Папки песочницы iOS
| Папка | Назначение | ОС удаляет? | В бэкапе? |
|---|---|---|---|
| `Documents/` | пользовательские файлы, видны в Finder | нет | да |
| `Library/Application Support/` | **данные приложения (мы здесь)** | нет | да |
| `Library/Caches/` | URLCache, картинки | да (под нехватку места) | нет |
| `tmp/` | временные файлы | да (произвольно) | нет |

### Ключевой код: generic-хранилище в Application Support
```swift
final class LocalStore: @unchecked Sendable {
    static let shared = LocalStore()
    private let baseURL: URL

    private init() {
        let appSupport = FileManager.default.urls(
            for: .applicationSupportDirectory, in: .userDomainMask
        ).first!
        let bundleID = Bundle.main.bundleIdentifier ?? "app"
        baseURL = appSupport.appendingPathComponent(bundleID, isDirectory: true)
        try? FileManager.default.createDirectory(at: baseURL, withIntermediateDirectories: true)
    }

    func save<T: Encodable>(_ value: T, forKey key: String) {
        guard let data = try? JSONEncoder().encode(value) else { return }
        try? data.write(to: fileURL(key), options: .atomic)
    }

    func load<T: Decodable>(forKey key: String) -> T? {
        guard let data = try? Data(contentsOf: fileURL(key)) else { return nil }
        return try? JSONDecoder().decode(T.self, from: data)
    }

    private func fileURL(_ key: String) -> URL {
        baseURL.appendingPathComponent("\(key).json")
    }
}
```

### Ключевой код: local-first репозиторий билета
```swift
final class TicketRepository {
    // 1) мгновенно с диска — работает в авиарежиме, 0 мс
    func loadLocal() -> Ticket? { store.load(forKey: ticketKey) }

    // 2) в фоне обновляем ИСТОЧНИК ПРАВДЫ, не блокируя UI
    func refreshFromNetwork() async throws -> Ticket {
        let result: Fetched<RemoteUser> = try await client.get(.user(id: 1))
        let ticket = Ticket(user: result.value)
        store.save(ticket, forKey: ticketKey)
        store.save(Date(), forKey: syncedAtKey)
        return ticket
    }

    // 3) при логауте — персональные данные не остаются на устройстве
    func clearLocal() {
        store.remove(forKey: ticketKey)
        store.remove(forKey: syncedAtKey)
    }
}
```
Поток на экране: `loadLocal → показать (QR из локального payload) → refreshFromNetwork → тихо обновить`. Экран ошибки возможен только при самом первом запуске без сети, когда локальной копии ещё нет.

### Как было ДО этого коммита (1–3)
Билет грузился так же, как лента и баланс — **прямо из сети** через `APIClient.get(.user(id: 1))`, и жил только в памяти ViewModel (`state: LoadState<Ticket>`). Диска не было.
- **Коммит 1 (online-only):** нет сети → `.failed` → экран ошибки `wifi.slash`. QR **не строится** — данные не пришли. Пассажир офлайн остаётся без билета.
- **Коммиты 2–3 (кэш):** билет «случайно» выигрывал от общего `URLCache` — если ответ `/users/1` лежал в кэше, он мог подхватиться. Но это **кэш**, а не источник правды: лежит в `Library/Caches` (ОС может вычистить), зависит от заголовков и наличия записи. Билет офлайн **мог** показаться, но полагаться на это нельзя.

### Что изменилось в `TicketViewModel`
```swift
// СТАЛО (коммит 4): local-first
func load() async {
    if let local = repository.loadLocal() {      // ① мгновенно с диска
        state = .loaded(local)
        syncStatus = .syncing
    } else {
        state = .loading
    }
    do {
        let fresh = try await repository.refreshFromNetwork()  // ② фоном обновляем источник правды
        state = .loaded(fresh)
        syncStatus = .synced(at: repository.lastSyncedAt ?? Date())
    } catch {
        if case .loaded = state { syncStatus = .offline }      // ③ копия есть → просто «офлайн»
        else { state = .failed(error) }                        // ошибка только при первом запуске без сети
    }
}
```
Отличия от «было»:
- билет берётся **с диска первым** — экран наполняется ещё до сети;
- сеть только **обновляет** копию, а не является единственным источником;
- появился `TicketSyncStatus` (`synced` / `syncing` / `offline`) — пользователь честно видит актуальность;
- экран ошибки теперь только при первом запуске без сети.

**Одной строкой:** было — билет = «то, что вернула сеть» (в памяти, в лучшем случае подстрахован кэшем); стало — билет = «то, что лежит на диске в `Application Support`», а сеть лишь держит копию свежей.

### Почему это «источник правды»
QR строится из **локально сохранённого** `qrPayload`, а не из живого ответа сервера — поэтому посадку можно пройти полностью офлайн. Сеть нужна лишь чтобы держать локальную копию свежей.

### Одна фраза для слайда
> «Кэш отвечает на вопрос "что показать, если сеть упала". Источник правды отвечает иначе: "данные всегда здесь, локально; сеть — лишь механизм их обновления". Для билета, баланса, черновиков — только второй подход; и лежать они должны в `Application Support`, а не в `Caches`.»

### Мостик к блоку 3
Выбор папки песочницы — это не только надёжность, но и безопасность: что попадает в бэкап, а что нет. Эта тема продолжается в блоке 3.2 (карта хранилищ) и далее — секреты уезжают уже не в файлы, а в Keychain.

---

## Приложение D. Outbox-очередь (углублённо к блоку 2.3)

**Основная идея коммита 5 — offline для ЗАПИСИ.** Коммиты 2–4 решали offline для чтения (кэш, локальный билет). Теперь действие пользователя, сделанное без сети, **не теряется** и автоматически отправляется при восстановлении связи.

Раньше «действие» = немедленный сетевой запрос (без сети — провал). Теперь действие сначала пишется в локальную очередь (outbox), UI реагирует оптимистично, а доставкой занимается фоновый воркер, ждущий сеть.

### Из чего собрано
- **`NetworkMonitor`** — обёртка над `NWPathMonitor` с `@Published isOnline`. Знание о сети **заранее**: ОС сообщает о появлении/пропаже связи до попытки запроса.
- **`OutboxItem`** — `Codable`-элемент: `clientID: UUID` (генерируется один раз), `action`, `createdAt`, `status` (`pending`/`inFlight`/`failed`), `retryCount`.
- **`OutboxStore`** — персистентная очередь поверх `LocalStore` (`outbox.json` в `Application Support`); в `init` читается с диска → **переживает перезапуск**.
- **`OutboxProcessor`** — воркер, отправляющий `pending`.

### Знание о сети заранее (NWPathMonitor)
```swift
@MainActor
final class NetworkMonitor: ObservableObject {
    static let shared = NetworkMonitor()
    @Published private(set) var isOnline: Bool = true

    private let monitor = NWPathMonitor()
    private init() {
        monitor.pathUpdateHandler = { [weak self] path in
            let online = path.status == .satisfied
            Task { @MainActor in self?.isOnline = online }
        }
        monitor.start(queue: DispatchQueue(label: "app.networkMonitor"))
    }
}
```

### Воркер: три триггера + backoff
```swift
func start() {
    // ① сеть восстановилась → синхронизируем (суть коммита)
    monitor.$isOnline.filter { $0 }
        .sink { [weak self] _ in Task { await self?.processQueue() } }
        .store(in: &cancellables)
    // ② старт приложения
    if monitor.isOnline { Task { await processQueue() } }
}

func enqueue(_ action: OutboxAction) {
    outbox.enqueue(action)
    if monitor.isOnline { Task { await processQueue() } }  // ③ сразу, если онлайн
}

private func send(_ item: OutboxItem) async {
    // экспоненциальный backoff между ретраями: 1, 2, 4, 8… c
    if item.retryCount > 0 {
        let delay = pow(2.0, Double(item.retryCount - 1))
        if Date().timeIntervalSince(item.createdAt) < delay { return }
    }
    outbox.markInFlight(item.clientID)
    do {
        let _: PostResponse = try await api.post(
            .posts, body: payload,
            idempotencyKey: item.clientID.uuidString   // 🔑 идемпотентность
        )
        outbox.markSent(item.clientID)                 // успех → удаляем
    } catch {
        outbox.markFailed(item.clientID)               // retry++/после N → .failed
    }
}
```

### Поток жизни действия
```
тап «лайк» (даже офлайн)
  → enqueue → запись на диск (pending), UI оптимистично
  → онлайн? нет → ждём NetworkMonitor
  → сеть появилась → processQueue
        pending → inFlight → POST(Idempotency-Key) → markSent (удалён)
        ошибка → markFailed (retry/backoff) → снова pending
```

### Идемпотентность — зачем `clientID`
🔑 `clientID` (UUID) **не меняется** между ретраями и летит в заголовке `Idempotency-Key`. Если ответ потерялся после того, как сервер уже применил операцию, повтор с тем же ключом не создаст дубликат.
> ⚠️ Честная оговорка: в демо сервер (JSONPlaceholder) ключ **не** дедуплицирует и лайки не хранит — это симуляция. Реализована «клиентская половина контракта»; серверную дедупликацию обеспечивает бэкенд.

### Очистка при логауте
`OutboxStore.clearAll()` вызывается из `SessionStore.logout()` рядом с очисткой кэша и билета — неотправленные действия принадлежат конкретному пользователю и не должны «уехать» от имени другого.

### Сценарий демо
1. Airplane Mode → тап «лайк» → в Настройках «в очереди: 1».
2. Убить и перезапустить приложение (всё ещё офлайн) → очередь на месте (читается с `outbox.json`).
3. Выключить Airplane Mode → `NWPathMonitor` ловит переход → воркер сам отправляет → очередь пустеет.

### Одна фраза для слайда
> «Offline-first — это не только про чтение. Запись тоже не должна теряться: действие пишем локально, помечаем оптимистично, а доставку поручаем воркеру, который ждёт сеть. Идемпотентный ключ гарантирует, что повтор при ретрае не задвоит операцию.»

---

## Приложение E. Keychain vs UserDefaults (углублённо к блоку 3.2)

**Основная идея коммита 6 — у пользователя появляется секрет (access token), и решается вопрос «где хранить секреты».** Коммит построен на наглядном контрасте: где **нельзя** (`UserDefaults` — plain-text plist) и где **нужно** (`Keychain` — AES-256 + Secure Enclave). Это начало блока безопасности.

### KeychainStore — обёртка над Security framework
```swift
final class KeychainStore: @unchecked Sendable {
    static let shared = KeychainStore()
    private let service: String

    func save(_ data: Data, account: String) throws {
        // сначала пробуем обновить, иначе — добавить
        let attributes: [CFString: Any] = [
            kSecValueData: data,
            // 🔑 класс доступности — ключевая деталь (см. ниже)
            kSecAttrAccessible: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        let update = SecItemUpdate(baseQuery(account: account) as CFDictionary,
                                   attributes as CFDictionary)
        if update == errSecItemNotFound {
            var add = baseQuery(account: account)
            add[kSecValueData] = data
            add[kSecAttrAccessible] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            let status = SecItemAdd(add as CFDictionary, nil)
            guard status == errSecSuccess else { throw KeychainError.unexpectedStatus(status) }
        }
    }

    private func baseQuery(account: String) -> [CFString: Any] {
        [kSecClass: kSecClassGenericPassword,   // стандартный класс для app-токенов
         kSecAttrService: service,
         kSecAttrAccount: account]
    }
}
```
Плюс `read` (`SecItemCopyMatching`) и `delete` (`SecItemDelete`), ошибки — через `enum KeychainError`.

### Класс доступности: `AfterFirstUnlockThisDeviceOnly`
- **`AfterFirstUnlock`** — токен доступен в фоне после первой разблокировки устройства. Нужно, чтобы фоновый outbox мог слать запросы с `Authorization` без участия пользователя.
- **`ThisDeviceOnly`** — секрет **не уезжает в iCloud-бэкап** и не переносится на другое устройство. Компрометация бэкапа ≠ компрометация токена.

### Жизненный цикл токена в SessionStore
```swift
func login(as name: String) {
    let token = "demo-token-\(UUID().uuidString)"
    try? keychain.save(token, account: tokenKeychainAccount)  // ← в Keychain, НЕ в UserDefaults
    currentUser = name
    accessToken = token
    UserDefaults.standard.set(name, forKey: userDefaultsKey)  // имя — не секрет, можно в UD
    TokenHolder.shared.token = token                          // прокидываем в APIClient
}

private init() {
    currentUser = UserDefaults.standard.string(forKey: userDefaultsKey)
    accessToken = try? keychain.readString(account: tokenKeychainAccount)  // восстановление сессии
    TokenHolder.shared.token = accessToken
}

func logout() {
    try? keychain.delete(account: tokenKeychainAccount)  // ← удаляем секрет первым
    // … затем CacheManager.clearAll() / clearLocal() / Outbox.clearAll()
}
```
`APIClient` берёт токен из `TokenHolder` и добавляет `Authorization: Bearer <token>` к каждому запросу. `TokenHolder` — мостик между `@MainActor SessionStore` и `nonisolated APIClient`.

🔑 Тонкая деталь контраста прямо в коде: **имя пользователя намеренно лежит в `UserDefaults`** (это не секрет — так правильно), а **токен — только в Keychain**.

### Антипример в Настройках (DEMO ONLY)
Соседние секции на экране демонстрируют разницу вживую:
- **🔒 Keychain** — токен зелёным, «Keychain · AES-256», класс доступности, Authorization-заголовок.
- **⚠️ UserDefaults** — кнопка пишет `INSECURE-<uuid>` в `UserDefaults`, тут же читает его обратно **без всякой защиты** (красным) и показывает путь к `Library/Preferences/<bundle>.plist` — этот файл открывается текстовым редактором, токен виден глазами.

### Контраст одной таблицей
| | UserDefaults | Keychain |
|---|---|---|
| Физически | plain-text `.plist` в `Library/Preferences` | зашифрованная БД ОС |
| Шифрование | нет | AES-256, ключи в Secure Enclave |
| Бэкап | уезжает в iCloud как есть | с `ThisDeviceOnly` — не уезжает |
| Доступ | любой с доступом к файлу/бэкапу | только Security API при разблокировке |
| Что класть | настройки, флаги, имя пользователя | **секреты: токены, пароли, ключи** |

### Сценарий демо
1. Войти → секция Keychain показывает токен; перезапустить приложение → токен на месте (восстановлен из Keychain, не из plist).
2. Нажать «Записать токен в UserDefaults» → токен виден красным + путь к plist → открыть файл, секрет читается глазами.
3. Выйти → токен из Keychain удалён.

### Мостик к коммиту 7
Сейчас токен читается **без биометрии** (он нужен фоновому outbox). В коммите 7 добавится второй, **платёжный** токен, привязанный к Keychain через `SecAccessControl(.biometryCurrentSet)` — его чтение потребует FaceID. То есть коммит 6 = «правильное хранилище для секрета», коммит 7 = «биометрический гейт поверх него».

### Одна фраза для слайда
> «`UserDefaults` — это открытый текст. Положить туда токен = отдать его любому, кто получил доступ к бэкапу или файловой системе. Секреты — только в Keychain, с классом доступности, который не пускает их в чужой бэкап.»

---

## Приложение F. Биометрия: FaceID-гейт + SecAccessControl (углублённо к блоку 3.4)

**Основная идея коммита 7 — биометрия как ГЕЙТ ДОСТУПА.** Появляются две вещи: (1) FaceID-замок на экране билета и (2) платёжный токен, привязанный к Keychain через `SecAccessControl` — его чтение само запрашивает FaceID на уровне ОС.

🔑 **Ключевой тезис: FaceID — это гейт, а не шифрование.** Данные билета уже лежат на диске (`Application Support`) и защищены iOS Data Protection. Биометрия не расшифровывает их — она лишь решает: **показать пользователю или нет.**

### Что появляется
- **`BiometricAuth`** — обёртка над `LAContext` с async/await.
- **FaceID-гейт на `TicketView`** — экран блокировки + реблокировка при уходе в фон.
- **`KeychainStore.saveBiometricProtected` / `readBiometricProtected`** — секрет, привязанный к биометрии.
- **Второй секрет `paymentToken`** в `SessionStore` — защищён биометрией (в отличие от `accessToken`).

### BiometricAuth: две политики
```swift
// только биометрия — для ГЕЙТА на билет
func authenticate(reason: String) async -> Result<Void, BiometricError> {
    let ctx = LAContext()
    ctx.localizedFallbackTitle = ""   // убираем кнопку «ввести пароль»
    guard ctx.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: ...) else { ... }
    // evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, …)
}

// биометрия ИЛИ пароль устройства — фолбэк при notEnrolled (напр. симулятор без FaceID)
func authenticateWithFallback(reason: String) async -> Result<Void, BiometricError> {
    // evaluatePolicy(.deviceOwnerAuthentication, …)
}
```
- `.deviceOwnerAuthenticationWithBiometrics` — **только** FaceID/TouchID, без автофолбэка на пароль.
- `.deviceOwnerAuthentication` — биометрия **или** пароль устройства.
- `BiometryType` (faceID/touchID/none) и `BiometricError` (unavailable/notEnrolled/canceled/failed/lockout) — для корректных текстов и иконок в UI.

### FaceID-гейт билета (реблокировка при фоне)
```swift
struct TicketView: View {
    @State private var isUnlocked = false
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        Group {
            if isUnlocked { unlockedContent } else { biometricGateView }
        }
        .onChange(of: scenePhase) { _, newPhase in
            if newPhase == .background { isUnlocked = false }   // ← гейт, не «один раз навсегда»
        }
    }

    private func authenticate() async {
        switch await biometric.authenticate(reason: "Подтвердите личность…") {
        case .success:
            isUnlocked = true
            await viewModel.load()
        case .failure(.notEnrolled):
            // фолбэк на пароль, чтобы симулятор без биометрии не был заблокирован
            if case .success = await biometric.authenticateWithFallback(reason: …) { isUnlocked = true }
        case .failure(.canceled): break
        case .failure(let e): authError = e.errorDescription
        }
    }
}
```
На экране блокировки есть честная подпись: «FaceID не шифрует билет — данные лежат в Application Support. Биометрия решает лишь: показать их или нет».

### Привязка Keychain к биометрии: SecAccessControl
```swift
func saveBiometricProtected(_ string: String, account: String) throws {
    // ACL: текущий набор биометрии; при добавлении нового лица секрет станет недоступен
    let access = SecAccessControlCreateWithFlags(
        kCFAllocatorDefault,
        kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        .biometryCurrentSet,                 // 🔑 не .biometryAny
        &error
    )
    let query: [CFString: Any] = [
        kSecClass: kSecClassGenericPassword,
        kSecAttrService: service,
        kSecAttrAccount: account,
        kSecValueData: data,
        kSecAttrAccessControl: access        // ← привязка к ACL
    ]
    SecItemAdd(query as CFDictionary, nil)
}

func readBiometricProtected(account: String, prompt: String) throws -> String? {
    let ctx = LAContext()
    ctx.localizedReason = prompt
    var query = baseQuery(account: account)
    query[kSecReturnData] = true
    query[kSecUseAuthenticationContext] = ctx   // iOS сама покажет FaceID-промпт
    // SecItemCopyMatching → Secure Enclave проверяет биометрию → отдаёт данные
}
```
🔑 Принципиально: при чтении приложение **не вызывает** `LAContext.evaluatePolicy` вручную — биометрию запрашивает **сам Keychain** через Secure Enclave. Это сильнее, чем «гейт в UI»: секрет физически не отдаётся без биометрии.

**`.biometryCurrentSet` vs `.biometryAny`:**
- `.biometryAny` — добавили новое лицо/отпечаток → секрет **всё ещё** читается (риск).
- `.biometryCurrentSet` — добавили новое лицо → секрет **недоступен** (защита от подмены биометрии). Правильный выбор для платёжных токенов.

### Два токена одного Keychain
| Токен | Класс/ACL | Чтение |
|---|---|---|
| `accessToken` (коммит 6) | `AfterFirstUnlockThisDeviceOnly` | без биометрии (нужен фоновому outbox) |
| `paymentToken` (коммит 7) | `SecAccessControl(.biometryCurrentSet)` | **только через FaceID** на уровне ОС |

`SessionStore.login` сохраняет оба; `logout` удаляет оба (единая точка — все 5 слоёв: Keychain×2 + Cache + LocalStore + Outbox).

### Не забыть: Info.plist
Нужен ключ `NSFaceIDUsageDescription` — без него обращение к FaceID **крашит** приложение.

### Сценарий демо (симулятор)
1. Войти → `Features → Face ID → Enrolled`.
2. Вкладка «Билет» → экран блокировки → «Разблокировать» → `Features → Face ID → Matching Face` → билет с QR.
3. Свернуть и вернуть приложение → билет снова заблокирован (реблокировка при фоне).
4. `Non-matching Face` → ошибка + повтор.
5. В Настройках «показать платёжный токен» → системный FaceID-промпт (Keychain-level, без `evaluatePolicy` в коде).
6. Выключить Enrolled → фолбэк на пароль устройства. Выйти → оба секрета удалены.

### Одна фраза для слайда
> «FaceID — это замок на двери, а не сейф. Данные уже зашифрованы на диске; биометрия только решает, открыть ли их показ. А `SecAccessControl(.biometryCurrentSet)` встраивает биометрию в саму запись Keychain — секрет не отдаётся ОС без живого FaceID, и становится недоступен, если набор биометрии изменили.»
