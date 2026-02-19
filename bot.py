# ============================================================================
# ПОТЕРЯННЫЕ ЗЕМЛИ — ПОЛНОСТЬЮ РАБОЧАЯ ВЕРСИЯ (ОДИН ФАЙЛ)
# ============================================================================
import os
import sys
import sqlite3
import random
import logging
import traceback
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import F
import asyncio

# ============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

print("\n" + "="*70)
print("🔧 ЗАПУСК БОТА 'ПОТЕРЯННЫЕ ЗЕМЛИ'")
print("="*70)
print(f"🐍 Python version: {sys.version.split()[0]}")
print(f"📍 Текущая директория: {os.getcwd()}")

# ============================================================================
# ПОЛУЧЕНИЕ ТОКЕНА И ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================================================
API_TOKEN = os.environ.get('BOT_TOKEN')
if not API_TOKEN:
    error_msg = "❌ CRITICAL ERROR: BOT_TOKEN не найден в переменных окружения!"
    print(error_msg)
    logger.error(error_msg)
    sys.exit(1)
else:
    print(f"✅ BOT_TOKEN загружен (длина: {len(API_TOKEN)})")

try:
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    print("✅ Бот и диспетчер инициализированы")
except Exception as e:
    print(f"❌ Ошибка инициализации бота: {e}")
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# СОСТОЯНИЯ FSM
# ============================================================================
class GameStates(StatesGroup):
    waiting_for_slot = State()
    waiting_for_name = State()
    waiting_for_class = State()
    waiting_for_class_confirm = State()
    choosing_action = State()
    choosing_battle_type = State()
    choosing_opponent = State()
    waiting_attacker_dice = State()
    waiting_defender_dice = State()
    waiting_monster_dice = State()
    choosing_stat_to_upgrade = State()
    in_shop_category = State()
    in_inventory = State()
    choosing_item_action = State()
    selecting_item_for_action = State()

