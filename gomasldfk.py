import telebot
import cloudscraper
import random
import string
import time
from datetime import datetime
import threading
import os

# Bot configuration
BOT_TOKEN = "7383135910:AAHTHNGo0oJuwMaaePyjsvr5VmpvXnvoGtc"  # Replace with your actual token
bot = telebot.TeleBot(BOT_TOKEN)

# Global variables
active_tasks = {}  # Dictionary to store active tasks with their status
class ScraperTask:
    def __init__(self, chat_id, total_attempts):
        self.chat_id = chat_id
        self.total_attempts = total_attempts
        self.current_attempt = 0
        self.found_codes = []
        self.not_found_codes = []
        self.is_running = False
        self.start_time = None
        self.end_time = None
        self.scraper = cloudscraper.create_scraper()
        
    def generate_code(self, length=8):
        """Generate a random alphanumeric code"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    def save_results(self):
        """Save results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Make sure the results directory exists
        if not os.path.exists("results"):
            os.makedirs("results")
            
        found_file = f"results/found_{timestamp}.txt"
        not_found_file = f"results/not_found_{timestamp}.txt"
        
        with open(found_file, "w") as f:
            for code in self.found_codes:
                f.write(code + "\n")
                
        with open(not_found_file, "w") as f:
            for code in self.not_found_codes:
                f.write(code + "\n")
                
        return found_file, not_found_file
    
    def get_summary(self):
        """Generate a summary of the scraping results"""
        duration = (self.end_time - self.start_time) if self.end_time else (datetime.now() - self.start_time)
        
        summary = f"📊 *Scraping Summary*\n\n"
        summary += f"✅ Completed: {self.current_attempt}/{self.total_attempts} attempts\n"
        summary += f"⏱ Duration: {duration.total_seconds():.2f} seconds\n"
        summary += f"🟢 Found codes: {len(self.found_codes)}\n"
        summary += f"🔴 Not found codes: {len(self.not_found_codes)}\n"
        summary += f"⚠️ Errors: {self.current_attempt - len(self.found_codes) - len(self.not_found_codes)}\n"
        
        if len(self.found_codes) > 0:
            summary += f"\n🎯 *Last 5 Found Codes*:\n"
            for code in self.found_codes[-5:]:
                summary += f"- `{code}`\n"
                
        return summary
    
    def start(self):
        """Start the scraping task"""
        self.is_running = True
        self.start_time = datetime.now()
        
        bot.send_message(self.chat_id, f"🚀 Starting scraping task with {self.total_attempts} attempts...")
        
        for i in range(self.total_attempts):
            if not self.is_running:
                break
                
            self.current_attempt = i + 1
            code = self.generate_code()
            url = f"https://you.com/pro/{code}"
            
            try:
                response = self.scraper.get(url)
                status = response.status_code
                
                status_message = f"[{self.current_attempt}/{self.total_attempts}] Code: {code} | Status: {status}"
                
                if status == 200:
                    self.found_codes.append(code)
                    status_message += " ✅"
                elif status == 404:
                    self.not_found_codes.append(code)
                    status_message += " ❌"
                else:
                    status_message += f" ⚠️ Unexpected status"
                
                # Send a status update every 10 attempts
                if self.current_attempt % 10 == 0:
                    bot.send_message(self.chat_id, status_message)
                
                # Be polite to the server
                time.sleep(1)
                
            except Exception as e:
                error_message = f"Error with code {code}: {str(e)}"
                bot.send_message(self.chat_id, error_message)
                time.sleep(5)  # Wait longer after an error
        
        self.end_time = datetime.now()
        self.is_running = False
        
        # Save results and send summary
        found_file, not_found_file = self.save_results()
        
        summary = self.get_summary()
        bot.send_message(self.chat_id, summary, parse_mode="Markdown")
        
        # Send result files
        if len(self.found_codes) > 0:
            with open(found_file, "rb") as f:
                bot.send_document(self.chat_id, f, caption="Found codes")
                
        if len(self.not_found_codes) > 0:
            with open(not_found_file, "rb") as f:
                bot.send_document(self.chat_id, f, caption="Not found codes")
                
        # Remove this task from active tasks
        del active_tasks[self.chat_id]
        
        return summary

