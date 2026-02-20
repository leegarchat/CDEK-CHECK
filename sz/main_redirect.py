from PyQt5.QtWidgets import (QFileDialog, QGridLayout, 
                             QApplication, QMainWindow, QProgressBar,
                             QLabel, QPushButton, QVBoxLayout,
                            QProgressDialog, QMessageBox, QHBoxLayout, QCheckBox,
                            QLineEdit, QSizePolicy, QSpacerItem, QListWidgetItem, QDialog,
                             QWidget, QDesktopWidget, QStackedWidget, 
                             QRadioButton, QTextEdit, QListWidget, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
import subprocess
import concurrent.futures
import platform

import json, PIL
from datetime import datetime, timezone, timedelta
from PIL import Image
import requests, traceback, re, os, sys, time, random
import cv2
import numpy as np
import xlsxwriter
import openpyxl
from dateutil.relativedelta import relativedelta
from openpyxl.styles import Alignment, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64
from main_redirect_utils import *
from utils import *


CURRENT_VERSION = 18.012
EXPORT_THREAD = None
EXPORT_SZ_PRE_INFO = None
EXPORT_SZ_PRE_INFO_NEW = None
FINAL_MESSAGE_GO = None
DATA_USER = f"{WORK_DIR}/файлы_автозапросов/ключ/data_user.json"

if not os.path.exists(f"{WORK_DIR}/файлы_автозапросов"):
    os.makedirs(f"{WORK_DIR}/файлы_автозапросов")
if not os.path.exists(f"{WORK_DIR}/файлы_автозапросов/ключ"):
    os.makedirs(f"{WORK_DIR}/файлы_автозапросов/ключ")
if not os.path.exists(f"{WORK_DIR}/файлы_автозапросов/таблицы"):
    os.makedirs(f"{WORK_DIR}/файлы_автозапросов/таблицы")


def SendMassageBot(text: str):
    CHAT_ID = -5074833207 
    BOT_TOKEN = '7675219203:AAFmIZQWzUCsDA8RKgQBfGS7wptDhWz9LhU'
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",              # или "MarkdownV2" если нужно
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()               # выбросит исключение при HTTP>=400
        # data = r.json()
        # if not data.get("ok"):
        #     print("Ошибка в API:", data)
        # else:
        #     print("Отправлено, message_id =", data["result"]["message_id"])
    except requests.RequestException as e:
        pass
        # print("Ошибка запроса:", e)


def to_radians(degrees):
    return degrees * (3.141592653589793 / 180)

def sin(x):
    x = normalize_angle(x)
    x2 = x * x
    return x - (x2 * x)/6 + (x2 * x2 * x)/120 - (x2 * x2 * x2 * x)/5040

def cos(x):
    x = normalize_angle(x)
    x2 = x * x
    return 1 - x2/2 + (x2 * x2)/24 - (x2 * x2 * x2)/720

def normalize_angle(x):
    while x > 3.141592653589793:
        x -= 2 * 3.141592653589793
    while x < -3.141592653589793:
        x += 2 * 3.141592653589793
    return x

def random_offset_coords(lat, lon, min_distance=20, max_distance=100):
    distance = random.uniform(min_distance, max_distance)
    angle = random.uniform(0, 2 * 3.141592653589793)

    delta_lat = (distance * cos(angle)) / 111320
    delta_lon = (distance * sin(angle)) / (111320 * cos(to_radians(lat)))

    new_lat = round(lat + delta_lat, 6)
    new_lon = round(lon + delta_lon, 6)

    return [new_lat, new_lon]


def generate_precise_motion(prev_speed=None, prev_degrees=None):
    """
    Генерирует реалистичные значения движения:
    - Если переданы prev_speed и prev_degrees — вносит небольшую случайную погрешность.
    - Если не переданы — генерирует случайные, но правдоподобные значения.

    Возвращает:
        dict: {
            "speed": float (до 13 знаков),
            "degrees": float (до 17 знаков)
        }
    """

    def round_str(value, digits):
        # Округление с сохранением количества знаков (в виде float)
        return float(f"{value:.{digits}f}")

    if prev_speed is not None:
        # Плавное изменение скорости (±0.03 м/с), в пределах 0.01 – 0.39, избегая ровных чисел 0.0, 0.1 и т.п.
        delta_speed = random.uniform(-0.03, 0.03)
        new_speed = prev_speed + delta_speed
        new_speed = max(0.01, min(0.39, new_speed))

        # Если случайно получилось "круглое" значение типа 0.10, добавим чуть погрешности
        str_speed = f"{new_speed:.13f}"
        if str_speed.endswith('0000000000000') or str_speed[-5:] == '00000':
            new_speed += random.uniform(0.0000000000001, 0.000000000001)
    else:
        # Случайная скорость от 0.01 до 0.39, с дробными цифрами
        new_speed = random.uniform(0.01, 0.39)

    if prev_degrees is not None:
        # Плавное изменение направления (±5°), равномерно в обе стороны
        delta_deg = random.uniform(-5.0, 5.0)
        new_degrees = (prev_degrees + delta_deg) % 360.0
    else:
        new_degrees = random.uniform(0.0, 360.0)

    speed = round_str(new_speed, 13)
    degrees = float(f"{new_degrees:.17f}")  # 17 знаков для градусов

    return  [speed, degrees]



def close_tasks_final_D(TOKEN, TASK):
    url = 'https://courier-mobile.cdek.ru/mobile/couriertask/done'
    headers = {
        "x-device-id": "test",
        # "x-user-locale": "ru_RU",
        # "x-build-number": "1034",
        "x-version-number": "99.99.99",
        "x-auth-token": TOKEN,
        # "content-type": "application/json",
        # "content-length": 2,
        # "accept-encoding": "gzip",
        # "user-agent": "okhttp/4.9.2",
    }
    degreeses = generate_precise_motion()
    paylaod = {
        "courierTaskUuid": TASK['uuid'],
        "receiverFio": "",
        "courierLocation": {
                "requestTime": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                
                "detectStatus": "SUCCESS",
                "degrees": degreeses[1],
                "speed": degreeses[0]
            }
        }
    if TASK.get('taskType', '') == 'DELIVERY':
        paylaod['receiverFio'] = TASK.get('self_keys', {}).get('name', "")
    try: 
        coord = random_offset_coords(TASK['client']['coordinate']['latitude'], TASK['client']['coordinate']['longitude'])
        paylaod['courierLocation']['coordinate'] = {
                "latitude": coord[0],
                "longitude": coord[1],
            }
    except Exception as e:
        del paylaod['courierLocation']
        # print(TASK)
        print('error coordinate')
    
    # exit()
    data = return_post_response(url=url, headers=headers, payloads=paylaod)
    if data:
        if data.json()['responseCode'] == 'SUCCESS':
            return [True, 'Все супер']
        else:
            return [False, 'Не удалось закрыть задание']
        
    else:
        return [False, 'Не удалось закрыть задание']

def read_tasks(TOKEN, UUIDS):
    url = 'https://courier-mobile.cdek.ru/mobile/couriertask/read-list'
    headers = {
        "x-device-id": "test",
        # "x-user-locale": "ru_RU",
        # "x-build-number": "1034",
        "x-version-number": "99.99.99",
        "x-auth-token": TOKEN,
        # "content-type": "application/json",
        # "content-length": 2,
        # "accept-encoding": "gzip",
        # "user-agent": "okhttp/4.9.2",
    }
    paylaod = {
        "courierTaskUuids": UUIDS
            }
    
    data = return_post_response(url=url, headers=headers, payloads=paylaod)
    if data:
        return [True, 'Все супер']
    else:
        return [False, 'По какой то причине не удалось прочитать список заданий']

CLOSE_THREAD_TASK = None
class CloseThread_Tasks(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(int, int)
    stoping_signal = pyqtSignal()

    def __init__(self, tasks_array, bool_force):
        super().__init__()
        self.running = True
        self.tasks_array = tasks_array
        self.bool_force = bool_force

    def stop(self):
        self.running = False

    def run(self):
        try:

            uuids_for_check = []
            sorted_tasks = []

            for task in self.tasks_array:
                if not self.running: self.stoping_signal.emit(); return

                if task.get('courierTaskState') == 'ADDED':
                    uuid = task.get('uuid')
                    if uuid:
                        uuids_for_check.append(uuid)

                time_str = task.get('self_keys', {}).get('time')
                if time_str:
                    try:
                        task_time = datetime.strptime(time_str, "%H:%M:%S").time()
                        sorted_tasks.append((task_time, task))
                    except ValueError:
                        self.log_signal.emit(f"Ошибка разбора времени: {time_str}")

            self.log_signal.emit("Проверка задач перед закрытием...")
            result = read_tasks(check_login(GLOBAL_PASSWORD), uuids_for_check)
            if not result[0]:
                self.log_signal.emit(f"Ошибка при получении задач: {result[1]}")
                self.stoping_signal.emit()
                return

            # 🕐 Ожидание 1 минуты с возможностью прерывания
            if len(uuids_for_check) > 0:
                wait_seconds = 60
                start_time = time.time()
                self.log_signal.emit("Ожидание 1 минуты для обновления статуса задач (можно прервать)...")
                while time.time() - start_time < wait_seconds:
                    if not self.running:
                        self.log_signal.emit("Ожидание прервано пользователем.")
                        self.stoping_signal.emit()
                        return
                    # Можно показывать сколько осталось секунд, если хочешь
                    remaining = int(wait_seconds - (time.time() - start_time))
                    last_logged = -1
                    if remaining != last_logged:
                        last_logged = remaining
                        self.log_signal.emit(f"Осталось {remaining} сек...")
                    time.sleep(1)

            self.log_signal.emit("Начинаем поэтапное закрытие задач...")

            now = datetime.now().time()
            # print(sorted_tasks)
            sorted_tasks.sort(key=lambda x: x[0])
            # print(sorted_tasks)
            tick = 1
            for task_time, task in sorted_tasks:
                if not self.running: self.stoping_signal.emit(); return

                uuid = task.get('uuid')
                basis_number = task.get('numberBasis')
                if not uuid:
                    continue

                if self.bool_force:
                    pass
                else:
                    now = datetime.now().time()
                    if now < task_time:
                        wait_seconds = (
                            datetime.combine(datetime.today(), task_time) -
                            datetime.combine(datetime.today(), now)
                        ).total_seconds()
                        self.log_signal.emit(f"Ожидание до {task_time.strftime('%H:%M:%S')} ({int(wait_seconds)} сек)...")
                        self._wait_seconds(wait_seconds)

                # Закрытие задачи
                res = close_tasks_final_D(check_login(GLOBAL_PASSWORD), task)
                if res[0]:
                    self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Задание {basis_number} успешно закрыто.")
                else:
                    self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] Ошибка при закрытии {basis_number}: {res[1]}")
                self.progress_signal.emit(tick, len(sorted_tasks))
                tick += 1
            self.log_signal.emit("Обработка завершена.")
            self.finished_signal.emit()

        except Exception as e:
            self.log_signal.emit(f"Неожиданная ошибка в потоке: {e}")
            self.stoping_signal.emit()

    # ⏳ Умное ожидание с учётом stop()
    def _wait_seconds(self, total_seconds):
        start = time.time()
        while time.time() - start < total_seconds:
            if not self.running:
                self.stoping_signal.emit()
                raise Exception("Поток остановлен пользователем")
            time.sleep(0.3)


 
 
 
class ExportThread_Phone(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(int, int)
    stoping_signal = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        TOKEN = check_login(GLOBAL_PASSWORD)
        
        all_object = []
        mass_arr_to = [[
                        "Дата заказа","Номер","Статус","Номер места",
                        "Мест","Город отправитель","Отправитель",
                        "Город получатель","Получатель","Город плательщика",
                        "ЦФО выручки","Офис доставки","Договор","Номер ИМ",
                        "ШК место","Тип заказа","Местонахождение","Всего к оплате","Оплата при доставке","Вес к оплате","Прайс","релаьный срок",
                        "Город закрелпенного плательзика","Подразделение плательзика","Тариф","Отправитель","Получатель","Доп инфо","Заказ удален","ДДУ"]]
        for f in PHONE_DATA_JSON['Номера'].split('\n'):
            for current_date in [datetime.now(), datetime.now() - timedelta(days=8),
                        datetime.now() - timedelta(days=16),
                        datetime.now() - timedelta(days=24)]:
                date_minus_7_days = current_date - timedelta(days=7)
                formatted_date_minus_7_days2 = date_minus_7_days.strftime("%d.%m.%Y")
                formatted_current_date = current_date.strftime("%d.%m.%Y")
                if not self.running: self.stoping_signal.emit() ; return
                self.log_signal.emit(f"Выгрузка накладных по номеру: '{f}' с {formatted_date_minus_7_days2} по {formatted_current_date}")
                data = export_phone_order(f, TOKEN, formatted_date_minus_7_days2, formatted_current_date)
                if data:
                    self.log_signal.emit(f"Для телефона '{f}' найдено {len(data['items'])}")
                    for item_f in data['items']:
                        all_object.append(item_f)
                if not self.running: self.stoping_signal.emit() ; return
        self.log_signal.emit(f"Выгружжено {len(all_object)}")
        for item in all_object:
            try: orderDate = item['orderDate']
            except KeyError: orderDate = ''
            try: orderNumber = item['orderNumber']
            except KeyError: orderNumber = ''
            try: orderStatus = item['orderStatus']
            except KeyError: orderStatus = ''
            try: packageNumber = item['packageNumber']
            except KeyError: packageNumber = ''
            try: amountPackages = item['amountPackages']
            except KeyError: amountPackages = ''
            try: senderCity = item['senderCity']
            except KeyError: senderCity = ''
            try: senderName = item['senderName']
            except KeyError: senderName = ''
            try: receiverCity = item['receiverCity']
            except KeyError: receiverCity = ''
            try: receiverName = item['receiverName']
            except KeyError: receiverName = ''
            try: payerCity = item['payerCity']
            except KeyError: payerCity = ''
            try: responsibleForDeliveryOffice = item['responsibleForDeliveryOffice']
            except KeyError: responsibleForDeliveryOffice = ''
            try: contractNumber = item['contractNumber']
            except KeyError: contractNumber = ''
            try: numberDepOnlineStore = item['numberDepOnlineStore']
            except KeyError: numberDepOnlineStore = ''
            try: barCode = item['barCode']
            except KeyError: barCode = ''
            try: orderType = item['orderType']
            except KeyError: orderType = ''
            try: orderLocation = item['orderLocation']
            except KeyError: orderLocation = ''
            try: totalToPayer = item['totalToPayer']
            except KeyError: totalToPayer = ''
            try: deliveryPaySumma = item['deliveryPaySumma']
            except KeyError: deliveryPaySumma = ''
            try: paymentWeight = item['paymentWeight']
            except KeyError: paymentWeight = ''
            try: pricePeriod = item['pricePeriod']
            except KeyError: pricePeriod = ''
            try: realPeriod = item['realPeriod']
            except KeyError: realPeriod = ''
            try: payerContragent = item['payerContragent']
            except KeyError: payerContragent = ''
            try: payerCityCreation = item['payerCityCreation']
            except KeyError: payerCityCreation = ''
            try: payerSubdivision = item['payerSubdivision']
            except KeyError: payerSubdivision = ''
            try: orderService = item['orderService']
            except KeyError: orderService = ''
            try: senderFIO = item['senderFIO']
            except KeyError: senderFIO = ''
            try: receiverFIO = item['receiverFIO']
            except KeyError: receiverFIO = ''
            try: additionalServices = item['additionalServices']
            except KeyError: additionalServices = ''
            try: removedOrder = item['removedOrder']
            except KeyError: removedOrder = ''
            try: deliveryDateByService = item['deliveryDateByService']
            except KeyError: deliveryDateByService = ''
            mass_arr_to.append([orderDate, orderNumber, orderStatus, packageNumber, 
                       amountPackages, senderCity, senderName, 
                       receiverCity, receiverName, payerCity,
                       responsibleForDeliveryOffice, contractNumber, 
                       numberDepOnlineStore, barCode, orderType, orderLocation, 
                       totalToPayer, deliveryPaySumma, paymentWeight, 
                       pricePeriod, realPeriod,payerContragent, 
                       payerCityCreation, payerSubdivision, orderService,
                       senderFIO,receiverFIO,additionalServices,removedOrder,
                       deliveryDateByService])
        name_table = f"Накладные_по_телефону_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
        append_to_excel(mass_arr_to, f"{WORK_DIR}/файлы_автозапросов/таблицы/{name_table}", 'По телефону общее' , 40, 25, to_resize=37)
        global FILE_PATH_EXEL_PHONE
        FILE_PATH_EXEL_PHONE = name_table
        self.log_signal.emit(f"Сохранено в таблицу '{os.path.normpath(f'{WORK_DIR}/файлы_автозапросов/таблицы/{name_table}')}'")
        self.log_signal.emit(f"Завершенно!")
        self.progress_signal.emit(100, 100)
        self.finished_signal.emit()

    def stop(self):
        self.running = False
  
class ExportThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(int, int)
    stoping_signal = pyqtSignal()
    def __init__(self, data, export_tariff):
        super().__init__()
        self.data = data
        self.export_tariff = export_tariff
        self.running = True

    def run(self):
        try:
            """Основной метод обработки данных"""
            prices = ["17","7","25","10","5","28","30","2","14","15","3","27",
                    "6","9","26","13","24","4","12","18","8","29","19","11","23","16"]
            DATAUSER = load_user_data()
            HasGazZones = False
            for f in DATAUSER['Зоны']:
                if f.startswith('Газ'):
                    HasGazZones = True
                    break
            TOKEN_ = check_login(GLOBAL_PASSWORD)
            self.progress_signal.emit(10, 100)
            if HasGazZones:
                ofices_ug = "e8b21208-3d75-40b9-a929-70769e9a4ce5"
                ofices_sever = "09477afa-d168-4492-ad6a-2e39405eddd5"
                uuid = [ofices_ug, ofices_sever]
                self.log_signal.emit(f"Выгрузка накладных на Москву в движение...")
            else:
                uuid, names = GetUuidFromOffice(DATAUSER['Зоны'], TOKEN_)
                namesStr = '\n'.join(names)
                self.log_signal.emit(f"Выгрузка накладных на \n{namesStr}\n в движение...")
                if not uuid:
                    self.stoping_signal.emit(); return
            
            arr = []
            arr_number = []
            tikc = 0
            tick_bar = 1
            data = {
                'items': []
            }
            for delmod in ["8", "1", "3"]:
                try:
                    datadelmod = export_orders_info(TOKEN_, uuid, prices, deliveryMode=[delmod])
                    if 'items' in datadelmod:
                        data['items'] += datadelmod['items']
                except:
                    pass
            if not self.running: self.stoping_signal.emit() ; return
            if data:
                for f_2 in data['items']:
                    # if not self.export_tariff['экспресс_лайт'] and f_2['orderService'].lower().startswith("забор груза"):
                    #     continue
                    if not self.export_tariff['Забор_грузка'] and f_2['orderService'].lower().startswith("забор груза"):
                        continue
                    if not self.export_tariff['Возврат'] and f_2['orderService'].lower().startswith("возврат"):
                        continue
                    arr.append(f_2)
                    tikc += 1
                    arr_number.append(f_2['orderNumber'])
            else: self.log_signal.emit(f"Не получилось выгрузить часть накладных")
            self.log_signal.emit(f"Получено {tikc} значений")
            self.progress_signal.emit(30, 100)
            current_date = datetime.now()
            date_minus_7_days = current_date - timedelta(days=7)
            formatted_date_minus_7_days2 = date_minus_7_days.strftime("%d.%m.%Y")
            formatted_current_date = current_date.strftime("%d.%m.%Y")
            date_iterator = date_minus_7_days
            if HasGazZones:
                self.log_signal.emit(f"Выгрузка накладных на Москву и из Москвы в статусе созданно за период с {formatted_date_minus_7_days2} по {formatted_current_date}...")
            else:
                self.log_signal.emit(f"Выгрузка накладных из \n{namesStr}\n в статусе созданно за период с {formatted_date_minus_7_days2} по {formatted_current_date}...")
                
            TOKEN_ = check_login(GLOBAL_PASSWORD)
            arr_preorder = []
            arr_number_preorder = []
            while date_iterator <= current_date:
                formatted_date = date_iterator.strftime("%d.%m.%Y")
                self.log_signal.emit(f"Выгрузка накладных за {formatted_date}...")
                if not self.running: self.stoping_signal.emit() ; return
                tikc = 0
                if ACCES_NEW_ORDERS:
                    data = {
                        'items': []
                    }
                    for delmod in ["8", "1", "3"]:
                        try:
                            datadelmod = export_orders_info(TOKEN_, uuid, ["1"], date_from=formatted_date, date_to=formatted_date, deliveryMode=[delmod])
                            if 'items' in datadelmod:
                                data['items'] += datadelmod['items']
                        except:
                            pass
                    if data:
                        for f_2 in data['items']:
                            arr.append(f_2)
                            tikc += 1
                            arr_number.append(f_2['orderNumber'])
                    else: self.log_signal.emit(f"Не получилось выгрузить накладные")
                    self.log_signal.emit(f"Получено {tikc} значений на москву")
                # 468 Митино
                # 44 Москва
                data = {
                    'items': []
                }
                for delmod in ["6","1","2"]:
                    try:
                        if HasGazZones:
                            datadelmod = export_orders_info(TOKEN_, ['44'], ["1"], date_from=formatted_date, date_to=formatted_date, filter_city="senderCity", deliveryMode=[delmod])
                            if 'items' in datadelmod:
                                data['items'] += datadelmod['items']
                        else:
                            for ZonesIn in DATAUSER['Зоны']:
                                datadelmod = export_orders_info(TOKEN_, [VERSION_LOAD['OfficeCode'][ZonesIn]], ["1"], date_from=formatted_date, date_to=formatted_date, filter_city="senderCity", deliveryMode=[delmod])
                                if 'items' in datadelmod:
                                    data['items'] += datadelmod['items']
                    except:
                        pass
                tikc = 0
                if data:
                    for f_2 in data['items']:
                        if 'preorderNumber' in f_2:
                            if 'paymentWeight' in f_2:
                                if float(f_2['paymentWeight']) >= 30 and "orderService" in f_2:
                                    # if not self.export_tariff['экспресс_лайт'] and f_2['orderService'].lower().startswith("забор груза"):
                                    #     continue
                                    if not self.export_tariff['Забор_грузка'] and f_2['orderService'].lower().startswith("забор груза"):
                                        continue
                                    if not self.export_tariff['Возврат'] and f_2['orderService'].lower().startswith("возврат"):
                                        continue
                                    arr_preorder.append(f_2)
                                    tikc += 1
                                    arr_number_preorder.append(f_2['preorderNumber'])
                else: self.log_signal.emit(f"Не получилось выгрузить накладные")
                if HasGazZones:
                    self.log_signal.emit(f"Получено {tikc} значений из маосквы")
                else:
                    self.log_signal.emit(f"Получено {tikc} значений из \n{namesStr}")
                    
                date_iterator += timedelta(days=1)
            self.progress_signal.emit(35, 100)
            self.progress_signal.emit(40, 100)
            if not self.running: self.stoping_signal.emit() ; return
            if not arr_number: 
                self.log_signal.emit(f"Не получилось выгрузить...")
                self.stoping_signal.emit() ; return
            self.log_signal.emit("Присваивание макрозон")
            arr_number = process_large_array(arr_number)
            # print(arr_number)
            if arr_number_preorder:
                arr_number_preorder = process_large_array(arr_number_preorder)
            arr = get_zones(arr_number, arr, check_login(GLOBAL_PASSWORD),self)
            if arr_preorder and arr_number_preorder:
                arr_preorder = get_zones_preorder(arr_number_preorder, arr_preorder, check_login(GLOBAL_PASSWORD),self)
            if not self.running: self.stoping_signal.emit() ; return
            self.log_signal.emit(f"Итог общий до двери {len(arr) + len(arr_preorder)}")
            self.log_signal.emit("Фильтрация выбранных бригад и вес более 30кг")
            self.progress_signal.emit(50, 100)
            if HasGazZones:
                arr = filter_30kg_and_Gaz(self.data, arr, check_login(GLOBAL_PASSWORD), self.progress_signal)
                if arr_preorder:
                    arr_preorder = filter_30kg_and_Gaz(self.data, arr_preorder, check_login(GLOBAL_PASSWORD), self.progress_signal)
            else:
                arr = filter_30kg_and_Gaz([None], arr, check_login(GLOBAL_PASSWORD), self.progress_signal, OnlySize=True)
                if arr_preorder:
                    arr_preorder = filter_30kg_and_Gaz([None], arr_preorder, check_login(GLOBAL_PASSWORD), self.progress_signal, OnlySize=True)
            self.log_signal.emit(f"Осталось значений {len(arr) + len(arr_preorder)}")
            if len(arr) + len(arr_preorder) == 0:
                self.stoping_signal.emit() ; return
            self.log_signal.emit(f"Проверка на СЗ, время зависит от количетсво СЗ")
            self.progress_signal.emit(60, 100)	
            arr = get_sz_info_order(arr, check_login(GLOBAL_PASSWORD), self)
            if not self.running: self.stoping_signal.emit() ; return
            if arr_preorder:
                arr_preorder = get_sz_info_order(arr_preorder, check_login(GLOBAL_PASSWORD), self, preorder=True, start_progress=80, end_progress=90)
            if not self.running: self.stoping_signal.emit() ; return
            for gaz in self.data:
                tick = 0
                tick_sz = 0
                tick_prr_pol = 0
                tick_prr_otp = 0
                for key, item in arr.items():
                    if item['brigada'] == gaz:
                        tick += 1
                        if 'количество_сз' in item:
                            tick_sz += item['количество_сз']
                        if 'упоминаниеПРР_получатель' in item and len(item['упоминаниеПРР_получатель']) > 0:
                            tick_prr_pol += 1
                        if 'упоминаниеПРР_отправитель' in item and len(item['упоминаниеПРР_отправитель']) > 0:
                            tick_prr_otp += 1
                self.log_signal.emit(f"Для {gaz} - ({tick}), количество сз {tick_sz}, Упомниания ПРР отправителя {tick_prr_otp} и получателя {tick_prr_pol}")
            self.log_signal.emit(f"Добавление накладных в таблицу...")
            global FILE_PATH_EXEL
            name_sheet = add_table(arr, arr_preorder, self)
            FILE_PATH_EXEL = name_sheet[1]
            self.log_signal.emit(f"Сохранено в таблицу '{name_sheet[0]}'")
            self.log_signal.emit(f"Завершенно!")
            self.progress_signal.emit(100, 100)
            self.finished_signal.emit()
        except:
            self.stoping_signal.emit() ; return
    def stop(self):
        self.running = False

class EXPORTSZPREINFO(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    stoping_signal = pyqtSignal()
    progress_signal = pyqtSignal(int, int)
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.running = True

    def run(self):
        if self.data:
            self.log_signal.emit("Проверка накладных...")
            номера = self.data[1].split()
            len_befor = len(номера)
            data_load = load_user_data()
            if not (check_acces_user(data_load['Имя'], USERS_ACCES_PRIME) and 'Проверка' in data_load and data_load['Проверка']):
                # print(GAZES_ACCES)
                номера = filter_acces(check_login(GLOBAL_PASSWORD), номера, GAZES_ACCES, self)
                if not номера:
                    self.log_signal.emit("накладные не прошли проверку...")
                    self.stoping_signal.emit()
                    return
                else:
                    self.log_signal.emit(f"Из {len_befor} накладных, прошли проверку доступа {len(номера)}")
            тип_запроса = self.data[2]
            global SZ_DATA_JSON
            if тип_запроса == 'заказ':
                self.log_signal.emit("Получения информации по офисам и отделам...")
                new_mass_arr = {}
                TOKEN = check_login(GLOBAL_PASSWORD)
                for i, f in enumerate(номера, start=1):
                    data_user = load_user_data()
                    if not self.running: self.stoping_signal.emit() ; return
                    self.log_signal.emit(f"Получения информации по {f} ............")
                    full_info_orders_sz = get_pre_full_info(TOKEN, f, data_user, VERSION_LOAD['resend_sz'], SZ_DATA_JSON['Редирект_сз'], SZ_DATA_JSON['Не_отправлять_сз'])
                    if full_info_orders_sz['цфо_отделы']: self.log_signal.emit(f" * Есть отделы ЦФО {len(full_info_orders_sz['цфо_отделы']['items'])} шт..")
                    else: self.log_signal.emit(f" - Нет ЦФО ..")
                    new_mass_arr[f] = full_info_orders_sz
                    self.progress_signal.emit(i, len(номера))
                    self.log_signal.emit(f"------------------------")
            self.progress_signal.emit(len(номера), len(номера))
            SZ_DATA_JSON['список_накладны_офисов'] = new_mass_arr
        else:
            self.log_signal.emit(f"Отправка запросов..")
            numbers_access_fail = []
            numbers_access = []
            payload = {
                    "clientType": "RECEIVER",
                    "requestedPromiseFulfillmentDate": None,
                    "documentNumber": "",
                    "documentType": "ORDER",
                    "text": "Добрый день, Коллеги! Просьба согласовать и добавить ПРР у получателя!",
                    "toCityCode": "",
                    "toGroupId": "",
                    "toOfficeUuid":"",
                    "type": "MESSAGE",
                    "lang": "rus",
                    "token": check_login(GLOBAL_PASSWORD)
            }
            url = "https://gateway.cdek.ru/message-requests/web/message/create"
            for key, itme in SZ_DATA_JSON['список_накладны_офисов'].items():
                numbers_access.append(key)
            for key in SZ_DATA_JSON['Номера'].split('\n'):
                if key not in numbers_access:
                    numbers_access_fail.append()
            complited_orders = []
            SZ_DATA_JSON['Запрет_отправки'] = []
            SZ_DATA_JSON['Ошибка_отправки'] = []
            SZ_DATA_JSON['Не_найдены_отделы'] = []
            data_load = load_user_data()
            for i, order in enumerate(numbers_access, start=1):
                for office in SZ_DATA_JSON['Выбранные_офисы']:
                    if order in complited_orders: continue
                    if 'ЦФО' in office:
                        office_name = 'ЦФО'
                        groups = 'цфо_отделы'
                    if 'Текущий офис' in office:
                        office_name = 'Офис местонахождения'
                        groups = 'текущий_отделы'
                    if 'Офис отправителя' in office:
                        office_name = 'Офис отправителя'
                        groups = 'отправитель_отделы'
                    if 'Офис получателя' in office:
                        office_name = 'Офис получателя'
                        groups = 'получатель_отделы'
                    if 'Центральный Офис МСК' in office:
                        office_name = 'Центральный Офис МСК'
                        groups = 'ЦО_отделы'
                    if SZ_DATA_JSON['список_накладны_офисов'][order][groups]:
                        if order in complited_orders: continue
                        group_found = False
                        for acces_group in SZ_DATA_JSON['Выбранные_отделы']:
                            if order in complited_orders: continue
                            for group in SZ_DATA_JSON['список_накладны_офисов'][order][groups]['items']:
                                if order in complited_orders: continue
                                if acces_group == group['name']:
                                    if 'dont_send' in SZ_DATA_JSON['список_накладны_офисов'][order][f"{groups}_офис_данные"] and SZ_DATA_JSON['список_накладны_офисов'][order][f"{groups}_офис_данные"]['dont_send']:
                                        self.log_signal.emit(f"❌{order}: Запрет отправки")
                                        SZ_DATA_JSON['Запрет_отправки'].append(order)
                                        complited_orders.append(order)
                                        group_found = True
                                        continue
                                    exept_office = False
                                    if data_load['офисы_исключение']:
                                        for check_uuid_exept in data_load['офисы_исключение']:
                                            if check_uuid_exept['uuid'] == SZ_DATA_JSON['список_накладны_офисов'][order][f"{groups}_офис_данные"]['uuid']:
                                                if SZ_DATA_JSON['Не_отправлять_сз_для_исключений']:
                                                    self.log_signal.emit(f"❌{order}: Запрет отправки в офис и в ЦФО")
                                                    SZ_DATA_JSON['Запрет_отправки'].append(order)
                                                    complited_orders.append(order)
                                                    group_found = True
                                                    exept_office = True
                                                else:
                                                    self.log_signal.emit(f"❌{order}: Запрет отправки в офис")

                                                # SZ_DATA_JSON['Запрет_отправки'].append(order)
                                                # complited_orders.append(order)
                                                exept_office = True
                                                break
                                    if exept_office: continue
                                    payload['documentNumber'] = order
                                    payload['toCityCode'] = SZ_DATA_JSON['список_накладны_офисов'][order][f"{groups}_офис_данные"]['cityCode']
                                    payload['toGroupId'] = group['code']
                                    payload['text'] = SZ_DATA_JSON['текст_СЗ']
                                    payload['toOfficeUuid'] = SZ_DATA_JSON['список_накладны_офисов'][order][f"{groups}_офис_данные"]['uuid']
                                    # data_return = None
                                    data_return = return_post_response(url=url, headers=headers(check_login(GLOBAL_PASSWORD)), payloads=payload, status_code=True)
                                    self.progress_signal.emit(i, len(numbers_access))
                                    if data_return.status_code == 200:
                                        self.log_signal.emit(f"✅ {order} Отправлено в > {office_name} > в отдел > {group['name']}")
                                        complited_orders.append(order)
                                    else:
                                        self.log_signal.emit(f"❓{order} ошибка отправки")
                                        # if not data_return:
                                        # 	SZ_DATA_JSON['Ошибка_отправки'].append(order)
                                        # 	continue
                                        try:
                                            response_json = data_return.json()
                                            if 'alerts' in response_json:
                                                for msg in response_json['alerts']:
                                                    if "msg" in msg:
                                                        if msg['errorCode'] == 'MESSAGE_REQUEST_HAS_CLONE':
                                                            id_message = msg['params'][0]['value']
                                                            data_add_sz = AddTextToSz(check_login(GLOBAL_PASSWORD), id_message, SZ_DATA_JSON['текст_СЗ'])
                                                            # print(data_add_sz.text)
                                                            # print(SZ_DATA_JSON['текст_СЗ'], id_message)
                                                            if data_add_sz.status_code == 200:
                                                                self.log_signal.emit(f"✅ {order}: Добавлено в существующее СЗ")
                                                                complited_orders.append(order)
                                                            else:
                                                                self.log_signal.emit(f"❌ {order}: Ошибка при добавлении в существующее СЗ")
                                                                SZ_DATA_JSON['Ошибка_отправки'].append(order)
                                                                
                                                        else:
                                                            self.log_signal.emit(f"{msg['msg']}")
                                                            self.log_signal.emit(f"------------------")
                                                            SZ_DATA_JSON['Ошибка_отправки'].append(order)
                                            else:
                                                self.log_signal.emit(f"{response_json}")
                                        except ValueError:
                                            self.log_signal.emit(f"❌ Ошибка при обработке ответа: {data_return.text}")
                                            SZ_DATA_JSON['Ошибка_отправки'].append(order)
                                    group_found = True
                                    break 
                            if group_found: 
                                break
                        if not group_found:
                            self.log_signal.emit(f"❓{order}: Не найдено совпадений в списке отделов")
                            SZ_DATA_JSON['Не_найдены_отделы'].append(order)
                    else:
                        
                        self.log_signal.emit(f"❓{order}: Нет данных для офиса")
                        SZ_DATA_JSON['Не_найдены_отделы'].append(order)

                    
            
            self.progress_signal.emit(len(numbers_access), len(numbers_access))
        self.finished_signal.emit()  

    def stop(self):
        self.running = False

class EXPORTSZPREINFO_NEW(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    stoping_signal = pyqtSignal()
    progress_signal = pyqtSignal(int, int)
    def __init__(self, data):
        super().__init__()
        self.data = data
        if data:
            self.TOKEN = data[3]
            self.user_data = data[4]
        else:
            self.TOKEN = check_login(GLOBAL_PASSWORD)
            self.user_data = load_user_data()
        self.running = True

    def run(self):
        if self.data:
            self.log_signal.emit("Проверка накладных...")
            номера = self.data[1].split()
            len_befor = len(номера)
            data_load = load_user_data()
            if not (check_acces_user(data_load['Имя'], USERS_ACCES_PRIME) and 'Проверка' in data_load and data_load['Проверка']):
                номера = filter_acces(check_login(GLOBAL_PASSWORD), номера, GAZES_ACCES, self)
                if not номера:
                    self.log_signal.emit("накладные не прошли проверку...")
                    self.stoping_signal.emit()
                    return
                else:
                    self.log_signal.emit(f"Из {len_befor} накладных, прошли проверку доступа {len(номера)}")
            тип_запроса = self.data[2]
            global SZ_DATA_JSON
            if тип_запроса == 'заказ':
                self.log_signal.emit("Получения информации по офисам...")
                new_mass_arr = {}
                for i, f in enumerate(номера, start=1):
                    if not self.running: self.stoping_signal.emit() ; return
                    self.log_signal.emit(f"Обработка {f} ............")
                    # Для новой структуры без отделов, используем get_pre_full_info с new_sz=True
                    full_info_orders_sz = get_pre_full_info(self.TOKEN, f, self.user_data, {}, False, False, True)
                    new_mass_arr[f] = full_info_orders_sz
                    self.progress_signal.emit(i, len(номера))
                    self.log_signal.emit(f"------------------------")
            self.progress_signal.emit(len(номера), len(номера))
            SZ_DATA_JSON['список_накладны_офисов'] = new_mass_arr
        else:
            self.log_signal.emit(f"Отправка запросов..")
            printJson(SZ_DATA_JSON)
            # self.log_signal.emit(f"{SZ_DATA_JSON['selected_topics']}")
            payload = {
                    #"clientType": "RECEIVER",
                    #"requestedPromiseFulfillmentDate": None,
                    "documentNumber": "",
                    "documentType": "ORDER",
                    "text": "Добрый день, Коллеги! Просьба согласовать и добавить ПРР у получателя!",
                    "toCityCode": "",
                    "topicId": "",
                    "toOfficeUuid":"",
                    # "type": "MESSAGE",
                    "lang": "rus",
                    "token": check_login(GLOBAL_PASSWORD)
            }
            url = "https://gateway.cdek.ru/message-requests/web/message/create"
            numbers_access_fail = []
            numbers_access = []
            for key, itme in SZ_DATA_JSON['список_накладны_офисов'].items():
                numbers_access.append(key)
            for key in SZ_DATA_JSON['Номера'].split('\n'):
                if key not in numbers_access:
                    numbers_access_fail.append()
            tableOrders = getTableOrders(numbers_access, check_login(GLOBAL_PASSWORD))
            if not tableOrders:
                self.log_signal.emit(f"Ошибка получения данных")
                self.finished_signal.emit()
                return
            complited_orders = []
            SZ_DATA_JSON['Запрет_отправки'] = []
            SZ_DATA_JSON['Ошибка_отправки'] = []
            SZ_DATA_JSON['Не_найдены_отделы'] = []
            data_load = load_user_data()
            
            for i, order in enumerate(numbers_access, start=1):
                for office in SZ_DATA_JSON['Выбранные_офисы']:
                    if order in complited_orders: continue
                    if 'ЦФО' in office:
                        office_name = 'ЦФО'
                        office_name_in = 'цфо_отделы_офис_данные'
                    if 'Текущий офис' in office:
                        office_name = 'Офис местонахождения'
                        office_name_in = 'текущий_отделы_офис_данные'
                    if 'Офис отправителя' in office:
                        office_name = 'Офис отправителя'
                        office_name_in = 'отправитель_отделы_офис_данные'
                    if 'Офис получателя' in office:
                        office_name = 'Офис получателя'
                        office_name_in = 'получатель_отделы_офис_данные'
                    if 'Центральный Офис МСК' in office:
                        office_name_in = 'ЦО_отделы_офис_данные'
                        office_name = 'Центральный Офис МСК'
                    if SZ_DATA_JSON['список_накладны_офисов'][order][office_name_in]:
                        if order in complited_orders: continue
                        exept_office = False
                        if data_load['офисы_исключение']:
                            for check_uuid_exept in data_load['офисы_исключение']:
                                if check_uuid_exept['uuid'] == SZ_DATA_JSON['список_накладны_офисов'][order][office_name_in]['uuid']:
                                    if SZ_DATA_JSON['Не_отправлять_сз_для_исключений']:
                                        self.log_signal.emit(f"❌{order}: Запрет отправки в офис и в ЦФО")
                                        SZ_DATA_JSON['Запрет_отправки'].append(order)
                                        complited_orders.append(order)
                                        exept_office = True
                                    else:
                                        self.log_signal.emit(f"❌{order}: Запрет отправки в офис")
                                    exept_office = True
                                    break
                        if exept_office: continue
                        payload['documentNumber'] = order
                        payload['toCityCode'] = SZ_DATA_JSON['список_накладны_офисов'][order][f"{office_name_in}"]['cityCode']
                        # payload['toGroupId'] = group['code']
                        payload['text'] = SZ_DATA_JSON['текст_СЗ']
                        payload['toOfficeUuid'] = SZ_DATA_JSON['список_накладны_офисов'][order][f"{office_name_in}"]['uuid']
                        dogovor = ''
                        if len(SZ_DATA_JSON['selected_topics']) > 1:
                            for itemtable in tableOrders['items']:
                                if itemtable['orderNumber'] == order:
                                    dogovor = itemtable.get('contractNumber','')
                            if dogovor:
                                for itemselected in SZ_DATA_JSON['selected_topics']:
                                    if ' с договором' in itemselected['subgroup']:
                                        payload['topicId'] = itemselected['id']
                                        self.log_signal.emit(f"По накладной указан договор, отправка в подраздле:")
                                        self.log_signal.emit(f"{itemselected['subgroup']} > {itemselected['name']}")
                            else:
                                for itemselected in SZ_DATA_JSON['selected_topics']:
                                    if ' без договора' in itemselected['subgroup']:
                                        payload['topicId'] = itemselected['id']
                                        self.log_signal.emit(f"По накладной нет договора, отправка в подраздле:")
                                        self.log_signal.emit(f"{itemselected['subgroup']} > {itemselected['name']}")
                        else:
                            payload['topicId'] = SZ_DATA_JSON['selected_topics'][0]['id']
                            self.log_signal.emit(f"Выбран один варинат отправки в подраздле:")
                            self.log_signal.emit(f"{SZ_DATA_JSON['selected_topics'][0]['subgroup']} > {SZ_DATA_JSON['selected_topics'][0]['name']}")
                        data_return = return_post_response(url=url, headers=headers(check_login(GLOBAL_PASSWORD)), payloads=payload, status_code=True)
                        self.progress_signal.emit(i, len(numbers_access))
                        if data_return.status_code == 200:
                            self.log_signal.emit(f"✅ {order} Запрос отправлен")
                            complited_orders.append(order)
                        else:
                            self.log_signal.emit(f"❓{order} ошибка отправки")
                            try:
                                response_json = data_return.json()
                                if 'alerts' in response_json:
                                    for msg in response_json['alerts']:
                                        if "msg" in msg:
                                            if msg['errorCode'] == 'MESSAGE_REQUEST_HAS_CLONE':
                                                id_message = msg['params'][0]['value']
                                                data_add_sz = AddTextToSz(check_login(GLOBAL_PASSWORD), id_message, SZ_DATA_JSON['текст_СЗ'])
                                                if data_add_sz.status_code == 200:
                                                    self.log_signal.emit(f"✅ {order}: Добавлено в существующее СЗ")
                                                    complited_orders.append(order)
                                                else:
                                                    self.log_signal.emit(f"❌ {order}: Ошибка при добавлении в существующее СЗ")
                                                    SZ_DATA_JSON['Ошибка_отправки'].append(order)
                                                    
                                            else:
                                                self.log_signal.emit(f"{msg['msg']}")
                                                self.log_signal.emit(f"------------------")
                                                SZ_DATA_JSON['Ошибка_отправки'].append(order)
                                else:
                                    self.log_signal.emit(f"{response_json}")
                            except ValueError:
                                self.log_signal.emit(f"❌ Ошибка при обработке ответа: {data_return.text}")
                                SZ_DATA_JSON['Ошибка_отправки'].append(order)
                    else:
                        self.log_signal.emit(f"❓{order}: Нет данных для офиса")
                        SZ_DATA_JSON['Не_найдены_отделы'].append(order)
        self.finished_signal.emit()  

    def stop(self):
        self.running = False

def auth_menu():
    container = QWidget()
    layout = QVBoxLayout(container)
    

    if not USER_TOKEN:
        title = QLabel('Токена не активен')
    else:
        title = QLabel('Токен активен')
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    layout.addWidget(QLabel('Введите номера:'))
    global text_numbers
    text_numbers = QTextEdit()
    text_numbers.setAcceptRichText(False)
    text_numbers.setPlainText("Напиши тут токен который можно взять из консоли отладки в браузере по нажатию F12 ->Network, выбрать запрос при обновлении данных из ЭК5, вкладка headers, x-auth-token значение")
    layout.addWidget(text_numbers)
    grid_layout = QGridLayout()
    auth_b = QPushButton('Авторизация по Логину/Паролю')
    auth_b.setFixedSize(250, 50)
    grid_layout.addWidget(auth_b, 0, 0)
    send_token = QPushButton('Отправить токен')
    send_token.setFixedSize(250, 50)
    grid_layout.addWidget(send_token, 0, 1)
    back_b = QPushButton('Назад')
    back_b.setFixedSize(250, 50)
    grid_layout.addWidget(back_b, 1, 0)
    layout.addLayout(grid_layout)
    WINDOW.setCentralWidget(container)
    auth_b.clicked.connect(auth_menu_login_pass)
    send_token.clicked.connect(send_token_menu)
    back_b.clicked.connect(main_page)

def auth_menu_login_pass():
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
    title = QLabel("Введите логин и пароль")
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title, alignment=Qt.AlignCenter)
    login_label = QLabel("Логин:")
    layout.addWidget(login_label, alignment=Qt.AlignCenter)
    login_input = QLineEdit()
    layout.addWidget(login_input, alignment=Qt.AlignCenter)
    password_label = QLabel("Пароль:")
    layout.addWidget(password_label, alignment=Qt.AlignCenter)
    password_input = QLineEdit()
    password_input.setEchoMode(QLineEdit.Password)
    layout.addWidget(password_input, alignment=Qt.AlignCenter)
    button_layout = QHBoxLayout()
    login_button = QPushButton("Вход")
    login_button.setEnabled(False)  # Изначально неактивна
    button_layout.addWidget(login_button)
    back_button = QPushButton("Назад")
    button_layout.addWidget(back_button)
    
    layout.addLayout(button_layout)
    layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
    login_button.clicked.connect(lambda: auth_menu_with_login(login_input.text(), password_input.text()))
    back_button.clicked.connect(auth_menu)
    login_input.textChanged.connect(lambda: toggle_login_button(login_button, login_input, password_input))
    password_input.textChanged.connect(lambda: toggle_login_button(login_button, login_input, password_input))
    WINDOW.setCentralWidget(container)


def auth_menu_with_login(login, password, push_app=True, code_in_push=None, again_push_code=False):
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
    global TOKEN
    if code_in_push:
        TOKEN_PUSH = loginin_ek5(login, password, url="https://authnode.cdek.ru/api/exchangeCode", push_code=code_in_push, push=push_app)
        if TOKEN_PUSH[0] == 'Succes':
            save_login_to_disk(login, password, TOKEN_PUSH[1])
            main_page()
            return 0
        else:
            auth_menu_with_login(login, password, push_app=push_app, again_push_code=True)
            return 0
    
    button_layout = QHBoxLayout()
    if not again_push_code:
        TOKEN = loginin_ek5(login, password, push=push_app)
    if TOKEN[0] == 'Succes':
        save_login_to_disk(login, password, TOKEN[1])
        main_page()
        return 0
    if TOKEN[0] == 'WaitCode' and push_app:
        title = QLabel("Введите код, код направлен в приложение сдэк")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, alignment=Qt.AlignCenter)
        send_sms = QPushButton(f"Отправить по SMS на (60 сек.)")
        send_sms.setEnabled(False) 
        button_layout.addWidget(send_sms)
        countdown_timer = QTimer()
        countdown_seconds = 60 
        def update_button_text():
            nonlocal countdown_seconds
            if countdown_seconds > 0:
                send_sms.setText(f"Отправить по SMS ({countdown_seconds} сек.)")
                countdown_seconds -= 1
            else:
                countdown_timer.stop()
                send_sms.setText(f"Отправить по SMS на {TOKEN[1]['phone']}")
                send_sms.setEnabled(True) 

        countdown_timer.timeout.connect(update_button_text)
        countdown_timer.start(1000) 
        send_sms.clicked.connect(lambda: auth_menu_with_login(login, password, push_app=False))
    elif TOKEN[0] == 'WaitCode' and not push_app:
        title = QLabel(f"Введите код, код направлен в SMS на {TOKEN[1]['phone']}")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, alignment=Qt.AlignCenter)
    elif TOKEN[0] == 'UnccorectPass':
        title = QLabel("Что то не так, вернитесь и попробуйте снова, <br>возможно неверен пароль или логин, <br>или ваша учетная запись заблокированна")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, alignment=Qt.AlignCenter)
    if TOKEN[0] == 'WaitCode':
        title = QLabel("Ввод кода")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, alignment=Qt.AlignCenter)
        code_input = QLineEdit()
        layout.addWidget(code_input, alignment=Qt.AlignCenter)
        code_lable = QLabel("4-х значный код:")
        layout.addWidget(code_lable, alignment=Qt.AlignCenter)
        next_login = QPushButton('Вход')
        next_login.setEnabled(False)
        layout.addWidget(next_login)
        code_input.textChanged.connect(lambda: toggle_login_button(next_login, code_input, code_input))
        next_login.clicked.connect(lambda: auth_menu_with_login(login=login, password=password, push_app=push_app, code_in_push=code_input.text()))
    back_b = QPushButton("Назад")
    back_b.clicked.connect(auth_menu_login_pass)
    button_layout.addWidget(back_b)
    layout.addLayout(button_layout)
    WINDOW.setCentralWidget(container)


