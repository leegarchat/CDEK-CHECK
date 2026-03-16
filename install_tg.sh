#!/bin/bash

echo "🚀 Начинаем установку Telegram Desktop (без sudo)..."

# 1. Определяем директории внутри домашней папки пользователя
APP_DIR="$HOME/.local/share/TelegramDesktop"
MENU_DIR="$HOME/.local/share/applications"

# Ищем Рабочий стол
if [ -d "$HOME/Рабочий стол" ]; then
    DESKTOP_DIR="$HOME/Рабочий стол"
elif [ -d "$HOME/Desktop" ]; then
    DESKTOP_DIR="$HOME/Desktop"
else
    DESKTOP_DIR="$HOME"
fi

# 2. Создаем нужные директории, если их нет
mkdir -p "$APP_DIR"
mkdir -p "$MENU_DIR"

# 3. Скачиваем официальный архив
TMP_ARCHIVE="/tmp/telegram_latest.tar.xz"
echo "📥 Скачиваем последнюю версию Linux x64..."
wget -qO "$TMP_ARCHIVE" "https://telegram.org/dl/desktop/linux"

# 4. Распаковываем файлы
echo "📦 Распаковываем в $APP_DIR..."
tar -xf "$TMP_ARCHIVE" -C "$APP_DIR" --strip-components=1

# 5. Выдаем права на выполнение
chmod +x "$APP_DIR/Telegram"
chmod +x "$APP_DIR/Updater"

# 6. Создаем ярлык для меню приложений
DESKTOP_FILE="$MENU_DIR/telegram-custom.desktop"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Name=Telegram Desktop
Comment=Официальный клиент Telegram
Exec=$APP_DIR/Telegram -- %u
Icon=telegram
Terminal=false
StartupWMClass=TelegramDesktop
Type=Application
Categories=Chat;Network;InstantMessaging;Qt;
MimeType=x-scheme-handler/tg;
EOF

# 7. Копируем ярлык на Рабочий стол и делаем его исполняемым
echo "🖥️ Создаем ярлыки..."
cp "$DESKTOP_FILE" "$DESKTOP_DIR/"
chmod +x "$DESKTOP_DIR/telegram-custom.desktop"

# 8. Убираем за собой мусор
rm "$TMP_ARCHIVE"

echo "✅ Установка завершена!"
echo "🔌 Запускаем Telegram с вашими настройками прокси..."

# 9. Первый запуск с передачей прокси-ссылки (отвязываем от терминала)
PROXY_LINK="tg://proxy?server=77.90.63.2&port=443&secret=ee8dd986e1d1ea297bdb58db4b5e369af57777772e676f6f676c652e636f6d"

nohup "$APP_DIR/Telegram" -- "$PROXY_LINK" > /dev/null 2>&1 &

echo "🎉 Готово! Авторизуйтесь в открывшемся окне."
