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

