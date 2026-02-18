# ============================================================================
# ПОТЕРЯННЫЕ ЗЕМЛИ — ИСПРАВЛЕННАЯ ВЕРСИЯ (БЕЗ ОШИБОК В БОЮ)
# ============================================================================
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

API_TOKEN = os.environ.get('BOT_TOKEN')
if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")

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

CLASSES = {
    "Воин": {"hp_bonus": 20, "atk_bonus": 3, "arm_bonus": 2, "agi_bonus": 0, "description": "🛡️ Высокая живучесть и защита", "emoji": "⚔️"},
    "Маг": {"hp_bonus": -10, "atk_bonus": 5, "arm_bonus": -1, "agi_bonus": 1, "description": "🔮 Сильная атака, но хрупкий", "emoji": "🧙"},
    "Разбойник": {"hp_bonus": 0, "atk_bonus": 2, "arm_bonus": 0, "agi_bonus": 3, "description": "🏃 Высокая ловкость, критические удары", "emoji": "🗡️"},
    "Паладин": {"hp_bonus": 15, "atk_bonus": 1, "arm_bonus": 3, "agi_bonus": -1, "description": "🛡️⚔️ Сбалансированный защитник", "emoji": "🛡️"},
    "Стрелок": {"hp_bonus": -5, "atk_bonus": 4, "arm_bonus": -1, "agi_bonus": 2, "description": "🏹 Дальний бой, высокий урон", "emoji": "🏹"},
    "Друид": {"hp_bonus": 10, "atk_bonus": 2, "arm_bonus": 1, "agi_bonus": 1, "description": "🌿 Природная магия и выносливость", "emoji": "🌿"}
}

# ============================================================================
# ИСПРАВЛЕННАЯ ФУНКЦИЯ ИНИЦИАЛИЗАЦИИ БД (ВСЕ ТАБЛИЦЫ СОЗДАЮТСЯ ПРАВИЛЬНО)
# ============================================================================
def init_db():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    
    # Таблица игроков (с gold)
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
    
    # Таблица монстров (ОБЯЗАТЕЛЬНО!)
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
    
    # Таблица активных боёв (с used_potion)
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
    
    # Таблица инвентаря (БЕЗ лишнего item_id)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            item_name TEXT,
            item_type TEXT,
            effect TEXT,
            equipped BOOLEAN DEFAULT 0,
            slot TEXT,
            bought_price INTEGER
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
    
    conn.commit()
    conn.close()

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (сокращены для экономии места, но полные)
# ============================================================================
def get_player(telegram_id):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM players WHERE telegram_id = ?', (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return row

def create_player(telegram_id, username, hero_slot, hero_name, hero_class):
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
    return True, "✅ Персонаж создан!"

def update_player(telegram_id, **kwargs):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [telegram_id]
    cur.execute(f'UPDATE players SET {set_clause} WHERE telegram_id = ?', values)
    conn.commit()
    conn.close()

def get_all_players(): 
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('SELECT * FROM players ORDER BY hero_slot'); rows = cur.fetchall(); conn.close(); return rows

def get_free_slots():
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('SELECT hero_slot FROM players'); occupied = {row[0] for row in cur.fetchall()}; conn.close(); return [i for i in range(1,7) if i not in occupied]

def get_monster(name):
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('SELECT * FROM monsters WHERE name = ?', (name,)); row = cur.fetchone(); conn.close(); return row

def calculate_damage(attacker_atk, attacker_agi, defender_arm, defender_agi, dice_roll):
    base = max(1, attacker_atk - defender_arm * 0.6)
    agility_mod = (attacker_agi - defender_agi) * 0.4
    dice_mod = (dice_roll - 10) * 1.8
    return max(1, round(base + agility_mod + dice_mod))

def add_gold(player_id, amount):
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('UPDATE players SET gold = gold + ? WHERE telegram_id = ?', (amount, player_id)); conn.commit(); conn.close()

def remove_gold(player_id, amount):
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('UPDATE players SET gold = gold - ? WHERE telegram_id = ?', (amount, player_id)); conn.commit(); conn.close()

def get_player_gold(player_id):
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('SELECT gold FROM players WHERE telegram_id = ?', (player_id,)); result = cur.fetchone(); conn.close(); return result[0] if result else 0

def add_item_to_inventory(player_id, item_name, item_type, effect, bought_price):
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('INSERT INTO inventory (player_id, item_name, item_type, effect, equipped, bought_price) VALUES (?, ?, ?, ?, 0, ?)', (player_id, item_name, item_type, effect, bought_price)); conn.commit(); conn.close()

def get_inventory(player_id):
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('SELECT * FROM inventory WHERE player_id = ?', (player_id,)); items = cur.fetchall(); conn.close(); return items

def get_shop_items(category=None):
    conn = sqlite3.connect('game.db'); cur = conn.cursor()
    if category: cur.execute('SELECT * FROM shop WHERE category = ? ORDER BY price', (category,)); items = cur.fetchall()
    else: cur.execute('SELECT * FROM shop ORDER BY category, price'); items = cur.fetchall()
    conn.close(); return items

def equip_item(player_id, item_id, slot):
    conn = sqlite3.connect('game.db'); cur = conn.cursor()
    cur.execute('UPDATE inventory SET equipped = 0, slot = NULL WHERE player_id = ? AND slot = ?', (player_id, slot))
    cur.execute('UPDATE inventory SET equipped = 1, slot = ? WHERE id = ? AND player_id = ?', (slot, item_id, player_id))
    conn.commit(); conn.close()

def unequip_item(player_id, slot):
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('UPDATE inventory SET equipped = 0, slot = NULL WHERE player_id = ? AND slot = ?', (player_id, slot)); conn.commit(); conn.close()

