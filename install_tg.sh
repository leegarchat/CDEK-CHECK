#!/bin/bash

echo "🚀 Начинаем установку Telegram Desktop (без sudo)..."

# 1. Определяем директории внутри домашней папки пользователя
APP_DIR="$HOME/.local/share/TelegramDesktop"
MENU_DIR="$HOME/.local/share/applications"

# Ищем Рабочий стол (учитываем русскую и английскую локали дистрибутивов)
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

# 3. Скачиваем официальный архив (прямая ссылка всегда отдает latest release)
TMP_ARCHIVE="/tmp/telegram_latest.tar.xz"
echo "📥 Скачиваем последнюю версию Linux x64..."
wget -qO "$TMP_ARCHIVE" "https://telegram.org/dl/desktop/linux"

# 4. Распаковываем файлы
echo "📦 Распаковываем в $APP_DIR..."
# Опция --strip-components=1 нужна, чтобы достать файлы из вложенной папки Telegram в архиве
tar -xf "$TMP_ARCHIVE" -C "$APP_DIR" --strip-components=1

# 5. Выдаем права на выполнение бинарникам
chmod +x "$APP_DIR/Telegram"
chmod +x "$APP_DIR/Updater" # Важно: именно этот файл отвечает за автообновление

# 6. Создаем ярлык (.desktop файл) для меню приложений
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

echo "✅ Готово! Telegram успешно установлен."
echo "Программа сама будет скачивать обновления и перезапускаться."
