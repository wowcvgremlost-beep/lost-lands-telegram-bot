# ============================================================================
# ПОТЕРЯННЫЕ ЗЕМЛИ — ИСПРАВЛЕННАЯ ВЕРСИЯ С КНОПКАМИ ДЕЙСТВИЙ
# ============================================================================
import os
import sqlite3
import random
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import F
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_TOKEN = os.environ.get('BOT_TOKEN')
if not API_TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

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

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ (без изменений)
# ============================================================================
def init_db():
    # ... (полный код инициализации базы данных без изменений) ...
    # [Код из вашего файла - он рабочий, не требует изменений]
    pass  # Замените на полный код из вашего файла

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (без изменений)
# ============================================================================
# ... (все функции: get_player, create_player, update_player, get_all_players, 
# get_free_slots, get_monster, calculate_damage, add_gold, remove_gold, 
# get_player_gold, add_item_to_inventory, get_inventory, get_shop_items, 
# equip_item, unequip_item, sell_item, use_potion_in_battle, create_battle, 
# get_active_battle, update_battle, complete_battle - без изменений) ...
# [Код из вашего файла - он рабочий, не требует изменений]

# ============================================================================
# КЛАВИАТУРЫ (без изменений)
# ============================================================================
# ... (все функции клавиатур: get_main_keyboard, get_class_keyboard, 
# get_battle_type_keyboard, get_free_slots_keyboard, get_opponent_keyboard, 
# get_monster_keyboard, get_upgrade_keyboard, get_shop_category_keyboard, 
# get_slot_emoji, get_category_emoji - без изменений) ...
# [Код из вашего файла - он рабочий, не требует изменений]

# ============================================================================
# ИСПРАВЛЕННАЯ ФУНКЦИЯ ОТОБРАЖЕНИЯ ПЕРСОНАЖА
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
# ИСПРАВЛЕННАЯ СИСТЕМА ИНВЕНТАРЯ С КНОПКАМИ ДЕЙСТВИЙ
# ============================================================================
def get_inventory_item_keyboard(item_id, is_equipped):
    """Клавиатура действий для конкретного предмета"""
    buttons = []
    if is_equipped:
        buttons.append([KeyboardButton(text=f"❌ Снять предмет {item_id}")])
    else:
        buttons.append([KeyboardButton(text=f"✅ Надеть предмет {item_id}")])
    
    buttons.append([KeyboardButton(text=f"💰 Продать предмет {item_id}")])
    buttons.append([KeyboardButton(text=f"🔥 Прокачать предмет {item_id}")])
    buttons.append([KeyboardButton(text="🔙 Вернуться в инвентарь")])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_inventory_main_keyboard():
    """Основная клавиатура инвентаря"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Надеть предмет"), KeyboardButton(text="❌ Снять предмет")],
            [KeyboardButton(text="💰 Продать предмет"), KeyboardButton(text="🔥 Прокачать предмет")],
            [KeyboardButton(text="🔙 В главное меню")]
        ],
        resize_keyboard=True
    )

@dp.message(F.text == "🎒 Инвентарь")
async def inventory_menu(message: types.Message, state: FSMContext):
    """Отобразить инвентарь с улучшенным интерфейсом"""
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
            "📭 ИНВЕНТАРЬ ПУСТ!\n"
            "Посетите магазин, чтобы купить предметы.",
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
    response += "Выберите действие с предметом:\n"
    response += "• Нажмите на предмет ниже для выбора действий\n"
    response += "• Или используйте кнопки внизу для массовых действий"
    
    # Создаем клавиатуру с кнопками для каждого предмета
    item_buttons = []
    for item in items:
        status_emoji = "✅" if item[5] else "🔲"
        btn_text = f"{status_emoji} {item[0]}. {item[2]} (Ур. {item[8]})"
        item_buttons.append([KeyboardButton(text=f"📌 {btn_text}")])
    
    # Добавляем основные кнопки действий
    action_buttons = [
        [KeyboardButton(text="✅ Надеть предмет"), KeyboardButton(text="❌ Снять предмет")],
        [KeyboardButton(text="💰 Продать предмет"), KeyboardButton(text="🔥 Прокачать предмет")],
        [KeyboardButton(text="🔙 В главное меню")]
    ]
    
    # Объединяем кнопки
    full_buttons = item_buttons + action_buttons
    keyboard = ReplyKeyboardMarkup(keyboard=full_buttons, resize_keyboard=True)
    
    await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)

@dp.message(GameStates.in_inventory)
async def inventory_handler(message: types.Message, state: FSMContext):
    """Обработчик действий в инвентаре"""
    data = await state.get_data()
    items = data.get('inventory_items', [])
    player_id = message.from_user.id
    
    # Обработка возврата в главное меню
    if message.text == "🔙 В главное меню":
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
            
            # Сохраняем выбранный предмет в состоянии
            await state.update_data(selected_item=selected_item)
            await state.set_state(GameStates.choosing_item_action)
            
            # Отправляем клавиатуру действий для этого предмета
            await message.answer(
                item_info, 
                parse_mode="Markdown", 
                reply_markup=get_inventory_item_keyboard(selected_item[0], selected_item[5])
            )
        except Exception as e:
            logger.error(f"Ошибка при выборе предмета: {e}")
            await message.answer("❌ Ошибка при выборе предмета. Попробуйте снова.")
        return
    
    # Обработка массовых действий
    if message.text == "✅ Надеть предмет":
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
        return
    
    if message.text == "❌ Снять предмет":
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
        return
    
    if message.text == "💰 Продать предмет":
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
        return
    
    if message.text == "🔥 Прокачать предмет":
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
        return
    
    await message.answer("❌ Неизвестная команда! Используйте кнопки меню.")

@dp.message(GameStates.choosing_item_action)
async def item_action_handler(message: types.Message, state: FSMContext):
    """Обработчик действий с выбранным предметом"""
    data = await state.get_data()
    selected_item = data.get('selected_item')
    player_id = message.from_user.id
    
    if message.text == "🔙 Вернуться в инвентарь":
        await inventory_menu(message, state)
        return
    
    if not selected_item:
        await message.answer("❌ Предмет не выбран! Вернитесь в инвентарь.")
        await inventory_menu(message, state)
        return
    
    # Извлекаем ID предмета из текста кнопки
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
            await message.answer("❌ Неизвестное действие!")
            await inventory_menu(message, state)
            return
        
        item_id = int(message.text.split(" ")[-1])
        
        # Проверяем, что предмет существует и принадлежит игроку
        if selected_item[0] != item_id:
            await message.answer("❌ Выбран неверный предмет! Вернитесь в инвентарь.")
            await inventory_menu(message, state)
            return
        
    except Exception as e:
        logger.error(f"Ошибка при обработке действия: {e}")
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
        await message.answer("❌ Введите номер предмета!")
        return
    
    data = await state.get_data()
    action = data.get('action')
    items = data.get('items', [])
    player_id = message.from_user.id
    
    selected_item = next((item for item in items if item[0] == item_id), None)
    if not selected_item:
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
# ОСНОВНЫЕ КОМАНДЫ (сокращены для экономии места)
# ============================================================================
# ... (остальные обработчики: /start, прокачка навыков, магазин, бой, статистика, помощь) ...
# [Код из вашего файла - он рабочий, не требует изменений]

async def main():
    init_db()
    logger.info("🤖 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
