# Фоновая синхронизация: silent push и смежные механики

> Дополнение к лекции (блок 2.3 Outbox). В демо-приложении синхронизация идёт через `NWPathMonitor` + `OutboxProcessor`. Silent push — **следующий уровень**, когда «сеть появилась» недостаточно или нужен nudge с сервера.

---

## Короткий ответ: можно ли?

**Да, но не как единственный и не как гарантированный механизм.**

Silent push (APNs с `content-available: 1`) даёт iOS **краткий** фоновый запуск (~до 30 с), чтобы приложение могло, например, **дренировать outbox** — отправить накопленные лайки/транзакции, подтянуть свежие билеты.

Это **не замена** `NWPathMonitor` и outbox, а **дополнительный триггер**: «сервер говорит: пора синхronizировать» или «данные на сервере изменились — обнови локальную копию».

---

## Как это работает (механика)

```
Сервер                          APNs                         iPhone
  │                               │                              │
  │  silent push                  │                              │
  │  { "aps": {                   │                              │
  │      "content-available": 1   │                              │
  │    },                         │                              │
  │    "sync": "outbox"           │                              │
  │  }                            │                              │
  ├──────────────────────────────►│─────────────────────────────►│
  │                               │         будит приложение     │
  │                               │         (если ОС разрешит)   │
  │                               │                              │
  │                               │         application(           │
  │                               │           didReceiveRemote…  │
  │                               │         ) → OutboxProcessor  │
  │                               │           .processQueue()    │
  │                               │         → completionHandler  │
  │                               │                              │
  │◄──────────────────────────────┼──────────────────────────────┤ POST /posts …
```

**Что нужно на клиенте:**
- Capability: **Background Modes → Remote notifications**
- Обработчик: `application(_:didReceiveRemoteNotification:fetchCompletionHandler:)` (или эквивалент через `UNUserNotificationCenter` + push delegate)
- Внутри — тот же `OutboxProcessor.processQueue()`, что уже есть в коммите 5
- Обязательно вызвать `completionHandler(.newData | .noData | .failed)` — иначе Apple режет бюджет фоновых запусков

**Что нужно на сервере:**
- APNs (JWT / сертификат), device token пользователя
- Логика «когда слать silent push» (см. сценарии ниже)

---

## Когда silent push **полезен** для нашего кошелька

| Сценарий | Зачем push, если есть NWPathMonitor |
|---|---|
| **Outbox не ушёл часами** | Сеть была, но приложение не запускалось; push — напоминание «пробуй снова» |
| **Сервер знает, что данные изменились** | Новый билет / обновление рейса — push «pull ticket», не ждать открытия приложения |
| **Пользователь в роуминге / captive portal** | `NWPathMonitor` видит «satisfied», но реального интернета нет; сервер шлёт push позже, когда реально доступен |
| **Предзагрузка офлайн-токенов BLE** | «Пополни пачку платёжных токенов, пока есть Wi‑Fi» — nudge с сервера |
| **Инвалидация кэша** | Push с `reason: cache_invalidate` → `CacheManager.clearAll()` или точечный сброс (осторожно с UX) |

---

## Когда silent push **не поможет** (ограничения iOS)

| Ограничение | Следствие |
|---|---|
| **Пользователь force-quit** (смахнул из app switcher) | Silent push **не будит** приложение до ручного запуска |
| **Throttling / бюджет** | Apple дозирует фоновые запуски: частые silent push → доставка реже или не вовсе |
| **Low Power Mode** | Фоновая работа сильно ограничена |
| **Нет разрешения / отозваны уведомления** | На части версий iOS отказ от уведомений влияет на фоновую доставку; поведение менялось — проверять актуальные HIG |
| **~30 секунд** | Длинная синхронизация не влезет — только дренаж outbox + один-два запроса |
| **Не гарантия доставки** | APNs best-effort; нельзя строить критичный контракт «push = обязательно отправили оплату» |
| **Abuse = бан** | Silent push «просто чтобы держать приложение живым» — нарушение правил; только реальная фоновая работа |

**Вывод для лекции:** silent push — **ускоритель и подстраховка**, не фундамент. Фундамент — **локальный outbox + источник правды + NWPathMonitor**.

---

## Архитектура: три триггера одного воркера

Идея: **один** `OutboxProcessor` / sync-сервис, **несколько** триггеров:

```
┌─────────────────────────────────────────────────────────┐
│              OutboxProcessor.processQueue()             │
└────────────────────────▲────────────────────────────────┘
                         │
     ┌───────────────────┼───────────────────┐
     │                   │                   │
  NWPathMonitor      app launch         silent push
  isOnline=true      + foreground       content-available
  (коммит 5)         refresh            (идея)
     │                   │                   │
     └───────────────────┴───────────────────┘
              + BGAppRefreshTask (идея)
              + BGProcessingTask (идея, тяжёлая sync)
```

