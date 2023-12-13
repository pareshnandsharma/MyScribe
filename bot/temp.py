from telebot import TeleBot, types, util
import sqlite3
from typing import Optional
import requests
import bs4
import re

GOOGLE_SE_ID = GOOGLE_SEARCH_ENGINE_ID
GOOGLE_SE_API = GOOGLE_SEARCH_ENGINE_API
GOOGLE_SE_URL = GOOGLE_SEARCH_ENGINE_URL



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
    TOKEN = TELEGRAM_BOT_TOKEN

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



AVG_READING_SPEED = 300  # WPM (Words Per Minute)
AVG_WORDS_PER_PAGE = 300


class BookDatabase:
    def __init__(self):
        self.current_book_id = None
        self.conn = sqlite3.connect(MY_DATABASE, check_same_thread=False)
        self.cur = self.conn.cursor()

    def insert_username_and_id(self, telegram_id: int, username: str, reading_speed: int = AVG_READING_SPEED) -> bool:
        """
        Inserts a new user into the BookDatabase if they don't already exist.

        Args:
            telegram_id (int): The user's Telegram ID.
            username (str): The user's username.
            reading_speed (int): User's reading speed. (WPM)

        Returns:
            bool: True if the user was successfully inserted, False otherwise.
        """
        # Insert user if they don't exist
        try:
            self.cur.execute("INSERT INTO users (id, first_name, reading_speed) VALUES (?,?,?)",
                             (telegram_id, username, reading_speed))
            self.conn.commit()
            return True
        except Exception as e:
            print(e)
            return False

    def insert_book_details(self, book_details):
        """
        Inserts the provided book details into the "books" table in the database.

        Args:
            book_details: An object containing the book's title, author, genre, language, total pages, ISBN-13, description, and cover URL.

        Returns:
            True if the insertion was successful, False otherwise.
        """
        try:
            # Execute SQL query to insert book details
            self.cur.execute(
                "INSERT INTO books (title, author, genre, language, total_pages, isbn13, description, book_cover_url)"
                "VALUES (lower(?),lower(?),lower(?),lower(?),?,?,?,?)",
                (book_details.book_title, book_details.book_author,
                 book_details.book_genre, book_details.book_language,
                 book_details.book_total_page_count, book_details.book_isbn13,
                 book_details.book_description, book_details.book_cover))

            # Commit changes to the database
            self.conn.commit()

            return True
        except sqlite3.Error as e:
            # Handle any database errors
            print(f"Error inserting book details: {e}")
            return False

    def insert_book_status(self, telegram_id: int, book_title: str, current_book_status: int) -> bool:
        book_id = self.retrieve_book_id(book_title)
        try:
            self.cur.execute("INSERT INTO books_and_users (user_id, book_id, book_status) VALUES (?,?,?)",
                             (telegram_id, book_id, current_book_status))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(e)
            return False

    def check_if_user_exist(self, telegram_id: int) -> bool:
        """
        Checks if a user exists in the database by their Telegram ID.

        Args:
            telegram_id (int): The Telegram ID of the user.

        Returns:
            bool: True if the user exists, False otherwise.
        """
        self.cur = self.conn.cursor()
        self.cur.execute("SELECT * FROM users WHERE id = ?", (telegram_id,))
        return self.cur.rowcount != 0
        #     return True
        # else:
        #     return False

    def check_if_book_exist(self, book_title: str) -> bool:
        """
        Checks if a book exists in the database based on its title.

        Args:
            book_title (str): The title of the book.

        Returns:
            bool: True if the book exists, False otherwise.
        """
        self.cur.execute("SELECT * FROM books WHERE title = ?", (book_title,))
        return self.cur.rowcount != 0

    def fetch_book_details_from_db(self, book_title: str) -> Optional[dict]:
        """
        Fetches book details from the database based on the provided book title.

        Args:
            book_title: The title of the book to fetch details for.

        Returns:
            A dictionary containing book details if the book is found, or False otherwise.
        """
        try:
            self.cur.execute("SELECT * FROM books WHERE title = ?", (book_title,))
            db_book_details = self.cur.fetchone()
        except sqlite3.Error as e:
            return None
        else:
            if db_book_details:
                self.current_book_id = db_book_details[0]
                return {'book_title': db_book_details[1],
                        'book_author': db_book_details[2],
                        'book_genre': db_book_details[3],
                        'book_language': db_book_details[4],
                        'book_total_page_count': db_book_details[5],
                        'book_isbn13': db_book_details[6],
                        'book_description': db_book_details[7],
                        'book_cover': db_book_details[8], }
            else:
                return None

    def retrieve_book_id(self, book_title: str) -> Optional[int]:
        self.cur.execute("SELECT id FROM books WHERE title = ?", (book_title,))
        book_id = self.cur.fetchone()
        if book_id:
            print(book_id)
            return book_id[0]
        else:
            return None

    def retrieve_total_pages(self, book_title):
        try:
            self.cur.execute("SELECT total_pages FROM books WHERE title = ?", (book_title,))
            total_pages = self.cur.fetchone()
            print(total_pages)
        except sqlite3.Error as e:
            print(e)
        else:
            if total_pages:
                return total_pages[0]
            else:
                return None

    def retrieve_book_status_if_exists(self, telegram_id: int, book_title: str) -> Optional[int]:
        """
        Retrieves the book's status (currently reading, completed, or wishlist) for a specific user if it exists in the database.

        Args:
            telegram_id: The Telegram ID of the user.
            book_title: The title of the book.

        Returns:
            The book's status as an integer (1 - Currently Reading, 2 - Completed, 3 - Wishlist) if found, or None if not found.
        """
        book_id = self.retrieve_book_id(book_title)
        print(book_id)
        self.cur.execute("SELECT book_status FROM books_and_users WHERE user_id = ? AND book_id = ? ",
                         (telegram_id, book_id))
        retrieved_book_status = self.cur.fetchone()
        print(retrieved_book_status)
        if retrieved_book_status:
            return retrieved_book_status[0]
        else:
            return None

    def retrieve_pages_read(self, telegram_id, book_title) -> Optional[int]:
        book_id = self.retrieve_book_id(book_title)
        self.cur.execute("SELECT pages_read FROM books_and_users WHERE user_id = ? AND book_id = ?",
                         (telegram_id, book_id))
        pages_read = self.cur.fetchone()[0]
        if pages_read:
            return int(pages_read)
        else:
            return 0

    def retrieve_reading_speed(self, telegram_id):
        try:
            self.cur.execute("SELECT reading_speed FROM users WHERE id = ?", (telegram_id,))
            reading_speed = self.cur.fetchone()
        except sqlite3.Error as e:
            print(e)
        else:
            if reading_speed:
                return reading_speed[0]
            else:
                return None

    def retrieve_reading_time_left(self, telegram_id, book_title):
        book_id = self.retrieve_book_id(book_title)
        try:
            self.cur.execute("SELECT time_left FROM books_and_users WHERE user_id = ? AND book_id = ?",
                             (telegram_id, book_id))
            reading_time_left = self.cur.fetchone()[0]
            print(f"first : {reading_time_left}")
        except sqlite3.Error as e:
            print(e)
        else:
            if reading_time_left:
                print(reading_time_left)
                return reading_time_left
            else:
                print("NOT NONE")
                self.update_reading_time_left(telegram_id, book_title)
                self.retrieve_reading_time_left(telegram_id, book_title)

    def update_user_reading_speed(self, telegram_id: int, reading_speed: int) -> bool:
        """
           Updates the reading speed of a user in the database.

           Args:
               telegram_id (int): The user's Telegram ID.
               reading_speed (int): The user's new reading speed (WPM).

           Returns:
               bool: True if the update was successful, False otherwise.
           """
        try:
            self.cur.execute("UPDATE users SET reading_speed = ? WHERE id = ?", (reading_speed, telegram_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(e)
            return False

    def update_reading_time_left(self, telegram_id, book_title):
        book_id = self.retrieve_book_id(book_title)
        reading_time_left = self.calculate_reading_time_left(telegram_id, book_title)
        print(reading_time_left)
        try:
            self.cur.execute("UPDATE books_and_users SET time_left = ? WHERE user_id = ? AND book_id = ?",
                             (reading_time_left, telegram_id, book_id))
            self.conn.commit()
        except sqlite3.Error as e:

            return False
        else:
            return True

    def update_pages_read(self, telegram_id, book_title, pages_read) -> bool:
        book_id = self.retrieve_book_id(book_title)
        pages_read_yet = self.retrieve_pages_read(telegram_id, book_title)
        if pages_read_yet:
            total_pages = pages_read + int(pages_read_yet)
        else:
            total_pages = pages_read
        print(pages_read, pages_read_yet, total_pages)
        print(telegram_id, book_title)
        try:
            self.cur.execute("UPDATE books_and_users SET pages_read = ? WHERE user_id = ? AND book_id = ?",
                             (total_pages, telegram_id, book_id))
            self.conn.commit()
        except sqlite3.Error as e:
            return False
        else:
            self.update_reading_time_left(telegram_id, book_title)
            return True

    def calculate_reading_time_left(self, telegram_id, book_title):
        user_reading_speed = self.retrieve_reading_speed(telegram_id)
        total_pages = self.retrieve_total_pages(book_title)
        pages_read = self.retrieve_pages_read(telegram_id, book_title)
        print(f"Pages read {pages_read}")
        if not pages_read:
            pages_read = 0
        total_pages = total_pages - pages_read
        total_words = total_pages * AVG_WORDS_PER_PAGE
        time_left_in_mins = total_words / user_reading_speed
        return time_left_in_mins


class BookWebScraping:
    def extract_genre(self, genre_tag: bs4.element.Tag) -> str:
        """
        Extract genre information from the HTML genre tag.

        Parameters:
        - genre_tag (bs4.element.Tag): HTML tag containing genre information.

        Returns:
        - str: Extracted genre information.
        """
        genre = None

        try:
            # Attempt to find genre information in next sibling's list items
            genres = genre_tag.nextSibling.findAll("li")
            genre = genres[0].get_text()
        except (AttributeError, IndexError):
            pass
        else:
            return genres[0].get_text()

        try:
            # If not found, try to extract genre information from the next sibling's text
            genre = genre_tag.nextSibling.get_text()
        except AttributeError:
            pass
        else:
            return genre.split(",")[0]

        return genre

    def get_book_genre_language_wikipedia(self, book_name: str, author_name: str) -> tuple:
        """
        Get book genre and language information from Wikipedia.

        Parameters:
        - book_name (str): Name of the book.
        - author_name (str): Name of the author (optional).

        Returns:
        - tuple: A tuple containing genre and language information.
        """
        if author_name:
            query = f"{book_name} by {author_name} wikipedia"
        else:
            query = f"{book_name} wikipedia"

        # Set parameters for Google Custom Search Engine (CSE) API request
        param = {
            "key": GOOGLE_SE_API,
            "cx": GOOGLE_SE_ID,
            "q": query,
        }

        # Perform Google CSE API request
        response = requests.get(GOOGLE_SE_URL, params=param)
        result = response.json()

        # Extract Wikipedia page URL from the API response
        url = result['items'][0]['link']

        # Fetch the HTML content of the Wikipedia page
        response2 = requests.get(url)
        soup = bs4.BeautifulSoup(response2.text, "html.parser")

        # Extract genre and language tags from the Wikipedia page HTML
        genre_tag = soup.find("th", string="Genre")
        lang_tag = soup.find("th", string="Language")

        # Extract genre information using the defined method
        genre = self.extract_genre(genre_tag)

        try:
            # Attempt to extract language information
            lang = lang_tag.nextSibling.get_text()
        except AttributeError:
            lang = None

        return genre, lang


class BookApi:
    G00GLE_BOOKS_API = BOOKS_API
    GOOGLE_BOOKS_URL = BOOKS_URL

    def __init__(self):
        self.book_search_result = None
        self.api_book_details = {'book_title': None,
                                 'book_author': None,
                                 'book_genre': None,
                                 'book_total_page_count': None,
                                 'book_isbn13': None,
                                 'book_language': None,
                                 'book_cover': None,
                                 'book_description': None, }

        self.books_ws = BookWebScraping()
        self.api_search_result = None

    def search_book_details(self, book_name: str, author_name: str = None) -> bool:
        """
        Searches for a specific book based on its title and author name using the Google Books API.

        Args:
            book_name: The title of the book.
            author_name: The author's name.

        Returns:
            dict: A dictionary containing the search results in JSON format.
        """
        self.api_search_result = None
        # Construct the search query
        if author_name:
            query = f"intitle:{book_name}+inauthor{author_name}"
        else:
            query = f"intitle:{book_name}"

        # Define the search parameters
        book_search_parameters = {
            'q': query,
            'maxResults': 5,
            'key': self.API
        }

        # Send a GET request to the Google Books API
        response = requests.get(url=self.URL, params=book_search_parameters)

        # Check for HTTP errors
        response.raise_for_status()

        # Return the search result
        self.api_search_result = response.json()
        print(self.api_search_result)
        return self.api_search_result['totalItems'] != 0

    def extract_book_details_from_api_result(self, search_result_count) -> dict | None:
        """
        Get book details from the API response.

        Returns:
        - dict: Dictionary containing book details.
        """
        try:
            # Attempt to retrieve volume information from the API response
            current_result = self.api_search_result['items'][search_result_count]['volumeInfo']
        except KeyError:
            # Handle the case where the expected keys are not present in the API response
            return None

        # GET Title
        print(current_result)
        try:
            # Attempt to get the book title from the volume information
            title = current_result['title']
        except Exception as e:
            # Handle any exception that may occur during title extraction
            return None
        else:
            # Set the book title in the book_details dictionary
            self.api_book_details['book_title'] = title

        # GET AUTHOR
        try:
            # Attempt to get the first author from the authors list
            author = current_result['authors'][0]
        except Exception as e:
            # Handle any exception that may occur during author extraction
            self.api_book_details['book_author'] = None
        else:
            # Set the book author in the book_details dictionary
            self.api_book_details['book_author'] = author

        # GET PAGE COUNT
        try:
            # Attempt to get the total page count from the volume information
            total_page_count = current_result['pageCount']
        except Exception as e:
            # Handle any exception that may occur during page count extraction
            self.api_book_details['book_total_page_count'] = None
        else:
            # Set the total page count in the book_details dictionary
            self.api_book_details['book_total_page_count'] = total_page_count

        # GET Description
        try:
            # Attempt to get the book description from the volume information
            desc = current_result['description']
        except Exception as e:
            # Handle any exception that may occur during description extraction
            self.api_book_details['book_description'] = None
        else:
            # Set the book description in the book_details dictionary
            self.api_book_details['book_description'] = desc

        # GET ISBN
        try:
            # Attempt to get the list of ISBNs from the volume information
            isbn_list = current_result['industryIdentifiers']
        except Exception as e:
            # Handle any exception that may occur during ISBN extraction
            self.api_book_details['book_isbn13'] = None
        else:
            # Iterate through the ISBN list and set the ISBN-13 in the book_details dictionary
            for isbn in isbn_list:
                if isbn['type'] == "ISBN_13":
                    self.api_book_details['book_isbn13'] = isbn['identifier']

        # GET BOOK COVER
        try:
            # Attempt to get the book cover URL from the volume information
            book_cover = current_result['imageLinks']['thumbnail']
        except Exception as e:
            # Handle any exception that may occur during book cover URL extraction
            self.api_book_details['book_cover'] = None
        else:
            # Set the book cover URL in the book_details dictionary
            self.api_book_details['book_cover'] = book_cover

        # GET BOOK GENRE AND LANGUAGE
        if self.api_book_details['book_title'] and self.api_book_details['book_author']:
            self.api_book_details['book_genre'], self.api_book_details[
                'book_language'] = self.books_ws.get_book_genre_language_wikipedia(
                self.api_book_details['book_title'], self.api_book_details['book_author'])

        return self.api_book_details

import re
from book_api import BookApi
from book_database import BookDatabase


class BookBot:

    def __init__(self):
        self.book_caption = None
        self.book_title = None
        self.book_author = None
        self.book_genre = None
        self.book_total_page_count = None
        self.book_language = None
        self.book_isbn13 = None
        self.book_description = None
        self.book_cover = None

        self.api_search_result_count = 0

        self.book_api = BookApi()
        self.book_database = BookDatabase()

    books_chat_patterns = {
        # "reading_pages": r"(read)?\s?(?P<number_of_pages>\d+)\s?page(s)?\s?(of|from)\s?(?<book_name>.+?)(
        # ?=today|yesterday|now|recently|currently|\.|$)",
        "reading_a_book": r"(?i)(reading|going through)\s(?P<book_name>.+?)(?=recently|now|currently|nowadays|\.|$)",
        "book_wishlist": None,
        "book_finished": r"(?i)(have read|read|finished|completed)\s(?P<book_name>.+?)(?=recently|yesterday|today|\.|$)",
        "reading_speed": r"(reading speed|speed test|)",
        "greetings": r"(?i)^(hi|hello|hiya|hola|sup|hey)",
        "negative_response": r"^(no|nope|nah|naw)",
    }

    def extract_book_title_from_sentence(self, regex_type: str, sentence: str) -> str | None:
        """Extracts Book title from a sentence using specific regex.

        If it can't find the book title it returns None.

        Args
        __________
        regex_type : str
            Uses a key from book_chat_patterns to determine the regular expression to be used
        sentence : str
            Sentence to extract book title from
        """
        try:
            self.book_title = re.search(self.books_chat_patterns[regex_type], sentence).group("book_name")
            return self.book_title
        except AttributeError:
            return None

    def get_book_details_from_api(self, book_title: str, book_author: str) -> bool:
        """
        Fetches book details from the Google Books API and populates the object's attributes.

        Args:
            book_title: The title of the book.
            book_author: The author's name.
        """

        # If there are no previous search results, try searching for the book
        if self.api_search_result_count == 0:
            if not self.book_api.search_book_details(book_title, book_author):
                # Attempt to search for the book with both title and author information
                # If unsuccessful, search again with only the title for wider coverage
                self.book_api.search_book_details(book_title)
        # Reset API search result counter if it's at the maximum
        elif self.api_search_result_count == 4:
            self.api_search_result_count = 0

        # Extract book details from the current API search result
        book_details = self.book_api.extract_book_details_from_api_result(self.api_search_result_count)

        # Update object attributes if details were found
        if book_details:
            for key, value in book_details.items():
                setattr(self, key, value)

            # Generate a concise caption summarizing the book details
            self.book_caption = f"Title : {self.book_title}\nAuthor : {self.book_author}"
            self.api_search_result_count += 1
            return True
        else:
            # Clear book title if no details were found
            self.book_title = None
            return False

    def get_book_details_from_db(self, current_book_title):
        book_details = self.book_database.fetch_book_details_from_db(current_book_title)
        if book_details:
            for key, value in book_details.items():
                setattr(self, key, value)
            return True
        else:
            return False

    def validate_pages_read(self, pages_read_today):
        if pages_read_today.isdigit() and int(pages_read_today) > 0:
            return int(pages_read_today)
        else:
            return None



    @property
    def complete_book_details(self):
        return f"Title : {self.book_title}\n" \
               f"Author : {self.book_author}\n" \
               f"Genre : {self.book_genre}\n" \
               f"Language : {self.book_language}\n" \
               f"Total Pages : {self.book_total_page_count}\n" \
               f"ISBN13 : {self.book_isbn13}\n\n"


import time
import telebot.types
from telegram_bot import TelegramBot
from book_database import BookDatabase
from book_bot import BookBot
from large_texts import LargeTexts

# BOOK STATUS
CURRENTLY_READING = 1
COMPLETED = 2
WISHLIST = 3


class ChatBot:

    def __init__(self):
        self.current_user_id = None
        self._current_book_title = None
        self.current_book_author = None
        self.current_book_status = None
        self.retrieved_book_status = None
        self.calc_reading_speed_start_time = None
        self.calc_reading_speed_end_time = None
        self.process_book_info_directly = False
        # Instance of TelegramBot class.
        self.telegram_bot = TelegramBot()
        self.bot = self.telegram_bot.bot

        # Instance of BookBot class.
        self.book_bot = BookBot()
        self.books_chat_patterns = self.book_bot.books_chat_patterns

        # Instance of BookDatabase class.
        self.book_database = BookDatabase()

        # Instance of LargeText class.
        self.large_texts = LargeTexts()

    @property
    def current_book_title(self):
        return self._current_book_title

    @current_book_title.setter
    def current_book_title(self, value):
        if value:
            self._current_book_title = value.lower()
        else:
            self._current_book_title = None

    # MISCELLANEOUS FUNCTIONS
    def send_greeting_message(self, message: telebot.types.Message) -> None:
        """
        Sends an informative greeting message to the user, using the welcome_message attribute of LargeTexts,

        Args:
            message (telebot.types.Message): The incoming Telegram message.

        Returns:
            None
        """

        # Extract user information
        # self.current_user_id = self.get_telegram_id(message)
        username = self.get_username(message)

        # Save user information to database if it doesn't already exist
        # if not self.book_database.check_if_user_exist(self.current_user_id):
        #     self.save_username_and_id_db(message, self.current_user_id, username)

        # Compose greeting message
        greetings_message = f"Hello {username},\n{self.large_texts.welcome_message}"

        # Send greeting message to user
        self.bot.send_message(message.chat.id, greetings_message)

    def save_username_and_id_db(self, message: telebot.types.Message) -> None:
        """
        Save the user's Telegram ID and username to the database. Sends error message if unsuccessful.

        Args:
            self (ChatBot): Instance of the ChatBot class.
            message (telebot.types.Message): Telegram message object.
            telegram_id (int): User's Telegram ID.
            user_name (str): User's username.

        Returns:
            None
        """
        self.current_user_id = message.from_user.id
        user_name = self.get_username(message)
        # Attempt to insert user information into the database
        if not self.book_database.insert_username_and_id(self.current_user_id, user_name):
            # Handle unsuccessful insertion and send error message to user
            self.bot.send_message(message.chat.id, "There is an error saving your information. Please Try Again.")

    # CHATBOT FUNCTIONS
    def get_telegram_id(self, message: telebot.types.Message | telebot.types.CallbackQuery) -> int:
        """
        Extracts the Telegram ID of the user from a telebot message or callback query.

        Args:
            message (telebot.types.Message | telebot.types.CallbackQuery): The Telegram message or callback query object.

        Returns:
            int: The user's Telegram ID.
        """
        telegram_id = message.from_user.id
        return telegram_id

    def get_username(self, message: telebot.types.Message) -> str | None:
        """
        Extracts the user's Telegram ID and username from a message.

        This method attempts to extract the user's first_name as the username,
        but catches any exceptions and returns None if the username is unavailable.

        Args:
            self (ChatBot): Instance of the ChatBot class.
            message (telebot.types.Message): Telegram message object.

        Returns:
            A tuple containing the user's Telegram ID and username (or None).
        """

        # Extract username from message return None if doens't exist
        try:
            username = message.from_user.first_name
        except Exception as e:
            print(e)
            username = None

        return username

    def reset_book_name_and_search_count(self):
        """
        Resets the book attributes for a fresh search.
        """
        self.current_book_title = None
        self.current_book_id = None
        self.current_book_author = None
        self.book_bot.api_search_result_count = 0

    # BOOKS RELATED FUNCTIONS
    def extract_book_title_from_regex(self, message: telebot.types.Message, regex: str | None = None,
                                      sentence: str | None = None) -> None:
        """
        Retrieves the book title from the message content.

        This function first attempts to extract the title using a provided regular expression. If the regex is not provided or the extraction fails, it prompts the user to enter the book title directly.

        Args:
            message: The Telegram message object.
            regex: (Optional) A regular expression to extract the book title from the message.
            sentence: (Optional) A sentence containing the book title (used in conjunction with the regex).

        Returns:
            str: The extracted book title, or None if the title could not be found.
        """
        # Attempt to extract title using regex
        if regex:
            self.current_book_title = self.book_bot.extract_book_title_from_sentence(regex, sentence)
            print(self.current_book_title)
            # Title not found using regex, prompt user for input
            if not self.current_book_title:
                self.bot.send_message(message.chat.id, "Please Enter Name of The Book")
                self.bot.register_next_step_handler(message, self.get_book_title_from_message)
        # No regex provided, prompt user for input
        else:
            self.bot.send_message(message.chat.id, "Please Enter Name of The Book")
            self.bot.register_next_step_handler(message, self.get_book_title_from_message)

    def get_book_title_from_message(self, message: telebot.types.Message) -> None:
        """
        Sets the current book title directly from the message text.

        This function is called when the user bypasses the regular book title extraction process
        and enters the book title directly in their message.

        Args:
            message: The Telegram message object.
        """
        self.current_book_title = message.text
        print(self.current_book_title)
        if self.process_book_info_directly:
            self.process_book_title_and_fetch_details(message)

    def process_book_title_and_fetch_details(self, message: telebot.types.Message) -> None:
        """
        Processes the user-provided book title and attempts to retrieve its details from the database.
        If found, shares the details. If not, prompts the user for the author name to search the API.

        Args:
            message: The Telegram message object.
        """
        # Try to fetch book details from the database
        if self.book_bot.get_book_details_from_db(self.current_book_title):
            # Update current book ID
            self.current_book_id = self.book_database.current_book_id
            self.share_book_details_from_database_(message)
        else:
            # If book not found in database, request author name for API search
            self.bot.send_message(message.chat.id, "Please Enter Author Name : ")
            self.bot.register_next_step_handler(message, self.get_author_name)

    def get_author_name(self, message: telebot.types.Message) -> None:
        """
        Retrieves the author name entered by the user and stores it for further processing.
        Then attempts to fetch book details from the API using both the title and author name.

        Args:
            message: The Telegram message object containing the user-provided author name.
        """
        # Store user-provided author name
        self.current_book_author = message.text
        # Initiate book details retrieval from GOOGLE BOOKS API with both title and author
        self.retrieve_book_data_using_api(message, self.current_book_title, self.current_book_author)

    def retrieve_book_data_using_api(self, message: telebot.types.Message, book_title: str, book_author: str) -> None:
        """
        Retrieves book details from the API based on user input and shares them in the Telegram chat.

        Args:
            message: The Telegram message object.
            book_title: The title of the book to search for.
            book_author: The author of the book to search for.
        """
        # Attempt to fetch book details from the API
        if self.book_bot.get_book_details_from_api(book_title, book_author):
            self.share_book_details_from_api_in_chat(message)
        else:
            # Inform user if book details not found
            self.bot.send_message(message.chat.id,
                                  "Sorry !! I could not found the book you were searching for. Please check the details again.")

    def share_book_details_from_api_in_chat(self, message: telebot.types.Message):
        """
        Shares the fetched book from API details to the Telegram chat. Reply Markup gives the user option to confirm the
        book details of fetch next one.

        Args:
            message: The Telegram message object.
        """
        # Check if book cover is available
        if self.book_bot.book_cover:
            self.bot.send_photo(message.chat.id, self.book_bot.book_cover, caption=self.book_bot.book_caption,
                                reply_markup=self.telegram_bot.new_book_markup)
        else:
            # Send message without cover image if not available
            self.bot.send_message(message.chat.id, self.book_bot.book_caption,
                                  reply_markup=self.telegram_bot.new_book_markup)

    def share_book_details_from_database_(self, message: telebot.types.Message):
        """
        Shares the book details retrieved from the database with the user in the Telegram chat.

        Args:
            message: The Telegram message object.
        """
        # if self.book_bot.book_cover:
        #     # Send photo with caption if cover image available
        #     self.bot.send_photo(message.chat.id, self.book_bot.book_cover, caption=self.book_bot.complete_book_details)
        # else:
        #     # Send message without cover image if not available
        #     self.bot.send_message(message.chat.id, self.book_bot.complete_book_details)
        if self.book_bot.book_cover:
            self.bot.send_photo(message.chat.id, self.book_bot.book_cover, caption=self.book_bot.complete_book_details)
        else:
            self.bot.send_message(message.chat.id, self.book_bot.complete_book_details)
        self.retrieve_book_status(message)

    def share_book_info_for_approval_and_edit(self, message: telebot.types.Message):
        """
        Sends a confirmation message to the user with the fetched book details and a reply markup for further actions.

        Args:
            message: The Telegram message object.
        """
        self.bot.send_photo(message.chat.id, self.book_bot.book_cover, caption=self.book_bot.complete_book_details,
                            reply_markup=self.telegram_bot.confirm_book_markup)

    def check_total_pages_count(self, message: telebot.types.Message):
        """
        Checks if the book's total page count is available. If not, prompts the user to input it manually.

        Args:
            message: The Telegram message object.
        """
        self.bot.send_message(message.chat.id, "I couldn't get total number of pages. Can you please enter that.")
        self.bot.register_next_step_handler(message, self.enter_total_pages_if_empty)

    def enter_total_pages_if_empty(self, message: telebot.types.Message):
        """
        Handles user input for the book's total page count and updates the stored book details.

        Args:
            message: The Telegram message object containing the user-provided page count.
        """
        if message.text.isdigit() and int(message.text) > 0:
            self.book_bot.book_total_page_count = message.text
            self.share_book_info_for_approval_and_edit(message)
        else:
            self.check_total_pages_count(message)

    def change_book_genre(self, message: telebot.types.Message) -> None:
        """
        Updates the book's genre with the user-provided input and re-displays the confirmation message.

        Args:
            message: The Telegram message object containing the new genre.
        """
        new_genre = message.text
        setattr(self.book_bot, "book_genre", new_genre)
        self.share_book_info_for_approval_and_edit(message)

    def change_book_language(self, message: telebot.types.Message) -> None:
        """
        Updates the book's language with the user-provided input and re-displays the confirmation message.

        Args:
            message: The Telegram message object containing the new language.
        """

        new_language = message.text
        setattr(self.book_bot, "book_language", new_language)
        self.share_book_info_for_approval_and_edit(message)

    # DATABASE RELATED FUNCTIONS

    def calculate_reading_speed(self) -> int:
        """
        Calculates the user's reading speed based on the time taken to read a pre-defined paragraph.

        Returns:
            int: The user's reading speed in words per minute.
        """
        # Calculate total reading time in minutes
        total_mins = round((self.calc_reading_speed_end_time - self.calc_reading_speed_start_time) / 60, 2)

        # Calculate reading speed (words per minute)
        reading_speed = self.large_texts.total_words_reading_speed_paragraph / total_mins

        # Converts reading speed to integer and returns it
        return int(reading_speed)

    def insert_book_status(self, message):
        if not self.book_database.insert_book_status(self.current_user_id, self.current_book_title,
                                                     self.current_book_status):
            self.bot.send_message(message.chat.id, "Sorry There was an error. Please Try Again")
        else:
            self.update_reading_time_left(message)

    def update_reading_time_left(self, message):
        if not self.book_database.update_reading_time_left(self.current_user_id, self.current_book_title):
            self.bot.send_message(message.chat.id, "Sorry There was an Error.")
        else:
            self.process_book_status(message)

    def retrieve_book_status(self, message: telebot.types.Message):
        print(self.current_book_status)
        self.retrieved_book_status = self.book_database.retrieve_book_status_if_exists(self.current_user_id,
                                                                                       self.current_book_title)

    def process_book_status(self, message):
        self.retrieve_book_status(message)
        if self.current_book_status == CURRENTLY_READING:
            self.process_currently_reading_book(message)
        elif self.current_book_status == COMPLETED:
            self.process_currently_reading_book(message)
        elif self.current_book_status == CURRENTLY_READING:
            self.process_currently_reading_book(message)

    def process_currently_reading_book(self, message):
        reading_time_left = self.retrieve_and_convert_reading_time_left()
        self.bot.send_message(message.chat.id, f"Time left to complete the book {reading_time_left}")
        total_pages_read = self.book_database.retrieve_pages_read(self.current_user_id, self.current_book_title)
        if total_pages_read:
            self.bot.send_message(message.chat.id,
                                  f"Wow !! you have already read {total_pages_read}. How many pages more have you read ?")
        else:
            self.bot.send_message(message.chat.id, f"How Many pages have you read?")
        self.bot.register_next_step_handler(message, self.update_pages_read)

    def update_pages_read(self, message):
        pages_read_today = message.text
        if pages_read_today.isdigit() and int(pages_read_today) > 0:
            pages_read_today = int(pages_read_today)
            total_pages_read = self.book_database.retrieve_pages_read(self.current_user_id, self.current_book_title)
            total_pages = self.book_database.retrieve_total_pages(self.current_book_title)
            if total_pages_read + pages_read_today >= total_pages:
                self.bot.send_message(message.chat.id, "Congratulations you have finsihed the book")
            else:
                if self.book_database.update_pages_read(self.current_user_id, self.current_book_title,
                                                        int(pages_read_today)):
                    total_pages_read = self.book_database.retrieve_pages_read(self.current_user_id,
                                                                              self.current_book_title)
                    reading_time_left = self.retrieve_and_convert_reading_time_left()
                    self.bot.send_message(message.chat.id,
                                          f"You have read {total_pages_read} out of {total_pages}. Total time left in finishing the book {reading_time_left}")
                else:
                    self.bot.send_message(message.chat.id, "SORRY ERROR")
        else:
            self.bot.send_message(message.chat.id, "Please enter number of pages read:")
            self.bot.register_next_step_handler(message, self.update_pages_read)

    def process_completed_books(self, message):
        ...

    def retrieve_and_convert_reading_time_left(self):
        """
        Converts minutes to a string representing hours and minutes format.

        Args:
          minutes: The number of minutes to convert.

        Returns:
          str: A string representing the time in hours and minutes format.
        """
        total_minutes_left = self.book_database.retrieve_reading_time_left(self.current_user_id,
                                                                           self.current_book_title)
        hours = int(total_minutes_left / 60)
        minutes = int(total_minutes_left % 60)
        return f"{hours} hours and {minutes} minutes"

    def chat(self):
        """
        Handles all incoming messages and callback handlers.

        Args:
            self (ChatBot): Instance of the ChatBot class.

        Returns:
            None
        """

        @self.bot.message_handler(commands=["start"])
        def command_start(message: telebot.types.Message) -> None:
            """
            Handles the `/start` command and related greeting messages.

            Args:
                message (telebot.types.Message): Incoming Telegram message object.

            Returns:
                None
            """
            self.save_username_and_id_db(message)
            self.send_greeting_message(message)

        @self.bot.message_handler(commands=["calculate_reading_speed"])
        def command_calc_reading_speed(message: telebot.types.Message) -> None:
            """
            Initiates the reading speed calculation process.

            This function sends a message to the user instructing them to read a paragraph and
            click on "Done" when finished.

            Args:
                message (telebot.types.Message): Incoming Telegram message object.

            Returns:
                None
            """
            # Send initial instruction message
            self.current_user_id = message.from_user.id
            self.bot.send_message(message.chat.id,
                                  "Please read the following paragraph and click on Done when you have finished reading.")

            # Wait for 5 seconds to allow user to read instructions
            time.sleep(5)

            self.calc_reading_speed_start_time = time.time()
            # Send reading speed paragraph and attach Done Reading button
            self.bot.send_message(message.chat.id, self.large_texts.reading_speed_paragraph,
                                  reply_markup=self.telegram_bot.done_reading_button)

        @self.bot.callback_query_handler(lambda query: query.data in ["reading_done"])
        def callback_calc_reading_speed(query: telebot.types.CallbackQuery) -> None:
            """
            Calculates and updates the user's reading speed based on the "Done Reading" button click.

            This function is triggered when the user clicks the "Done Reading" button after completing the reading speed test.
            It retrieves the user's Telegram ID, calculates their reading speed based on the time taken,
            and updates the user's reading speed in the database if successful.

            Args:
                query (telebot.types.CallbackQuery): Incoming Telegram callback query object.

            Returns:
                None
            """
            self.current_user_id = query.from_user.id
            # Record the end time of the reading speed test
            self.calc_reading_speed_end_time = time.time()

            # Get the user's Telegram ID from the callback query
            telegram_id = self.get_telegram_id(query)

            # Calculate the user's reading speed
            reading_speed = self.calculate_reading_speed()

            # Update the user's reading speed in the database
            if self.book_database.update_user_reading_speed(telegram_id, reading_speed):
                # Inform the user about successful update
                self.bot.send_message(query.message.chat.id,
                                      f"Your new reading speed is {reading_speed} WPM. It has been saved.")
            else:
                # Inform the user about failure to update
                self.bot.send_message(query.message.chat.id,
                                      "Sorry! Your reading speed could not be updated. Please Try Again")

        @self.bot.message_handler(regexp=self.books_chat_patterns["reading_a_book"])
        def regex_reading_a_book(message: telebot.types.Message) -> None:
            """
            Handles messages that indicate the user is reading a book.

            This function extracts the book title from the message text using regular expression.
            If the title is successfully extracted, it is stored in the `self.current_book_title` attribute.
            Otherwise, a message is sent to the user requesting the book title directly

            Args:
                message (telebot.types.Message): Incoming Telegram message object.

            Returns:
                None
            """
            self.current_user_id = message.from_user.id
            self.current_book_status = CURRENTLY_READING
            # Extract book title from message text
            sentence = message.text
            self.extract_book_title_from_regex(message, "reading_a_book", sentence)
            self.process_book_title_and_fetch_details(message)

        #
        # @self.bot.message_handler(regexp=self.books_chat_patterns["book_finished"])
        # def regex_finished_a_book(message: telebot.types.Message) -> None:
        #     self.current_book_status = COMPLETED
        #
        # @self.bot.message_handler(regexp=self.books_chat_patterns["wishlist_book"])
        # def regex_wishlist_book(message: telebot.types.Message) -> None:
        #     self.current_book_status = WISHLIST

        @self.bot.message_handler(commands=["readingabook"])
        def command_reading_a_book(message: telebot.types.Message) -> None:
            """
            Handles the "/readingabook" command and prompts the user for the book title.

            Args:
                message (telebot.types.Message): Incoming Telegram message object.

            Returns:
                None
            """
            self.current_user_id = message.from_user.id
            self.current_book_status = CURRENTLY_READING
            self.process_book_info_directly = True
            self.extract_book_title_from_regex(message)

        @self.bot.callback_query_handler(lambda query: query.data in ["confirm_book_details", "get_next_book_details"])
        def new_books_handler(query):
            """
            Handles user interactions with the "confirm_book_details" and "get_next_book_details" buttons in the Telegram chat.

            Args:
                query: The Telegram callback query object.
            """
            # Delete previous message containing book details
            self.current_user_id = query.from_user.id
            self.bot.delete_message(query.message.chat.id, query.message.id)

            # Handle confirmation button
            if query.data == "confirm_book_details":
                # Prompt for total pages if not available
                if self.book_bot.book_total_page_count is None or self.book_bot.book_total_page_count == 0:
                    self.check_total_pages_count(query.message)
                else:
                    # Confirm and edit book details if total pages available
                    self.share_book_info_for_approval_and_edit(query.message)
            elif query.data == "get_next_book_details":
                # Handle get next book button
                self.retrieve_book_data_using_api(query.message, self.current_book_title, self.current_book_author)

        @self.bot.callback_query_handler(
            lambda query: query.data in ["change_genre", "change_language", "no_change_req"])
        def confirm_and_insert_new_book(query):
            self.current_user_id = query.from_user.id
            self.bot.edit_message_reply_markup(query.message.chat.id, query.message.id, reply_markup=[])
            if query.data == "no_change_req":
                self.current_book_title = self.book_bot.book_title
                if self.book_database.insert_book_details(self.book_bot):
                    self.insert_book_status(query.message)
                else:
                    self.bot.send_message(query.message.chat.id,
                                          "I am sorry!\nThere was an error while saving book details. Please Try Again.")
            elif query.data == "change_genre":
                self.bot.send_message(query.message.chat.id, "Please enter genre.")
                self.bot.register_next_step_handler(query.message, self.change_book_genre)
            elif query.data == "change_language":
                self.bot.register_next_step_handler(query.message, self.change_book_language)

        self.bot.infinity_polling()


cb = ChatBot()
cb.chat()