# Command handlers
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handle the /start command"""
    welcome_message = (
        "👋 Welcome to the Code Scraper Bot!\n\n"
        "This bot helps you scrape codes from you.com/pro/\n\n"
        "Available commands:\n"
        "/start - Show this message\n"
        "/scrape [attempts] - Start scraping with specified number of attempts\n"
        "/status - Check current scraping status\n"
        "/stop - Stop the active scraping task\n"
        "/help - Show help information\n\n"
        "Example: /scrape 100"
    )
    bot.reply_to(message, welcome_message)

@bot.message_handler(commands=['help'])
def handle_help(message):
    """Handle the /help command"""
    help_message = (
        "📚 *Bot Commands*:\n\n"
        "/start - Show welcome message\n"
        "/scrape [attempts] - Start scraping with specified number of attempts\n"
        "/status - Check current scraping status\n"
        "/stop - Stop the active scraping task\n"
        "/help - Show this help information\n\n"
        "*Examples*:\n"
        "/scrape 100 - Run 100 attempts\n"
        "/scrape 500 - Run 500 attempts\n\n"
        "⚠️ Please use responsibly and respect the target website's terms of service."
    )
    bot.reply_to(message, help_message, parse_mode="Markdown")

@bot.message_handler(commands=['scrape'])
def handle_scrape(message):
    """Handle the /scrape command"""
    chat_id = message.chat.id
    
    # Check if there's already an active task for this chat
    if chat_id in active_tasks:
        bot.reply_to(message, "⚠️ You already have an active scraping task. Use /status to check progress or /stop to stop it.")
        return
    
    # Parse the number of attempts
    try:
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, "⚠️ Please specify the number of attempts. Example: /scrape 100")
            return
            
        attempts = int(command_parts[1])
        if attempts <= 0:
            bot.reply_to(message, "⚠️ Number of attempts must be positive.")
            return
            
        if attempts > 1000:
            bot.reply_to(message, "⚠️ Maximum allowed attempts is 1000.")
            return
            
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid number of attempts. Please provide a valid number.")
        return
    
    # Create a new scraper task
    task = ScraperTask(chat_id, attempts)
    active_tasks[chat_id] = task
    
    # Start the task in a separate thread
    thread = threading.Thread(target=task.start)
    thread.daemon = True
    thread.start()
    
    bot.reply_to(message, f"✅ Scraping task started with {attempts} attempts. Use /status to check progress.")

@bot.message_handler(commands=['status'])
def handle_status(message):
    """Handle the /status command"""
    chat_id = message.chat.id
    
    if chat_id not in active_tasks:
        bot.reply_to(message, "❌ No active scraping task. Use /scrape [attempts] to start one.")
        return
    
    task = active_tasks[chat_id]
    
    if task.is_running:
        progress = (task.current_attempt / task.total_attempts) * 100
        duration = (datetime.now() - task.start_time).total_seconds()
        
        status_message = (
            f"🔄 *Active Scraping Task*\n\n"
            f"Progress: {task.current_attempt}/{task.total_attempts} ({progress:.1f}%)\n"
            f"Elapsed time: {duration:.2f} seconds\n"
            f"Found codes: {len(task.found_codes)}\n"
            f"Not found codes: {len(task.not_found_codes)}\n\n"
            f"Use /stop to stop the task."
        )
        
        bot.reply_to(message, status_message, parse_mode="Markdown")
    else:
        summary = task.get_summary()
        bot.reply_to(message, summary, parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    """Handle the /stop command"""
    chat_id = message.chat.id
    
    if chat_id not in active_tasks:
        bot.reply_to(message, "❌ No active scraping task to stop.")
        return
    
    task = active_tasks[chat_id]
    
    if task.is_running:
        task.is_running = False
        bot.reply_to(message, "🛑 Scraping task is being stopped... Final summary will be sent shortly.")
    else:
        bot.reply_to(message, "❌ The task is not running.")

# Start the bot
if __name__ == "__main__":
    print("Bot started...")
    
    # Create results directory if it doesn't exist
    if not os.path.exists("results"):
        os.makedirs("results")
        
    # Start the bot
    bot.polling(none_stop=True)