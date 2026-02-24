# РАССЛЕДОВАНИЕ: Безопасность мессенджера MAX (ru.oneme.app) v26.5.0

## Аудит на основе декомпиляции Android-приложения | Февраль 2026

---

## СОДЕРЖАНИЕ

1. [Введение](#1-введение)
2. [Общая архитектура и происхождение](#2-общая-архитектура-и-происхождение)
3. [Разрешения приложения — полный доступ к устройству](#3-разрешения-приложения--полный-доступ-к-устройству)
4. [Протоколы передачи данных](#4-протоколы-передачи-данных)
5. [Куда уходят данные — карта серверов](#5-куда-уходят-данные--карта-серверов)
6. [Шифрование: что защищено, а что нет](#6-шифрование-что-защищено-а-что-нет)
7. [7 систем аналитики и слежки](#7-семь-систем-аналитики-и-слежки)
8. [Синхронизация контактов — скрытый сбор данных](#8-синхронизация-контактов--скрытый-сбор-данных)
9. [Фингерпринтинг устройства](#9-фингерпринтинг-устройства)
10. [Mobile ID — cleartext-трафик к операторам](#10-mobile-id--cleartext-трафик-к-операторам)
11. [Доступ к другим приложениям](#11-доступ-к-другим-приложениям)
12. [Локальное хранение данных](#12-локальное-хранение-данных)
13. [Итоговая карта потоков данных](#13-итоговая-карта-потоков-данных)
14. [Выводы и оценка рисков](#14-выводы-и-оценка-рисков)

---

## 1. Введение

Данное расследование представляет собой результат полного реверс-инжиниринга APK-файла мессенджера **MAX** (пакет `ru.oneme.app`, версия 26.5.0, build 6558). Исходный код был получен путём декомпиляции и деобфускации Java/Kotlin-классов. Анализу подвергнуты: манифест приложения, все сетевые эндпоинты, protobuf-структуры данных, SDK аналитики, конфигурации безопасности, нативные библиотеки и конфигурации Huawei/Google-сервисов.

**Ключевой вывод**: MAX — это ребрендированный мессенджер **TamTam/OneMe** от **VK Group** (ранее Mail.ru Group), глубоко интегрированный с инфраструктурой **Одноклассников (OK.ru)**. Приложение содержит **7 независимых систем аналитики**, отправляет данные минимум на **4 различных сервера аналитики**, не имеет **end-to-end шифрования** сообщений и собирает **контакты устройства**, включая номера телефонов людей, не являющихся пользователями MAX.

---

## 2. Общая архитектура и происхождение

### Генеалогия приложения

Декомпиляция выявила чёткую цепочку происхождения:

```
OK.ru (Одноклассники)
  └── TamTam Messenger (ru.ok.tamtam)
        └── OneMe (one.me / ru.oneme.app)
              └── MAX (ребрендинг, тот же пакет ru.oneme.app)
```

**Доказательства:**
- Пакет `ru.ok.tamtam.android` — сервисы, базы данных, уведомления
- Пакет `ru.ok.messages` — медиа, фоторедактор
- Пакет `one.me.android` — основное приложение
- Класс приложения: `one.me.android.OneMeApplication`
- API бэкенд: `api.ok.ru` (Одноклассники)
- Protobuf-классы: `ru.ok.tamtam.nano.Protos`, `ru.ok.tamtam.nano.Tasks`
- PageID AppGallery Huawei: `C113469599`
- Huawei AppID: `113469599`

### Технологический стек

| Компонент | Технология |
|---|---|
| Язык | Java + Kotlin |
| Сеть (REST) | OkHttp (HTTP/2) |
| Сеть (realtime) | WebSocket + Protobuf Nano |
| Звонки (сигнализация) | WebTransport/QUIC (Kwik/Flupke) + WebSocket (fallback) |
| Звонки (медиа) | WebRTC |
| Карты | Яндекс.Карты (тайлы + геокодирование) + Huawei Maps |
| Push | Huawei HMS Push + Firebase FCM |
| Аналитика | MyTracker + OneLog + AppTracer + HMS Analytics + OpenTelemetry |
| Сканер QR | Google ML Kit Barcode |
| Анимации | RLottie (нативная библиотека) |
| Медиа | AndroidX Media3 (ExoPlayer) |

---

## 3. Разрешения приложения — полный доступ к устройству

### Критические разрешения

| Разрешение | Доступ | Риск |
|---|---|---|
| `READ_CONTACTS` + `WRITE_CONTACTS` | **Полный доступ к адресной книге** — чтение и запись | Высокий |
| `ACCESS_FINE_LOCATION` + `ACCESS_COARSE_LOCATION` | Точная геолокация (GPS + Wi-Fi + сотовые вышки) | Высокий |
| `CAMERA` | Доступ к камере | Средний |
| `RECORD_AUDIO` | Доступ к микрофону | Средний |
| `READ_MEDIA_IMAGES` + `READ_MEDIA_VIDEO` | Все фото и видео на устройстве | Средний |
| `BLUETOOTH_CONNECT` | Подключение к Bluetooth-устройствам | Средний |
| `SYSTEM_ALERT_WINDOW` | Отображение поверх других приложений | Средний |
| `USE_BIOMETRIC` + `USE_FINGERPRINT` | Биометрические данные | Средний |
| `com.google.android.gms.permission.AD_ID` | **Рекламный идентификатор Google** | Высокий |
| `REQUEST_INSTALL_PACKAGES` | Установка APK-файлов | Средний |
| `RECEIVE_BOOT_COMPLETED` | **Автозапуск при включении устройства** | Средний |
| `CHANGE_NETWORK_STATE` + `CHANGE_WIFI_STATE` | Изменение сетевых настроек | Низкий |

### Разрешения для фоновых сервисов

Приложение регистрирует **5 типов Foreground Service**:
- `FOREGROUND_SERVICE_MICROPHONE` — фоновый доступ к микрофону
- `FOREGROUND_SERVICE_CAMERA` — фоновый доступ к камере
- `FOREGROUND_SERVICE_MEDIA_PROJECTION` — запись экрана
- `FOREGROUND_SERVICE_MEDIA_PLAYBACK` — фоновое воспроизведение
- `FOREGROUND_SERVICE_DATA_SYNC` — фоновая синхронизация данных

### Разрешения для лаунчеров (badge-счётчики)

Приложение запрашивает доступ к badge-API **7 производителей**: Samsung, Sony, HTC, Huawei, OPPO, Majeur, а также универсальный `me.everything.badger`.

---

## 4. Протоколы передачи данных

### 4.1 Основной канал сообщений: WebSocket + Protobuf

```
Клиент ←→ api.oneme.ru:443 (TLS 1.2/1.3)
Протокол: WebSocket
Формат данных: Protocol Buffers (Nano)
```

Все сообщения, чаты, контакты, статусы и задачи (Tasks) передаются через постоянное WebSocket-соединение на `api.oneme.ru`. Данные сериализуются через **Protobuf Nano** (`com.google.protobuf.nano`).

Полный список задач (56 типов), передаваемых через protobuf:
`MsgSend`, `MsgEdit`, `MsgDelete`, `MsgDeleteRange`, `MsgReact`, `MsgCancelReaction`, `ChatCreate`, `ChatUpdate`, `ChatDelete`, `ChatClear`, `ChatHide`, `ChatSubscribe`, `ChatsList`, `ContactUpdate`, `ContactVerify`, `Config`, `FileUpload`, `FileDownload`, `VideoUpload`, `VideoConvert`, `VideoPlay`, `LocationRequest`, `LocationStop`, `CritLog` и другие.

### 4.2 REST API: HTTPS + JSON

```
Клиент → api.ok.ru (HTTPS)
Формат: JSON
Методы: log.externalLog, vchat.clientStats и др.
```

Вся аналитика и вспомогательные запросы идут через REST API на серверы Одноклассников.

### 4.3 Звонки: WebTransport/QUIC + WebRTC

```
Сигнализация: WebTransport (QUIC/TLS 1.3) → динамический сервер
              WebSocket (fallback) → динамический сервер
Медиа:        WebRTC (SRTP) через TURN/STUN серверы
```

Для VoIP-звонков используется **WebTransport** на основе QUIC-стека **Kwik/Flupke** (библиотека `tech.kwik`). Это обеспечивает TLS 1.3 шифрование с cipher suites AES-128-GCM. При невозможности QUIC-соединения происходит fallback на WebSocket. Адреса сигнальных серверов и TURN/STUN-серверов **приходят динамически** с основного API при инициации звонка.

### 4.4 Аналитика: HTTPS POST

```
MyTracker → tracker-api.vk-analytics.ru (HTTPS)
OneLog    → api.ok.ru (HTTPS)
AppTracer → sdk-api.apptracer.ru (HTTPS)
HMS       → GRS-resolved URL (HTTPS)
```

### 4.5 Карты: HTTPS

```
Тайлы карт      → tiles.api-maps.yandex.ru (HTTPS)
Геокодирование   → geocode-maps.yandex.ru (HTTPS)
```

---

## 5. Куда уходят данные — карта серверов

### Серверы MAX (основное приложение)

| Сервер | Назначение | Протокол |
|---|---|---|
| `api.oneme.ru:443` | **Основной API** — сообщения, чаты, контакты | WebSocket + TLS |
| `api-test.oneme.ru` | Тестовый сервер #1 | WebSocket + TLS |
| `api-tg.oneme.ru` | Тестовый сервер (предп. Telegram-интеграция) | WebSocket + TLS |
| `api-test2.oneme.ru` | Тестовый сервер #2 | WebSocket + TLS |
| `max.ru` / `download.max.ru` | Веб-сайт, загрузка APK | HTTPS |
| `legal.max.ru` | Юридические документы | HTTPS |
| `help.max.ru` | FAQ/Помощь | HTTPS |

### Серверы VK Group / Одноклассники

| Сервер | Назначение | Протокол |
|---|---|---|
| **`api.ok.ru`** | REST API ОК: аналитика OneLog, статистика звонков | HTTPS |
| `api.odnoklassniki.ru` | Альтернативный API ОК | HTTPS |
| **`tracker-api.vk-analytics.ru`** | MyTracker — основная аналитика | HTTPS |
| `ip4.tracker-api.vk-analytics.ru` | MyTracker (IPv4 only) | HTTPS |
| `ts.tracker-api.vk-analytics.ru` | MyTracker — метрики Time Spent | HTTPS |
| `mlapi.tracker-api.vk-analytics.ru` | MyTracker — ML-модели | HTTPS |
| `beta-ml.tracker-api.vk-analytics.ru` | MyTracker — бета ML | HTTPS |
| **`sdk-api.apptracer.ru`** | AppTracer — крашлитика и перфоманс | HTTPS |

### Серверы Яндекс

| Сервер | Назначение |
|---|---|
| `tiles.api-maps.yandex.ru` | Тайлы карт |
| `geocode-maps.yandex.ru` | Обратное геокодирование |

### Серверы Huawei (HMS)

| Категория | Сервер (зона RU) | Назначение |
|---|---|---|
| Push | `data-drru.push.dbankcloud.com` | Push-уведомления |
| Аналитика | `metrics5.dt.dbankcloud.ru` | BI-метрики |
| Логирование | `logservice-drru.dt.dbankcloud.ru` | Логи HMS |
| Геолокация | `openlocation-drru.map.dbankcloud.ru` | Геосервисы |
| Безопасность | `tsms-drru.security.dbankcloud.ru` | Проверка безопасности |
| Конфигурация | `configserver-drru.platform.hicloud.ru` | Удалённая конфигурация |
| CDN | `h5hosting-drru.dbankcdn.ru` | Контент |
| AppGallery | `store-drru.hispace.dbankcloud.ru` | Магазин приложений |
| Маршрутизация | `grs.platform.dbankcloud.ru` | Global Route Service |

### Серверы мобильных операторов (Mobile ID)

| Сервер | Оператор | Протокол |
|---|---|---|
| `mobileid.megafon.ru` | МегаФон | **HTTP (cleartext!)** |
| `idgw.mobileid.mts.ru` | МТС | **HTTP (cleartext!)** |
| `he-mc.tele2.ru` | Tele2 | **HTTP (cleartext!)** |
| `he-mc.t2.ru` | T2 (Tele2) | **HTTP (cleartext!)** |
| `*.beeline.ru` | Билайн (все поддомены!) | **HTTP (cleartext!)** |

### Google

| Сервер | Назначение |
|---|---|
| Google FCM | Push-уведомления |
| Google Maps API (ключ: `AIzaSyDJbuC3fODS_aR7jcOkoP6qWIsQen9XARI`) | Геосервисы |

---

## 6. Шифрование: что защищено, а что нет

### Что ЗАЩИЩЕНО

| Компонент | Механизм защиты |
|---|---|
| Транспорт (основной) | TLS 1.2/1.3 через OkHttp и WebSocket |
| Звонки (сигнализация) | TLS 1.3 через QUIC (AES-128-GCM-SHA256) |
| Звонки (медиа) | SRTP через WebRTC |
| HMS-трафик | TLS с кастомным TrustManager + BKS-сертификаты |
| Биометрия | Android Keystore / HW Keystore |

### Что НЕ ЗАЩИЩЕНО

| Компонент | Проблема | Уровень риска |
|---|---|---|
| **Сообщения (E2E)** | **End-to-end шифрование ОТСУТСТВУЕТ.** Сообщения сериализуются через Protobuf и передаются по TLS-каналу, но НЕ шифруются клиентским ключом. Сервер `api.oneme.ru` имеет полный доступ к содержимому всех сообщений. | **КРИТИЧЕСКИЙ** |
| **Mobile ID трафик** | Авторизация через Mobile ID идёт по **нешифрованному HTTP** к серверам 5 мобильных операторов. Данные SIM-аутентификации передаются в открытом виде. | **ВЫСОКИЙ** |
| **SSL Pinning** | Certificate Pinning через OkHttp `CertificatePinner` **НЕ обнаружен**. Приложение уязвимо к MITM-атакам при компрометации CA. | **СРЕДНИЙ** |
| **Локальная БД** | Room Database (`OneMeRoomDatabase`) **НЕ шифруется** (SQLCipher не используется). На rooted устройствах вся история чатов доступна. | **СРЕДНИЙ** |
| **SharedPreferences** | Токены и сессионные данные хранятся в обычных SharedPreferences **без EncryptedSharedPreferences**. | **СРЕДНИЙ** |

### Отсутствие E2E — детальный анализ

В декомпилированном коде **полностью отсутствуют** признаки end-to-end шифрования:
- Нет обмена ключами (Diffie-Hellman, X3DH, Signal Protocol)
- Нет `Cipher.getInstance("AES")` в пакетах сообщений
- Нет двойного ratchet или аналогичных механизмов
- Протобуф-структура `Protos.Chat` содержит поле `messagesTtlSec` (самоудаляющиеся сообщения), но это серверная функция, а не E2E

**Вывод**: Все сообщения MAX доступны оператору серверов VK Group в открытом виде.

---

## 7. Семь систем аналитики и слежки

### Обзор

В приложении обнаружено **7 независимых систем** сбора данных о пользователе:

| # | Система | Владелец | Сервер отправки | Статус |
|---|---|---|---|---|
| 1 | **MyTracker SDK v4.0.0** | VK Group | `tracker-api.vk-analytics.ru` | Управляется флагом `mytracker-enabled` |
| 2 | **OneLog** | OK.ru / VK | `api.ok.ru` | Управляется флагом `analytics-enabled` |
| 3 | **Calls Analytics SDK v0.1.4** | OK.ru / VK | `api.ok.ru` | Управляется флагом `calls-sdk-incall-stat` |
| 4 | **App Tracer** | OK.ru / VK | `sdk-api.apptracer.ru` | Управляется флагом `tracer-non-fatal-crashed-enabled` |
| 5 | **Firebase Analytics** | Google | Серверы Google | Только AppInstanceId для MyTracker |
| 6 | **Huawei HMS Analytics** | Huawei | GRS-маршруты (`.ru` для РФ) | Включено |
| 7 | **OpenTelemetry** | Open Source | Внутренний context propagation | Без внешней отправки |

---

### 7.1 MyTracker SDK v4.0.0 — главная система слежки

**Tracker ID**: `34982109644049932883`  
**Принадлежит**: VK Analytics (бывш. Mail.ru Group)

#### Что собирает MyTracker

**Персональные данные пользователя:**

| Поле | Тип | Описание |
|---|---|---|
| `customUserId` | Long | **Внутренний ID пользователя MAX** (устанавливается при инициализации) |
| `age` | int | Возраст |
| `gender` | enum | Пол (MALE/FEMALE/UNKNOWN) |
| `emails[]` | String[] | Электронные адреса |
| `phones[]` | String[] | Номера телефонов |
| `okIds[]` | String[] | ID в Одноклассниках |
| `vkIds[]` | String[] | ID ВКонтакте |
| `icqIds[]` | String[] | ID ICQ |
| `vkConnectIds[]` | String[] | VK Connect ID |
| `customParams` | Map | Произвольные доп. параметры |
| `lang` | String | Язык |

**Идентификаторы устройства:**

| Идентификатор | Как собирается |
|---|---|
| **Google Advertising ID (GAID)** | Через `AdvertisingIdClient.getAdvertisingIdInfo()` |
| **Huawei OAID** | Через HMS `AdvertisingIdClient` |
| **Android ID** | `android_id` в протобуфе (`proto/a.java`) |
| **Firebase App Instance ID** | Через `FirebaseAnalytics.getAppInstanceId()` |
| **MyTracker Instance ID** | UUID в SharedPreferences `mytracker_prefs` |
| **Limit Ad Tracking** | Флаг ограничения рекламного отслеживания |

**Данные сенсоров устройства (антифрод):**

| Сенсор | По умолчанию |
|---|---|
| Гироскоп | **Включён** |
| Датчик освещённости | **Включён** |
| Магнитометр | **Включён** |
| Барометр | **Включён** |
| Датчик приближения | **Включён** |

**Данные об устройстве:**
- Размер и разрешение экрана
- Тип тачскрина
- UI mode (телефон/планшет/TV/часы)
- **Детекция root** (проверка `/sbin/.magisk`, `/proc/mounts`)
- Список установленных приложений (`InstalledPackagesProvider.getInstalledPackages()`)

**Модули трекинга:**
- App Lifecycle — жизненный цикл приложения
- Time Spent — время, проведённое в приложении (отдельный сервер `ts.tracker-api.vk-analytics.ru`)
- User Lifecycle — жизненный цикл пользователя
- Antifraud — антифрод-проверки
- Purchase — отслеживание покупок
- Ads — рекламные метрики
- MiniApps — мини-приложения
- Remote Config — удалённая конфигурация
- Game — игровые метрики

**URL-адреса MyTracker:**

| URL | Назначение |
|---|---|
| `https://tracker-api.vk-analytics.ru/v3/` | Основной API (v3) |
| `https://ip4.tracker-api.vk-analytics.ru` | IPv4-only эндпоинт |
| `https://ts.tracker-api.vk-analytics.ru/mobile/v1` | Метрики времени |
| `https://mlapi.tracker-api.vk-analytics.ru` | ML-модели |
| `https://beta-ml.tracker-api.vk-analytics.ru` | Бета ML-модели |

---

### 7.2 OneLog — аналитика Одноклассников

**Эндпоинт**: `https://api.ok.ru/api/log/externalLog`

#### Формат запроса

```json
{
  "collector": "<категория_события>",
  "data": {
    "application": "ru.oneme.app:26.5.0:6558",
    "platform": "android:phone:14",
    "items": [
      {
        "timestamp": 1740000000000,
        "type": 0,
        "operation": "msg_send",
        "time": 150,
        "uid": "123456789",
        "network": "excellent",
        "count": 1,
        "groups": ["chat", "text"],
        "data": ["..."],
        "custom": {"key": "value"}
      }
    ]
  }
}
```

#### Что именно передаётся:

| Поле | Значение |
|---|---|
| `uid` | **ID пользователя** — передаётся в каждом событии |
| `operation` | Код операции (действие пользователя) |
| `network` | Качество сети: excellent/good/moderate/poor |
| `timestamp` | Точное время каждого действия |
| `time` | Длительность операции в миллисекундах |
| `application` | Полная идентификация приложения (имя, версия, билд) |
| `platform` | Тип устройства + версия Android |

**Известные коллекторы:**
- `ok.mobile.apps.video` — видеопроигрыватель: `vid` (ID видео), `vsid` (ID сессии), `cdn_host`, тип контента, autoplay, place, in_history
- `app.vchat.events.product` — события видеозвонков

**Буферизация:** до 500 событий накапливаются локально в `files/onelog/{collector}/`, затем отправляются пакетом с gzip-сжатием.

---

### 7.3 Calls Analytics SDK v0.1.4

**Эндпоинты:**
- `vchat.clientStats` → `api.ok.ru` — технические метрики звонков
- `log.externalLog` → `api.ok.ru` — продуктовая аналитика звонков

**Типы событий:**
- `SdkMetricStatEvent` — числовые метрики (имя, значение)
- `SdkIntervalStatEvent` — интервальные метрики
- `ProductAnalyticsEvent` — полная структура OneLog (uid, operation, time, network...)

**Метаданные:**
- `sdkType`: `"ANDROID"`
- `sdkVersion`: `"0.1.4"`
- Качество сеанса: jitter, packet loss, bitrate, codec

---

### 7.4 App Tracer — крашлитика и профилирование

**Эндпоинты:**

| URL | Метод | Назначение |
|---|---|---|
| `https://sdk-api.apptracer.ru/api/sample/initUpload` | POST | Инициализация загрузки профиля |
| `https://sdk-api.apptracer.ru/api/sample/upload` | POST | Загрузка бинарных семплов профилирования |
| `https://sdk-api.apptracer.ru/api/crash/trackSession` | POST | **Отслеживание краш-сессий** |
| `https://sdk-api.apptracer.ru/api/perf/upload` | POST | Загрузка метрик производительности |

**Собираемые данные (SystemState):**

| Поле | Описание |
|---|---|
| `versionName` + `versionCode` | Версия приложения |
| `packageName` | `ru.oneme.app` |
| `buildUuid` | UUID билда |
| `sessionUuid` | UUID текущей сессии |
| `device` | Модель устройства |
| **`deviceId`** | **Идентификатор устройства** |
| `vendor` | Производитель |
| `osVersion` | Версия Android |
| `isInBackground` | Приложение в фоне? |
| **`isRooted`** | **Устройство с root?** |
| `hostedLibrariesInfo` | Информация о подключённых библиотеках |

**Инициализаторы (загружаются при старте приложения):**
- `NativeBridgeInitializer` — нативный мост для перехвата крашей
- `CrashReportInitializer` — крашлитика
- `PerformanceMetricsInitializer` — метрики производительности
- `DiskUsageInitializer` — использование диска
- `HeapDumpInitializer` — дампы кучи памяти
- `LoggerInitializer` — логирование
- `TracerInitializer` — основной трейсинг

---

### 7.5 Firebase Analytics

Интеграция **минимальная** — используется исключительно для получения `FirebaseAnalytics.getAppInstanceId()`, который затем передаётся в **MyTracker** для кросс-идентификации. Firebase `AppInstanceId` кешируется в `mytracker_prefs`.

Полноценный Firebase Analytics SDK (события, screen views) **не обнаружен**.

---

### 7.6 Huawei HMS Analytics

Для устройств Huawei:
- `HMSBIInitializer` инициализирует BI-аналитику
- IMEI, UDID, серийный номер — **отключены** (`setEnableImei(false)`)
- `HaReporter` (WiseSecurity) отправляет события безопасности
- Маршрутизация для РФ: `metrics5.dt.dbankcloud.ru`

---

### 7.7 OpenTelemetry

Присутствуют модули `io.opentelemetry.api` и `io.opentelemetry.context`. Используются **только для внутреннего context propagation** (распределённый трейсинг между компонентами). Внешней отправки телеметрии **не обнаружено**.

---

## 8. Синхронизация контактов — скрытый сбор данных

### Механизм

Приложение использует полный **Android Sync Adapter** для двусторонней синхронизации контактов (`ContactsContract.RawContacts`).

### Что отправляется на сервер

| Данные | Protobuf-поле | Описание |
|---|---|---|
| **Номер телефона** | `Protos.Contact.serverPhone` (long) | **Сырой номер телефона без хеширования** |
| **Имя с устройства** | `Protos.ContactName.name` (тип DEVICE=2) | Имя из адресной книги Android |
| **Фамилия с устройства** | `Protos.ContactName.lastName` (тип DEVICE=2) | Фамилия из адресной книги |
| **Аватар с устройства** | `Protos.Contact.deviceAvatarUrl` | URL фото контакта |
| **Имя устройства** | `Protos.Contact.deviceName` | Название телефона |
| Пол | `Protos.Contact.gender` | MALE/FEMALE |
| Дата рождения | `Protos.Contact.birthday` | Строка |
| Страна | `Protos.Contact.country` | Строка |

### Критическая находка: NonContactsBuffer

В коде обнаружен компонент **`NonContactsBuffer`** (зарегистрирован как component #226) с конфигурационными параметрами:

| Параметр | Значение по умолчанию | Описание |
|---|---|---|
| `non-contact-sync-time` | 24 часа | Интервал синхронизации **не-контактов** |
| `non-contact-max-chunk-size` | — | Размер пакета для отправки |
| `non-contact-collection-interval` | — | Интервал сбора |

**Это означает**: приложение собирает и буферизует данные о **телефонных номерах, которые НЕ являются контактами пользователя** — потенциально для «рекомендаций» или отправки приглашений. Данные людей, никогда не давших согласие на обработку, передаются на серверы VK Group.

### Серверное управление

Параметры синхронизации управляются удалённо через PmsKey — сервер может в любой момент изменить частоту сбора и объём данных.

---

## 9. Фингерпринтинг устройства

### Собираемые идентификаторы (сводка)

| Идентификатор | Источник | Кем используется | Уникальность |
|---|---|---|---|
| Google Advertising ID (GAID) | Google Play Services | MyTracker → VK Analytics | Кросс-приложение |
| Huawei OAID | HMS | MyTracker → VK Analytics | Кросс-приложение |
| Android ID | System Settings | MyTracker | Уникален для приложения |
| Firebase App Instance ID | Firebase | MyTracker | Уникален для установки |
| MyTracker Instance ID | UUID (SharedPrefs) | MyTracker | Уникален для установки |
| deviceId | Нативный код | AppTracer, Calls SDK | Уникален для устройства |
| Huawei AAID | HMS OpenDevice | Huawei Push | Уникален для устройства |

### Дополнительный фингерпринтинг

- **Модель устройства** (`Build.MODEL`, `Build.MANUFACTURER`)
- **Версия Android** (`Build.VERSION.RELEASE`, `SDK_INT`)
- **Разрешение экрана** (`widthPixels × heightPixels`, DPI, density)
- **Локали** (язык, регион)
- **Тип тачскрина**, UI mode
- **Root-детекция** (проверка `/sbin/.magisk`, `/proc/mounts`)
- **Список установленных приложений** (`InstalledPackagesProvider.getInstalledPackages()`)
- **Показания сенсоров**: гироскоп, освещённость, магнитометр, барометр, приближение

---

## 10. Mobile ID — cleartext-трафик к операторам

### Конфигурация безопасности

Файл `network_security_config.xml` содержит **явное исключение** для 5 доменов мобильных операторов:

```xml
<domain-config cleartextTrafficPermitted="true">
    <domain includeSubdomains="false">mobileid.megafon.ru</domain>
    <domain includeSubdomains="false">idgw.mobileid.mts.ru</domain>
    <domain includeSubdomains="false">he-mc.tele2.ru</domain>
    <domain includeSubdomains="false">he-mc.t2.ru</domain>
    <domain includeSubdomains="true">beeline.ru</domain>
</domain-config>
```

### Суть проблемы

**Mobile ID** — протокол автоматической верификации пользователя по SIM-карте: оператор идентифицирует абонента по IP-адресу в мобильной сети. Для этого HTTP-запрос должен проходить через инфраструктуру оператора **без TLS**, чтобы оператор мог «видеть» запрос и подтвердить абонента.

### Риски

1. **Билайн** имеет `includeSubdomains="true"` — cleartext разрешён для **ВСЕХ** поддоменов `beeline.ru`, а не только для Mobile ID эндпоинта
2. Данные SIM-аутентификации передаются по **нешифрованному HTTP**
3. При подключении через Wi-Fi (не мобильную сеть) данные могут быть перехвачены любым участником сети

---

## 11. Доступ к другим приложениям

### Queries (видимость пакетов)

Приложение через `<queries>` в манифесте запрашивает информацию о:

| Приложение/Intent | Назначение |
|---|---|
| `yandexmaps://` | Яндекс.Карты |
| `yandexnavi://` | Яндекс.Навигатор |
| `dgis://` | 2GIS |
| `petalmaps://` | Huawei Petal Maps |
| CustomTabs Service | Браузеры с поддержкой Chrome Custom Tabs |
| `https://` browsable | Все браузеры |
| `com.huawei.hms`, `com.huawei.hwid`, `com.huawei.hff`, `com.huawei.works` | Huawei-сервисы |
| `com.hisilicon.android.hiRMService` | HiSilicon RM Service |
| `com.huawei.appmarket` | AppGallery |

### Implicit Intents

- `ACTION_SEND` / `ACTION_SEND_MULTIPLE` с `*/*` — отправка файлов в другие приложения
- `ACTION_VIEW` с `https://` — открытие ссылок
- Deep link scheme `max://max.ru/` — приём ссылок из других приложений
- `BOOT_COMPLETED` — автозапуск (получает broadcast)

### Регистрация контент-провайдеров

- `ru.oneme.app.provider` — FileProvider для обмена файлами
- `ru.oneme.app.notifications` — провайдер изображений уведомлений
- `ru.oneme.app.huawei.push.provider` — провайдер Huawei Push

---

## 12. Локальное хранение данных

### База данных Room (без шифрования)

`OneMeRoomDatabase` содержит таблицы, включая:

| Таблица | Содержимое |
|---|---|
| `fcm_notifications_analytics` | `push_id`, `chat_id`, `msg_id`, `suid`, `content_length`, `sent_time`, `push_type` |
| Чаты | История сообщений, метаданные |
| Контакты | Синхронизированные контакты |

**SQLCipher НЕ используется** — база данных хранится в открытом виде.

### SharedPreferences (без шифрования)

| Файл | Содержимое |
|---|---|
| `user.prefs` | Языковые настройки, пользовательские параметры |
| `mytracker_prefs` | Instance ID, Firebase App Instance ID, токены трекера |
| Системные prefs | `contactsLastSync`, `isFullContactsSyncCompleted`, push-конфигурация |

**EncryptedSharedPreferences НЕ используются** — токены и идентификаторы хранятся в открытом виде.

### Push-уведомления (PushInfo)

Содержимое push-уведомлений включает:
- `chatId` — ID чата
- `text` — **текст сообщения**
- `msgId` — ID сообщения
- `senderId` — ID отправителя
- `senderName` — имя отправителя
- `timestamp` — время
- `avatarUrl` — URL аватара
- `userId` — ID получателя

Логирование HMS SDK: `"receive a push token: " + packageName` — токены попадают в logcat.

---

## 13. Итоговая карта потоков данных

```
┌─────────────────┐
│   УСТРОЙСТВО    │
│   ПОЛЬЗОВАТЕЛЯ  │
└───────┬─────────┘
        │
        │ Сообщения, чаты, контакты (Protobuf/WebSocket)
        ├────────────────────────────────► api.oneme.ru (VK Group)
        │
        │ Аналитика OneLog + Calls Stats (JSON/HTTPS)
        ├────────────────────────────────► api.ok.ru (Одноклассники/VK)
        │
        │ MyTracker: ID, сенсоры, приложения, время (HTTPS)
        ├────────────────────────────────► tracker-api.vk-analytics.ru (VK Analytics)
        │
        │ Краши, перфоманс, дампы памяти (HTTPS)
        ├────────────────────────────────► sdk-api.apptracer.ru (VK)
        │
        │ Тайлы карт, геокодирование (HTTPS)
        ├────────────────────────────────► *.api-maps.yandex.ru (Яндекс)
        │
        │ Push-токены, аналитика HMS (HTTPS)
        ├────────────────────────────────► *.dbankcloud.ru (Huawei, серверы в РФ)
        │
        │ Mobile ID авторизация (HTTP CLEARTEXT!)
        ├────────────────────────────────► mobileid.megafon.ru
        ├────────────────────────────────► idgw.mobileid.mts.ru
        ├────────────────────────────────► he-mc.tele2.ru
        └────────────────────────────────► *.beeline.ru
```

---

## 14. Выводы и оценка рисков

### КРИТИЧЕСКИЕ УЯЗВИМОСТИ

| # | Проблема | Описание | Влияние |
|---|---|---|---|
| 1 | **Отсутствие E2E-шифрования** | Все сообщения доступны на серверах VK Group в открытом виде. Нет никаких механизмов end-to-end шифрования. | Полный доступ оператора серверов к переписке |
| 2 | **Сбор данных не-контактов** | `NonContactsBuffer` собирает номера телефонов людей, НЕ являющихся пользователями MAX и НЕ давших согласия. | Нарушение приватности третьих лиц |
| 3 | **7 систем аналитики** | Избыточный сбор данных через MyTracker, OneLog, CallsAnalytics, AppTracer, Firebase, HMS Analytics, OpenTelemetry. | Массовая телеметрия |

### ВЫСОКИЕ РИСКИ

| # | Проблема | Описание |
|---|---|---|
| 4 | **Cleartext-трафик Mobile ID** | HTTP-авторизация к 5 операторам связи, включая wildcard `*.beeline.ru` |
| 5 | **MyTracker: список приложений** | Сбор списка ВСЕХ установленных приложений на устройстве |
| 6 | **MyTracker: рекламные ID** | Сбор Google GAID + Huawei OAID для кросс-приложенной идентификации |
| 7 | **Телефоны без хеширования** | Номера телефонов контактов передаются на сервер как `long` без хеширования |

### СРЕДНИЕ РИСКИ

| # | Проблема | Описание |
|---|---|---|
| 8 | **Отсутствие SSL Pinning** | OkHttp `CertificatePinner` не обнаружен — уязвимость к MITM при компрометации CA |
| 9 | **Незашифрованная БД** | Room Database без SQLCipher — данные доступны на rooted устройствах |
| 10 | **Незашифрованные SharedPreferences** | Токены и идентификаторы в открытом виде |
| 11 | **5 датчиков для антифрода** | Гироскоп, освещённость, магнитометр, барометр, приближение — по умолчанию включены |
| 12 | **Root-детекция** | Проверка `/sbin/.magisk`, `/proc/mounts` — информация отправляется на серверы аналитики |

### ПОЛНЫЙ СПИСОК ДАННЫХ, ПОКИДАЮЩИХ УСТРОЙСТВО

| Категория | Данные | Получатель |
|---|---|---|
| **Сообщения** | Текст, вложения, реакции, пересылки | api.oneme.ru (VK) |
| **Контакты** | Имена, фамилии, телефоны, аватары | api.oneme.ru (VK) |
| **Не-контакты** | Номера телефонов из адресной книги | api.oneme.ru (VK) |
| **Геолокация** | GPS-координаты (если разрешено) | api.oneme.ru + Яндекс.Карты |
| **ID пользователя** | В каждом аналитическом событии | api.ok.ru + tracker-api.vk-analytics.ru |
| **Рекламный ID** | GAID / OAID | tracker-api.vk-analytics.ru |
| **Android ID** | Идентификатор устройства | tracker-api.vk-analytics.ru |
| **Список приложений** | Все установленные пакеты | tracker-api.vk-analytics.ru |
| **Сенсоры** | Данные 5 датчиков | tracker-api.vk-analytics.ru |
| **Время в приложении** | Метрики time spent | ts.tracker-api.vk-analytics.ru |
| **Модель устройства** | Производитель, модель, версия OS | Все 4 сервера аналитики |
| **Root-статус** | Наличие root / Magisk | tracker-api.vk-analytics.ru + sdk-api.apptracer.ru |
| **Качество сети** | Тип и качество соединения | api.ok.ru |
| **Действия в приложении** | Все операции с таймингами | api.ok.ru (OneLog) |
| **Push-токены** | FCM / HMS token | api.oneme.ru |
| **Метрики звонков** | Jitter, packet loss, codec, bitrate | api.ok.ru |
| **Краши и дампы** | Stack traces, heap dumps, профили | sdk-api.apptracer.ru |
| **Пол, возраст, день рождения** | Персональные данные профиля | api.oneme.ru + tracker-api.vk-analytics.ru |
| **Страна** | Геопривязка | api.oneme.ru |

---

### Заключение

Мессенджер **MAX** представляет собой ребрендированный TamTam/OneMe от VK Group с глубокой интеграцией в экосистему Одноклассников. Несмотря на позиционирование как «безопасный мессенджер», приложение:

1. **Не обеспечивает конфиденциальность сообщений** — отсутствие E2E означает, что VK Group имеет техническую возможность читать все сообщения
2. **Собирает избыточные данные** — 7 систем аналитики, включая список приложений, данные сенсоров, рекламные идентификаторы
3. **Передаёт данные третьих лиц** — номера телефонов из адресной книги, включая не-пользователей MAX
4. **Допускает незащищённый трафик** — cleartext HTTP для Mobile ID, включая wildcard для всех поддоменов beeline.ru
5. **Не защищает локальные данные** — база данных и preferences без шифрования

Весь пользовательский трафик проходит через серверы, контролируемые **VK Group** (Mail.ru Group), с аналитическими данными, дублируемыми на серверы Одноклассников.

---

*Аудит проведён путём статического анализа декомпилированного APK. Версия: 26.5.0, build 6558. Дата: 24 февраля 2026 г.*