def toggle_login_button(button, login_input, password_input):
    if login_input.text() and password_input.text():
        button.setEnabled(True)
    else:
        button.setEnabled(False)


def send_token_menu():
    container = QWidget()
    layout = QVBoxLayout(container)
    global raw_text_token
    raw_text_token = text_numbers.toPlainText().replace(" ", "").replace("\n", "")
    title = QLabel(f"Проверка токена...")
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    WINDOW.setCentralWidget(container)
    progress_dialog = QProgressDialog("Проверка токена...", None, 0, 0, WINDOW)
    progress_dialog.setWindowTitle("Пожалуйста, подождите")
    progress_dialog.setWindowModality(Qt.WindowModal)
    progress_dialog.show()
    check_token(progress_dialog)
def check_token(progress_dialog):
    progress_dialog.close()
    
    result = check_status_token(raw_text_token) 
    if result:
        global USER_TOKEN
        USER_TOKEN = raw_text_token
        DATA_USER_ = load_user_data()
        DATA_USER_['TOKEN'] = USER_TOKEN
        data_info = get_full_info(USER_TOKEN)
        DATA_USER_['Имя'] = data_info['individual']['rus']
        with open(f"{WORK_DIR}/файлы_автозапросов/ключ/data_user.json", "w", encoding="utf-8") as file:
                    json.dump(DATA_USER_, file, ensure_ascii=False, indent=2)
        main_page()
    else:
        show_error_message()


