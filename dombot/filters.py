from datetime import datetime
import sqlite3 as db
import re
from telethon import events, Button
from telethon.errors.rpcerrorlist import MessageIdInvalidError
import vars as bot_vars
from functools import partial
from functions import command, command_with_args


filters_dict = {}
data_for_callback = {}
db_conn = None


try:
    db_conn = db.connect(r"dombot/rss/databases/sqlite/filters.db", isolation_level=None)
except Exception as e:
    error = e.args[1]
    bot_vars.bot.send_message(bot_vars.D0MiNiX, error)


tables = []
db_cursor = db_conn.cursor()
db_cursor.execute(f"SELECT name from sqlite_master WHERE type ='table' AND name NOT LIKE 'sqlite_%'")
for table in db_cursor:
    tables.append(int(table[0]))

for table in tables:
    db_cursor.execute(f"SELECT filter_name FROM `{table}`;")
    filters_dict[table] = []
    for data in db_cursor:
        filters_dict[table].append(data[0])

db_cursor.close()


class DatabaseQuery:
	def __init__(self, table_name=None, values=None, filt_name=None):
		self.table_name = table_name
		self.values = values
		self.filt_name = filt_name
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
			query = f"SELECT {values} FROM `{self.table_name}` WHERE filter_name=?"
			filt_name = (self.filt_name,)
			self.mycursor.execute(query, filt_name)
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
			query = f"DELETE FROM `{self.table_name}` WHERE filter_name=?;"
			self.mycursor.execute(query, values)
			if self.mycursor.rowcount == 0:
				return "No data"
		except Exception as err:
			return err.args[0]


