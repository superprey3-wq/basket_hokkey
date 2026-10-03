# GOOL SPORT 🏀🏒

Отдельный от футбольного GOOL сервис для баскетбола и хоккея.

v0.1:
- Flashscore — канонический LIVE список и счёт.
- 1xBet — LIVE тотал и движение рынка.
- Сопоставление Flashscore ↔ 1xBet и обязательная проверка счёта.
- Отдельные настройки Basketball / Hockey.
- Направленный STEAM: ТБ и ТМ.
- Защита после изменения счёта; в хоккее после гола новая рыночная эпоха.
- Один первый сигнал на матч без противоположных дублей.
- Shadow-журнал, расчёт результата, P/L и ROI.
- Второй Telegram-бот: /status, /report, /help.
- По умолчанию GOOL_SPORT_MODE=shadow.

Сервер:
1. Создать /home/container/sport.env по .env.example.
2. Токен второго Telegram-бота хранить только в env сервера.
3. Startup command:

python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/superprey3-wq/basket_hokkey/main/sport_autoupdate.py','/home/container/sport_autoupdate.py')" && exec python /home/container/sport_autoupdate.py

После запуска /status показывает покрытие источников, /report — результаты shadow.
