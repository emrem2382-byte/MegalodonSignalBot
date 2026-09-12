# 🦈 Megalodon Signal Bot

Telegram бот: **@MegalodonSignalBot**

Сканира списък с акции, изчислява няколко технически индикатора и праща
**BUY сигнали** в Telegram чат. Работи безплатно на GitHub Actions по график
(cron) — не ти трябва сървър вкъщи.

⚠️ **Само сигнализира, не търгува.** Не се свързва с Revolut или друг брокер
и не изпраща реални поръчки. Не е финансов съвет.

## Как работи

1. GitHub Actions се стартира по cron (или ръчно) на всеки 30 мин през
   пазарните часове.
2. За всеки тикер от [`config/tickers.txt`](config/tickers.txt) сваля
   ценова история безплатно през `yfinance`.
3. Пуска всички индикатори от [`bot/indicators/`](bot/indicators) върху
   данните.
4. Ако достатъчно индикатори кажат BUY (виж `MIN_BUY_VOTES`), праща съобщение
   през @MegalodonSignalBot в Telegram.
5. Пази в `data/state.json` кои сигнали вече са пратени днес, за да не спамва.

## Setup

### 1. Направи Telegram бот
1. В Telegram отвори [@BotFather](https://t.me/BotFather) → `/newbot` →
   име `Megalodon Signals`, username `MegalodonSignalBot` → ще получиш
   **токен** (нещо като `123456:ABC...`).
2. Намери го през линка, който BotFather дава (`t.me/MegalodonSignalBot`),
   и му пиши нещо (напр. "здрасти"), за да го "отключиш".
3. Вземи **chat_id**: отвори в браузър (замени `<TOKEN>`):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   и намери числото в `"chat":{"id": ...}`.
   (За груповия чат: добави бота в групата и пиши там, после виж пак
   `getUpdates` — за групи id-то е отрицателно число.)

### 2. Качи проекта в GitHub
```bash
cd mega
git init
git add .
git commit -m "Initial commit: Megalodon Signal Bot"
git branch -M main
git remote add origin https://github.com/<твоя-user>/<repo-name>.git
git push -u origin main
```

### 3. Добави секретите в GitHub
В repo-то: **Settings → Secrets and variables → Actions → New repository secret**
- `TELEGRAM_BOT_TOKEN` — токенът от BotFather
- `TELEGRAM_CHAT_ID` — числото от стъпка 1.3

### 4. Активирай Actions
Отиди в таб **Actions** на repo-то → workflow-ът `Stock buy signals` ще се
стартира автоматично по график. Можеш и ръчно: **Run workflow** бутон.

## Локално тестване (по избор)
```bash
pip install -r requirements.txt
copy .env.example .env   # после попълни токена и chat_id в .env
python -m bot.main
```

## Добавяне на нови акции
Просто добави символ на нов ред в [`config/tickers.txt`](config/tickers.txt).
Revolut непрекъснато добавя нови листвания — списъкът се разширява ръчно,
без нужда от промени в кода.

## Проследяване на позиции (stop-loss / take-profit известия)
Ако решиш да влезеш в сделка, можеш да накараш бота да следи цената и да ти
пише в Telegram, ако падне под стоп-лос или стигне таргет.

Редактирай [`data/positions.json`](data/positions.json) на GitHub и добави
запис за тикера:
```json
{
  "VICI": {
    "entry_price": 24.83,
    "stop_loss": 24.66,
    "take_profit": 25.82
  }
}
```
- `entry_price` — по избор, само за да показва P&L% в известието
- `stop_loss` — по избор, известява ако дневният low падне под него
- `take_profit` — по избор, известява ако дневният high стигне до него

На всеки скан ботът проверява всички проследени позиции. Щом стоп или цел
бъде пробит, идва известие в Telegram и записът автоматично се маха от
файла (веднъж отработен, watch-ът е приключен). **Важно:** това е само
известие, не реална поръчка — ботът не се свързва с брокера ти.

## Добавяне на нови индикатори
Проектът е направен разширяем — когато прецениш:
1. Нов файл в `bot/indicators/`, напр. `bollinger.py`.
2. Наследи `Indicator` от `base.py`, имплементирай `evaluate(df)`.
3. Регистрирай инстанция в `bot/indicators/__init__.py` → `ALL_INDICATORS`.

Готово — engine-ът и Telegram съобщението автоматично го включват.

## Конфигурация (env / GitHub secrets)
| Променлива | По подразбиране | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | токен от BotFather |
| `TELEGRAM_CHAT_ID` | — | chat/канал където се пращат сигналите |
| `MIN_BUY_VOTES` | `3` | минимален брой индикатори, съгласни за BUY (и трябва да са повече от SELL гласовете) |
| `LOOKBACK_PERIOD` | `5y` | исторически прозорец за индикаторите (EMA200 + седмичен HTF в FIA се нуждаят от него) |
| `LOOKBACK_INTERVAL` | `1d` | интервал на свещите |
