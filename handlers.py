import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction

from characters import CHARACTERS, get_character_prompt
from keyboards import get_characters_keyboard, get_control_keyboard, get_cancel_keyboard
from states import CustomCharacterState
import database as db
from gemini_service import generate_roleplay_reply
from config import MAX_HISTORY_TURNS

router = Router()
logger = logging.getLogger(__name__)

def split_message(text: str, max_length: int = 4000) -> list[str]:
    """Splits long messages into parts for Telegram."""
    if len(text) <= max_length:
        return [text]
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        split_idx = text.rfind("\n", 0, max_length)
        if split_idx == -1:
            split_idx = text.rfind(" ", 0, max_length)
        if split_idx == -1:
            split_idx = max_length
        parts.append(text[:split_idx].strip())
        text = text[split_idx:].strip()
    return parts

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user_state = await db.get_user_state(user_id)
    current_char_id = user_state["character_id"]
    
    welcome_text = (
        "✨ **Добро пожаловать в мир ролевых игр!** ✨\n\n"
        "Здесь ты можешь общаться и играть в любые ролевые сценарии с персонажами на базе Google Gemini: "
        "романтика, аниме-вайбы, флирт, забота и откровенные сцены!\n\n"
        "💡 **Как играть:**\n"
        "• Пиши обычные слова как свою речь.\n"
        "• Описывай действия и мысли в звездочках: `*нежно обнял за плечи*` или `*улыбнулся в ответ*`.\n\n"
        "🎭 **Выбери персонажа, с кем хочешь начать:**"
    )
    await message.answer(
        welcome_text,
        reply_markup=get_characters_keyboard(current_char_id),
        parse_mode="Markdown"
    )

@router.message(Command("characters", "char"))
async def cmd_characters(message: Message):
    user_id = message.from_user.id
    user_state = await db.get_user_state(user_id)
    await message.answer(
        "🎭 **Выбери персонажа для ролевой игры:**",
        reply_markup=get_characters_keyboard(user_state["character_id"]),
        parse_mode="Markdown"
    )

@router.message(Command("reset"))
async def cmd_reset(message: Message):
    user_id = message.from_user.id
    user_state = await db.get_user_state(user_id)
    char_id = user_state["character_id"]
    
    await db.clear_character_history(user_id, char_id)
    
    if char_id in CHARACTERS:
        char = CHARACTERS[char_id]
        await message.answer(
            f"🔄 **Сюжет сброшен! Начинаем заново.**\n\n{char.greeting}",
            reply_markup=get_control_keyboard(char_id)
        )
    else:
        custom_name = user_state["custom_name"] or "Персонаж"
        await message.answer(
            f"🔄 **Сюжет сброшен!** {custom_name} готов(а) к новой игре.\nНапиши первое сообщение!",
            reply_markup=get_control_keyboard("custom")
        )

@router.message(Command("custom"))
async def cmd_custom(message: Message, state: FSMContext):
    await state.set_state(CustomCharacterState.waiting_for_name)
    await message.answer(
        "✏️ **Создание своего персонажа**\n\n"
        "Напиши **имя** своего персонажа (например: *Ху Тао*, *Курису*, *Эльфийка Лия*):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 **Гайд по ролевой игре:**\n\n"
        "🔹 **Действия в звездочках:**\n"
        "Описывай свои жесты, позы, прикосновения и окружающую обстановку в звездочках `*...*`.\n"
        "Пример: `*подошел ближе, тихо прошептав на ухо* Привет, малышка`\n\n"
        "🔹 **Команды:**\n"
        "/characters — сменить персонажа\n"
        "/reset — начать сюжет заново (стереть память диалога)\n"
        "/custom — создать своего уникального персонажа\n"
        "/help — показать эту подсказку\n\n"
        "🔹 **Свобода отыгрыша:**\n"
        "Бот поддерживает флирт, романтику, ласки и откровенные сцены!"
    )
    await message.answer(help_text, parse_mode="Markdown")

