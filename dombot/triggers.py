from datetime import datetime
import sqlite3 as db
import re
from telethon import events, Button
from telethon.errors.rpcerrorlist import MessageIdInvalidError
import vars as bot_vars
from functools import partial
from functions import command, command_with_args


triggers_dict = {}
data_for_callback = {}
TRIGGERS_FOLDER = "triggers_data"
db_conn = None


try:
    db_conn = db.connect(r"dombot/rss/databases/sqlite/triggers.db", isolation_level=None)
except Exception as e:
    error = e.args[1]
    bot_vars.bot.send_message(bot_vars.D0MiNiX, error)


tables = []
db_cursor = db_conn.cursor()
db_cursor.execute(f"SELECT name from sqlite_master WHERE type ='table' AND name NOT LIKE 'sqlite_%'")
for table in db_cursor:
    tables.append(int(table[0]))

for table in tables:
    db_cursor.execute(f"SELECT trigger_name FROM `{table}`;")
    triggers_dict[table] = []
    for data in db_cursor:
        triggers_dict[table].append(data[0])

db_cursor.close()


class DatabaseQuery:
	def __init__(self, table_name=None, values=None, trig_name=None):
		self.table_name = table_name
		self.values = values
		self.trig_name = trig_name
		self.mycursor = db_conn.cursor()

	def select_multiple(self, column=None, value=None):
		try:
			values = ", ".join(map(lambda x: f"{x}", self.values))
			query = f"SELECT {values} FROM `{self.table_name}`" + (
			    	f" WHERE {column}='{value}'" if column is not None else "")
			self.mycursor.execute(query)
			return self.mycursor
		except Exception as err:
			return err.args[0]

	def select_single(self):
		try:
			values = ", ".join(self.values)
			query = f"SELECT {values} FROM `{self.table_name}` WHERE trigger_name=?"
			trig_name = (self.trig_name,)
			self.mycursor.execute(query, trig_name)
			result = [k for k in self.mycursor]
			return result
		except Exception as err:
			return err.args[0]

	def insert(self):
		try:
			values = tuple(self.values)
			query = f"INSERT INTO `{self.table_name}` VALUES(?, ?, ?, ?, ?, ?, ?);"
			self.mycursor.execute(query, values)
			self.mycursor.close()
			return None
		except Exception as err:
			return err.args[0]

	def create_table(self):
		try:
			values = ", ".join(self.values)
			query = (f"CREATE TABLE IF NOT EXISTS `{self.table_name}` ({values})")
			self.mycursor.execute(query)
			self.mycursor.close()
			return None
		except Exception as err:
			return err.args[0]

	def show_tables(self):
		try:
			tables_list = []
			self.mycursor.execute("SELECT name from sqlite_master WHERE type ='table' "
									"AND name NOT LIKE 'sqlite_%'")
			for table in self.mycursor:
				tables_list.append(table[0])
			return tables_list
		except Exception as err:
			return err.args[0]

	def delete(self):
		try:
			values = tuple(self.values)
			query = f"DELETE FROM `{self.table_name}` WHERE trigger_name=?;"
			self.mycursor.execute(query, values)
			if self.mycursor.rowcount == 0:
				return "No data"
		except Exception as err:
			return err.args[0]


class Triggers:
	def __init__(self, event_data, reply_data=None):
		self.is_fwd = 0
		self.chat_id = event_data.chat_id
		if event_data.sender.username is not None:
			self.sender_info = event_data.sender.username
		else:
			self.sender_info = str(event_data.sender.id)
		self.current_utc = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")
		self.trig_name = event_data.raw_text.split(" ", 1)[1]
		self.trig_name = self.trig_name.lower()
		if hasattr(reply_data, "id"):
			self.msg_id = reply_data.id
		else:
			self.msg_id = 0
		self.file_id = ""
		self.response = ""

		if hasattr(reply_data, "media") and hasattr(reply_data.media, "emoticon"):
			self.response = reply_data.media.emoticon
			if reply_data.forward:
				self.is_fwd = 1
		elif hasattr(reply_data, "media") and hasattr(reply_data.media, "webpage"):
			self.response = reply_data.text
			if reply_data.forward:
				self.is_fwd = 1
		elif (hasattr(reply_data, "game") and reply_data.game) or \
			 (hasattr(reply_data, "geo") and reply_data.geo) or \
			 (hasattr(reply_data, "poll") and reply_data.poll) or \
			 (hasattr(reply_data, "contact") and reply_data.contact):
			self.response = ""
		elif reply_data is not None:
			if reply_data.forward:
				self.is_fwd = 1
			if reply_data.media:
				self.file_id = reply_data.file.id
			else:
				self.response = reply_data.text

	def check_table_existence(self, table_name):
		error = None
		fields = ["trigger_name VARCHAR(64) PRIMARY KEY", "file_id VARCHAR(256)", 
					"trigger_text VARCHAR(4096)", "msg_id INT", "added_by VARCHAR(128)", "added_on VARCHAR(32)",
					"is_fwd BOOLEAN"]
		db_query = DatabaseQuery(table_name=self.chat_id, values=fields)
		tables_list = db_query.show_tables()

		if isinstance(tables_list, str):
			error = tables_list
			return error

		if table_name not in tables_list:
			error = db_query.create_table()

		return error

	def save(self, dict_to_save):
		error = None
		error = self.check_table_existence(str(self.chat_id))

		if isinstance(error, str):
			return error

		db_query = DatabaseQuery(table_name=self.chat_id, values=[self.trig_name, self.file_id, \
									 							  self.response, self.msg_id, \
																  self.sender_info, \
																  self.current_utc, self.is_fwd])
		error = db_query.insert()

		if error:
			return error

		if self.chat_id not in dict_to_save.keys():
			dict_to_save[self.chat_id] = []

		dict_to_save[self.chat_id].append(self.trig_name)
		return error

	def remove(self, dict_to_save):
		db_query = DatabaseQuery(table_name=self.chat_id, values=[self.trig_name])
		error = db_query.delete()

		if error:
			return error

		dict_to_save[self.chat_id].remove(self.trig_name)
		return error

	def replace(self, dict_to_save):
		error = None
		error = self.remove(dict_to_save)

		if error:
			return error

		error = self.save(dict_to_save)
		return error


