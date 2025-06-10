import os
import glob
import threading
from flask import Flask
from yt_dlp import YoutubeDL
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '7889633004:AAESEridzpDhI-zSAZAZGcHCC2Vj_DVsCuE'
bot = telebot.TeleBot(TOKEN)

# === 保持 Replit 醒著 ===
app = Flask('')

@app.route('/')
def home():
    return "✅ 機器人在線"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# === 處理 /start、/help ===
@bot.message_handler(commands=['start', 'help'])
def send_instructions(message):
    bot.reply_to(message, "請傳送 YouTube 連結，我會自動分析可下載格式，讓你選擇 MP3 或 MP4。")

# === 處理連結 ===
@bot.message_handler(content_types=['text'])
def handle_link(message):
    url = message.text.strip()

    if "youtube.com" not in url and "youtu.be" not in url:
        bot.reply_to(message, "❌ 請傳送有效的 YouTube 連結。")
        return

    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            title = info.get('title', 'download')

        # 檢查是否支援 mp3/mp4 格式
        has_audio = any(f.get('vcodec') == 'none' for f in formats)
        has_video = any(f.get('vcodec') != 'none' and f.get('ext') == 'mp4' for f in formats)

        if not has_audio and not has_video:
            bot.reply_to(message, "⚠️ 無可用格式。可能影片太舊、受限或不公開。")
            return

        markup = InlineKeyboardMarkup()
        if has_audio:
            markup.add(InlineKeyboardButton("🎵 下載 MP3", callback_data=f"mp3|{url}"))
        if has_video:
            markup.add(InlineKeyboardButton("🎥 下載 MP4", callback_data=f"mp4|{url}"))

        bot.reply_to(message, f"🎬 {title}\n請選擇你要的格式：", reply_markup=markup)

    except Exception as e:
        bot.reply_to(message, f"❌ 分析失敗：\n{str(e)}")

# === 處理格式選擇 ===
@bot.callback_query_handler(func=lambda call: True)
def handle_download(call):
    format_type, url = call.data.split('|')
    chat_id = call.message.chat.id

    try:
        title = "media"
        filename = ""

        if format_type == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': '%(title)s.%(ext)s',
                'quiet': True,
                'noplaylist': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        elif format_type == 'mp4':
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
                'outtmpl': '%(title)s.%(ext)s',
                'quiet': True,
                'noplaylist': True,
            }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            filename = glob.glob(f"{title}.*")[0]

        if not os.path.exists(filename):
            bot.send_message(chat_id, "❌ 找不到下載檔案。")
            return

        with open(filename, 'rb') as f:
            if format_type == 'mp3':
                bot.send_audio(chat_id, f, title=title)
            else:
                bot.send_document(chat_id, f, caption=title)

        bot.send_message(chat_id, "✅ 已成功傳送！")

    except Exception as e:
        bot.send_message(chat_id, f"❌ 錯誤：\n{str(e)}")

    finally:
        # 自動清除所有暫存檔案
        for ext in ('*.mp3', '*.mp4', '*.webm'):
            for f in glob.glob(ext):
                try:
                    os.remove(f)
                except:
                    pass

# === 啟動 Bot 與 Flask ===
if __name__ == '__main__':
    keep_alive()
    print("🚀 機器人已啟動")
    bot.polling()
