from typing import Optional

import requests
import bs4

# Google Custom Search Engine (CSE) credentials
GOOGLE_SE_ID = "1411e694edc7b4f63"
GOOGLE_SE_API = "AIzaSyA89Ic5eHaWXk6wzxvjT0BRl2o8Aar5GDE"
GOOGLE_SE_URL = "https://www.googleapis.com/customsearch/v1?[parameters]"


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

    def scrap_book_recommendations(self, book_title):
        """
        Scrapes book recommendations from Goodreads for a given book title, prioritizing ethical scraping practices.

        Args:
            book_title (str): The title of the book to get recommendations for.

        Returns:
            dict: A dictionary of recommended books and their authors, in the format {book_title: author_name}.
        """
        book_title.replace(" ", "+")
        query = f"books+similar+to+{book_title}+goodreads"
        # Set parameters for Google Custom Search Engine (CSE) API request
        url = f"https://google.com/search?q=books+similar+to+{book_title}+goodreads"

        # Fetch the URL data using requests.get(url),
        # store it in a variable, request_result.
        response = requests.get(url)

        soup = bs4.BeautifulSoup(response.text, "html.parser")
        links = soup.findAll('div', class_='kCrYT')

        # print(links)
        for link in links:
            try:
                url_link = link.a['href'][7:]
            except TypeError:
                continue
            else:
                break

        # print(url_link)
        request_result = requests.get(url_link)
        soup = bs4.BeautifulSoup(request_result.text,
                                 "html.parser")

        books = []
        authors = []
        recommended_books_and_authors = {}
        book_titles = soup.findAll('span', itemprop='name')[2:]
        for i in range(len(book_titles)):
            if i % 2 == 0:
                books.append(book_titles[i].text)
            else:
                authors.append(book_titles[i].text)

        # print("Books Recommendations : ")
        # print(books, authors)
        for book, author in zip(books, authors):
            recommended_books_and_authors[book] = author

        return recommended_books_and_authors