@bot_vars.bot.on(events.CallbackQuery)
async def trigger_change_confirmation(event):

	data = event.data.decode("UTF-8")

	if not re.match(r"yes_tr|no_tr", data):
		return

	message = await event.get_message()
	time_format = "%m-%d-%y %H:%M:%S"
	current_time = datetime.strptime(datetime.utcnow().strftime(time_format), time_format)
	event_data = data_for_callback[event.chat_id][event.message_id][0]
	event_time = event_data.date.strptime(event_data.date.strftime(time_format), time_format)

	if (current_time - event_time).total_seconds() > 60:
		await event.edit("Sorry, too late, response required within 1 minute.")
		# Remove the chat id key if there are no more replacements awaiting for that chat
		if not data_for_callback[event.chat_id]:
			del data_for_callback[event.chat_id]
		raise events.StopPropagation()

	text = re.findall(r"replace the (.+?) trigger", message.text)[0]

	if data == "yes_tr":
		event_data = data_for_callback[event.chat_id][event.message_id][0]
		reply_data = data_for_callback[event.chat_id][event.message_id][1]
		error = Triggers(event_data, reply_data).replace(triggers_dict)

		if error:
			await event.edit(f"Error in database, please try again. {error}")
		else:
			await event.edit(f"Replaced the {text} trigger successfully.")

		del data_for_callback[event.chat_id][event.message_id]
		# Remove the chat id key if there are no more replacements awaiting for that chat
		if not data_for_callback[event.chat_id]:
			del data_for_callback[event.chat_id]
		raise events.StopPropagation
	else:
		# If the replaced trigger is of text type, the file gets created first, 
		# so need to delete here
		await event.edit(f"Alright, no change then. Keeping {text} as it is.")
		raise events.StopPropagation


