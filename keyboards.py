from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from characters import CHARACTERS

def get_characters_keyboard(current_id: str = "") -> InlineKeyboardMarkup:
    """Returns an inline keyboard with all roleplay characters."""
    buttons = []
    
    # 2 buttons per row
    row = []
    for char_id, char in CHARACTERS.items():
        is_current = (char_id == current_id)
        prefix = "✅ " if is_current else ""
        text = f"{prefix}{char.emoji} {char.name}"
        row.append(InlineKeyboardButton(text=text, callback_data=f"select_char_{char_id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    # Custom character button
    custom_prefix = "✅ " if current_id == "custom" else ""
    buttons.append([
        InlineKeyboardButton(
            text=f"{custom_prefix}✏️ Создать своего персонажа",
            callback_data="start_custom_char"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_control_keyboard(character_id: str) -> InlineKeyboardMarkup:
    """Returns quick control buttons for the current dialogue."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Сброс сюжета", callback_data="reset_dialog"),
            InlineKeyboardButton(text="🎭 Сменить персонажа", callback_data="open_characters"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ О персонаже", callback_data=f"info_char_{character_id}")
        ]
    ])

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button for FSM custom character creation."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_custom")]
    ])
