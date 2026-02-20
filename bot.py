import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"  # Замените на токен от @BotFather
DATABASE = "lost_lands.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            gold INTEGER DEFAULT 100,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица персонажей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            race TEXT,
            class_type TEXT,
            -- Базовые характеристики
            strength INTEGER DEFAULT 5,
            agility INTEGER DEFAULT 5,
            vitality INTEGER DEFAULT 5,
            intelligence INTEGER DEFAULT 5,
            dexterity INTEGER DEFAULT 5,
            luck INTEGER DEFAULT 5,
            -- Боевые характеристики (рассчитываются)
            hp INTEGER DEFAULT 100,
            hp_max INTEGER DEFAULT 100,
            mp INTEGER DEFAULT 50,
            mp_max INTEGER DEFAULT 50,
            phys_atk INTEGER DEFAULT 10,
            speed_atk INTEGER DEFAULT 5,
            evasion INTEGER DEFAULT 3,
            phys_def INTEGER DEFAULT 2,
            mag_def INTEGER DEFAULT 2,
            mag_atk INTEGER DEFAULT 8,
            haste INTEGER DEFAULT 2,
            hit INTEGER DEFAULT 2,
            crit INTEGER DEFAULT 5,
            anti_crit INTEGER DEFAULT 5,
            -- Навыки для прокачки
            skill_points INTEGER DEFAULT 0,
            -- Экипировка
            weapon_id INTEGER,
            armor_id INTEGER,
            accessory_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблица инвентаря
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER,
            item_id TEXT,
            item_type TEXT,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (character_id) REFERENCES characters(id)
        )
    ''')
    
    # Таблица логов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logging.info("✅ База данных инициализирована")

def get_conn():
    return sqlite3.connect(DATABASE)

# ==================== ДАННЫЕ ИГРЫ ====================
RACES = {
    "human": {"name": "🧑 Человек", "bonus": "+3 навыка (по выбору)"},
    "elf": {"name": "🧝 Эльф", "bonus": "+2 Проворство; +1 Ловкость"},
    "dwarf": {"name": "🧔 Гном", "bonus": "+3 Сила"},
    "orc": {"name": "👹 Орк", "bonus": "+3 Живучесть"},
    "fallen": {"name": "💀 Падший", "bonus": "+2 Ловкость; +1 Интеллект"}
}

CLASSES = {
    "warrior": {"name": "⚔️ Воин", "bonus": "+1 Сила; +1 Живучесть"},
    "archer": {"name": "🏹 Лучник", "bonus": "+1 Ловкость; +1 Удача"},
    "mage": {"name": "🔮 Волшебник", "bonus": "+2 Интеллект"},
    "bard": {"name": "🎭 Бард", "bonus": "+1 Интеллект; +1 Ловкость"},
    "paladin": {"name": "🛡️ Паладин", "bonus": "+1 Сила; +1 Интеллект"},
    "necromancer": {"name": "💀 Некромант", "bonus": "+1 Интеллект; +1 Живучесть"}
}

SKILLS_INFO = {
    "strength": {"name": "💪 Сила", "desc": "Физ.АТК: 1 навык = +4"},
    "agility": {"name": "🦶 Ловкость", "desc": "Скр.АТК/Укл: 1 навык = +8/+3"},
    "vitality": {"name": "❤️ Живучесть", "desc": "ОЗ/Ф.Защ/М.Защ: 1 навык = +15/+1/+1"},
    "intelligence": {"name": "🧠 Интеллект", "desc": "ОД/М.АТК: 1 навык = +3/+4"},
    "dexterity": {"name": "⚡ Проворство", "desc": "Уск./Удар: 1 навык = +2/+2"},
    "luck": {"name": "🍀 Удача", "desc": "Крит/Ант.Крит: 1 навык = +4/+2"}
}

# Магазин
SHOP_ITEMS = {
    "potions": [
        {"id": "potion_hp_small", "name": "🧪 Малое зелье ОЗ", "type": "Зелье", "effect": "+30 ОЗ", "price": 50},
        {"id": "potion_hp_medium", "name": "🧪 Среднее зелье ОЗ", "type": "Зелье", "effect": "+60 ОЗ", "price": 100},
        {"id": "potion_hp_large", "name": "🧪 Большое зелье ОЗ", "type": "Зелье", "effect": "+100 ОЗ", "price": 150},
        {"id": "potion_mp_small", "name": "💙 Малое зелье ОД", "type": "Зелье", "effect": "+30 ОД", "price": 50},
        {"id": "potion_mp_medium", "name": "💙 Среднее зелье ОД", "type": "Зелье", "effect": "+60 ОД", "price": 100},
        {"id": "potion_mp_large", "name": "💙 Большое зелье ОД", "type": "Зелье", "effect": "+100 ОД", "price": 150},
    ],
    "weapons": [
        {"id": "w_sword_apprentice", "name": "⚔️ Меч Ученика", "type": "Оружие 1", "effect": "+1 Сила", "price": 150, "stat": "strength", "value": 1},
        {"id": "w_shield_apprentice", "name": "🛡️ Щит Ученика", "type": "Оружие 2", "effect": "+1 Живучесть", "price": 150, "stat": "vitality", "value": 1},
        {"id": "w_bow_apprentice", "name": "🏹 Лук Ученика", "type": "Оружие 1", "effect": "+1 Ловкость", "price": 150, "stat": "agility", "value": 1},
        {"id": "w_arrows_apprentice", "name": "🎯 Стрелы Ученика", "type": "Оружие 2", "effect": "+1 Проворство", "price": 150, "stat": "dexterity", "value": 1},
        {"id": "w_staff_apprentice", "name": "🪄 Посох Ученика", "type": "Оружие 1", "effect": "+1 Интеллект", "price": 150, "stat": "intelligence", "value": 1},
        {"id": "w_orb_apprentice", "name": "🔮 Сфера Ученика", "type": "Оружие 2", "effect": "+1 Интеллект", "price": 150, "stat": "intelligence", "value": 1},
    ],
    "armor": [
        {"id": "a_helmet", "name": "⛑️ Шлем Ученика", "type": "Экипировка 1", "effect": "+1 Живучесть", "price": 200, "stat": "vitality", "value": 1},
        {"id": "a_armor", "name": "🦺 Броня Ученика", "type": "Экипировка 2", "effect": "+1 Живучесть", "price": 200, "stat": "vitality", "value": 1},
        {"id": "a_pants", "name": "👖 Штаны Ученика", "type": "Экипировка 3", "effect": "+1 Ловкость", "price": 200, "stat": "agility", "value": 1},
        {"id": "a_boots", "name": "👢 Ботинки Ученика", "type": "Экипировка 4", "effect": "+1 Ловкость", "price": 200, "stat": "agility", "value": 1},
        {"id": "a_arms", "name": "💪 Руки Ученика", "type": "Экипировка 5", "effect": "+1 Сила", "price": 200, "stat": "strength", "value": 1},
        {"id": "a_gloves", "name": "🧤 Перчатки Ученика", "type": "Экипировка 6", "effect": "+1 Сила", "price": 200, "stat": "strength", "value": 1},
    ],
    "accessories": [
        {"id": "acc_amulet", "name": "📿 Амулет Ловкости", "type": "Аксессуары 1", "effect": "+2 Удача", "price": 400, "stat": "luck", "value": 2},
        {"id": "acc_ring", "name": "💍 Кольцо Защиты", "type": "Аксессуары 2", "effect": "+2 Удача", "price": 400, "stat": "luck", "value": 2},
        {"id": "acc_chain", "name": "⛓️ Цепь Силы", "type": "Аксессуары 3", "effect": "+2 Удача", "price": 400, "stat": "luck", "value": 2},
    ],
    "misc": [
        {"id": "scroll_xp", "name": "📜 Свиток опыта", "type": "Разное", "effect": "+50 Опыта", "price": 500},
    ]
}

# Монстры
MONSTERS = {
    "weak": [
        {"id": "m_rat", "name": "🐀 Крыса", "hp": 20, "atk": 5, "def": 1, "xp": 10, "gold": 5},
        {"id": "m_slime", "name": "💧 Слизень", "hp": 25, "atk": 6, "def": 2, "xp": 15, "gold": 8},
        {"id": "m_goblin", "name": "👺 Гоблин", "hp": 30, "atk": 8, "def": 2, "xp": 20, "gold": 12},
        {"id": "m_bat", "name": "🦇 Летучая мышь", "hp": 18, "atk": 7, "def": 1, "xp": 12, "gold": 6},
        {"id": "m_spider", "name": "🕷️ Паук", "hp": 22, "atk": 9, "def": 3, "xp": 18, "gold": 10},
    ],
    "medium": [
        {"id": "m_wolf", "name": "🐺 Волк", "hp": 45, "atk": 12, "def": 4, "xp": 35, "gold": 25},
        {"id": "m_skeleton", "name": "💀 Скелет", "hp": 50, "atk": 14, "def": 5, "xp": 40, "gold": 30},
        {"id": "m_zombie", "name": "🧟 Зомби", "hp": 60, "atk": 10, "def": 8, "xp": 45, "gold": 28},
        {"id": "m_bandit", "name": "🗡️ Бандит", "hp": 55, "atk": 15, "def": 3, "xp": 50, "gold": 40},
        {"id": "m_wraith", "name": "👻 Призрак", "hp": 40, "atk": 18, "def": 2, "xp": 55, "gold": 35},
    ],
    "strong": [
        {"id": "m_ogre", "name": "👹 Огр", "hp": 90, "atk": 22, "def": 10, "xp": 80, "gold": 60},
        {"id": "m_troll", "name": "🧌 Тролль", "hp": 100, "atk": 20, "def": 12, "xp": 90, "gold": 70},
        {"id": "m_minotaur", "name": "🐂 Минотавр", "hp": 110, "atk": 25, "def": 8, "xp": 100, "gold": 80},
        {"id": "m_werewolf", "name": "🐺 Оборотень", "hp": 85, "atk": 28, "def": 6, "xp": 95, "gold": 75},
        {"id": "m_elemental", "name": "🔥 Элементаль", "hp": 95, "atk": 24, "def": 9, "xp": 105, "gold": 85},
    ],
    "very_strong": [
        {"id": "m_dragon_whelp", "name": "🐉 Детёныш дракона", "hp": 150, "atk": 35, "def": 15, "xp": 150, "gold": 120},
        {"id": "m_demon", "name": "😈 Демон", "hp": 140, "atk": 40, "def": 12, "xp": 160, "gold": 130},
        {"id": "m_vampire", "name": "🧛 Вампир", "hp": 130, "atk": 38, "def": 10, "xp": 155, "gold": 125},
        {"id": "m_lich", "name": "💀 Лич", "hp": 120, "atk": 45, "def": 8, "xp": 170, "gold": 140},
        {"id": "m_hydra", "name": "🐍 Гидра", "hp": 160, "atk": 32, "def": 18, "xp": 165, "gold": 135},
    ],
    "bosses": [
        {"id": "b_shadow_lord", "name": "👑 Повелитель Теней", "hp": 300, "atk": 55, "def": 25, "xp": 500, "gold": 400},
        {"id": "b_ancient_dragon", "name": "🐉 Древний Дракон", "hp": 400, "atk": 65, "def": 30, "xp": 700, "gold": 600},
        {"id": "b_demon_king", "name": "🔥 Король Демонов", "hp": 350, "atk": 70, "def": 28, "xp": 650, "gold": 550},
    ],
    "titan": {
        "id": "t_final_boss", 
        "name": "👑🔥 ТИТАН РАЗРУШЕНИЯ", 
        "hp": 1000, 
        "atk": 100, 
        "def": 50, 
        "xp": 5000, 
        "gold": 2000
    }
}

# Карты
CARDS = {
    "red": [
        {"name": "⚔️ Внезапная атака", "effect": "Противник получает -2 к броску"},
        {"name": "🩸 Кровотечение", "effect": "Противник теряет 10 ОЗ в начале хода"},
        {"name": "🔥 Огненная стрела", "effect": "+5 к вашей атаке в этом раунде"},
        {"name": "💀 Проклятие слабости", "effect": "Противник: -3 к Силе на 1 раунд"},
    ],
    "yellow": [
        {"name": "🗝️ Найти сокровище", "effect": "+50 золота"},
        {"name": "📜 Древний свиток", "effect": "+100 опыта"},
        {"name": "🤝 Помощь союзника", "effect": "Восстановить 30 ОЗ"},
        {"name": "🗺️ Карта сокровищ", "effect": "Следующий бой: +10% к награде"},
    ],
    "green": [
        {"name": "✨ Благословение", "effect": "+2 ко всем характеристикам на 1 бой"},
        {"name": "⚡ Ускорение", "effect": "+5 к Проворству на 1 бой"},
        {"name": "🛡️ Щит веры", "effect": "+5 к защите на 1 бой"},
        {"name": "🍀 Удача героя", "effect": "+10 к Криту на 1 бой"},
    ],
    "black": [
        {"name": "🌑 Тьма", "effect": "-3 к точности атаки"},
        {"name": "🕸️ Паутина", "effect": "-2 к Проворству"},
        {"name": "💤 Утомление", "effect": "-20 ОД"},
        {"name": "🌀 Замешательство", "effect": "Следующий бросок: результат / 2"},
    ]
}

# ==================== FSM STATES ====================
class CharacterCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_race = State()
    waiting_for_class = State()

class BattleState(StatesGroup):
    waiting_for_player_roll = State()
    waiting_for_enemy_roll = State()
    hero_vs_hero_select = State()

class ShopState(StatesGroup):
    viewing_category = State()
    selecting_item = State()

# ==================== КЛАВИАТУРЫ ====================
def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👤 Мой персонаж", callback_data="char_sheet"))
    builder.row(InlineKeyboardButton(text="⭐ Навыки", callback_data="skills_menu"))
    builder.row(InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory_menu"))
    builder.row(InlineKeyboardButton(text="🏪 Магазин", callback_data="shop_main"))
    builder.row(
        InlineKeyboardButton(text="⚔️ Бой", callback_data="battle_menu"),
        InlineKeyboardButton(text="🃏 Карточки", callback_data="cards_menu")
    )
    builder.row(InlineKeyboardButton(text="📋 Лог", callback_data="logs_view"))
    return builder.as_markup()

def race_kb():
    builder = InlineKeyboardBuilder()
    for race_id, race_data in RACES.items():
        builder.row(InlineKeyboardButton(text=race_data["name"], callback_data=f"race_{race_id}"))
    return builder.as_markup()

def class_kb():
    builder = InlineKeyboardBuilder()
    for class_id, class_data in CLASSES.items():
        builder.row(InlineKeyboardButton(text=class_data["name"], callback_data=f"class_{class_id}"))
    return builder.as_markup()

def skills_kb():
    builder = InlineKeyboardBuilder()
    for skill_id, skill_data in SKILLS_INFO.items():
        builder.row(InlineKeyboardButton(text=f"{skill_data['name']} [+]", callback_data=f"skill_up_{skill_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return builder.as_markup()

def inventory_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎒 Надеть", callback_data="inv_equip"))
    builder.row(InlineKeyboardButton(text="🔓 Снять", callback_data="inv_unequip"))
    builder.row(InlineKeyboardButton(text="💰 Продать (50%)", callback_data="inv_sell"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return builder.as_markup()

def shop_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🧪 Зелья", callback_data="shop_potions"))
    builder.row(InlineKeyboardButton(text="⚔️ Оружие", callback_data="shop_weapons"))
    builder.row(InlineKeyboardButton(text="🦺 Экипировка", callback_data="shop_armor"))
    builder.row(InlineKeyboardButton(text="📿 Аксессуары", callback_data="shop_accessories"))
    builder.row(InlineKeyboardButton(text="📦 Разное", callback_data="shop_misc"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return builder.as_markup()

def battle_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👥 Герой vs Герой", callback_data="battle_hvh"))
    builder.row(InlineKeyboardButton(text="👹 Герой vs Монстр", callback_data="battle_hvm"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return builder.as_markup()

def monster_select_kb(difficulty):
    builder = InlineKeyboardBuilder()
    monsters = MONSTERS.get(difficulty, [])
    for i, monster in enumerate(monsters):
        builder.row(InlineKeyboardButton(text=monster["name"], callback_data=f"monster_{difficulty}_{i}"))
    if difficulty != "weak":
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="battle_hvm_difficulty"))
    else:
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu"))
    return builder.as_markup()

def monster_difficulty_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🟢 Слабые", callback_data="monsters_weak"))
    builder.row(InlineKeyboardButton(text="🟡 Средние", callback_data="monsters_medium"))
    builder.row(InlineKeyboardButton(text="🔴 Сильные", callback_data="monsters_strong"))
    builder.row(InlineKeyboardButton(text="🟣 Очень сильные", callback_data="monsters_very_strong"))
    builder.row(InlineKeyboardButton(text="👑 Боссы", callback_data="monsters_bosses"))
    builder.row(InlineKeyboardButton(text="💀 ТИТАН", callback_data="monsters_titan"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu"))
    return builder.as_markup()

def cards_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔴 Красная", callback_data="card_red"))
    builder.row(InlineKeyboardButton(text="🟡 Жёлтая", callback_data="card_yellow"))
    builder.row(InlineKeyboardButton(text="🟢 Зелёная", callback_data="card_green"))
    builder.row(InlineKeyboardButton(text="⚫ Чёрная", callback_data="card_black"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return builder.as_markup()

def battle_action_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏳️ Сдаться", callback_data="battle_surrender"))
    return builder.as_markup()

# ==================== ХЕНДЛЕРЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Игрок"
    
    conn = get_conn()
    cursor = conn.cursor()
    
    # Создаём пользователя если нет
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    
    # Проверяем есть ли персонаж
    cursor.execute("SELECT id FROM characters WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        await message.answer(
            "🎮 Добро пожаловать в Lost Lands RPG!\n\n"
            "Создайте своего персонажа:\n"
            "Введите имя (3-30 символов):"
        )
        await dp.storage.set_state(user_id=user_id, state=CharacterCreation.waiting_for_name)
    else:
        conn.close()
        await message.answer("🗡️ Добро zurück, герой!", reply_markup=main_menu_kb())
        log_action(user_id, "Вход в игру")

@dp.message(CharacterCreation.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not (3 <= len(name) <= 30):
        await message.answer("❌ Имя должно быть от 3 до 30 символов. Попробуйте ещё раз:")
        return
    
    await state.update_data(name=name)
    await message.answer("🧬 Выберите расу:", reply_markup=race_kb())
    await state.set_state(CharacterCreation.waiting_for_race)

@dp.callback_query(CharacterCreation.waiting_for_race)
async def process_race(callback: types.CallbackQuery, state: FSMContext):
    race_id = callback.data.replace("race_", "")
    await state.update_data(race=race_id)
    await callback.message.edit_text(f"⚔️ Выберите класс:", reply_markup=class_kb())
    await state.set_state(CharacterCreation.waiting_for_class)

@dp.callback_query(CharacterCreation.waiting_for_class)
async def process_class(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    class_id = callback.data.replace("class_", "")
    
    user_id = callback.from_user.id
    conn = get_conn()
    cursor = conn.cursor()
    
    # Базовые статы
    stats = {"strength": 5, "agility": 5, "vitality": 5, "intelligence": 5, "dexterity": 5, "luck": 5}
    
    # Бонусы расы
    race = data["race"]
    if race == "elf":
        stats["dexterity"] += 2
        stats["agility"] += 1
    elif race == "dwarf":
        stats["strength"] += 3
    elif race == "orc":
        stats["vitality"] += 3
    elif race == "fallen":
        stats["agility"] += 2
        stats["intelligence"] += 1
    # human: +3 skill points later
    
    # Бонусы класса
    if class_id == "warrior":
        stats["strength"] += 1
        stats["vitality"] += 1
    elif class_id == "archer":
        stats["agility"] += 1
        stats["luck"] += 1
    elif class_id == "mage":
        stats["intelligence"] += 2
    elif class_id == "bard":
        stats["intelligence"] += 1
        stats["agility"] += 1
    elif class_id == "paladin":
        stats["strength"] += 1
        stats["intelligence"] += 1
    elif class_id == "necromancer":
        stats["intelligence"] += 1
        stats["vitality"] += 1
    
    # Расчёт боевых характеристик
    hp = 100 + stats["vitality"] * 15
    mp = 50 + stats["intelligence"] * 3
    phys_atk = 10 + stats["strength"] * 4
    speed_atk = 5 + stats["agility"] * 8
    evasion = 3 + stats["agility"] * 3
    phys_def = 2 + stats["vitality"]
    mag_def = 2 + stats["vitality"]
    mag_atk = 8 + stats["intelligence"] * 4
    haste = 2 + stats["dexterity"] * 2
    hit = 2 + stats["dexterity"] * 2
    crit = 5 + stats["luck"] * 4
    anti_crit = 5 + stats["luck"] * 2
    
    skill_points = 3 if race == "human" else 0
    
    cursor.execute('''
        INSERT INTO characters (
            user_id, name, race, class_type,
            strength, agility, vitality, intelligence, dexterity, luck,
            hp, hp_max, mp, mp_max,
            phys_atk, speed_atk, evasion, phys_def, mag_def, mag_atk,
            haste, hit, crit, anti_crit,
            skill_points
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, data["name"], race, class_id,
        stats["strength"], stats["agility"], stats["vitality"], 
        stats["intelligence"], stats["dexterity"], stats["luck"],
        hp, hp, mp, mp,
        phys_atk, speed_atk, evasion, phys_def, mag_def, mag_atk,
        haste, hit, crit, anti_crit,
        skill_points
    ))
    
    conn.commit()
    conn.close()
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ Персонаж создан!\n\n"
        f"👤 {data['name']}\n"
        f"{RACES[race]['name']} | {CLASSES[class_id]['name']}\n"
        f"❤️ ОЗ: {hp} | 💙 ОД: {mp}\n"
        f"⚔️ Физ.АТК: {phys_atk} | 🔮 Маг.АТК: {mag_atk}\n\n"
        f"🎁 Бонусы применены!",
        reply_markup=main_menu_kb()
    )
    log_action(user_id, f"Создан персонаж: {data['name']} ({race}, {class_id})")

