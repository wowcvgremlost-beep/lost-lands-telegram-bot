# ============================================================================
# ПОТЕРЯННЫЕ ЗЕМЛИ — ПОЛНОСТЬЮ РАБОЧАЯ ВЕРСИЯ
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

# Токен из переменной окружения
API_TOKEN = os.environ.get('BOT_TOKEN')
if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Добавьте его в переменные окружения Railway.")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния FSM
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

# Классы персонажей
CLASSES = {
    "Воин": {
        "hp_bonus": 20,
        "atk_bonus": 3,
        "arm_bonus": 2,
        "agi_bonus": 0,
        "description": "🛡️ Высокая живучесть и защита",
        "emoji": "⚔️"
    },
    "Маг": {
        "hp_bonus": -10,
        "atk_bonus": 5,
        "arm_bonus": -1,
        "agi_bonus": 1,
        "description": "🔮 Сильная атака, но хрупкий",
        "emoji": "🧙"
    },
    "Разбойник": {
        "hp_bonus": 0,
        "atk_bonus": 2,
        "arm_bonus": 0,
        "agi_bonus": 3,
        "description": "🏃 Высокая ловкость, критические удары",
        "emoji": "🗡️"
    },
    "Паладин": {
        "hp_bonus": 15,
        "atk_bonus": 1,
        "arm_bonus": 3,
        "agi_bonus": -1,
        "description": "🛡️⚔️ Сбалансированный защитник",
        "emoji": "🛡️"
    },
    "Стрелок": {
        "hp_bonus": -5,
        "atk_bonus": 4,
        "arm_bonus": -1,
        "agi_bonus": 2,
        "description": "🏹 Дальний бой, высокий урон",
        "emoji": "🏹"
    },
    "Друид": {
        "hp_bonus": 10,
        "atk_bonus": 2,
        "arm_bonus": 1,
        "agi_bonus": 1,
        "description": "🌿 Природная магия и выносливость",
        "emoji": "🌿"
    }
}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
    
    conn.commit()
    conn.close()

# Вспомогательные функции для работы с боями
def create_battle(attacker_id, defender_id, attacker_hp, defender_hp, battle_type="pvp"):
    """Создать новый бой в БД"""
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO active_battles 
        (attacker_id, defender_id, attacker_hp, defender_hp, status, battle_type)
        VALUES (?, ?, ?, ?, 'waiting_attacker', ?)
    ''', (attacker_id, defender_id, attacker_hp, defender_hp, battle_type))
    battle_id = cur.lastrowid
    conn.commit()
    conn.close()
    return battle_id

def get_active_battle(player_id):
    """Получить активный бой для игрока (как атакующего или защитника)"""
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM active_battles 
        WHERE (attacker_id = ? OR defender_id = ?) 
        AND status != 'completed'
        ORDER BY id DESC LIMIT 1
    ''', (player_id, player_id))
    row = cur.fetchone()
    conn.close()
    return row

