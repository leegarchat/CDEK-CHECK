#!/bin/bash

# Завершать работу при любой ошибке
set -e

echo "=== Старт настройки окружения ==="

# 1. Сохраняем имя реального пользователя, который запустил скрипт через sudo
REAL_USER=${SUDO_USER:-$(whoami)}
REAL_HOME=$(eval echo "~$REAL_USER")

TARGET_DIR="$REAL_HOME/Documents/Автозапросы"
LAUNCHER_PATH="$REAL_HOME/Desktop/Запуск_Автозапросы.command"

echo "Рабочий пользователь: $REAL_USER"
echo "Путь к директории: $TARGET_DIR"

# 2. Создание каталога (гарантируем, что создаем структуру)
mkdir -p "$TARGET_DIR"

# 3. Скачивание файлов
echo "Скачивание необходимых компонентов..."
curl -L -o "$TARGET_DIR/get-pip.py" "https://sourceforge.net/projects/cdek-my/files/get-pip.py/download"
curl -L -o "$TARGET_DIR/test_ui2.py" "https://sourceforge.net/projects/cdek-my/files/test_ui2.py/download"

# 4. Установка pip и зависимостей через sudo
echo "Установка pip..."
sudo python3 "$TARGET_DIR/get-pip.py"

echo "Установка библиотек..."
sudo python3 -m pip install PyQt5 requests Pillow pyzbar xlsxwriter openpyxl python-dateutil opencv-python

# 5. Возвращаем права на папку пользователю (исправление ошибки PermissionError)
echo "Исправление прав доступа на каталог..."
sudo chown -R "$REAL_USER:staff" "$TARGET_DIR"

# 6. Создание фонового лаунчера на Рабочем столе
echo "Создание ярлыка на Рабочем столе..."
cat << EOF > "$LAUNCHER_PATH"
#!/bin/bash

# Переход в рабочую директорию
cd "$TARGET_DIR"

# Изолированный запуск Python-скрипта (отвязываем от Терминала)
nohup python3 "$TARGET_DIR/test_ui2.py" > /dev/null 2>&1 &

# Небольшая пауза для инициализации PyQt5 окна
sleep 0.5

# Мягкое закрытие окна Терминала без уничтожения процесса Python
osascript -e 'tell application "Terminal" to close first window' & exit
EOF

# 7. Выдача прав на исполнение для .command файла и смена владельца ярлыка
chmod +x "$LAUNCHER_PATH"
sudo chown "$REAL_USER:staff" "$LAUNCHER_PATH"

echo "=== Настройка успешно завершена! ==="
echo "Исправленный ярлык для запуска создан на вашем Рабочем столе."