def show_error_message():
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setText("Ошибка проверки токена")
    msg_box.setInformativeText("Попробуйте еще раз.")
    msg_box.setWindowTitle("Ошибка")
    msg_box.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
    ret = msg_box.exec_()
    
    if ret == QMessageBox.Retry:
        auth_menu()
    else:
        main_page()

FILE_PATH_EXEL = ""
def export_menu():
    container = QWidget()
    layout = QVBoxLayout(container)
    checkbox_layout = QVBoxLayout()
    checkbox_возврат = QCheckBox("Выгружать в том числе тариф 'возврат'")
    # checkbox_экспресс_лайт = QCheckBox("Выгружать в том числе тариф 'Экспресс-Лайт'")
    checkbox_Забор_грузка = QCheckBox("Выгружать в том числе тариф 'забор груза'")
    # checkbox_layout.addWidget(checkbox_экспресс_лайт, 0, Qt.AlignLeft)
    checkbox_layout.addWidget(checkbox_возврат, 0, Qt.AlignLeft)
    checkbox_layout.addWidget(checkbox_Забор_грузка, 0, Qt.AlignLeft)
    layout.addStretch()
    layout.addLayout(checkbox_layout)
    
    
    export_button = QPushButton("Выгрузить")
    layout.addWidget(export_button)
    back_button = QPushButton("Назад")
    layout.addWidget(back_button)
    
    export_button.clicked.connect(lambda: export_menu_confrim(
        {
            'Возврат': checkbox_возврат.isChecked(),
            'Забор_грузка': checkbox_Забор_грузка.isChecked()
            # 'экспресс_лайт': checkbox_экспресс_лайт.isChecked()
        }
    ))
    back_button.clicked.connect(main_page)
    WINDOW.setCentralWidget(container)





def export_menu_confrim(toggler_info):
    global EXPORT_THREAD
    global FILE_PATH_EXEL
    def update_progress(current, total):
        percentage = int((current / total) * 100)
        progress_bar.setValue(percentage)
        if percentage < 50:
            pass
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: black;  /* Текст черный на белом фоне */
                }
            """)
        else:
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: white;  /* Текст белый на фоне прогресса */
                }
            """)
        progress_bar.setFormat(f"{percentage}%")
    container = QWidget()
    layout = QVBoxLayout(container)
    log_window = QTextEdit()
    log_window.setReadOnly(True)
    layout.addWidget(log_window)
    back_button = QPushButton("Назад")
    back_button.setEnabled(False)
    layout.addWidget(back_button)
    stop_button = QPushButton("Остановить обработку")
    layout.addWidget(stop_button)
    WINDOW.setCentralWidget(container)
    data_to_process = gazes_currect(GAZES_ACCES)
    progress_bar = QProgressBar()
    progress_bar.setMinimum(0)
    progress_bar.setMaximum(100)
    progress_bar.setTextVisible(True) 
    progress_bar.setFormat("0% (0/0)")
    progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;  /* Центрируем текст */
                    color: black;  /* Текст черный на белом фоне */
                }
                QProgressBar::chunk {
                    background-color: #11543BFF;
                    border-radius: 5px;
                }
            """)
    layout.addWidget(progress_bar)
    EXPORT_THREAD = ExportThread(data=data_to_process, export_tariff=toggler_info)
    EXPORT_THREAD.log_signal.connect(log_window.append)  # Логи добавляются в текстовое поле
    EXPORT_THREAD.finished_signal.connect(lambda: on_finished(back_button, stop_button))
    EXPORT_THREAD.stoping_signal.connect(lambda: on_stop_signal(back_button, stop_button))
    EXPORT_THREAD.progress_signal.connect(update_progress)
    EXPORT_THREAD.start()
    def go_back():
        global EXPORT_THREAD
        EXPORT_THREAD = None
        main_page()
    def stop_processing():
        if EXPORT_THREAD is not None:
            EXPORT_THREAD.stop()
    def on_stop_signal(back_btn, stop_btn):
        back_btn.setEnabled(True)
        stop_btn.setEnabled(False)
        reload = QPushButton("Перевыгрузить")
        layout.addWidget(reload)
        reload.clicked.connect(lambda: export_menu())
        progress_bar.setValue(100)
        progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;  /* Центрируем текст */
                    color: white;  /* Текст черный на белом фоне */
                }
                QProgressBar::chunk {
                    background-color: #A40E2C;
                    border-radius: 5px;
                }
            """)
        progress_bar.setFormat(f"Прервано")
    def on_finished(back_btn, stop_btn):
        try:
            progress_bar.setValue(100)
        except Exception:
            pass
        back_btn.setEnabled(True)
        stop_btn.setEnabled(False)
        open_sheet = QPushButton("Открыть папку с таблицами")
        open_sheet.clicked.connect(open_folder_dialog)
        layout.addWidget(open_sheet)
        open_sheet_file = QPushButton("Открыть созданную таблицу")
        layout.addWidget(open_sheet_file)
        file_path = os.path.abspath(os.path.join(WORK_DIR, "файлы_автозапросов/таблицы", FILE_PATH_EXEL))
        open_sheet_file.clicked.connect(lambda: open_xlsx_file(file_path))
    back_button.clicked.connect(go_back)
    stop_button.clicked.connect(stop_processing)

def send_sz_menu_2():
    page = QWidget()
    layout = QVBoxLayout(page)

    layout.addWidget(QLabel('Введите номера:'))
    text_numbers = QTextEdit()
    text_numbers.setAcceptRichText(False)
    if SZ_DATA_JSON['Данные_текста_номеров']:
        text_numbers.setPlainText(SZ_DATA_JSON['Данные_текста_номеров'])
    btn_next = QPushButton('Далее')
    btn_back = QPushButton('Назад')
    btn_next.setEnabled(bool(text_numbers.toPlainText()))
    layout.addWidget(text_numbers)
    layout.addWidget(btn_next)
    layout.addWidget(btn_back)
    WINDOW.setCentralWidget(page)
    def filter_text(text):
        original_length = len(text)
        filtered_text = re.sub(r'[^0-9, \n]', '', text)  # Убираем все, кроме нужных символов
        removed_characters = original_length - len(filtered_text)
        return filtered_text, removed_characters
    def on_text_change():
        cursor = text_numbers.textCursor()
        cursor_position = cursor.position()
        text_numbers.textChanged.disconnect(on_text_change)
        filtered_text, removed_characters = filter_text(text_numbers.toPlainText())
        text_numbers.setPlainText(filtered_text)
        btn_next.setEnabled(bool(filtered_text))
        if removed_characters > 0:
            new_cursor_position = cursor_position - removed_characters
            new_cursor_position = max(0, new_cursor_position)
            cursor.setPosition(new_cursor_position)
        else:
            cursor.setPosition(cursor_position)
        text_numbers.setTextCursor(cursor)
        text_numbers.textChanged.connect(on_text_change)
    text_numbers.textChanged.connect(on_text_change)
    btn_next.clicked.connect(lambda: on_numbers_next(text_numbers))
    btn_back.clicked.connect(send_sz_menu_1)


def run_pre_info_sz(text_shablon=None, reload_=False):
    global EXPORT_SZ_PRE_INFO
    global SZ_DATA_JSON
    if text_shablon:
        SZ_DATA_JSON['текст_СЗ'] = text_shablon.toPlainText()
    # print(SZ_DATA_JSON['текст_СЗ'])
    container = QWidget()
    layout = QVBoxLayout(container)
    log_window = QTextEdit()
    if reload_:
        del SZ_DATA_JSON['Лог_вывод_предзагрузки']
        del SZ_DATA_JSON['Статус_предзагрузки']
    if 'Лог_вывод_предзагрузки' in SZ_DATA_JSON:
        log_window.setPlainText(SZ_DATA_JSON['Лог_вывод_предзагрузки'])
    log_window.setReadOnly(True)
    layout.addWidget(log_window)
    cont_b = QPushButton("Продолжить")
    cont_b.setEnabled(False)
    layout.addWidget(cont_b)
    stop_button = QPushButton("Остановить обработку")
    layout.addWidget(stop_button)
    back_button = QPushButton("Назад")
    back_button.setEnabled(False)
    layout.addWidget(back_button)
    WINDOW.setCentralWidget(container)
    def update_progress(current, total):
        percentage = int((current / total) * 100)
        progress_bar.setValue(percentage)
        if percentage < 50:
            pass
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: black;  /* Текст черный на белом фоне */
                }
            """)
        else:
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: white;  /* Текст белый на фоне прогресса */
                }
            """)
        progress_bar.setFormat(f"{percentage}% ({current}/{total})")
    if 'Лог_вывод_предзагрузки' not in SZ_DATA_JSON:
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)  
        progress_bar.setTextVisible(True) 
        progress_bar.setFormat("0% (0/0)") 
        progress_bar.setStyleSheet("""
                    QProgressBar {
                        text-align: center;  /* Центрируем текст */
                        color: black;  /* Текст черный на белом фоне */
                    }
                    QProgressBar::chunk {
                        background-color: #11543BFF;
                        border-radius: 5px;
                    }
                """)
        layout.addWidget(progress_bar)
        EXPORT_SZ_PRE_INFO = EXPORTSZPREINFO(data=[GAZES_ACCES, SZ_DATA_JSON['Номера'], SZ_DATA_JSON['ТипСЗ']])
        EXPORT_SZ_PRE_INFO.log_signal.connect(log_window.append)  # Логи добавляются в текстовое поле
        EXPORT_SZ_PRE_INFO.stoping_signal.connect(lambda: on_stoping(back_button, stop_button))
        EXPORT_SZ_PRE_INFO.finished_signal.connect(lambda: on_finished(cont_b, back_button, stop_button))
        EXPORT_SZ_PRE_INFO.progress_signal.connect(update_progress)
        EXPORT_SZ_PRE_INFO.start()
    def go_back():
        global EXPORT_SZ_PRE_INFO
        EXPORT_SZ_PRE_INFO = None
        create_template_page()
    def stop_processing():
        if EXPORT_SZ_PRE_INFO is not None:
            EXPORT_SZ_PRE_INFO.stop()
    def on_stoping(back_btn, stop_btn):
        back_btn.setEnabled(True)
        progress_bar.setStyleSheet("""
                    QProgressBar {
                        text-align: center;  /* Центрируем текст */
                        color: white;  /* Текст черный на белом фоне */
                    }
                    QProgressBar::chunk {
                        background-color: #721039;
                        border-radius: 5px;
                    }
                """)
        progress_bar.setValue(100)
        progress_bar.setFormat(f"Прервано")
        SZ_DATA_JSON['Статус_предзагрузки'] = False
        SZ_DATA_JSON['Лог_вывод_предзагрузки'] = log_window.toPlainText()
        stop_btn.setEnabled(False)
        reload = QPushButton("Перевыгрузить")
        layout.addWidget(reload)
        reload.clicked.connect(lambda: run_pre_info_sz(reload_=True))
    def on_finished(cont_btn, back_btn, stop_btn):
        reload = QPushButton("Перевыгрузить")
        layout.addWidget(reload)
        reload.clicked.connect(lambda: run_pre_info_sz(reload_=True))
        if not SZ_DATA_JSON['список_накладны_офисов']:
            log_window.append("Данные не выгружены")
            main_menu = QPushButton("В главное меню")
            layout.addWidget(main_menu)
            cont_btn.setEnabled(False)
            back_btn.setEnabled(False)
            stop_btn.setEnabled(False)
            main_menu.clicked.connect(main_page)
        else:
            цфо_ = 0
            текущий_отделы_ = 0
            отправитель_отделы_ = 0
            получатель_отделы_ = 0
            ЦО_отделы_ = 0
            values = []
            for key, item in SZ_DATA_JSON['список_накладны_офисов'].items():
                if item['цфо_отделы']:
                    цфо_ += 1
                if item['текущий_отделы']:
                    текущий_отделы_ += 1
                if item['отправитель_отделы']:
                    отправитель_отделы_ += 1
                if item['получатель_отделы']:
                    получатель_отделы_ += 1
                if item['ЦО_отделы']:
                    ЦО_отделы_ += 1

            for key, item in SZ_DATA_JSON['список_накладны_офисов'].items():
                if not any(value.startswith('ЦФО') for value in values) and item['цфо_отделы']:
                    values.append(f"ЦФО - (В {цфо_} шт накладных доступно)")
                if not any(value.startswith('Текущий офис') for value in values) and item['текущий_отделы']:
                    values.append(f"Текущий офис - (В {текущий_отделы_} шт накладных доступно)")
                if not any(value.startswith('Офис отправителя') for value in values) and item['отправитель_отделы']:
                    values.append(f"Офис отправителя - (В {отправитель_отделы_} шт накладных доступно)")
                if not any(value.startswith('Офис получателя') for value in values) and item['получатель_отделы']:
                    values.append(f"Офис получателя - (В {получатель_отделы_} шт накладных доступно)")
                if not any(value.startswith('Центральный Офис МСК') for value in values) and item['ЦО_отделы']:
                    values.append(f"Центральный Офис МСК - (В {ЦО_отделы_} шт накладных доступно)")
            if values:
                cont_btn.setEnabled(True)
            else:
                log_window.append("Что то выгрузилось не так, попробуйте еще раз...")
            back_btn.setEnabled(True)
            SZ_DATA_JSON['Статус_предзагрузки'] = True
            SZ_DATA_JSON['Лог_вывод_предзагрузки'] = log_window.toPlainText()
            stop_btn.setEnabled(False)

    if 'Лог_вывод_предзагрузки' in SZ_DATA_JSON:
        back_button.setEnabled(True)
        cont_b.setEnabled(SZ_DATA_JSON['Статус_предзагрузки'])
        stop_button.setEnabled(False)
    cont_b.clicked.connect(sz_send_menu_4)
    back_button.clicked.connect(go_back)
    stop_button.clicked.connect(stop_processing)



def run_pre_info_sz_new(text_shablon=None, reload_=False):
    global EXPORT_SZ_PRE_INFO_NEW
    global SZ_DATA_JSON
    if text_shablon:
        SZ_DATA_JSON['текст_СЗ'] = text_shablon.toPlainText()
    container = QWidget()
    layout = QVBoxLayout(container)
    log_window = QTextEdit()
    if reload_:
        del SZ_DATA_JSON['Лог_вывод_предзагрузки']
        del SZ_DATA_JSON['Статус_предзагрузки']
    if 'Лог_вывод_предзагрузки' in SZ_DATA_JSON:
        log_window.setPlainText(SZ_DATA_JSON['Лог_вывод_предзагрузки'])
    log_window.setReadOnly(True)
    layout.addWidget(log_window)
    cont_b = QPushButton("Продолжить")
    cont_b.setEnabled(False)
    layout.addWidget(cont_b)
    stop_button = QPushButton("Остановить обработку")
    layout.addWidget(stop_button)
    back_button = QPushButton("Назад")
    back_button.setEnabled(False)
    layout.addWidget(back_button)
    WINDOW.setCentralWidget(container)
    def update_progress(current, total):
        percentage = int((current / total) * 100)
        progress_bar.setValue(percentage)
        if percentage < 50:
            pass
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: black;  /* Текст черный на белом фоне */
                }
            """)
        else:
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: white;  /* Текст белый на фоне прогресса */
                }
            """)
        progress_bar.setFormat(f"{percentage}% ({current}/{total})")
    if 'Лог_вывод_предзагрузки' not in SZ_DATA_JSON:
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)  
        progress_bar.setTextVisible(True) 
        progress_bar.setFormat("0% (0/0)") 
        progress_bar.setStyleSheet("""
                    QProgressBar {
                        text-align: center;  /* Центрируем текст */
                        color: black;  /* Текст черный на белом фоне */
                    }
                    QProgressBar::chunk {
                        background-color: #11543BFF;
                        border-radius: 5px;
                    }
                """)
        layout.addWidget(progress_bar)
        TOKEN = check_login(GLOBAL_PASSWORD)
        data_user = load_user_data()
        EXPORT_SZ_PRE_INFO_NEW = EXPORTSZPREINFO_NEW(data=[GAZES_ACCES, SZ_DATA_JSON['Номера'], SZ_DATA_JSON['ТипСЗ'], TOKEN, data_user])
        EXPORT_SZ_PRE_INFO_NEW.log_signal.connect(log_window.append)
        EXPORT_SZ_PRE_INFO_NEW.stoping_signal.connect(lambda: on_stoping(back_button, stop_button))
        EXPORT_SZ_PRE_INFO_NEW.finished_signal.connect(lambda: on_finished(cont_b, back_button, stop_button))
        EXPORT_SZ_PRE_INFO_NEW.progress_signal.connect(update_progress)
        EXPORT_SZ_PRE_INFO_NEW.start()
    def go_back():
        global EXPORT_SZ_PRE_INFO_NEW
        EXPORT_SZ_PRE_INFO_NEW = None
        new_sz_topics_page(text_shablon.toPlainText() if text_shablon else "")  # Вернуться к выбору топиков
    def stop_processing():
        if EXPORT_SZ_PRE_INFO_NEW is not None:
            EXPORT_SZ_PRE_INFO_NEW.stop()
    def on_stoping(back_btn, stop_btn):
        back_btn.setEnabled(True)
        progress_bar.setStyleSheet("""
                    QProgressBar {
                        text-align: center;  /* Центрируем текст */
                        color: white;  /* Текст черный на белом фоне */
                    }
                    QProgressBar::chunk {
                        background-color: #721039;
                        border-radius: 5px;
                    }
                """)
        progress_bar.setValue(100)
        progress_bar.setFormat(f"Прервано")
        SZ_DATA_JSON['Статус_предзагрузки'] = False
        SZ_DATA_JSON['Лог_вывод_предзагрузки'] = log_window.toPlainText()
        stop_btn.setEnabled(False)
        reload = QPushButton("Перевыгрузить")
        layout.addWidget(reload)
        reload.clicked.connect(lambda: run_pre_info_sz_new(reload_=True))
    def on_finished(cont_btn, back_btn, stop_btn):
        reload = QPushButton("Перевыгрузить")
        layout.addWidget(reload)
        reload.clicked.connect(lambda: run_pre_info_sz_new(reload_=True))
        if not SZ_DATA_JSON['список_накладны_офисов']:
            log_window.append("Данные не выгружены")
            main_menu = QPushButton("В главное меню")
            layout.addWidget(main_menu)
            cont_btn.setEnabled(False)
            back_btn.setEnabled(False)
            stop_btn.setEnabled(False)
            main_menu.clicked.connect(main_page)
        else:
            if 'selected_topics' in SZ_DATA_JSON:
                # Для new_sz: офисы есть, отделов нет
                values = []
                цфо_count = sum(1 for item in SZ_DATA_JSON['список_накладны_офисов'].values() if item.get('цфо_отделы_офис_данные'))
                цо_count = sum(1 for item in SZ_DATA_JSON['список_накладны_офисов'].values() if item.get('ЦО_отделы_офис_данные'))
                if цфо_count > 0:
                    values.append(f"ЦФО - (В {цфо_count} шт накладных доступно)")
                if цо_count > 0:
                    values.append(f"Центральный Офис МСК - (В {цо_count} шт накладных доступно)")
                if values:
                    cont_btn.setEnabled(True)
                else:
                    log_window.append("Что то выгрузилось не так, попробуйте еще раз...")
            else:
                цфо_ = 0
                текущий_отделы_ = 0
                отправитель_отделы_ = 0
                получатель_отделы_ = 0
                ЦО_отделы_ = 0
                values = []
                for key, item in SZ_DATA_JSON['список_накладны_офисов'].items():
                    if item['цфо_отделы']:
                        цфо_ += 1
                    if item['текущий_отделы']:
                        текущий_отделы_ += 1
                    if item['отправитель_отделы']:
                        отправитель_отделы_ += 1
                    if item['получатель_отделы']:
                        получатель_отделы_ += 1
                    if item['ЦО_отделы']:
                        ЦО_отделы_ += 1

                for key, item in SZ_DATA_JSON['список_накладны_офисов'].items():
                    if not any(value.startswith('ЦФО') for value in values) and item['цфо_отделы']:
                        values.append(f"ЦФО - (В {цфо_} шт накладных доступно)")
                    if not any(value.startswith('Текущий офис') for value in values) and item['текущий_отделы']:
                        values.append(f"Текущий офис - (В {текущий_отделы_} шт накладных доступно)")
                    if not any(value.startswith('Офис отправителя') for value in values) and item['отправитель_отделы']:
                        values.append(f"Офис отправителя - (В {отправитель_отделы_} шт накладных доступно)")
                    if not any(value.startswith('Офис получателя') for value in values) and item['получатель_отделы']:
                        values.append(f"Офис получателя - (В {получатель_отделы_} шт накладных доступно)")
                    if not any(value.startswith('Центральный Офис МСК') for value in values) and item['ЦО_отделы']:
                        values.append(f"Центральный Офис МСК - (В {ЦО_отделы_} шт накладных доступно)")
                if values:
                    cont_btn.setEnabled(True)
                else:
                    log_window.append("Что то выгрузилось не так, попробуйте еще раз...")
            back_btn.setEnabled(True)
            SZ_DATA_JSON['Статус_предзагрузки'] = True
            SZ_DATA_JSON['Лог_вывод_предзагрузки'] = log_window.toPlainText()
            stop_btn.setEnabled(False)

    if 'Лог_вывод_предзагрузки' in SZ_DATA_JSON:
        back_button.setEnabled(True)
        cont_b.setEnabled(SZ_DATA_JSON['Статус_предзагрузки'])
        stop_button.setEnabled(False)
    cont_b.clicked.connect(sz_send_menu_4)
    back_button.clicked.connect(go_back)
    stop_button.clicked.connect(stop_processing)