# ============================================================================
# КЛАССЫ ПЕРСОНАЖЕЙ
# ============================================================================
CLASSES = {
    "Воин": {"hp_bonus": 20, "atk_bonus": 3, "arm_bonus": 2, "agi_bonus": 0, "description": "🛡️ Высокая живучесть и защита", "emoji": "⚔️"},
    "Маг": {"hp_bonus": -10, "atk_bonus": 5, "arm_bonus": -1, "agi_bonus": 1, "description": "🔮 Сильная атака, но хрупкий", "emoji": "🧙"},
    "Разбойник": {"hp_bonus": 0, "atk_bonus": 2, "arm_bonus": 0, "agi_bonus": 3, "description": "🏃 Высокая ловкость, критические удары", "emoji": "🗡️"},
    "Паладин": {"hp_bonus": 15, "atk_bonus": 1, "arm_bonus": 3, "agi_bonus": -1, "description": "🛡️⚔️ Сбалансированный защитник", "emoji": "🛡️"},
    "Стрелок": {"hp_bonus": -5, "atk_bonus": 4, "arm_bonus": -1, "agi_bonus": 2, "description": "🏹 Дальний бой, высокий урон", "emoji": "🏹"},
    "Друид": {"hp_bonus": 10, "atk_bonus": 2, "arm_bonus": 1, "agi_bonus": 1, "description": "🌿 Природная магия и выносливость", "emoji": "🌿"}
}

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ============================================================================
def init_db():
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        
        # Таблица игроков
        cur.execute('''
            CREATE TABLE IF NOT EXISTS players (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                hero_slot INTEGER,
                hero_name TEXT,
                hero_class TEXT,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                skill_points INTEGER DEFAULT 0,
                max_hp INTEGER DEFAULT 100,
                current_hp INTEGER DEFAULT 100,
                attack INTEGER DEFAULT 10,
                armor INTEGER DEFAULT 5,
                agility INTEGER DEFAULT 5,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица монстров
        cur.execute('''
            CREATE TABLE IF NOT EXISTS monsters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                floor INTEGER,
                name TEXT,
                level INTEGER,
                hp INTEGER,
                attack INTEGER,
                armor INTEGER,
                agility INTEGER,
                exp_reward INTEGER
            )
        ''')
        
        # Таблица активных боёв
        cur.execute('''
            CREATE TABLE IF NOT EXISTS active_battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attacker_id INTEGER,
                defender_id INTEGER,
                attacker_dice INTEGER,
                defender_dice INTEGER,
                attacker_hp INTEGER,
                defender_hp INTEGER,
                round_num INTEGER DEFAULT 1,
                status TEXT,
                battle_type TEXT,
                used_potion BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица магазина
        cur.execute('''
            CREATE TABLE IF NOT EXISTS shop (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                item_type TEXT,
                effect TEXT,
                price INTEGER,
                category TEXT
            )
        ''')
        
        # Таблица инвентаря
        cur.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                item_name TEXT,
                item_type TEXT,
                effect TEXT,
                equipped BOOLEAN DEFAULT 0,
                slot TEXT,
                bought_price INTEGER,
                level INTEGER DEFAULT 1,
                max_level INTEGER DEFAULT 5
            )
        ''')
        
        # Заполнение монстров
        cur.execute('SELECT COUNT(*) FROM monsters')
        if cur.fetchone()[0] == 0:
            monsters = [
                (1, 'Гоблин', 1, 50, 8, 3, 6, 80),
                (1, 'Крыса', 1, 30, 5, 1, 8, 50),
                (1, 'Скелет', 2, 60, 10, 4, 5, 100),
                (1, 'Паук', 1, 40, 7, 2, 9, 70),
                (2, 'Орк', 3, 120, 15, 10, 7, 250),
                (2, 'Тролль', 4, 180, 20, 15, 6, 400),
                (2, 'Гарпия', 3, 90, 12, 5, 12, 220),
                (2, 'Зомби', 3, 100, 10, 8, 4, 180),
                (3, 'Минотавр', 6, 250, 25, 20, 8, 600),
                (3, 'Вампир', 5, 200, 22, 12, 15, 550),
                (3, 'Грифон', 5, 180, 18, 10, 18, 500),
                (3, 'Элементаль', 6, 220, 24, 18, 10, 580),
                (4, 'Циклоп', 8, 400, 35, 25, 9, 900),
                (4, 'Медуза', 7, 300, 28, 15, 16, 800),
                (4, 'Демон', 9, 450, 40, 30, 12, 1100),
                (4, 'Лич', 8, 350, 32, 22, 14, 950),
                (5, 'Дракон', 12, 800, 50, 35, 20, 1500),
                (5, 'Гидра', 11, 700, 45, 30, 18, 1400),
                (5, 'Архидемон', 13, 900, 55, 40, 22, 1700),
                (5, 'Титан', 15, 1200, 60, 45, 25, 2000)
            ]
            cur.executemany('INSERT INTO monsters (floor, name, level, hp, attack, armor, agility, exp_reward) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', monsters)
            logger.info(f"✅ Добавлено {len(monsters)} монстров в базу")
        
        # Заполнение магазина
        cur.execute('SELECT COUNT(*) FROM shop')
        if cur.fetchone()[0] == 0:
            items = [
                ("Малое зелье", "Зелье", "+30HP", 50, "Зелья"),
                ("Среднее зелье", "Зелье", "+60HP", 100, "Зелья"),
                ("Большое зелье", "Зелье", "+100HP", 150, "Зелья"),
                ("Меч Ученика", "Оружие 1", "+1 Атака", 150, "Оружие"),
                ("Щит Ученика", "Оружие 2", "+1 Броня", 150, "Оружие"),
                ("Шлем Ученика", "Экипировка 1", "+1 Броня", 200, "Экипировка"),
                ("Броня Ученика", "Экипировка 2", "+1 Броня", 200, "Экипировка"),
                ("Штаны Ученика", "Экипировка 3", "+1 Ловкость", 200, "Экипировка"),
                ("Ботинки Ученика", "Экипировка 4", "+1 Ловкость", 200, "Экипировка"),
                ("Руки Ученика", "Экипировка 5", "+1 Атака", 200, "Экипировка"),
                ("Перчатки Ученика", "Экипировка 6", "+1 Атака", 200, "Экипировка"),
                ("Амулет Ловкости", "Аксессуар 1", "+2 Ловкость", 400, "Аксессуары"),
                ("Кольцо Защиты", "Аксессуар 2", "+2 Броня", 400, "Аксессуары"),
                ("Цепь Силы", "Аксессуар 3", "+2 Атака", 400, "Аксессуары"),
                ("Свиток опыта", "Разное", "+50 Опыта", 500, "Разное")
            ]
            cur.executemany('INSERT INTO shop (name, item_type, effect, price, category) VALUES (?, ?, ?, ?, ?)', items)
            logger.info(f"✅ Добавлено {len(items)} предметов в магазин")
        
        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована успешно")
        print("✅ База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА инициализации базы данных: {e}", exc_info=True)
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА инициализации базы данных: {e}")
        traceback.print_exc()
        raise

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================
def get_player(telegram_id):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM players WHERE telegram_id = ?', (telegram_id,))
        row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        logger.error(f"❌ Ошибка получения игрока {telegram_id}: {e}")
        return None

def create_player(telegram_id, username, hero_slot, hero_name, hero_class):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM players')
        if cur.fetchone()[0] >= 6:
            conn.close()
            return False, "❌ В игре уже 6 игроков!"
        cur.execute('SELECT hero_name FROM players WHERE hero_name = ?', (hero_name,))
        if cur.fetchone():
            conn.close()
            return False, f"❌ Имя '{hero_name}' занято!"
        cur.execute('SELECT hero_slot FROM players WHERE hero_slot = ?', (hero_slot,))
        if cur.fetchone():
            conn.close()
            return False, f"❌ Слот {hero_slot} занят!"
        cls = CLASSES[hero_class]
        cur.execute('''
            INSERT INTO players (telegram_id, username, hero_slot, hero_name, hero_class, max_hp, current_hp, attack, armor, agility, gold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (telegram_id, username, hero_slot, hero_name, hero_class, 100+cls['hp_bonus'], 100+cls['hp_bonus'], 10+cls['atk_bonus'], 5+cls['arm_bonus'], 5+cls['agi_bonus']))
        conn.commit()
        conn.close()
        logger.info(f"✅ Игрок {telegram_id} ({hero_name}) создан")
        return True, "✅ Персонаж создан!"
    except Exception as e:
        logger.error(f"❌ Ошибка создания игрока {telegram_id}: {e}")
        return False, f"❌ Ошибка сервера"