def sell_item(player_id, item_id):
    conn = sqlite3.connect('game.db'); cur = conn.cursor()
    cur.execute('SELECT bought_price FROM inventory WHERE id = ? AND player_id = ?', (item_id, player_id))
    result = cur.fetchone()
    if not result: conn.close(); return False, "Предмет не найден!"
    sell_price = result[0] // 2; add_gold(player_id, sell_price)
    cur.execute('DELETE FROM inventory WHERE id = ? AND player_id = ?', (item_id, player_id))
    conn.commit(); conn.close(); return True, f"Предмет продан за {sell_price} золота!"

def use_potion_in_battle(player_id, battle_id):
    conn = sqlite3.connect('game.db'); cur = conn.cursor()
    cur.execute('SELECT used_potion FROM active_battles WHERE id = ?', (battle_id,)); battle = cur.fetchone()
    if battle and battle[0]: conn.close(); return False, "Вы уже использовали зелье в этом бою!"
    cur.execute('SELECT id, effect FROM inventory WHERE player_id = ? AND item_type = "Зелье" AND equipped = 0 LIMIT 1', (player_id,)); potion = cur.fetchone()
    if not potion: conn.close(); return False, "Нет зелий в инвентаре!"
    heal = 30 if "+30HP" in potion[1] else 60 if "+60HP" in potion[1] else 100
    cur.execute('DELETE FROM inventory WHERE id = ?', (potion[0],)); cur.execute('UPDATE active_battles SET used_potion = 1 WHERE id = ?', (battle_id,)); conn.commit(); conn.close(); return True, heal

def create_battle(attacker_id, defender_id, attacker_hp, defender_hp, battle_type="pvp"):
    conn = sqlite3.connect('game.db'); cur = conn.cursor()
    cur.execute('INSERT INTO active_battles (attacker_id, defender_id, attacker_hp, defender_hp, status, battle_type, used_potion) VALUES (?, ?, ?, ?, "waiting_attacker", ?, 0)', (attacker_id, defender_id, attacker_hp, defender_hp, battle_type))
    battle_id = cur.lastrowid; conn.commit(); conn.close(); return battle_id

def get_active_battle(player_id):
    conn = sqlite3.connect('game.db'); cur = conn.cursor()
    cur.execute('SELECT * FROM active_battles WHERE (attacker_id = ? OR defender_id = ?) AND status != "completed" ORDER BY id DESC LIMIT 1', (player_id, player_id))
    row = cur.fetchone(); conn.close(); return row

def update_battle(battle_id, **kwargs):
    conn = sqlite3.connect('game.db'); cur = conn.cursor()
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [battle_id]
    cur.execute(f'UPDATE active_battles SET {set_clause} WHERE id = ?', values)
    conn.commit(); conn.close()

def complete_battle(battle_id):
    update_battle(battle_id, status='completed')

def get_main_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Мой персонаж"), KeyboardButton(text="⭐ Прокачка навыков")],
        [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="⚔️ Бой"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="❓ Помощь")]
    ], resize_keyboard=True)

def get_class_keyboard(selected_class=None):
    buttons = [[KeyboardButton(text=f"{'✅ ' if cls_name == selected_class else ''}{cls_data['emoji']} {cls_name}")] for cls_name, cls_data in CLASSES.items()]
    if selected_class: buttons.append([KeyboardButton(text="✅ Подтвердить выбор")])
    buttons.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_battle_type_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚔️ Герой vs Герой")],
        [KeyboardButton(text="👹 Герой vs Монстр")],
        [KeyboardButton(text="🔙 Назад")]
    ], resize_keyboard=True)

def get_free_slots_keyboard():
    slots = get_free_slots()
    if not slots: return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Назад")]], resize_keyboard=True)
    buttons = [[KeyboardButton(text=f"Слот {slot}")] for slot in slots] + [[KeyboardButton(text="🔙 Назад")]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_opponent_keyboard(exclude_id=None):
    players = get_all_players(); buttons = []
    for p in players:
        if not exclude_id or p[0] != exclude_id: buttons.append([KeyboardButton(text=f"{p[3]} ({p[4]})")])
    if not buttons: buttons = [[KeyboardButton(text="Нет доступных противников")]]
    buttons.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_monster_keyboard(floor=None):
    conn = sqlite3.connect('game.db'); cur = conn.cursor()
    if floor:
        cur.execute('SELECT name FROM monsters WHERE floor = ? ORDER BY level', (floor,)); monsters = [r[0] for r in cur.fetchall()]; conn.close()
        buttons = [[KeyboardButton(text=monsters[i]), KeyboardButton(text=monsters[i+1]) if i+1 < len(monsters) else KeyboardButton(text=" ")] for i in range(0, len(monsters), 2)]
    else:
        cur.execute('SELECT DISTINCT floor FROM monsters ORDER BY floor'); floors = [f"Этаж {r[0]}" for r in cur.fetchall()]; conn.close()
        buttons = [[KeyboardButton(text=floor)] for floor in floors]
    buttons.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_upgrade_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❤️ Здоровье (+5)"), KeyboardButton(text="⚔️ Атака (+2)")],
        [KeyboardButton(text="🛡️ Броня (+1)"), KeyboardButton(text="🏃 Ловкость (+1)")],
        [KeyboardButton(text="🔙 Назад")]
    ], resize_keyboard=True)

def get_shop_category_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🧪 Зелья"), KeyboardButton(text="⚔️ Оружие")],
        [KeyboardButton(text="🛡️ Экипировка"), KeyboardButton(text="💍 Аксессуары")],
        [KeyboardButton(text="📦 Разное"), KeyboardButton(text="🔙 Назад")]
    ], resize_keyboard=True)