class Filters:
	def __init__(self, event_data, reply_data=None):
		self.is_fwd = 0
		self.chat_id = event_data.chat_id
		if event_data.sender.username is not None:
			self.sender_info = event_data.sender.username
		else:
			self.sender_info = str(event_data.sender.id)
		self.current_utc = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")
		self.filt_name = event_data.raw_text.split(" ", 1)[1]
		self.filt_name = self.filt_name.lower()
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
		fields = ["filter_name VARCHAR(64) PRIMARY KEY", "file_id VARCHAR(256)", 
					"filter_text VARCHAR(4096)", "msg_id INT", "added_by VARCHAR(128)", "added_on VARCHAR(32)",
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

		db_query = DatabaseQuery(table_name=self.chat_id, values=[self.filt_name, self.file_id, \
									 							  self.response, self.msg_id, \
																  self.sender_info, \
																  self.current_utc, self.is_fwd])
		error = db_query.insert()

		if error:
			return error

		if self.chat_id not in dict_to_save.keys():
			dict_to_save[self.chat_id] = []

		dict_to_save[self.chat_id].append(self.filt_name)
		return error

	def remove(self, dict_to_save):
		db_query = DatabaseQuery(table_name=self.chat_id, values=[self.filt_name])
		error = db_query.delete()

		if error:
			return error

		dict_to_save[self.chat_id].remove(self.filt_name)
		return error

	def replace(self, dict_to_save):
		error = None
		error = self.remove(dict_to_save)

		if error:
			return error

		error = self.save(dict_to_save)
		return error


@bot_vars.bot.on(events.CallbackQuery)
async def filter_change_confirmation(event):

	data = event.data.decode("UTF-8")

	if not re.match(r"yes_fr|no_fr", data):
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

	text = re.findall(r"replace the (.+?) filter", message.text)[0]

	if data == "yes_fr":
		event_data = data_for_callback[event.chat_id][event.message_id][0]
		reply_data = data_for_callback[event.chat_id][event.message_id][1]
		error = Filters(event_data, reply_data).replace(filters_dict)

		if error:
			await event.edit(f"Error in database, please try again. {error}")
		else:
			await event.edit(f"Replaced the {text} filter successfully.")

		del data_for_callback[event.chat_id][event.message_id]
		# Remove the chat id key if there are no more replacements awaiting for that chat
		if not data_for_callback[event.chat_id]:
			del data_for_callback[event.chat_id]
		raise events.StopPropagation
	else:
		# If the replaced filter is of text type, the file gets created first, 
		# so need to delete here
		await event.edit(f"Alright, no change then. Keeping {text} as it is.")
		raise events.StopPropagation


@events.register(events.NewMessage())
async def filters(event):

	cmd = partial(command, event.raw_text)
	cmd_with_args = partial(command_with_args, event.raw_text)

	if cmd_with_args("set_filter") or cmd_with_args("set_fr"):

		if not event.is_reply:
			await event.reply("Please reply to a message that you want to set filter as.")
			raise events.StopPropagation

		reply = await event.get_reply_message()
		filt_name = event.raw_text.split(" ", 1)

		if len(filt_name) <= 1:
			await event.reply(f"Duh!! Give some name. Correct usage: `/set_filter <name>`.")
			raise events.StopPropagation
		elif len(filt_name[1]) > 64:
			await event.reply(f"Sorreh, can't accept filter names with more than 64 characters for now.")
			raise events.StopPropagation
		elif filt_name[1].startswith("/"):
			await event.reply("No no no, bad idea to set a command as a filter.")
			raise events.StopPropagation

		filter_name = filt_name[1].lower()

		error = Filters(event, reply).save(filters_dict)

		if error and (error.startswith("UNIQUE") or "is not unique" in error):
			buttons_layout = [Button.inline("Yes!", b"yes_fr"), Button.inline("Nope", b"no_fr")]
			msg_id = await event.reply(f"Filter already exists. Do you want to replace the"
										f" `{filter_name}` filter?", buttons=buttons_layout)
			if event.chat_id not in data_for_callback:
				data_for_callback[event.chat_id] = {}
			data_for_callback[event.chat_id][msg_id.id] = [event, reply]
			raise events.StopPropagation

		if error is None:
			await event.reply(f"Filter `{filter_name}` saved successfully.")
		else:
			await event.reply(f"Error in database. {error}")

		raise events.StopPropagation

	elif cmd_with_args("rm_filter") or cmd_with_args("rm_fr"):
		filt_name = event.raw_text.split(" ", 1)

		if len(filt_name) <= 1:
			await event.reply(f"Duh!! Give some name. Correct usage: `/rm_filter <name>`.")
			raise events.StopPropagation

		filter_name = filt_name[1].lower()
		error = Filters(event).remove(filters_dict)

		if error == "No data":
			await event.reply(f"Filter `{filter_name}` doesn't exist.")
		elif error:
			await event.reply(f"Error in database. {error}")
		else:
			await event.reply(f"Filter `{filter_name}` removed successfully.")

		# Clean up the table
		if not filters_dict[event.chat_id]:
			try:
				mycursor = db_conn.cursor()
				query = f"DROP TABLE IF EXISTS `{event.chat_id}`;"
				mycursor.execute(query)
				await event.respond("...and with that last one, goes away all the filters.")
			except Exception as err:
				await event.reply(f"Error deleting `{event.chat_id}` table. {err.args[0]}")

		raise events.StopPropagation

	elif cmd("filters_info") or cmd("fr_info"):
		response = ""
		db_query = DatabaseQuery(table_name=event.chat_id, values=["filter_name", "added_by", \
																	"added_on"])
		error = db_query.select_multiple()
		triggers_data = None

		if isinstance(error, str) and error.startswith("no such table"):
			await event.reply("No filters found in this chat. Setup one using `/set_filter <name>` and"
								" remove using `/rm_filter <name>`.")
			raise events.StopPropagation
		else:
			triggers_data = error

		response_list = []
		for count, data in enumerate(triggers_data, start=1):
			filter_name = data[0]
			added_by = data[1]
			added_on = data[2]
			response = f"`{count}. " + f"{filter_name} " + f"(@{added_by} - {added_on})`"
			response_list.append(response)

		if response_list:
			new_line = '\n'
			_lst = [response_list[i:i + 50] for i in range(0, len(response_list), 50)]
			for resp in _lst:
				await event.respond(new_line.join(resp))
		else:
			await event.respond(response)

		raise events.StopPropagation

	elif cmd("filters"):
		response = ""
		db_query = DatabaseQuery(table_name=event.chat_id, values=["filter_name"])
		error = db_query.select_multiple()
		triggers_data = None

		if isinstance(error, str) and error.startswith("no such table"):
			await event.reply("No filters found in this chat. Setup one using `/set_filter <name>` and"
								" remove using `/rm_filter <name>`.")
			raise events.StopPropagation
		else:
			triggers_data = error

		response_list = []
		for count, data in enumerate(triggers_data, start=1):
			filter_name = data[0]
			response = f"`{count}.` " + f"`{filter_name}`"
			response_list.append(response)

		if response_list:
			new_line = '\n'
			_lst = [response_list[i:i + 50] for i in range(0, len(response_list), 50)]
			for resp in _lst:
				await event.respond(new_line.join(resp))
		else:
			await event.respond("No filters found in this chat. Start creating using `/set_filter` command.")

		raise events.StopPropagation

	elif event.chat_id in filters_dict:
		event_text = event.raw_text.lower()
		word = [x for x in event_text.split() if x in filters_dict[event.chat_id]]
		
		if not word:
			raise events.StopPropagation

		db_query = DatabaseQuery(table_name=event.chat_id, values=["file_id", "filter_text", "msg_id", "is_fwd"], \
									filt_name=word[0])
		response = db_query.select_single()

		if isinstance(response, str):
			await event.reply(f"Error sending the filter. {response}")

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
						await event.reply(f"Error sending the filter. {e.args[0]}")
		except MessageIdInvalidError:
			await event.reply(f"Message doesn't exists in this chat anymore, hence, can't be forwarded." + \
								f"Better, remove the filter.")

		raise events.StopPropagation
