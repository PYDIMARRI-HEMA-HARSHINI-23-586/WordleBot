import requests
import random
import logging

# --- Constants ---
WORD_LIST_FILE = "5words.txt"
API_BASE_URL = "https://wordle.we4shakthi.in/game"
PLAYER_NAME = "Hema"
WORD_LENGTH = 5
MAX_ATTEMPTS = 6
OPTIMAL_FIRST_GUESS = "salet"

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WordleAPIError(Exception):
    """Custom exception for API related errors."""
    pass

class WordleAPI:
    SESSION = requests.Session()

    @staticmethod
    def _post_request(endpoint, payload):
        """Helper method for making POST requests with error handling."""
        url = f"{API_BASE_URL}/{endpoint}"
        try:
            response = WordleAPI.SESSION.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logging.error(f"Request to {url} timed out.")
            raise WordleAPIError(f"Request timed out when connecting to API endpoint: {endpoint}")
        except requests.exceptions.RequestException as e:
            logging.error(f"API request to {url} failed: {e}")
            raise WordleAPIError(f"Failed to connect to Wordle API at endpoint: {endpoint}") from e

    @staticmethod
    def register(player_name=PLAYER_NAME):
        """Registers a player and returns their unique game ID."""
        payload = {"mode": "wordle", "name": player_name}
        response_data = WordleAPI._post_request("register", payload)
        player_id = response_data.get("id")
        if player_id:
            logging.info(f"Registered player '{player_name}' with ID: {player_id}")
        else:
            logging.error("Registration failed: No player ID received.")
            raise WordleAPIError("Registration failed: No player ID in response.")
        return player_id

    @staticmethod
    def create_game(player_id):
        """Creates a new game for the player ID."""
        payload = {"id": player_id, "overwrite": True}
        response_data = WordleAPI._post_request("create", payload)
        logging.info(f"Created a new game for player ID: {player_id}. Response: {response_data}")
        return response_data

    @staticmethod
    def guess(player_id, guess_word):
        """Submits a guess and returns feedback from the API."""
        payload = {"guess": guess_word, "id": player_id}
        response_data = WordleAPI._post_request("guess", payload)
        feedback = response_data.get("feedback")
        logging.info(f"Guessed '{guess_word}', feedback: {feedback}")
        return feedback


class WordleBot:
    INSTRUCTIONS = "The bot will guess the word. Feedback is fetched from the API."

    def __init__(self, player_id):
        self.player_id = player_id
        self.possible_words = self._load_word_list()
        self.current_guess = OPTIMAL_FIRST_GUESS
        self.attempt_number = 0
        self.game_status = "PLAYING"
        self.last_feedback = ""

    @staticmethod
    def _load_word_list():
        """Loads 5-letter words from the word list file."""
        try:
            with open(WORD_LIST_FILE, "r", encoding="utf-8") as file:
                return [
                    word.strip().lower()
                    for word in file
                    if len(word.strip()) == WORD_LENGTH
                ]
        except FileNotFoundError:
            logging.error(f"Error: The word list file '{WORD_LIST_FILE}' was not found.")
            print(f"Error: The word list file '{WORD_LIST_FILE}' was not found. Please create it.")
            return []

    @staticmethod
    def _is_word_still_possible(word, guess, feedback):
        """Checks if a candidate word is valid given a guess and its feedback."""
        if word == guess:
            return False

        word_chars = list(word)
        guess_chars = list(guess)

        # First pass: Handle green matches ('G')
        for i in range(WORD_LENGTH):
            if feedback[i] == 'G':
                if word_chars[i] != guess_chars[i]:
                    return False
                word_chars[i] = None
                guess_chars[i] = None

        # Second pass: Handle yellow matches ('Y')
        for i in range(WORD_LENGTH):
            if feedback[i] == 'Y':
                if word_chars[i] == guess_chars[i]:
                    return False
                if guess_chars[i] not in word_chars:
                    return False
                word_chars[word_chars.index(guess_chars[i])] = None

        # Third pass: Handle grey matches ('R')
        for i in range(WORD_LENGTH):
            if feedback[i] == 'R':
                if guess_chars[i] in word_chars:
                    return False
        
        return True

    def filter_possible_words(self):
        """Filters the list of possible words based on the last feedback."""
        self.possible_words = [
            word for word in self.possible_words
            if self._is_word_still_possible(word, self.current_guess, self.last_feedback)
        ]
        logging.info(f"Words remaining: {len(self.possible_words)}")


    def make_guess(self):
        """Makes a guess using the API."""
        if not self.current_guess:
            self.game_status = "LOST"
            return
        
        try:
            self.last_feedback = WordleAPI.guess(self.player_id, self.current_guess)

            if not self.last_feedback or len(self.last_feedback) != WORD_LENGTH:
                logging.error("Received invalid feedback from API: '%s'. Stopping.", self.last_feedback)
                self.game_status = "ERROR"
                return

            if self.last_feedback == "G" * WORD_LENGTH:
                print(f"🎉 The bot guessed the word '{self.current_guess}' in {self.attempt_number + 1} attempts!")
                self.game_status = "WON"

        except WordleAPIError:
            self.game_status = "ERROR"


    def start_game(self):
        """Runs the bot's guessing loop."""
        print(self.INSTRUCTIONS)
        while self.game_status == "PLAYING" and self.attempt_number < MAX_ATTEMPTS:
            print(f"\n--- Attempt {self.attempt_number + 1}/{MAX_ATTEMPTS} ---")
            print(f"Bot is guessing: {self.current_guess.upper()}")

            self.make_guess()

            if self.game_status != "PLAYING":
                break

            self.filter_possible_words()

            if not self.possible_words:
                print("🤔 No more possible words. The bot is stumped.")
                self.game_status = "LOST"
                break
            
            self.current_guess = self.possible_words[0]
            self.attempt_number += 1

        if self.game_status == "PLAYING":
            print(f"❌ The bot couldn't guess the word in {MAX_ATTEMPTS} attempts.")
        elif self.game_status == "ERROR":
            print("An API error occurred. Please check the connection and logs.")


if __name__ == "__main__":
    try:
        player_id = WordleAPI.register()
        if player_id:
            WordleAPI.create_game(player_id)
            game_bot = WordleBot(player_id)
            game_bot.start_game()
    except WordleAPIError as e:
        print(f"\nCould not start the game due to an API error: {e}")
    except KeyboardInterrupt:
        print("\nGame interrupted by user.")
    except FileNotFoundError:
        print(f"Error: The word list file '{WORD_LIST_FILE}' was not found. Please create it.")