На слайде: «не плодим логику — плодим **триггеры**».

---

## Идеи payload silent push (контракт с сервером)

```json
{
  "aps": {
    "content-available": 1
  },
  "sync": {
    "action": "drain_outbox",
    "priority": "normal"
  }
}
```

Варианты `action`:

| action | Что делает клиент |
|---|---|
| `drain_outbox` | Только `OutboxProcessor.processQueue()` |
| `refresh_ticket` | `TicketRepository.refreshFromNetwork()` + сохранить в LocalStore |
| `refresh_feed` | `APIClient.get(.posts)` — обновить кэш |
| `prefetch_payment_tokens` | Запросить пачку BLE-токенов → Keychain (блок 4, BLE на словах) |
| `invalidate_cache` | `CacheManager.clearAll()` или по ключу — **осторожно**, только с версией/причиной |

Рекомендация: **узкий payload**, idempotency на клиенте (тот же `clientID` в outbox уже есть).

---

## Смежные механики (не silent push, но в одной теме)

### BGAppRefreshTask / BGProcessingTask (BackgroundTasks framework)

- **App Refresh** — система сама выбирает окно (~15 мин+), приложение регистрирует `BGAppRefreshTaskRequest`
- **Processing** — длинные задачи (минуты), когда устройство на зарядке и Wi‑Fi
- Хорошо для: «дослать outbox, когда система дала слот», без push
- Минус: время непредсказуемо

### Push + Background Tasks вместе

```
silent push received
  → schedule BGProcessingTask если outbox > N элементов
  → иначе сразу processQueue() в fetch handler
```

### VoIP / PushKit

- Для звонков; **не** для outbox — Apple жёстко режет злоупотребления

### Significant Location Change / Region Monitoring

- Для «пользователь приехал в аэропорт — обнови посадочный»; тяжёлая UX/permission история, не для демо

---

## Связь с темами лекции

| Тема лекции | Как ложится silent push |
|---|---|
| **Outbox + идемпотентность** | Push будит → те же POST с `Idempotency-Key`; дубликаты не страшны |
| **Keychain `AfterFirstUnlock`** | Фон после первой разблокировки — токен для POST доступен |
| **Offline-first** | Push не создаёт зависимость от сети в UI; только фоновый drain |
| **Инвалидация кэша** | Push «данные устарели» — альтернатива polling; риск: лишняя агрессия |
| **BLE офлайн-токены** | Push «пополни кошелёк токенов» пока Wi‑Fi — сильный story для блока 4 |

---

## Сценарий для демо (если когда-нибудь расширять проект)

1. Пользователь офлайн ставит 3 лайка → outbox = 3.
2. Включает сеть, **не открывает** приложение.
3. Сервер (или тестовый скрипт) шлёт silent push `drain_outbox`.
4. Приложение в фоне отправляет 3 POST, outbox пустеет.
5. Пользователь открывает приложение — «ожидает отправки» уже нет.

**Для лекции без живого APNs:** достаточно слайда + схема; реальный APNs требует Apple Developer, provisioning, device token.

---

## Чек-лист «делать / не делать»

**Делать:**
- [ ] Один код path для sync из push и из `NWPathMonitor`
- [ ] Короткая работа в `fetchCompletionHandler`, честный `completionHandler`
- [ ] Идемпотентность outbox (уже есть)
- [ ] Логирование «sync triggered by: push | path | bg_task» для отладки
- [ ] Push только при реальной работе (drain / refresh)

**Не делать:**
- [ ] Silent push как единственный способ отправить критичные данные
- [ ] Частые push «каждые 5 минут проверь сеть»
- [ ] Хранить секреты в payload push
- [ ] Полагаться на push после force-quit
- [ ] Visible notification маскировать под silent без `content-available`

---

## Одна фраза для слайда

> «Outbox + NWPathMonitor покрывают offline **когда приложение уже живо**. Silent push — **опциональный nudge** от сервера: разбуди на ~30 секунд и дожми очередь, но iOS не гарантирует доставку и режет злоупотребления. Архитектура: один воркер — много триггеров.»

---

## Ссылки (актуализировать перед лекцией)

- [Pushing background updates to your app](https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/pushing_background_updates_to_your_app) — Apple
- [Background Tasks framework](https://developer.apple.com/documentation/backgroundtasks) — BGAppRefreshTask, BGProcessingTask
- [Using background tasks to update your app](https://developer.apple.com/documentation/uikit/using-background-tasks-to-update-your-app)
