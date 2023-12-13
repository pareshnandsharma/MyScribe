import requests
from book_webscraping import BookWebScraping


class BookApi:
    API = "AIzaSyB0_24AJ9EPevq8PYrjua-E8PTFHwoKcWE"
    URL = "https://www.googleapis.com/books/v1/volumes"

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
