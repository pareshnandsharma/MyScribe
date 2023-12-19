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
        if self.book_bot.book_cover:
            self.bot.send_photo(message.chat.id, self.book_bot.book_cover, caption=self.book_bot.complete_book_details)
        else:
            self.bot.send_message(message.chat.id, self.book_bot.complete_book_details)
        self.insert_book_status(message)

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
        if self.book_database.check_if_book_status_exists(self.current_user_id, self.current_book_title):
            self.process_book_status(message)
        else:
            if not self.book_database.insert_book_status(self.current_user_id, self.current_book_title,
                                                         self.current_book_status):
                self.bot.send_message(message.chat.id, "Sorry There was an error. Please Try Again")
            else:
                self.process_book_status(message)

    def update_reading_time_left(self, message):
        if not self.book_database.update_reading_time_left(self.current_user_id, self.current_book_title):
            self.bot.send_message(message.chat.id, "Sorry There was an Error.")

    # def retrieve_book_status(self, message: telebot.types.Message):
    #     self.retrieved_book_status = self.book_database.retrieve_book_status_if_exists(self.current_user_id, self.current_book_title)
    #     if not self.retrieved_book_status:
    #         self.insert_book_status(message)
    #     else:
    #         self.process_book_status(message)

    def process_book_status(self, message):
        if self.current_book_status == CURRENTLY_READING:
            self.process_currently_reading_book(message)
        elif self.current_book_status == COMPLETED:
            self.process_completed_books(message)
        elif self.current_book_status == WISHLIST:
            self.process_wishlisted_books(message)

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
                self.current_book_status = COMPLETED
                self.insert_book_status(message)
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
        self.book_database.update_pages_read(self.current_user_id, self.current_book_title, None)
        self.bot.send_message(message.chat.id,
                              f"Congratulations on finishing {self.current_book_title}. Please give it a rating "
                              f"from 1-5 (5 being the highest)")
        self.bot.register_next_step_handler(message, self.insert_book_rating)

    def insert_book_rating(self, message):
        book_rating = message.text
        if book_rating.isdigit():
            if 0 < int(book_rating) <= 5:
                if self.book_database.insert_book_rating(self.current_user_id, self.current_book_title, book_rating):
                    self.bot.send_message(message.chat.id,
                                          f"You rated {self.current_book_title} {book_rating} out of 5")
                else:
                    self.bot.send_message(message.chat.id, "There was an error please try again.")
            else:
                self.bot.send_message(message.chat.id, "Please give a rating between 1-5")
                self.bot.register_next_step_handler(message, self.insert_book_rating)
        else:
            self.bot.send_message(message.chat.id, "Please give a rating between 1-5")
            self.bot.register_next_step_handler(message, self.insert_book_rating)

    def process_wishlisted_books(self, message):
        self.bot.send_message(message.chat.id,
                              f"Congratulations!! You have successfully added {self.current_book_title} "
                              f"to your wishlist.")

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
        @self.bot.message_handler(regexp=self.books_chat_patterns["book_finished"])
        def regex_finished_a_book(message: telebot.types.Message) -> None:
            self.current_book_status = COMPLETED
            # Extract book title from message text
            sentence = message.text
            self.extract_book_title_from_regex(message, "reading_a_book", sentence)
            self.process_book_title_and_fetch_details(message)

        # @self.bot.message_handler(regexp=self.books_chat_patterns["wishlist_book"])
        # def regex_wishlist_book(message: telebot.types.Message) -> None:
        #     self.current_book_status = WISHLIST

        @self.bot.message_handler(regexp=self.books_chat_patterns["book_wishlist"])
        def regex_finished_a_book(message: telebot.types.Message) -> None:
            self.current_book_status = WISHLIST
            # Extract book title from message text
            sentence = message.text
            self.extract_book_title_from_regex(message, "book_wishlist", sentence)
            self.process_book_title_and_fetch_details(message)

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

        @self.bot.message_handler(commands=["finishedabook"])
        def command_reading_a_book(message: telebot.types.Message) -> None:
            """
            Handles the "/finishedabook" command and prompts the user for the book title.

            Args:
                message (telebot.types.Message): Incoming Telegram message object.

            Returns:
                None
            """
            self.current_user_id = message.from_user.id
            self.current_book_status = COMPLETED
            self.process_book_info_directly = True
            self.extract_book_title_from_regex(message)

        @self.bot.message_handler(commands=["wishlistabook"])
        def command_reading_a_book(message: telebot.types.Message) -> None:
            """
            Handles the "/wishlistabook" command and prompts the user for the book title.

            Args:
                message (telebot.types.Message): Incoming Telegram message object.

            Returns:
                None
            """
            self.current_user_id = message.from_user.id
            self.current_book_status = WISHLIST
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