def update_battle(battle_id, **kwargs):
    """Обновить данные боя"""
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [battle_id]
    cur.execute(f'UPDATE active_battles SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()

def complete_battle(battle_id):
    """Завершить бой"""
    update_battle(battle_id, status='completed')

# Вспомогательные функции для работы с игроками
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
        return False, "❌ В игре уже 6 игроков! Максимум достигнут."
    
    cur.execute('SELECT hero_name FROM players WHERE hero_name = ?', (hero_name,))
    if cur.fetchone():
        conn.close()
        return False, f"❌ Имя '{hero_name}' уже занято!"
    
    cur.execute('SELECT hero_slot FROM players WHERE hero_slot = ?', (hero_slot,))
    if cur.fetchone():
        conn.close()
        return False, f"❌ Слот {hero_slot} уже занят!"
    
    cls = CLASSES[hero_class]
    cur.execute('''
        INSERT INTO players 
        (telegram_id, username, hero_slot, hero_name, hero_class, 
         max_hp, current_hp, attack, armor, agility)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        telegram_id, username, hero_slot, hero_name, hero_class,
        100 + cls['hp_bonus'],
        100 + cls['hp_bonus'],
        10 + cls['atk_bonus'],
        5 + cls['arm_bonus'],
        5 + cls['agi_bonus']
    ))
    
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
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM players ORDER BY hero_slot')
    rows = cur.fetchall()
    conn.close()
    return rows

def get_free_slots():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT hero_slot FROM players')
    occupied = {row[0] for row in cur.fetchall()}
    conn.close()
    return [i for i in range(1, 7) if i not in occupied]

def get_monster(name):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM monsters WHERE name = ?', (name,))
    row = cur.fetchone()
    conn.close()
    return row

def calculate_damage(attacker_atk, attacker_agi, defender_arm, defender_agi, dice_roll):
    base_damage = max(1, attacker_atk - defender_arm * 0.6)
    agility_mod = (attacker_agi - defender_agi) * 0.4
    dice_mod = (dice_roll - 10) * 1.8
    total = base_damage + agility_mod + dice_mod
    return max(1, round(total))

# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мой персонаж"), KeyboardButton(text="⭐ Прокачка навыков")],
            [KeyboardButton(text="⚔️ Бой"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )

def get_class_keyboard(selected_class=None):
    buttons = []
    for cls_name, cls_data in CLASSES.items():
        prefix = "✅ " if cls_name == selected_class else ""
        buttons.append([KeyboardButton(text=f"{prefix}{cls_data['emoji']} {cls_name}")])
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
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    buttons = [[KeyboardButton(text=f"Слот {slot}")] for slot in slots]
    buttons.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_opponent_keyboard(exclude_telegram_id=None):
    players = get_all_players()
    buttons = []
    for player in players:
        if exclude_telegram_id and player[0] == exclude_telegram_id:
            continue
        buttons.append([KeyboardButton(text=f"{player[3]} ({player[4]})")])
    if not buttons:
        buttons = [[KeyboardButton(text="Нет доступных противников")]]
    buttons.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_monster_keyboard(floor=None):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    if floor:
        cur.execute('SELECT name FROM monsters WHERE floor = ? ORDER BY level', (floor,))
        monsters = [row[0] for row in cur.fetchall()]
        conn.close()
        buttons = []
        for i in range(0, len(monsters), 2):
            row = [KeyboardButton(text=monsters[i])]
            if i + 1 < len(monsters):
                row.append(KeyboardButton(text=monsters[i + 1]))
            buttons.append(row)
        buttons.append([KeyboardButton(text="🔙 Назад")])
        return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    else:
        cur.execute('SELECT DISTINCT floor FROM monsters ORDER BY floor')
        floors = [f"Этаж {row[0]}" for row in cur.fetchall()]
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

# Команды
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    player = get_player(telegram_id)
    
    if player:
        await show_character(message, player)
        await state.set_state(GameStates.choosing_action)
    else:
        free_slots = get_free_slots()
        if not free_slots:
            await message.answer(
                "❌ Игра заполнена! Максимум 6 игроков.\n"
                "Дождитесь, пока кто-то освободит слот.",
                reply_markup=get_main_keyboard()
            )
            return
        
        await message.answer(
            f"🎮 Добро пожаловать в Потерянные земли!\n\n"
            f"👥 Игроков в игре: {6 - len(free_slots)}/6\n\n"
            "Создайте персонажа:\n"
            "1️⃣ Выберите свободный слот (1-6)\n"
            "2️⃣ Введите уникальное имя\n"
            "3️⃣ Выберите класс и подтвердите",
            reply_markup=get_free_slots_keyboard()
        )
        await state.set_state(GameStates.waiting_for_slot)

@dp.message(GameStates.waiting_for_slot)
async def process_slot_selection(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
        await state.set_state(GameStates.choosing_action)
        return
    
    try:
        slot = int(message.text.split()[1])
        if slot not in get_free_slots():
            raise ValueError
    except:
        await message.answer("❌ Выберите слот из списка!", reply_markup=get_free_slots_keyboard())
        return
    
    await state.update_data(hero_slot=slot)
    await message.answer(f"✅ Слот {slot} выбран.\n📝 Введите имя персонажа (3-20 символов):")
    await state.set_state(GameStates.waiting_for_name)

@dp.message(GameStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    hero_name = message.text.strip()
    if len(hero_name) < 3 or len(hero_name) > 20:
        await message.answer("❌ Имя должно быть от 3 до 20 символов!")
        return
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT hero_name FROM players WHERE hero_name = ?', (hero_name,))
    if cur.fetchone():
        conn.close()
        await message.answer("❌ Имя занято! Введите другое:")
        return
    conn.close()
    
    await state.update_data(hero_name=hero_name)
    
    classes_text = "🎭 Выберите класс:\n\n"
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
async def process_class_selection(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await message.answer("📝 Введите имя персонажа:")
        await state.set_state(GameStates.waiting_for_name)
        return
    
    class_text = message.text.strip()
    for prefix in ['✅ ', '⚔️ ', '🧙 ', '🗡️ ', '🛡️ ', '🏹 ', '🌿 ']:
        if class_text.startswith(prefix):
            class_text = class_text[len(prefix):]
            break
    
    if class_text not in CLASSES:
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
async def confirm_class_selection(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        classes_text = "🎭 Выберите класс:\n\n"
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
            player = get_player(telegram_id)
            await show_character(message, player)
            await state.set_state(GameStates.choosing_action)
        else:
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

async def show_character(message: types.Message, player):
    cls = CLASSES[player[4]]
    stats_text = (
        f"👤 **{player[3]}** {cls['emoji']}\n"
        f"🎭 Класс: {player[4]}\n"
        f"📊 Уровень: {player[5]} | Опыт: {player[6]}/{player[5] * 100}\n"
        f"⭐ Очков навыков: {player[7]}\n\n"
        f"❤️ Здоровье: {player[9]}/{player[8]}\n"
        f"⚔️ Атака: {player[10]}\n"
        f"🛡️ Броня: {player[11]}\n"
        f"🏃 Ловкость: {player[12]}\n\n"
        f"🏆 Побед: {player[13]} | Поражений: {player[14]}"
    )
    await message.answer(stats_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.message(F.text == "👤 Мой персонаж")
async def my_character(message: types.Message):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Создайте персонажа: /start")
        return
    await show_character(message, player)

@dp.message(F.text == "⭐ Прокачка навыков")
async def upgrade_skills(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Создайте персонажа: /start")
        return
    
    if player[7] <= 0:
        await message.answer(
            "❌ У вас нет очков навыков!\n"
            "Победите монстров, чтобы получить опыт и повысить уровень.",
            reply_markup=get_main_keyboard()
        )
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
    if message.text == "🔙 Назад":
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    data = await state.get_data()
    player = data['player']
    telegram_id = message.from_user.id
    
    if player[7] <= 0:
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
        await message.answer("❌ Выберите параметр из меню!")
        return
    
    stat_db, bonus, stat_name = stat_map[message.text]
    
    # Обновляем параметр
    if stat_db == "max_hp":
        update_player(telegram_id, 
                     max_hp=player[8] + bonus,
                     current_hp=player[9] + bonus,
                     skill_points=player[7] - 1)
    elif stat_db == "attack":
        update_player(telegram_id, attack=player[10] + bonus, skill_points=player[7] - 1)
    elif stat_db == "armor":
        update_player(telegram_id, armor=player[11] + bonus, skill_points=player[7] - 1)
    elif stat_db == "agility":
        update_player(telegram_id, agility=player[12] + bonus, skill_points=player[7] - 1)
    
    # Получаем обновлённые данные
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

@dp.message(F.text == "⚔️ Бой")
async def battle_menu(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Создайте персонажа: /start")
        return
    
    await message.answer(
        "⚔️ ВЫБЕРИТЕ ТИП БОЯ:\n"
        "⚔️ **Герой vs Герой** — дуэль с другим игроком\n"
        "👹 **Герой vs Монстр** — бой с монстром подземелья",
        parse_mode="Markdown",
        reply_markup=get_battle_type_keyboard()
    )
    await state.set_state(GameStates.choosing_battle_type)

@dp.message(GameStates.choosing_battle_type)
async def choose_battle_type(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
        await state.set_state(GameStates.choosing_action)
        return
    
    if message.text == "⚔️ Герой vs Герой":
        await message.answer(
            "👥 ВЫБЕРИТЕ ПРОТИВНИКА:\n(нельзя выбрать себя)",
            reply_markup=get_opponent_keyboard(exclude_telegram_id=message.from_user.id)
        )
        await state.set_state(GameStates.choosing_opponent)
        await state.update_data(battle_type="pvp")
    
    elif message.text == "👹 Герой vs Монстр":
        await message.answer("🏰 ВЫБЕРИТЕ ЭТАЖ:", reply_markup=get_monster_keyboard())
        await state.set_state(GameStates.choosing_opponent)
        await state.update_data(battle_type="pve")
    
    else:
        await message.answer("❌ Выберите тип боя из меню!")

@dp.message(GameStates.choosing_opponent)
async def choose_opponent(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await battle_menu(message, state)
        return
    
    data = await state.get_data()
    battle_type = data.get('battle_type')
    
    if battle_type == "pvp":
        opponent_name = message.text.split(' (')[0]
        opponent = None
        for player in get_all_players():
            if player[3] == opponent_name:
                opponent = player
                break
        
        if not opponent:
            await message.answer("❌ Противник не найден!")
            return
        
        if opponent[0] == message.from_user.id:
            await message.answer("❌ Нельзя сражаться с собой!")
            return
        
        attacker = get_player(message.from_user.id)
        
        # Создаем бой в БД
        battle_id = create_battle(
            attacker[0], 
            opponent[0], 
            attacker[9], 
            opponent[9], 
            "pvp"
        )
        
        # Отправляем уведомление второму игроку
        try:
            await bot.send_message(
                chat_id=opponent[0],
                text=f"⚔️ ВЫЗОВ НА ДУЭЛЬ!\n"
                     f"{attacker[3]} вызывает вас на бой!\n"
                     f"Дождитесь его броска кубика..."
            )
        except:
            await message.answer(f"⚠️ {opponent_name} не запустил бота. Он должен написать /start")
        
        await message.answer(
            f"⚔️ БОЙ НАЧАТ!\n"
            f"{'='*30}\n"
            f"👤 {attacker[3]} ({attacker[4]})\n"
            f"❤️ {attacker[9]}/{attacker[8]} HP\n"
            f"⚔️ ATK: {attacker[10]} | 🛡️ ARM: {attacker[11]} | 🏃 AGI: {attacker[12]}\n\n"
            f"👤 {opponent_name} ({opponent[4]})\n"
            f"❤️ {opponent[9]}/{opponent[8]} HP\n"
            f"⚔️ ATK: {opponent[10]} | 🛡️ ARM: {opponent[11]} | 🏃 AGI: {opponent[12]}\n"
            f"{'='*30}\n\n"
            f"🎲 {attacker[3]}, киньте кубик d20 и введите результат (1-20):"
        )
        
        # Сохраняем данные боя в состояние
        await state.update_data(
            battle_id=battle_id,
            battle_type="pvp",
            attacker=attacker,
            defender=opponent
        )
        await state.set_state(GameStates.waiting_attacker_dice)
    
    elif battle_type == "pve":
        if message.text.startswith("Этаж"):
            floor = int(message.text.split()[1])
            await state.update_data(floor=floor)
            await message.answer(f"👹 МОНСТРЫ ЭТАЖА {floor}:", reply_markup=get_monster_keyboard(floor=floor))
        else:
            monster_name = message.text
            monster = get_monster(monster_name)
            if not monster:
                await message.answer("❌ Монстр не найден!")
                return
            
            attacker = get_player(message.from_user.id)
            await state.update_data(
                battle_type="pve",
                attacker=attacker,
                monster=monster,
                monster_name=monster_name,
                attacker_hp=attacker[9],
                monster_hp=monster[4],
                round_num=1
            )
            
            await message.answer(
                f"⚔️ БОЙ НАЧАТ!\n"
                f"{'='*30}\n"
                f"👤 {attacker[3]} ({attacker[4]})\n"
                f"❤️ {attacker[9]}/{attacker[8]} HP\n"
                f"⚔️ ATK: {attacker[10]} | 🛡️ ARM: {attacker[11]} | 🏃 AGI: {attacker[12]}\n\n"
                f"👹 {monster_name} (ур. {monster[3]})\n"
                f"❤️ {monster[4]} HP\n"
                f"⚔️ ATK: {monster[5]} | 🛡️ ARM: {monster[6]} | 🏃 AGI: {monster[7]}\n"
                f"{'='*30}\n\n"
                f"🎲 Киньте кубик d20 для себя (1-20):"
            )
            await state.set_state(GameStates.waiting_attacker_dice)

@dp.message(GameStates.waiting_attacker_dice)
async def process_attacker_dice(message: types.Message, state: FSMContext):
    try:
        dice = int(message.text)
        if dice < 1 or dice > 20:
            raise ValueError
    except:
        await message.answer("❌ Введите число 1-20!")
        return
    
    data = await state.get_data()
    battle_type = data.get('battle_type')
    await state.update_data(attacker_dice=dice)
    
    if battle_type == "pvp":
        battle_id = data['battle_id']
        defender = data['defender']
        attacker = data['attacker']
        
        # Сохраняем бросок атакующего в БД
        update_battle(battle_id, attacker_dice=dice, status='waiting_defender')
        
        # Отправляем бросок второму игроку
        try:
            await bot.send_message(
                chat_id=defender[0],
                text=f"🎲 {attacker[3]} бросил кубик: {dice}\n"
                     f"Ваша очередь! Киньте кубик d20 и введите результат (1-20):"
            )
            await message.answer(f"✅ Ваш бросок ({dice}) отправлен {defender[3]}.\nОжидайте его ответа...")
            
            # Очищаем состояние первого игрока
            await state.clear()
            
        except:
            await message.answer(f"❌ Не удалось отправить сообщение {defender[3]}. Он должен написать /start")
    
    else:  # PvE
        monster_name = data['monster_name']
        await message.answer(f"🎲 Теперь киньте кубик d20 для {monster_name} (1-20):")
        await state.set_state(GameStates.waiting_monster_dice)

@dp.message(GameStates.waiting_monster_dice)
async def process_monster_dice(message: types.Message, state: FSMContext):
    try:
        dice = int(message.text)
        if dice < 1 or dice > 20:
            raise ValueError
    except:
        await message.answer("❌ Введите число 1-20!")
        return
    
    data = await state.get_data()
    attacker = data['attacker']
    monster = data['monster']
    attacker_dice = data['attacker_dice']
    round_num = data.get('round_num', 1)
    attacker_hp = data.get('attacker_hp', attacker[9])
    monster_hp = data.get('monster_hp', monster[4])
    
    # Расчёт урона
    attacker_dmg = calculate_damage(attacker[10], attacker[12], monster[6], monster[7], attacker_dice)
    monster_dmg = calculate_damage(monster[5], monster[7], attacker[11], attacker[12], dice)
    
    # Криты
    if attacker_dice >= 18:
        attacker_dmg = round(attacker_dmg * 1.8)
    if dice >= 18:
        monster_dmg = round(monster_dmg * 1.8)
    
    new_attacker_hp = max(0, attacker_hp - monster_dmg)
    new_monster_hp = max(0, monster_hp - attacker_dmg)
    
    # Лог боя
    log_lines = [f"🎲 РАУНД {round_num}", "=" * 40]
    if attacker_dice >= 18:
        log_lines.append(f"💥 КРИТ {attacker[3]}! Бросок {attacker_dice} → {attacker_dmg} урона")
    else:
        log_lines.append(f"⚔️ {attacker[3]} атакует: бросок {attacker_dice} → {attacker_dmg} урона")
    log_lines.append(f"❤️ {monster[2]}: {monster_hp} → {new_monster_hp} HP")
    log_lines.append("-" * 40)
    if dice >= 18:
        log_lines.append(f"👹 КРИТ {monster[2]}! Бросок {dice} → {monster_dmg} урона")
    else:
        log_lines.append(f"👹 {monster[2]} атакует: бросок {dice} → {monster_dmg} урона")
    log_lines.append(f"❤️ {attacker[3]}: {attacker_hp} → {new_attacker_hp} HP")
    log_lines.append("=" * 40)
    log_lines.append(f"📊 ИТОГ: {attacker[3]} {new_attacker_hp}/{attacker[8]} HP | {monster[2]} {new_monster_hp}/{monster[4]} HP")
    log_text = "\n".join(log_lines)
    
    await message.answer(log_text)
    update_player(attacker[0], current_hp=new_attacker_hp)
    
    # Проверка завершения
    if new_monster_hp <= 0:
        exp_gain = monster[8]
        new_exp = attacker[6] + exp_gain
        exp_for_next = attacker[5] * 100
        
        if new_exp >= exp_for_next:
            new_lvl = attacker[5] + 1
            update_player(
                attacker[0],
                level=new_lvl,
                exp=new_exp - exp_for_next,
                skill_points=attacker[7] + 5,
                max_hp=attacker[8] + 10,
                current_hp=attacker[8] + 10,
                attack=attacker[10] + 1,
                armor=attacker[11] + 1,
                agility=attacker[12] + 1,
                wins=attacker[13] + 1
            )
            await message.answer(
                f"✅ ПОБЕДА! {attacker[3]} достиг {new_lvl} уровня!\n"
                f"✨ +{exp_gain} опыта | +5 очков навыков | +10 HP | +1 ко всем параметрам"
            )
        else:
            update_player(attacker[0], exp=new_exp, current_hp=attacker[8], wins=attacker[13] + 1)
            await message.answer(f"✅ ПОБЕДА! +{exp_gain} опыта ({new_exp}/{exp_for_next})")
        
        await state.clear()
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
    
    elif new_attacker_hp <= 0:
        update_player(attacker[0], current_hp=attacker[8], losses=attacker[14] + 1)
        await message.answer(
            f"☠️ {attacker[3]} пал в бою с {monster[2]}...\n"
            f"✨ Воскрешение с полным здоровьем!"
        )
        await state.clear()
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
    
    else:
        # Продолжение боя
        await state.update_data(
            attacker_hp=new_attacker_hp,
            monster_hp=new_monster_hp,
            round_num=round_num + 1
        )
        await message.answer(
            f"🎲 РАУНД {round_num + 1}\n"
            f"Ваше здоровье: {new_attacker_hp}/{attacker[8]} HP\n"
            f"Здоровье {monster[2]}: {new_monster_hp}/{monster[4]} HP\n"
            f"Киньте кубик d20 для себя (1-20):"
        )
        await state.set_state(GameStates.waiting_attacker_dice)

# Глобальный обработчик для любых сообщений с числами (для обработки бросков в активных боях)
@dp.message()
async def handle_any_message(message: types.Message, state: FSMContext):
    """Глобальный обработчик для обработки бросков в активных боях"""
    
    # Проверяем, является ли сообщение числом 1-20
    try:
        dice = int(message.text)
        if dice < 1 or dice > 20:
            return  # Не обрабатываем
    except:
        return  # Не число
    
    # Проверяем, есть ли активный бой для этого игрока
    battle = get_active_battle(message.from_user.id)
    
    if not battle:
        return  # Нет активного боя
    
    # Определяем роль игрока в бою
    is_attacker = battle[1] == message.from_user.id
    is_defender = battle[2] == message.from_user.id
    
    if not (is_attacker or is_defender):
        return  # Не участвует в этом бою
    
    # Проверяем статус боя
    if battle[8] == 'completed':
        await message.answer("❌ Этот бой уже завершён!")
        return
    
    if is_attacker and battle[8] == 'waiting_attacker':
        # Атакующий кидает кубик
        await process_pvp_attacker_dice(message, battle, dice, state)
    
    elif is_defender and battle[8] == 'waiting_defender':
        # Защитник кидает кубик
        await process_pvp_defender_dice(message, battle, dice, state)
    
    elif is_attacker and battle[8] == 'waiting_defender':
        await message.answer("⏳ Ожидайте броска от противника...")
    
    elif is_defender and battle[8] == 'waiting_attacker':
        await message.answer("⏳ Ожидайте броска от противника...")

async def process_pvp_attacker_dice(message, battle, dice, state):
    """Обработка броска атакующего"""
    attacker = get_player(battle[1])
    defender = get_player(battle[2])
    
    # Сохраняем бросок в БД
    update_battle(battle[0], attacker_dice=dice, status='waiting_defender')
    
    # Отправляем уведомление защитнику
    try:
        await bot.send_message(
            chat_id=defender[0],
            text=f"🎲 {attacker[3]} бросил кубик: {dice}\n"
                 f"Ваша очередь! Киньте кубик d20 и введите результат (1-20):"
        )
    except:
        pass
    
    await message.answer(f"✅ Ваш бросок ({dice}) отправлен {defender[3]}.\nОжидайте его ответа...")

async def process_pvp_defender_dice(message, battle, dice, state):
    """Обработка броска защитника и расчёт боя"""
    attacker = get_player(battle[1])
    defender = get_player(battle[2])
    attacker_dice = battle[3]
    round_num = battle[7] or 1
    attacker_hp = battle[5] or attacker[9]
    defender_hp = battle[6] or defender[9]
    
    # Расчёт урона
    attacker_dmg = calculate_damage(attacker[10], attacker[12], defender[11], defender[12], attacker_dice)
    defender_dmg = calculate_damage(defender[10], defender[12], attacker[11], attacker[12], dice)
    
    # Увороты
    dodge_chance_att = min(70, max(0, (defender[12] - attacker[12]) * 2))
    dodge_chance_def = min(70, max(0, (attacker[12] - defender[12]) * 2))
    
    did_dodge_att = random.randint(1, 100) <= dodge_chance_att
    did_dodge_def = random.randint(1, 100) <= dodge_chance_def
    
    if did_dodge_att:
        attacker_dmg = 0
    if did_dodge_def:
        defender_dmg = 0
    
    # Криты
    is_crit_att = attacker_dice >= 18
    is_crit_def = dice >= 18
    if is_crit_att and not did_dodge_att:
        attacker_dmg = round(attacker_dmg * 1.8)
    if is_crit_def and not did_dodge_def:
        defender_dmg = round(defender_dmg * 1.8)
    
    # Новое здоровье
    new_attacker_hp = max(0, attacker_hp - defender_dmg)
    new_defender_hp = max(0, defender_hp - attacker_dmg)
    
    # Формирование лога
    log_lines = [f"🎲 РАУНД {round_num}", "=" * 40]
    
    if did_dodge_att:
        log_lines.append(f"💨 {defender[3]} уворачивается от атаки {attacker[3]}!")
    elif is_crit_att:
        log_lines.append(f"💥 КРИТ {attacker[3]}! Бросок {attacker_dice} → {attacker_dmg} урона")
    else:
        log_lines.append(f"⚔️ {attacker[3]} атакует: бросок {attacker_dice} → {attacker_dmg} урона")
    
    if attacker_dmg > 0:
        log_lines.append(f"❤️ {defender[3]}: {defender_hp} → {new_defender_hp} HP")
    
    log_lines.append("-" * 40)
    
    if did_dodge_def:
        log_lines.append(f"💨 {attacker[3]} уворачивается от атаки {defender[3]}!")
    elif is_crit_def:
        log_lines.append(f"💥 КРИТ {defender[3]}! Бросок {dice} → {defender_dmg} урона")
    else:
        log_lines.append(f"⚔️ {defender[3]} атакует: бросок {dice} → {defender_dmg} урона")
    
    if defender_dmg > 0:
        log_lines.append(f"❤️ {attacker[3]}: {attacker_hp} → {new_attacker_hp} HP")
    
    log_lines.append("=" * 40)
    log_lines.append(f"📊 ИТОГ: {attacker[3]} {new_attacker_hp}/{attacker[8]} HP | {defender[3]} {new_defender_hp}/{defender[8]} HP")
    log_text = "\n".join(log_lines)
    
    # Отправка лога обоим игрокам
    await message.answer(log_text)
    try:
        await bot.send_message(chat_id=attacker[0], text=log_text)
    except:
        pass
    
    # Обновление БД
    update_player(attacker[0], current_hp=new_attacker_hp)
    update_player(defender[0], current_hp=new_defender_hp)
    
    # Проверка завершения
    if new_attacker_hp <= 0 and new_defender_hp <= 0:
        result = "⚔️ НИЧЬЯ! Оба пали в бою."
        update_player(attacker[0], current_hp=attacker[8])
        update_player(defender[0], current_hp=defender[8])
        complete_battle(battle[0])
        
    elif new_defender_hp <= 0:
        result = f"✅ {attacker[3]} победил {defender[3]}!"
        update_player(attacker[0], wins=attacker[13] + 1, current_hp=attacker[8])
        update_player(defender[0], losses=defender[14] + 1, current_hp=defender[8])
        complete_battle(battle[0])
        
    elif new_attacker_hp <= 0:
        result = f"✅ {defender[3]} победил {attacker[3]}!"
        update_player(defender[0], wins=defender[13] + 1, current_hp=defender[8])
        update_player(attacker[0], losses=attacker[14] + 1, current_hp=attacker[8])
        complete_battle(battle[0])
        
    else:
        # Продолжение боя
        update_battle(
            battle[0],
            attacker_hp=new_attacker_hp,
            defender_hp=new_defender_hp,
            round_num=round_num + 1,
            status='waiting_attacker'
        )
        
        try:
            await bot.send_message(
                chat_id=attacker[0],
                text=f"🎲 РАУНД {round_num + 1}\n"
                     f"Ваше здоровье: {new_attacker_hp}/{attacker[8]} HP\n"
                     f"Здоровье {defender[3]}: {new_defender_hp}/{defender[8]} HP\n"
                     f"Киньте кубик d20 (1-20):"
            )
        except:
            pass
        
        await message.answer(
            f"🎲 РАУНД {round_num + 1}\n"
            f"Ваше здоровье: {new_defender_hp}/{defender[8]} HP\n"
            f"Здоровье {attacker[3]}: {new_attacker_hp}/{attacker[8]} HP\n"
            f"Ожидайте броска от {attacker[3]}..."
        )
        return
    
    # Завершение боя
    await message.answer(f"{result}\n\nВыберите действие:", reply_markup=get_main_keyboard())
    try:
        await bot.send_message(chat_id=attacker[0], text=f"{result}\n\nВыберите действие:", reply_markup=get_main_keyboard())
    except:
        pass

@dp.message(F.text == "📊 Статистика")
async def stats(message: types.Message):
    players = get_all_players()
    if not players:
        await message.answer("📊 Нет игроков в игре!")
        return
    
    stats_text = "📊 СТАТИСТИКА ИГРОКОВ:\n" + "="*40 + "\n"
    for player in players:
        cls = CLASSES[player[4]]
        win_rate = round(player[13] / (player[13] + player[14]) * 100, 1) if (player[13] + player[14]) > 0 else 0
        stats_text += (
            f"👤 {player[3]} {cls['emoji']}\n"
            f"   🎭 {player[4]} | 📊 ур. {player[5]}\n"
            f"   ❤️ {player[9]}/{player[8]} HP\n"
            f"   ⚔️ {player[10]} ATK | 🛡️ {player[11]} ARM | 🏃 {player[12]} AGI\n"
            f"   🏆 {player[13]} побед | {player[14]} пораж. | {win_rate}%\n"
            f"{'='*40}\n"
        )
    await message.answer(stats_text)

@dp.message(F.text == "❓ Помощь")
async def help_cmd(message: types.Message):
    await message.answer(
        "❓ ПОМОЩЬ:\n"
        "🎲 Кидайте физический кубик d20 и вводите результат в бота.\n"
        "⚔️ PvP: после выбора противника он получит уведомление.\n"
        "👹 PvE: вы вводите оба броска (свой и за монстра).\n"
        "❤️ После смерти герой воскресает с полным здоровьем.\n"
        "✨ За победы над монстрами получаете опыт и уровень.\n"
        "⭐ Прокачка: улучшайте характеристики за очки навыков.\n\n"
        "Команды:\n"
        "/start — создать/показать персонажа"
    )

async def main():
    init_db()
    print("🤖 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