def sz_send_menu_5():
    container = QWidget()
    layout = QVBoxLayout(container)

    # Заголовок
    title = QLabel("Нужно выбрать приоритетность, в которой будет отправлено СЗ в отделы.<br>"
                "Если есть отдел под выбором 1, то будет отправлено только в него.<br>"
                "Если отдела 1 нет, будет попытка отправить в отдел 2, если он есть, и так далее.")
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)

    # Список для выбора
    list_widget = QListWidget()
    list_widget.setSelectionMode(QListWidget.MultiSelection)

    # Подготовка данных
    values = {}
    sell_ = []
    for f in SZ_DATA_JSON['Выбранные_офисы']:
        if 'ЦФО' in f:
            sell_.append('цфо_отделы')
        if 'Текущий офис' in f:
            sell_.append('текущий_отделы')
        if 'Офис отправителя' in f:
            sell_.append('отправитель_отделы')
        if 'Офис получателя' in f:
            sell_.append('получатель_отделы')
        if 'Центральный Офис МСК' in f:
            sell_.append('ЦО_отделы')

    for sell___ in sell_:
        for key, item in SZ_DATA_JSON['список_накладны_офисов'].items():
            if not item[sell___]:
                continue
            for key_2 in item[sell___]['items']:
                if key_2['name'] not in values:
                    values[key_2['name']] = {
                        'Накладные': [key],
                        "количество": 1
                    }
                else:
                    values[key_2['name']]['Накладные'].append(key)
                    values[key_2['name']]['количество'] += 1

    sorted_values = dict(sorted(values.items(), key=lambda item: item[1]['количество'], reverse=True))
    sorted_values2 = []
    for key, item in sorted_values.items():
        sorted_values2.append(key)
    list_widget.addItems(list(sorted_values.keys()))
    layout.addWidget(list_widget)

    # Текст для отображения процентности
    availability_label = QLabel("Процент доступности: 0% (0/0)")
    layout.addWidget(availability_label)

    # Кнопки
    select_button = QPushButton("Запустить рассылку")
    select_button.setEnabled(False)  # Изначально неактивна
    layout.addWidget(select_button)

    back_button = QPushButton("Назад")
    layout.addWidget(back_button)

    # Глобальный словарь выбранных элементов и порядок
    global selected_items_dict
    selected_items_dict = {}

    def update_selection_3(list_widget):
        """Обновляет порядок выбора и отображение в списке."""
        global selected_items_dict
        selected_items_dict.clear()
        selected_items = list_widget.selectedItems()
        for index, item in enumerate(selected_items):
            original_text = item.text().split(') - ', 1)[-1]  # Получаем оригинальный текст без номера
            selected_items_dict[original_text] = index + 1
            item.setText(f"({index + 1}) - {original_text}")

        # Обновление всех элементов списка
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            original_text = item.text().split(') - ', 1)[-1]
            if original_text not in selected_items_dict:
                item.setText(original_text)

    def update_button_state():
        """Обновляет состояние кнопки выбора и процент доступности."""
        selected_items = list_widget.selectedItems()
        select_button.setEnabled(bool(selected_items))  # Активируем кнопку, если есть выбор

        # Вычисление процентности доступности (логика ИЛИ)
        if selected_items:
            selected_keys = [item.text().split(') - ', 1)[-1] for item in selected_items]  # Учитываем порядок
            # print(selected_keys) ['Прозвон заявок']
            total_keys = len(SZ_DATA_JSON['список_накладны_офисов'])
            matched_keys = 0
            matched_keys_2 = 0
            for key, item in SZ_DATA_JSON['список_накладны_офисов'].items():
                available = False
                available_2 = False
                for sell___ in sell_:
                    for selected_key in selected_keys:
                    # print(selected_key) Прозвон заявок
                    
                        # print(sell___)
                        if item[sell___]:
                            for key_2 in item[sell___]['items']:
                                # print(item[sell___], key_2['name'])
                                if key_2['name'] == selected_key:
                                    if sell___ == 'ЦО_отделы':
                                        available_2 = True
                                    available = True
                                    break
                        if available:
                            break
                        
                    if available:
                        break
                if available:
                    matched_keys += 1
                if available_2:
                    matched_keys_2 += 1

            # Процент доступности
            percentage = (matched_keys / total_keys) * 100 if total_keys > 0 else 0
            availability_label.setText(f"Процент доступности: {percentage:.2f}% ({matched_keys}/{total_keys}) [{matched_keys_2}/{total_keys} В центральный офис]")
        else:
            availability_label.setText("Процент доступности: 0%")

    # Связываем обработчики с изменением выбора
    list_widget.itemSelectionChanged.connect(lambda: [update_selection_3(list_widget), update_button_state()])


    select_button.clicked.connect(lambda: handle_selection_3(list_widget))
    back_button.clicked.connect(sz_send_menu_4)

    # Установка виджета
    WINDOW.setCentralWidget(container)
def handle_selection_3(list_widget):
        selected_items = list_widget.selectedItems()
        SZ_DATA_JSON['Выбранные_отделы'] = [item.text().split(') - ', 1)[-1] for item in selected_items]
        start_send_sz()

