import telebot
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import os
import pickle
import datetime
import youtube_dl

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

bot = telebot.TeleBot('TOKEN')

api_service_name = "youtube"
api_version = "v3"
client_secrets_file = "client_secret.json"
credentials_pickle_file = "credentials_pickle_file"
last_update_time = "last_update_time"
time_read_format = '%y-%m-%d %H:%M:%S'

# описание команд
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f'Я бот. Приятно познакомиться, {message.from_user.first_name}. Напиши /help, чтобы узнать больше информации')

@bot.message_handler(commands=['help'])
def send_info(message):
    bot.reply_to(message, f'Бот предназначен для получения аудиодорожки видео YouTube \n Используй команду /subscriptions, чтобы получить список аудио \n Напиши ему "воняешь" и поймешь, кто из вас двоих действительно воняет')


@bot.message_handler(commands=['subscriptions'])
def handle_docs_audio(message):

	os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

	if os.path.exists(credentials_pickle_file):
		with open(credentials_pickle_file, 'rb') as f:
			credentials = pickle.load(f)
	else:
		flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
		credentials = flow.run_console()
		with open(credentials_pickle_file, 'wb') as f:
			pickle.dump(credentials, f)

	youtube = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)
	request = youtube.subscriptions().list(part="snippet,id,contentDetails", mine=True, maxResults=500)

	# в response находится список всех подписок пользователя
	response = request.execute()

	# в y находится список всех channelId из списка подписок пользователя 
	y = ([i["snippet"]["resourceId"]["channelId"] for i in response["items"]])

	# в channel находится список всех Id каналов, на которые подписан пользователь
	channel = []
	for i in y:
		request = youtube.channels().list(part="snippet,contentDetails,statistics",id=i,maxResults=500)
		response = request.execute()
		channel.append(response)

	# в p находится список uploads - айди плейлиста загруженные каждого канала 
	p = ([i["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"] for i in channel])	

	# в playlistItem находится список параметров плейлиста загруженные 
	playlistItem = []
	for i in p:
		request = youtube.playlistItems().list(part="contentDetails",playlistId=i,maxResults=500)
		response = request.execute()
		playlistItem.append(response)

	# в s находится список ID видео всех каналов
	s = ([i["items"] for i in playlistItem])

	current_time = datetime.datetime.now()
	if os.path.exists(last_update_time):
		with open(last_update_time, "rb") as f:
			last_update = datetime.datetime.strptime(pickle.load(f), time_read_format)
	else:
		last_update = current_time - datetime.timedelta(days=5)


	for i in s:
		for j in i:
			if "videoPublishedAt" in j["contentDetails"].keys():
				time = j["contentDetails"]["videoPublishedAt"][:-1]
				if datetime.datetime.fromisoformat(time) > last_update:
					with youtube_dl.YoutubeDL({
						'format': 'worstaudio/worst',
						'postprocessors': [{
							'key': 'FFmpegExtractAudio',
							'preferredcodec': 'mp3',
							'preferredquality': '128',
						}]}) as ydl:
						ydl.download(['http://www.youtube.com/watch?v=' + j["contentDetails"]["videoId"]])

					for path in os.listdir(os.path.abspath(os.getcwd())):
						if path.endswith(".mp3"):
							try:
								bot.send_audio(chat_id=message.from_user.id, audio=open(path, 'rb'), timeout=120)
								bot.send_audio(chat_id="@jjjeeepppaaa", audio=open(path, 'rb'), timeout=120)
							except Exception as e:
								bot.send_message(message.chat.id, str(e) + '\nhttp://www.youtube.com/watch?v=' + j["contentDetails"]["videoId"])
							os.remove(path)

				else:
					break


	with open(last_update_time, "wb") as f:
		pickle.dump(datetime.datetime.strftime(current_time, time_read_format), f)


# обработка текстовых сообщений
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if message.text.lower() == 'воняешь':
        bot.send_message(message.from_user.id, 'сам воняешь')
    else:
        bot.send_message(message.from_user.id, 'Не понимаю, что это значит.')




# запуск бота
bot.polling(none_stop=True)