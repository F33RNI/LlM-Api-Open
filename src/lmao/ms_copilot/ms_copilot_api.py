"""
Copyright (c) 2024 Fern Lane

This file is part of LlM-Api-Open (LMAO) project.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import imghdr
import json
import logging
import os
import subprocess
import tempfile
import time
import threading
from collections.abc import Generator
from typing import Any, Dict
import uuid

from markdownify import markdownify
import undetected_chromedriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException

from lmao.ms_copilot.proxy_extension import ProxyExtension


# JS script that injects pretty "large" JS file into <head></head>. Pass script's content as first argument
_INJECT_JS = """
const injectedScript = document.createElement("script"); 
injectedScript.type = "text/javascript"; 
injectedScript.text = arguments[0];
window.document.head.appendChild(injectedScript);
"""

# JS script that returns searchbox element or null without raising any error
_GET_SEARCHBOX = """
try {
    return document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-action-bar-main").shadowRoot.querySelector("div > div.main-container > div > div.input-row > cib-text-input").shadowRoot.querySelector("#searchbox");
} catch (error) {
    console.error(error);
}
return null;
"""

# JS script that returns submit button
_GET_SUBMIT_BUTTON = """
return document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-action-bar-main").shadowRoot.querySelector("div > div.main-container > div > div.bottom-controls > div.bottom-right-controls > div.control.submit > button");
"""

# JS script that returns input element that accepts images
_GET_IMAGE_INPUT = """
return document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-action-bar-main").shadowRoot.querySelectorAll("#vs_fileinput")[0]
"""

# JS script that pastes text into searchbox and returns searchbox itself
_PASTE_TEXT = """
const searchBox = document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-action-bar-main").shadowRoot.querySelector("div > div.main-container > div > div.input-row > cib-text-input").shadowRoot.querySelector("#searchbox");
searchBox.value = arguments[0];
return searchBox;
"""

# JS script that sets conversation style (WORKS ONLY ON NEW CONVERSATIONS). Pass 1 / 2 / 3 as argument
# (1 - Creative, 2 - Balanced, 3 - Precise)
_SET_STYLE = """
document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-conversation-main").shadowRoot.querySelector("#cib-chat-main > div > cib-welcome-container").shadowRoot.querySelector("div.controls > cib-tone-selector").shadowRoot.querySelector("#tone-options > li:nth-child(" + arguments[0] + ") > button").click();
"""

# JS script that returns "Stop responding" button
_STOP_RESPONDING = """
return document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-action-bar-main").shadowRoot.querySelector("div > cib-typing-indicator").shadowRoot.querySelector("#stop-responding-button");
"""

# "large" JS files
_CONVERSATION_MANAGE_JS = os.path.abspath(os.path.join(os.path.dirname(__file__), "conversationManage.js"))
_CONVERSATION_PARSER_JS = os.path.abspath(os.path.join(os.path.dirname(__file__), "conversationParser.js"))

# Maximum time to wait elements for load
_WAIT_TIMEOUT = 30

# Maximum timeout to wait for page to load
_PAGE_LOAD_WAIT_TIMEOUT = 15

# Number of retries to reload page if failed to load
_PAGE_LOAD_RETRIES = 2

# Yield response each >=100ms
_STREAM_READER_CYCLE = 0.1

# Auto-refresher 1 cycle minimal delay
_REFRESHER_CYCLE = 1.0

# Try to restart session in case of error during refreshing page
_RESTART_DELAY = 10

# How long to wait after pasting image (to make sure it's uploaded)
# TODO: track uploading spinner instead
_IMAGE_PASTE_DELAY = 3

# How long to wait after receiving message finish to make sure it's really finish (due to image generations)
_WAIT_AFTER_FINISH = 3


# Class to keep placeholder https://stackoverflow.com/a/21754294
class Default(dict):
    def __missing__(self, key):
        return key.join("{}")


def _parse_browser_version_major(browser_executable_path: str) -> int or None:
    """Tries to determine browser version by running browser_executable_path --version

    Args:
        browser_executable_path (str): path to browser executable

    Returns:
        int or None: parsed major version (ex. 122) or None in case of error
    """
    try:
        command = [browser_executable_path, "--version"]
        logging.info(f"Running {' '.join(command)}")
        version_str = (
            subprocess.run(command, stdout=subprocess.PIPE, timeout=10, check=True).stdout.decode("utf-8").split()
        )
        for version_str_part in version_str:
            version_parts = version_str_part.split(".")
            if len(version_parts) < 2:
                continue
            version = int(version_parts[0].strip())
            logging.info(f"Detected major version: {version}")
            return version
    except Exception as e:
        logging.error(f"Error trying to parse {browser_executable_path} version", exc_info=e)
    return None


class MSCopilotApi:
    def __init__(self, config: Dict) -> None:
        """Initializes MS Copilot module

        Args:
            config (Dict): module config
            Example:
            {
                "cookies_file": "MS_Copilot_cookies.json",
                "proxy": "",
                "base_url": "https://copilot.microsoft.com/",
                "headless": true,
                "chrome_options": [
                    "--disable-infobars",
                    "--disable-extensions",
                    "--ignore-ssl-errors=yes",
                    "--ignore-certificate-errors",
                    "--disable-default-apps",
                    "--disable-notifications",
                    "--disable-popup-window",
                    "--no-sandbox",
                    "--auto-open-devtools-for-tabs",
                    "--window-size=1920x960"
                ],
                "headless_mode": "old",
                "auto_refresh_interval": 120,
                "user_agent": ""
            }
        """
        self.config = config

        self.driver = None

        self._cookies = []

        self._conversation_id_last = ""
        self._conversation_new = False

        self._refresher_running_flag = None
        self._refresher_dont_refresh_flag = False
        self._refresher_timer = 0.0
        self._refresher_thread = None
        self._refresher_busy = False

        # Load "large" JS scripts
        logging.info(f"Loading {_CONVERSATION_MANAGE_JS}")
        with open(_CONVERSATION_MANAGE_JS, "r", encoding="utf-8") as file:
            self._conversation_manage_js = file.read()

        logging.info(f"Loading {_CONVERSATION_PARSER_JS}")
        with open(_CONVERSATION_PARSER_JS, "r", encoding="utf-8") as file:
            self._conversation_parser_js = file.read()

    def is_initialized(self) -> bool:
        """
        Returns:
            bool: True if session is started
        """
        return self.driver is not None

    def session_start(self, **kwargs) -> None:
        """Starts MS Copilot handler (opens browser, logs into account and starts auto-refresher)

        Raises:
            Exception: in case of existing session or any other error including timeout waiting for element to load
        """
        # Check if running
        if self.driver is not None:
            raise Exception("Error starting new session! Previous one is not closed! Please run session_close()")

        try:
            # Load cookies
            cookies_file = self.config.get("cookies_file")
            logging.info(f"Loading cookies from {cookies_file}")
            with open(cookies_file, "r", encoding="utf-8") as file:
                self._cookies = json.load(file)
                if self._cookies is None or not isinstance(self._cookies, list) or len(self._cookies) == 0:
                    raise Exception("Empty or wrong cookies file")
                logging.info(f"Loaded {len(self._cookies)} cookies")

            # Set driver options
            logging.info("Adding chrome options")
            chrome_options = undetected_chromedriver.ChromeOptions()

            # Hope this fill fix "Timed out receiving message from renderer" but it did't help :(
            # logging.info("Using eager page load strategy")
            # chrome_options.page_load_strategy = "eager"

            # Proxy
            if self.config.get("proxy_enabled"):
                proxy_host = self.config.get("proxy_host")
                proxy_port = int(self.config.get("proxy_port"))
                proxy_user = self.config.get("proxy_user", "")
                proxy_password = self.config.get("proxy_password", "")

                logging.info(f"Using proxy: {proxy_user}:{proxy_password}@{proxy_host}:{proxy_port}")
                proxy_extension = ProxyExtension(proxy_host, proxy_port, proxy_user, proxy_password)
                chrome_options.add_argument(f"--load-extension={proxy_extension.directory}")

            # Enable old headless mode (or other one)
            headless_mode = self.config.get("headless_mode")
            if self.config.get("headless") and headless_mode:
                chrome_options.add_argument(f"--headless={headless_mode}")

            # Other options
            for chrome_option in self.config.get("chrome_options"):
                chrome_options.add_argument(chrome_option)

            # User agent
            user_agent = self.config.get("user_agent")
            if user_agent:
                logging.info(f"Using user-agent: {user_agent}")
                chrome_options.add_argument(f"--user-agent={user_agent}")

            # Initialize chrome
            headless = self.config.get("headless")
            logging.info(f"Initializing driver{' in headless mode' if headless else ''}")

            # Find browser path
            browser_executable_path = self.config.get("browser_executable_path")
            if not self.config.get("browser_executable_path"):
                browser_executable_path = undetected_chromedriver.find_chrome_executable()
            logging.info(f"Browser executable path: {browser_executable_path}")

            # Check
            if not browser_executable_path:
                raise Exception("Unable to find browser executable path. Please specify it manually")

            # Find browser major version
            version_main = self.config.get("version_main_manual")
            if not version_main:
                version_main = _parse_browser_version_major(browser_executable_path)

            # Extract driver executable path from config
            driver_executable_path = self.config.get("driver_executable_path")
            if not driver_executable_path:
                driver_executable_path = None

            # Initialize browser
            self.driver = undetected_chromedriver.Chrome(
                browser_executable_path=browser_executable_path,
                driver_executable_path=driver_executable_path,
                version_main=version_main,
                options=chrome_options,
                headless=headless,
                enable_cdp_events=True,
                **kwargs,
            )

            # Add cookies
            logging.info(f"Trying to add {len(self._cookies)} cookies")

            # Enables network tracking so we may use Network.setCookie method
            self.driver.execute_cdp_cmd("Network.enable", {})

            for cookie in self._cookies:
                try:
                    # Add cookie
                    # self.driver.add_cookie(cookie)
                    self.driver.execute_cdp_cmd("Network.setCookie", cookie)
                except Exception:
                    logging.warning(f"Error adding cookie {cookie['name']}")

            # Disable network tracking
            self.driver.execute_cdp_cmd("Network.disable", {})

            # Load initial page
            base_url = self.config.get("base_url")
            if not self._load_or_refresh(base_url):
                raise Exception(f"Unable to load {base_url}")

            # Save cookies before starting refresher
            self.cookies_save()

            # Start auto-refresher if needed
            if self._refresher_thread is None and self.config.get("auto_refresh_interval") > 0:
                logging.info("Starting auto-refresher thread")
                self._refresher_running_flag = True
                self._refresher_dont_refresh_flag = False
                self._refresher_timer = time.time()
                self._refresher_thread = threading.Thread(target=self._refresher)
                self._refresher_thread.start()

        # WebDriverWait().until() timeout or other error
        except (TimeoutException, Exception) as e:
            # Try to close browser
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

            # Raise exception after
            raise e

    def prompt_send(
        self,
        prompt: str,
        image: bytes or None = None,
        conversation_id: str or None = None,
        style: str or None = None,
    ) -> str or None:
        """Sends prompt to MS Copilot

        Args:
            prompt (str): prompt text
            image (bytes or None, optional): image to attach to the prompt (will be saved into temp file)
            conversation_id (str or None, optional): existing conversation ID or None to create a new one
            style (str or None, optional): "creative" / "balanced" / "precise" (works only with new conversations)

        Raises:
            Exception: in case of no session or timeout waiting for element or other error

        Returns:
            str or None: conversation ID
        """
        if self.driver is None:
            raise Exception("No opened session! Please call session_start() first")

        # Pause auto-refresher
        self._refresher_pause_resume(pause=True)

        image_tempfile_name = None

        try:
            # Fix base url (remove ending slash)
            base_url = self.config.get("base_url").strip()
            while base_url.endswith("/"):
                base_url = base_url[:-1]

            # Load initial page
            base_url = self.config.get("base_url")
            if not self._load_or_refresh(base_url):
                raise Exception(f"Unable to load {base_url}")

            # Try to load conversation
            if conversation_id:
                if not self._conversation_manage("load", conversation_id, raise_on_error=False):
                    logging.warning(f"Unable to load conversation {conversation_id}. Creating a new one")
                    conversation_id = None

            # Check for disabled searchbox (usually caused by "Sorry, this conversation has reached its limit...")
            if not self.driver.execute_script(_GET_SEARCHBOX).is_enabled:
                logging.warning(f"Found disabled searchbox in conversation {conversation_id}. Limit reached?")
                logging.info("Creating a new conversation")
                conversation_id = None

                if not self._load_or_refresh(base_url):
                    raise Exception(f"Unable to load {base_url}")

            # Set style
            if style and not conversation_id:
                logging.info(f"Changing conversation style to {style}")
                if style == "creative":
                    style_int = 1
                elif style == "precise":
                    style_int = 3
                else:
                    style_int = 2
                self.driver.execute_script(_SET_STYLE, style_int)
                time.sleep(0.1)

            # Generate new conversation ID if needed
            self._conversation_new = False
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
                self._conversation_new = True

            # Save image
            if image is not None:
                image_format = imghdr.what(None, h=image)
                if not image_format:
                    raise Exception("Unable to detect image format")
                logging.info(f"Detected image format: {image_format}")

                logging.info("Creating temp file for image")
                image_tempfile = tempfile.NamedTemporaryFile(mode="w+b", suffix=f".{image_format}", delete=False)
                image_tempfile_name = image_tempfile.name
                logging.info(f"Saving image into {image_tempfile_name}")
                with image_tempfile as temp:
                    temp.write(image)
                    temp.flush()
                image_tempfile.close()

            # Paste image
            if image_tempfile_name:
                logging.info(f"Pasting {image_tempfile_name}")
                file_input = self.driver.execute_script(_GET_IMAGE_INPUT)
                file_input.send_keys(os.path.abspath(image_tempfile_name))
                logging.info(f"Waiting {_IMAGE_PASTE_DELAY} seconds to make sure it's uploaded")
                time.sleep(_IMAGE_PASTE_DELAY)

            # Paste text
            logging.info("Pasting text prompt into searchbox")
            searchbox = self.driver.execute_script(_PASTE_TEXT, prompt)
            time.sleep(0.1)
            searchbox.send_keys(Keys.SPACE)
            time.sleep(0.1)
            searchbox.send_keys(Keys.BACKSPACE)
            time.sleep(0.1)

            # Wait for submit button (just in case)
            if not self.driver.execute_script(_GET_SUBMIT_BUTTON).is_enabled:
                logging.info("Waiting for submit button to become available")
                time_start = time.time()
                while True:
                    if time.time() - time_start > _WAIT_TIMEOUT:
                        raise Exception("Timeout waiting for submit button to become available")

                    if self.driver.execute_script(_GET_SUBMIT_BUTTON).is_enabled:
                        logging.info("Submit button is now available")
                        break

                    time.sleep(0.1)

            # Count number of bot's responses
            bot_messages_len_start = self._conversation_parse("count")
            logging.info(f"Found {bot_messages_len_start} bot messages")

            # Submit
            logging.info("Clinking on submit button")
            self.driver.execute_script(_GET_SUBMIT_BUTTON).click()

            # Wait until bot starts responding
            logging.info("Waiting for bot to start responding")
            time_start = time.time()
            while True:
                if time.time() - time_start > _WAIT_TIMEOUT:
                    raise Exception("Timeout waiting for bot to start responding")

                bot_messages_len = self._conversation_parse("count")
                if bot_messages_len != bot_messages_len_start:
                    logging.info(f"Found {bot_messages_len - bot_messages_len_start} new bot's messages")
                    break

                time.sleep(0.1)

            # Check for captcha and try to solve it
            captcha_iframe = self._conversation_parse("captcha")
            if captcha_iframe:
                logging.warning("Found captcha. Trying to solve it")
                logging.info("Waiting 5 seconds for captcha to load")
                time.sleep(5)

                logging.info("Switching to the iframe")
                self.driver.switch_to.frame(captcha_iframe)
                time.sleep(1)

                logging.info("Retrieving child iframe and switching to it")
                WebDriverWait(self.driver, _WAIT_TIMEOUT).until(
                    expected_conditions.frame_to_be_available_and_switch_to_it(
                        (
                            By.CSS_SELECTOR,
                            "iframe[src^='https://challenges.cloudflare.com/cdn-cgi/challenge-platform']",
                        )
                    )
                )
                time.sleep(1)

                logging.info("Clicking on captcha")
                self.driver.execute_script("querySelector('#challenge-stage > div > label').click()")
                time.sleep(1)

                logging.info("Switching to the default content")
                self.driver.switch_to.default_content()

            # Wait extra 500ms (to make sure everything is loaded properly)
            time.sleep(0.5)

            # Save cookies
            self.cookies_save()

            # Save conversation ID for response_read_stream()
            self._conversation_id_last = conversation_id

            # Return new conversation ID
            return conversation_id

        # On error: resume refresher and re-raise error
        except Exception as e:
            self._refresher_pause_resume(pause=False, reset_time=True)
            raise e

        # Delete temp file
        finally:
            if image_tempfile_name:
                logging.info(f"Deleting {image_tempfile_name}")
                os.remove(image_tempfile_name)

    def response_read_stream(self, convert_to_markdown: bool = True) -> Generator[Dict]:
        """Reads response from MS Copilot

        Args:
            convert_to_markdown (bool, optional): True to convert result from HTML to Markdown. Defaults to True

        Raises:
            Exception: in case of no opened session, no valid assistant messages, timeout or any other error

        Yields:
            Generator[Dict]: {
                "finished": True if it's the last response, False if not,
                "conversation_id": ID of current conversation (from prompt_send),
                "response": "response as text (or meta response)",
                "images": ["array of image URL's"],
                "caption": "images caption",
                "attributions": [
                    {
                        "name": "name of attribution",
                        "url": "URL of attribution"
                    },
                    ...
                ],
                "suggestions": ["array of suggestions of the requests"]
            }
        """
        if self.driver is None:
            raise Exception("No opened session! Please call session_start() first")
        try:
            # Pause auto-refresher
            self._refresher_pause_resume(pause=True)

            # Generate until response finished and wait extra _WAIT_AFTER_FINISH seconds
            finished = False
            finished_timer = 0
            while not finished:
                # Retrieve data as JSON
                # See parseMessages() docs for more info
                response = dict(self._conversation_parse("parse"))

                # Check if finished
                finished_ = self._conversation_parse("finished")
                if isinstance(finished_, dict) and "error" in finished_:
                    logging.warning(f"Error checking finished state: {finished_['error']}")
                    finished_ = False

                # Reset timer
                if not finished_ and finished_timer != 0:
                    logging.info("Received non-finished flag. Resetting timer and waiting for finished flag again")
                    finished_timer = 0

                # Start timer
                if finished_ and finished_timer == 0:
                    logging.info(f"Received finished flag. Waiting extra {_WAIT_AFTER_FINISH}s")
                    finished_timer = time.time()

                # Done
                if finished_ and time.time() - finished_timer >= _WAIT_AFTER_FINISH:
                    logging.info(f"{_WAIT_AFTER_FINISH}s passed. Finishing")
                    finished = True

                # Not finished yet or we need to wait
                else:
                    finished = False

                response_parsed = {"finished": finished, "conversation_id": self._conversation_id_last}

                # Extract text and code blocks
                response_text = response.get("text")
                code_blocks = response.get("code_blocks")

                # Convert to markdown
                if response_text and convert_to_markdown:
                    try:

                        def _code_language_callback(element_) -> str or None:
                            """Extracts language name from lang attribute

                            Args:
                                element (bs4.element.Tag): <pre> tag

                            Returns:
                                str or None: language name if exists
                            """
                            if element_.find("code"):
                                languages_ = element_.find("code").get_attribute_list("lang")
                                return languages_[0] if len(languages_) != 0 else None
                            return None

                        # Convert to markdown with code blocks placeholders
                        response_text = markdownify(
                            response_text,
                            escape_asterisks=False,
                            escape_underscores=False,
                            code_language_callback=_code_language_callback,
                        )

                        # Restore code blocks
                        if code_blocks is not None:
                            response_text = response_text.format_map(Default(code_blocks))
                    except Exception as e:
                        logging.error(f"Error converting HTML to Markdown! {e}")

                # Fix no text by using meta or empty string
                if not response_text:
                    response_text = response.get("meta", "")

                response_parsed["response"] = response_text.strip()

                # Add image URLs
                if response.get("images") is not None:
                    response_parsed["images"] = response.get("images")

                # Add image caption
                if response.get("caption") is not None:
                    response_parsed["caption"] = response.get("caption")

                # Add attributions
                if response.get("attributions") is not None:
                    response_parsed["attributions"] = response.get("attributions")

                # Add suggestions
                suggestions = self._conversation_parse("suggestions")
                if len(suggestions) != 0:
                    response_parsed["suggestions"] = suggestions

                # Sleep a bit to prevent overloading
                time.sleep(_STREAM_READER_CYCLE)

                # Stream data as dictionary
                yield response_parsed

            # Done -> update cookies
            logging.info("Response finished")
            self.cookies_save()

        finally:
            # Try to rename conversation
            if self._conversation_new:
                time.sleep(1)
                self._conversation_manage("rename", self._conversation_id_last, raise_on_error=False)
                time.sleep(1)
                self._load_or_refresh()
            self._conversation_new = False

            # Resume refresher and reset it's timer
            self._refresher_pause_resume(pause=False, reset_time=True)

    def response_stop(self) -> None:
        """Clicks on Stop responding button and sleeps 1 extra second

        Raises:
            Exception: no opened session, no or disabled button
        """
        if self.driver is None:
            raise Exception("No opened session! Please call session_start() first")
        stop_btn = self.driver.execute_script(_STOP_RESPONDING)
        time.sleep(1)
        if stop_btn is None:
            raise Exception('No "Stop responding" button')
        if stop_btn.is_enabled:
            stop_btn.click()
        else:
            raise Exception("Stop responding button is not enabled")

    def conversation_delete(self, conversation_id: str) -> None:
        """Deletes conversation by searching it in side menu and clicking on Delete button

        Args:
            conversation_id (str): ID of conversation to delete or empty string ("") to delete the top one

        Raises:
            Exception: in case of no conversation, timeout or any other error
        """
        if self.driver is None:
            raise Exception("No opened session! Please call session_start() first")

        try:
            # Pause auto-refresher
            self._refresher_pause_resume(pause=True)

            # Delete conversation
            self._conversation_manage("delete", conversation_id, raise_on_error=True)

        finally:
            # Resume refresher and reset it's timer
            self._refresher_pause_resume(pause=False, reset_time=True)

    def session_close(self, from_refresher: bool = False) -> None:
        """Closes all browser instances

        Args:
            from_refresher (bool, optional): True to not stopping the refresher. Defaults to False

        Raises:
            Exception: no opened session or other exception during driver.quit()
        """
        if self.driver is None:
            raise Exception("No opened session! Please call session_start() first")

        # Stop refresher
        if not from_refresher:
            self._refresher_running_flag = False
            if self._refresher_thread is not None and self._refresher_thread.is_alive():
                logging.info("Joining refresher thread")
                self._refresher_thread.join()
            self._refresher_thread = None
            self._refresher_busy = False

            # Save cookies before exit
            try:
                self.cookies_save()
            except Exception as e:
                logging.warning(f"Cannot save cookies before closing browser: {e}")

        # Close browser
        logging.info("Closing browser")
        self.driver.quit()
        time.sleep(1)
        self.driver = None
        logging.info("Browser closed")

    def cookies_save(self) -> None:
        """Retrieves cookies from current session and updates existing one and save them to file"""
        if self.driver is None:
            raise Exception("No opened session! Please call session_start() first")

        cookies_new = self.driver.get_cookies()
        for cookie_new in cookies_new:
            try:
                # Search in existing cookies (last one)
                cookie_old_index = -1
                for i, cookie in enumerate(self._cookies):
                    if (
                        cookie["domain"] == cookie_new["domain"]
                        and cookie["name"] == cookie_new["name"]
                        and cookie["path"] == cookie_new["path"]
                        and cookie["value"] != cookie_new["value"]
                    ):
                        cookie_old_index = i

                # Update cookie value
                if cookie_old_index != -1:
                    self._cookies[cookie_old_index]["value"] = cookie_new["value"]
                    logging.info(f"Value of cookie {cookie_new['name']} updated")

            except Exception as e:
                logging.warning(f"Error updating {cookie_new.get('name')} value: {e}")

        # Save to the file
        cookies_file = self.config.get("cookies_file")
        with open(cookies_file, "w+", encoding="utf-8") as file:
            logging.info(f"Saving cookies to {cookies_file}")
            json.dump(self._cookies, file, ensure_ascii=False, indent=4)

    def _conversation_manage(self, action: str, conversation_id: str, raise_on_error: bool) -> bool:
        """Loads conversation / deletes conversation or renames last conversation to conversation_id

        Args:
            action (str): "load" or "delete" or "rename"
            conversation_id (str): unique conversation ID
            raise_on_error (bool): True to raise exception in case of error

        Raises:
            Exception: in case of error if raise_on_error is True

        Returns:
            bool: True if successful, False if not
        """
        logging.info(f"Trying to {action} conversation")
        try:
            self.driver.set_script_timeout(_WAIT_TIMEOUT)
            conversation_id_ = self.driver.execute_async_script(self._conversation_manage_js, action, conversation_id)
            if conversation_id_ is None:
                raise Exception(f"Unable to {action} conversation to {conversation_id}")
            elif conversation_id_ != conversation_id:
                raise Exception(str(conversation_id_))
            else:
                logging.info(f'"Conversation {action}" finished successfully')
            time.sleep(1)
            return True
        except Exception as e:
            if raise_on_error:
                raise e
            else:
                logging.error(f"Unable to {action} conversation: {e}")

        return False

    def _conversation_parse(self, action: str) -> Any:
        """Executes actionHandle() function from conversationParser and injects it's JS if needed

        Args:
            action (str): "captcha", "count", "parse", "suggestions" or "finished"

        Returns:
            Any: action result or { "error": "exception text" }
        """
        # Check if conversationParser.js is injected
        is_injected = False
        try:
            is_injected = self.driver.execute_script("return isParseInjected();")
        except:
            pass

        # Inject JS
        if not is_injected:
            logging.warning("conversationParser is not injected. Injecting it")
            self.driver.execute_script(_INJECT_JS, self._conversation_parser_js)
            logging.info(f"Injected? {self.driver.execute_script('return isParseInjected();')}")

        # Execute script and return result
        return self.driver.execute_script(f"return actionHandle('{action}');")

    def _load_or_refresh(self, url: str or None = None, restart_session_on_error: bool = True) -> bool:
        """Tries to load or refresh page and inject JS scripts without raising any error

        Args:
            url (str or None, optional): URL to load or None to refresh. Defaults to None
            restart_session_on_error (bool, optional): call session_close() and session_start() on error

        Returns:
            bool: True if loaded successfully, False if not
        """
        # Wait a bit just in case
        time.sleep(0.5)

        retries_counter = 0
        while True:
            try:
                # Set timeout
                self.driver.set_page_load_timeout(_PAGE_LOAD_WAIT_TIMEOUT)

                # Load if url provided, refresh otherwise
                if url:
                    logging.info(f"Loading {url}")
                    self.driver.get(url)
                else:
                    logging.info("Refreshing current page")
                    self.driver.refresh()

                # Wait for a searchbox
                self._wait_for_searchbox()

                # Wait for page to stop loading by counting messages
                logging.info("Waiting for page to stop loading")
                time_start = time.time()
                while True:
                    if time.time() - time_start > _WAIT_TIMEOUT:
                        raise Exception("Timeout waiting for page to stop loading")

                    bot_messages_len_start = self._conversation_parse("count")
                    time.sleep(0.25)
                    bot_messages_len = self._conversation_parse("count")
                    time.sleep(0.25)
                    if bot_messages_len == bot_messages_len_start:
                        logging.info("Page loaded successfully")
                        break

                # Seems OK
                return True

            except Exception as e:
                logging.error(f"Error loading page: {e}")
                retries_counter += 1
                if retries_counter > _PAGE_LOAD_RETRIES:
                    logging.warning(f"No more retries ({retries_counter} / {_PAGE_LOAD_RETRIES}) :(")
                    return False

                if restart_session_on_error:
                    logging.info("Restarting session")
                    self.session_close(from_refresher=True)
                    time.sleep(1)
                    self.session_start()
                    time.sleep(1)

                logging.warning(f"Trying to load page again. Retries: {retries_counter} / {_PAGE_LOAD_RETRIES}")

            # Wait a bit before next cycle
            time.sleep(1)

    def _wait_for_searchbox(self) -> None:
        """Waits for searchbox textarea to become visible and 1 extra second before and after to make sure it's loaded

        Raises:
            Exception: in case of timeout
        """
        logging.info("Waiting for page to load (waiting for searchbox textarea element)")
        time_started = time.time()
        time.sleep(1)
        while True:
            if time.time() - time_started >= _WAIT_TIMEOUT:
                raise Exception("Timeout waiting for searchbox textarea to load")
            if self.driver.execute_script(_GET_SEARCHBOX):
                break
            time.sleep(0.1)
        time.sleep(1)
        logging.info("Page loaded")

    def _refresher_pause_resume(self, pause: bool, reset_time: bool = False) -> None:
        """Pauses or resumes auto-refresher

        Args:
            pause (bool): True to pause auto-refresher
            reset_time (bool, optional): True to update refresher timer. Defaults to False.
        """
        # Pause
        if pause:
            if self._refresher_busy:
                logging.info("Waiting for refresher to finish")
                while self._refresher_busy:
                    time.sleep(1)
            logging.info("Pausing refresher")
            self._refresher_dont_refresh_flag = True

        # Resume
        else:
            logging.info("Resuming refresher")
            self._refresher_dont_refresh_flag = False

        # Reset timer
        if reset_time:
            self._refresher_timer = time.time()

    def _refresher(self) -> None:
        """Automatically refreshes browser Page every self.auto_refresh_interval seconds and saves cookies
        (should be background thread)
        Set self._refresher_dont_refresh_flag to True to pause refresher
        Set self._refresher_timer to time.time() to extend time before refresh
        Set self.auto_refresh_interval to 0 or self._refresher_running_flag to False to stop it
        """
        if self._refresher_running_flag:
            logging.info("Auto-refresher thread started")
        while self._refresher_running_flag:
            try:
                # Clear busy flag
                self._refresher_busy = False

                # Check if turned off
                auto_refresh_interval = self.config.get("auto_refresh_interval")
                if auto_refresh_interval <= 0:
                    logging.warning("auto_refresh_interval <= 0. Stopping auto-refresher")
                    self._refresher_running_flag = False
                    break

                # It's time to refresh
                time_current = time.time()
                if (
                    self.driver
                    and not self._refresher_dont_refresh_flag
                    and time_current - self._refresher_timer > auto_refresh_interval
                ):
                    # Set busy flag
                    self._refresher_busy = True

                    # Refresh page
                    self._refresher_timer = time_current
                    if not self._load_or_refresh():
                        raise Exception("Unable to auto-refresh page")

                    # Save cookies
                    self.cookies_save()

                # Clear busy flag
                self._refresher_busy = False

                # Sleep before next cycle (and listen to ctrl+c, sigkill and all this stuff)
                time.sleep(_REFRESHER_CYCLE)

            # Catch ctrl+c, sigkill and all this stuff
            except (SystemExit, KeyboardInterrupt):
                logging.warning("Interrupted! Stopping auto-refresher")
                break

            # Catch and handle error during refreshing page
            except Exception as e:
                logging.error("Error refreshing page", exc_info=e)

                # Close session
                logging.warning("Trying to close session")
                try:
                    self.session_close(from_refresher=True)
                except Exception as e_:
                    logging.error("Error closing session", exc_info=e_)

                # Restart it
                logging.warning(f"Trying to restart session after {_RESTART_DELAY}")
                try:
                    time.sleep(_RESTART_DELAY)
                except (SystemExit, KeyboardInterrupt):
                    logging.warning("Interrupted! Stopping auto-refresher")
                    break
                logging.warning("Trying to restart session")
                try:
                    self.session_start()
                except Exception as e_:
                    logging.error("Error restarting session", exc_info=e_)

        # Stopped
        logging.warning("Auto-refresher stopped")
        self._refresher_thread = None
        self._refresher_busy = False
