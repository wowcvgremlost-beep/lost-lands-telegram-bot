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
            battle_type="pvp",
            attacker=attacker,
            defender=opponent,
            opponent_name=opponent_name,
            attacker_hp=attacker[9],
            defender_hp=opponent[9],
            round_num=1
        )
        
        # Отправляем уведомление второму игроку
        try:
            await bot.send_message(
                chat_id=opponent[0],
                text=f"⚔️ ВЫЗОВ НА БОЙ!\n"
                     f"Игрок {attacker[3]} вызывает вас на дуэль!\n"
                     f"Нажмите /battle чтобы принять вызов."
            )
        except Exception as e:
            await message.answer(f"⚠️ Не удалось отправить вызов {opponent_name} (он должен написать боту /start)")
        
        await message.answer(
            f"⚔️ ВЫЗОВ ОТПРАВЛЕН!\n"
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
    battle_type = data.get('battle_type')
    
    await state.update_data(attacker_dice=dice)
    
    if battle_type == "pvp":
        # Ждём броска защитника — отправляем уведомление
        defender_name = data['opponent_name']
        defender_id = data['defender'][0]
        
        # Отправляем запрос второму игроку
        try:
            await bot.send_message(
                chat_id=defender_id,
                text=f"🎲 {data['attacker'][3]} бросил кубик: {dice}\n"
                     f"Ваша очередь! Киньте кубик d20 и введите результат (1-20):"
            )
            # Сохраняем состояние боя для второго игрока в глобальном хранилище
            # (В реальном проекте лучше использовать базу данных)
            await state.update_data(defender_notified=True)
            await message.answer(
                f"✅ Ваш бросок ({dice}) отправлен {defender_name}.\n"
                f"Ожидайте его ответа..."
            )
            # Оставляем состояние как есть — ждём ответа от второго игрока
            # Второй игрок должен написать боту число напрямую
            # Для упрощения: второй игрок вводит число в чат с ботом
            await state.set_state(GameStates.waiting_defender_dice)
        except Exception as e:
            await message.answer(f"❌ Не удалось отправить сообщение {defender_name}. Убедитесь, что он запустил бота (/start)")
    
    else:  # PvE
        await message.answer(
            f"🎲 Теперь киньте кубик d20 для {data['monster_name']} и введите результат (1-20):"
        )
        await state.set_state(GameStates.waiting_monster_dice)

@dp.message(GameStates.waiting_defender_dice)
async def process_defender_dice(message: types.Message, state: FSMContext):
    # Эта функция вызывается КОГДА ЛЮБОЙ ИГРОК вводит число после начала PvP боя
    # Нужно определить: кто вводит — атакующий или защитник?
    
    try:
        dice = int(message.text)
        if dice < 1 or dice > 20:
            raise ValueError
    except:
        await message.answer("❌ Введите число от 1 до 20!")
        return
    
    data = await state.get_data()
    
    # Определяем роль текущего игрока
    current_player_id = message.from_user.id
    attacker_id = data['attacker'][0]
    defender_id = data['defender'][0]
    
    if current_player_id == attacker_id:
        # Атакующий пытается ввести второй бросок — игнорируем
        await message.answer("⏳ Ожидайте броска от противника...")
        return
    
    if current_player_id != defender_id:
        # Неизвестный игрок
        await message.answer("❌ Вы не участвуете в этом бою!")
        return
    
    # Это защитник — обрабатываем его бросок
    attacker_dice = data['attacker_dice']
    attacker = data['attacker']
    defender = data['defender']
    round_num = data.get('round_num', 1)
    attacker_hp = data.get('attacker_hp', attacker[9])
    defender_hp = data.get('defender_hp', defender[9])
    
    # Расширенный расчёт боя с уворотами, блоками, критами
    battle_log = await calculate_detailed_battle(
        attacker, attacker_hp, attacker_dice,
        defender, defender_hp, dice,
        round_num
    )
    
    # Обновляем здоровье
    new_attacker_hp = battle_log['attacker_hp']
    new_defender_hp = battle_log['defender_hp']
    
    # Обновление в БД
    update_player(attacker[0], current_hp=new_attacker_hp)
    update_player(defender[0], current_hp=new_defender_hp)
    
    # Отправляем лог боя ОБОИМ игрокам
    log_text = battle_log['log']
    
    await message.answer(log_text)  # Защитнику
    try:
        await bot.send_message(chat_id=attacker[0], text=log_text)  # Атакующему
    except:
        pass
    
    # Проверка завершения боя
    if new_attacker_hp <= 0 and new_defender_hp <= 0:
        result = "⚔️ НИЧЬЯ! Оба пали в бою!"
        update_player(attacker[0], current_hp=attacker[8])  # Воскрешение
        update_player(defender[0], current_hp=defender[8])
        
    elif new_defender_hp <= 0:
        result = f"✅ {attacker[3]} победил {defender[3]}!"
        update_player(attacker[0], wins=attacker[13] + 1, current_hp=attacker[8])
        update_player(defender[0], losses=defender[14] + 1, current_hp=defender[8])
        
    elif new_attacker_hp <= 0:
        result = f"✅ {defender[3]} победил {attacker[3]}!"
        update_player(defender[0], wins=defender[13] + 1, current_hp=defender[8])
        update_player(attacker[0], losses=attacker[14] + 1, current_hp=attacker[8])
        
    else:
        # Продолжение боя — запрашиваем новые броски
        await state.update_data(
            attacker_hp=new_attacker_hp,
            defender_hp=new_defender_hp,
            round_num=round_num + 1
        )
        
        # Запрос нового броска у атакующего
        try:
            await bot.send_message(
                chat_id=attacker[0],
                text=f"🎲 РАУНД {round_num + 1}\n"
                     f"Ваше здоровье: {new_attacker_hp}/{attacker[8]} HP\n"
                     f"Здоровье {defender[3]}: {new_defender_hp}/{defender[8]} HP\n\n"
                     f"Киньте кубик d20 и введите результат (1-20):"
            )
        except:
            pass
        
        await message.answer(
            f"🎲 РАУНД {round_num + 1}\n"
            f"Ваше здоровье: {new_defender_hp}/{defender[8]} HP\n"
            f"Здоровье {attacker[3]}: {new_attacker_hp}/{attacker[8]} HP\n\n"
            f"Ожидайте броска от {attacker[3]}..."
        )
        return  # Не завершаем бой
    
    # Завершение боя
    await state.clear()
    await message.answer(f"{result}\n\nВыберите действие:", reply_markup=get_main_keyboard())
    try:
        await bot.send_message(chat_id=attacker[0], text=f"{result}\n\nВыберите действие:", reply_markup=get_main_keyboard())
    except:
        pass

async def calculate_detailed_battle(attacker, attacker_hp, attacker_dice, defender, defender_hp, defender_dice, round_num):
    """Расширенный расчёт боя с уворотами, блоками, критами"""
    log_lines = [f"🎲 РАУНД {round_num}"]
    log_lines.append("=" * 40)
    
    # ===== АТАКА АТАКУЮЩЕГО =====
    # Шанс уворота защитника
    dodge_chance = max(0, min(70, (defender[12] - attacker[12]) * 2))  # Разница в ловкости × 2%
    dodge_roll = random.randint(1, 100)
    did_dodge = dodge_roll <= dodge_chance
    
    if did_dodge:
        log_lines.append(f"💨 {defender[3]} уворачивается от атаки {attacker[3]}! (Уворот: {dodge_roll} ≤ {dodge_chance}%)")
        attacker_dmg = 0
    else:
        # Шанс блока
        block_chance = max(0, min(50, defender[11] * 0.8))  # Броня × 0.8%
        block_roll = random.randint(1, 100)
        did_block = block_roll <= block_chance
        
        # Базовый урон
        base_dmg = max(1, attacker[10] - defender[11] * 0.6)
        agility_mod = (attacker[12] - defender[12]) * 0.4
        dice_mod = (attacker_dice - 10) * 1.8
        
        # Критический удар (бросок 18+)
        is_crit = attacker_dice >= 18
        crit_mult = 1.8 if is_crit else 1.0
        
        attacker_dmg = max(1, round((base_dmg + agility_mod + dice_mod) * crit_mult))
        
        if did_block:
            blocked = round(attacker_dmg * 0.6)  # Блокирует 60% урона
            attacker_dmg -= blocked
            log_lines.append(
                f"🛡️ {defender[3]} блокирует атаку! (Блок: {block_roll} ≤ {block_chance}%)\n"
                f"   Урон снижен на {blocked} ({attacker_dmg} получено)"
            )
        elif is_crit:
            log_lines.append(
                f"💥 КРИТИЧЕСКИЙ УДАР {attacker[3]}! (бросок {attacker_dice})\n"
                f"   Урон ×1.8 = {attacker_dmg}"
            )
        else:
            log_lines.append(
                f"⚔️ {attacker[3]} атакует {defender[3]}:\n"
                f"   Бросок: {attacker_dice} | Урон: {attacker_dmg}"
            )
    
    # Применение урона
    new_defender_hp = max(0, defender_hp - attacker_dmg)
    if attacker_dmg > 0:
        log_lines.append(f"❤️ {defender[3]} получает {attacker_dmg} урона → {new_defender_hp} HP")
    log_lines.append("-" * 40)
    
    # ===== АТАКА ЗАЩИТНИКА =====
    # Шанс уворота атакующего
    dodge_chance = max(0, min(70, (attacker[12] - defender[12]) * 2))
    dodge_roll = random.randint(1, 100)
    did_dodge = dodge_roll <= dodge_chance
    
    if did_dodge:
        log_lines.append(f"💨 {attacker[3]} уворачивается от атаки {defender[3]}! (Уворот: {dodge_roll} ≤ {dodge_chance}%)")
        defender_dmg = 0
    else:
        # Шанс блока
        block_chance = max(0, min(50, attacker[11] * 0.8))
        block_roll = random.randint(1, 100)
        did_block = block_roll <= block_chance
        
        # Базовый урон
        base_dmg = max(1, defender[10] - attacker[11] * 0.6)
        agility_mod = (defender[12] - attacker[12]) * 0.4
        dice_mod = (defender_dice - 10) * 1.8
        
        # Критический удар
        is_crit = defender_dice >= 18
        crit_mult = 1.8 if is_crit else 1.0
        
        defender_dmg = max(1, round((base_dmg + agility_mod + dice_mod) * crit_mult))
        
        if did_block:
            blocked = round(defender_dmg * 0.6)
            defender_dmg -= blocked
            log_lines.append(
                f"🛡️ {attacker[3]} блокирует атаку! (Блок: {block_roll} ≤ {block_chance}%)\n"
                f"   Урон снижен на {blocked} ({defender_dmg} получено)"
            )
        elif is_crit:
            log_lines.append(
                f"💥 КРИТИЧЕСКИЙ УДАР {defender[3]}! (бросок {defender_dice})\n"
                f"   Урон ×1.8 = {defender_dmg}"
            )
        else:
            log_lines.append(
                f"⚔️ {defender[3]} атакует {attacker[3]}:\n"
                f"   Бросок: {defender_dice} | Урон: {defender_dmg}"
            )
    
    # Применение урона
    new_attacker_hp = max(0, attacker_hp - defender_dmg)
    if defender_dmg > 0:
        log_lines.append(f"❤️ {attacker[3]} получает {defender_dmg} урона → {new_attacker_hp} HP")
    log_lines.append("=" * 40)
    
    # Итог раунда
    log_lines.append(f"📊 ИТОГ РАУНДА {round_num}:")
    log_lines.append(f"   {attacker[3]}: {new_attacker_hp}/{attacker[8]} HP")
    log_lines.append(f"   {defender[3]}: {new_defender_hp}/{defender[8]} HP")
    
    return {
        'log': "\n".join(log_lines),
        'attacker_hp': new_attacker_hp,
        'defender_hp': new_defender_hp,
        'attacker_dmg': attacker_dmg,
        'defender_dmg': defender_dmg
    }

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
    round_num = data.get('round_num', 1)
    attacker_hp = data.get('attacker_hp', attacker[9])
    monster_hp = data.get('monster_hp', monster[4])
    
    # Расширенный расчёт боя с монстром
    battle_log = await calculate_detailed_monster_battle(
        attacker, attacker_hp, attacker_dice,
        monster, monster_hp, dice,
        round_num
    )
    
    new_attacker_hp = battle_log['attacker_hp']
    new_monster_hp = battle_log['monster_hp']
    
    # Обновление героя в БД
    update_player(attacker[0], current_hp=new_attacker_hp)
    
    # Лог боя
    await message.answer(battle_log['log'])
    
    # Проверка завершения
    if new_monster_hp <= 0:
        # Победа над монстром
        exp_gain = monster[8]
        new_exp = attacker[6] + exp_gain
        exp_for_next = attacker[5] * 100
        
        if new_exp >= exp_for_next:
            new_lvl = attacker[5] + 1
            await message.answer(
                f"✅ {attacker[3]} победил {monster[2]}!\n"
                f"✨ Получено {exp_gain} опыта!\n"
                f"{'='*40}\n"
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
        
        await state.clear()
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
            f"Здоровье {monster[2]}: {new_monster_hp}/{monster[4]} HP\n\n"
            f"Киньте кубик d20 для себя (1-20):"
        )
        await state.set_state(GameStates.waiting_attacker_dice)

async def calculate_detailed_monster_battle(attacker, attacker_hp, attacker_dice, monster, monster_hp, monster_dice, round_num):
    """Расширенный расчёт боя с монстром"""
    log_lines = [f"🎲 РАУНД {round_num}"]
    log_lines.append("=" * 40)
    
    # ===== АТАКА ГЕРОЯ =====
    # Монстры не уворачиваются в PvE для упрощения
    base_dmg = max(1, attacker[10] - monster[6] * 0.6)
    agility_mod = (attacker[12] - monster[7]) * 0.4
    dice_mod = (attacker_dice - 10) * 1.8
    
    is_crit = attacker_dice >= 18
    crit_mult = 1.8 if is_crit else 1.0
    
    attacker_dmg = max(1, round((base_dmg + agility_mod + dice_mod) * crit_mult))
    
    if is_crit:
        log_lines.append(
            f"💥 КРИТИЧЕСКИЙ УДАР {attacker[3]}! (бросок {attacker_dice})\n"
            f"   Урон ×1.8 = {attacker_dmg}"
        )
    else:
        log_lines.append(
            f"⚔️ {attacker[3]} атакует {monster[2]}:\n"
            f"   Бросок: {attacker_dice} | Урон: {attacker_dmg}"
        )
    
    new_monster_hp = max(0, monster_hp - attacker_dmg)
    log_lines.append(f"❤️ {monster[2]} получает {attacker_dmg} урона → {new_monster_hp} HP")
    log_lines.append("-" * 40)
    
    # ===== АТАКА МОНСТРА =====
    base_dmg = max(1, monster[5] - attacker[11] * 0.6)
    agility_mod = (monster[7] - attacker[12]) * 0.4
    dice_mod = (monster_dice - 10) * 1.8
    
    is_crit = monster_dice >= 18
    crit_mult = 1.8 if is_crit else 1.0
    
    monster_dmg = max(1, round((base_dmg + agility_mod + dice_mod) * crit_mult))
    
    if is_crit:
        log_lines.append(
            f"👹 {monster[2]} наносит критический удар! (бросок {monster_dice})\n"
            f"   Урон ×1.8 = {monster_dmg}"
        )
    else:
        log_lines.append(
            f"👹 {monster[2]} атакует {attacker[3]}:\n"
            f"   Бросок: {monster_dice} | Урон: {monster_dmg}"
        )
    
    new_attacker_hp = max(0, attacker_hp - monster_dmg)
    log_lines.append(f"❤️ {attacker[3]} получает {monster_dmg} урона → {new_attacker_hp} HP")
    log_lines.append("=" * 40)
    
    log_lines.append(f"📊 ИТОГ РАУНДА {round_num}:")
    log_lines.append(f"   {attacker[3]}: {new_attacker_hp}/{attacker[8]} HP")
    log_lines.append(f"   {monster[2]}: {new_monster_hp}/{monster[4]} HP")
    
    return {
        'log': "\n".join(log_lines),
        'attacker_hp': new_attacker_hp,
        'monster_hp': new_monster_hp,
        'attacker_dmg': attacker_dmg,
        'monster_dmg': monster_dmg
    }

# Команда для принятия вызова в PvP
@dp.message(Command("battle"))
async def accept_battle(message: types.Message, state: FSMContext):
    # Проверяем, есть ли активный вызов для этого игрока
    # (В упрощённой версии просто проверяем состояние)
    current_state = await state.get_state()
    if current_state and "waiting_defender_dice" in current_state:
        await message.answer(
            "✅ Вы вступили в бой!\n"
            "Киньте кубик d20 и введите результат (1-20):"
        )
    else:
        await message.answer("❌ Нет активных вызовов. Дождитесь, пока кто-то вызовет вас на бой.")