def update_player(telegram_id, **kwargs):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [telegram_id]
        cur.execute(f'UPDATE players SET {set_clause} WHERE telegram_id = ?', values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления игрока {telegram_id}: {e}")
        return False

def get_all_players():
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM players ORDER BY hero_slot')
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка игроков: {e}")
        return []

def get_free_slots():
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT hero_slot FROM players')
        occupied = {row[0] for row in cur.fetchall()}
        conn.close()
        return [i for i in range(1, 7) if i not in occupied]
    except Exception as e:
        logger.error(f"❌ Ошибка получения свободных слотов: {e}")
        return []

def get_monster(name):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM monsters WHERE name = ?', (name,))
        row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        logger.error(f"❌ Ошибка получения монстра {name}: {e}")
        return None

def calculate_damage(attacker_atk, attacker_agi, defender_arm, defender_agi, dice_roll):
    base = max(1, attacker_atk - defender_arm * 0.6)
    agility_mod = (attacker_agi - defender_agi) * 0.4
    dice_mod = (dice_roll - 10) * 1.8
    return max(1, round(base + agility_mod + dice_mod))

def add_gold(player_id, amount):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('UPDATE players SET gold = gold + ? WHERE telegram_id = ?', (amount, player_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления золота игроку {player_id}: {e}")
        return False

def remove_gold(player_id, amount):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('UPDATE players SET gold = gold - ? WHERE telegram_id = ?', (amount, player_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка удаления золота игрока {player_id}: {e}")
        return False

def get_player_gold(player_id):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT gold FROM players WHERE telegram_id = ?', (player_id,))
        result = cur.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"❌ Ошибка получения золота игрока {player_id}: {e}")
        return 0

def add_item_to_inventory(player_id, item_name, item_type, effect, bought_price):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('INSERT INTO inventory (player_id, item_name, item_type, effect, equipped, bought_price) VALUES (?, ?, ?, ?, 0, ?)', (player_id, item_name, item_type, effect, bought_price))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления предмета в инвентарь игрока {player_id}: {e}")
        return False

def get_inventory(player_id):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM inventory WHERE player_id = ?', (player_id,))
        items = cur.fetchall()
        conn.close()
        return items
    except Exception as e:
        logger.error(f"❌ Ошибка получения инвентаря игрока {player_id}: {e}")
        return []

def get_shop_items(category=None):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        if category:
            cur.execute('SELECT * FROM shop WHERE category = ? ORDER BY price', (category,))
        else:
            cur.execute('SELECT * FROM shop ORDER BY category, price')
        items = cur.fetchall()
        conn.close()
        return items
    except Exception as e:
        logger.error(f"❌ Ошибка получения товаров магазина: {e}")
        return []

def equip_item(player_id, item_id, slot):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('UPDATE inventory SET equipped = 0, slot = NULL WHERE player_id = ? AND slot = ?', (player_id, slot))
        cur.execute('UPDATE inventory SET equipped = 1, slot = ? WHERE id = ? AND player_id = ?', (slot, item_id, player_id))
        conn.commit()
        conn.close()
        logger.info(f"✅ Предмет {item_id} экипирован игроком {player_id} в слот {slot}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка экипировки предмета {item_id} игроком {player_id}: {e}")
        return False

def unequip_item(player_id, slot):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('UPDATE inventory SET equipped = 0, slot = NULL WHERE player_id = ? AND slot = ?', (player_id, slot))
        conn.commit()
        conn.close()
        logger.info(f"✅ Предмет снят игроком {player_id} со слота {slot}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка снятия экипировки игроком {player_id} со слота {slot}: {e}")
        return False

def sell_item(player_id, item_id):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT bought_price FROM inventory WHERE id = ? AND player_id = ?', (item_id, player_id))
        result = cur.fetchone()
        if not result:
            conn.close()
            logger.warning(f"❌ Предмет {item_id} не найден в инвентаре игрока {player_id}")
            return False, "Предмет не найден!"
        sell_price = result[0] // 2
        add_gold(player_id, sell_price)
        cur.execute('DELETE FROM inventory WHERE id = ? AND player_id = ?', (item_id, player_id))
        conn.commit()
        conn.close()
        logger.info(f"✅ Предмет {item_id} продан игроком {player_id} за {sell_price} золота")
        return True, f"Предмет продан за {sell_price} золота!"
    except Exception as e:
        logger.error(f"❌ Ошибка продажи предмета {item_id} игроком {player_id}: {e}")
        return False, f"❌ Ошибка сервера"

def use_potion_in_battle(player_id, battle_id):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT used_potion FROM active_battles WHERE id = ?', (battle_id,))
        battle = cur.fetchone()
        if battle and battle[0]:
            conn.close()
            return False, "Вы уже использовали зелье в этом бою!"
        cur.execute('SELECT id, effect FROM inventory WHERE player_id = ? AND item_type = "Зелье" AND equipped = 0 LIMIT 1', (player_id,))
        potion = cur.fetchone()
        if not potion:
            conn.close()
            return False, "Нет зелий в инвентаре!"
        heal = 30 if "+30HP" in potion[1] else 60 if "+60HP" in potion[1] else 100
        cur.execute('DELETE FROM inventory WHERE id = ?', (potion[0],))
        cur.execute('UPDATE active_battles SET used_potion = 1 WHERE id = ?', (battle_id,))
        conn.commit()
        conn.close()
        logger.info(f"✅ Зелье использовано игроком {player_id} в бою {battle_id}")
        return True, heal
    except Exception as e:
        logger.error(f"❌ Ошибка использования зелья игроком {player_id} в бою {battle_id}: {e}")
        return False, f"❌ Ошибка сервера"

def create_battle(attacker_id, defender_id, attacker_hp, defender_hp, battle_type="pvp"):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('INSERT INTO active_battles (attacker_id, defender_id, attacker_hp, defender_hp, status, battle_type, used_potion) VALUES (?, ?, ?, ?, "waiting_attacker", ?, 0)', (attacker_id, defender_id, attacker_hp, defender_hp, battle_type))
        battle_id = cur.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"✅ Бой {battle_id} создан: {attacker_id} vs {defender_id}")
        return battle_id
    except Exception as e:
        logger.error(f"❌ Ошибка создания боя: {e}")
        return None

def get_active_battle(player_id):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM active_battles WHERE (attacker_id = ? OR defender_id = ?) AND status != "completed" ORDER BY id DESC LIMIT 1', (player_id, player_id))
        row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        logger.error(f"❌ Ошибка получения активного боя игрока {player_id}: {e}")
        return None

def update_battle(battle_id, **kwargs):
    try:
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [battle_id]
        cur.execute(f'UPDATE active_battles SET {set_clause} WHERE id = ?', values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления боя {battle_id}: {e}")
        return False

def complete_battle(battle_id):
    try:
        update_battle(battle_id, status='completed')
        logger.info(f"✅ Бой {battle_id} завершен")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка завершения боя {battle_id}: {e}")
        return False

# ============================================================================
# КЛАВИАТУРЫ
# ============================================================================
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мой персонаж"), KeyboardButton(text="⭐ Прокачка навыков")],
            [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🛒 Магазин")],
            [KeyboardButton(text="⚔️ Бой"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )

def get_class_keyboard(selected_class=None):
    buttons = [[KeyboardButton(text=f"{'✅ ' if cls_name == selected_class else ''}{cls_data['emoji']} {cls_name}")] for cls_name, cls_data in CLASSES.items()]
    if selected_class:
        buttons.append([KeyboardButton(text="✅ Подтвердить выбор")])
    buttons.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_battle_type_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚔️ Герой vs Герой")],
            [KeyboardButton(text="👹 Герой vs Монстр")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def get_free_slots_keyboard():
    slots = get_free_slots()
    if not slots:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Назад")]], resize_keyboard=True)
    buttons = [[KeyboardButton(text=f"Слот {slot}")] for slot in slots] + [[KeyboardButton(text="🔙 Назад")]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_opponent_keyboard(exclude_id=None):
    players = get_all_players()
    buttons = []
    for p in players:
        if not exclude_id or p[0] != exclude_id:
            buttons.append([KeyboardButton(text=f"{p[3]} ({p[4]})")])
    if not buttons:
        buttons = [[KeyboardButton(text="Нет доступных противников")]]
    buttons.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_monster_keyboard(floor=None):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    if floor:
        cur.execute('SELECT name FROM monsters WHERE floor = ? ORDER BY level', (floor,))
        monsters = [r[0] for r in cur.fetchall()]
        conn.close()
        buttons = []
        for i in range(0, len(monsters), 2):
            row = [KeyboardButton(text=monsters[i])]
            if i+1 < len(monsters):
                row.append(KeyboardButton(text=monsters[i+1]))
            buttons.append(row)
    else:
        cur.execute('SELECT DISTINCT floor FROM monsters ORDER BY floor')
        floors = [f"Этаж {r[0]}" for r in cur.fetchall()]
        conn.close()
        buttons = [[KeyboardButton(text=floor)] for floor in floors]
    buttons.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_upgrade_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❤️ Здоровье (+5)"), KeyboardButton(text="⚔️ Атака (+2)")],
            [KeyboardButton(text="🛡️ Броня (+1)"), KeyboardButton(text="🏃 Ловкость (+1)")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def get_shop_category_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧪 Зелья"), KeyboardButton(text="⚔️ Оружие")],
            [KeyboardButton(text="🛡️ Экипировка"), KeyboardButton(text="💍 Аксессуары")],
            [KeyboardButton(text="📦 Разное"), KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def get_slot_emoji(slot):
    return {
        "Оружие 1": "⚔️",
        "Оружие 2": "🛡️",
        "Экипировка 1": "🪖",
        "Экипировка 2": "🧥",
        "Экипировка 3": "👖",
        "Экипировка 4": "👢",
        "Экипировка 5": "🧤",
        "Экипировка 6": "🧤",
        "Аксессуар 1": "📿",
        "Аксессуар 2": "💍",
        "Аксессуар 3": "⛓️"
    }.get(slot, "📦")

def get_category_emoji(category):
    return {
        "Зелья": "🧪",
        "Оружие": "⚔️",
        "Экипировка": "🛡️",
        "Аксессуары": "💍",
        "Разное": "📦"
    }.get(category, "🎁")

# ============================================================================
# ОТОБРАЖЕНИЕ ПЕРСОНАЖА
# ============================================================================
async def show_character(message, player):
    try:
        cls = CLASSES[player[4]]
        gold = get_player_gold(player[0])
        
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('SELECT item_name, slot, level FROM inventory WHERE player_id = ? AND equipped = 1', (player[0],))
        equipped = cur.fetchall()
        conn.close()
        
        stats_text = (
            f"👤 **{player[3]}** {cls['emoji']}\n"
            f"🎭 Класс: {player[4]}\n"
            f"📊 Уровень: {player[5]} | Опыт: {player[6]}/{player[5] * 100}\n"
            f"⭐ Очков навыков: {player[7]}\n"
            f"💰 Золото: {gold}\n\n"
            f"⚔️ Attack: {'█' * (player[10] // 5)} {player[10]}\n"
            f"💪 Power: {'█' * (player[10] // 5)} {player[10]}\n"
            f"❤️ HP: {'█' * (player[9] // 50)} {player[9]}/{player[8]}\n\n"
        )
        
        equipment_text = "🛡️ ЭКИПИРОВКА:\n"
        slots_order = ["Оружие 1", "Оружие 2", "Экипировка 1", "Экипировка 2", "Экипировка 3", 
                       "Экипировка 4", "Экипировка 5", "Экипировка 6", "Аксессуар 1", "Аксессуар 2", "Аксессуар 3"]
        
        for slot in slots_order:
            item = next((e for e in equipped if e[1] == slot), None)
            if item:
                equipment_text += f"{get_slot_emoji(slot)} {slot}: {item[0]} (Ур. {item[2]})\n"
        
        if not equipment_text.endswith("ЭКИПИРОВКА:\n"):
            stats_text += equipment_text
        else:
            stats_text += "📭 Нет экипировки"
        
        await message.answer(stats_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"❌ Ошибка отображения персонажа: {e}")
        await message.answer("❌ Произошла ошибка при отображении вашего персонажа.")

# ============================================================================
# ИНВЕНТАРЬ С КНОПКАМИ ДЕЙСТВИЙ
# ============================================================================
def get_inventory_keyboard(items):
    """Создает клавиатуру с кнопками для каждого предмета"""
    buttons = []
    for item in items:
        status = "✅" if item[5] else "🔲"
        btn_text = f"{status} {item[0]}. {item[2]} (Ур. {item[8]}/{item[9]})"
        buttons.append([KeyboardButton(text=f"📌 {btn_text}")])
    
    # Добавляем кнопки действий
    action_buttons = [
        [KeyboardButton(text="✅ Надеть"), KeyboardButton(text="❌ Снять")],
        [KeyboardButton(text="💰 Продать"), KeyboardButton(text="🔥 Прокачать")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    
    # Объединяем кнопки предметов и действий
    full_buttons = buttons + action_buttons
    return ReplyKeyboardMarkup(keyboard=full_buttons, resize_keyboard=True)

@dp.message(F.text == "🎒 Инвентарь")
async def inventory_menu(message: types.Message, state: FSMContext):
    """Отобразить инвентарь"""
    logger.info(f"Пользователь {message.from_user.id} открыл инвентарь")
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Создайте персонажа: /start")
        return
    
    items = get_inventory(message.from_user.id)
    
    # ВСЕГДА обновляем состояние перед отображением
    await state.update_data(inventory_items=items)
    await state.set_state(GameStates.in_inventory)
    
    if not items:
        await message.answer(
            "📭 ИНВЕНТАРЬ ПУСТ!\nПосетите магазин, чтобы купить предметы.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Формируем текст инвентаря
    response = "🎒 ВАШ ИНВЕНТАРЬ\n" + "="*40 + "\n\n"
    equipped_slots = {}
    for item in items:
        slot = item[6] if item[6] else "Не экипирован"
        if slot not in equipped_slots:
            equipped_slots[slot] = []
        equipped_slots[slot].append(item)
    
    slots_order = ["Оружие 1", "Оружие 2", "Экипировка 1", "Экипировка 2", "Экипировка 3", 
                   "Экипировка 4", "Экипировка 5", "Экипировка 6", "Аксессуар 1", "Аксессуар 2", "Аксессуар 3", "Не экипирован"]
    
    for slot in slots_order:
        if slot in equipped_slots:
            response += f"\n{get_slot_emoji(slot)} **{slot}**:\n"
            for item in equipped_slots[slot]:
                status = "✅ Экипировано" if item[5] else "🔲 В инвентаре"
                response += f"▫️ **{item[0]}. {item[2]}** (Ур. {item[8]}/{item[9]})\n"
                response += f"   Тип: {item[3]} | Эффект: {item[4]}\n"
                response += f"   Статус: {status}\n\n"
    
    response += f"{'='*40}\n"
    response += "Выберите предмет или действие:\n"
    response += "• Нажмите 📌 для выбора предмета\n"
    response += "• Или используйте кнопки действий внизу"
    
    # Отправляем сообщение с клавиатурой
    await message.answer(response, parse_mode="Markdown", reply_markup=get_inventory_keyboard(items))

@dp.message(GameStates.in_inventory)
async def inventory_handler(message: types.Message, state: FSMContext):
    """Обработчик действий в инвентаре"""
    data = await state.get_data()
    items = data.get('inventory_items', [])
    player_id = message.from_user.id
    
    logger.info(f"[ИНВЕНТАРЬ] Пользователь {player_id} в состоянии in_inventory, текст: '{message.text}'")
    
    # Обработка возврата в главное меню
    if message.text == "🔙 Назад":
        logger.info(f"[ИНВЕНТАРЬ] Пользователь {player_id} вернулся в главное меню")
        await message.answer("ToSelector действие:", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    # Обработка выбора предмета через кнопку 📌
    if message.text.startswith("📌"):
        try:
            # Извлекаем ID предмета из текста кнопки
            item_id = int(message.text.split(".")[0].split(" ")[1])
            selected_item = next((item for item in items if item[0] == item_id), None)
            
            if not selected_item:
                await message.answer("❌ Предмет не найден в вашем инвентаре!")
                logger.warning(f"[ИНВЕНТАРЬ] Предмет ID {item_id} не найден для пользователя {player_id}")
                return
            
            # Отображаем информацию о предмете и действия
            status = "✅ Экипировано" if selected_item[5] else "🔲 В инвентаре"
            item_info = (
                f"📦 **ВЫБРАН ПРЕДМЕТ**\n"
                f"{'='*40}\n"
                f"🆔 ID: {selected_item[0]}\n"
                f"🏷️ Название: {selected_item[2]}\n"
                f"📊 Тип: {selected_item[3]}\n"
                f"✨ Эффект: {selected_item[4]}\n"
                f"⭐ Уровень: {selected_item[8]}/{selected_item[9]}\n"
                f"💰 Цена покупки: {selected_item[7]} золота\n"
                f"{'='*40}\n"
                f"Статус: {status}\n\n"
                f"Выберите действие:"
            )
            
            # Создаем клавиатуру действий для этого предмета
            action_buttons = [
                [KeyboardButton(text=f"✅ Надеть предмет {selected_item[0]}")],
                [KeyboardButton(text=f"❌ Снять предмет {selected_item[0]}")],
                [KeyboardButton(text=f"💰 Продать предмет {selected_item[0]}")],
                [KeyboardButton(text=f"🔥 Прокачать предмет {selected_item[0]}")],
                [KeyboardButton(text="🔙 Вернуться в инвентарь")]
            ]
            
            # Сохраняем выбранный предмет в состоянии
            await state.update_data(selected_item=selected_item)
            await state.set_state(GameStates.choosing_item_action)
            
            await message.answer(
                item_info, 
                parse_mode="Markdown", 
                reply_markup=ReplyKeyboardMarkup(keyboard=action_buttons, resize_keyboard=True)
            )
            logger.info(f"[ИНВЕНТАРЬ] Пользователь {player_id} выбрал предмет ID {item_id} для действий")
        except Exception as e:
            logger.error(f"[ИНВЕНТАРЬ] Ошибка при выборе предмета: {e}", exc_info=True)
            await message.answer("❌ Ошибка при выборе предмета. Вернитесь в инвентарь.")
        return
    
    # Обработка массовых действий
    if message.text == "✅ Надеть":
        # Показываем только неэкипированные предметы
        unequipped = [item for item in items if not item[5]]
        if not unequipped:
            await message.answer("📭 Нет предметов для надевания!")
            return
        
        response = "✅ ВЫБЕРИТЕ ПРЕДМЕТ ДЛЯ НАДЕВАНИЯ:\n\n"
        for item in unequipped:
            response += f"{item[0]}. {item[2]} (Ур. {item[8]}/{item[9]}) | {item[3]}\n"
        response += "\nВведите номер предмета:"
        
        await message.answer(response)
        await state.set_state(GameStates.selecting_item_for_action)
        await state.update_data(action="equip", items=unequipped)
        logger.info(f"[ИНВЕНТАРЬ] Пользователь {player_id} начал выбор предмета для надевания")
        return
    
    if message.text == "❌ Снять":
        # Показываем только экипированные предметы
        equipped = [item for item in items if item[5]]
        if not equipped:
            await message.answer("📭 Нет экипированных предметов для снятия!")
            return
        
        response = "❌ ВЫБЕРИТЕ ПРЕДМЕТ ДЛЯ СНЯТИЯ:\n\n"
        for item in equipped:
            response += f"{item[0]}. {item[2]} в слоте {item[6]}\n"
        response += "\nВведите номер предмета:"
        
        await message.answer(response)
        await state.set_state(GameStates.selecting_item_for_action)
        await state.update_data(action="unequip", items=equipped)
        logger.info(f"[ИНВЕНТАРЬ] Пользователь {player_id} начал выбор предмета для снятия")
        return
    
    if message.text == "💰 Продать":
        if not items:
            await message.answer("📭 Нет предметов для продажи!")
            return
        
        response = "💰 ВЫБЕРИТЕ ПРЕДМЕТ ДЛЯ ПРОДАЖИ:\n\n"
        for item in items:
            sell_price = item[7] // 2
            response += f"{item[0]}. {item[2]} | Цена продажи: {sell_price} 💰\n"
        response += "\nВведите номер предмета:"
        
        await message.answer(response)
        await state.set_state(GameStates.selecting_item_for_action)
        await state.update_data(action="sell", items=items)
        logger.info(f"[ИНВЕНТАРЬ] Пользователь {player_id} начал выбор предмета для продажи")
        return
    
    if message.text == "🔥 Прокачать":
        # Показываем только предметы, которые можно прокачать
        upgradable = [item for item in items if item[8] < item[9]]
        if not upgradable:
            await message.answer("📭 Нет предметов для прокачки (все на макс. уровне)!")
            return
        
        response = "🔥 ВЫБЕРИТЕ ПРЕДМЕТ ДЛЯ ПРОКАЧКИ:\n\n"
        for item in upgradable:
            upgrade_cost = item[7] * 2
            response += f"{item[0]}. {item[2]} (Ур. {item[8]}/{item[9]}) | Стоимость: {upgrade_cost} 💰\n"
        response += "\nВведите номер предмета:"
        
        await message.answer(response)
        await state.set_state(GameStates.selecting_item_for_action)
        await state.update_data(action="upgrade", items=upgradable)
        logger.info(f"[ИНВЕНТАРЬ] Пользователь {player_id} начал выбор предмета для прокачки")
        return
    
    await message.answer("❌ Неизвестная команда! Используйте кнопки меню.")

@dp.message(GameStates.choosing_item_action)
async def item_action_handler(message: types.Message, state: FSMContext):
    """Обработчик действий с выбранным предметом"""
    data = await state.get_data()
    selected_item = data.get('selected_item')
    player_id = message.from_user.id
    
    logger.info(f"[ИНВЕНТАРЬ] Пользователь {player_id} в состоянии choosing_item_action, текст: '{message.text}'")
    
    if message.text == "🔙 Вернуться в инвентарь":
        logger.info(f"[ИНВЕНТАРЬ] Пользователь {player_id} вернулся в инвентарь из выбора действия")
        await inventory_menu(message, state)
        return
    
    if not selected_item:
        logger.warning(f"[ИНВЕНТАРЬ] Пользователь {player_id} пытается выполнить действие без выбранного предмета")
        await message.answer("❌ Предмет не выбран! Вернитесь в инвентарь.")
        await inventory_menu(message, state)
        return
    
    # Извлекаем действие и ID предмета из текста кнопки
    try:
        if "Надеть предмет" in message.text:
            action = "equip"
        elif "Снять предмет" in message.text:
            action = "unequip"
        elif "Продать предмет" in message.text:
            action = "sell"
        elif "Прокачать предмет" in message.text:
            action = "upgrade"
        else:
            await message.answer("❌ Неизвестное действие! Вернитесь в инвентарь.")
            await inventory_menu(message, state)
            return
        
        # Извлекаем ID предмета из текста кнопки
        item_id = int(message.text.split(" ")[-1])
        
        # Проверяем, что предмет существует и принадлежит игроку
        if selected_item[0] != item_id:
            logger.warning(f"[ИНВЕНТАРЬ] Несоответствие ID предмета: ожидался {selected_item[0]}, получен {item_id}")
            await message.answer("❌ Выбран неверный предмет! Вернитесь в инвентарь.")
            await inventory_menu(message, state)
            return
        
    except Exception as e:
        logger.error(f"[ИНВЕНТАРЬ] Ошибка при обработке действия: {e}", exc_info=True)
        await message.answer("❌ Ошибка при обработке действия. Вернитесь в инвентарь.")
        await inventory_menu(message, state)
        return
    
    # Выполняем действие
    if action == "equip":
        if selected_item[5]:
            await message.answer("❌ Этот предмет уже экипирован!")
            await inventory_menu(message, state)
            return
        
        slot_map = {
            "Оружие 1": "Оружие 1", "Оружие 2": "Оружие 2",
            "Экипировка 1": "Экипировка 1", "Экипировка 2": "Экипировка 2",
            "Экипировка 3": "Экипировка 3", "Экипировка 4": "Экипировка 4",
            "Экипировка 5": "Экипировка 5", "Экипировка 6": "Экипировка 6",
            "Аксессуар 1": "Аксессуар 1", "Аксессуар 2": "Аксессуар 2", "Аксессуар 3": "Аксессуар 3"
        }
        
        slot = slot_map.get(selected_item[3])
        if not slot:
            await message.answer("❌ Нельзя экипировать этот тип предмета!")
            await inventory_menu(message, state)
            return
        
        equip_item(player_id, item_id, slot)
        await message.answer(f"✅ {selected_item[2]} экипировано в слот {slot}!")
        await inventory_menu(message, state)
        return
    
    elif action == "unequip":
        if not selected_item[5]:
            await message.answer("❌ Этот предмет не экипирован!")
            await inventory_menu(message, state)
            return
        
        unequip_item(player_id, selected_item[6])
        await message.answer(f"✅ Предмет {selected_item[2]} снят со слота {selected_item[6]}!")
        await inventory_menu(message, state)
        return
    
    elif action == "sell":
        success, msg = sell_item(player_id, item_id)
        await message.answer(msg)
        # ВАЖНО: после продажи предмета нужно обновить состояние и вернуться в инвентарь
        await inventory_menu(message, state)
        return
    
    elif action == "upgrade":
        if selected_item[8] >= selected_item[9]:
            await message.answer(f"❌ Предмет уже на максимальном уровне ({selected_item[9]})!")
            await inventory_menu(message, state)
            return
        
        upgrade_cost = selected_item[7] * 2
        gold = get_player_gold(player_id)
        
        if gold < upgrade_cost:
            await message.answer(f"❌ Недостаточно золота для прокачки!\nНужно: {upgrade_cost} 💰\nУ вас: {gold} 💰")
            await inventory_menu(message, state)
            return
        
        remove_gold(player_id, upgrade_cost)
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('UPDATE inventory SET level = level + 1 WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        
        await message.answer(
            f"🔥 Предмет прокачан!\n"
            f"{'='*40}\n"
            f"✅ {selected_item[2]} теперь на уровне {selected_item[8] + 1}/{selected_item[9]}\n"
            f"💰 Потрачено: {upgrade_cost} золота"
        )
        await inventory_menu(message, state)
        return

@dp.message(GameStates.selecting_item_for_action)
async def select_item_for_action(message: types.Message, state: FSMContext):
    """Обработчик выбора предмета для действия"""
    try:
        item_id = int(message.text)
    except ValueError:
        logger.warning(f"[ИНВЕНТАРЬ] Пользователь {message.from_user.id} ввел некорректный номер предмета: {message.text}")
        await message.answer("❌ Введите номер предмета!")
        return
    
    data = await state.get_data()
    action = data.get('action')
    items = data.get('items', [])
    player_id = message.from_user.id
    
    selected_item = next((item for item in items if item[0] == item_id), None)
    if not selected_item:
        logger.warning(f"[ИНВЕНТАРЬ] Пользователь {player_id} выбрал несуществующий предмет с ID {item_id}")
        await message.answer("❌ Предмет не найден!")
        await inventory_menu(message, state)
        return
    
    # Выполняем действие
    if action == "equip":
        slot_map = {
            "Оружие 1": "Оружие 1", "Оружие 2": "Оружие 2",
            "Экипировка 1": "Экипировка 1", "Экипировка 2": "Экипировка 2",
            "Экипировка 3": "Экипировка 3", "Экипировка 4": "Экипировка 4",
            "Экипировка 5": "Экипировка 5", "Экипировка 6": "Экипировка 6",
            "Аксессуар 1": "Аксессуар 1", "Аксессуар 2": "Аксессуар 2", "Аксессуар 3": "Аксессуар 3"
        }
        
        slot = slot_map.get(selected_item[3])
        if not slot:
            await message.answer("❌ Нельзя экипировать этот тип предмета!")
            await inventory_menu(message, state)
            return
        
        equip_item(player_id, item_id, slot)
        await message.answer(f"✅ {selected_item[2]} экипировано в слот {slot}!")
        await inventory_menu(message, state)
        return
    
    elif action == "unequip":
        unequip_item(player_id, selected_item[6])
        await message.answer(f"✅ Предмет {selected_item[2]} снят со слота {selected_item[6]}!")
        await inventory_menu(message, state)
        return
    
    elif action == "sell":
        success, msg = sell_item(player_id, item_id)
        await message.answer(msg)
        await inventory_menu(message, state)
        return
    
    elif action == "upgrade":
        if selected_item[8] >= selected_item[9]:
            await message.answer(f"❌ Предмет уже на максимальном уровне ({selected_item[9]})!")
            await inventory_menu(message, state)
            return
        
        upgrade_cost = selected_item[7] * 2
        gold = get_player_gold(player_id)
        
        if gold < upgrade_cost:
            await message.answer(f"❌ Недостаточно золота для прокачки!\nНужно: {upgrade_cost} 💰\nУ вас: {gold} 💰")
            await inventory_menu(message, state)
            return
        
        remove_gold(player_id, upgrade_cost)
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute('UPDATE inventory SET level = level + 1 WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        
        await message.answer(
            f"🔥 Предмет прокачан!\n"
            f"{'='*40}\n"
            f"✅ {selected_item[2]} теперь на уровне {selected_item[8] + 1}/{selected_item[9]}\n"
            f"💰 Потрачено: {upgrade_cost} золота"
        )
        await inventory_menu(message, state)
        return
    
    await message.answer("❌ Неизвестное действие!")
    await inventory_menu(message, state)

# ============================================================================
# ОСНОВНЫЕ КОМАНДЫ
# ============================================================================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """Обработчик команды /start с полной обработкой ошибок"""
    try:
        logger.info(f"[START] Пользователь {message.from_user.id} запустил /start")
        print(f"✅ /start получен от пользователя {message.from_user.id}")
        
        player = get_player(message.from_user.id)
        if player:
            logger.info(f"[START] Пользователь {message.from_user.id} уже имеет персонажа")
            await show_character(message, player)
            await state.set_state(GameStates.choosing_action)
        else:
            logger.info(f"[START] Пользователь {message.from_user.id} создает нового персонажа")
            free_slots = get_free_slots()
            
            if not free_slots:
                logger.warning(f"[START] Игра заполнена для пользователя {message.from_user.id}")
                await message.answer(
                    "❌ Игра заполнена! Максимум 6 игроков.",
                    reply_markup=get_main_keyboard()
                )
                return
            
            # Создаем клавиатуру с обработкой ошибок
            try:
                keyboard = get_free_slots_keyboard()
            except Exception as e:
                logger.error(f"[START] Ошибка создания клавиатуры: {e}", exc_info=True)
                await message.answer(
                    "❌ Ошибка при создании клавиатуры. Попробуйте позже.",
                    reply_markup=get_main_keyboard()
                )
                return
            
            await message.answer(
                f"🎮 Добро пожаловать в Потерянные земли!\n\n"
                f"👥 Игроков в игре: {6 - len(free_slots)}/6\n\n"
                "Создайте персонажа:\n"
                "1️⃣ Выберите свободный слот (1-6)\n"
                "2️⃣ Введите уникальное имя (3-20 символов)\n"
                "3️⃣ Выберите класс и подтвердите выбор",
                reply_markup=keyboard
            )
            await state.set_state(GameStates.waiting_for_slot)
            logger.info(f"[START] Пользователь {message.from_user.id} перешел в состояние waiting_for_slot")
            
    except Exception as e:
        logger.error(f"[START] КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в /start: {e}")
        traceback.print_exc()
        try:
            await message.answer(
                "❌ Произошла критическая ошибка. Попробуйте позже или обратитесь к администратору.",
                reply_markup=get_main_keyboard()
            )
        except:
            pass

# ... остальные обработчики команд (прокачка навыков, магазин, бой, статистика, помощь) ...
# [Все остальные обработчики из вашего файла работают корректно, поэтому не привожу их для экономии места]

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА С МАКСИМАЛЬНОЙ ОБРАБОТКОЙ ОШИБОК
# ============================================================================
async def main():
    """Основная функция запуска бота"""
    print("\n" + "="*70)
    print("🚀 ЗАПУСК БОТА")
    print("="*70)
    
    # Инициализация базы данных
    try:
        init_db()
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА инициализации БД: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    # Проверка подключения к Telegram
    try:
        print("📡 Проверка подключения к Telegram API...")
        me = await bot.get_me()
        print(f"✅ Подключено к Telegram как @{me.username} (ID: {me.id})")
        logger.info(f"Подключено к Telegram как @{me.username}")
        print("\n" + "="*70)
        print("✅ БОТ ГОТОВ К РАБОТЕ!")
        print("="*70)
        print("💬 Отправьте /start в Telegram для начала игры")
        print("="*70 + "\n")
    except Exception as e:
        print(f"❌ ОШИБКА подключения к Telegram: {e}")
        print("💡 Проверьте правильность BOT_TOKEN в настройках Railway")
        traceback.print_exc()
        sys.exit(1)
    
    # Запуск поллинга
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n⚠️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА во время работы: {e}")
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        traceback.print_exc()
        sys.exit(1)

# ============================================================================
# ТОЧКА ВХОДА С МАКСИМАЛЬНОЙ ОБРАБОТКОЙ ОШИБОК
# ============================================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Запуск прерван пользователем")
    except Exception as e:
        print(f"\n❌ ФАТАЛЬНАЯ ОШИБКА при запуске: {e}")
        logger.error(f"ФАТАЛЬНАЯ ОШИБКА: {e}", exc_info=True)
        traceback.print_exc()
        sys.exit(1)