@events.register(events.NewMessage())
async def triggers(event):

	cmd = partial(command, event.raw_text)
	cmd_with_args = partial(command_with_args, event.raw_text)

	if cmd_with_args("set_trigger") or cmd_with_args("set_tr"):

		if not event.is_reply:
			await event.reply("Please reply to a message that you want to set trigger as.")
			raise events.StopPropagation

		reply = await event.get_reply_message()
		trig_name = event.raw_text.split(" ", 1)

		if len(trig_name) <= 1:
			await event.reply(f"Duh!! Give some name. Correct usage: `/set_trigger <name>`.")
			raise events.StopPropagation
		elif len(trig_name[1]) > 64:
			await event.reply(f"Sorreh, can't accept trigger names with more than 64 characters for now.")
			raise events.StopPropagation
		elif trig_name[1].startswith("/"):
			await event.reply("No no no, bad idea to set a command as a trigger.")
			raise events.StopPropagation

		trigger_name = trig_name[1].lower()

		error = Triggers(event, reply).save(triggers_dict)

		if error and (error.startswith("UNIQUE") or "is not unique" in error):
			buttons_layout = [Button.inline("Yes!", b"yes_tr"), Button.inline("Nope", b"no_tr")]
			msg_id = await event.reply(f"Trigger already exists. Do you want to replace the"
										f" `{trigger_name}` trigger?", buttons=buttons_layout)
			if event.chat_id not in data_for_callback:
				data_for_callback[event.chat_id] = {}
			data_for_callback[event.chat_id][msg_id.id] = [event, reply]
			raise events.StopPropagation

		if error is None:
			await event.reply(f"Trigger `{trigger_name}` saved successfully.")
		else:
			await event.reply(f"Error in database. {error}")

		raise events.StopPropagation

	elif cmd_with_args("rm_trigger") or cmd_with_args("rm_tr"):
		trig_name = event.raw_text.split(" ", 1)

		if len(trig_name) <= 1:
			await event.reply(f"Duh!! Give some name. Correct usage: `/rm_trigger <name>`.")
			raise events.StopPropagation

		trigger_name = trig_name[1].lower()
		error = Triggers(event).remove(triggers_dict)

		if error == "No data":
			await event.reply(f"Trigger `{trigger_name}` doesn't exist.")
		elif error:
			await event.reply(f"Error in database. {error}")
		else:
			await event.reply(f"Trigger `{trigger_name}` removed successfully.")

		# Clean up the table
		if not triggers_dict[event.chat_id]:
			try:
				mycursor = db_conn.cursor()
				query = f"DROP TABLE IF EXISTS `{event.chat_id}`;"
				mycursor.execute(query)
				await event.respond("...and with that last one, goes away all the triggers.")
			except Exception as err:
				await event.reply(f"Error deleting `{event.chat_id}` table. {err.args[0]}")

		raise events.StopPropagation

	elif cmd("triggers_info") or cmd("tr_info"):
		response = ""
		db_query = DatabaseQuery(table_name=event.chat_id, values=["trigger_name", "added_by", \
																	"added_on"])
		error = db_query.select_multiple()
		triggers_data = None

		if isinstance(error, str) and error.startswith("no such table"):
			await event.reply("No triggers found in this chat. Setup one using `/set_trigger <name>` and"
								" remove using `/rm_trigger <name>`.")
			raise events.StopPropagation
		else:
			triggers_data = error

		response_list = []
		for count, data in enumerate(triggers_data, start=1):
			trigger_name = data[0]
			added_by = data[1]
			added_on = data[2]
			response = f"`{count}. " + f"{trigger_name} " + f"(@{added_by} - {added_on})`"
			response_list.append(response)

		if response_list:
			new_line = '\n'
			_lst = [response_list[i:i + 50] for i in range(0, len(response_list), 50)]
			for resp in _lst:
				await event.respond(new_line.join(resp))
		else:
			await event.respond(response)

		raise events.StopPropagation

	elif cmd("triggers"):
		response = ""
		db_query = DatabaseQuery(table_name=event.chat_id, values=["trigger_name"])
		error = db_query.select_multiple()
		triggers_data = None

		if isinstance(error, str) and error.startswith("no such table"):
			await event.reply("No triggers found in this chat. Setup one using `/set_trigger <name>` and"
								" remove using `/rm_trigger <name>`.")
			raise events.StopPropagation
		else:
			triggers_data = error

		response_list = []
		for count, data in enumerate(triggers_data, start=1):
			trigger_name = data[0]
			response = f"`{count}.` " + f"`{trigger_name}`"
			response_list.append(response)

		if response_list:
			new_line = '\n'
			_lst = [response_list[i:i + 50] for i in range(0, len(response_list), 50)]
			for resp in _lst:
				await event.respond(new_line.join(resp))
		else:
			await event.respond("No triggers found in this chat. Start creating using `/set_trigger` command.")

		raise events.StopPropagation

	elif event.chat_id in triggers_dict and event.raw_text.lower() in triggers_dict[event.chat_id]:
		db_query = DatabaseQuery(table_name=event.chat_id, values=["file_id", "trigger_text", "msg_id", "is_fwd"], \
									trig_name=event.raw_text.lower())
		response = db_query.select_single()

		if isinstance(response, str):
			await event.reply(f"Error sending the trigger. {response}")

		file_id = response[0][0]
		text = response[0][1]
		msg_id = response[0][2]
		is_fwd = response[0][3]

		try:
			if text != "":
				if is_fwd:
					await bot_vars.bot.forward_messages(event.chat_id, messages=msg_id, from_peer=event.chat_id)
				else:
					await event.respond(text)
			elif file_id != "":
				if is_fwd:
					await bot_vars.bot.forward_messages(event.chat_id, messages=msg_id, from_peer=event.chat_id)
				else:
					await event.respond(file=file_id)
			else:
				try:
					msg = await bot_vars.bot.get_messages(event.chat_id, ids=msg_id)
					if is_fwd:
						await bot_vars.bot.forward_messages(event.chat_id, messages=msg_id, from_peer=event.chat_id)
					else:
						await bot_vars.bot.send_message(event.chat_id, message=msg)
				except Exception as e:
					try:
						# game bots like @gamee causes above exception
						await bot_vars.bot.forward_messages(event.chat_id, messages=msg_id, from_peer=event.chat_id)
					except Exception as e:
						await event.reply(f"Error sending the trigger. {e.args[0]}")
		except MessageIdInvalidError:
			await event.reply(f"Message doesn't exists in this chat anymore, hence, can't be forwarded." + \
								f"Better, remove the trigger.")

		raise events.StopPropagation

MONKE_CHAT_ID = -721939051 # TODO: Change to real monke chat id
n = 0
import random

@events.register(events.NewMessage(chats=[MONKE_CHAT_ID]))
async def title_of_yr_stape(event):
	global n
	text = event.raw_text
	len_txt = len(text)

	if 10 < len_txt < 25 or not text.isascii():
		return

	n += 1

	if n < 500:
		return

	if random.random() < 0.002:
		await event.reply("TITLE OF YOUR SEXTAPE!")
		n = 0
		raise events.StopPropagation
