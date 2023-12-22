import os

from telebot import TeleBot, types, util
from dotenv import load_dotenv

load_dotenv()


class TelegramBot:
    """
    This class represents a Telegram bot built with the `telebot` library.

    Attributes:
        bot (telebot.TeleBot): The underlying Telegram bot instance.
        reading_book_markup (telebot.types.ReplyKeyboardMarkup): Keyboard markup used
            for the reading book confirmation dialogue.
        confirm_book_markup (telebot.types.ReplyKeyboardMarkup): Keyboard markup used
            for confirming book details.

    Methods:
        __init__(self): Initializes the bot with the bot token and parses mode.
    """
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    def __init__(self):
        self.bot = TeleBot(self.TOKEN, parse_mode=None)
        self.reading_speed_markup = util.quick_markup({
            'Calculate Reading Speed': {'callback_data': 'confirm_yes'},
            'Enter Reading Speed': {'callback_data': 'next_book'},
            'Use Average Reading Speed (240WPM)': {'callback_data': 'enter_author_name'}
        }, row_width=1)
        self.done_reading_button = util.quick_markup({
            "Done !!": {"callback_data": "reading_done"}
        }, row_width=1)
        self.new_book_markup = util.quick_markup({
            'Yes': {'callback_data': 'confirm_book_details'},
            'Next': {'callback_data': 'get_next_book_details'}
        }, row_width=2)
        self.confirm_book_markup = util.quick_markup({
            'Change Genre': {'callback_data': 'change_genre'},
            'Change Language': {'callback_data': 'change_language'},
            'Everything Looks Good!': {'callback_data': 'no_change_req'},
        }, row_width=2)
        self.recommendation_markup = util.quick_markup({
            'Wishlist': {'callback_data': 'recommendation_wishlist'},
            'Next Recommendation': {'callback_data': 'recommendation_next_book'},
        }, row_width=1)