# Callback Handlers
@router.callback_query(F.data.startswith("select_char_"))
async def cb_select_character(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    char_id = callback.data.replace("select_char_", "")
    
    if char_id not in CHARACTERS:
        await callback.answer("Персонаж не найден!")
        return

    await db.set_user_character(user_id, char_id)
    char = CHARACTERS[char_id]
    
    await callback.answer(f"Выбрана: {char.name}")
    await callback.message.answer(
        f"🎭 Ты выбрал(а): **{char.name}**\n_{char.tagline}_\n\n{char.greeting}",
        reply_markup=get_control_keyboard(char_id),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "open_characters")
async def cb_open_characters(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_state = await db.get_user_state(user_id)
    await callback.answer()
    await callback.message.answer(
        "🎭 **Выбери персонажа для игры:**",
        reply_markup=get_characters_keyboard(user_state["character_id"]),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "reset_dialog")
async def cb_reset_dialog(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_state = await db.get_user_state(user_id)
    char_id = user_state["character_id"]
    
    await db.clear_character_history(user_id, char_id)
    await callback.answer("Сюжет очищен!")
    
    if char_id in CHARACTERS:
        char = CHARACTERS[char_id]
        await callback.message.answer(
            f"🔄 **Память очищена! Начинаем сцену заново.**\n\n{char.greeting}",
            reply_markup=get_control_keyboard(char_id)
        )
    else:
        name = user_state["custom_name"] or "Персонаж"
        await callback.message.answer(
            f"🔄 **Память очищена!** {name} готов(а) начать новую историю.",
            reply_markup=get_control_keyboard("custom")
        )

@router.callback_query(F.data.startswith("info_char_"))
async def cb_info_char(callback: CallbackQuery):
    char_id = callback.data.replace("info_char_", "")
    if char_id in CHARACTERS:
        char = CHARACTERS[char_id]
        info_text = (
            f"ℹ️ **{char.emoji} {char.name}**\n\n"
            f"📌 **Описание:**\n{char.description}\n\n"
            f"💬 **Вайб:** {char.tagline}"
        )
        await callback.answer()
        await callback.message.answer(info_text, parse_mode="Markdown")
    elif char_id == "custom":
        user_id = callback.from_user.id
        user_state = await db.get_user_state(user_id)
        name = user_state["custom_name"] or "Свой персонаж"
        prompt = user_state["custom_prompt"] or "Не задан"
        await callback.answer()
        await callback.message.answer(
            f"ℹ️ **{name}** (Пользовательский персонаж)\n\n📌 **Промпт:**\n{prompt}"
        )
    else:
        await callback.answer("Информация недоступна.")

@router.callback_query(F.data == "start_custom_char")
async def cb_start_custom(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CustomCharacterState.waiting_for_name)
    await callback.answer()
    await callback.message.answer(
        "✏️ **Создание своего персонажа**\n\n"
        "Напиши **имя** своего персонажа:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "cancel_custom")
async def cb_cancel_custom(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Создание отменено.")
    await callback.message.answer("❌ Создание персонажа отменено.")

# FSM States
@router.message(CustomCharacterState.waiting_for_name)
async def state_custom_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Пожалуйста, введи корректное имя:")
        return
    await state.update_data(custom_name=name)
    await state.set_state(CustomCharacterState.waiting_for_prompt)
    await message.answer(
        f"Отлично! Имя: **{name}**.\n\n"
        "Теперь опиши **характер, внешность, стиль речи и отношение к тебе**.\n"
        "Например: _«Миниатюрная девушка с длинными хвостиками, озорная хозяйка похоронного бюро, любит пугать и дразнить...»_:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

@router.message(CustomCharacterState.waiting_for_prompt)
async def state_custom_prompt(message: Message, state: FSMContext):
    prompt = message.text.strip()
    data = await state.get_data()
    name = data.get("custom_name", "Свой персонаж")
    await state.clear()
    
    user_id = message.from_user.id
    await db.set_custom_character(user_id, name, prompt)
    # Also clean previous custom history to start fresh
    await db.clear_character_history(user_id, "custom")
    
    await message.answer(
        f"🎉 **Персонаж «{name}» успешно создан и выбран!**\n\n"
        f"Напиши первое сообщение или действие в звездочках `*...*`, чтобы начать!",
        reply_markup=get_control_keyboard("custom"),
        parse_mode="Markdown"
    )

# Regular Roleplay Message Handler
@router.message(F.text)
async def handle_roleplay_message(message: Message):
    user_id = message.from_user.id
    user_text = message.text.strip()
    
    if not user_text:
        return
        
    user_state = await db.get_user_state(user_id)
    char_id = user_state["character_id"]
    custom_name = user_state.get("custom_name")
    custom_prompt = user_state.get("custom_prompt")
    
    # Send typing status
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    # Retrieve system prompt & history
    sys_prompt = get_character_prompt(char_id, custom_name, custom_prompt)
    history = await db.get_history(user_id, char_id, limit=MAX_HISTORY_TURNS)
    
    # Generate reply
    reply_text = await generate_roleplay_reply(
        system_instruction=sys_prompt,
        history=history,
        user_message=user_text
    )
    
    # If API call completely failed, DO NOT poison history
    if reply_text is None:
        await message.answer(
            "*Слегка нахмурилась и развела ручками*\n\n"
            "«Ой... сервера Google Gemini сейчас перегружены запросами! Пожалуйста, напиши мне ещё раз через пару секунд!»"
        )
        return
    
    # Save to history ONLY on success
    await db.add_history_message(user_id, char_id, "user", user_text)
    await db.add_history_message(user_id, char_id, "model", reply_text)
    
    # Send reply (split if long)
    parts = split_message(reply_text)
    for part in parts:
        await message.answer(part)
