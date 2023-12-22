import os
import sqlite3
from typing import Optional
from dotenv import  load_dotenv

load_dotenv()

AVG_READING_SPEED = 300  # WPM (Words Per Minute)
AVG_WORDS_PER_PAGE = 300


class BookDatabase:
    """
    Facilitates interactions with the MyScribe's database.
    """
    def __init__(self):
        self.current_book_id = None
        self.conn = sqlite3.connect(os.getenv("MYSCRIBE_DATABASE"), check_same_thread=False)
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

    def insert_book_rating(self, telegram_id: int, book_title: str, book_rating):
        book_id = self.retrieve_book_id(book_title)
        try:
            self.cur.execute("UPDATE books_and_users SET rating  = ? WHERE user_id = ? AND book_id = ?", (book_rating, telegram_id, book_id))
            self.conn.commit()
        except sqlite3.Error as e:
            print(e)
            return False
        else:
            return True

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

    def fetch_book_details_from_db(self, book_title: str) -> dict | None:
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

    def retrieve_book_id(self, book_title: str) -> int | None:
        """
        Retrieves the unique ID of a book from the database, given its title.

        Args:
            book_title (str): The title of the book to search for.

        Returns:
            int | None: The ID of the book if found, otherwise None.
        """
        self.cur.execute("SELECT id FROM books WHERE title = ?", (book_title,))
        book_id = self.cur.fetchone()
        if book_id:
            print(book_id)
            return book_id[0]
        else:
            return None

    def retrieve_total_pages(self, book_title: str) -> int | None:
        """
        Retrieves the total number of pages for a specified book from the database.

        Args:
            book_title (str): The title of the book to search for.

        Returns:
            int | None: The total number of pages if found, otherwise None.
        """
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

    def check_if_book_status_exists(self, telegram_id: int, book_title: str) -> int | None:
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
            return True
        else:
            return False

    def retrieve_pages_read(self, telegram_id, book_title) -> int:
        """
        Retrieves the number of pages read by a user for a specific book from the database.

        Args:
            telegram_id (int): The unique identifier of the user in Telegram.
            book_title (str): The title of the book to retrieve reading progress for.

        Returns:
            int : The number of pages read if found, otherwise 0 to indicate no progress.
        """
        book_id = self.retrieve_book_id(book_title)
        self.cur.execute("SELECT pages_read FROM books_and_users WHERE user_id = ? AND book_id = ?",
                         (telegram_id, book_id))
        pages_read = self.cur.fetchone()[0]
        if pages_read:
            return int(pages_read)
        else:
            return 0

    def retrieve_reading_speed(self, telegram_id: int) -> int | None:
        """
        Retrieves the user's reading speed from the database.

        Args:
            telegram_id (int): The unique identifier of the user in Telegram.

        Returns:
            int | None: The user's reading speed if found, otherwise None.
        """
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

    def retrieve_reading_time_left(self, telegram_id: int, book_title: str) -> str:
        """
        Retrieves the user's estimated reading time left for a specific book from the database.
        If not found, updates the time left and then retrieves it.

        Args:
            telegram_id (int): The unique identifier of the user in Telegram.
            book_title (str): The title of the book to retrieve reading time left for.

        Returns:
            str | None: The estimated reading time left as a formatted string, otherwise None.
        """

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

    def update_reading_time_left(self, telegram_id: int, book_title: str) -> bool:
        """
        Updates the user's estimated reading time left for a specific book in the database.

        Args:
            telegram_id (int): The unique identifier of the user in Telegram.
            book_title (str): The title of the book to update the time left for.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
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

    def update_pages_read(self, telegram_id: int, book_title: str, pages_read: int) -> bool:
        """
        Updates the number of pages read by a user for a specific book in the database.

        Args:
            telegram_id (int): The unique identifier of the user in Telegram.
            book_title (str): The title of the book to update the pages read for.
            pages_read (int): The number of pages recently read by the user.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        book_id = self.retrieve_book_id(book_title)
        pages_read_yet = self.retrieve_pages_read(telegram_id, book_title)
        if pages_read:
            if pages_read_yet:
                total_pages = pages_read + int(pages_read_yet)
            else:
                total_pages = pages_read
            print(pages_read, pages_read_yet, total_pages)
            print(telegram_id, book_title)
        else:
            total_pages = None
        try:
            self.cur.execute("UPDATE books_and_users SET pages_read = ? WHERE user_id = ? AND book_id = ?",
                             (total_pages, telegram_id, book_id))
            self.conn.commit()
        except sqlite3.Error as e:
            return False
        else:
            self.update_reading_time_left(telegram_id, book_title)
            return True

    def calculate_reading_time_left(self, telegram_id: int, book_title: str) -> int:
        """
        Calculates the estimated reading time left for a user to finish a specific book.

        Args:
            telegram_id (int): The unique identifier of the user in Telegram.
            book_title (str): The title of the book to calculate the time left for.

        Returns:
            int: The estimated reading time left in minutes.
        """
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


    # def get_books_by_user_id(self, telegram_id: int) -> list:
    #     """
    #     Retrieves a list of all book IDs associated with a given user ID.
    #
    #     Args:
    #         telegram_id: The Telegram ID of the user.
    #
    #     Returns:
    #         A list of book IDs.
    #     """
    #     # Execute SQL query to retrieve book IDs And Save them to a list
    #     self.cur.execute("SELECT book_id from books_and_users WHERE user_id = ?", (telegram_id,))
    #     book_ids = [row[0] for row in self.cur]
    #
    #     return book_ids

    # def get_book_id_for_current_book(self, user_book_ids: list, book_title: str) -> int:
    #     if user_book_ids:
    #         for book_id in user_book_ids:
    #             self.cur.execute("SELECT * FROM books WHERE book_id = ? and title = ?", (book_id, book_title))
    #         return self.cur.rowco


