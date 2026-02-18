# ============================================================================
# ПОТЕРЯННЫЕ ЗЕМЛИ — ИСПРАВЛЕННАЯ ВЕРСИЯ
# ============================================================================
import os
import sqlite3
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import F
import asyncio

# Токен из переменной окружения
API_TOKEN = os.environ.get('BOT_TOKEN')
if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния FSM (ИСПРАВЛЕНО: разделены состояния)
class GameStates(StatesGroup):
    waiting_for_slot = State()      # Выбор слота
    waiting_for_name = State()      # Ввод имени
    waiting_for_class = State()     # Выбор класса
    waiting_for_class_confirm = State()  # Подтверждение класса
    choosing_action = State()
    choosing_hero_to_upgrade = State()
    choosing_stat_to_upgrade = State()
    choosing_battle_type = State()
    choosing_opponent = State()
    waiting_attacker_dice = State()
    waiting_defender_dice = State()
    waiting_monster_dice = State()

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
    
    # Таблица игроков (привязка к Telegram ID)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            hero_slot INTEGER,  -- 1-6
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
    
    # Таблица боёв (для PvP)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS battles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER,
            defender_id INTEGER,
            attacker_dice INTEGER,
            defender_dice INTEGER,
            attacker_damage INTEGER,
            defender_damage INTEGER,
            attacker_hp_after INTEGER,
            defender_hp_after INTEGER,
            winner_id INTEGER,
            battle_type TEXT,  -- 'pvp' or 'pve'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    conn.commit()
    conn.close()

# Получение данных игрока
def get_player(telegram_id):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM players WHERE telegram_id = ?', (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return row

# Создание нового игрока
def create_player(telegram_id, username, hero_slot, hero_name, hero_class):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    
    # Проверка: не превышено ли 6 игроков
    cur.execute('SELECT COUNT(*) FROM players')
    if cur.fetchone()[0] >= 6:
        conn.close()
        return False, "❌ В игре уже 6 игроков! Максимум достигнут."
    
    # Проверка: имя не занято
    cur.execute('SELECT hero_name FROM players WHERE hero_name = ?', (hero_name,))
    if cur.fetchone():
        conn.close()
        return False, f"❌ Имя '{hero_name}' уже занято! Выберите другое."
    
    # Проверка: слот не занят
    cur.execute('SELECT hero_slot FROM players WHERE hero_slot = ?', (hero_slot,))
    if cur.fetchone():
        conn.close()
        return False, f"❌ Слот {hero_slot} уже занят!"
    
    # Бонусы класса
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

# Обновление данных игрока
def update_player(telegram_id, **kwargs):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [telegram_id]
    cur.execute(f'UPDATE players SET {set_clause} WHERE telegram_id = ?', values)
    conn.commit()
    conn.close()

# Получение всех игроков
def get_all_players():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM players ORDER BY hero_slot')
    rows = cur.fetchall()
    conn.close()
    return rows

# Получение свободных слотов
def get_free_slots():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT hero_slot FROM players')
    occupied = {row[0] for row in cur.fetchall()}
    conn.close()
    return [i for i in range(1, 7) if i not in occupied]

# Получение монстра по имени
def get_monster(name):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM monsters WHERE name = ?', (name,))
    row = cur.fetchone()
    conn.close()
    return row

# Расчёт урона с учётом ВСЕХ характеристик
def calculate_damage(attacker_atk, attacker_agi, defender_arm, defender_agi, dice_roll):
    """
    Формула урона:
    - Базовый урон: (Атака - Броня * 0.7)
    - Модификатор ловкости: (Ловкость_атакующего - Ловкость_защитника) * 0.3
    - Кубик: (Бросок - 10) * 1.5
    - Итого: базовый + модификатор_ловкости + кубик
    """
    base_damage = max(1, attacker_atk - defender_arm * 0.7)
    agility_mod = (attacker_agi - defender_agi) * 0.3
    dice_mod = (dice_roll - 10) * 1.5
    
    total = base_damage + agility_mod + dice_mod
    return max(1, round(total))

# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мой персонаж"), KeyboardButton(text="⚔️ Бой")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )

def get_class_keyboard(selected_class=None):
    """Клавиатура выбора класса с кнопкой подтверждения"""
    buttons = []
    
    # Кнопки классов
    for cls_name, cls_data in CLASSES.items():
        prefix = "✅ " if cls_name == selected_class else ""
        buttons.append([KeyboardButton(text=f"{prefix}{cls_data['emoji']} {cls_name}")])
    
    # Кнопка подтверждения (если выбран класс)
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
    else:
        cur.execute('SELECT DISTINCT floor FROM monsters ORDER BY floor')
        floors = [f"Этаж {row[0]}" for row in cur.fetchall()]
        conn.close()
        buttons = [[KeyboardButton(text=floor)] for floor in floors]
        buttons.append([KeyboardButton(text="🔙 Назад")])
        return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
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

# ОСНОВНЫЕ КОМАНДЫ
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    player = get_player(telegram_id)
    
    if player:
        # Игрок уже создан
        await show_character(message, player)
        await state.set_state(GameStates.choosing_action)
    else:
        # Создание нового персонажа
        free_slots = get_free_slots()
        
        if not free_slots:
            await message.answer(
                "❌ Извините, в игре уже 6 игроков!\n"
                "Дождитесь, пока кто-то освободит слот.",
                reply_markup=get_main_keyboard()
            )
            return
        
        await message.answer(
            "🎮 Добро пожаловать в Потерянные земли!\n\n"
            f"👥 В игре сейчас {6 - len(free_slots)}/6 игроков\n\n"
            "Создайте своего персонажа:\n"
            "1️⃣ Выберите свободный слот (1-6)\n"
            "2️⃣ Введите имя персонажа (уникальное)\n"
            "3️⃣ Выберите класс и подтвердите выбор\n\n"
            "Выберите слот:",
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
    await message.answer(
        f"✅ Выбран слот {slot}\n\n"
        "📝 Введите имя персонажа (латиницей или кириллицей, без пробелов):"
    )
    await state.set_state(GameStates.waiting_for_name)

@dp.message(GameStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    hero_name = message.text.strip()
    
    if len(hero_name) < 3 or len(hero_name) > 20:
        await message.answer("❌ Имя должно быть от 3 до 20 символов!")
        return
    
    # Проверка на уникальность (временно, до создания)
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT hero_name FROM players WHERE hero_name = ?', (hero_name,))
    if cur.fetchone():
        conn.close()
        await message.answer("❌ Это имя уже занято! Введите другое:")
        return
    conn.close()
    
    await state.update_data(hero_name=hero_name)
    
    # Показать классы
    classes_text = "🎭 Выберите класс персонажа:\n\n"
    for cls_name, cls_data in CLASSES.items():
        classes_text += f"{cls_data['emoji']} **{cls_name}**\n"
        classes_text += f"   {cls_data['description']}\n"
        classes_text += f"   Бонусы: "
        bonuses = []
        if cls_data['hp_bonus'] != 0:
            bonuses.append(f"HP {'+' if cls_data['hp_bonus'] > 0 else ''}{cls_data['hp_bonus']}")
        if cls_data['atk_bonus'] != 0:
            bonuses.append(f"ATK {'+' if cls_data['atk_bonus'] > 0 else ''}{cls_data['atk_bonus']}")
        if cls_data['arm_bonus'] != 0:
            bonuses.append(f"ARM {'+' if cls_data['arm_bonus'] > 0 else ''}{cls_data['arm_bonus']}")
        if cls_data['agi_bonus'] != 0:
            bonuses.append(f"AGI {'+' if cls_data['agi_bonus'] > 0 else ''}{cls_data['agi_bonus']}")
        classes_text += ", ".join(bonuses) + "\n\n"
    
    await message.answer(
        classes_text,
        reply_markup=get_class_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(GameStates.waiting_for_class)

@dp.message(GameStates.waiting_for_class)
async def process_class_selection(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        # Возврат к выбору имени
        await message.answer("📝 Введите имя персонажа:")
        await state.set_state(GameStates.waiting_for_name)
        return
    
    # Извлекаем имя класса из кнопки (удаляем эмодзи и ✅)
    class_text = message.text.strip()
    
    # Удаляем эмодзи и ✅ в начале
    for prefix in ['✅ ', '⚔️ ', '🧙 ', '🗡️ ', '🛡️ ', '🏹 ', '🌿 ']:
        if class_text.startswith(prefix):
            class_text = class_text[len(prefix):]
            break
    
    if class_text not in CLASSES:
        await message.answer("❌ Выберите класс из списка!", reply_markup=get_class_keyboard())
        return
    
    # Сохраняем выбранный класс
    await state.update_data(hero_class=class_text)
    
    # Показываем клавиатуру с подтверждением
    await message.answer(
        f"🎭 Вы выбрали класс: **{class_text}**\n\n"
        f"{CLASSES[class_text]['description']}\n\n"
        f"**Бонусы класса:**\n"
        f"❤️ HP: {'+' if CLASSES[class_text]['hp_bonus'] > 0 else ''}{CLASSES[class_text]['hp_bonus']}\n"
        f"⚔️ ATK: {'+' if CLASSES[class_text]['atk_bonus'] > 0 else ''}{CLASSES[class_text]['atk_bonus']}\n"
        f"🛡️ ARM: {'+' if CLASSES[class_text]['arm_bonus'] > 0 else ''}{CLASSES[class_text]['arm_bonus']}\n"
        f"🏃 AGI: {'+' if CLASSES[class_text]['agi_bonus'] > 0 else ''}{CLASSES[class_text]['agi_bonus']}\n\n"
        f"✅ Нажмите 'Подтвердить выбор', чтобы создать персонажа\n"
        f"🔙 Или выберите другой класс",
        parse_mode="Markdown",
        reply_markup=get_class_keyboard(selected_class=class_text)
    )
    await state.set_state(GameStates.waiting_for_class_confirm)

@dp.message(GameStates.waiting_for_class_confirm)
async def confirm_class_selection(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        # Возврат к выбору класса
        data = await state.get_data()
        classes_text = "🎭 Выберите класс персонажа:\n\n"
        for cls_name, cls_data in CLASSES.items():
            classes_text += f"{cls_data['emoji']} **{cls_name}**\n"
            classes_text += f"   {cls_data['description']}\n"
            classes_text += f"   Бонусы: "
            bonuses = []
            if cls_data['hp_bonus'] != 0:
                bonuses.append(f"HP {'+' if cls_data['hp_bonus'] > 0 else ''}{cls_data['hp_bonus']}")
            if cls_data['atk_bonus'] != 0:
                bonuses.append(f"ATK {'+' if cls_data['atk_bonus'] > 0 else ''}{cls_data['atk_bonus']}")
            if cls_data['arm_bonus'] != 0:
                bonuses.append(f"ARM {'+' if cls_data['arm_bonus'] > 0 else ''}{cls_data['arm_bonus']}")
            if cls_data['agi_bonus'] != 0:
                bonuses.append(f"AGI {'+' if cls_data['agi_bonus'] > 0 else ''}{cls_data['agi_bonus']}")
            classes_text += ", ".join(bonuses) + "\n\n"
        
        await message.answer(
            classes_text,
            reply_markup=get_class_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(GameStates.waiting_for_class)
        return
    
    if message.text == "✅ Подтвердить выбор":
        data = await state.get_data()
        hero_slot = data['hero_slot']
        hero_name = data['hero_name']
        hero_class = data['hero_class']
        
        telegram_id = message.from_user.id
        username = message.from_user.username or f"user_{telegram_id}"
        
        # Создаём персонажа
        success, msg = create_player(telegram_id, username, hero_slot, hero_name, hero_class)
        
        if success:
            player = get_player(telegram_id)
            await show_character(message, player)
            await state.set_state(GameStates.choosing_action)
        else:
            await message.answer(msg, reply_markup=get_free_slots_keyboard())
            await state.set_state(GameStates.waiting_for_slot)
        return
    
    # Если пользователь снова нажал на класс
    class_text = message.text.strip()
    
    # Удаляем эмодзи и ✅ в начале
    for prefix in ['✅ ', '⚔️ ', '🧙 ', '🗡️ ', '🛡️ ', '🏹 ', '🌿 ']:
        if class_text.startswith(prefix):
            class_text = class_text[len(prefix):]
            break
    
    if class_text in CLASSES:
        await state.update_data(hero_class=class_text)
        await message.answer(
            f"🎭 Вы выбрали класс: **{class_text}**\n\n"
            f"{CLASSES[class_text]['description']}\n\n"
            f"**Бонусы класса:**\n"
            f"❤️ HP: {'+' if CLASSES[class_text]['hp_bonus'] > 0 else ''}{CLASSES[class_text]['hp_bonus']}\n"
            f"⚔️ ATK: {'+' if CLASSES[class_text]['atk_bonus'] > 0 else ''}{CLASSES[class_text]['atk_bonus']}\n"
            f"🛡️ ARM: {'+' if CLASSES[class_text]['arm_bonus'] > 0 else ''}{CLASSES[class_text]['arm_bonus']}\n"
            f"🏃 AGI: {'+' if CLASSES[class_text]['agi_bonus'] > 0 else ''}{CLASSES[class_text]['agi_bonus']}\n\n"
            f"✅ Нажмите 'Подтвердить выбор', чтобы создать персонажа\n"
            f"🔙 Или выберите другой класс",
            parse_mode="Markdown",
            reply_markup=get_class_keyboard(selected_class=class_text)
        )
        return
    
    await message.answer("❌ Используйте кнопки для выбора!")

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
        await message.answer("❌ Вы не создали персонажа! Напишите /start")
        return
    
    await show_character(message, player)

@dp.message(F.text == "⚔️ Бой")
async def battle_menu(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Вы не создали персонажа! Напишите /start")
        return
    
    await message.answer(
        "⚔️ ВЫБЕРИТЕ ТИП БОЯ:\n\n"
        "⚔️ **Герой vs Герой** — PvP бой с другим игроком\n"
        "👹 **Герой vs Монстр** — PvE бой с монстром подземелья",
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
            "👥 ВЫБЕРИТЕ ПРОТИВНИКА:\n"
            "(вы не можете выбрать себя)",
            reply_markup=get_opponent_keyboard(exclude_telegram_id=message.from_user.id)
        )
        await state.set_state(GameStates.choosing_opponent)
        await state.update_data(battle_type="pvp")
    
    elif message.text == "👹 Герой vs Монстр":
        await message.answer(
            "🏰 ВЫБЕРИТЕ ЭТАЖ ПОДЗЕМЕЛЬЯ:",
            reply_markup=get_monster_keyboard()
        )
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
        # PvP: выбираем игрока
        opponent_name = message.text.split(' (')[0]
        opponent = None
        
        for player in get_all_players():
            if player[3] == opponent_name:
                opponent = player
                break
        
        if not opponent:
            await message.answer("❌ Противник не найден! Выберите из списка.")
            return
        
        # Проверка: не сам с собой
        if opponent[0] == message.from_user.id:
            await message.answer("❌ Вы не можете сражаться с самим собой!")
            return
        
        # Сохраняем данные боя
        attacker = get_player(message.from_user.id)
        await state.update_data(
            attacker=attacker,
            defender=opponent,
            opponent_name=opponent_name
        )
        
        await message.answer(
            f"⚔️ БОЙ НАЧАТ!\n"
            f"{'='*30}\n"
            f"👤 {attacker[3]} ({attacker[4]})\n"
            f"❤️ HP: {attacker[9]}/{attacker[8]}\n"
            f"⚔️ ATK: {attacker[10]} | 🛡️ ARM: {attacker[11]} | 🏃 AGI: {attacker[12]}\n\n"
            f"👤 {opponent_name} ({opponent[4]})\n"
            f"❤️ HP: {opponent[9]}/{opponent[8]}\n"
            f"⚔️ ATK: {opponent[10]} | 🛡️ ARM: {opponent[11]} | 🏃 AGI: {opponent[12]}\n"
            f"{'='*30}\n\n"
            f"🎲 {attacker[3]}, киньте кубик d20 и введите результат (1-20):"
        )
        await state.set_state(GameStates.waiting_attacker_dice)
    
    elif battle_type == "pve":
        # PvE: выбираем этаж или монстра
        if message.text.startswith("Этаж"):
            # Выбрали этаж, теперь показываем монстров
            floor = int(message.text.split()[1])
            await state.update_data(floor=floor)
            await message.answer(
                f"👹 ВЫБЕРИТЕ МОНСТРА НА ЭТАЖЕ {floor}:",
                reply_markup=get_monster_keyboard(floor=floor)
            )
        else:
            # Выбрали монстра
            monster_name = message.text
            monster = get_monster(monster_name)
            
            if not monster:
                await message.answer("❌ Монстр не найден! Выберите из списка.")
                return
            
            attacker = get_player(message.from_user.id)
            await state.update_data(
                attacker=attacker,
                monster=monster,
                monster_name=monster_name
            )
            
            await message.answer(
                f"⚔️ БОЙ НАЧАТ!\n"
                f"{'='*30}\n"
                f"👤 {attacker[3]} ({attacker[4]})\n"
                f"❤️ HP: {attacker[9]}/{attacker[8]}\n"
                f"⚔️ ATK: {attacker[10]} | 🛡️ ARM: {attacker[11]} | 🏃 AGI: {attacker[12]}\n\n"
                f"👹 {monster_name} (ур. {monster[3]})\n"
                f"❤️ HP: {monster[4]}\n"
                f"⚔️ ATK: {monster[5]} | 🛡️ ARM: {monster[6]} | 🏃 AGI: {monster[7]}\n"
                f"{'='*30}\n\n"
                f"🎲 {attacker[3]}, киньте кубик d20 для себя и введите результат (1-20):"
            )
            await state.set_state(GameStates.waiting_attacker_dice)

@dp.message(GameStates.waiting_attacker_dice)
async def process_attacker_dice(message: types.Message, state: FSMContext):
    try:
        dice = int(message.text)
        if dice < 1 or dice > 20:
            raise ValueError
    except:
        await message.answer("❌ Введите число от 1 до 20!")
        return
    
    data = await state.get_data()
    battle_type = data.get('battle_type', 'pvp')
    
    await state.update_data(attacker_dice=dice)
    
    if battle_type == "pvp":
        # Ждём броска защитника
        defender_name = data['opponent_name']
        await message.answer(
            f"🎲 {defender_name}, киньте кубик d20 и введите результат (1-20):\n"
            f"(Перешлите это сообщение {defender_name})"
        )
        await state.set_state(GameStates.waiting_defender_dice)
    else:
        # PvE: игрок вводит бросок за монстра
        await message.answer(
            f"🎲 Теперь киньте кубик d20 для {data['monster_name']} и введите результат (1-20):"
        )
        await state.set_state(GameStates.waiting_monster_dice)

@dp.message(GameStates.waiting_defender_dice)
async def process_defender_dice(message: types.Message, state: FSMContext):
    try:
        dice = int(message.text)
        if dice < 1 or dice > 20:
            raise ValueError
    except:
        await message.answer("❌ Введите число от 1 до 20!")
        return
    
    data = await state.get_data()
    attacker = data['attacker']
    defender = data['defender']
    attacker_dice = data['attacker_dice']
    
    # Расчёт урона
    attacker_dmg = calculate_damage(
        attacker[10], attacker[12],  # ATK, AGI атакующего
        defender[11], defender[12],  # ARM, AGI защитника
        attacker_dice
    )
    
    defender_dmg = calculate_damage(
        defender[10], defender[12],  # ATK, AGI защитника
        attacker[11], attacker[12],  # ARM, AGI атакующего
        dice
    )
    
    # Новый урон
    new_attacker_hp = max(0, attacker[9] - defender_dmg)
    new_defender_hp = max(0, defender[9] - attacker_dmg)
    
    # Обновление в БД
    update_player(attacker[0], current_hp=new_attacker_hp)
    update_player(defender[0], current_hp=new_defender_hp)
    
    # Лог боя
    log = (
        f"🎲 РАУНД:\n"
        f"{'='*30}\n"
        f"👤 {attacker[3]} бросает {attacker_dice} → {attacker_dmg} урона!\n"
        f"👤 {defender[3]} бросает {dice} → {defender_dmg} урона!\n"
        f"{'='*30}\n\n"
        f"❤️ {attacker[3]}: {new_attacker_hp}/{attacker[8]} HP\n"
        f"❤️ {defender[3]}: {new_defender_hp}/{defender[8]} HP"
    )
    
    await message.answer(log)
    
    # Проверка завершения
    if new_attacker_hp <= 0 and new_defender_hp <= 0:
        await message.answer("⚔️ НИЧЬЯ! Оба пали в бою!")
        update_player(attacker[0], current_hp=attacker[8])  # Воскрешение
        update_player(defender[0], current_hp=defender[8])
    elif new_defender_hp <= 0:
        await message.answer(f"✅ {attacker[3]} победил {defender[3]}!")
        update_player(attacker[0], wins=attacker[13] + 1, current_hp=attacker[8])  # Воскрешение победителя
        update_player(defender[0], losses=defender[14] + 1, current_hp=defender[8])  # Воскрешение проигравшего
    elif new_attacker_hp <= 0:
        await message.answer(f"✅ {defender[3]} победил {attacker[3]}!")
        update_player(defender[0], wins=defender[13] + 1, current_hp=defender[8])
        update_player(attacker[0], losses=attacker[14] + 1, current_hp=attacker[8])
    
    await state.set_state(GameStates.choosing_action)
    await message.answer("Выберите действие:", reply_markup=get_main_keyboard())

@dp.message(GameStates.waiting_monster_dice)
async def process_monster_dice(message: types.Message, state: FSMContext):
    try:
        dice = int(message.text)
        if dice < 1 or dice > 20:
            raise ValueError
    except:
        await message.answer("❌ Введите число от 1 до 20!")
        return
    
    data = await state.get_data()
    attacker = data['attacker']
    monster = data['monster']
    attacker_dice = data['attacker_dice']
    
    # Расчёт урона
    attacker_dmg = calculate_damage(
        attacker[10], attacker[12],  # ATK, AGI героя
        monster[6], monster[7],      # ARM, AGI монстра
        attacker_dice
    )
    
    monster_dmg = calculate_damage(
        monster[5], monster[7],      # ATK, AGI монстра
        attacker[11], attacker[12],  # ARM, AGI героя
        dice
    )
    
    # Новый урон
    new_attacker_hp = max(0, attacker[9] - monster_dmg)
    new_monster_hp = max(0, monster[4] - attacker_dmg)
    
    # Обновление героя в БД
    update_player(attacker[0], current_hp=new_attacker_hp)
    
    # Лог боя
    log = (
        f"🎲 РАУНД:\n"
        f"{'='*30}\n"
        f"👤 {attacker[3]} бросает {attacker_dice} → {attacker_dmg} урона!\n"
        f"👹 {monster[2]} бросает {dice} → {monster_dmg} урона!\n"
        f"{'='*30}\n\n"
        f"❤️ {attacker[3]}: {new_attacker_hp}/{attacker[8]} HP\n"
        f"❤️ {monster[2]}: {new_monster_hp}/{monster[4]} HP"
    )
    
    await message.answer(log)
    
    # Проверка завершения
    if new_monster_hp <= 0:
        # Победа над монстром
        # Начисление опыта
        exp_gain = monster[8]  # exp_reward
        new_exp = attacker[6] + exp_gain
        
        # Проверка уровня
        exp_for_next = attacker[5] * 100
        if new_exp >= exp_for_next:
            # Повышение уровня
            new_lvl = attacker[5] + 1
            await message.answer(
                f"✅ {attacker[3]} победил {monster[2]}!\n"
                f"✨ Получено {exp_gain} опыта!\n"
                f"{'='*30}\n"
                f"🎉 ПОВЫШЕНИЕ УРОВНЯ!\n"
                f"Достигнут {new_lvl} уровень!\n"
                f"+5 очков навыков, +10 здоровья, +1 ко всем параметрам!"
            )
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
        else:
            await message.answer(
                f"✅ {attacker[3]} победил {monster[2]}!\n"
                f"✨ Получено {exp_gain} опыта! ({new_exp}/{exp_for_next})"
            )
            update_player(
                attacker[0],
                exp=new_exp,
                current_hp=attacker[8],  # Воскрешение
                wins=attacker[13] + 1
            )
        
        await state.set_state(GameStates.choosing_action)
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
        
    elif new_attacker_hp <= 0:
        # Поражение от монстра
        await message.answer(
            f"☠️ {attacker[3]} пал в бою с {monster[2]}...\n"
            f"✨ Воскрешение с полным здоровьем!"
        )
        update_player(
            attacker[0],
            current_hp=attacker[8],
            losses=attacker[14] + 1
        )
        await state.set_state(GameStates.choosing_action)
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
    
    else:
        # Продолжение боя
        await state.update_data(
            attacker=get_player(attacker[0]),  # Обновляем данные
            monster=(monster[0], monster[1], monster[2], monster[3], new_monster_hp, monster[5], monster[6], monster[7], monster[8])
        )
        await message.answer(
            "🎲 КИНЬТЕ КУБИКИ СНОВА!\n"
            f"Для {attacker[3]} (1-20):"
        )
        await state.set_state(GameStates.waiting_attacker_dice)

@dp.message(F.text == "📊 Статистика")
async def stats(message: types.Message):
    players = get_all_players()
    
    if not players:
        await message.answer("📊 Пока нет игроков в игре!")
        return
    
    stats_text = "📊 **СТАТИСТИКА ИГРОКОВ:**\n\n"
    stats_text += "="*40 + "\n"
    
    for player in players:
        cls = CLASSES[player[4]]
        win_rate = round(player[13] / (player[13] + player[14]) * 100, 1) if (player[13] + player[14]) > 0 else 0
        
        stats_text += (
            f"👤 {player[3]} {cls['emoji']}\n"
            f"   🎭 {player[4]} | 📊 ур. {player[5]}\n"
            f"   ❤️ {player[9]}/{player[8]} HP\n"
            f"   ⚔️ {player[10]} ATK | 🛡️ {player[11]} ARM | 🏃 {player[12]} AGI\n"
            f"   🏆 {player[13]} побед | {player[14]} поражений | {win_rate}% побед\n"
            f"{'='*40}\n"
        )
    
    await message.answer(stats_text, parse_mode="Markdown")

@dp.message(F.text == "❓ Помощь")
async def help_cmd(message: types.Message):
    help_text = (
        "❓ **ПОМОЩЬ:**\n"
        "{'='*40}\n\n"
        "🎲 **КУБИКИ:**\n"
        "• Используйте физический кубик d20\n"
        "• Бросок влияет на урон по формуле:\n"
        "  Урон = (АТК - БРОНЯ×0.7) + (ЛОВК×0.3) + (КУБИК-10)×1.5\n\n"
        "⚔️ **БОЙ:**\n"
        "• PvP: оба игрока вводят свои броски\n"
        "• PvE: игрок вводит оба броска\n"
        "• Победитель получает опыт (только монстры)\n"
        "• После смерти герой воскресает с полным HP\n\n"
        "⭐ **ПРОКАЧКА:**\n"
        "(В разработке)\n"
        "• +5 HP = +5 макс. здоровья и текущего за 1 очко"
        "• +2 ATK = +2 к атаке за 1 очко"
        "• +1 ARM = +1 к броне за 1 очко"
        "• +1 AGI = +1 к ловкости за 1 очко"
        "{'='*40}"
    )
    
    await message.answer(help_text, parse_mode="Markdown")

# ЗАПУСК БОТА
async def main():
    init_db()
    print("🤖 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