def get_slot_emoji(slot):
    return {"Оружие 1": "⚔️", "Оружие 2": "🛡️", "Экипировка 1": "🪖", "Экипировка 2": "🧥", "Экипировка 3": "👖", "Экипировка 4": "👢", "Экипировка 5": "🧤", "Экипировка 6": "🧤", "Аксессуар 1": "📿", "Аксессуар 2": "💍", "Аксессуар 3": "⛓️"}.get(slot, "📦")

async def show_character(message, player):
    cls = CLASSES[player[4]]; gold = get_player_gold(player[0])
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('SELECT item_name, slot FROM inventory WHERE player_id = ? AND equipped = 1', (player[0],)); equipped = cur.fetchall(); conn.close()
    equipment_text = "\n".join([f"{get_slot_emoji(slot)} {slot}: {name}" for name, slot in sorted(equipped, key=lambda x: x[1])]) or "📭 Нет экипировки"
    stats = f"👤 **{player[3]}** {cls['emoji']}\n🎭 Класс: {player[4]}\n📊 Уровень: {player[5]} | Опыт: {player[6]}/{player[5]*100}\n⭐ Очков навыков: {player[7]}\n💰 Золото: {gold}\n\n❤️ Здоровье: {player[9]}/{player[8]}\n⚔️ Атака: {player[10]}\n🛡️ Броня: {player[11]}\n🏃 Ловкость: {player[12]}\n\n🏆 Побед: {player[13]} | Поражений: {player[14]}\n\n🛡️ ЭКИПИРОВКА:\n{equipment_text}"
    await message.answer(stats, parse_mode="Markdown", reply_markup=get_main_keyboard())

# ============================================================================
# ОСНОВНЫЕ КОМАНДЫ (с исправленной логикой обработки)
# ============================================================================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if player: await show_character(message, player); await state.set_state(GameStates.choosing_action)
    else:
        free_slots = get_free_slots()
        if not free_slots: await message.answer("❌ Игра заполнена! Максимум 6 игроков.", reply_markup=get_main_keyboard()); return
        await message.answer(f"🎮 Добро пожаловать!\n👥 Игроков: {6-len(free_slots)}/6\n\nСоздайте персонажа:\n1️⃣ Выберите слот (1-6)\n2️⃣ Введите имя\n3️⃣ Выберите класс", reply_markup=get_free_slots_keyboard())
        await state.set_state(GameStates.waiting_for_slot)

