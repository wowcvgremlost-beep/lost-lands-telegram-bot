import os
import sqlite3
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import F
import asyncio
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = os.environ.get('BOT_TOKEN')
if not API_TOKEN:
    logger.error("❌ BOT_TOKEN не найден! Добавьте его в переменные окружения Railway.")
    raise ValueError("BOT_TOKEN не найден!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

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

CLASSES = {
    "Воин": {"hp_bonus": 20, "atk_bonus": 3, "arm_bonus": 2, "agi_bonus": 0, "description": "🛡️ Высокая живучесть и защита", "emoji": "⚔️"},
    "Маг": {"hp_bonus": -10, "atk_bonus": 5, "arm_bonus": -1, "agi_bonus": 1, "description": "🔮 Сильная атака, но хрупкий", "emoji": "🧙"},
    "Разбойник": {"hp_bonus": 0, "atk_bonus": 2, "arm_bonus": 0, "agi_bonus": 3, "description": "🏃 Высокая ловкость, критические удары", "emoji": "🗡️"},
    "Паладин": {"hp_bonus": 15, "atk_bonus": 1, "arm_bonus": 3, "agi_bonus": -1, "description": "🛡️⚔️ Сбалансированный защитник", "emoji": "🛡️"},
    "Стрелок": {"hp_bonus": -5, "atk_bonus": 4, "arm_bonus": -1, "agi_bonus": 2, "description": "🏹 Дальний бой, высокий урон", "emoji": "🏹"},
    "Друид": {"hp_bonus": 10, "atk_bonus": 2, "arm_bonus": 1, "agi_bonus": 1, "description": "🌿 Природная магия и выносливость", "emoji": "🌿"}
}

# Функции работы с базой данных
def get_connection():
    return sqlite3.connect('game.db')

def init_db():
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            # Таблицы игроков
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
                );
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
                );
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
                );
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
                );
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
                );
            ''')
            
            # Если монстры не загружены, добавляем их
            cur.execute('SELECT COUNT(*) FROM monsters')
            count = cur.fetchone()[0]
            if count == 0:
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
                
            # Если товары не загружены, добавляем их
            cur.execute('SELECT COUNT(*) FROM shop')
            count = cur.fetchone()[0]
            if count == 0:
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
            
        conn.commit()
        logger.info("✅ База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise

# Вспомогательные функции
def get_player(telegram_id):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM players WHERE telegram_id = ?', (telegram_id,))
            return cur.fetchone()
    except Exception as e:
        logger.error(f"❌ Ошибка при получении игрока: {e}")
        return None

def create_player(telegram_id, username, hero_slot, hero_name, hero_class):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM players')
            if cur.fetchone()[0] >= 6:
                return False, "❌ В игре уже 6 игроков!"
            cur.execute('SELECT hero_name FROM players WHERE hero_name = ?', (hero_name,))
            if cur.fetchone():
                return False, f"❌ Имя '{hero_name}' занято!"
            cur.execute('SELECT hero_slot FROM players WHERE hero_slot = ?', (hero_slot,))
            if cur.fetchone():
                return False, f"❌ Слот {hero_slot} занят!"
            cls = CLASSES[hero_class]
            cur.execute('''
                INSERT INTO players (telegram_id, username, hero_slot, hero_name, hero_class, max_hp, current_hp, attack, armor, agility, gold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ''', (telegram_id, username, hero_slot, hero_name, hero_class, 100+cls['hp_bonus'], 100+cls['hp_bonus'], 10+cls['atk_bonus'], 5+cls['arm_bonus'], 5+cls['agi_bonus']))
            conn.commit()
            return True, "✅ Персонаж создан!"
    except Exception as e:
        logger.error(f"❌ Ошибка создания игрока: {e}")
        return False, f"❌ Ошибка сервера: {str(e)}"

def update_player(telegram_id, **kwargs):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [telegram_id]
            cur.execute(f'UPDATE players SET {set_clause} WHERE telegram_id = ?', values)
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления игрока: {e}")
        return False

def get_all_players():
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM players ORDER BY hero_slot')
            return cur.fetchall()
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка игроков: {e}")
        return []

def get_free_slots():
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT hero_slot FROM players')
            occupied = {row[0] for row in cur.fetchall()}
            return [i for i in range(1, 7) if i not in occupied]
    except Exception as e:
        logger.error(f"❌ Ошибка получения свободных слотов: {e}")
        return []

def get_monster(name):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM monsters WHERE name = ?', (name,))
            return cur.fetchone()
    except Exception as e:
        logger.error(f"❌ Ошибка получения монстра: {e}")
        return None

def calculate_damage(attacker_atk, attacker_agi, defender_arm, defender_agi, dice_roll):
    base = max(1, attacker_atk - defender_arm * 0.6)
    agility_mod = (attacker_agi - defender_agi) * 0.4
    dice_mod = (dice_roll - 10) * 1.8
    return max(1, round(base + agility_mod + dice_mod))

def add_gold(player_id, amount):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('UPDATE players SET gold = gold + ? WHERE telegram_id = ?', (amount, player_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления золота: {e}")
        return False

def remove_gold(player_id, amount):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('UPDATE players SET gold = gold - ? WHERE telegram_id = ?', (amount, player_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка удаления золота: {e}")
        return False

def get_player_gold(player_id):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT gold FROM players WHERE telegram_id = ?', (player_id,))
            result = cur.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"❌ Ошибка получения золота: {e}")
        return 0

def add_item_to_inventory(player_id, item_name, item_type, effect, bought_price):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO inventory (player_id, item_name, item_type, effect, equipped, bought_price) VALUES (?, ?, ?, ?, 0, ?)', (player_id, item_name, item_type, effect, bought_price))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления предмета в инвентарь: {e}")
        return False

def get_inventory(player_id):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM inventory WHERE player_id = ?', (player_id,))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"❌ Ошибка получения инвентаря: {e}")
        return []

def get_shop_items(category=None):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if category:
                cur.execute('SELECT * FROM shop WHERE category = ? ORDER BY price', (category,))
            else:
                cur.execute('SELECT * FROM shop ORDER BY category, price')
            return cur.fetchall()
    except Exception as e:
        logger.error(f"❌ Ошибка получения товаров магазина: {e}")
        return []

def equip_item(player_id, item_id, slot):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('UPDATE inventory SET equipped = 0, slot = NULL WHERE player_id = ? AND slot = ?', (player_id, slot))
            cur.execute('UPDATE inventory SET equipped = 1, slot = ? WHERE id = ? AND player_id = ?', (slot, item_id, player_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка экипировки: {e}")
        return False

def unequip_item(player_id, slot):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('UPDATE inventory SET equipped = 0, slot = NULL WHERE player_id = ? AND slot = ?', (player_id, slot))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка снятия экипировки: {e}")
        return False

def sell_item(player_id, item_id):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT bought_price FROM inventory WHERE id = ? AND player_id = ?', (item_id, player_id))
            result = cur.fetchone()
            if not result:
                return False, "Предмет не найден!"
            sell_price = result[0] // 2
            add_gold(player_id, sell_price)
            cur.execute('DELETE FROM inventory WHERE id = ? AND player_id = ?', (item_id, player_id))
            conn.commit()
            return True, f"Предмет продан за {sell_price} золота!"
    except Exception as e:
        logger.error(f"❌ Ошибка продажи предмета: {e}")
        return False, f"❌ Ошибка сервера: {str(e)}"

def use_potion_in_battle(player_id, battle_id):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT used_potion FROM active_battles WHERE id = ?', (battle_id,))
            battle = cur.fetchone()
            if battle and battle[0]:
                return False, "Вы уже использовали зелье в этом бою!"
            cur.execute('SELECT id, effect FROM inventory WHERE player_id = ? AND item_type = "Зелье" AND equipped = 0 LIMIT 1', (player_id,))
            potion = cur.fetchone()
            if not potion:
                return False, "Нет зелий в инвентаре!"
            heal = 30 if "+30HP" in potion[1] else 60 if "+60HP" in potion[1] else 100
            cur.execute('DELETE FROM inventory WHERE id = ?', (potion[0],))
            cur.execute('UPDATE active_battles SET used_potion = 1 WHERE id = ?', (battle_id,))
            conn.commit()
            return True, heal
    except Exception as e:
        logger.error(f"❌ Ошибка использования зелья: {e}")
        return False, f"❌ Ошибка сервера: {str(e)}"

def create_battle(attacker_id, defender_id, attacker_hp, defender_hp, battle_type="pvp"):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO active_battles (attacker_id, defender_id, attacker_hp, defender_hp, status, battle_type, used_potion) VALUES (?, ?, ?, ?, "waiting_attacker", ?, 0)', (attacker_id, defender_id, attacker_hp, defender_hp, battle_type))
            return cur.lastrowid
    except Exception as e:
        logger.error(f"❌ Ошибка создания боя: {e}")
        return None

def get_active_battle(player_id):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM active_battles WHERE (attacker_id = ? OR defender_id = ?) AND status != "completed" ORDER BY id DESC LIMIT 1', (player_id, player_id))
            return cur.fetchone()
    except Exception as e:
        logger.error(f"❌ Ошибка получения активного боя: {e}")
        return None

def update_battle(battle_id, **kwargs):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [battle_id]
            cur.execute(f'UPDATE active_battles SET {set_clause} WHERE id = ?', values)
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления боя: {e}")
        return False

def complete_battle(battle_id):
    try:
        update_battle(battle_id, status='completed')
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка завершения боя: {e}")
        return False

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
    with get_connection() as conn:
        cur = conn.cursor()
        if floor:
            cur.execute('SELECT name FROM monsters WHERE floor = ? ORDER BY level', (floor,))
            monsters = [r[0] for r in cur.fetchall()]
            buttons = []
            for i in range(0, len(monsters), 2):
                row = [KeyboardButton(text=monsters[i])]
                if i+1 < len(monsters):
                    row.append(KeyboardButton(text=monsters[i+1]))
                buttons.append(row)
        else:
            cur.execute('SELECT DISTINCT floor FROM monsters ORDER BY floor')
            floors = [f"Этаж {r[0]}" for r in cur.fetchall()]
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

async def show_character(message, player):
    try:
        cls = CLASSES[player[4]]
        gold = get_player_gold(player[0])
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT item_name, slot, level FROM inventory WHERE player_id = ? AND equipped = 1', (player[0],))
            equipped = cur.fetchall()
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
        await message.answer("❌ Произошла ошибка при отображении вашего персонажа. Попробуйте позже.")

# Основные команды
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} запустил /start")
    player = get_player(message.from_user.id)
    if player:
        logger.info(f"Пользователь {message.from_user.id} уже имеет персонажа")
        await show_character(message, player)
        await state.set_state(GameStates.choosing_action)
    else:
        logger.info(f"Пользователь {message.from_user.id} создаёт нового персонажа")
        free_slots = get_free_slots()
        if not free_slots:
            logger.warning(f"Игра заполнена! Пользователь {message.from_user.id} не может создать персонажа")
            await message.answer("❌ Игра заполнена! Максимум 6 игроков.", reply_markup=get_main_keyboard())
            return
        await message.answer(
            f"🎮 Добро пожаловать в Потерянные Земли!\n\n"
            f"👥 Игроков в игре: {6 - len(free_slots)}/6\n\n"
            "Создайте персонажа:\n"
            "1️⃣ Выберите свободный слот (1-6)\n"
            "2️⃣ Введите уникальное имя (3-20 символов)\n"
            "3️⃣ Выберите класс и подтвердите выбор",
            reply_markup=get_free_slots_keyboard()
        )
        await state.set_state(GameStates.waiting_for_slot)

@dp.message(GameStates.waiting_for_slot)
async def process_slot(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} выбирает слот")
    if message.text == "🔙 Назад":
        logger.info(f"Пользователь {message.from_user.id} вернулся в главное меню из выбора слота")
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
        await state.set_state(GameStates.choosing_action)
        return
    try:
        slot = int(message.text.split()[1])
        assert slot in get_free_slots()
    except:
        logger.warning(f"Пользователь {message.from_user.id} выбрал неверный слот")
        await message.answer("❌ Выберите слот из списка!", reply_markup=get_free_slots_keyboard())
        return
    await state.update_data(hero_slot=slot)
    logger.info(f"Пользователь {message.from_user.id} выбрал слот {slot}")
    await message.answer(f"✅ Слот {slot} выбран.\n📝 Введите имя персонажа (3-20 символов):")
    await state.set_state(GameStates.waiting_for_name)

@dp.message(GameStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит имя")
    name = message.text.strip()
    if len(name) < 3 or len(name) > 20:
        logger.warning(f"Пользователь {message.from_user.id} ввёл некорректное имя: {name}")
        await message.answer("❌ Имя должно быть от 3 до 20 символов!")
        return
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT hero_name FROM players WHERE hero_name = ?', (name,))
        if cur.fetchone():
            conn.close()
            logger.warning(f"Пользователь {message.from_user.id} пытается создать персонажа с занятым именем: {name}")
            await message.answer("❌ Имя уже занято! Введите другое:")
            return
    await state.update_data(hero_name=name)
    logger.info(f"Пользователь {message.from_user.id} ввёл имя: {name}")
    classes_text = "🎭 Выберите класс персонажа:\n\n"
    for cls_name, cls_data in CLASSES.items():
        classes_text += f"{cls_data['emoji']} **{cls_name}**\n"
        classes_text += f"   {cls_data['description']}\n"
        bonuses = []
        if cls_data['hp_bonus'] != 0:
            bonuses.append(f"HP {'+' if cls_data['hp_bonus'] > 0 else ''}{cls_data['hp_bonus']}")
        if cls_data['atk_bonus'] != 0:
            bonuses.append(f"ATK {'+' if cls_data['atk_bonus'] > 0 else ''}{cls_data['atk_bonus']}")
        if cls_data['arm_bonus'] != 0:
            bonuses.append(f"ARM {'+' if cls_data['arm_bonus'] > 0 else ''}{cls_data['arm_bonus']}")
        if cls_data['agi_bonus'] != 0:
            bonuses.append(f"AGI {'+' if cls_data['agi_bonus'] > 0 else ''}{cls_data['agi_bonus']}")
        classes_text += f"   Бонусы: {', '.join(bonuses)}\n\n"
    await message.answer(classes_text, parse_mode="Markdown", reply_markup=get_class_keyboard())
    await state.set_state(GameStates.waiting_for_class)

@dp.message(GameStates.waiting_for_class)
async def process_class(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} выбирает класс")
    if message.text == "🔙 Назад":
        logger.info(f"Пользователь {message.from_user.id} вернулся в выбор имени из выбора класса")
        await message.answer("📝 Введите имя персонажа:")
        await state.set_state(GameStates.waiting_for_name)
        return
    class_text = message.text.strip()
    for prefix in ['✅ ', '⚔️ ', '🧙 ', '🗡️ ', '🛡️ ', '🏹 ', '🌿 ']:
        if class_text.startswith(prefix):
            class_text = class_text[len(prefix):]
            break
    if class_text not in CLASSES:
        logger.warning(f"Пользователь {message.from_user.id} выбрал неверный класс: {class_text}")
        await message.answer("❌ Выберите класс из списка!", reply_markup=get_class_keyboard())
        return
    await state.update_data(hero_class=class_text)
    cls = CLASSES[class_text]
    await message.answer(
        f"🎭 Вы выбрали: **{class_text}**\n\n"
        f"{cls['description']}\n\n"
        f"**Бонусы:**\n"
        f"❤️ HP: {'+' if cls['hp_bonus'] > 0 else ''}{cls['hp_bonus']}\n"
        f"⚔️ ATK: {'+' if cls['atk_bonus'] > 0 else ''}{cls['atk_bonus']}\n"
        f"🛡️ ARM: {'+' if cls['arm_bonus'] > 0 else ''}{cls['arm_bonus']}\n"
        f"🏃 AGI: {'+' if cls['agi_bonus'] > 0 else ''}{cls['agi_bonus']}\n\n"
        f"✅ Нажмите 'Подтвердить выбор' для создания персонажа",
        parse_mode="Markdown",
        reply_markup=get_class_keyboard(selected_class=class_text)
    )
    await state.set_state(GameStates.waiting_for_class_confirm)

@dp.message(GameStates.waiting_for_class_confirm)
async def confirm_class(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} подтверждает выбор класса")
    if message.text == "🔙 Назад":
        logger.info(f"Пользователь {message.from_user.id} вернулся в выбор класса из подтверждения")
        classes_text = "🎭 Выберите класс персонажа:\n\n"
        for cls_name, cls_data in CLASSES.items():
            classes_text += f"{cls_data['emoji']} **{cls_name}**\n"
            classes_text += f"   {cls_data['description']}\n"
            bonuses = []
            if cls_data['hp_bonus'] != 0:
                bonuses.append(f"HP {'+' if cls_data['hp_bonus'] > 0 else ''}{cls_data['hp_bonus']}")
            if cls_data['atk_bonus'] != 0:
                bonuses.append(f"ATK {'+' if cls_data['atk_bonus'] > 0 else ''}{cls_data['atk_bonus']}")
            if cls_data['arm_bonus'] != 0:
                bonuses.append(f"ARM {'+' if cls_data['arm_bonus'] > 0 else ''}{cls_data['arm_bonus']}")
            if cls_data['agi_bonus'] != 0:
                bonuses.append(f"AGI {'+' if cls_data['agi_bonus'] > 0 else ''}{cls_data['agi_bonus']}")
            classes_text += f"   Бонусы: {', '.join(bonuses)}\n\n"
        await message.answer(classes_text, parse_mode="Markdown", reply_markup=get_class_keyboard())
        await state.set_state(GameStates.waiting_for_class)
        return
    if message.text == "✅ Подтвердить выбор":
        data = await state.get_data()
        hero_slot = data['hero_slot']
        hero_name = data['hero_name']
        hero_class = data['hero_class']
        telegram_id = message.from_user.id
        username = message.from_user.username or f"user_{telegram_id}"
        success, msg = create_player(telegram_id, username, hero_slot, hero_name, hero_class)
        if success:
            logger.info(f"Пользователь {message.from_user.id} успешно создал персонажа")
            player = get_player(telegram_id)
            await show_character(message, player)
            await state.set_state(GameStates.choosing_action)
        else:
            logger.warning(f"Пользователь {message.from_user.id} не смог создать персонажа: {msg}")
            await message.answer(msg, reply_markup=get_free_slots_keyboard())
            await state.set_state(GameStates.waiting_for_slot)
        return
    # Если снова выбран класс
    class_text = message.text.strip()
    for prefix in ['✅ ', '⚔️ ', '🧙 ', '🗡️ ', '🛡️ ', '🏹 ', '🌿 ']:
        if class_text.startswith(prefix):
            class_text = class_text[len(prefix):]
            break
    if class_text in CLASSES:
        logger.info(f"Пользователь {message.from_user.id} изменил выбор класса на: {class_text}")
        await state.update_data(hero_class=class_text)
        cls = CLASSES[class_text]
        await message.answer(
            f"🎭 Вы выбрали: **{class_text}**\n\n"
            f"{cls['description']}\n\n"
            f"**Бонусы:**\n"
            f"❤️ HP: {'+' if cls['hp_bonus'] > 0 else ''}{cls['hp_bonus']}\n"
            f"⚔️ ATK: {'+' if cls['atk_bonus'] > 0 else ''}{cls['atk_bonus']}\n"
            f"🛡️ ARM: {'+' if cls['arm_bonus'] > 0 else ''}{cls['arm_bonus']}\n"
            f"🏃 AGI: {'+' if cls['agi_bonus'] > 0 else ''}{cls['agi_bonus']}\n\n"
            f"✅ Нажмите 'Подтвердить выбор' для создания персонажа",
            parse_mode="Markdown",
            reply_markup=get_class_keyboard(selected_class=class_text)
        )
        return
    await message.answer("❌ Используйте кнопки!")

@dp.message(F.text == "👤 Мой персонаж")
async def my_char(message: types.Message):
    logger.info(f"Пользователь {message.from_user.id} запрашивает информацию о персонаже")
    player = get_player(message.from_user.id)
    if player:
        await show_character(message, player)
    else:
        await message.answer("❌ Создайте персонажа: /start")

@dp.message(F.text == "⭐ Прокачка навыков")
async def upgrade(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} запрашивает прокачку навыков")
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Создайте персонажа: /start")
        return
    if player[7] <= 0:
        await message.answer("❌ У вас нет очков навыков!\nПобедите монстров, чтобы получить опыт и повысить уровень.", reply_markup=get_main_keyboard())
        return
    await message.answer(
        f"⭐ ПРОКАЧКА НАВЫКОВ ({player[7]} очков)\n"
        f"{'='*40}\n"
        f"👤 {player[3]} ({player[4]})\n"
        f"📊 Уровень: {player[5]}\n\n"
        f"Текущие характеристики:\n"
        f"❤️ Здоровье: {player[9]}/{player[8]}\n"
        f"⚔️ Атака: {player[10]}\n"
        f"🛡️ Броня: {player[11]}\n"
        f"🏃 Ловкость: {player[12]}\n\n"
        f"Выберите параметр для прокачки:",
        reply_markup=get_upgrade_keyboard()
    )
    await state.set_state(GameStates.choosing_stat_to_upgrade)
    await state.update_data(player=player)

@dp.message(GameStates.choosing_stat_to_upgrade)
async def process_upgrade(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} выбирает параметр для прокачки")
    if message.text == "🔙 Назад":
        logger.info(f"Пользователь {message.from_user.id} вернулся в главное меню из прокачки")
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
        await state.clear()
        return
    data = await state.get_data()
    player = data['player']
    telegram_id = message.from_user.id
    if player[7] <= 0:
        logger.warning(f"Пользователь {message.from_user.id} пытался прокачать без очков навыков")
        await message.answer("❌ Нет очков навыков!", reply_markup=get_main_keyboard())
        await state.clear()
        return
    stat_map = {
        "❤️ Здоровье (+5)": ("max_hp", 5, "Здоровье"),
        "⚔️ Атака (+2)": ("attack", 2, "Атака"),
        "🛡️ Броня (+1)": ("armor", 1, "Броня"),
        "🏃 Ловкость (+1)": ("agility", 1, "Ловкость")
    }
    if message.text not in stat_map:
        logger.warning(f"Пользователь {message.from_user.id} выбрал неверный параметр для прокачки")
        await message.answer("❌ Выберите параметр из меню!")
        return
    stat_db, bonus, stat_name = stat_map[message.text]
    if stat_db == "max_hp":
        update_player(telegram_id, max_hp=player[8] + bonus, current_hp=player[9] + bonus, skill_points=player[7] - 1)
    elif stat_db == "attack":
        update_player(telegram_id, attack=player[10] + bonus, skill_points=player[7] - 1)
    elif stat_db == "armor":
        update_player(telegram_id, armor=player[11] + bonus, skill_points=player[7] - 1)
    elif stat_db == "agility":
        update_player(telegram_id, agility=player[12] + bonus, skill_points=player[7] - 1)
    updated_player = get_player(telegram_id)
    await message.answer(
        f"✅ Прокачано!\n"
        f"+{bonus} к {stat_name}\n\n"
        f"⭐ Осталось очков: {updated_player[7]}\n\n"
        f"Текущие характеристики:\n"
        f"❤️ Здоровье: {updated_player[9]}/{updated_player[8]}\n"
        f"⚔️ Атака: {updated_player[10]}\n"
        f"🛡️ Броня: {updated_player[11]}\n"
        f"🏃 Ловкость: {updated_player[12]}",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

# Магазин
@dp.message(F.text == "🛒 Магазин")
async def shop_menu(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} открывает магазин")
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Создайте персонажа: /start", reply_markup=get_main_keyboard())
        return
    gold = get_player_gold(message.from_user.id)
    await message.answer(
        f"🛒 **ДОБРО ПОЖАЛОВАТЬ В МАГАЗИН!**\n"
        f"{'='*40}\n"
        f"💰 Ваше золото: {gold}\n"
        f"✨ Здесь вы можете купить:\n"
        f"   • Зелья для восстановления здоровья\n"
        f"   • Оружие и экипировку для усиления\n"
        f"   • Аксессуары с уникальными бонусами\n"
        f"   • Свитки опыта для прокачки\n"
        f"{'='*40}\n\n"
        f"Выберите категорию:",
        parse_mode="Markdown",
        reply_markup=get_shop_category_keyboard()
    )
    await state.set_state(GameStates.in_shop_category)
    await state.update_data(last_purchase=None)

@dp.message(GameStates.in_shop_category)
async def shop_handler(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} взаимодействует с магазином")
    if message.text == "🔙 Назад" or message.text == "🔙 В главное меню":
        logger.info(f"Пользователь {message.from_user.id} возвращается в главное меню из магазина")
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
        await state.clear()
        return
    if message.text.strip().isdigit():
        item_id = int(message.text.strip())
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM shop WHERE id = ?', (item_id,))
            item = cur.fetchone()
        if not item:
            logger.warning(f"Пользователь {message.from_user.id} пытается купить несуществующий товар с ID {item_id}")
            await message.answer(
                "❌ Товар не найден!\n"
                "Введите корректный номер из списка или выберите категорию.",
                reply_markup=get_shop_category_keyboard()
            )
            return
        player_id = message.from_user.id
        gold = get_player_gold(player_id)
        if gold < item[4]:
            logger.warning(f"Пользователь {message.from_user.id} не может купить товар {item[1]}: недостаточно золота")
            await message.answer(
                f"❌ Недостаточно золота!\n"
                f"Нужно: {item[4]} 💰\n"
                f"У вас: {gold} 💰\n\n"
                f"Выберите другой товар или заработайте золото в бою.",
                reply_markup=get_shop_category_keyboard()
            )
            return
        remove_gold(player_id, item[4])
        add_item_to_inventory(player_id, item[1], item[2], item[3], item[4])
        category_emoji = {
            "Зелья": "🧪",
            "Оружие": "⚔️",
            "Экипировка": "🛡️",
            "Аксессуары": "💍",
            "Разное": "📦"
        }.get(item[5], "🎁")
        await message.answer(
            f"{category_emoji} **{item[1]}** приобретён!\n"
            f"{'='*40}\n"
            f"💰 Потрачено: {item[4]} золота\n"
            f"📦 Предмет добавлен в инвентарь\n"
            f"✨ Эффект: {item[3]}\n"
            f"{'='*40}\n\n"
            f"Хотите купить что-то ещё или вернуться в меню?",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🛒 Продолжить покупки")],
                    [KeyboardButton(text="🎒 Открыть инвентарь")],
                    [KeyboardButton(text="🔙 В главное меню")]
                ],
                resize_keyboard=True
            )
        )
        await state.update_data(last_purchase=item[1])
        return
    category_map = {
        "🧪 Зелья": "Зелья",
        "⚔️ Оружие": "Оружие",
        "🛡️ Экипировка": "Экипировка",
        "💍 Аксессуары": "Аксессуары",
        "📦 Разное": "Разное"
    }
    if message.text not in category_map:
        if message.text == "🛒 Продолжить покупки":
            logger.info(f"Пользователь {message.from_user.id} продолжает покупки в магазине")
            await message.answer("Выберите категорию товаров:", reply_markup=get_shop_category_keyboard())
            return
        elif message.text == "🎒 Открыть инвентарь":
            logger.info(f"Пользователь {message.from_user.id} перешёл в инвентарь из магазина")
            await inventory_menu(message, state)
            await state.set_state(GameStates.in_inventory)
            return
        elif message.text == "🔙 В главное меню":
            logger.info(f"Пользователь {message.from_user.id} вернулся в главное меню из магазина")
            await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
            await state.clear()
            return
        logger.warning(f"Пользователь {message.from_user.id} ввёл неверную команду в магазине: {message.text}")
        await message.answer(
            "❌ Неизвестная команда!\n"
            "Выберите категорию из меню или введите номер товара для покупки.",
            reply_markup=get_shop_category_keyboard()
        )
        return
    category = category_map[message.text]
    items = get_shop_items(category)
    if not items:
        logger.warning(f"Пользователь {message.from_user.id} выбрал пустую категорию: {category}")
        await message.answer("❌ В этой категории временно нет товаров!", reply_markup=get_shop_category_keyboard())
        return
    response = f"{get_category_emoji(category)} **КАТЕГОРИЯ: {category}**\n"
    response += f"{'='*40}\n\n"
    for item in items:
        item_emoji = "🎁"
        if "Зелье" in item[2]:
            item_emoji = "🧪"
        elif "Оружие" in item[2]:
            item_emoji = "⚔️"
        elif "Экипировка" in item[2]:
            item_emoji = "🛡️"
        elif "Аксессуар" in item[2]:
            item_emoji = "💍"
        response += f"{item_emoji} **{item[0]}. {item[1]}**\n"
        response += f"   Эффект: {item[3]}\n"
        response += f"   💰 Цена: {item[4]} золота\n"
        response += f"{'-'*40}\n"
    response += f"\n{'='*40}\n"
    response += "🛒 **Чтобы купить товар:**\n"
    response += "→ Введите номер товара (например: `1`)\n\n"
    response += "🔙 **Чтобы вернуться:**\n"
    response += "→ Нажмите кнопку «Назад»"
    await message.answer(response, parse_mode="Markdown")
    await state.update_data(current_category=category)
    return

# Основной цикл программы
async def main():
    init_db()
    print("🤖 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