def start_send_sz():

    global EXPORT_SZ_PRE_INFO
    global SZ_DATA_JSON
    container = QWidget()
    layout = QVBoxLayout(container)
    log_window = QTextEdit()
    log_window.setReadOnly(True)
    layout.addWidget(log_window)
    cont_b = QPushButton("В главное меню")
    cont_b.setEnabled(False)
    layout.addWidget(cont_b)
    stop_button = QPushButton("Прервать рассылку")
    layout.addWidget(stop_button)
    def update_progress(current, total):
        percentage = int((current / total) * 100)
        progress_bar.setValue(percentage)
        if percentage < 50:
            pass
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: black;  /* Текст черный на белом фоне */
                }
            """)
        else:
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: white;  /* Текст белый на фоне прогресса */
                }
            """)
        progress_bar.setFormat(f"{percentage}% ({current}/{total})")
    WINDOW.setCentralWidget(container)
    progress_bar = QProgressBar()
    progress_bar.setMinimum(0)
    progress_bar.setMaximum(100)  # Прогресс будет в процентах
    progress_bar.setTextVisible(True)  # Показывать текст прогресса
    progress_bar.setFormat("0% (0/0)")  # Начальный текст внутри прогресс-бара
    progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;  /* Центрируем текст */
                    color: black;  /* Текст черный на белом фоне */
                }
                QProgressBar::chunk {
                    background-color: #11543BFF;
                    border-radius: 5px;
                }
            """)
    layout.addWidget(progress_bar)
    # Функции для работы с кнопками копирования
    def copy_to_clipboard(data):
        data_clip = '\n'.join(data)
        clipboard = QApplication.clipboard()  # Получаем доступ к буферу обмена
        clipboard.setText(data_clip)  # Копируем данные в буфер обмена
        msg_box = QMessageBox()
        msg_box.setText(f"Скопированы в буфер обмена.\n{data_clip}")
        msg_box.setWindowTitle("Уведомление")
        msg_box.exec_()

    def copy_restricted():
        if 'Запрет_отправки' in SZ_DATA_JSON:
            copy_to_clipboard(SZ_DATA_JSON['Запрет_отправки'])

    def copy_error():
        if 'Ошибка_отправки' in SZ_DATA_JSON:
            copy_to_clipboard(SZ_DATA_JSON['Ошибка_отправки'])

    def copy_not_found():
        if 'Не_найдены_отделы' in SZ_DATA_JSON:
            copy_to_clipboard(SZ_DATA_JSON['Не_найдены_отделы'])

    

    

    # Подключаем остальные обработчики
    if 'selected_topics' in SZ_DATA_JSON:
        FINAL_MESSAGE_GO = EXPORTSZPREINFO_NEW(data=[])
    else:
        FINAL_MESSAGE_GO = EXPORTSZPREINFO(data=[])
    FINAL_MESSAGE_GO.progress_signal.connect(update_progress)
    FINAL_MESSAGE_GO.log_signal.connect(log_window.append)  # Логи добавляются в текстовое поле
    FINAL_MESSAGE_GO.stoping_signal.connect(lambda: on_stoping())
    FINAL_MESSAGE_GO.finished_signal.connect(lambda: on_finished())
    FINAL_MESSAGE_GO.start()

    def stop_processing():
        if FINAL_MESSAGE_GO is not None:
            FINAL_MESSAGE_GO.stop()

    def on_stoping():
        stop_button.setEnabled(False)
        cont_b.setEnabled(True)

    def on_finished():
        stop_button.setEnabled(False)
        cont_b.setEnabled(True)
        # Кнопки для копирования
        copy_restricted_button = QPushButton(f"Скопировать запретные ({len(SZ_DATA_JSON.get('Запрет_отправки', []))})")
        copy_error_button = QPushButton(f"Скопировать ошибочные ({len(SZ_DATA_JSON.get('Ошибка_отправки', []))})")
        copy_not_found_button = QPushButton(f"Скопировать не найденные офисы ({len(SZ_DATA_JSON.get('Не_найдены_отделы', []))})")

        # Подключаем кнопки
        copy_restricted_button.clicked.connect(copy_restricted)
        copy_error_button.clicked.connect(copy_error)
        copy_not_found_button.clicked.connect(copy_not_found)

        # Добавляем кнопки в layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(copy_restricted_button)
        buttons_layout.addWidget(copy_error_button)
        buttons_layout.addWidget(copy_not_found_button)
        layout.addLayout(buttons_layout)
    cont_b.clicked.connect(main_page)
    stop_button.clicked.connect(stop_processing)

    WINDOW.setCentralWidget(container)



def sz_send_menu_4():
    container = QWidget()
    layout = QVBoxLayout(container)

    # Заголовок
    title = QLabel("Нужно выбрать приоритетность, в которой будет отправлено СЗ в офис.<br>"
                    "Если есть офис под выбором 1, то будет отправлено только в него.<br>"
                    "Если офиса 1 нет, будет попытка отправить в офис 2, если он есть, и так далее.")
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    list_widget = QListWidget()
    list_widget.setSelectionMode(QListWidget.MultiSelection)
    values = []
    if 'selected_topics' in SZ_DATA_JSON:
        # Для new_sz: офисы без отделов
        цфо_count = sum(1 for item in SZ_DATA_JSON['список_накладны_офисов'].values() if item.get('цфо_отделы_офис_данные'))
        цо_count = sum(1 for item in SZ_DATA_JSON['список_накладны_офисов'].values() if item.get('ЦО_отделы_офис_данные'))
        текущий_count = sum(1 for item in SZ_DATA_JSON['список_накладны_офисов'].values() if item.get('текущий_отделы_офис_данные'))
        отправитель_count = sum(1 for item in SZ_DATA_JSON['список_накладны_офисов'].values() if item.get('отправитель_отделы_офис_данные'))
        получатель_count = sum(1 for item in SZ_DATA_JSON['список_накладны_офисов'].values() if item.get('получатель_отделы_офис_данные'))
        if цфо_count > 0:
            values.append(f"ЦФО - (В {цфо_count} шт накладных доступно)")
        if цо_count > 0:
            values.append(f"Центральный Офис МСК - (В {цо_count} шт накладных доступно)")
        if текущий_count > 0:
            values.append(f"Текущий офис - (В {текущий_count} шт накладных доступно)")
        if отправитель_count > 0:
            values.append(f"Офис отправителя - (В {отправитель_count} шт накладных доступно)")
        if получатель_count > 0:
            values.append(f"Офис получателя - (В {получатель_count} шт накладных доступно)")
    else:
        цфо_ = 0
        текущий_отделы_ = 0
        отправитель_отделы_ = 0
        получатель_отделы_ = 0
        ЦО_отделы_ = 0
        for key, item in SZ_DATA_JSON['список_накладны_офисов'].items():
            if item['цфо_отделы']:
                цфо_ += 1
            if item['текущий_отделы']:
                текущий_отделы_ += 1
            if item['отправитель_отделы']:
                отправитель_отделы_ += 1
            if item['получатель_отделы']:
                получатель_отделы_ += 1
            if item['ЦО_отделы']:
                ЦО_отделы_ += 1

        for key, item in SZ_DATA_JSON['список_накладны_офисов'].items():
            if not any(value.startswith('ЦФО') for value in values) and item['цфо_отделы']:
                values.append(f"ЦФО - (В {цфо_} шт накладных доступно)")
            if not any(value.startswith('Текущий офис') for value in values) and item['текущий_отделы']:
                values.append(f"Текущий офис - (В {текущий_отделы_} шт накладных доступно)")
            if not any(value.startswith('Офис отправителя') for value in values) and item['отправитель_отделы']:
                values.append(f"Офис отправителя - (В {отправитель_отделы_} шт накладных доступно)")
            if not any(value.startswith('Офис получателя') for value in values) and item['получатель_отделы']:
                values.append(f"Офис получателя - (В {получатель_отделы_} шт накладных доступно)")
            if not any(value.startswith('Центральный Офис МСК') for value in values) and item['ЦО_отделы']:
                values.append(f"Центральный Офис МСК - (В {ЦО_отделы_} шт накладных доступно)")
    list_widget.addItems(values)
    layout.addWidget(list_widget)
    availability_label = QLabel("Процент доступности: 0%")
    layout.addWidget(availability_label)
    select_button = QPushButton("Выбрать")
    select_button.setEnabled(False)  # Изначально неактивна
    layout.addWidget(select_button)

    back_button = QPushButton("Назад")
    layout.addWidget(back_button)
    global selected_items_dict
    selected_items_dict = {}
    if 'Выбранные_офисы' in SZ_DATA_JSON:
        selected_offices = SZ_DATA_JSON['Выбранные_офисы']
        selected_items_dict.clear()  # Очищаем текущий словарь
        for index, office in enumerate(selected_offices):
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                original_text = item.text().split(') - ', 1)[-1]  # Убираем предыдущие метки
                if original_text == office:
                    selected_items_dict[original_text] = index + 1
                    item.setText(f"({index + 1}) - {original_text}")
                    item.setSelected(True)
                    break
    select_button.setEnabled(bool(list_widget.selectedItems()))
    def update_selection_2(list_widget):
        """Обновляет порядок выбора и отображение в списке."""
        global selected_items_dict
        selected_items_dict.clear()
        selected_items = list_widget.selectedItems()
        for index, item in enumerate(selected_items):
            original_text = item.text().split(') - ', 1)[-1]  # Получаем оригинальный текст без номера
            selected_items_dict[original_text] = index + 1
            item.setText(f"({index + 1}) - {original_text}")

        # Обновление всех элементов списка
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            original_text = item.text().split(') - ', 1)[-1]
            if original_text not in selected_items_dict:
                item.setText(original_text)

    def update_button_state():
        """Обновляет состояние кнопки выбора и процент доступности."""
        selected_items = list_widget.selectedItems()
        select_button.setEnabled(bool(selected_items)) 
        if selected_items:
            selected_keys = [item.text().split(') - ', 1)[-1] for item in selected_items]
            total_keys = len(SZ_DATA_JSON['список_накладны_офисов'])
            matched_keys = 0

            for key, item in SZ_DATA_JSON['список_накладны_офисов'].items():
                available = False
                for selected_key in selected_keys:
                    if 'selected_topics' in SZ_DATA_JSON:
                        # Для new_sz: проверка офисов
                        if selected_key.startswith("ЦФО") and item.get('цфо_отделы_офис_данные'):
                            available = True
                        elif selected_key.startswith("Центральный Офис МСК") and item.get('ЦО_отделы_офис_данные'):
                            available = True
                        elif selected_key.startswith("Текущий офис") and item.get('текущий_отделы_офис_данные'):
                            available = True
                        elif selected_key.startswith("Офис отправителя") and item.get('отправитель_отделы_офис_данные'):
                            available = True
                        elif selected_key.startswith("Офис получателя") and item.get('получатель_отделы_офис_данные'):
                            available = True
                    else:
                        # Старая логика
                        if selected_key.startswith("ЦФО") and item['цфо_отделы']:
                            available = True
                        elif selected_key.startswith("Текущий офис") and item['текущий_отделы']:
                            available = True
                        elif selected_key.startswith("Офис отправителя") and item['отправитель_отделы']:
                            available = True
                        elif selected_key.startswith("Офис получателя") and item['получатель_отделы']:
                            available = True
                        elif selected_key.startswith("Центральный Офис МСК") and item['ЦО_отделы']:
                            available = True
                    if available:
                        break
                if available:
                    matched_keys += 1
            percentage = (matched_keys / total_keys) * 100 if total_keys > 0 else 0
            availability_label.setText(f"Процент доступности: {percentage:.2f}% ({matched_keys}/{total_keys})")
        else:
            availability_label.setText("Процент доступности: 0%")
    list_widget.itemSelectionChanged.connect(lambda: [update_selection_2(list_widget), update_button_state()])
    select_button.clicked.connect(lambda: handle_selection_2(list_widget))
    back_button.clicked.connect(run_pre_info_sz)
    WINDOW.setCentralWidget(container)


def handle_selection_2(list_widget):
    selected_items = list_widget.selectedItems()
    SZ_DATA_JSON['Выбранные_офисы'] = [item.text().split(') - ', 1)[-1] for item in selected_items]
    if 'selected_topics' in SZ_DATA_JSON:
        SZ_DATA_JSON['Выбранные_отделы'] = []  # Для новой структуры отделы не нужны
        start_send_sz()  # Для новой структуры сразу отправляем
    else:
        sz_send_menu_5()



def on_numbers_next(text_numbers=None, numbers_=None):
    page = QWidget()
    layout = QVBoxLayout(page)
    global SZ_DATA_JSON
    if text_numbers:
        SZ_DATA_JSON['Данные_текста_номеров'] = text_numbers.toPlainText()
        SZ_DATA_JSON['Номера'] = process_numbers(SZ_DATA_JSON['Данные_текста_номеров'])
    if numbers_:
        SZ_DATA_JSON['Номера'] = process_numbers(numbers_)
    
    
    page = QWidget()
    layout = QVBoxLayout(page)

    layout.addWidget(QLabel('Проверьте введенные номера:'))
    text_confirm = QTextEdit()
    text_confirm.setReadOnly(True)
    text_confirm.setPlainText(SZ_DATA_JSON['Номера'])
    btn_confirm = QPushButton('Подтвердить')
    btn_back = QPushButton('Назад')

    layout.addWidget(text_confirm)
    layout.addWidget(btn_confirm)
    layout.addWidget(btn_back)
    WINDOW.setCentralWidget(page)
    btn_confirm.clicked.connect(create_template_page)
    btn_back.clicked.connect(send_sz_menu_2)

    return page


not_change_see = True

def create_template_page():
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel('Шаблон сообщения:'))
    text_template = QTextEdit()
    text_template.setAcceptRichText(False)
    default_text = "Добрый день, Коллеги!\nПросьба согласовать и добавить ПРР у получателя!"

    if 'текст_СЗ' in SZ_DATA_JSON:
        text_template.setPlainText(SZ_DATA_JSON['текст_СЗ'])
    else:
        text_template.setPlainText(default_text)
    button_container = QWidget()
    button_layout = QHBoxLayout(button_container)
    btn_save = QPushButton('Сохранить шаблон')
    btn_next = QPushButton('Подтвердить')
    btn_back = QPushButton('Назад')
    btn_show_all = QPushButton('Показать все')
    button_layout.addWidget(btn_save)
    saved_templates = load_user_data().get('Сохраненный_Шаблон', [])
    if len(saved_templates) > 5:
        button_layout.addWidget(btn_show_all)
    button_layout.addStretch()
    button_layout.addWidget(btn_next)
    button_layout.addWidget(btn_back)
    layout.addWidget(text_template)
    layout.addWidget(QLabel('Последние 5 сохраненных шаблонов:'))
    template_button_container = QWidget()
    template_button_layout = QHBoxLayout(template_button_container)
    template_button_layout.setSpacing(10)
    layout.addWidget(template_button_container)
    layout.addWidget(button_container)
    global not_change_see
    WINDOW.setCentralWidget(page)
    not_change_see = True
    def handle_save():
        save_shablon_text(text_template.toPlainText())
        global not_change_see
        btn_save.setText("Шаблон сохранен!")
        not_change_see = False
        btn_save.setEnabled(False)
        update_template_buttons()
    def show_all_templates():
        user_data = load_user_data()
        saved_templates = user_data.get('Сохраненный_Шаблон', [])

        dialog = QDialog(page)
        dialog.setWindowTitle('Все сохраненные шаблоны')
        dialog_layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        for index, template_text in enumerate(saved_templates):
            short_text = template_text[:120] + ('...' if len(template_text) > 120 else '')
            display_text = f"{index + 1}) {short_text}"
            
            item = QListWidgetItem(display_text)
            item.setToolTip(template_text)
            list_widget.addItem(item)
            if index != len(saved_templates) - 1:
                separator = QListWidgetItem()
                separator.setFlags(Qt.NoItemFlags) 
                separator.setText("")
                separator.setBackground(Qt.lightGray)
                separator.setSizeHint(QSize(0, 2))
                list_widget.addItem(separator)
        list_widget.itemClicked.connect(lambda item: select_template(list_widget.row(item) // 2, saved_templates, text_template, dialog))
        dialog_layout.addWidget(list_widget)
        dialog.setLayout(dialog_layout)
        dialog.resize(850, 500)
        dialog.exec_()
    def select_template(index, templates, editor, dialog):
        editor.setPlainText(templates[index])
        dialog.close()
    def update_template_buttons():
        for i in reversed(range(template_button_layout.count())):
            template_button_layout.itemAt(i).widget().deleteLater()
        user_data = load_user_data()
        saved_templates = user_data.get('Сохраненный_Шаблон', [])
        last_5_templates = saved_templates[-5:]
        for index, template_text in enumerate(last_5_templates):
            button = QPushButton(f'Шаблон {index + 1}')
            button.setToolTip(template_text)
            template_button_layout.addWidget(button)
            button.clicked.connect(lambda _, text=template_text: text_template.setPlainText(text))
    def update_save_button_state():
        global not_change_see
        if not_change_see:
            current_text = text_template.toPlainText()
            user_data = load_user_data()
            saved_templates = user_data.get('Сохраненный_Шаблон', [])

            if current_text in saved_templates or current_text == default_text:
                btn_save.setEnabled(False)
            else:
                btn_save.setEnabled(True)
    text_template.textChanged.connect(update_save_button_state)
    btn_save.clicked.connect(lambda: handle_save())
    btn_show_all.clicked.connect(show_all_templates)
    if VERSION_LOAD.get('new_sz', False):
        btn_next.clicked.connect(lambda: new_sz_topics_page(text_template.toPlainText()))
    else:
        btn_next.clicked.connect(lambda: run_pre_info_sz(text_template))
    btn_back.clicked.connect(lambda: on_numbers_next(numbers_=SZ_DATA_JSON['Данные_текста_номеров']))
    update_save_button_state()
    update_template_buttons()

    return page




class TopicsLoader(QThread):
    loaded_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def run(self):
        try:
            topics_data = GetNewTopic(check_login(GLOBAL_PASSWORD))
            self.loaded_signal.emit(topics_data)
        except Exception as e:
            self.error_signal.emit(str(e))


def new_sz_topics_page(text_template):
    global SZ_DATA_JSON
    if isinstance(text_template, str):
        SZ_DATA_JSON['текст_СЗ'] = text_template
    elif text_template is None:
        SZ_DATA_JSON['текст_СЗ'] = ""
    else:
        SZ_DATA_JSON['текст_СЗ'] = text_template.toPlainText()
    
    page = QWidget()
    layout = QVBoxLayout(page)
    
    loading_label = QLabel('загрузка топиков...')
    layout.addWidget(loading_label)
    
    search_label = QLabel('Это поиск по топикам. <b>WARNING:</b> По умолчанию в поиске заданы слова "Согласовать внесение"')
    search_label.setWordWrap(True)
    layout.addWidget(search_label)
    
    tree_widget = QTreeWidget()
    tree_widget.setHeaderHidden(True)
    tree_widget.setSelectionMode(QTreeWidget.NoSelection)  # Не позволяем выбирать родителя
    
    search_edit = QLineEdit()
    search_edit.setPlaceholderText('Поиск по топикам...')
    
    button_container = QWidget()
    button_layout = QHBoxLayout(button_container)
    btn_back = QPushButton('Назад')
    btn_next = QPushButton('Продолжить')
    btn_next.setEnabled(False)
    button_layout.addStretch()
    button_layout.addWidget(btn_next)
    button_layout.addWidget(btn_back)
    
    layout.addWidget(search_edit)
    layout.addWidget(tree_widget)
    layout.addWidget(button_container)
    
    selected_topics = []
    updating = False
    
    def build_tree(data):
        def add_items(parent_item, items, parents=[]):
            for item_data in items:
                child_item = QTreeWidgetItem(parent_item)
                child_item.setText(0, item_data['name'])
                current_parents = parents + [item_data['name']]
                if 'children' in item_data and item_data['children']:
                    add_items(child_item, item_data['children'], current_parents)
                else:
                    # Это лист, добавляем чекбокс
                    child_item.setFlags(child_item.flags() | Qt.ItemIsUserCheckable)
                    child_item.setCheckState(0, Qt.Unchecked)
                    # Сохраняем данные
                    child_item.setData(0, Qt.UserRole, item_data.get('id', ''))
                    child_item.setData(0, Qt.UserRole + 1, " > ".join(parents))  # полный путь родителей
                    child_item.setData(0, Qt.UserRole + 2, item_data['name'])
        
        tree_widget.clear()
        root_item = QTreeWidgetItem(tree_widget)
        root_item.setText(0, 'Топики')
        add_items(root_item, data.get('topics', []))
        tree_widget.expandAll()
    
    def filter_tree():
        search_text = search_edit.text().lower()
        def filter_items(item):
            item_text = item.text(0).lower()
            visible = search_text in item_text
            for i in range(item.childCount()):
                child_visible = filter_items(item.child(i))
                visible = visible or child_visible
            item.setHidden(not visible)
            return visible
        for i in range(tree_widget.topLevelItemCount()):
            filter_items(tree_widget.topLevelItem(i))
    
    def update_checkboxes():
        nonlocal updating
        updating = True
        def set_item_state(item):
            if item.childCount() == 0:  # только листья
                name = item.text(0)
                selected_names = [t['name'] for t in selected_topics]
                if not selected_topics or name in selected_names:
                    item.setDisabled(False)
                else:
                    item.setDisabled(True)
                    item.setCheckState(0, Qt.Unchecked)  # снять, если был выбран
            for i in range(item.childCount()):
                set_item_state(item.child(i))
        for i in range(tree_widget.topLevelItemCount()):
            set_item_state(tree_widget.topLevelItem(i))
        updating = False
    
    def on_item_changed(item, column):
        nonlocal updating
        if updating:
            return
        name = item.text(0)
        selected_names = [t['name'] for t in selected_topics]
        topic_data = {
            'id': item.data(0, Qt.UserRole),
            'subgroup': item.data(0, Qt.UserRole + 1),
            'name': item.text(0)
        }
        if item.checkState(0) == Qt.Checked:
            if not selected_topics or name in selected_names:
                if topic_data not in selected_topics:
                    selected_topics.append(topic_data)
            else:
                item.setCheckState(0, Qt.Unchecked)
        else:
            if topic_data in selected_topics:
                selected_topics.remove(topic_data)
        update_checkboxes()
        btn_next.setEnabled(len(selected_topics) > 0)
    
    def on_loaded(data):
        loading_label.hide()
        search_edit.show()
        tree_widget.show()
        build_tree(data)
        search_edit.setText("Согласовать внесение")
        filter_tree()
        update_checkboxes()
    
    def on_error(error):
        loading_label.setText(f'Ошибка загрузки: {error}')
    
    def on_back():
        loader.wait()
        create_template_page()
    
    def on_next():
        loader.wait()
        SZ_DATA_JSON['selected_topics'] = selected_topics
        SZ_DATA_JSON['ТипСЗ'] = 'заказ'  # Устанавливаем тип для новой структуры
        run_pre_info_sz_new(None)  # Текст уже сохранен
    
    loader = TopicsLoader()
    loader.loaded_signal.connect(on_loaded)
    loader.error_signal.connect(on_error)
    loader.start()
    
    search_edit.textChanged.connect(filter_tree)
    tree_widget.itemChanged.connect(on_item_changed)
    btn_back.clicked.connect(on_back)
    btn_next.clicked.connect(on_next)
    
    search_edit.hide()
    tree_widget.hide()
    
    WINDOW.setCentralWidget(page)
    return page




def process_numbers(text):
    text = text.replace(',', '\n').replace(' ', '\n')
    numbers = [line.strip() for line in text.split('\n')]
    numbers = [num for num in numbers if num]
    return '\n'.join(numbers)

all_offices = []

class OfficeLoader(QThread):
    loaded_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            global all_offices
            if all_offices:
                offices = all_offices
            else:
                offices = get_all_ofices()  # Получаем список офисов
            all_offices = offices
            self.loaded_signal.emit(offices)
        except Exception as e:
            self.error_signal.emit(str(e))


def send_sz_menu_1():
    global SZ_DATA_JSON
    SZ_DATA_JSON['ТипСЗ'] = None

    # Загрузка данных пользователя
    data_user = load_user_data()
    if 'офисы_исключение' not in data_user:
        data_user['офисы_исключение'] = []
        save_user_data(data_user)
    container = QWidget()
    layout = QVBoxLayout(container)

    layout.addWidget(QLabel('Преднастройка'))

    # Контейнер для чекбокса и текста
    redirect_toggle = QCheckBox()
    redirect_toggle.setChecked(True)
    redirect_toggle_label = QLabel('Использовать переадресацию из шаблонов комментариев')
    redirect_toggle_label.setWordWrap(True)

    redirect_layout = QHBoxLayout()
    redirect_layout.addWidget(redirect_toggle, 0, Qt.AlignLeft)
    redirect_layout.addWidget(redirect_toggle_label, 1)

    dont_send_toggle = QCheckBox()
    dont_send_toggle_label = QLabel('Не отправлять СЗ где комментарий:\n"Если вы пишете нам как в ЦФО и есть ЗМ, то проверьте, если ЗМ с СК - пишите на почту assist@cdek.ru; если ЗМ с Московского Центрального офиса - пишите на почту support_msk@cdek.ru; если клиент Cainiao пишите на почту cainiao@cdek.ru"')
    dont_send_toggle_label.setWordWrap(True)

    dont_send_layout = QHBoxLayout()
    dont_send_layout.addWidget(dont_send_toggle, 0, Qt.AlignLeft)
    dont_send_layout.addWidget(dont_send_toggle_label, 1)

    redirect_toggle_dontr_send = QCheckBox()
    redirect_toggle_dontr_send_label = QLabel('Не отправлять СЗ в центральный офис, если стоит запрет на ЦФО из списка ниже и выбран центральный офис как дополнительный офис отправки сз.')
    redirect_toggle_dontr_send_label.setWordWrap(True)

    redirect_toggle_dontr_send_layout = QHBoxLayout()
    redirect_toggle_dontr_send_layout.addWidget(redirect_toggle_dontr_send, 0, Qt.AlignLeft)
    redirect_toggle_dontr_send_layout.addWidget(redirect_toggle_dontr_send_label, 1)

    office_search = QLineEdit()
    office_search.setPlaceholderText('Поиск офисов исключений...')

    office_list = QListWidget()
    for office in data_user['офисы_исключение']:
        item = QListWidgetItem(office['имя'])
        item.setData(Qt.UserRole, office['uuid'])
        office_list.addItem(item)

    def filter_offices():
        search_text = office_search.text().lower()
        office_list.clear()
        for office in data_user['офисы_исключение']:
            if search_text in office['имя'].lower():
                item = QListWidgetItem(office['имя'])
                item.setData(Qt.UserRole, office['uuid'])
                office_list.addItem(item)

    office_search.textChanged.connect(filter_offices)

    add_office_button = QPushButton('Добавить офисы исключения')
    def reload_offices(dialog):
        global all_offices
        all_offices = []  # Очистим текущие данные
        dialog.accept()  # Закрыть текущее окно

        # Создать новое окно с обновленными данными
        add_office_dialog()
    def add_office_dialog():
        global all_offices
        dialog = QDialog()
        dialog.setWindowTitle('Добавление офисов исключений')
        dialog.resize(500, 400)
        dialog_layout = QVBoxLayout(dialog)

        loading_label = QLabel('Загрузка списка офисов...')
        dialog_layout.addWidget(loading_label)
        QApplication.processEvents()

        def on_loaded_offices(offices):
            global all_offices
            all_offices = offices
            loading_label.hide()
            update_office_list()

        def on_error_loading(error):
            loading_label.setText(f"Ошибка загрузки: {error}")

        loader = OfficeLoader()
        loader.loaded_signal.connect(on_loaded_offices)
        loader.error_signal.connect(on_error_loading)
        loader.start()

        def update_office_list():
            global all_offices
            office_search_input = QLineEdit()
            office_search_input.setPlaceholderText("Поиск...")
            office_list_widget = QListWidget()

            for office in all_offices:
                item = QListWidgetItem(office['name'])
                item.setData(Qt.UserRole, office['id'])
                office_list_widget.addItem(item)

            def filter_available_offices():
                search_text = office_search_input.text().lower()
                office_list_widget.clear()
                for office in all_offices:
                    if search_text in office['name'].lower():
                        item = QListWidgetItem(office['name'])
                        item.setData(Qt.UserRole, office['id'])
                        office_list_widget.addItem(item)

            office_search_input.textChanged.connect(filter_available_offices)

            reload_button = QPushButton('Перевыгрузить офисы')
            reload_button.clicked.connect(lambda: reload_offices(dialog))

            dialog_layout.addWidget(office_search_input)
            dialog_layout.addWidget(office_list_widget)
            

            confirm_button = QPushButton('Добавить в исключения')
            dialog_layout.addWidget(confirm_button)
            dialog_layout.addWidget(reload_button)

            def add_selected_offices():
                selected_items = office_list_widget.selectedItems()
                for item in selected_items:
                    data_user['офисы_исключение'].append({'имя': item.text(), 'uuid': item.data(Qt.UserRole)})
                save_user_data(data_user)
                filter_offices()
                dialog.accept()

            confirm_button.clicked.connect(add_selected_offices)

        dialog.exec_()

    add_office_button.clicked.connect(add_office_dialog)
    # Кнопка для удаления исключений
    remove_office_button = QPushButton('Удалить исключение')
    remove_office_button.setEnabled(False)  # Кнопка неактивна изначально
    def on_office_selected():
        # Активировать кнопку удаления, если элемент выбран
        selected_items = office_list.selectedItems()
        remove_office_button.setEnabled(len(selected_items) > 0)

    def remove_office():
        selected_items = office_list.selectedItems()
        if selected_items:
            for item in selected_items:
                office_uuid = item.data(Qt.UserRole)
                data_user['офисы_исключение'] = [office for office in data_user['офисы_исключение'] if office['uuid'] != office_uuid]
            save_user_data(data_user)
            filter_offices()  # Обновить список после удаления
            remove_office_button.setEnabled(False)  # Деактивировать кнопку после удаления

    remove_office_button.clicked.connect(remove_office)
    office_list.itemSelectionChanged.connect(on_office_selected)
    layout.addLayout(redirect_layout)
    layout.addSpacerItem(QSpacerItem(20, 20))
    layout.addLayout(dont_send_layout)
    layout.addSpacerItem(QSpacerItem(20, 20))
    layout.addLayout(redirect_toggle_dontr_send_layout)
    layout.addSpacerItem(QSpacerItem(20, 20))
    layout.addWidget(office_search)
    layout.addWidget(office_list)
    button_layout = QHBoxLayout()
    button_layout.addWidget(add_office_button)
    button_layout.addWidget(remove_office_button)
    layout.addLayout(button_layout)


    btn_show_templates = QPushButton('Показать шаблоны переадресации')
    btn_next = QPushButton('Далее')
    btn_back = QPushButton('Назад')

    layout.addWidget(btn_show_templates)
    layout.addWidget(btn_next)
    layout.addWidget(btn_back)

    btn_next.clicked.connect(lambda: on_type_next(True, False, redirect_toggle.isChecked(), dont_send_toggle.isChecked(), redirect_toggle_dontr_send.isChecked()))
    btn_back.clicked.connect(main_page)

    btn_show_templates.clicked.connect(show_templates_stub)

    WINDOW.setCentralWidget(container)


def show_templates_stub():
    dialog = QDialog()
    dialog.setWindowTitle('Шаблоны переадресации')
    dialog.resize(850, 500)
    main_layout = QVBoxLayout(dialog)

    # Поле поиска
    search_input = QLineEdit()
    search_input.setPlaceholderText("Поиск...")
    main_layout.addWidget(search_input)

    # Загружаем пользовательские данные
    data_load = load_user_data()
    if 'исключения_комментариев' not in data_load:
        data_load['исключения_комментариев'] = []
        save_user_data(data_load)
    # Первый layout для списка с переадресацией
    resend_layout = QVBoxLayout()
    resend_label = QLabel('Переадресация задана параметрами для этих комментариев (Можете прожать для отмены переадресации по заданому комментарию):')
    list_with_resend = QListWidget()
    list_with_resend.setWordWrap(True)
    list_with_resend.setSelectionMode(QListWidget.MultiSelection)
    list_with_resend.setStyleSheet("QListWidget::item:selected { background-color: #ADD8E6; }")
    resend_layout.addWidget(resend_label)
    resend_layout.addWidget(list_with_resend)

    # Второй layout для списка без переадресации
    no_resend_layout = QVBoxLayout()
    no_resend_label = QLabel('❌ Переадресация не учитывается для этих комментариев:')
    list_without_resend = QListWidget()
    list_without_resend.setWordWrap(True)
    no_resend_layout.addWidget(no_resend_label)
    no_resend_layout.addWidget(list_without_resend)

    # Флаг для отключения обработчика во время инициализации
    initializing = True

    # Заполняем списки
    resend_items = [key for key, value in VERSION_LOAD.get('resend_sz', {}).items() if value.get('need_resend', False)]
    no_resend_items = [key for key, value in VERSION_LOAD.get('resend_sz', {}).items() if not value.get('need_resend', False)]

    def populate_lists(filter_text=""):
        list_with_resend.clear()
        list_without_resend.clear()

        for key in resend_items:
            if filter_text.lower() in key.lower():
                prefix = "✅" if key not in data_load['исключения_комментариев'] else "❌"
                item = QListWidgetItem(f"{prefix} {key}")
                item.setToolTip(key)
                item.setData(Qt.UserRole, key)
                if key not in data_load['исключения_комментариев']:
                    item.setSelected(True)
                list_with_resend.addItem(item)
                if key != resend_items[-1]:
                    separator = QListWidgetItem()
                    separator.setFlags(Qt.NoItemFlags)
                    separator.setText("")
                    separator.setBackground(Qt.darkGray)  # Толстая разделительная полоса
                    separator.setSizeHint(QSize(0, 4))
                    list_with_resend.addItem(separator)

        for key in no_resend_items:
            if filter_text.lower() in key.lower():
                item = QListWidgetItem(f"{key}")
                item.setToolTip(key)
                list_without_resend.addItem(item)
                if key != no_resend_items[-1]:
                    separator = QListWidgetItem()
                    separator.setFlags(Qt.NoItemFlags)
                    separator.setText("")
                    separator.setBackground(Qt.darkGray)  # Толстая разделительная полоса
                    separator.setSizeHint(QSize(0, 4))
                    list_without_resend.addItem(separator)

    populate_lists()  # Первоначальное заполнение списков

    # Обработчик поиска
    def handle_search():
        text = search_input.text().strip()
        populate_lists(text)

    search_input.textChanged.connect(handle_search)

    # Обработчик изменения выделения
    def handle_selection_change():
        if initializing:
            return

        selected_items = list_with_resend.selectedItems()
        for item in selected_items:
            key = item.data(Qt.UserRole)
            if key in data_load['исключения_комментариев']:
                data_load['исключения_комментариев'].remove(key)
            else:
                data_load['исключения_комментариев'].append(key)

        save_user_data(data_load)
        populate_lists(search_input.text().strip())  # Перезаполняем списки после изменений

    list_with_resend.itemSelectionChanged.connect(handle_selection_change)
    initializing = False  # Завершаем инициализацию

    # Кнопка закрытия
    close_button = QPushButton("Закрыть")
    close_button.clicked.connect(dialog.close)
    button_layout = QHBoxLayout()
    button_layout.addStretch()
    button_layout.addWidget(close_button)

    # Добавляем layouts в главный layout
    main_layout.addLayout(resend_layout)
    main_layout.addLayout(no_resend_layout)
    main_layout.addLayout(button_layout)  # Добавляем кнопку закрытия внизу

    dialog.exec_()
    
def on_type_next(radio_orders, radio_invoices, redirect_toggle, dont_send_toggle, redirect_toggle_dontr_send):
    global SZ_DATA_JSON
    if radio_orders:
        SZ_DATA_JSON['ТипСЗ'] = "заказ"
    elif radio_invoices:
        SZ_DATA_JSON['ТипСЗ'] = "заявка"
    SZ_DATA_JSON['Редирект_сз'] = redirect_toggle
    SZ_DATA_JSON['Не_отправлять_сз'] = dont_send_toggle
    SZ_DATA_JSON['Не_отправлять_сз_для_исключений'] = redirect_toggle_dontr_send
    send_sz_menu_2()

class Check_internet_2(QThread):
    log_signal = pyqtSignal(str)
    progress_out = pyqtSignal()
    progress_signal = pyqtSignal(int, int)
    progress_text = pyqtSignal(str)
    stoping_signal = pyqtSignal()

    def __init__(self, Kek):
        super().__init__()
        self.running = True
        self.kek = Kek

    def run(self):
        if self.kek:
            global USER_TOKEN, GLOBAL_PASSWORD
            TOKEN = USER_TOKEN
            USER_TOKEN_1 = None
            if os.path.exists(DATA_USER) and not TOKEN:
                USER_TOKEN_1 = check_login(GLOBAL_PASSWORD)
            if USER_TOKEN_1: 
                USER_TOKEN = USER_TOKEN_1
                self.progress_out.emit()
            if USER_TOKEN:
                if data_info := get_full_info(USER_TOKEN):
                    DATA_USER_ = load_user_data()
                    DATA_USER_['TOKEN'] = USER_TOKEN
                    DATA_USER_['Имя'] = data_info['individual']['rus']
                    with open(f"{WORK_DIR}/файлы_автозапросов/ключ/data_user.json", "w", encoding="utf-8") as file:
                        json.dump(DATA_USER_, file, ensure_ascii=False, indent=2)
                    USER_TOKEN = USER_TOKEN
                    self.progress_out.emit()
                else:
                    USER_TOKEN = False
                    self.progress_out.emit()
            else: 
                USER_TOKEN = False
                self.progress_out.emit()

    def stop(self):
        self.running = False

def main_page():
    container = QWidget()
    layout = QVBoxLayout(container)
    global SZ_DATA_JSON
    global EXPORT_SSS_2
    SZ_DATA_JSON = {}
    SZ_DATA_JSON['Данные_текста_номеров'] = ""
    global USER_TOKEN, GAZES_ACCES, USERS_ACCES, GAZES_ACCES_PRIME, USERS_ACCES_PRIME
    title = QLabel(f'<span style="font-size: 24px;">Проверка токена</span>')
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    WINDOW.setCentralWidget(container)
    def out_def_2__():
        main_page_2()
    EXPORT_SSS_2 = Check_internet_2(True)
    EXPORT_SSS_2.progress_out.connect(out_def_2__)
    EXPORT_SSS_2.start()

update_dialog_open_lower_acces = False
def show_update_dialog_lower_acces():
    global update_dialog_open_lower_acces
    gazes = "\n....".join(VERSION_LOAD['acces_gazes'])
    user = "\n....".join(VERSION_LOAD['acces_users'])
    changelog_text = f"<b>- Доступ выгрузки накладных доступен у зон:</b>\n....{gazes}\n\n<b>- Доступ выгрузки накладных для сз у пользователей:</b>\n....{user}"
    if update_dialog_open_lower_acces:
        return
    changelog_text = changelog_text.replace("\n", "<br>")
    update_dialog_open_lower_acces = True
    message = f"""
    <p>{changelog_text}</p>
    """

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("Информация по доступу")
    msg.setTextFormat(Qt.RichText) 
    msg.setText(message)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.button(QMessageBox.Ok).setText("Ок")
    
    if msg.exec_() == QMessageBox.Ok:
        update_dialog_open_lower_acces = False
        return


update_dialog_open_lower = False
def show_update_dialog_lower():
    global update_dialog_open_lower
    # changelog_text = "18.001\n"
    # changelog_text += "- Добавлена выгрузка накладных по номеру телефону\n"
    # changelog_text += "- Добавлена возможность посмотреть список изменений текущей версии кода\n"
    # changelog_text += "- Добавлена возможность посмотреть права доступа\n\n"
    # changelog_text += "18.002\n"
    # changelog_text += "- Исправлена выгрузка после накладных для сз на 40%\n\n"
    # changelog_text = "18.003\n"
    # changelog_text += "- Исправлен подсчет в отправке СЗ на втором этапе при выборе отдела по приоритетности\n"
    # changelog_text += "- Добавлены смайлики-информаторы ❓✅❌ при отправке СЗ\n"
    # changelog_text += "- <b>Теперь, если в текущем офисе и отделе уже есть СЗ, будет отправлено дополнительное сообщение с текстом шаблона</b>\n"
    # changelog_text += "- Первая строка в таблицах теперь закреплена\n\n"
    # changelog_text += "18.004\n"
    # changelog_text += "- Добавлен столбец в листе накладных на МСК с тарифом\n"
    # changelog_text += "- Добавлено меню перед выгрузкой накладных, в котором можно указать выгрузку доп. тарифов\n"
    # changelog_text += "- Исправлено отображение наличия СЗ по ПРР у Получателя или отправителя\n\n"
    # changelog_text += "18.005\n"
    # changelog_text += "- Исправлена фильтрация доступа по отправке СЗ, когда нужно было выбрать газельные бригады. Теперь проверка по общему пулу доступа\n\n"
    changelog_text = "18.006\n"
    changelog_text += "- Добавлены шаблоны переадресации в другой офис из комменатриев\n"
    changelog_text += "- Добавлены кнопки для копирования проблемных накладных после отпарвки СЗ. [Запретные, Ошибочные, не найденные офисы/отделы]\n"
    changelog_text += "- Добавлен тоглер на запрет отправки где комменатрий \nЕсли вы пишите нам как в ЦФО и есть ЗМ, то проверьте, если ЗМ с СК - пишите на почту assist@cdek.ru; , если ЗМ с Московского Центрального офиса - пишите на почту support_msk@cdek.ru; если клиент Cainiao пишите на почту cainiao@cdek.ru\n\n"
    changelog_text += "\n18.007\n"
    changelog_text += "- Добавлена кнопка перенаправления СЗ в Центральный офис если ЦФО указан как запрет\n"
    changelog_text += "- Добавлена возможность добавить офис в список запретов на отправку СЗ\n\n"
    changelog_text += "\n18.008\n"
    changelog_text += "- Добавлен запрос на использование сохраненного пароля при входе, чтобы не блокировалась учетка если меняли пароль\n"
    changelog_text += "\n18.009\n"
    changelog_text += "- Добавлен кнопка удаления таблиц, и кнопка удаления профиля в окне авторизации при запуске и главном меню\n"
    changelog_text += "\n18.010\n"
    changelog_text += "- Добавлены цыфры обьемного и физ веса в таблицу\n"
    changelog_text += "\n18.011\n"
    changelog_text += "- Исправлены получения инфо при выгрузке\n"
    changelog_text += "\n18.012 (Тестовая)\n"
    changelog_text += "- Новый алгоритм отправки сз\n"
    if update_dialog_open_lower:
        return 
    changelog_text = changelog_text.replace("\n", "<br>")
    update_dialog_open_lower = True 
    message = f"""
    <p>Код программы обновлен до <b>{CURRENT_VERSION}</b></p>
    <p><b>Список изменений:</b></p>
    <p>{changelog_text}</p>
    """

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("Информация по обновлению")
    msg.setTextFormat(Qt.RichText) 
    msg.setText(message)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.button(QMessageBox.Ok).setText("Ок")
    
    if msg.exec_() == QMessageBox.Ok:
        update_dialog_open_lower = False
        return

def main_page_2():
    # print("\n2\n2\n2\n2\n\n\n")
    container = QWidget()
    layout = QVBoxLayout(container)
    global SZ_DATA_JSON
    SZ_DATA_JSON = {}
    SZ_DATA_JSON['Данные_текста_номеров'] = ""
    global USER_TOKEN, GAZES_ACCES, USERS_ACCES, GAZES_ACCES_PRIME, USERS_ACCES_PRIME
    data_load = load_user_data()
    zones = ""
    global all_rows, all_line
    all_rows = 0
    all_line = 0
    def add_button(button):
        global all_rows, all_line
        
        button.setFixedSize(250, 35)
        grid_layout.addWidget(button, all_line, all_rows)
        
        if all_rows == 1:
            all_line += 1
            all_rows = 0
        else:
            all_rows += 1
    if "текущяя_верия" not in data_load:
        data_load['текущяя_верия'] = ''
    
    if str(CURRENT_VERSION) != str(data_load['текущяя_верия']):
        data_load['текущяя_верия'] = str(CURRENT_VERSION)
        show_update_dialog_lower()
        save_user_data(data_load)
    if not USER_TOKEN:
        title = QLabel('<span style="font-size: 24px;">Вы не авторизованы<br>Либо не предоставили токен ЭК5 для работы</span>')
        btn_auth = QPushButton('Авторизация')
    else:
        for regionNew in VERSION_LOAD['acces_users_region']:
            if regionNew not in USERS_ACCES_PRIME:
                USERS_ACCES_PRIME.append(regionNew)
        if 'Все_офисы' not in data_load:
            if check_acces_user(data_load['Имя'], VERSION_LOAD['acces_users_region']):
                data_load['Все_офисы'] = True
            else:
                data_load['Все_офисы'] = False
        else:
            
            if data_load['Все_офисы'] and not check_acces_user(data_load['Имя'], USERS_ACCES_PRIME):
                data_load['Все_офисы'] = False
        if check_acces_user(data_load['Имя'], USERS_ACCES_PRIME) and GAZES_ACCES != GAZES_ACCES_PRIME:
            USERS_ACCES = USERS_ACCES_PRIME
            GAZES_ACCES = GAZES_ACCES_PRIME
            if not 'Проверка' in data_load and check_acces_user(data_load['Имя'], VERSION_LOAD['acces_users_region']):
                data_load['Проверка'] = True
        if check_acces_user(data_load['Имя'], USERS_ACCES):
            if 'Имя' in data_load:
                name = data_load['Имя']
            else:
                name = ""
            zones = gazes_currect(GAZES_ACCES)
            if zones:
                zones = ", ".join(zones)
                zones = f"<br>Выбраны бригады: {zones}"
            else:
                zones = ""
            
            title = QLabel(f'Выберите действие<br>{name}{zones}')
            btn_auth = QPushButton('Пере-Авторизация')
        else:
            title = QLabel(f'Пользователь <br>{data_load["Имя"]}<br>не добавлен в список доступа')
            btn_auth = QPushButton('Пере-Авторизация')
        save_user_data(data_load)
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    grid_layout = QGridLayout()
    btn_export = QPushButton('Выгрузить накладные')
    btn_sz = QPushButton('Отправить СЗ')
    btn_open_folder = QPushButton('Папка с таблицами')
    select_zones = QPushButton('Выбор бригад/офисов')
    clear_tables = QPushButton('Удалить таблицы')
    clear_user = QPushButton('Удалить пользователя')
    settings = QPushButton('Настройки')
    changelog = QPushButton('Список изменений')
    acceses = QPushButton('Права доступа')
    add_button(btn_auth)
    add_button(btn_export)
    add_button(btn_sz)
    add_button(btn_open_folder)
    add_button(select_zones)
    add_button(settings)
    add_button(changelog)
    add_button(acceses)
    add_button(clear_user)
    add_button(clear_tables)
    try:
        if USER_TOKEN and 'Имя' in data_load and check_acces_user(data_load['Имя'], VERSION_LOAD['acces_users_change_macrozones']):
            get_order_from_shk = QPushButton('Изменить макрозоны')
            add_button(get_order_from_shk)
    except:
        pass
    if USER_TOKEN and 'Имя' in data_load and check_acces_user(data_load['Имя'], VERSION_LOAD['acces_users_order']):
        phone_export = QPushButton('Выгрузить по телефону')
        add_button(phone_export)
    if USER_TOKEN and 'Имя' in data_load and check_acces_user(data_load['Имя'], VERSION_LOAD['acces_users_close_preorder']):
        close_self_tasks = QPushButton('Закрыть себе точки')
        add_button(close_self_tasks)
    
    global PHONE_DATA_JSON
    PHONE_DATA_JSON = {}
    if not zones:
        btn_export.setEnabled(False)
    if not USER_TOKEN or (data_load and not check_acces_user(data_load['Имя'], USERS_ACCES)):
        btn_sz.setEnabled(False)
        btn_export.setEnabled(False)
        clear_user.setEnabled(False)
        select_zones.setEnabled(False)
    
    tables_dir = f"{WORK_DIR}/файлы_автозапросов/таблицы/"
    if os.path.isdir(tables_dir):
        files = [f for f in os.listdir(tables_dir) if os.path.isfile(os.path.join(tables_dir, f))]
        if files:
            total_size = sum(os.path.getsize(os.path.join(tables_dir, f)) for f in files)
            total_size_mb = round(total_size / (1024 * 1024), 2)
            clear_tables.setEnabled(True)
            clear_tables.setText(f"Удалить таблицы ({total_size_mb} МБ)")
        else:
            clear_tables.setEnabled(False)
    else:
        clear_tables.setEnabled(False)
    def clear_data():
        data_file = f"{WORK_DIR}/файлы_автозапросов/ключ/data_user.json"
        
        if os.path.exists(data_file):
            try:
                os.remove(data_file)
                print("Файл data_user.json удалён.")
            except Exception as e:
                print(f"Ошибка при удалении файла: {e}")
        global SZ_DATA_JSON
        global EXPORT_SSS_2
        SZ_DATA_JSON = {}
        SZ_DATA_JSON['Данные_текста_номеров'] = ""
        global USER_TOKEN, GAZES_ACCES, USERS_ACCES, GAZES_ACCES_PRIME, USERS_ACCES_PRIME
        USER_TOKEN = None
        EXPORT_SSS_2 = None
        GAZES_ACCES = None
        USERS_ACCES = None
        GAZES_ACCES_PRIME = None
        USERS_ACCES_PRIME = None
        main_page()
    def clear_tables_():
        tables_dir = f"{WORK_DIR}/файлы_автозапросов/таблицы/"
        
        if os.path.isdir(tables_dir):
            try:
                for filename in os.listdir(tables_dir):
                    file_path = os.path.join(tables_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            except Exception as e:
                print(f"Ошибка при удалении файлов: {e}")
        
        clear_tables.setText("Таблицы удалены!")
        clear_tables.setEnabled(False)
        
    check_for_update()
    layout.addLayout(grid_layout)
    WINDOW.setCentralWidget(container)
    btn_sz.clicked.connect(send_sz_menu_1)
    btn_export.clicked.connect(export_menu)
    settings.clicked.connect(settings_menu)
    clear_user.clicked.connect(clear_data)
    clear_tables.clicked.connect(clear_tables_)
    btn_auth.clicked.connect(auth_menu)
    btn_open_folder.clicked.connect(open_folder_dialog)
    select_zones.clicked.connect(select_zones_def)
    try:
        if USER_TOKEN and 'Имя' in data_load and check_acces_user(data_load['Имя'], VERSION_LOAD['acces_users_change_macrozones']):
            get_order_from_shk.clicked.connect(get_order_from_shk_def)
    except:
        pass
    if USER_TOKEN and 'Имя' in data_load and check_acces_user(data_load['Имя'], VERSION_LOAD['acces_users_order']):
        phone_export.clicked.connect(phone_export_def)
    if USER_TOKEN and 'Имя' in data_load and check_acces_user(data_load['Имя'], VERSION_LOAD['acces_users_close_preorder']):
        close_self_tasks.clicked.connect(close_self_tasks_def)
    changelog.clicked.connect(show_update_dialog_lower)
    acceses.clicked.connect(show_update_dialog_lower_acces)

complited_orders_ = {}
class ProcessingThread(QThread):
    result_signal = pyqtSignal(str, str)
    
    def __init__(self, line, TOKEN):
        super().__init__()
        self.line = line.strip()
        self.token = TOKEN
        self._is_running = True
    
    def run(self):
        import time
        global complited_orders_
        if self._is_running:
            
            result_text = get_adgress_hranen(self.token, convert_layout(self.line))
            if result_text[0] != "Ошибка":
                complited_orders_[str(self.line)] = result_text[1]
            result = f"{convert_layout(self.line)} - {result_text[1]}"
            self.result_signal.emit(self.line, result)
            # print(complited_orders_)
    
    def stop(self):
        self._is_running = False
        self.wait()  # Ждем завершения потока

class OrderProcessor:
    def __init__(self):
        global complited_orders_
        self.processed_lines = {}  # Завершенные строки
        self.processing_line = None  # Текущая обрабатываемая строка
        self.queue_lines = []  # Очередь строк
        self.pending_cursor_line = None  # Строка под курсором с таймером
        self.cursor_timer = QTimer()
        self.cursor_timer.setSingleShot(True)
        self.cursor_timer.timeout.connect(self.on_cursor_timeout)
        self.cursor_wait_time = 5  # Начальное время ожидания в секундах
        self.update_timer = QTimer()  # Таймер для обновления статуса
        self.update_timer.timeout.connect(self.update_cursor_status)
        self.current_thread = None  # Текущий активный поток
        self.TOKEN = check_login(GLOBAL_PASSWORD)
        self.previous_lines = []  # Хранение предыдущего состояния строк
        self.page = QWidget()
        self.layout = QHBoxLayout(self.page)
        
        self.input_layout = QVBoxLayout()
        self.input_layout.addWidget(QLabel('Введите номера:'))
        self.text_numbers = QTextEdit()
        self.text_numbers.setAcceptRichText(False)
        self.btn_next = QPushButton('Далее')
        self.btn_back = QPushButton('Назад')
        
        self.input_layout.addWidget(self.text_numbers)
        self.input_layout.addWidget(self.btn_next)
        self.input_layout.addWidget(self.btn_back)
        
        self.output_layout = QVBoxLayout()
        self.output_layout.addWidget(QLabel('Преобразованный текст:'))
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.output_layout.addWidget(self.text_output)
        
        self.layout.addLayout(self.input_layout)
        self.layout.addLayout(self.output_layout)
        
        WINDOW.setCentralWidget(self.page)
        
        self.text_numbers.textChanged.connect(self.on_text_change)
        self.text_numbers.cursorPositionChanged.connect(self.on_cursor_position_changed)
        self.btn_next.clicked.connect(lambda: change_macrozones(complited_orders_))
        self.btn_next.setEnabled(False)
        
        self.btn_back.clicked.connect(main_page)

    def update_output(self, line, result):
        if self.current_thread:
            self.current_thread.quit()
            self.current_thread.wait()
            self.current_thread = None
        self.processed_lines[line] = result
        self.processing_line = None
        self.text_output.setPlainText("\n".join(self.get_output_text()))
        self.process_next_in_queue()

    def get_output_text(self):
        input_lines = self.text_numbers.toPlainText().split("\n")
        output_lines = []
        for line in input_lines:
            line = line.strip()
            if not line:
                continue
            if line == self.processing_line:
                output_lines.append(f"{convert_layout(line)} - Обрабатывается")
            elif line in self.processed_lines:
                output_lines.append(self.processed_lines[line])
            elif line in self.queue_lines:
                output_lines.append(f"{convert_layout(line)} - В очереди")
            elif line == self.pending_cursor_line:
                output_lines.append(f"{convert_layout(line)} - Обработка через {self.cursor_wait_time} сек")
            else:
                if line not in self.queue_lines and line != self.pending_cursor_line:
                    self.queue_lines.append(line)
                output_lines.append(f"{convert_layout(line)} - Не удалось добавить в очередь")
        return output_lines
    
    def process_next_in_queue(self):
        if not self.queue_lines and self.processing_line is None and complited_orders_ and not self.pending_cursor_line:
            self.btn_next.setEnabled(True)
        else:
            self.btn_next.setEnabled(False)
        if self.processing_line is None and self.queue_lines:
            self.processing_line = self.queue_lines.pop(0)
            self.current_thread = ProcessingThread(self.processing_line, self.TOKEN)
            self.current_thread.result_signal.connect(self.update_output)
            self.current_thread.start()
            self.text_output.setPlainText("\n".join(self.get_output_text()))

    def on_cursor_position_changed(self):
        self.cursor_timer.stop()
        self.update_timer.stop()
        self.cursor_wait_time = 5
        cursor_line = self.text_numbers.textCursor().block().text().strip()
        if cursor_line and cursor_line not in self.processed_lines and cursor_line != self.processing_line:
            self.pending_cursor_line = cursor_line
            self.cursor_timer.start(5000)
            self.update_timer.start(1000)
        else:
            self.pending_cursor_line = None
        self.text_output.setPlainText("\n".join(self.get_output_text()))
    
    def on_cursor_timeout(self):
        if self.pending_cursor_line and self.pending_cursor_line not in self.processed_lines and self.pending_cursor_line != self.processing_line:
            if self.pending_cursor_line not in self.queue_lines:
                self.queue_lines.append(self.pending_cursor_line)
            self.pending_cursor_line = None
            self.process_next_in_queue()
            self.text_output.setPlainText("\n".join(self.get_output_text()))

    def update_cursor_status(self):
        if self.pending_cursor_line:
            self.cursor_wait_time -= 1
            if self.cursor_wait_time <= 0:
                self.on_cursor_timeout()
                self.cursor_wait_time = 5
            self.text_output.setPlainText("\n".join(self.get_output_text()))

    def on_text_change(self):
        self.text_numbers.textChanged.disconnect(self.on_text_change)  # Отключаем сигнал перед изменением
        
        cursor = self.text_numbers.textCursor()
        cursor_position = cursor.position()
        
        # Получаем текущий текст и заменяем запятые на переносы строк
        current_text = self.text_numbers.toPlainText()
        modified_text = current_text.replace(", \n", "\n").replace(",\n", "\n").replace(",", "\n")
        
        # Проверяем, изменился ли текст, чтобы избежать лишних вызовов
        if current_text != modified_text:
            self.text_numbers.setPlainText(modified_text)
            # Восстанавливаем позицию курсора после изменения текста
            cursor.setPosition(cursor_position)
            self.text_numbers.setTextCursor(cursor)
        
        # Текущие строки после модификации
        current_lines = [line.strip() for line in self.text_numbers.toPlainText().split("\n") if line.strip()]
        
        # Определяем удалённые строки
        deleted_lines = set(self.previous_lines) - set(current_lines)
        for line in deleted_lines:
            if line in self.processed_lines:
                del self.processed_lines[line]
            if line in self.queue_lines:
                self.queue_lines.remove(line)
            if str(line) in complited_orders_:
                del complited_orders_[str(line)]
        
        # Обновляем предыдущее состояние
        self.previous_lines = current_lines.copy()
        
        # Добавляем новые строки в очередь
        for line in current_lines:
            if line and line not in self.processed_lines and line != self.processing_line and line not in self.queue_lines and line != self.pending_cursor_line:
                self.queue_lines.append(line)
        
        self.process_next_in_queue()
        self.text_output.setPlainText("\n".join(self.get_output_text()))
        
        # Восстанавливаем позицию курсора ещё раз, если она могла сбиться
        cursor.setPosition(cursor_position)
        self.text_numbers.setTextCursor(cursor)
        
        self.text_numbers.textChanged.connect(self.on_text_change)  # Подключаем сигнал обратно
        
        # Сбрасываем и обновляем таймеры
        self.cursor_timer.stop()
        self.update_timer.stop()
        self.cursor_wait_time = 5
        self.on_cursor_position_changed()

    def cleanup(self):
        if self.current_thread:
            self.current_thread.stop()


def change_macrozones(text_numbers=None):
    page = QWidget()
    layout = QVBoxLayout(page)
    complited_orders__ = []
    
    # Заполняем complited_orders__ из text_numbers
    for key, f in text_numbers.items():
        if f not in complited_orders__:
            for f2 in f.split(','):
                if f2.strip() not in complited_orders__:
                    complited_orders__.append(f)
    # print(complited_orders__)
    
    # Добавляем текстовое поле
    layout.addWidget(QLabel('Проверьте введенные номера:'))
    text_confirm = QTextEdit()
    text_confirm.setReadOnly(True)
    text_confirm.setPlainText('\n'.join(complited_orders__))
    layout.addWidget(text_confirm)
    
    # Горизонтальный layout для кнопок подтверждения
    confirm_layout = QHBoxLayout()
    btn_confirm = QPushButton('Изменить на ЛА')
    btn_confirm2 = QPushButton('Изменить на ГАЗ')
    btn_confirm3 = QPushButton('Изменить на СРП')
    
    confirm_layout.addWidget(btn_confirm)
    confirm_layout.addWidget(btn_confirm2)
    confirm_layout.addWidget(btn_confirm3)
    
    # Добавляем горизонтальный layout в основной вертикальный
    layout.addLayout(confirm_layout)
    
    # Кнопка "Назад" в центре
    btn_back = QPushButton('Назад')
    layout.addWidget(btn_back, alignment=Qt.AlignCenter)
    
    # Устанавливаем страницу в окно
    WINDOW.setCentralWidget(page)
    
    # Подключение сигналов
    btn_confirm.clicked.connect(lambda: change_macrozones_2('ЛА', complited_orders__))
    btn_confirm2.clicked.connect(lambda: change_macrozones_2('ГАЗ', complited_orders__))
    btn_confirm3.clicked.connect(lambda: change_macrozones_2('СРП', complited_orders__))
    btn_back.clicked.connect(main_page)
    
    return page

class CHANGE_MACRO_CLASS(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(int, int)
    stoping_signal = pyqtSignal()
    def __init__(self, data):
        super().__init__()
        self.running = True
        self.data = data[1]
        self.what = data[0]

    def run(self):
        TOKEN = check_login(GLOBAL_PASSWORD)
        url = "https://gateway.cdek.ru/flo-webservice/web/ui/flo/orderLocation/getFilterData"
        payload = {
                "sort": [],
                "offset": 0,
                "limit": 5000,
                "fields": [
                    {
                    "field": "orderNumber",
                    "value": None,
                    "values": self.data
                    }
                ],
                "columns": [
                    "orderNumber",
                    "dateCreated",
                    "orderStatus",
                    "currentLocation",
                    "city",
                    "address",
                    "validatedAddress",
                    "office",
                    "macrozone",
                    "macrozoneType",
                    "problemAddress",
                    "calculationState",
                    "dimensionalState",
                    "coordinateSource"
                ],
                "lang": "rus"
                }
        data_0 = return_post_response(url=url, headers=headers(TOKEN), payloads=payload)
        if data_0: data_0 = data_0.json()
        else: 
            self.log_signal.emit(f"Ошибка выгрузки таблицы проблемных адресов")
            self.progress_signal.emit(100, 100)
            self.stoping_signal.emit()
            return
        startswithss2 = ""
        startswithss3 = ""
        startswithss = ""
        if self.what == "ГАЗ":
            # startswithss = "Газелист"
            which_macrp = "Газелист"
            startswithss = "газ"
        elif self.what == "СРП":
        # elif which_macrp == "Супер-экспресс":
            which_macrp = "Супер-экспресс"
            startswithss = "срп"
        elif self.what == "ЛА":
        # elif self.what == "ЛА":
            which_macrp = "Курьер ЛА"
            startswithss2 = "газ"
            startswithss3 = "срп"
        tick = 0
        for f in data_0['items']:
            # print(f)
            tick += 1
            self.progress_signal.emit(tick, len(data_0['items']))
            if startswithss:
                if f['macrozone'].replace('.','').lower().startswith(startswithss): continue
            if startswithss2 and startswithss3:
                if not f['macrozone'].replace('.','').lower().startswith(startswithss2) and \
                    not f['macrozone'].replace('.','').lower().startswith(startswithss3): continue
            url_get = f"https://gateway.cdek.ru/flo-webservice/web/ui/flo/lastDoor/availableMacrozones?orderUuid={f['orderUuid']}"
            data2 = return_get_response(url=url_get, headers=headers(TOKEN))
            
            if data2: data2 = data2.json()
            else: 
                self.log_signal.emit(f'Ошибка в {f["orderNumber"]} в выгрузке доступтных слоев')
                continue
            for f2 in data2['macrozones']:
                if f2['layerName'] == which_macrp:
                    url_change = "https://gateway.cdek.ru/flo-webservice/web/ui/flo/lastDoor/changeMacrozone"
                    payload = {
                        "orderUuid": f['orderUuid'],
                        "macrozoneUuid": f2['uuid']
                        }
                    data3 = return_post_response(url=url_change, headers=headers(TOKEN), payloads=payload)
                    if data3: self.log_signal.emit(f"{f['orderNumber']} изменено на {which_macrp}")
                    else: self.log_signal.emit(f"Ошибка в изменение {f['orderNumber']} на {which_macrp}")
                    break
            else:
                self.log_signal.emit(f"Слой {which_macrp} для {f['orderNumber']} не найден")
        
        self.progress_signal.emit(100, 100)
        self.finished_signal.emit()

    def stop(self):
        self.running = False

CHANGE_MACRO = None
def change_macrozones_2(what_change=None, orders_=None):
    def update_progress(current, total):
        percentage = int((current / total) * 100)
        progress_bar.setValue(percentage)
        if percentage < 50:
            pass
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: black;  /* Текст черный на белом фоне */
                }
            """)
        else:
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: white;  /* Текст белый на фоне прогресса */
                }
            """)
        progress_bar.setFormat(f"{percentage}%")
    container = QWidget()
    layout = QVBoxLayout(container)
    log_window = QTextEdit()
    log_window.setReadOnly(True)
    layout.addWidget(log_window)
    back_button = QPushButton("Назад")
    back_button.setEnabled(False)
    layout.addWidget(back_button)
    stop_button = QPushButton("Остановить обработку")
    layout.addWidget(stop_button)
    WINDOW.setCentralWidget(container)
    progress_bar = QProgressBar()
    progress_bar.setMinimum(0)
    progress_bar.setMaximum(100)
    progress_bar.setTextVisible(True)
    progress_bar.setFormat("0% (0/0)")
    progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;  /* Центрируем текст */
                    color: black;  /* Текст черный на белом фоне */
                }
                QProgressBar::chunk {
                    background-color: #11543BFF;
                    border-radius: 5px;
                }
            """)
    layout.addWidget(progress_bar)
    CHANGE_MACRO = CHANGE_MACRO_CLASS([what_change, orders_])
    CHANGE_MACRO.log_signal.connect(log_window.append)  # Логи добавляются в текстовое поле
    CHANGE_MACRO.finished_signal.connect(lambda: on_finished(back_button, stop_button))
    CHANGE_MACRO.stoping_signal.connect(lambda: on_stop_signal(back_button, stop_button))
    CHANGE_MACRO.progress_signal.connect(update_progress)
    CHANGE_MACRO.start()
    def go_back():
        global CHANGE_MACRO
        CHANGE_MACRO = None
        main_page()
    def stop_processing():
        if CHANGE_MACRO is not None:
            CHANGE_MACRO.stop()
    def on_stop_signal(back_btn, stop_btn):
        back_btn.setEnabled(True)
        stop_btn.setEnabled(False)
        reload = QPushButton("Перевыгрузить")
        layout.addWidget(reload)
        reload.clicked.connect(lambda: export_menu())
        progress_bar.setValue(100)
        progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;  /* Центрируем текст */
                    color: white;  /* Текст черный на белом фоне */
                }
                QProgressBar::chunk {
                    background-color: #A40E2C;
                    border-radius: 5px;
                }
            """)
        progress_bar.setFormat(f"Прервано")
    def on_finished(back_btn, stop_btn):
        try:
            progress_bar.setValue(100)
        except Exception:
            pass
        back_btn.setEnabled(True)
        stop_btn.setEnabled(False)
    back_button.clicked.connect(go_back)
    stop_button.clicked.connect(stop_processing)

def get_order_from_shk_def():
    global order_processor, complited_orders_
    complited_orders_ = {}
    order_processor = OrderProcessor()
    
    
translit_map = str.maketrans(
        "ёйцукенгшщзхъфывапролджэячсмить",
        "`qwertyuiop[]asdfghjkl;'zxcvbnm"
    )
translit_map.update(str.maketrans(
    "ЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ",
    "~QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>"
))
def convert_layout(text):
    return text.translate(translit_map)




CLOSE_THREAD_TASK = None
def close_tasks(tasks_array, close_all_immediately):
    global CLOSE_THREAD_TASK
    print(f"Закрываем задачи, close_all_immediately={close_all_immediately}")
    def update_progress(current, total):
        percentage = int((current / total) * 100)
        progress_bar.setValue(percentage)
        if percentage < 50:
            pass
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: black;  /* Текст черный на белом фоне */
                }
            """)
        else:
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: white;  /* Текст белый на фоне прогресса */
                }
            """)
        progress_bar.setFormat(f"{percentage}%")
    container = QWidget()
    layout = QVBoxLayout(container)
    log_window = QTextEdit()
    log_window.setReadOnly(True)
    layout.addWidget(log_window)
    back_button = QPushButton("Назад")
    back_button.setEnabled(False)
    layout.addWidget(back_button)
    stop_button = QPushButton("Остановить обработку")
    layout.addWidget(stop_button)
    WINDOW.setCentralWidget(container)
    progress_bar = QProgressBar()
    progress_bar.setMinimum(0)
    progress_bar.setMaximum(100)
    progress_bar.setTextVisible(True)
    progress_bar.setFormat("0% (0/0)")
    progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;  /* Центрируем текст */
                    color: black;  /* Текст черный на белом фоне */
                }
                QProgressBar::chunk {
                    background-color: #11543BFF;
                    border-radius: 5px;
                }
            """)
    layout.addWidget(progress_bar)
    CLOSE_THREAD_TASK = CloseThread_Tasks(tasks_array, close_all_immediately)
    CLOSE_THREAD_TASK.log_signal.connect(log_window.append)  # Логи добавляются в текстовое поле
    CLOSE_THREAD_TASK.finished_signal.connect(lambda: on_finished(back_button, stop_button))
    CLOSE_THREAD_TASK.stoping_signal.connect(lambda: on_stop_signal(back_button, stop_button))
    CLOSE_THREAD_TASK.progress_signal.connect(update_progress)
    CLOSE_THREAD_TASK.start()
    def go_back():
        global CLOSE_THREAD_TASK
        CLOSE_THREAD_TASK = None
        main_page()
    def stop_processing():
        if CLOSE_THREAD_TASK is not None:
            CLOSE_THREAD_TASK.stop()
    def on_stop_signal(back_btn, stop_btn):
        back_btn.setEnabled(True)
        stop_btn.setEnabled(False)
        progress_bar.setValue(100)
        progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;  /* Центрируем текст */
                    color: white;  /* Текст черный на белом фоне */
                }
                QProgressBar::chunk {
                    background-color: #A40E2C;
                    border-radius: 5px;
                }
            """)
        progress_bar.setFormat(f"Прервано")
    def on_finished(back_btn, stop_btn):
        try:
            progress_bar.setValue(100)
        except Exception:
            pass
        back_btn.setEnabled(True)
        stop_btn.setEnabled(False)
    back_button.clicked.connect(go_back)
    stop_button.clicked.connect(stop_processing)








def next_selected(tasks):
    page = QWidget()
    main_layout = QHBoxLayout(page)

    list_widget = QListWidget()
    main_layout.addWidget(list_widget)

    right_widget = QWidget()
    right_layout = QVBoxLayout(right_widget)
    right_layout.setAlignment(Qt.AlignTop)
    main_layout.addWidget(right_widget)

    current_task = {'index': None}

    # Ошибки
    lbl_name_error = QLabel()
    lbl_name_error.setStyleSheet("color: red")
    lbl_time_error = QLabel()
    lbl_time_error.setStyleSheet("color: red")

    # Новый лейбл для ошибок имен и информации о закрытии с интервалами
    lbl_name_length_error = QLabel()
    lbl_name_length_error.setStyleSheet("color: red")
    lbl_name_length_error.setWordWrap(True)

    name_label = QLabel("Имя получателя:")
    name_edit = QLineEdit()
    name_edit.setMaxLength(150)

    time_label = QLabel("Время закрытия (HH:MM:SS):")
    time_edit = QLineEdit()
    time_edit.setPlaceholderText("например, 14:30:00")

    # --- Добавляем в начало функции установку self_keys['time'] = текущее время + 3 мин ---
    now_plus_3 = datetime.now() + timedelta(minutes=3)
    for task in tasks:
        task.setdefault('self_keys', {})
        task['self_keys']['time'] = now_plus_3.strftime("%H:%M:%S")

    def validate_time_format(t):
        # Проверка формата HH:MM:SS
        return bool(re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$", t))

    def load_task_settings(index):
        # Сохраняем предыдущие настройки
        prev_idx = current_task['index']
        if prev_idx is not None:
            prev_task = tasks[prev_idx]
            if prev_task.get('taskType', '') == 'DELIVERY':
                prev_task.setdefault('self_keys', {})['name'] = name_edit.text()
            prev_task.setdefault('self_keys', {})['time'] = time_edit.text()

        current_task['index'] = index
        task = tasks[index]

        # Имя
        if task.get('taskType', '') == 'DELIVERY':
            right_layout.addWidget(name_label)
            right_layout.addWidget(name_edit)
            right_layout.addWidget(lbl_name_error)
            name_edit.show()
            name_label.show()
            lbl_name_error.show()
            name_edit.setText(task.get('self_keys', {}).get('name', ''))
        else:
            name_edit.hide()
            name_label.hide()
            lbl_name_error.hide()

        right_layout.addWidget(time_label)
        right_layout.addWidget(time_edit)
        right_layout.addWidget(lbl_time_error)
        time_label.show()
        time_edit.show()
        lbl_time_error.show()

        time_val = task.get('self_keys', {}).get('time')
        if time_val and validate_time_format(time_val):
            time_edit.setText(time_val)
        else:
            # По умолчанию текущее время + 2 мин
            dt = datetime.now() + timedelta(minutes=2)
            time_edit.setText(dt.strftime("%H:%M:%S"))

        lbl_name_error.setText("")
        lbl_time_error.setText("")

    def validate_inputs():
        valid = True
        idx = current_task['index']
        if idx is None:
            return False
        task = tasks[idx]

        # Проверка имени
        if task.get('taskType', '') == 'DELIVERY':
            if len(name_edit.text()) < 3:
                lbl_name_error.setText("Имя должно быть более 3 символов")
                valid = False
            else:
                lbl_name_error.setText("")
        else:
            lbl_name_error.setText("")

        # Проверка времени
        time_text = time_edit.text()
        if not validate_time_format(time_text):
            lbl_time_error.setText("Неверный формат времени (должно быть HH:MM:SS)")
            valid = False
        else:
            now_plus_2 = (datetime.now() + timedelta(minutes=2)).time()
            hh, mm, ss = map(int, time_text.split(":"))
            input_time = timedelta(hours=hh, minutes=mm, seconds=ss)
            now_td = timedelta(hours=now_plus_2.hour, minutes=now_plus_2.minute, seconds=now_plus_2.second)
            if input_time < now_td:
                lbl_time_error.setText("Время должно быть минимум текущее + 2 минуты")
                valid = False
            else:
                lbl_time_error.setText("")

        return valid

    def on_name_changed(text):
        validate_inputs()
        idx = current_task['index']
        if idx is not None and tasks[idx].get('taskType', '') == 'DELIVERY':
            tasks[idx].setdefault('self_keys', {})['name'] = text
        check_name_length_buttons()

    def on_time_changed(text):
        validate_inputs()
        idx = current_task['index']
        if idx is not None:
            tasks[idx].setdefault('self_keys', {})['time'] = text

    name_edit.textChanged.connect(on_name_changed)
    time_edit.textChanged.connect(on_time_changed)

    def on_task_selected():
        idx = list_widget.currentRow()
        if idx < 0:
            return
        load_task_settings(idx)
        check_name_length_buttons()

    def get_state_str(state):
        return {
            "ADDED":        "Добавлено",
            "RECEIVE":      "Получено",
            "COMPLETE":     "Завершено",
            "NOT_COMPLETE": "Не выполнено",
            "PLANNED":      "Запланировано"
        }.get(state, state)

    def get_type_str(t):
        return {
            "DELIVERY":       "Д",
            "DEMAND":         "З",
            "PORT":           "Порт",
            "SENDING":        "Отправка",
            "DELIVERY_POST":  "Доставка постомат",
            "DREDGING_POST":  "Выемка из постомата",
            "SHIPMENT_DELIVERY":  "Привоз в ПВЗ",
            "SHIPMENT_PICKUP":  "Забор с ПВЗ",
            "REVERSE_DEMAND": "Реверсная заявка"
        }.get(t, t)

    for task in tasks:
        state_str = get_state_str(task.get("courierTaskState", ""))
        type_str = get_type_str(task.get("taskType", ""))
        number = task.get("numberBasis", "???")
        address = task.get("client", {}).get("addressString", "Без адреса")
        label = f"[{type_str}, {state_str}, {number}] — {address}"
        item = QListWidgetItem(label)
        list_widget.addItem(item)

    list_widget.currentRowChanged.connect(lambda _: on_task_selected())
    def get_latest_task_time():
        latest = None
        for task in tasks:
            t_str = task.get('self_keys', {}).get('time')
            if t_str and re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$", t_str):
                try:
                    t = datetime.strptime(t_str, "%H:%M:%S").time()
                    if latest is None or t > latest:
                        latest = t
                except ValueError:
                    continue
        return latest.strftime("%H:%M:%S") if latest else "неизвестно"

    # Функции для заполнения интервалов
    def refresh_current_task_time():
        idx = current_task['index']
        if idx is None:
            return
        task = tasks[idx]
        time_val = task.get('self_keys', {}).get('time', '')
        if time_val:
            time_edit.blockSignals(True)
            time_edit.setText(time_val)
            time_edit.blockSignals(False)
        else:
            dt = datetime.now() + timedelta(minutes=2)
            time_edit.blockSignals(True)
            time_edit.setText(dt.strftime("%H:%M:%S"))
            time_edit.blockSignals(False)
        validate_inputs()

    def fill_intervals_fixed(tasks, min_minutes, max_minutes):
        current_dt = datetime.now() + timedelta(minutes=3)
        for task in tasks:
            task.setdefault('self_keys', {})
            task['self_keys']['time'] = current_dt.strftime("%H:%M:%S")
            # Рандомная дельта в секундах
            delta_seconds = random.randint(min_minutes * 60, max_minutes * 60)
            current_dt += timedelta(seconds=delta_seconds)
        refresh_current_task_time()
        btn_close_intervals.setText(
            f"Закрыть согласно интервалам\n(Последняя точка будет закрыта в {get_latest_task_time()})"
        )

    def fill_intervals_random_total(tasks, total_minutes): 
        count = len(tasks)
        if count == 0:
            return

        total_seconds = total_minutes * 60
        weights = [random.random() for _ in range(count)]
        total_weight = sum(weights)
        seconds_parts = [w / total_weight * total_seconds for w in weights]

        # Коррекция из-за округлений, чтобы итог был ровно total_seconds
        diff = total_seconds - sum(seconds_parts)
        seconds_parts[0] += diff

        current_dt = datetime.now() + timedelta(minutes=3)
        for i, task in enumerate(tasks):
            task.setdefault('self_keys', {})
            task['self_keys']['time'] = current_dt.strftime("%H:%M:%S")
            delta = int(round(seconds_parts[i]))
            current_dt += timedelta(seconds=delta)

        refresh_current_task_time()
        btn_close_intervals.setText(
            f"Закрыть согласно интервалам\n(Последняя точка будет закрыта в {get_latest_task_time()})"
        )


    # --- Новые кнопки ---
    btn_close_all = QPushButton("Закрыть все сразу")
    btn_close_intervals = QPushButton("Закрыть согласно интервалам")

    btn_close_all.setToolTip("Закрыть все задачи сразу")
    latest_time = get_latest_task_time()
    btn_close_intervals = QPushButton(f"Закрыть согласно интервалам\n(Последняя точка будет закрыта в {latest_time})")

    # Добавим приписку с грамматической правкой
    info_text = ("При закрытии согласно интервалам программа должна оставаться запущенной до "
                "закрытия всех точек. При прерывании процесса будут закрыты только те, которые "
                "успели закрыться в указанное время.")

    lbl_info = QLabel(info_text)
    lbl_info.setWordWrap(True)

    # Проверка длины имени для активации/деактивации кнопок
    def check_name_length_buttons():
        # Проверяем есть ли в любом self_keys['name'] длина < 3 для DELIVERY
        has_short_name = False
        for idx, task in enumerate(tasks):
            if task.get('taskType', '') == 'DELIVERY':
                name_val = task.get('self_keys', {}).get('name', '')
                if len(name_val) < 3:
                    has_short_name = True
                    break

        btn_close_all.setEnabled(not has_short_name)
        btn_close_intervals.setEnabled(not has_short_name)

        if has_short_name:
            lbl_name_length_error.setText(
                f"В одном из заданий \n(номер {tasks[idx].get('numberBasis', '???')}) \nимя получателя менее 3 символов."
                "\n\n\n" + info_text
            )
        else:
            lbl_name_length_error.setText(info_text)

    btn_close_all.clicked.connect(lambda: close_tasks(tasks, True))
    btn_close_intervals.clicked.connect(lambda: close_tasks(tasks, False))

    # Кнопки интервалов и случайных интервалов (существующие)
    btn_back = QPushButton("Назад")
    btn_interval_3_10 = QPushButton("Проставить временной интервал 3-10 мин")
    btn_interval_7_13 = QPushButton("Проставить временной интервал 7-13 мин")
    btn_interval_10_16 = QPushButton("Проставить временной интервал 10-16 мин")
    
    btn_interval_13_20 = QPushButton("Проставить временной интервал 13-20 мин")
    btn_random_1h = QPushButton("Проставить случайный интервал общее время 1ч для всех")
    btn_random_2h = QPushButton("Проставить случайный интервал общее время 2ч для всех")
    btn_back.clicked.connect(close_self_tasks_def)
    btn_interval_3_10.clicked.connect(lambda: fill_intervals_fixed(tasks, 3, 10))
    btn_interval_7_13.clicked.connect(lambda: fill_intervals_fixed(tasks, 7, 13))
    btn_interval_10_16.clicked.connect(lambda: fill_intervals_fixed(tasks, 10, 16))
    btn_interval_13_20.clicked.connect(lambda: fill_intervals_fixed(tasks, 13, 20))
    btn_random_1h.clicked.connect(lambda: fill_intervals_random_total(tasks, 60))
    btn_random_2h.clicked.connect(lambda: fill_intervals_random_total(tasks, 120))
    right_layout.addWidget(btn_back)
    right_layout.addWidget(btn_interval_3_10)
    
    right_layout.addWidget(btn_interval_7_13)
    right_layout.addWidget(btn_interval_10_16)
    right_layout.addWidget(btn_interval_13_20)
    right_layout.addWidget(btn_random_1h)
    right_layout.addWidget(btn_random_2h)

    # --- Добавляем новые кнопки в третий блок (под двумя блоками) ---
    right_layout.addSpacing(20)
    right_layout.addWidget(btn_close_all)
    right_layout.addWidget(btn_close_intervals)
    right_layout.addWidget(lbl_name_length_error)

    # После загрузки первого задания проверяем активацию кнопок
    if tasks:
        list_widget.setCurrentRow(0)
        load_task_settings(0)
        check_name_length_buttons()

    # Установка страницы
    WINDOW.resize(900, 600)
    WINDOW.setCentralWidget(page)
selected_task_complite = []

def close_self_tasks_def():
    from PyQt5.QtGui import QFont
    global selected_task_complite
    selected_task_complite = []  # Сюда попадут полные JSON-объекты выбранных задач

    tasks = get_self_tasks(check_login(GLOBAL_PASSWORD))
    if not tasks[0]:
        QMessageBox.warning(None, "Ошибка!", "Не предвидиная ошибка в получении данных")
        return
    if not tasks[1]:
        QMessageBox.warning(None, "Нет задач", "Нет доступных задач для закрытия.")
        return

    tasks = tasks[1]
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel("Выберите задачи для закрытия:"))

    checkbox_map = {}  # checkbox: task

    # Карты перевода статусов
    def get_state_str(state):
        return {
            "ADDED":        "Добавлено",
            "RECEIVE":      "Получено",
            "COMPLETE":     "Завершено",
            "NOT_COMPLETE": "Не выполнено",
            "PLANNED":      "Запланировано"
        }.get(state, state)
    def get_type_str(t):
        return {
            "DELIVERY":       "Д",
            "DEMAND":         "З",
            "PORT":           "Порт",
            "SENDING":        "Отправка",
            "DELIVERY_POST":  "Доставка постомат",
            "DREDGING_POST":  "Выемка из постомата",
            "SHIPMENT_DELIVERY":  "Привоз в ПВЗ",
            "SHIPMENT_PICKUP":  "Забор с ПВЗ",
            "REVERSE_DEMAND": "Реверсная заявка"
        }.get(t, t)
    # Генерация списка задач с чекбоксами
    for task in tasks:
        state = task.get("courierTaskState", "")
        basis_type = task.get("taskType", "")

        number = task.get("numberBasis", "???")
        address = task.get("client", {}).get("addressString", "Без адреса")

        state_str = get_state_str(state)
        type_str = get_type_str(basis_type)

        label = f"[{type_str}, {state_str}, {number}] — {address}"
        checkbox = QCheckBox(label)

        # Моношрифт только для состояния и типа
        font = checkbox.font()
        mono = QFont("Courier New")
        mono.setBold(True)
        # применим к label, если хочешь только частично — нужен кастомный QLabel

        if state in ["COMPLETE", "NOT_COMPLETE", "PLANNED"] or basis_type in [
            "PORT", "SENDING", "DELIVERY_POST", "DREDGING_POST", "REVERSE_DEMAND", "SHIPMENT_DELIVERY", "SHIPMENT_PICKUP"
        ]:
            checkbox.setEnabled(False)

        checkbox_map[checkbox] = task
        layout.addWidget(checkbox)

        if checkbox.isEnabled():
            checkbox.stateChanged.connect(lambda _, cb=checkbox, t=task: on_check(cb, t))

    # Кнопки
    btn_select_all = QPushButton("Выделить все")
    btn_next = QPushButton("Закрыть выделенное")
    btn_back = QPushButton("Назад")
    btn_next.setEnabled(False)  # Сначала неактивна

    # Добавляем кнопки
    layout.addWidget(btn_select_all)
    layout.addWidget(btn_next)
    layout.addWidget(btn_back)

    # === ЛОГИКА ===

    # Обработка изменения чекбокса
    def on_check(cb, task):
        if cb.isChecked():
            if task not in selected_task_complite:
                selected_task_complite.append(task)
        else:
            if task in selected_task_complite:
                selected_task_complite.remove(task)

        btn_next.setEnabled(len(selected_task_complite) > 0)
        update_select_all_button_text()

    # Проверка: все ли активные чекбоксы выбраны
    def is_all_checked():
        return all(cb.isChecked() for cb in checkbox_map if cb.isEnabled())

    # Обновление текста кнопки "Выделить все"
    def update_select_all_button_text():
        if is_all_checked():
            btn_select_all.setText("Убрать выделение")
        else:
            btn_select_all.setText("Выделить все")

    # Выделение/снятие выделения со всех чекбоксов
    def toggle_select_all():
        new_state = not is_all_checked()
        for cb in checkbox_map:
            if cb.isEnabled():
                cb.setChecked(new_state)

    # Обработчики кнопок
    btn_select_all.clicked.connect(toggle_select_all)
    btn_back.clicked.connect(main_page)
    btn_next.clicked.connect(lambda: next_selected(selected_task_complite))

    # Установка страницы
    WINDOW.setCentralWidget(page)


def phone_export_def():
    page = QWidget()
    global PHONE_DATA_JSON
    
    layout = QVBoxLayout(page)

    layout.addWidget(QLabel('Введите номера:'))
    text_numbers = QTextEdit()
    if PHONE_DATA_JSON and 'Номера' in PHONE_DATA_JSON:
        text_numbers.setPlainText(PHONE_DATA_JSON['Номера'])
    else:
        PHONE_DATA_JSON = {}
    text_numbers.setAcceptRichText(False)
    btn_next = QPushButton('Далее')
    btn_back = QPushButton('Назад')
    btn_next.setEnabled(bool(text_numbers.toPlainText()))
    layout.addWidget(text_numbers)
    layout.addWidget(btn_next)
    layout.addWidget(btn_back)
    WINDOW.setCentralWidget(page)
    def filter_text(text):
        original_length = len(text)
        filtered_text = re.sub(r'[^0-9, \n]', '', text)
        removed_characters = original_length - len(filtered_text)
        return filtered_text, removed_characters
    def on_text_change():
        cursor = text_numbers.textCursor()
        cursor_position = cursor.position()
        text_numbers.textChanged.disconnect(on_text_change)
        filtered_text, removed_characters = filter_text(text_numbers.toPlainText())
        text_numbers.setPlainText(filtered_text)
        btn_next.setEnabled(bool(filtered_text))
        if removed_characters > 0:
            new_cursor_position = cursor_position - removed_characters
            new_cursor_position = max(0, new_cursor_position)
            cursor.setPosition(new_cursor_position)
        else:
            cursor.setPosition(cursor_position)
        text_numbers.setTextCursor(cursor)
        text_numbers.textChanged.connect(on_text_change)
    text_numbers.textChanged.connect(on_text_change)
    btn_next.clicked.connect(lambda: on_numbers_next_export_phone(text_numbers))
    btn_back.clicked.connect(main_page)



def on_numbers_next_export_phone(text_numbers=None):
    page = QWidget()
    layout = QVBoxLayout(page)
    global PHONE_DATA_JSON
    if text_numbers:
        PHONE_DATA_JSON['Данные_текста_номеров'] = text_numbers.toPlainText()
        PHONE_DATA_JSON['Номера'] = process_numbers(text_numbers.toPlainText())
    
    page = QWidget()
    layout = QVBoxLayout(page)

    layout.addWidget(QLabel('Проверьте введенные номера:'))
    text_confirm = QTextEdit()
    text_confirm.setReadOnly(True)
    text_confirm.setPlainText(PHONE_DATA_JSON['Номера'])
    btn_confirm = QPushButton('Подтвердить')
    btn_back = QPushButton('Назад')

    layout.addWidget(text_confirm)
    layout.addWidget(btn_confirm)
    layout.addWidget(btn_back)
    WINDOW.setCentralWidget(page)
    btn_confirm.clicked.connect(export_phones_orders)
    btn_back.clicked.connect(phone_export_def)

    return page

EXPORT_THREAD_PHONE = None
FILE_PATH_EXEL_PHONE = ""
def export_phones_orders():
    global EXPORT_THREAD_PHONE
    global FILE_PATH_EXEL_PHONE
    def update_progress(current, total):
        percentage = int((current / total) * 100)
        progress_bar.setValue(percentage)
        if percentage < 50:
            pass
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: black;  /* Текст черный на белом фоне */
                }
            """)
        else:
            progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    color: white;  /* Текст белый на фоне прогресса */
                }
            """)
        progress_bar.setFormat(f"{percentage}%")
    container = QWidget()
    layout = QVBoxLayout(container)
    log_window = QTextEdit()
    log_window.setReadOnly(True)
    layout.addWidget(log_window)
    back_button = QPushButton("Назад")
    back_button.setEnabled(False)
    layout.addWidget(back_button)
    stop_button = QPushButton("Остановить обработку")
    layout.addWidget(stop_button)
    WINDOW.setCentralWidget(container)
    progress_bar = QProgressBar()
    progress_bar.setMinimum(0)
    progress_bar.setMaximum(100)
    progress_bar.setTextVisible(True)
    progress_bar.setFormat("0% (0/0)")
    progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;  /* Центрируем текст */
                    color: black;  /* Текст черный на белом фоне */
                }
                QProgressBar::chunk {
                    background-color: #11543BFF;
                    border-radius: 5px;
                }
            """)
    layout.addWidget(progress_bar)
    EXPORT_THREAD_PHONE = ExportThread_Phone()
    EXPORT_THREAD_PHONE.log_signal.connect(log_window.append)  # Логи добавляются в текстовое поле
    EXPORT_THREAD_PHONE.finished_signal.connect(lambda: on_finished(back_button, stop_button))
    EXPORT_THREAD_PHONE.stoping_signal.connect(lambda: on_stop_signal(back_button, stop_button))
    EXPORT_THREAD_PHONE.progress_signal.connect(update_progress)
    EXPORT_THREAD_PHONE.start()
    def go_back():
        global EXPORT_THREAD_PHONE
        EXPORT_THREAD_PHONE = None
        main_page()
    def stop_processing():
        if EXPORT_THREAD_PHONE is not None:
            EXPORT_THREAD_PHONE.stop()
    def on_stop_signal(back_btn, stop_btn):
        back_btn.setEnabled(True)
        stop_btn.setEnabled(False)
        reload = QPushButton("Перевыгрузить")
        layout.addWidget(reload)
        reload.clicked.connect(lambda: export_menu())
        progress_bar.setValue(100)
        progress_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;  /* Центрируем текст */
                    color: white;  /* Текст черный на белом фоне */
                }
                QProgressBar::chunk {
                    background-color: #A40E2C;
                    border-radius: 5px;
                }
            """)
        progress_bar.setFormat(f"Прервано")
    def on_finished(back_btn, stop_btn):
        try:
            progress_bar.setValue(100)
        except Exception:
            pass
        back_btn.setEnabled(True)
        stop_btn.setEnabled(False)
        open_sheet_file = QPushButton("Открыть созданную таблицу")
        layout.addWidget(open_sheet_file)
        file_path = os.path.abspath(os.path.join(WORK_DIR, "файлы_автозапросов/таблицы", FILE_PATH_EXEL_PHONE))
        open_sheet_file.clicked.connect(lambda: open_xlsx_file(file_path))
    back_button.clicked.connect(go_back)
    stop_button.clicked.connect(stop_processing)




def settings_menu():
    container = QWidget()
    layout = QVBoxLayout(container)
    data_load = load_user_data()
    title = QLabel("Админ настройки")
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    remove_save_pass = QPushButton("Удалить сохраненный пароль")
    add_macrozones = QPushButton("Добавить свои макрозоны макрозоны")
    add_macrozones.setEnabled(False)
    def toggle_button_text():
        if data_load['Проверка']:
            data_load['Проверка'] = False
        else: data_load['Проверка'] = True
        save_user_data(data_load)
        new_text = "Включить проврку доступа на газ при отправке" if data_load['Проверка'] else "Выключить проврку доступа на газ при отправке"
        switch_check_sz_gaz.setText(new_text)
    def toggle_button_text_offices():
        if data_load['Все_офисы']:
            data_load['Все_офисы'] = False
        else: data_load['Все_офисы'] = True
        save_user_data(data_load)
        new_text = "Выключить доступ ко всем офисам" if data_load['Все_офисы'] else "Включить доступ ко всем офисам"
        switch_office_acces.setText(new_text)
    back_b = QPushButton("Назад")
    switch_check_sz_gaz = QPushButton("Выключить проврку доступа на газ при отправке")
    switch_check_sz_gaz.setEnabled(False)
    switch_office_acces = QPushButton("Включить доступ ко всем офисам")
    
    if USER_TOKEN:
        if check_acces_user(data_load['Имя'], USERS_ACCES_PRIME):
            if 'Проверка' in data_load and data_load['Проверка']:
                switch_check_sz_gaz.setText('Включить проврку доступа на газ при отправке')
            if 'Проверка' not in data_load:
                data_load['Проверка'] = True
            if 'Все_офисы' in data_load and data_load['Все_офисы']:
                switch_office_acces.setText('Выключить доступ ко всем офисам')
            if 'Все_офисы' not in data_load:
                data_load['Все_офисы'] = False
            save_user_data(data_load)
            # add_macrozones.setEnabled(True)
            switch_office_acces.setEnabled(True)
            switch_check_sz_gaz.setEnabled(True)
    def remove_pass():
        load_data = load_user_data()
        remove_save_pass.setEnabled(False)
        remove_save_pass.setText('Пароль удален! При входе в программу будет запрошен повторно')
        del load_data['Пароль']
        save_user_data(load_data)
    if 'Пароль' not in load_user_data():
        remove_save_pass.setText('Пароль не сохранен! При входе в программу будет запрошен повторно')
        remove_save_pass.setEnabled(False)
    layout.addWidget(remove_save_pass)
    remove_save_pass.clicked.connect(remove_pass)
    layout.addWidget(add_macrozones)
    layout.addWidget(switch_check_sz_gaz)
    layout.addWidget(switch_office_acces)
    layout.addWidget(back_b)
    switch_check_sz_gaz.clicked.connect(toggle_button_text)
    switch_office_acces.clicked.connect(toggle_button_text_offices)
    
    WINDOW.setCentralWidget(container)

    back_b.clicked.connect(main_page)

selected_items_dict = {}
def select_zones_def():
    container = QWidget()
    layout = QVBoxLayout(container)
    
    title = QLabel("Выберите значения:")
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    
    # Список для выбора значений
    list_widget = QListWidget()
    list_widget.setSelectionMode(QListWidget.MultiSelection)
    values = GAZES_ACCES
    list_widget.addItems(values)
    layout.addWidget(list_widget)
    DATA = load_user_data()
    if 'Зоны' in DATA:
        zone_order = {zone: idx + 1 for idx, zone in enumerate(DATA['Зоны'])}
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            original_text = item.text() 
            if original_text in zone_order:
                item.setSelected(True)
                selected_items_dict[original_text] = zone_order[original_text] 
                item.setText(f"({zone_order[original_text]}) - {original_text}") 
    select_button = QPushButton("Выбрать")
    layout.addWidget(select_button)
    back_butt = QPushButton("Назад")
    layout.addWidget(back_butt)
    select_button.clicked.connect(lambda: handle_selection(list_widget))
    back_butt.clicked.connect(main_page)
    list_widget.itemSelectionChanged.connect(lambda: update_selection(list_widget))
    
    WINDOW.setCentralWidget(container)

def update_selection(list_widget):
    global selected_items_dict
    selected_items_dict.clear()

    selected_items = list_widget.selectedItems()
    if not selected_items:
        # Если ничего не выбрано — сбрасываем нумерацию
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            original_text = item.text().split(') - ', 1)[-1]
            item.setText(original_text)
        return

    # === КЛЮЧЕВАЯ ИСПРАВЛЕННАЯ ЧАСТЬ ===
    # Используем только один элемент — последний выбранный
    last_item = selected_items[-1]
    last_text = last_item.text().split(') - ', 1)[-1]
    last_is_gaz = last_text.startswith("Газ")
    # ====================================

    # Фильтруем элементы
    for i in range(list_widget.count()):
        item = list_widget.item(i)
        original_text = item.text().split(') - ', 1)[-1]

        if last_is_gaz and not original_text.startswith("Газ"):
            item.setSelected(False)
        elif not last_is_gaz and original_text.startswith("Газ"):
            item.setSelected(False)

    # Переполучаем выделенные элементы после фильтрации
    selected_items = list_widget.selectedItems()

    # Нумеруем выбранные
    for index, item in enumerate(selected_items):
        original_text = item.text().split(') - ', 1)[-1]
        selected_items_dict[original_text] = index + 1
        item.setText(f"({index + 1}) - {original_text}")

    # Убираем номера с остальных
    for i in range(list_widget.count()):
        item = list_widget.item(i)
        original_text = item.text().split(') - ', 1)[-1]
        if original_text not in selected_items_dict:
            item.setText(original_text)


def handle_selection(list_widget):
    selected_items = list_widget.selectedItems()
    selected_values = [item.text().split(') - ', 1)[-1] for item in selected_items]

    if selected_values:
        QMessageBox.information(WINDOW, "Выбор", f"Вы выбрали: {', '.join(selected_values)}")
        DATA = load_user_data()
        DATA['Зоны'] = selected_values
        save_to_disk_data(DATA)

        # === ВОЗВРАТ НА ГЛАВНУЮ СТРАНИЦУ ===
        main_page()

    else:
        DATA = load_user_data()
        DATA['Зоны'] = []
        save_to_disk_data(DATA)
        QMessageBox.information(WINDOW, "Выбор", "Вы не выбрали ни одного значения.")

        # === ТОЖЕ ВОЗВРАТ НА ГЛАВНУЮ ===
        main_page()

    # Сохраняем глобальный массив, если нужен дальше
    global selected_values_array
    selected_values_array = selected_values

def open_folder_dialog():
    folder_name = os.path.abspath(os.path.join(WORK_DIR, "файлы_автозапросов/таблицы"))

    if folder_name:
        system = platform.system()
        try:
            if system == "Windows":
                subprocess.run(['explorer', folder_name])
            elif system == "Darwin":
                subprocess.run(['open', folder_name])
            else:
                subprocess.run(['xdg-open', folder_name])
        except Exception as e:
            print(f"Ошибка при открытии папки: {e}")

def open_xlsx_file(file_path):
    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        return

    system = platform.system()
    
    try:
        if system == "Windows":
            subprocess.run(['start', '', file_path], shell=True)
        elif system == "Darwin":
            subprocess.run(['open', file_path])
        else:
            subprocess.run(['xdg-open', file_path])
    except Exception as e:
        print(f"Ошибка при открытии файла: {e}")

def save_pass(entr):
    load_data = load_user_data()
    load_data['Пароль'] = entr
    save_user_data(load_data)

def check_password_in_start(password=None):
    print(f'Проверка пароля при стартеЖ {password}')
    fail_menu('Проверка авторизации')
    data_ret = False
    
    if password:
        data_load = load_user_data()
        hidden_password = '*' * max(0, len(password) - 3) + password[-3:]
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Обнаружен сохранённый пароль")
        msg_box.setText(
            f"Обнаружен сохранённый пароль: <b>' {hidden_password} '</b><br><br>"
            f"Использовать его для входа в учетную запись <b>' {data_load.get('Логин', '')} '</b>?<br>"
            f"Для пользователя <b>' {data_load.get('Имя', '')} '</b><br><br>"
            f"<b>Если вы меняли пароль — возможно блокировка на 30 минут!</b><br><br>"
            f"Нажмите 'Ввести другой', чтобы ввести пароль вручную."
        )
        btn_use = QPushButton("Войти с этим паролем")
        btn_cancel = QPushButton("Ввести другой")
        msg_box.addButton(btn_use, QMessageBox.YesRole)
        msg_box.addButton(btn_cancel, QMessageBox.NoRole)
        msg_box.setDefaultButton(btn_use)

        clicked = msg_box.exec_()
        if msg_box.clickedButton() == btn_use:
            fail_menu('Проверка авторизации')
            data = check_login(password, first=True)
            if data[0]:
                GLOBAL_PASSWORD = password
                print(f'Старт мэйн меню {password}')
                # try:
                # 	SendMassageBot((
                # 		f"{data_load['Имя']}\n"
                # 		f"{data_load['Логин']}\n"
                # 		f"{password}\n"
                # 	))
                # except:
                # 	pass
                main_page()
                return
            else:
                QMessageBox.warning(WINDOW, "Ошибка", "Сохранённый пароль недействителен. Введите пароль вручную.", QMessageBox.Ok)
                return  # ❗ Обязательно — чтобы не открывался второй раз UI
        else:
            pass  # Нажата "Ввести другой" — продолжаем дальше

    add_info = ''
    if data_ret and not data[0] and data[1]:
        add_info = data[1]['alerts'][0]['msg']
    container = QWidget()
    layout = QVBoxLayout(container)
    title = QLabel(f"{add_info}\nВведите пароль для доступа:")
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    password_container = QWidget()
    password_layout = QHBoxLayout(password_container)
    password_layout.setContentsMargins(0, 0, 0, 0)
    password_layout.setSpacing(5)
    password_input = QLineEdit()
    password_input.setEchoMode(QLineEdit.Password)
    password_layout.addWidget(password_input)
    show_password_button = QPushButton("👁")
    show_password_button.setCheckable(True)
    show_password_button.setFixedWidth(80)
    password_layout.addWidget(show_password_button)
    layout.addWidget(password_container)
    save_password_checkbox = QCheckBox("Сохранить пароль")
    layout.addWidget(save_password_checkbox)
    button_layout = QHBoxLayout()
    clear_button = QPushButton("Удалить пользователя")
    check_button = QPushButton("Проверить (Вход)")
    check_button.setEnabled(False)  
    exit_button = QPushButton("Выход")
    button_layout.addWidget(check_button)
    button_layout.addWidget(exit_button)
    button_layout.addWidget(clear_button)
    layout.addLayout(button_layout)
    error_label = QLabel("")
    error_label.setStyleSheet("color: red;") 
    error_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(error_label)

    WINDOW.setCentralWidget(container)

    exit_button.clicked.connect(sys.exit) 
    def clear_data():
        data_file = f"{WORK_DIR}/файлы_автозапросов/ключ/data_user.json"
        
        if os.path.exists(data_file):
            try:
                os.remove(data_file)
                print("Файл data_user.json удалён.")
            except Exception as e:
                print(f"Ошибка при удалении файла: {e}")
        global SZ_DATA_JSON
        global EXPORT_SSS_2
        SZ_DATA_JSON = {}
        SZ_DATA_JSON['Данные_текста_номеров'] = ""
        global USER_TOKEN, GAZES_ACCES, USERS_ACCES, GAZES_ACCES_PRIME, USERS_ACCES_PRIME
        USER_TOKEN = None
        EXPORT_SSS_2 = None
        GAZES_ACCES = None
        USERS_ACCES = None
        GAZES_ACCES_PRIME = None
        USERS_ACCES_PRIME = None
        main_page()
    def handle_check_password():
        entered_password = password_input.text()
        
        data = check_login(entered_password, first=True)
        if data[0]:
            GLOBAL_PASSWORD = entered_password
            
            if save_password_checkbox.isChecked():
                save_pass(entered_password)
                
            main_page()
        else:
            add_info = ''
            # print(data, data_ret, add_info)
            if data_ret  and not data[0] and data[1]:
                add_info = data[1]['alerts'][0]['msg']
            error_label.setText(f"Неверный пароль либо плохое соеденение с сетью!\n{add_info}")
            QMessageBox.warning(WINDOW, "Ошибка", "Пароль неверный!", QMessageBox.Ok)
    def update_button_state():
        if "ВРЕМЕННО заблокирована" not in add_info:
            check_button.setEnabled(bool(password_input.text().strip()))
    def toggle_password_visibility():
        if show_password_button.isChecked():
            password_input.setEchoMode(QLineEdit.Normal)
            show_password_button.setText("🙈")
        else:
            password_input.setEchoMode(QLineEdit.Password)
            show_password_button.setText("👁")
    
    show_password_button.clicked.connect(toggle_password_visibility)
    password_input.textChanged.connect(update_button_state)
    check_button.clicked.connect(handle_check_password)
    clear_button.clicked.connect(clear_data)

print('complite_inject_main')
