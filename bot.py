import os
import logging
import os
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- បញ្ចូល TOKEN របស់អ្នកនៅទីនេះ ---
TELEGRAM_TOKEN = os.environ.get("7807737407:AAE7L4bYmWkCIIVPjuAUjDii0i8uCbJMEUU")
# ---------------------------------

# កំណត់អត្តសញ្ញាណទំហំ Upload អតិបរមារបស់ Telegram (50MB)
TELEGRAM_MAX_UPLOAD_SIZE = 50 * 1024 * 1024 

# បើកដំណើរការ Logging ដើម្បីងាយស្រួលក្នុងការ Debug
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ផ្ញើសារស្វាគមន៍នៅពេលអ្នកប្រើវាយ /start"""
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"សួស្តី {user_name}!\n\n"
        "សូមផ្ញើ Link វីដេអូ (ដូចជា YouTube, Facebook, TikTok...) "
        "មកឲ្យខ្ញុំ ខ្ញុំនឹងព្យាយាមទាញយកវាជូនអ្នក។"
    )


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ដោះស្រាយសារដែលមាន Link វីដេអូ"""
    video_url = update.message.text
    chat_id = update.message.chat_id

    # ផ្ញើសារប្រាប់អ្នកប្រើថា "កំពុងដំណើរការ"
    processing_msg = await update.message.reply_text("⏳ កំពុងទាញយក... សូមរង់ចាំបន្តិច...")

    # កំណត់ឈ្មោះ File បណ្តោះអាសន្នដោយផ្អែកលើ Chat ID
    output_filename = f"video_{chat_id}.%(ext)s"

    ydl_opts = {
        'format': 'best[ext=mp4][filesize<=?50M]/best[filesize<=?50M]/best', # ព្យាយាមយក MP4 ដែលល្អបំផុត ក្រោម 50MB
        'outtmpl': output_filename, # គំរូឈ្មោះ File ដែលត្រូវទាញយក
        'max_filesize': TELEGRAM_MAX_UPLOAD_SIZE, # កំណត់ទំហំទាញយកអតិបរមា
        'noplaylist': True, # កុំទាញយក Playlist ទាំងមូល
        'quiet': True, # កុំបង្ហាញ Output ច្រើនក្នុង Console
        'merge_output_format': 'mp4', # បើមានការ merge (វីដេអូ និងសំឡេង) សូមឲ្យចេញជា MP4
    }

    downloaded_file_path = None
    
    try:
        # ចាប់ផ្តើមទាញយកជាមួយ yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            # យកឈ្មោះ File ពិតប្រាកដ បន្ទាប់ពីទាញយករួច
            downloaded_file_path = ydl.prepare_filename(info)

        if downloaded_file_path and os.path.exists(downloaded_file_path):
            # ពិនិត្យទំហំ File ម្តងទៀត
            file_size = os.path.getsize(downloaded_file_path)

            if file_size > TELEGRAM_MAX_UPLOAD_SIZE:
                # បើ File ធំពេក (ទោះបីជាបានកំណត់ max_filesize ហើយក៏ដោយ)
                await context.bot.edit_message_text(
                    text=f"❌ ការទាញយកបរាជ័យ។\nវីដេអូនេះមានទំហំធំពេក (លើស 50MB) មិនអាចផ្ញើតាម Telegram បានទេ។",
                    chat_id=chat_id,
                    message_id=processing_msg.message_id
                )
            else:
                # ផ្ញើ File វីដេអូ
                await context.bot.edit_message_text(
                    text="✅ ទាញយកបានជោគជ័យ! កំពុងផ្ញើវីដេអូជូន...",
                    chat_id=chat_id,
                    message_id=processing_msg.message_id
                )
                
                # បើក File ហើយផ្ញើ
                with open(downloaded_file_path, 'rb') as video_file:
                    await context.bot.send_video(
                        chat_id=chat_id, 
                        video=video_file, 
                        supports_streaming=True,
                        caption=info.get('title', 'Video Downloaded')
                    )
        else:
            raise Exception("រកមិនឃើញ File បន្ទាប់ពីទាញយក។")

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"DownloadError: {e}")
        error_message = str(e)
        if "Unsupported URL" in error_message:
            reply_text = "❌ ខ្ញុំមិនស្គាល់ Link នេះទេ។"
        elif "HTTP Error 404" in error_message:
            reply_text = "❌ រកមិនឃើញវីដេអូ (Error 404)។"
        else:
            reply_text = f"❌ មានបញ្ហា។ ខ្ញុំមិនអាចទាញយកវីដេអូពី Link នេះបានទេ។"
        
        await context.bot.edit_message_text(
            text=reply_text,
            chat_id=chat_id,
            message_id=processing_msg.message_id
        )
        
    except Exception as e:
        logger.error(f"General Error: {e}")
        await context.bot.edit_message_text(
            text="❌ មានបញ្ហាអ្វីមួយកើតឡើង។ សូមព្យាយាមម្តងទៀត។",
            chat_id=chat_id,
            message_id=processing_msg.message_id
        )
        
    finally:
        # លុប File វីដេអូចេញពី Server បន្ទាប់ពីផ្ញើរួច (សំខាន់มาก)
        if downloaded_file_path and os.path.exists(downloaded_file_path):
            os.remove(downloaded_file_path)
            logger.info(f"បានលុប File: {downloaded_file_path}")


def main():
    """ចាប់ផ្តើម Bot"""
    print("Bot កំពុងចាប់ផ្តើមដំណើរការ...")

    # បង្កើត Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # បន្ថែម Handlers (អ្នកដោះស្រាយ)
    application.add_handler(CommandHandler("start", start_command))
    
    # នេះជា Handler សំខាន់៖ វានឹងដំណើរការ Function `download_video` 
    # នៅពេលទទួលបានសារជាអក្សរ (TEXT) ដែលមិនមែនជាពាក្យបញ្ជា (COMMAND)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    # ចាប់ផ្តើម Bot
    application.run_polling()


if __name__ == "__main__":
    main()