@dp.message(GameStates.waiting_for_slot)
async def process_slot(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад": await message.answer("Выберите действие:", reply_markup=get_main_keyboard()); await state.set_state(GameStates.choosing_action); return
    try: slot = int(message.text.split()[1]); assert slot in get_free_slots()
    except: await message.answer("❌ Выберите слот из списка!", reply_markup=get_free_slots_keyboard()); return
    await state.update_data(hero_slot=slot); await message.answer(f"✅ Слот {slot} выбран.\n📝 Введите имя (3-20 символов):"); await state.set_state(GameStates.waiting_for_name)

@dp.message(GameStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3 or len(name) > 20: await message.answer("❌ Имя должно быть 3-20 символов!"); return
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('SELECT hero_name FROM players WHERE hero_name = ?', (name,)); exists = cur.fetchone(); conn.close()
    if exists: await message.answer("❌ Имя занято! Введите другое:"); return
    await state.update_data(hero_name=name)
    text = "🎭 Выберите класс:\n\n" + "\n".join([f"{d['emoji']} **{n}**\n   {d['description']}\n   Бонусы: " + ", ".join([f"{'+' if v>0 else ''}{v}{k}" for k,v in [('HP',d['hp_bonus']),('ATK',d['atk_bonus']),('ARM',d['arm_bonus']),('AGI',d['agi_bonus'])] if v!=0]) for n,d in CLASSES.items()])
    await message.answer(text, parse_mode="Markdown", reply_markup=get_class_keyboard()); await state.set_state(GameStates.waiting_for_class)

@dp.message(GameStates.waiting_for_class)
async def process_class(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад": await message.answer("📝 Введите имя:"); await state.set_state(GameStates.waiting_for_name); return
    cls_text = message.text.strip()
    for prefix in ['✅ ', '⚔️ ', '🧙 ', '🗡️ ', '🛡️ ', '🏹 ', '🌿 ']: cls_text = cls_text.replace(prefix, '', 1)
    if cls_text not in CLASSES: await message.answer("❌ Выберите класс из списка!", reply_markup=get_class_keyboard()); return
    await state.update_data(hero_class=cls_text); cls = CLASSES[cls_text]
    await message.answer(f"🎭 Вы выбрали: **{cls_text}**\n\n{cls['description']}\n\n**Бонусы:**\n❤️ HP: {'+' if cls['hp_bonus']>0 else ''}{cls['hp_bonus']}\n⚔️ ATK: {'+' if cls['atk_bonus']>0 else ''}{cls['atk_bonus']}\n🛡️ ARM: {'+' if cls['arm_bonus']>0 else ''}{cls['arm_bonus']}\n🏃 AGI: {'+' if cls['agi_bonus']>0 else ''}{cls['agi_bonus']}\n\n✅ Нажмите 'Подтвердить выбор'", parse_mode="Markdown", reply_markup=get_class_keyboard(selected_class=cls_text))
    await state.set_state(GameStates.waiting_for_class_confirm)

@dp.message(GameStates.waiting_for_class_confirm)
async def confirm_class(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        text = "🎭 Выберите класс:\n\n" + "\n".join([f"{d['emoji']} **{n}**\n   {d['description']}\n   Бонусы: " + ", ".join([f"{'+' if v>0 else ''}{v}{k}" for k,v in [('HP',d['hp_bonus']),('ATK',d['atk_bonus']),('ARM',d['arm_bonus']),('AGI',d['agi_bonus'])] if v!=0]) for n,d in CLASSES.items()])
        await message.answer(text, parse_mode="Markdown", reply_markup=get_class_keyboard()); await state.set_state(GameStates.waiting_for_class); return
    if message.text == "✅ Подтвердить выбор":
        data = await state.get_data(); slot, name, cls = data['hero_slot'], data['hero_name'], data['hero_class']
        success, msg = create_player(message.from_user.id, message.from_user.username or f"user_{message.from_user.id}", slot, name, cls)
        if success: await show_character(message, get_player(message.from_user.id)); await state.set_state(GameStates.choosing_action)
        else: await message.answer(msg, reply_markup=get_free_slots_keyboard()); await state.set_state(GameStates.waiting_for_slot)
        return
    # Если снова выбран класс
    cls_text = message.text.strip()
    for prefix in ['✅ ', '⚔️ ', '🧙 ', '🗡️ ', '🛡️ ', '🏹 ', '🌿 ']: cls_text = cls_text.replace(prefix, '', 1)
    if cls_text in CLASSES: await state.update_data(hero_class=cls_text); cls = CLASSES[cls_text]; await message.answer(f"🎭 Вы выбрали: **{cls_text}**\n\n{cls['description']}\n\n**Бонусы:**\n❤️ HP: {'+' if cls['hp_bonus']>0 else ''}{cls['hp_bonus']}\n⚔️ ATK: {'+' if cls['atk_bonus']>0 else ''}{cls['atk_bonus']}\n🛡️ ARM: {'+' if cls['arm_bonus']>0 else ''}{cls['arm_bonus']}\n🏃 AGI: {'+' if cls['agi_bonus']>0 else ''}{cls['agi_bonus']}\n\n✅ Нажмите 'Подтвердить выбор'", parse_mode="Markdown", reply_markup=get_class_keyboard(selected_class=cls_text)); return
    await message.answer("❌ Используйте кнопки!")

@dp.message(F.text == "👤 Мой персонаж")
async def my_char(message: types.Message): player = get_player(message.from_user.id); await (show_character(message, player) if player else message.answer("❌ Создайте персонажа: /start"))

@dp.message(F.text == "⭐ Прокачка навыков")
async def upgrade(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if not player: await message.answer("❌ Создайте персонажа: /start"); return
    if player[7] <= 0: await message.answer("❌ Нет очков навыков! Побеждайте монстров.", reply_markup=get_main_keyboard()); return
    await message.answer(f"⭐ ПРОКАЧКА ({player[7]} очков)\n{'='*40}\n👤 {player[3]} ({player[4]})\n📊 Уровень: {player[5]}\n\n❤️ {player[9]}/{player[8]} HP\n⚔️ {player[10]} ATK | 🛡️ {player[11]} ARM | 🏃 {player[12]} AGI\n\nВыберите параметр:", reply_markup=get_upgrade_keyboard())
    await state.set_state(GameStates.choosing_stat_to_upgrade); await state.update_data(player=player)

@dp.message(GameStates.choosing_stat_to_upgrade)
async def process_upgrade(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад": await message.answer("Выберите действие:", reply_markup=get_main_keyboard()); await state.clear(); return
    player = (await state.get_data())['player']; tid = message.from_user.id
    if player[7] <= 0: await message.answer("❌ Нет очков!", reply_markup=get_main_keyboard()); await state.clear(); return
    stat_map = {"❤️ Здоровье (+5)": ("max_hp",5,"Здоровье"), "⚔️ Атака (+2)": ("attack",2,"Атака"), "🛡️ Броня (+1)": ("armor",1,"Броня"), "🏃 Ловкость (+1)": ("agility",1,"Ловкость")}
    if message.text not in stat_map: await message.answer("❌ Выберите из меню!"); return
    col, bonus, name = stat_map[message.text]
    if col == "max_hp": update_player(tid, max_hp=player[8]+bonus, current_hp=player[9]+bonus, skill_points=player[7]-1)
    elif col == "attack": update_player(tid, attack=player[10]+bonus, skill_points=player[7]-1)
    elif col == "armor": update_player(tid, armor=player[11]+bonus, skill_points=player[7]-1)
    elif col == "agility": update_player(tid, agility=player[12]+bonus, skill_points=player[7]-1)
    p = get_player(tid); await message.answer(f"✅ +{bonus} к {name}\n⭐ Осталось: {p[7]}\n\n❤️ {p[9]}/{p[8]} HP\n⚔️ {p[10]} ATK | 🛡️ {p[11]} ARM | 🏃 {p[12]} AGI", reply_markup=get_main_keyboard()); await state.clear()

@dp.message(F.text == "🛒 Магазин")
async def shop(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if not player: await message.answer("❌ Создайте персонажа: /start"); return
    await message.answer(f"🛒 МАГАЗИН\n{'='*40}\n💰 Золото: {get_player_gold(message.from_user.id)}\n\nВыберите категорию:", reply_markup=get_shop_category_keyboard())
    await state.set_state(GameStates.in_shop_category)

@dp.message(GameStates.in_shop_category)
async def shop_category(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад": await message.answer("Выберите действие:", reply_markup=get_main_keyboard()); await state.clear(); return
    cat_map = {"🧪 Зелья": "Зелья", "⚔️ Оружие": "Оружие", "🛡️ Экипировка": "Экипировка", "💍 Аксессуары": "Аксессуары", "📦 Разное": "Разное"}
    if message.text not in cat_map: await message.answer("❌ Выберите категорию!"); return
    cat = cat_map[message.text]; items = get_shop_items(cat)
    if not items: await message.answer("❌ Категория пуста!"); return
    resp = f"🛒 {cat}\n{'='*40}\n\n" + "\n".join([f"{i[0]}. {i[1]} | {i[3]} | 💰 {i[4]}" for i in items]) + f"\n\n{'='*40}\nВведите номер товара или 'Назад':"
    await message.answer(resp); await state.update_data(shop_category=cat)

# ============================================================================
# КРИТИЧЕСКИ ВАЖНО: ОБРАБОТЧИК ПОКУПКИ ТОЛЬКО В СОСТОЯНИИ МАГАЗИНА
# ============================================================================
@dp.message(GameStates.in_shop_category, F.text.regexp(r'^\d+$'))
async def buy_item(message: types.Message, state: FSMContext):
    try: item_id = int(message.text)
    except: await message.answer("❌ Введите номер!"); return
    conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('SELECT * FROM shop WHERE id = ?', (item_id,)); item = cur.fetchone(); conn.close()
    if not item: await message.answer("❌ Товар не найден!"); return
    tid = message.from_user.id; gold = get_player_gold(tid)
    if gold < item[4]: await message.answer(f"❌ Недостаточно золота! Нужно {item[4]}, у вас {gold}"); return
    remove_gold(tid, item[4]); add_item_to_inventory(tid, item[1], item[2], item[3], item[4])
    await message.answer(f"✅ Куплено: {item[1]}\n💰 -{item[4]} золота\n📦 В инвентаре!", reply_markup=get_main_keyboard()); await state.clear()

@dp.message(F.text == "🎒 Инвентарь")
async def inventory(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if not player: await message.answer("❌ Создайте персонажа: /start"); return
    items = get_inventory(message.from_user.id)
    if not items: await message.answer("📭 Инвентарь пуст! Посетите магазин."); return
    resp = "🎒 ИНВЕНТАРЬ\n" + "="*40 + "\n\n"
    slots = {}
    for i in items: s = i[6] if i[6] else "Не экипирован"; slots.setdefault(s, []).append(i)
    for slot in ["Оружие 1","Оружие 2","Экипировка 1","Экипировка 2","Экипировка 3","Экипировка 4","Экипировка 5","Экипировка 6","Аксессуар 1","Аксессуар 2","Аксессуар 3","Не экипирован"]:
        if slot in slots: resp += f"\n{get_slot_emoji(slot)} {slot}:\n" + "\n".join([f"  {i[0]}. {i[2]} | {i[3]} | {'✅' if i[5] else '🔲'}" for i in slots[slot]])
    resp += f"\n\n{'='*40}\nКоманды:\n• Экипировать [номер]\n• Снять [слот]\n• Продать [номер]"
    await message.answer(resp); await state.set_state(GameStates.in_inventory)

@dp.message(GameStates.in_inventory)
async def inv_handler(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад": await message.answer("Выберите действие:", reply_markup=get_main_keyboard()); await state.clear(); return
    if message.text.startswith("Экипировать "):
        try: item_id = int(message.text.split()[1])
        except: await message.answer("❌ Формат: Экипировать [номер]"); return
        conn = sqlite3.connect('game.db'); cur = conn.cursor(); cur.execute('SELECT * FROM inventory WHERE id = ? AND player_id = ?', (item_id, message.from_user.id)); item = cur.fetchone(); conn.close()
        if not item: await message.answer("❌ Предмет не найден!"); return
        slot_map = {"Оружие 1":"Оружие 1","Оружие 2":"Оружие 2","Экипировка 1":"Экипировка 1","Экипировка 2":"Экипировка 2","Экипировка 3":"Экипировка 3","Экипировка 4":"Экипировка 4","Экипировка 5":"Экипировка 5","Экипировка 6":"Экипировка 6","Аксессуар 1":"Аксессуар 1","Аксессуар 2":"Аксессуар 2","Аксессуар 3":"Аксессуар 3"}
        slot = slot_map.get(item[3]); 
        if not slot: await message.answer("❌ Нельзя экипировать!"); return
        equip_item(message.from_user.id, item_id, slot); await message.answer(f"✅ {item[2]} в {slot}!")
    elif message.text.startswith("Снять "):
        slot = message.text.split(maxsplit=1)[1]; unequip_item(message.from_user.id, slot); await message.answer(f"✅ Снято с {slot}!")
    elif message.text.startswith("Продать "):
        try: item_id = int(message.text.split()[1])
        except: await message.answer("❌ Формат: Продать [номер]"); return
        success, msg = sell_item(message.from_user.id, item_id); await message.answer(msg)
    else: await message.answer("❌ Неизвестная команда!")

@dp.message(F.text == "⚔️ Бой")
async def battle_menu(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if not player: await message.answer("❌ Создайте персонажа: /start"); return
    await message.answer("⚔️ ВЫБЕРИТЕ ТИП БОЯ:\n⚔️ **Герой vs Герой** — дуэль\n👹 **Герой vs Монстр** — подземелье", parse_mode="Markdown", reply_markup=get_battle_type_keyboard())
    await state.set_state(GameStates.choosing_battle_type)

@dp.message(GameStates.choosing_battle_type)
async def choose_battle(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад": await message.answer("Выберите действие:", reply_markup=get_main_keyboard()); await state.set_state(GameStates.choosing_action); return
    if message.text == "⚔️ Герой vs Герой":
        await message.answer("👥 ВЫБЕРИТЕ ПРОТИВНИКА:\n(нельзя выбрать себя)", reply_markup=get_opponent_keyboard(exclude_id=message.from_user.id))
        await state.set_state(GameStates.choosing_opponent); await state.update_data(battle_type="pvp")
    elif message.text == "👹 Герой vs Монстр":
        await message.answer("🏰 ВЫБЕРИТЕ ЭТАЖ:", reply_markup=get_monster_keyboard())
        await state.set_state(GameStates.choosing_opponent); await state.update_data(battle_type="pve")
    else: await message.answer("❌ Выберите тип боя!")

@dp.message(GameStates.choosing_opponent)
async def choose_opponent(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад": await battle_menu(message, state); return
    data = await state.get_data(); bt = data.get('battle_type')
    if bt == "pvp":
        opp_name = message.text.split(' (')[0]; opp = next((p for p in get_all_players() if p[3] == opp_name), None)
        if not opp: await message.answer("❌ Противник не найден!"); return
        if opp[0] == message.from_user.id: await message.answer("❌ Нельзя с собой!"); return
        att = get_player(message.from_user.id); bid = create_battle(att[0], opp[0], att[9], opp[9], "pvp")
        try: await bot.send_message(opp[0], f"⚔️ ВЫЗОВ!\n{att[3]} вызывает вас!\nДождитесь его броска...")
        except: await message.answer(f"⚠️ {opp_name} не запустил бота (/start)")
        await message.answer(f"⚔️ БОЙ НАЧАТ!\n{'='*30}\n👤 {att[3]} ({att[4]})\n❤️ {att[9]}/{att[8]} HP\n⚔️ {att[10]} ATK | 🛡️ {att[11]} ARM | 🏃 {att[12]} AGI\n\n👤 {opp_name} ({opp[4]})\n❤️ {opp[9]}/{opp[8]} HP\n⚔️ {opp[10]} ATK | 🛡️ {opp[11]} ARM | 🏃 {opp[12]} AGI\n{'='*30}\n\n🎲 {att[3]}, киньте кубик (1-20):")
        await state.update_data(battle_id=bid, attacker=att, defender=opp); await state.set_state(GameStates.waiting_attacker_dice)
    elif bt == "pve":
        if message.text.startswith("Этаж"):
            floor = int(message.text.split()[1]); await state.update_data(floor=floor)
            await message.answer(f"👹 МОНСТРЫ ЭТАЖА {floor}:", reply_markup=get_monster_keyboard(floor=floor))
        else:
            mon = get_monster(message.text)
            if not mon: await message.answer("❌ Монстр не найден!"); return
            att = get_player(message.from_user.id)
            await state.update_data(attacker=att, monster=mon, monster_name=message.text, attacker_hp=att[9], monster_hp=mon[4], round_num=1)
            await message.answer(f"⚔️ БОЙ НАЧАТ!\n{'='*30}\n👤 {att[3]} ({att[4]})\n❤️ {att[9]}/{att[8]} HP\n⚔️ {att[10]} ATK | 🛡️ {att[11]} ARM | 🏃 {att[12]} AGI\n\n👹 {message.text} (ур. {mon[3]})\n❤️ {mon[4]} HP\n⚔️ {mon[5]} ATK | 🛡️ {mon[6]} ARM | 🏃 {mon[7]} AGI\n{'='*30}\n\n🎲 Киньте кубик для себя (1-20):")
            await state.set_state(GameStates.waiting_attacker_dice)

# ============================================================================
# ИСПРАВЛЕННЫЕ ОБРАБОТЧИКИ БОЯ (числа НЕ перехватываются магазином)
# ============================================================================
@dp.message(GameStates.waiting_attacker_dice)
async def att_dice(message: types.Message, state: FSMContext):
    try: dice = int(message.text); assert 1 <= dice <= 20
    except: await message.answer("❌ Введите число 1-20!"); return
    data = await state.get_data(); bt = data.get('battle_type')
    if bt == "pvp":
        bid = data['battle_id']; defn = data['defender']; att = data['attacker']
        update_battle(bid, attacker_dice=dice, status='waiting_defender')
        try: await bot.send_message(defn[0], f"🎲 {att[3]} бросил: {dice}\nВаша очередь! (1-20):"); await message.answer(f"✅ Бросок ({dice}) отправлен {defn[3]}.\nОжидайте...")
        except: await message.answer(f"❌ Не удалось отправить {defn[3]}")
        await state.clear()  # Очищаем состояние атакующего
    else:  # PvE
        await state.update_data(attacker_dice=dice)
        await message.answer(f"🎲 Теперь киньте кубик для {data['monster_name']} (1-20):")
        await state.set_state(GameStates.waiting_monster_dice)

@dp.message(GameStates.waiting_monster_dice)
async def mon_dice(message: types.Message, state: FSMContext):
    try: dice = int(message.text); assert 1 <= dice <= 20
    except: await message.answer("❌ Введите число 1-20!"); return
    data = await state.get_data(); att = data['attacker']; mon = data['monster']; att_dice = data['attacker_dice']; rn = data.get('round_num',1); att_hp = data.get('attacker_hp',att[9]); mon_hp = data.get('monster_hp',mon[4])
    att_dmg = calculate_damage(att[10],att[12],mon[6],mon[7],att_dice); mon_dmg = calculate_damage(mon[5],mon[7],att[11],att[12],dice)
    if att_dice >= 18: att_dmg = round(att_dmg*1.8)
    if dice >= 18: mon_dmg = round(mon_dmg*1.8)
    new_att_hp = max(0, att_hp - mon_dmg); new_mon_hp = max(0, mon_hp - att_dmg)
    log = f"🎲 РАУНД {rn}\n{'='*40}\n{('💥 КРИТ ' + att[3] + '! Бросок ' + str(att_dice) + ' → ' + str(att_dmg) + ' урона') if att_dice>=18 else ('⚔️ ' + att[3] + ' атакует: ' + str(att_dice) + ' → ' + str(att_dmg) + ' урона')}\n❤️ {mon[2]}: {mon_hp} → {new_mon_hp} HP\n{'-'*40}\n{('👹 КРИТ ' + mon[2] + '! Бросок ' + str(dice) + ' → ' + str(mon_dmg) + ' урона') if dice>=18 else ('👹 ' + mon[2] + ' атакует: ' + str(dice) + ' → ' + str(mon_dmg) + ' урона')}\n❤️ {att[3]}: {att_hp} → {new_att_hp} HP\n{'='*40}\n📊 ИТОГ: {att[3]} {new_att_hp}/{att[8]} HP | {mon[2]} {new_mon_hp}/{mon[4]} HP"
    await message.answer(log); update_player(att[0], current_hp=new_att_hp)
    if new_mon_hp <= 0:
        exp = mon[8]; gold = mon[8]; new_exp = att[6] + exp; exp_next = att[5]*100
        add_gold(att[0], gold)
        if new_exp >= exp_next:
            update_player(att[0], level=att[5]+1, exp=new_exp-exp_next, skill_points=att[7]+5, max_hp=att[8]+10, current_hp=att[8]+10, attack=att[10]+1, armor=att[11]+1, agility=att[12]+1, wins=att[13]+1)
            await message.answer(f"✅ ПОБЕДА! {att[3]} достиг {att[5]+1} уровня!\n✨ +{exp} опыта | 💰 +{gold} золота\n+5 очков | +10 HP | +1 ко всем параметрам")
        else:
            update_player(att[0], exp=new_exp, current_hp=att[8], wins=att[13]+1)
            await message.answer(f"✅ ПОБЕДА! +{exp} опыта | 💰 +{gold} золота ({new_exp}/{exp_next})")
        await state.clear(); await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
    elif new_att_hp <= 0:
        update_player(att[0], current_hp=att[8], losses=att[14]+1)
        await message.answer("☠️ Пал в бою...\n✨ Воскрешение!"); await state.clear(); await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
    else:
        await state.update_data(attacker_hp=new_att_hp, monster_hp=new_mon_hp, round_num=rn+1)
        await message.answer(f"🎲 РАУНД {rn+1}\nВаше здоровье: {new_att_hp}/{att[8]} HP\nЗдоровье {mon[2]}: {new_mon_hp}/{mon[4]} HP\nКиньте кубик для себя (1-20):")
        await state.set_state(GameStates.waiting_attacker_dice)

# ============================================================================
# ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ДЛЯ PvP БОЁВ (только числа и команда зелья)
# ============================================================================
@dp.message()
async def global_handler(message: types.Message, state: FSMContext):
    # Команда зелья в бою
    if message.text == "🧪 Использовать зелье":
        battle = get_active_battle(message.from_user.id)
        if not battle or battle[8] == 'completed': await message.answer("❌ Нет активного боя!"); return
        success, res = use_potion_in_battle(message.from_user.id, battle[0])
        if not success: await message.answer(res); return
        p = get_player(message.from_user.id); new_hp = min(p[8], p[9] + res); update_player(message.from_user.id, current_hp=new_hp)
        await message.answer(f"🧪 Зелье использовано! +{res} HP\n❤️ {new_hp}/{p[8]} HP\n⏭️ Пропущен ход атаки.")
        return
    
    # Обработка чисел ТОЛЬКО для активных боев (PvP)
    try: dice = int(message.text); assert 1 <= dice <= 20
    except: return  # Не число или не в диапазоне — игнорируем
    
    battle = get_active_battle(message.from_user.id)
    if not battle or battle[8] == 'completed': return
    
    is_att = battle[1] == message.from_user.id; is_def = battle[2] == message.from_user.id
    if not (is_att or is_def): return
    
    if is_att and battle[8] == 'waiting_attacker':
        await process_pvp_attacker_dice(message, battle, dice, state)
    elif is_def and battle[8] == 'waiting_defender':
        await process_pvp_defender_dice(message, battle, dice, state)
    elif is_att and battle[8] == 'waiting_defender':
        await message.answer("⏳ Ожидайте броска противника...")
    elif is_def and battle[8] == 'waiting_attacker':
        await message.answer("⏳ Ожидайте броска противника...")

async def process_pvp_attacker_dice(message, battle, dice, state):
    att = get_player(battle[1]); defn = get_player(battle[2])
    update_battle(battle[0], attacker_dice=dice, status='waiting_defender')
    try: await bot.send_message(defn[0], f"🎲 {att[3]} бросил: {dice}\nВаша очередь! (1-20):")
    except: pass
    await message.answer(f"✅ Бросок ({dice}) отправлен {defn[3]}.\nОжидайте...")

async def process_pvp_defender_dice(message, battle, dice, state):
    att = get_player(battle[1])
    defn = get_player(battle[2])
    att_dice = battle[3]
    rn = battle[7] or 1
    att_hp = battle[5] or att[9]
    def_hp = battle[6] or defn[9]
    
    att_dmg = calculate_damage(att[10], att[12], defn[11], defn[12], att_dice)
    def_dmg = calculate_damage(defn[10], defn[12], att[11], att[12], dice)
    
    # Увороты
    if random.randint(1, 100) <= min(70, max(0, (defn[12] - att[12]) * 2)):
        att_dmg = 0
    if random.randint(1, 100) <= min(70, max(0, (att[12] - defn[12]) * 2)):
        def_dmg = 0
    
    # Криты
    if att_dice >= 18 and att_dmg > 0:
        att_dmg = round(att_dmg * 1.8)
    if dice >= 18 and def_dmg > 0:
        def_dmg = round(def_dmg * 1.8)
    
    new_att_hp = max(0, att_hp - def_dmg)
    new_def_hp = max(0, def_hp - att_dmg)
    
    log_lines = [f"🎲 РАУНД {rn}", "=" * 40]
    
    if att_dmg == 0:
        log_lines.append(f"💨 {defn[3]} уворачивается от {att[3]}!")
    elif att_dice >= 18:
        log_lines.append(f"💥 КРИТ {att[3]}! {att_dice} → {att_dmg} урона")
    else:
        log_lines.append(f"⚔️ {att[3]} атакует: {att_dice} → {att_dmg} урона")
    
    if att_dmg > 0:
        log_lines.append(f"❤️ {defn[3]}: {def_hp} → {new_def_hp} HP")
    
    log_lines.append("-" * 40)
    
    if def_dmg == 0:
        log_lines.append(f"💨 {att[3]} уворачивается от {defn[3]}!")
    elif dice >= 18:
        log_lines.append(f"💥 КРИТ {defn[3]}! {dice} → {def_dmg} урона")
    else:
        log_lines.append(f"⚔️ {defn[3]} атакует: {dice} → {def_dmg} урона")
    
    if def_dmg > 0:
        log_lines.append(f"❤️ {att[3]}: {att_hp} → {new_att_hp} HP")
    
    log_lines.append("=" * 40)
    log_lines.append(f"📊 ИТОГ: {att[3]} {new_att_hp}/{att[8]} HP | {defn[3]} {new_def_hp}/{defn[8]} HP")
    
    log = "\n".join(log_lines)
    await message.answer(log)
    
    # Отправка лога атакующему (в отдельном блоке try-except)
    try:
        await bot.send_message(att[0], log)
    except:
        pass
    
    update_player(att[0], current_hp=new_att_hp)
    update_player(defn[0], current_hp=new_def_hp)
    
    # Проверка завершения боя
    if new_att_hp <= 0 and new_def_hp <= 0:
        result = "⚔️ НИЧЬЯ!"
        update_player(att[0], current_hp=att[8])
        update_player(defn[0], current_hp=defn[8])
        complete_battle(battle[0])
    elif new_def_hp <= 0:
        result = f"✅ {att[3]} победил {defn[3]}!"
        update_player(att[0], wins=att[13] + 1, current_hp=att[8])
        update_player(defn[0], losses=defn[14] + 1, current_hp=defn[8])
        complete_battle(battle[0])
    elif new_att_hp <= 0:
        result = f"✅ {defn[3]} победил {att[3]}!"
        update_player(defn[0], wins=defn[13] + 1, current_hp=defn[8])
        update_player(att[0], losses=att[14] + 1, current_hp=att[8])
        complete_battle(battle[0])
    else:
        # Продолжение боя
        update_battle(battle[0], attacker_hp=new_att_hp, defender_hp=new_def_hp, round_num=rn + 1, status='waiting_attacker')
        try:
            await bot.send_message(att[0], f"🎲 РАУНД {rn + 1}\nВаше здоровье: {new_att_hp}/{att[8]} HP\nЗдоровье {defn[3]}: {new_def_hp}/{defn[8]} HP\nКиньте кубик (1-20):")
        except:
            pass
        await message.answer(f"🎲 РАУНД {rn + 1}\nВаше здоровье: {new_def_hp}/{defn[8]} HP\nЗдоровье {att[3]}: {new_att_hp}/{att[8]} HP\nОжидайте броска...")
        return
    
    await message.answer(f"{result}\n\nВыберите действие:", reply_markup=get_main_keyboard())
    try:
        await bot.send_message(att[0], f"{result}\n\nВыберите действие:", reply_markup=get_main_keyboard())
    except:
        pass

@dp.message(F.text == "📊 Статистика")
async def stats(message: types.Message):
    players = get_all_players()
    if not players: await message.answer("📊 Нет игроков!"); return
    text = "📊 СТАТИСТИКА:\n" + "="*40 + "\n"
    for p in players:
        cls = CLASSES[p[4]]; wr = round(p[13]/(p[13]+p[14])*100,1) if p[13]+p[14]>0 else 0
        text += f"👤 {p[3]} {cls['emoji']}\n   🎭 {p[4]} | 📊 ур. {p[5]}\n   ❤️ {p[9]}/{p[8]} HP\n   ⚔️ {p[10]} ATK | 🛡️ {p[11]} ARM | 🏃 {p[12]} AGI\n   🏆 {p[13]} побед | {p[14]} пораж. | {wr}%\n{'='*40}\n"
    await message.answer(text)

@dp.message(F.text == "❓ Помощь")
async def help_cmd(message: types.Message):
    await message.answer("❓ ПОМОЩЬ:\n🎲 Кидайте кубик d20 и вводите результат.\n⚔️ PvP: после выбора противника он получит уведомление.\n👹 PvE: вводите оба броска (свой и за монстра).\n❤️ После смерти — воскрешение с полным здоровьем.\n✨ За победы — опыт и золото.\n⭐ Прокачка: улучшайте характеристики.\n🛒 Магазин: покупайте зелья, оружие, экипировку.\n🎒 Инвентарь: экипируйте предметы.\n🧪 Зелья в бою: 1 раз за бой (пропускает ход).\n\nКоманда: /start")

async def main():
    init_db(); print("🤖 Бот запускается..."); await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