# ==================== ГЛАВНОЕ МЕНЮ ====================

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("🗡️ Главное меню", reply_markup=main_menu_kb())

@dp.callback_query(F.data == "char_sheet")
async def show_character(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM characters WHERE user_id = ?", (user_id,))
    char = cursor.fetchone()
    
    if not char:
        await callback.answer("❌ Персонаж не найден", show_alert=True)
        return
    
    # Индексы колонок (упрощённо)
    char_data = {
        "name": char[2], "race": char[3], "class": char[4],
        "hp": char[13], "hp_max": char[14], "mp": char[15], "mp_max": char[16],
        "phys_atk": char[17], "speed_atk": char[18], "evasion": char[19],
        "phys_def": char[20], "mag_def": char[21], "mag_atk": char[22],
        "haste": char[23], "hit": char[24], "crit": char[25], "anti_crit": char[26],
        "skill_points": char[27],
        "weapon": char[28], "armor": char[29], "accessory": char[30]
    }
    
    # Получаем золото и опыт
    cursor.execute("SELECT gold, xp, level FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    gold, xp, level = user_data
    xp_next = level * 100
    
    conn.close()
    
    equipment_text = ""
    if char_data["weapon"]:
        equipment_text += f"⚔️ Оружие: {char_data['weapon']}\n"
    if char_data["armor"]:
        equipment_text += f"🦺 Броня: {char_data['armor']}\n"
    if char_data["accessory"]:
        equipment_text += f"📿 Аксессуар: {char_data['accessory']}\n"
    if not equipment_text:
        equipment_text = "📭 Нет экипировки"
    
    await callback.message.edit_text(
        f"👤 {char_data['name']}\n"
        f"{RACES[char_data['race']]['name']} | {CLASSES[char_data['class']]['name']}\n"
        f"⭐ Уровень: {level} | ✨ Опыт: {xp}/{xp_next}\n"
        f"💰 Золото: {gold}\n\n"
        f"❤️ ОЗ: {char_data['hp']}/{char_data['hp_max']}\n"
        f"💙 ОД: {char_data['mp']}/{char_data['mp_max']}\n\n"
        f"⚔️ Физ.АТК: {char_data['phys_atk']} | 🔮 Маг.АТК: {char_data['mag_atk']}\n"
        f"🦶 Скр.АТК: {char_data['speed_atk']} | 🛡️ Укл: {char_data['evasion']}\n"
        f"🛡️ Ф.Защ: {char_data['phys_def']} | 🔮 М.Защ: {char_data['mag_def']}\n"
        f"⚡ Уск: {char_data['haste']} | 🎯 Удар: {char_data['hit']}\n"
        f"🍀 Крит: {char_data['crit']}% | 🛡️ Ант.Крит: {char_data['anti_crit']}%\n\n"
        f"🎒 Экипировка:\n{equipment_text}",
        reply_markup=main_menu_kb()
    )

# ==================== НАВЫКИ ====================

@dp.callback_query(F.data == "skills_menu")
async def skills_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT skill_points FROM characters WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    skill_points = result[0] if result else 0
    conn.close()
    
    text = f"⭐ Навыки | Доступно очков: {skill_points}\n\n"
    for skill_id, skill_data in SKILLS_INFO.items():
        text += f"• {skill_data['name']}\n  {skill_data['desc']}\n\n"
    
    await callback.message.edit_text(text, reply_markup=skills_kb())

@dp.callback_query(F.data.startswith("skill_up_"))
async def upgrade_skill(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    skill = callback.data.replace("skill_up_", "")
    
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT skill_points FROM characters WHERE user_id = ?", (user_id,))
    skill_points = cursor.fetchone()[0]
    
    if skill_points <= 0:
        conn.close()
        await callback.answer("❌ Нет очков навыков!", show_alert=True)
        return
    
    # Увеличиваем навык
    cursor.execute(f"UPDATE characters SET {skill} = {skill} + 1, skill_points = skill_points - 1 WHERE user_id = ?", (user_id,))
    
    # Пересчитываем боевые статы
    cursor.execute(f"SELECT {skill}, vitality, intelligence, agility, dexterity, luck FROM characters WHERE user_id = ?", (user_id,))
    stats = cursor.fetchone()
    
    # Здесь можно добавить пересчёт всех зависимых характеристик
    # Для краткости опущено, но в продакшене обязательно!
    
    conn.commit()
    conn.close()
    
    await callback.answer(f"✅ {SKILLS_INFO[skill]['name']} улучшен!", show_alert=True)
    await skills_menu(callback)
    log_action(user_id, f"Улучшен навык: {skill}")

# ==================== ИНВЕНТАРЬ ====================

@dp.callback_query(F.data == "inventory_menu")
async def inventory_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM characters WHERE user_id = ?", (user_id,))
    char_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT item_id, item_type, quantity FROM inventory WHERE character_id = ?", (char_id,))
    items = cursor.fetchall()
    conn.close()
    
    if not items:
        text = "🎒 Инвентарь пуст"
    else:
        text = "🎒 Инвентарь:\n\n"
        for item_id, item_type, qty in items:
            # Находим информацию об предмете
            item_info = None
            for category in SHOP_ITEMS.values():
                for item in category:
                    if item["id"] == item_id:
                        item_info = item
                        break
            if item_info:
                text += f"• {item_info['name']} x{qty} ({item_info['effect']})\n"
    
    await callback.message.edit_text(text, reply_markup=inventory_kb())

# ==================== МАГАЗИН ====================

@dp.callback_query(F.data == "shop_main")
async def shop_main(callback: types.CallbackQuery):
    await callback.message.edit_text("🏪 Магазин | Выберите категорию:", reply_markup=shop_main_kb())

@dp.callback_query(F.data.startswith("shop_"))
async def shop_category(callback: types.CallbackQuery):
    category = callback.data.replace("shop_", "")
    
    if category == "main":
        await shop_main(callback)
        return
    
    items = SHOP_ITEMS.get(category, [])
    if not items:
        await callback.answer("❌ Категория пуста", show_alert=True)
        return
    
    text = f"🏪 {category.upper()}:\n\n"
    builder = InlineKeyboardBuilder()
    
    for i, item in enumerate(items):
        text += f"{i+1}. {item['name']}\n   💰 {item['price']} зол. | {item['effect']}\n\n"
        builder.row(InlineKeyboardButton(text=f"Купить ({item['price']}💰)", callback_data=f"buy_{item['id']}"))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="shop_main"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def buy_item(callback: types.CallbackQuery):
    item_id = callback.data.replace("buy_", "")
    user_id = callback.from_user.id
    
    # Ищем предмет
    item = None
    for category in SHOP_ITEMS.values():
        for itm in category:
            if itm["id"] == item_id:
                item = itm
                break
        if item:
            break
    
    if not item:
        await callback.answer("❌ Предмет не найден", show_alert=True)
        return
    
    conn = get_conn()
    cursor = conn.cursor()
    
    # Проверяем золото
    cursor.execute("SELECT gold FROM users WHERE user_id = ?", (user_id,))
    gold = cursor.fetchone()[0]
    
    if gold < item["price"]:
        conn.close()
        await callback.answer("❌ Недостаточно золота!", show_alert=True)
        return
    
    # Снимаем золото
    cursor.execute("UPDATE users SET gold = gold - ? WHERE user_id = ?", (item["price"], user_id))
    
    # Добавляем в инвентарь
    cursor.execute("SELECT id FROM characters WHERE user_id = ?", (user_id,))
    char_id = cursor.fetchone()[0]
    
    cursor.execute('''
        INSERT INTO inventory (character_id, item_id, item_type, quantity) 
        VALUES (?, ?, ?, 1)
        ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + 1
    ''', (char_id, item_id, item["type"]))
    
    conn.commit()
    conn.close()
    
    await callback.answer(f"✅ Куплено: {item['name']}!", show_alert=True)
    log_action(user_id, f"Куплен предмет: {item['name']} за {item['price']} зол.")
    await shop_category(callback)

# ==================== БОЙ ====================

@dp.callback_query(F.data == "battle_menu")
async def battle_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("⚔️ Режим боя:", reply_markup=battle_menu_kb())

@dp.callback_query(F.data == "battle_hvm")
async def battle_hvm_difficulty(callback: types.CallbackQuery):
    await callback.message.edit_text("👹 Выберите сложность монстра:", reply_markup=monster_difficulty_kb())

@dp.callback_query(F.data.startswith("monsters_"))
async def select_monster_difficulty(callback: types.CallbackQuery):
    difficulty = callback.data.replace("monsters_", "")
    
    if difficulty == "titan":
        monster = MONSTERS["titan"]
        await start_battle_vs_monster(callback, monster)
    else:
        await callback.message.edit_text(f"👹 Выберите монстра ({difficulty}):", 
                                       reply_markup=monster_select_kb(difficulty))

@dp.callback_query(F.data.startswith("monster_"))
async def start_battle_vs_monster(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    difficulty = parts[1]
    index = int(parts[2])
    
    monster = MONSTERS[difficulty][index]
    await start_battle_vs_monster(callback, monster)

async def start_battle_vs_monster(callback: types.CallbackQuery, monster):
    user_id = callback.from_user.id
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT hp, hp_max, phys_atk, mag_atk, evasion, crit FROM characters WHERE user_id = ?", (user_id,))
    char = cursor.fetchone()
    conn.close()
    
    if not char:
        await callback.answer("❌ Персонаж не найден", show_alert=True)
        return
    
    battle_data = {
        "monster": monster,
        "monster_hp": monster["hp"],
        "player_hp": char[0],
        "player_max_hp": char[1],
        "turn": "player"
    }
    
    await dp.storage.set_data(user_id=user_id, data=battle_data)
    
    await callback.message.edit_text(
        f"⚔️ БОЙ НАЧАЛСЯ!\n\n"
        f"👹 {monster['name']}\n"
        f"❤️ ОЗ: {monster['hp']}/{monster['hp']} | ⚔️ АТК: {monster['atk']} | 🛡️ ЗАЩ: {monster['def']}\n\n"
        f"🎲 Бросьте кубик (1-20) и введите результат:",
        reply_markup=battle_action_kb()
    )
    await dp.storage.set_state(user_id=user_id, state=BattleState.waiting_for_player_roll)

@dp.message(BattleState.waiting_for_player_roll)
async def process_player_roll(message: types.Message, state: FSMContext):
    try:
        roll = int(message.text)
        if not (1 <= roll <= 20):
            await message.answer("❌ Число должно быть от 1 до 20!")
            return
    except ValueError:
        await message.answer("❌ Введите число от 1 до 20!")
        return
    
    battle_data = await dp.storage.get_data(user_id=message.from_user.id)
    
    # Расчёт урона игрока
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT phys_atk, crit, luck FROM characters WHERE user_id = ?", (message.from_user.id,))
    stats = cursor.fetchone()
    conn.close()
    
    crit_chance = stats[1] + stats[2] * 4
    is_crit = roll >= 18 or (roll + crit_chance > 20)
    damage = roll + stats[0]
    if is_crit:
        damage = int(damage * 1.5)
    
    battle_data["monster_hp"] -= damage
    
    if battle_data["monster_hp"] <= 0:
        # Победа
        xp_reward = battle_data["monster"]["xp"]
        gold_reward = battle_data["monster"]["gold"]
        
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET xp = xp + ?, gold = gold + ? WHERE user_id = ?", 
                      (xp_reward, gold_reward, message.from_user.id))
        conn.commit()
        conn.close()
        
        await message.answer(
            f"🎉 ПОБЕДА!\n\n"
            f"👹 {battle_data['monster']['name']} повержен!\n"
            f"✨ +{xp_reward} опыта | 💰 +{gold_reward} золота",
            reply_markup=main_menu_kb()
        )
        await state.clear()
        await dp.storage.clear(user_id=message.from_user.id)
        log_action(message.from_user.id, f"Победа над {battle_data['monster']['name']}")
        return
    
    # Ход монстра
    monster_roll = roll  # Для демо: используем тот же бросок, в реальности игрок вводит отдельно
    monster_damage = monster_roll + battle_data["monster"]["atk"] - 2  # -2 за защиту игрока (упрощённо)
    monster_damage = max(1, monster_damage)  # Минимум 1 урон
    
    battle_data["player_hp"] -= monster_damage
    
    if battle_data["player_hp"] <= 0:
        # Поражение
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET gold = 0 WHERE user_id = ?", (message.from_user.id,))
        cursor.execute("UPDATE characters SET hp = hp_max WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        conn.close()
        
        await message.answer(
            f"💀 ПОРАЖЕНИЕ!\n\n"
            f"Вы потеряли всё золото, но воскресли с полным ОЗ.\n"
            f"Используйте зелья для восстановления в бою!",
            reply_markup=main_menu_kb()
        )
        await state.clear()
        await dp.storage.clear(user_id=message.from_user.id)
        log_action(message.from_user.id, "Поражение в бою")
        return
    
    await dp.storage.set_data(user_id=message.from_user.id, data=battle_data)
    
    await message.answer(
        f"⚔️ Ваш урон: {damage} {'💥 КРИТ!' if is_crit else ''}\n"
        f"👹 {battle_data['monster']['name']}: {battle_data['monster_hp']} ОЗ\n\n"
        f"👹 Атака монстра: {monster_damage} урона\n"
        f"❤️ Ваше ОЗ: {battle_data['player_hp']}\n\n"
        f"🎲 Ваш следующий бросок (1-20):",
        reply_markup=battle_action_kb()
    )

@dp.callback_query(BattleState.waiting_for_player_roll, F.data == "battle_surrender")
async def surrender_battle(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    conn = get_conn()
    cursor = conn.cursor()
    # Восстанавливаем ОЗ при сдаче
    cursor.execute("UPDATE characters SET hp = hp_max WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        "🏳️ Вы сдались.\n"
        "ОЗ восстановлено, золото сохранено.\n"
        "Попробуйте ещё раз, герой!",
        reply_markup=main_menu_kb()
    )
    await state.clear()
    await dp.storage.clear(user_id=user_id)
    log_action(user_id, "Сдался в бою")

# ==================== КАРТОЧКИ ====================

@dp.callback_query(F.data == "cards_menu")
async def cards_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("🃏 Выберите тип карты:", reply_markup=cards_kb())

@dp.callback_query(F.data.startswith("card_"))
async def draw_card(callback: types.CallbackQuery):
    card_type = callback.data.replace("card_", "")
    cards = CARDS.get(card_type, [])
    
    if not cards:
        await callback.answer("❌ Карты не найдены", show_alert=True)
        return
    
    import random
    card = random.choice(cards)
    
    colors = {"red": "🔴", "yellow": "🟡", "green": "🟢", "black": "⚫"}
    
    await callback.message.edit_text(
        f"{colors.get(card_type, '🃏')} Выпала карта:\n\n"
        f"✨ {card['name']}\n"
        f"📋 Эффект: {card['effect']}",
        reply_markup=cards_kb()
    )
    log_action(callback.from_user.id, f"Вытянута карта {card_type}: {card['name']}")

# ==================== ЛОГИ ====================

@dp.callback_query(F.data == "logs_view")
async def view_logs(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT action, details, timestamp FROM logs 
        WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10
    ''', (user_id,))
    logs = cursor.fetchall()
    conn.close()
    
    if not logs:
        text = "📋 Лог пуст"
    else:
        text = "📋 Последние действия:\n\n"
        for action, details, timestamp in logs:
            text += f"⏰ {timestamp}\n📌 {action}\n📝 {details}\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def log_action(user_id, action, details=""):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, action, details)
    )
    conn.commit()
    conn.close()

async def recalculate_stats(user_id):
    """Пересчитывает боевые характеристики на основе навыков и экипировки"""
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM characters WHERE user_id = ?", (user_id,))
    char = cursor.fetchone()
    
    if not char:
        conn.close()
        return
    
    # Базовые статы + экипировка (упрощённо)
    # В продакшене нужно загружать данные предметов и применять бонусы
    
    # Пример пересчёта HP
    new_hp_max = 100 + char[7] * 15  # vitality * 15
    cursor.execute("UPDATE characters SET hp_max = ? WHERE user_id = ?", (new_hp_max, user_id))
    
    conn.commit()
    conn.close()

# ==================== ЗАПУСК ====================

async def on_startup():
    init_db()
    logging.info("🤖 Бот запущен!")

async def on_shutdown():
    await bot.session.close()
    logging.info("🔴 Бот остановлен")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
