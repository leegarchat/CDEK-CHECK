#!/bin/bash

# Завершать работу при любой ошибке
set -e

echo "=== Старт настройки окружения ==="

# 1. Определение путей
TARGET_DIR="$HOME/Documents/Автозапросы"
LAUNCHER_PATH="$HOME/Desktop/Запуск_Автозапросы.command"

# 2. Создание каталога
echo "Создание директории: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# 3. Скачивание файлов
echo "Скачивание необходимых компонентов..."
curl -L -o "get-pip.py" "https://sourceforge.net/projects/cdek-my/files/get-pip.py/download"
curl -L -o "test_ui2.py" "https://sourceforge.net/projects/cdek-my/files/test_ui2.py/download"

# 4. Установка pip и зависимостей
# Используем sudo, так какget-pip в глобальный python3 на macOS может потребовать прав администратора
echo "Установка pip..."
sudo python3 get-pip.py

echo "Установка библиотек..."
sudo python3 -m pip install PyQt5 requests Pillow pyzbar xlsxwriter openpyxl python-dateutil opencv-python

# 5. Создание лаунчера на Рабочем столе
echo "Создание ярлыка на Рабочем столе..."
cat << 'EOF' > "$LAUNCHER_PATH"
#!/bin/bash

# Переход в рабочую директорию
cd "$HOME/Documents/Автозапросы"

# Запуск скрипта в фоне с передачей полного пути
python3 "$HOME/Documents/Автозапросы/test_ui2.py" &

# Закрытие окна Терминала (убивает текущую сессию bash, окно закроется в зависимости от настроек Терминала)
osascript -e 'tell application "Terminal" to close first window' & exit
EOF

# 6. Выдача прав на исполнение для .command файла
chmod +x "$LAUNCHER_PATH"

echo "=== Настройка успешно завершена! ==="
echo "Ярлык для запуска создан на вашем Рабочем столе."
