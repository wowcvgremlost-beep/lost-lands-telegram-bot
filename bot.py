# ============================================================================
# ПОТЕРЯННЫЕ ЗЕМЛИ — TELEGRAM БОТ (Railway версия)
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
import asyncio

# Получаем токен из переменной окружения Railway
API_TOKEN = os.environ.get('BOT_TOKEN')

if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Добавьте его в переменные окружения Railway.")

# Инициализация
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния для конечного автомата
class GameStates(StatesGroup):
    choosing_action = State()
    choosing_hero = State()
    upgrading_stat = State()
    choosing_floor = State()
    waiting_dice = State()

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            hero1_name TEXT DEFAULT 'Герой1',
            hero1_lvl INTEGER DEFAULT 1,
            hero1_exp INTEGER DEFAULT 0,
            hero1_skill_points INTEGER DEFAULT 0,
            hero1_max_hp INTEGER DEFAULT 100,
            hero1_hp INTEGER DEFAULT 100,
            hero1_atk INTEGER DEFAULT 10,
            hero1_arm INTEGER DEFAULT 5,
            hero1_agi INTEGER DEFAULT 5,
            hero2_name TEXT DEFAULT 'Герой2',
            hero2_lvl INTEGER DEFAULT 1,
            hero2_exp INTEGER DEFAULT 0,
            hero2_skill_points INTEGER DEFAULT 0,
            hero2_max_hp INTEGER DEFAULT 100,
            hero2_hp INTEGER DEFAULT 100,
            hero2_atk INTEGER DEFAULT 10,
            hero2_arm INTEGER DEFAULT 5,
            hero2_agi INTEGER DEFAULT 5,
            hero3_name TEXT DEFAULT 'Герой3',
            hero3_lvl INTEGER DEFAULT 1,
            hero3_exp INTEGER DEFAULT 0,
            hero3_skill_points INTEGER DEFAULT 0,
            hero3_max_hp INTEGER DEFAULT 100,
            hero3_hp INTEGER DEFAULT 100,
            hero3_atk INTEGER DEFAULT 10,
            hero3_arm INTEGER DEFAULT 5,
            hero3_agi INTEGER DEFAULT 5,
            hero4_name TEXT DEFAULT 'Герой4',
            hero4_lvl INTEGER DEFAULT 1,
            hero4_exp INTEGER DEFAULT 0,
            hero4_skill_points INTEGER DEFAULT 0,
            hero4_max_hp INTEGER DEFAULT 100,
            hero4_hp INTEGER DEFAULT 100,
            hero4_atk INTEGER DEFAULT 10,
            hero4_arm INTEGER DEFAULT 5,
            hero4_agi INTEGER DEFAULT 5,
            hero5_name TEXT DEFAULT 'Герой5',
            hero5_lvl INTEGER DEFAULT 1,
            hero5_exp INTEGER DEFAULT 0,
            hero5_skill_points INTEGER DEFAULT 0,
            hero5_max_hp INTEGER DEFAULT 100,
            hero5_hp INTEGER DEFAULT 100,
            hero5_atk INTEGER DEFAULT 10,
            hero5_arm INTEGER DEFAULT 5,
            hero5_agi INTEGER DEFAULT 5,
            hero6_name TEXT DEFAULT 'Герой6',
            hero6_lvl INTEGER DEFAULT 1,
            hero6_exp INTEGER DEFAULT 0,
            hero6_skill_points INTEGER DEFAULT 0,
            hero6_max_hp INTEGER DEFAULT 100,
            hero6_hp INTEGER DEFAULT 100,
            hero6_atk INTEGER DEFAULT 10,
            hero6_arm INTEGER DEFAULT 5,
            hero6_agi INTEGER DEFAULT 5,
            current_hero INTEGER DEFAULT 1
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS monsters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            floor INTEGER,
            name TEXT,
            lvl INTEGER,
            hp INTEGER,
            atk INTEGER,
            arm INTEGER,
            agi INTEGER,
            exp INTEGER
        )
    ''')
    # Заполняем монстров (20 штук)
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
        cur.executemany('INSERT INTO monsters (floor, name, lvl, hp, atk, arm, agi, exp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', monsters)
    conn.commit()
    conn.close()

# Получение данных игрока
def get_player(user_id):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    if not row:
        # Создаём нового игрока
        cur.execute('INSERT INTO players (user_id) VALUES (?)', (user_id,))
        conn.commit()
        cur.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
        row = cur.fetchone()
    conn.close()
    return row

# Обновление данных игрока
def update_player(user_id, **kwargs):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]
    cur.execute(f'UPDATE players SET {set_clause} WHERE user_id = ?', values)
    conn.commit()
    conn.close()

# Расчёт урона
def calculate_damage(atk, arm, dice):
    base = max(1, atk - arm * 0.7)
    return max(1, round(base + (dice - 10)))

# ОСНОВНЫЕ КОМАНДЫ
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    player = get_player(user_id)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧙 Персонажи"), KeyboardButton(text="⚔️ Бой")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    await message.answer(
        "🌍 Добро пожаловать в Потерянные земли!\n\n"
        "🎲 Настольная RPG с физическими кубиками d20\n"
        "🧙 Управляйте 6 героями, прокачивайте навыки\n"
        "👹 Сражайтесь с монстрами 5 этажей подземелья\n"
        "⚔️ PvP-бои с друзьями\n\n"
        "Выберите действие:",
        reply_markup=kb
    )
    await state.set_state(GameStates.choosing_action)

# МЕНЮ ПЕРСОНАЖЕЙ
@dp.message(lambda m: m.text == "🧙 Персонажи")
async def characters_menu(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1️⃣ Герой 1"), KeyboardButton(text="2️⃣ Герой 2"), KeyboardButton(text="3️⃣ Герой 3")],
            [KeyboardButton(text="4️⃣ Герой 4"), KeyboardButton(text="5️⃣ Герой 5"), KeyboardButton(text="6️⃣ Герой 6")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await message.answer("Выберите героя для просмотра/прокачки:", reply_markup=kb)
    await state.set_state(GameStates.choosing_hero)

# ВЫБОР ГЕРОЯ
@dp.message(GameStates.choosing_hero)
async def select_hero(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await start(message, state)
        return
    
    try:
        hero_num = int(message.text.split()[0].replace('️⃣', ''))
    except:
        await message.answer("❌ Выберите героя из меню!")
        return
    
    user_id = message.from_user.id
    player = get_player(user_id)
    
    # Индексы для героя (начинаются с 1)
    idx = {
        1: (1, 2, 3, 4, 5, 6, 7, 8, 9),
        2: (10,11,12,13,14,15,16,17,18),
        3: (19,20,21,22,23,24,25,26,27),
        4: (28,29,30,31,32,33,34,35,36),
        5: (37,38,39,40,41,42,43,44,45),
        6: (46,47,48,49,50,51,52,53,54)
    }[hero_num]
    
    name = player[idx[0]]
    lvl = player[idx[1]]
    exp = player[idx[2]]
    skill_points = player[idx[3]]
    max_hp = player[idx[4]]
    hp = player[idx[5]]
    atk = player[idx[6]]
    arm = player[idx[7]]
    agi = player[idx[8]]
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"❤️ Здоровье ({max_hp})"), KeyboardButton(text=f"⚔️ Атака ({atk})")],
            [KeyboardButton(text=f"🛡️ Броня ({arm})"), KeyboardButton(text=f"🏃 Ловкость ({agi})")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    await message.answer(
        f"🧙‍♂️ Герой: {name}\n"
        f"📊 Уровень: {lvl} | Опыт: {exp}/{lvl * 100}\n"
        f"⭐ Очки навыков: {skill_points}\n"
        f"❤️ Здоровье: {hp}/{max_hp}\n"
        f"⚔️ Атака: {atk}\n"
        f"🛡️ Броня: {arm}\n"
        f"🏃 Ловкость: {agi}\n\n"
        "Выберите параметр для прокачки:",
        reply_markup=kb
    )
    await state.update_data(hero_num=hero_num, skill_points=skill_points)
    await state.set_state(GameStates.upgrading_stat)

# ПРОКАЧКА ПАРАМЕТРА
@dp.message(GameStates.upgrading_stat)
async def upgrade_stat(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await characters_menu(message, state)
        return
    
    data = await state.get_data()
    hero_num = data['hero_num']
    skill_points = data['skill_points']
    
    if skill_points <= 0:
        await message.answer("❌ Нет очков навыков!\nПобедите монстров, чтобы получить опыт и повысить уровень.", 
                           reply_markup=ReplyKeyboardMarkup(
                               keyboard=[[KeyboardButton(text="⚔️ Бой")]],
                               resize_keyboard=True
                           ))
        return
    
    stat_text = message.text.split()[0]
    
    stat_map = {
        "❤️": ("max_hp", 5, "Здоровье"),
        "⚔️": ("atk", 2, "Атака"),
        "🛡️": ("arm", 1, "Броня"),
        "🏃": ("agi", 1, "Ловкость")
    }
    
    if stat_text not in stat_map:
        await message.answer("❌ Выберите параметр из меню!")
        return
    
    stat_name_db, bonus, stat_name_ru = stat_map[stat_text]
    
    # Индексы для обновления БД
    idx = {
        1: {"max_hp": 5, "hp": 6, "atk": 7, "arm": 8, "agi": 9, "skill_points": 4},
        2: {"max_hp": 14, "hp": 15, "atk": 16, "arm": 17, "agi": 18, "skill_points": 13},
        3: {"max_hp": 23, "hp": 24, "atk": 25, "arm": 26, "agi": 27, "skill_points": 22},
        4: {"max_hp": 32, "hp": 33, "atk": 34, "arm": 35, "agi": 36, "skill_points": 31},
        5: {"max_hp": 41, "hp": 42, "atk": 43, "arm": 44, "agi": 45, "skill_points": 40},
        6: {"max_hp": 50, "hp": 51, "atk": 52, "arm": 53, "agi": 54, "skill_points": 49}
    }[hero_num]
    
    user_id = message.from_user.id
    player = get_player(user_id)
    
    # Обновляем параметр
    current_val = player[idx[stat_name_db]]
    update_player(user_id, **{
        list(idx.keys())[list(idx.values()).index(idx[stat_name_db])]: current_val + bonus,
        "skill_points": player[idx["skill_points"]] - 1
    })
    
    # Если здоровье — обновляем текущее тоже
    if stat_name_db == "max_hp":
        update_player(user_id, **{
            list(idx.keys())[list(idx.values()).index(idx["hp"])]: player[idx["hp"]] + bonus
        })
    
    await message.answer(
        f"✅ Прокачано!\n"
        f"+{bonus} к {stat_name_ru}\n\n"
        f"⭐ Осталось очков навыков: {skill_points - 1}",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🧙 Персонажи"), KeyboardButton(text="⚔️ Бой")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(GameStates.choosing_action)

# МЕНЮ БОЯ
@dp.message(lambda m: m.text == "⚔️ Бой")
async def battle_menu(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1️⃣ Этаж 1"), KeyboardButton(text="2️⃣ Этаж 2"), KeyboardButton(text="3️⃣ Этаж 3")],
            [KeyboardButton(text="4️⃣ Этаж 4"), KeyboardButton(text="5️⃣ Этаж 5")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await message.answer(
        "⚔️ Выберите этаж для боя:\n\n"
        "1️⃣ Этаж 1: Гоблины, Крысы, Скелеты, Пауки\n"
        "2️⃣ Этаж 2: Орки, Тролли, Гарпии, Зомби\n"
        "3️⃣ Этаж 3: Минотавры, Вампиры, Грифоны, Элементали\n"
        "4️⃣ Этаж 4: Циклопы, Медузы, Демоны, Личи\n"
        "5️⃣ Этаж 5: Драконы, Гидры, Архидемоны, Титаны",
        reply_markup=kb
    )
    await state.set_state(GameStates.choosing_floor)

# НАЧАЛО БОЯ С МОНСТРОМ
@dp.message(GameStates.choosing_floor)
async def start_battle(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await start(message, state)
        return
    
    try:
        floor = int(message.text.split()[0].replace('️⃣', ''))
    except:
        await message.answer("❌ Выберите этаж из меню!")
        return
    
    user_id = message.from_user.id
    
    # Выбираем случайного монстра этажа
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM monsters WHERE floor = ? ORDER BY RANDOM() LIMIT 1', (floor,))
    monster = cur.fetchone()
    conn.close()
    
    if not monster:
        await message.answer("❌ На этом этаже нет монстров!")
        return
    
    # Загружаем данные текущего героя игрока (используем Герой1 для простоты)
    player = get_player(user_id)
    
    # Берём Герой1 (индексы 1-9)
    hero_name = player[1]
    hero_lvl = player[2]
    hero_hp = player[6]
    hero_atk = player[7]
    hero_arm = player[8]
    hero_agi = player[9]
    
    monster_name = monster[2]
    monster_lvl = monster[3]
    monster_hp = monster[4]
    monster_atk = monster[5]
    monster_arm = monster[6]
    monster_agi = monster[7]
    monster_exp = monster[8]
    
    # Сохраняем состояние боя
    await state.update_data(
        hero_name=hero_name,
        hero_lvl=hero_lvl,
        hero_hp=hero_hp,
        hero_atk=hero_atk,
        hero_arm=hero_arm,
        hero_agi=hero_agi,
        monster_name=monster_name,
        monster_lvl=monster_lvl,
        monster_hp=monster_hp,
        monster_atk=monster_atk,
        monster_arm=monster_arm,
        monster_agi=monster_agi,
        monster_exp=monster_exp,
        floor=floor
    )
    
    await message.answer(
        f"⚔️ БОЙ НАЧАТ!\n"
        f"{'='*30}\n"
        f"🧙 {hero_name} (ур. {hero_lvl})\n"
        f"❤️ Здоровье: {hero_hp}\n"
        f"⚔️ Атака: {hero_atk} | 🛡️ Броня: {hero_arm}\n"
        f"🏃 Ловкость: {hero_agi}\n\n"
        f"👹 {monster_name} (ур. {monster_lvl})\n"
        f"❤️ Здоровье: {monster_hp}\n"
        f"⚔️ Атака: {monster_atk} | 🛡️ Броня: {monster_arm}\n"
        f"🏃 Ловкость: {monster_agi}\n"
        f"{'='*30}\n\n"
        f"🎲 КИНЬТЕ КУБИК d20!\n"
        f"Введите результат броска (число от 1 до 20):",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True,
            one_time_keyboard=False
        )
    )
    await state.set_state(GameStates.waiting_dice)

# ОБРАБОТКА БРОСКА КУБИКА
@dp.message(GameStates.waiting_dice)
async def process_dice(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await start(message, state)
        return
    
    try:
        dice = int(message.text)
        if dice < 1 or dice > 20:
            raise ValueError
    except:
        await message.answer("❌ Введите число от 1 до 20!\n🎲 Киньте кубик d20 и введите результат:")
        return
    
    data = await state.get_data()
    
    # Генерируем бросок монстра
    monster_dice = random.randint(1, 20)
    
    # Расчёт урона
    dmg_to_monster = calculate_damage(data['hero_atk'], data['monster_arm'], dice)
    dmg_to_hero = calculate_damage(data['monster_atk'], data['hero_arm'], monster_dice)
    
    # Обновление здоровья
    new_monster_hp = max(0, data['monster_hp'] - dmg_to_monster)
    new_hero_hp = max(0, data['hero_hp'] - dmg_to_hero)
    
    log = (
        f"🎲 РАУНД:\n"
        f"{'='*30}\n"
        f"🧙 {data['hero_name']} бросает {dice} → {dmg_to_monster} урона!\n"
        f"👹 {data['monster_name']} бросает {monster_dice} → {dmg_to_hero} урона!\n"
        f"{'='*30}\n\n"
        f"❤️ {data['hero_name']}: {new_hero_hp} HP\n"
        f"❤️ {data['monster_name']}: {new_monster_hp} HP"
    )
    
    await message.answer(log)
    
    # Проверка завершения боя
    if new_monster_hp <= 0 and new_hero_hp <= 0:
        # Ничья
        await message.answer(
            "⚔️ НИЧЬЯ!\n"
            "Оба пали в бою...\n"
            "🧙 Герой воскресает с полным здоровьем.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🧙 Персонажи"), KeyboardButton(text="⚔️ Бой")]],
                resize_keyboard=True
            )
        )
        # Воскрешение героя
        update_player(message.from_user.id, hero1_hp=data['hero_hp'])
        await state.set_state(GameStates.choosing_action)
        
    elif new_monster_hp <= 0:
        # Победа
        # Начисление опыта
        exp_gain = int(data['monster_exp'] * (1 + (data['monster_lvl'] - data['hero_lvl']) * 0.1))
        new_exp = data['hero_exp'] + exp_gain if 'hero_exp' in data else exp_gain
        
        # Проверка уровня
        exp_for_next = data['hero_lvl'] * 100
        if new_exp >= exp_for_next:
            new_lvl = data['hero_lvl'] + 1
            await message.answer(
                f"✨ ПОБЕДА!\n"
                f"{'='*30}\n"
                f"✅ {data['hero_name']} победил {data['monster_name']}!\n"
                f"✨ Получено {exp_gain} опыта!\n"
                f"{'='*30}\n\n"
                f"🎉 ПОВЫШЕНИЕ УРОВНЯ!\n"
                f"{data['hero_name']} достиг {new_lvl} уровня!\n"
                f"+5 очков навыков, +10 здоровья, +1 ко всем параметрам!\n"
                f"🧙 Герой воскресает с полным здоровьем.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🧙 Персонажи"), KeyboardButton(text="⚔️ Бой")]],
                    resize_keyboard=True
                )
            )
            # Обновляем все параметры
            update_player(
                message.from_user.id,
                hero1_lvl=new_lvl,
                hero1_exp=new_exp - exp_for_next,
                hero1_skill_points=data.get('hero_skill_points', 0) + 5,
                hero1_max_hp=data['hero_hp'] + 10,
                hero1_hp=data['hero_hp'] + 10,
                hero1_atk=data['hero_atk'] + 1,
                hero1_arm=data['hero_arm'] + 1,
                hero1_agi=data['hero_agi'] + 1
            )
        else:
            await message.answer(
                f"✨ ПОБЕДА!\n"
                f"{'='*30}\n"
                f"✅ {data['hero_name']} победил {data['monster_name']}!\n"
                f"✨ Получено {exp_gain} опыта!\n"
                f"📊 Всего опыта: {new_exp}/{exp_for_next}\n"
                f"{'='*30}\n\n"
                f"🧙 Герой воскресает с полным здоровьем.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🧙 Персонажи"), KeyboardButton(text="⚔️ Бой")]],
                    resize_keyboard=True
                )
            )
            update_player(
                message.from_user.id,
                hero1_exp=new_exp,
                hero1_hp=data['hero_hp']  # Воскрешение
            )
        await state.set_state(GameStates.choosing_action)
        
    elif new_hero_hp <= 0:
        # Поражение
        await message.answer(
            f"☠️ ПОРАЖЕНИЕ!\n"
            f"{'='*30}\n"
            f"💀 {data['hero_name']} пал в бою с {data['monster_name']}...\n"
            f"{'='*30}\n\n"
            f"✨ ВОСКРЕШЕНИЕ!\n"
            f"🧙 Герой воскресает с полным здоровьем.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🧙 Персонажи"), KeyboardButton(text="⚔️ Бой")]],
                resize_keyboard=True
            )
        )
        # Воскрешение
        update_player(message.from_user.id, hero1_hp=data['hero_hp'])
        await state.set_state(GameStates.choosing_action)
        
    else:
        # Продолжение боя
        await state.update_data(hero_hp=new_hero_hp, monster_hp=new_monster_hp)
        await message.answer(
            "🎲 КИНЬТЕ КУБИК СНОВА!\n"
            "Введите результат броска (число от 1 до 20):"
        )

# СТАТИСТИКА
@dp.message(lambda m: m.text == "📊 Статистика")
async def stats(message: types.Message):
    await message.answer(
        "📊 СТАТИСТИКА ИГРЫ:\n"
        "{'='*30}\n"
        "• 6 уникальных героев для прокачки\n"
        "• 20 видов монстров на 5 этажах\n"
        "• Система уровней и опыта\n"
        "• Прокачка: здоровье, атака, броня, ловкость\n"
        "• PvP-бои (в разработке)\n"
        "• Физические кубики d20 для атмосферы!\n"
        "{'='*30}\n\n"
        "🎲 Как играть:\n"
        "1. Выберите героя в меню «Персонажи»\n"
        "2. Прокачайте параметры за очки навыков\n"
        "3. Идите на «Бой» и выберите этаж\n"
        "4. Киньте физический кубик d20\n"
        "5. Введите результат в бота\n"
        "6. Бот рассчитает урон и покажет результат\n"
        "7. Побеждайте монстров и получайте опыт!",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🧙 Персонажи"), KeyboardButton(text="⚔️ Бой")]],
            resize_keyboard=True
        )
    )

# ПОМОЩЬ
@dp.message(lambda m: m.text == "❓ Помощь")
async def help_cmd(message: types.Message):
    await message.answer(
        "❓ ПОМОЩЬ:\n"
        "{'='*30}\n\n"
        "🎲 КУБИКИ:\n"
        "• Используйте физический кубик d20\n"
        "• Бросок 1-20 влияет на урон\n"
        "• 10 = базовый урон, 20 = +10, 1 = -9\n\n"
        "⚔️ БОЙ:\n"
        "• Оба участника наносят урон одновременно\n"
        "• Победитель получает опыт (только монстры)\n"
        "• После смерти герой воскресает с полным HP\n\n"
        "⭐ ПРОКАЧКА:\n"
        "• +5 HP = +5 макс. здоровья и текущего\n"
        "• +2 ATK = +2 к атаке за 1 очко навыка"
        "• +1 ARM = +1 к броне за 1 очко навыка"
        "• +1 AGI = +1 к ловкости за 1 очко навыка"
        "{'='*30}",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🧙 Персонажи"), KeyboardButton(text="⚔️ Бой")]],
            resize_keyboard=True
        )
    )

# ЗАПУСК БОТА
async def main():
    init_db()
    print("🤖 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
