import logging
import os
import time
import reply_messages
import asyncio
import redis

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
	Application, 
	ApplicationBuilder, 
	ContextTypes, 
	CommandHandler, 
	MessageHandler, 
	ConversationHandler, 
	filters, 
	Defaults
)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

redis_client = redis.StrictRedis(host="redis-db", port="6379", db=0, decode_responses=True)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await context.bot.send_message(chat_id=update.effective_chat.id, text=reply_messages.help_message)

async def test_async_heavy_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await asyncio.sleep(10)
	await context.bot.send_message(chat_id=update.effective_chat.id, text="Are you spamming heavy async command?")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await context.bot.send_message(chat_id=update.effective_chat.id, text="I don't know thic command >.<")

TITLE, BODY = range(2)

async def new_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	await update.message.reply_text(
		"Type a title for your new note",
		reply_markup=ReplyKeyboardMarkup(
			[["/cancel"]], one_time_keyboard=True, input_field_placeholder="type your title here"
		),
	)

	return TITLE

async def new_note_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user = update.message.from_user

	if redis_client.hexists("user:" + str(user.id), update.message.text):
		await update.message.reply_text(
			"Note with this title already exists, choose new one or cancel and delete old note",
			reply_markup=ReplyKeyboardMarkup(
				[["/cancel"]], one_time_keyboard=True, input_field_placeholder="type your title here"
			),
		)
		return TITLE
	else:
		context.user_data["next_title"] = update.message.text
		await update.message.reply_text(
			"Type a body of your new note",
			reply_markup=ReplyKeyboardMarkup(
				[["/cancel"]], one_time_keyboard=True, input_field_placeholder="type body of note here"
			),
		)
		return BODY

async def new_note_body(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user = update.message.from_user
	logger.info("User: %s, Title: %s, Body: %s", user.first_name, context.user_data["next_title"], update.message.text)

	redis_client.hset("user:" + str(user.id), context.user_data["next_title"], update.message.text)

	await update.message.reply_text(
		"Your note was saved!", 
		reply_markup=ReplyKeyboardRemove()
	)

	return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user = update.message.from_user
	logger.info("User %s canceled the conversation.", user.first_name)
	await update.message.reply_text(
		"Okay :c", 
		reply_markup=ReplyKeyboardRemove()
	)

	return ConversationHandler.END

async def ls_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user = update.message.from_user
	titles = redis_client.hkeys("user:" + str(user.id))
	reply_text = "You have " + str(len(titles)) + " notes:\n" + "\n".join(['- ' + title for title in titles])
	await context.bot.send_message(chat_id=update.effective_chat.id, text=reply_text)

async def del_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	await update.message.reply_text(
		"Type a title of the note you want to delete",
		reply_markup=ReplyKeyboardMarkup(
			[["/cancel"]], one_time_keyboard=True, input_field_placeholder="type your title here"
		),
	)

	return TITLE

async def del_note_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user = update.message.from_user

	reply_text = ""
	if redis_client.hdel("user:" + str(user.id), update.message.text):
		reply_text = "Note successfuly deleted"
	else:
		reply_text = "No note was deleted"
	await context.bot.send_message(chat_id=update.effective_chat.id, text=reply_text)

	return ConversationHandler.END

async def show_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	await update.message.reply_text(
		"Type a title of the note you want to view",
		reply_markup=ReplyKeyboardMarkup(
			[["/cancel"]], one_time_keyboard=True, input_field_placeholder="type title of note here"
		),
	)

	return TITLE

async def show_note_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user = update.message.from_user

	if redis_client.hexists("user:" + str(user.id), update.message.text):
		reply_text = "Note " + update.message.text + " is:\n" + str(redis_client.hget("user:" + str(user.id), update.message.text))
		await context.bot.send_message(chat_id=update.effective_chat.id, text=reply_text)
		return ConversationHandler.END
	else:
		context.user_data["next_title"] = update.message.text
		await update.message.reply_text(
			"There is no such note, try again",
			reply_markup=ReplyKeyboardMarkup(
				[["/cancel"]], one_time_keyboard=True, input_field_placeholder="type title of note here"
			),
		)
		return TITLE

if __name__ == '__main__':
	token = os.environ['TOKEN']
	application = (
		ApplicationBuilder()
		.token(token)
		.build()
	)

	help_handler = CommandHandler(['start', 'help'], help, block=False)
	application.add_handler(help_handler)

	ls_notes_handler = CommandHandler("ls_notes", ls_notes, block=False)
	application.add_handler(ls_notes_handler)

	test_async_heavy_spam_handler = CommandHandler('async_heavy_spam', test_async_heavy_spam, block=False)
	application.add_handler(test_async_heavy_spam_handler)

	new_note_conv_handler = ConversationHandler(
		entry_points=[CommandHandler("new_note", new_note)],
		states={
			TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_note_title)],
			BODY: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_note_body)],
		},
		fallbacks=[CommandHandler("cancel", cancel)],
	)
	application.add_handler(new_note_conv_handler)

	del_note_conv_handler = ConversationHandler(
		entry_points=[CommandHandler("del_note", del_note)],
		states={
			TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, del_note_title)]
		},
		fallbacks=[CommandHandler("cancel", cancel)],
	)
	application.add_handler(del_note_conv_handler)

	show_note_conv_handler = ConversationHandler(
		entry_points=[CommandHandler("show_note", show_note)],
		states={
			TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_note_title)]
		},
		fallbacks=[CommandHandler("cancel", cancel)],
	)
	application.add_handler(show_note_conv_handler)


	unknown_handler = MessageHandler(filters.COMMAND, unknown)
	application.add_handler(unknown_handler)
	
	application.run_polling()
