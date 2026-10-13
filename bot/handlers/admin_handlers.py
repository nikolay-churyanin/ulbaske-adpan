import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageOriginUser, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class AdminHandlers:
    def __init__(self, bot_instance, admin_store):
        self.bot = bot_instance
        self.admins = admin_store

    def _keyboard(self, include_remove=True):
        rows = [[InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add")]]
        removable = [item for item in self.admins.list_admins() if item["source"] == "file"]
        if include_remove and removable:
            rows.append([InlineKeyboardButton("➖ Удалить админа", callback_data="admin_remove_menu")])
        rows.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        return InlineKeyboardMarkup(rows)

    def _list_text(self, current_id=None):
        lines = ["👥 Админы бота\n"]
        items = self.admins.list_admins()
        if not items:
            lines.append("Список пуст. Пропишите ADMIN_IDS в .env")
        else:
            for item in items:
                mark = " · .env" if item["source"] == "env" else ""
                you = " ← вы" if current_id and item["id"] == current_id else ""
                lines.append(f"• {item['name']} ({item['id']}){mark}{you}")
        lines.append(
            "\nЧтобы добавить человека: нажмите «Добавить» и перешлите любое его "
            "сообщение боту или пришлите числовой Telegram ID."
        )
        return "\n".join(lines)

    async def show_menu(self, query, context):
        context.user_data.pop("waiting_for_admin_id", None)
        await query.edit_message_text(
            self._list_text(query.from_user.id),
            reply_markup=self._keyboard(),
        )

    async def request_add(self, query, context):
        context.user_data["waiting_for_admin_id"] = True
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admins_menu")]]
        await query.edit_message_text(
            "Перешлите сюда сообщение нового админа или отправьте его Telegram ID числом.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def show_remove_menu(self, query, context):
        removable = [item for item in self.admins.list_admins() if item["source"] == "file"]
        if not removable:
            await query.edit_message_text(
                "Удалять некого: все текущие админы заданы в .env.",
                reply_markup=self._keyboard(include_remove=False),
            )
            return
        keyboard = [
            [InlineKeyboardButton(
                f"{item['name']} ({item['id']})",
                callback_data=f"admin_remove_{item['id']}",
            )]
            for item in removable
        ]
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admins_menu")])
        await query.edit_message_text(
            "Кого убрать из админов?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def remove_admin(self, query, context, admin_id):
        ok, reason = self.admins.remove_admin(admin_id)
        if ok:
            text = f"✅ Админ {admin_id} удалён."
        elif reason == "env":
            text = "❌ Этого админа нельзя убрать из бота: id задан в .env."
        elif reason == "last":
            text = "❌ Нельзя удалить последнего админа."
        else:
            text = "❌ Такого админа нет в списке."
        context.user_data.pop("waiting_for_admin_id", None)
        listed = self._list_text(query.from_user.id)
        await query.edit_message_text(
            f"{text}\n\n{listed}",
            reply_markup=self._keyboard(),
        )

    def _extract_candidate(self, update: Update):
        message = update.message
        if not message:
            return None, None

        origin = getattr(message, "forward_origin", None)
        if isinstance(origin, MessageOriginUser) and origin.sender_user:
            user = origin.sender_user
            return user.id, user.username or user.full_name

        if message.contact and message.contact.user_id:
            contact = message.contact
            name = " ".join(part for part in [contact.first_name, contact.last_name] if part)
            return contact.user_id, name or str(contact.user_id)

        text = (message.text or "").strip()
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text), str(int(text))
        return None, None

    async def handle_add_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin_id, name = self._extract_candidate(update)
        if admin_id is None:
            await update.message.reply_text(
                "Не понял. Перешлите сообщение человека или пришлите числовой ID."
            )
            return

        ok, reason = self.admins.add_admin(
            admin_id,
            name=name,
            added_by=update.effective_user.id if update.effective_user else None,
        )
        context.user_data.pop("waiting_for_admin_id", None)
        if ok:
            text = f"✅ Добавлен админ {name} ({admin_id})."
        elif reason == "already":
            text = f"Этот id уже админ: {admin_id}."
        else:
            text = "❌ Не удалось добавить админа."
        await update.message.reply_text(text)
        await self.bot_show_menu_message(update, context)

    async def bot_show_menu_message(self, update, context):
        await update.message.reply_text(
            self._list_text(update.effective_user.id if update.effective_user else None),
            reply_markup=self._keyboard(),
        )
