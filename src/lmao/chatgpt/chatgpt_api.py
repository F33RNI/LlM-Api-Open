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

import gc
import json
import logging
import os
import subprocess
import threading
import time
from collections.abc import Generator
from typing import Any, Dict

import undetected_chromedriver
from markdownify import markdownify
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from lmao.chatgpt.proxy_extension import ProxyExtension

# JS script that injects "large" JS file into <head></head>. Pass script's content as first argument
_INJECT_JS = """
const injectedScript = document.createElement("script"); 
injectedScript.type = "text/javascript"; 
injectedScript.text = arguments[0];
window.document.head.appendChild(injectedScript);
"""

# JS script that clicks on scroll to bottom button
_SCROLL_TO_BOTTOM = """
const scrollButtons = document.querySelectorAll("button.cursor-pointer.absolute");
if (scrollButtons.length > 0)
    scrollButtons[0].click();
"""

# JS script to paste text into textarea
_TYPE_INTO_TEXTAREA = """
let element = arguments[0], text = arguments[1];
if (!("value" in element))
    throw new Error("Expected an <input> or <textarea>");
element.focus();
element.value = text;
element.innerHTML = text;
element.dispatchEvent(new Event("change"));
"""

# JS script to move cursor to the end of textarea
_MOVE_CURSOR_TEXTAREA = """
let element = arguments[0];
if (!("value" in element))
    throw new Error("Expected an <input> or <textarea>");
element.selectionStart = element.value.length;
"""

# JS script to get last assistant message ID
_ASSISTANT_GET_LAST_MESSAGE_ID = """
try {
    const assistantMessages = document.querySelectorAll("[data-message-author-role='assistant']");
    if (assistantMessages.length > 0)
        return [...assistantMessages].at(-1).getAttribute("data-message-id");
} catch (e) { }
return null;
"""

# JS script to get last conversation ID
_GET_LAST_CONVERSATION_ID = """
try {
    const conversationsGroups = document.getElementsByTagName("ol");
    if (conversationsGroups.length > 0) {
        conversationsGroup = [...document.getElementsByTagName("ol")].at(0);
        conversationID = [...conversationsGroup.firstChild.getElementsByTagName("a")[0].href.split("c/")].at(-1);
        return conversationID;
    }
} catch (e) { }
return null;
"""

# JS script that checks if current conversation exists or not by checking for toast message
_CONVERSATION_EXISTS = """
const toastRoots = document.getElementsByClassName("toast-root");
if (toastRoots.length > 0 && toastRoots[0].innerText.includes("Unable to load"))
    return false;
return true;
"""

# JS script that checks for Regenerate button due to "There was an error generating a response" and presses on it
_CONVERSATION_ERROR_RESOLVE = """
const buttons = document.getElementsByTagName("button");
for (const button of buttons) {
    if (button.innerText == "Regenerate") {
        button.focus();
        button.click();
        return true;
    }
}
return false;
"""

# JS script that cancels assistant response (clicks on Stop generating button)
_RESPONSE_STOP = """
const buttons = document.getElementsByTagName("button");
for (const button of buttons) {
    if (button.hasAttribute("aria-label") && button.getAttribute("aria-label") === "Stop generating")
        button.click();
}
"""


# "large" JS files
_ASSISTANT_GET_LAST_MESSAGE_JS = os.path.abspath(os.path.join(os.path.dirname(__file__), "assistantGetLastMessage.js"))
_CONVERSATION_SEARCH_JS = os.path.abspath(os.path.join(os.path.dirname(__file__), "conversationSearch.js"))

# Maximum time to wait elements for load
_WAIT_TIMEOUT = 30

# Try to find start of response each >=100ms
_WAITER_CYCLE = 0.1

# Yield response each >=100ms
_STREAM_READER_CYCLE = 0.1

# Auto-refresher 1 cycle minimal delay
_REFRESHER_CYCLE = 1.0

# Try to restart session in case of error during refreshing page
_RESTART_DELAY = 10


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


class ChatGPTApi:
    def __init__(self, config: Dict) -> None:
        """Initializes ChatGpt module

        Args:
            config (Dict): module config
            Example:
            {
                "cookies_file": "ChatGPT_cookies.json",
                "proxy": "",
                "base_url": "https://chat.openai.com/",
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

        self._refresher_running_flag = None
        self._refresher_dont_refresh_flag = False
        self._refresher_timer = 0.0
        self._refresher_thread = None
        self._refresher_busy = False

        # Load "large" JS scripts
        logging.info(f"Loading {_ASSISTANT_GET_LAST_MESSAGE_JS}")
        with open(_ASSISTANT_GET_LAST_MESSAGE_JS, "r", encoding="utf-8") as file:
            self._assistant_get_last_message_js = file.read()

        logging.info(f"Loading {_CONVERSATION_SEARCH_JS}")
        with open(_CONVERSATION_SEARCH_JS, "r", encoding="utf-8") as file:
            self._conversation_search_js = file.read()

    def is_initialized(self) -> bool:
        """
        Returns:
            bool: True if session is started
        """
        return self.driver is not None

    def session_start(self, **kwargs) -> None:
        """Starts ChatGPT handler (opens browser, logs into account and starts auto-refresher)

        Raises:
            Exception: in case of existing session or any other error including timeout waiting for element to load
        """
        # Check if running
        if self.driver is not None:
            raise Exception("Error starting new session! Previous one is not closed! Please run session_close()")

        try:
            # Load cookies
            cookies_file = self.config.get("cookies_file")
            if cookies_file and os.path.exists(cookies_file):
                logging.info(f"Loading cookies from {cookies_file}")
                with open(cookies_file, "r", encoding="utf-8") as file:
                    self._cookies = json.load(file)
                    if self._cookies is None or not isinstance(self._cookies, list):
                        raise Exception("Wrong cookies file")
                    logging.info(f"Loaded {len(self._cookies)} cookies")

            # Set driver options
            logging.info("Adding chrome options")
            chrome_options = undetected_chromedriver.ChromeOptions()

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
            self.driver.set_page_load_timeout(_WAIT_TIMEOUT)

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
            logging.info(f"Loading {base_url}")
            self.driver.get(base_url)

            # Wait for textarea (New chat)
            self._wait_for_prompt_textarea()

            # Wait
            logging.info("Waiting 5 extra seconds")
            time.sleep(5)

            # Close welcome back dialogue
            self._welcome_back_resolve()

            # Prevent "element not interactable" error
            self._remove_new_chat_button()

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

            # Cleanup
            gc.collect()

            # Raise exception after
            raise e

    def prompt_send(self, prompt: str, conversation_id: str or None = None) -> str or None:
        """Sends prompt to ChatGPT

        Args:
            prompt (str): prompt text
            conversation_id (str or None, optional): existing conversation ID or None to create a new one

        Raises:
            Exception: in case of no session or timeout waiting for element or other error

        Returns:
            str or None: conversation ID or None if something goes wrong (most likely it'll just return an exception)
        """
        if self.driver is None:
            raise Exception("No opened session! Please call session_start() first")

        # Pause auto-refresher
        self._refresher_pause_resume(pause=True)

        try:
            # Fix base url (remove ending slash)
            base_url = self.config.get("base_url").strip()
            while base_url.endswith("/"):
                base_url = base_url[:-1]

            # Load conversation or create a new one
            if conversation_id:
                conversation_url = f"{base_url}/c/{conversation_id.strip()}"
            else:
                conversation_url = base_url
            logging.info(f"Loading {conversation_url}")
            self.driver.get(conversation_url)

            # Wait and scroll after
            self._wait_for_prompt_textarea()
            self._scroll_to_bottom()

            # Check for "Unable to load conversation ..." and create a new one if not exists
            if not self.driver.execute_script(_CONVERSATION_EXISTS):
                logging.warning(f"Conversation {conversation_id} doesn't exists! Creating a new one")
                conversation_id = None
                logging.info(f"Loading {base_url}")
                self.driver.get(base_url)
                self._wait_for_prompt_textarea()
                self._scroll_to_bottom()

            # Get last conversation id
            if not conversation_id:
                conversation_id_last_start = self.driver.execute_script(_GET_LAST_CONVERSATION_ID)
            else:
                conversation_id_last_start = conversation_id

            # Check for response error
            if self.driver.execute_script(_CONVERSATION_ERROR_RESOLVE):
                logging.warning("Found Regenerate button (due to error?) Waiting for regeneration to finish")
                time.sleep(1)
                self._wait_for_send_button()

            # Get message ID of last assistant message
            assistant_message_id_start = self.driver.execute_script(_ASSISTANT_GET_LAST_MESSAGE_ID)
            if assistant_message_id_start:
                logging.info(f"Last assistant message ID: {assistant_message_id_start}")

            # Get prompt area
            prompt_textarea = self.driver.find_element(By.ID, "prompt-textarea")

            # Paste -> click -> move cursor to the end -> add space -> erase space
            logging.info("Pasting prompt into textarea")
            self.driver.execute_script(_TYPE_INTO_TEXTAREA, prompt_textarea, prompt)
            time.sleep(0.1)
            prompt_textarea.click()
            time.sleep(0.1)
            self.driver.execute_script(_MOVE_CURSOR_TEXTAREA, prompt_textarea)
            time.sleep(0.1)
            prompt_textarea.send_keys(Keys.SPACE)
            time.sleep(0.1)
            prompt_textarea.send_keys(Keys.BACKSPACE)
            time.sleep(0.1)

            # Click send prompt button
            logging.info("Clinking on send-button")
            send_buttons_old = self.driver.find_elements(By.XPATH, "//*[@data-testid='send-button']")
            if len(send_buttons_old) != 0:
                send_buttons_old[0].click()
            else:
                self.driver.find_element(
                    By.XPATH,
                    '//button[@class="mb-1 mr-1 flex h-8 w-8 items-center justify-center rounded-full bg-black text-white transition-colors hover:opacity-70 focus-visible:outline-none focus-visible:outline-black disabled:bg-[#D7D7D7] disabled:text-[#f4f4f4] disabled:hover:opacity-100 dark:bg-white dark:text-black dark:focus-visible:outline-white disabled:dark:bg-token-text-quaternary dark:disabled:text-token-main-surface-secondary"]',
                ).click()

            # Wait until assistant starts responding
            logging.info("Waiting for assistant to start responding")
            time_start = time.time()
            while True:
                # Check timeout
                if time.time() - time_start > _WAIT_TIMEOUT:
                    raise Exception("Timeout waiting for assistant to start responding")

                # Try to find new assistant message ID
                assistant_message_id = self.driver.execute_script(_ASSISTANT_GET_LAST_MESSAGE_ID)

                # Get conversation ID if it's a new conversation
                if not conversation_id:
                    conversation_id_last = self.driver.execute_script(_GET_LAST_CONVERSATION_ID)
                else:
                    conversation_id_last = conversation_id

                # Stop waiting if found a new message and conversation ID changed (if case of new conversation)
                if (
                    assistant_message_id
                    and (
                        conversation_id
                        or (
                            not conversation_id
                            and conversation_id_last
                            and conversation_id_last != conversation_id_last_start
                        )
                    )
                    and assistant_message_id != assistant_message_id_start
                ):
                    conversation_id = conversation_id_last
                    logging.info(f"New conversation ID: {conversation_id_last}")
                    logging.info(f"New assistant message ID: {assistant_message_id}")
                    break

                # Sleep a bit before next cycle to prevent overloading and to allow all elements to load properly
                time.sleep(_WAITER_CYCLE)

            # Save cookies
            self.cookies_save()

            # Save conversation ID for response_read_stream()
            self._conversation_id_last = conversation_id

            # Return new conversation ID
            return conversation_id

        except Exception as e:
            # Resume refresher, reset it's timer and re-raise error
            self._refresher_pause_resume(pause=False, reset_time=True)
            raise e

    def response_read_stream(self, convert_to_markdown: bool = True) -> Generator[Dict]:
        """Reads response from ChatGPT

        Args:
            convert_to_markdown (bool, optional): True to convert result from HTML to Markdown. Defaults to True

        Raises:
            Exception: in case of no opened session, no valid assistant messages, timeout or any other error

        Yields:
            Generator[Dict]: {
                "finished": True if it's the last response, False if not,
                "conversation_id": ID of current conversation (from prompt_send),
                "message_id": "ID of current message (from assistant)",
                "response": "Actual response as HTML or Markdown"
            }
        """
        if self.driver is None:
            raise Exception("No opened session! Please call session_start() first")
        try:
            # Pause auto-refresher
            self._refresher_pause_resume(pause=True)

            # generate until response finished
            finished = False
            while not finished:
                # Retrieve message ID, class name, inner HTML and code blocks
                response = self._assistant_get_last_message(raw=not convert_to_markdown)
                if response is None:
                    raise Exception("No valid assistant messages found")
                message_id, class_name, response_text, code_blocks = response

                # Check response type
                if class_name.startswith("result-streaming"):
                    finished = False
                elif class_name.startswith("markdown"):
                    finished = True
                elif "result-thinking" not in class_name:
                    raise Exception(f"Unknown response type: {class_name}")

                response_parsed = {"finished": finished}

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

                # Convert to markdown
                if convert_to_markdown:
                    try:
                        # Convert to markdown with code blocks placeholders
                        response_text = markdownify(
                            response_text,
                            escape_asterisks=False,
                            escape_underscores=False,
                            code_language_callback=_code_language_callback,
                        )

                        # Restore code blocks
                        if code_blocks is not None and isinstance(code_blocks, dict):
                            response_text = response_text.format_map(Default(code_blocks))
                    except Exception as e:
                        logging.error(f"Error converting HTML to Markdown! {e}")

                # Remove leading and tailing new lines
                response_parsed["response"] = response_text.strip()

                # Add conversation ID and message ID
                response_parsed["conversation_id"] = self._conversation_id_last
                response_parsed["message_id"] = message_id

                # Sleep a bit to prevent overloading
                time.sleep(_STREAM_READER_CYCLE)

                # Stream data as dictionary
                yield response_parsed

            # Done -> update cookies
            logging.info("Response finished")
            self.cookies_save()

            # Resume refresher and reset it's timer
            self._refresher_pause_resume(pause=False, reset_time=True)

        # Resume refresher and reset it's timer
        finally:
            self._refresher_pause_resume(pause=False, reset_time=True)

    def response_stop(self) -> None:
        """Clicks on Stop generating button

        Raises:
            Exception: no opened session or script execution error
        """
        if self.driver is None:
            raise Exception("No opened session! Please call session_start() first")
        self.driver.execute_script(_RESPONSE_STOP)

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

            # Close welcome back dialogue
            self._welcome_back_resolve()

            # Prevent "element not interactable" error
            self._remove_new_chat_button()

            # Search chat and get it's <a> tag and expand button
            logging.info("Executing conversation search script. Please wait")
            self.driver.set_script_timeout(_WAIT_TIMEOUT)
            search_result = self.driver.execute_async_script(self._conversation_search_js, conversation_id)
            if search_result is None:
                raise Exception("Unable to find chat expand button")
            if isinstance(search_result, str):
                raise Exception(search_result)
            chat_a_tag, chat_expand_button = search_result

            # Click on expand button
            action_chains = ActionChains(self.driver)
            time.sleep(0.1)
            logging.info("Moving to the a tag")
            action_chains.move_to_element(chat_a_tag).click().perform()
            time.sleep(0.5)
            logging.info("Clicking on expand button")
            chat_expand_button.click()
            time.sleep(0.5)

            # List all menu items
            menu_items = self.driver.find_elements(By.XPATH, "//*[@role='menuitem']")
            if len(menu_items) == 0:
                raise Exception("No menu expanded")

            # Try to find delete button
            clicked = False
            for menu_item in menu_items:
                if "Delete" in menu_item.get_attribute("innerHTML"):
                    logging.info("Clinking on Delete chat button")
                    menu_item.click()
                    clicked = True
                    time.sleep(1)
                    break

            # Check if we found it
            if not clicked:
                raise Exception("No Delete chat button")

            # Now it's time to confirm chat deletion
            danger_buttons = self.driver.find_elements(By.XPATH, "//*[@class='btn relative btn-danger']")
            if len(danger_buttons) == 0:
                raise Exception("No confirmation dialog")

            # Try to find Delete button inside all btn-danger buttons and click it
            for danger_button in danger_buttons:
                if "Delete" in danger_button.get_attribute("innerHTML"):
                    logging.info("Clicking on confirmation button")
                    danger_button.click()
                    logging.info("Conversation deleted")

                    # Resume refresher and reset it's timer
                    self._refresher_pause_resume(pause=False, reset_time=True)
                    return

            # We couldn't find confirmation button
            raise Exception("No confirmation button")

        # Resume refresher and reset it's timer
        finally:
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

        # Cleanup
        gc.collect()

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

    def _assistant_get_last_message(self, raw: bool) -> Any:
        """Executes assistantGetLastMessage() function from assistantGetLastMessage and injects it's JS if needed

        Args:
            raw (bool): False to use preformatRecursion(), True to return as is

        Returns:
            Any: [message ID, responseContainerClassName, responseContainer.innerHTML, codeBlocks (as JSON)] or null
        """
        # Check if assistantGetLastMessage.js is injected
        is_injected = False
        try:
            is_injected = self.driver.execute_script("return isGetLastMessageInjected();")
        except:
            pass

        # Inject JS
        if not is_injected:
            logging.warning("assistantGetLastMessage is not injected. Injecting it")
            self.driver.execute_script(_INJECT_JS, self._assistant_get_last_message_js)
            logging.info(f"Injected? {self.driver.execute_script('return isGetLastMessageInjected();')}")

        # Execute script and return result
        raw = "true" if raw else "false"
        return self.driver.execute_script(f"return conversationGetLastMessage({raw});")

    def _welcome_back_resolve(self) -> None:
        """Clicks on "Stay logged out" in welcome back dialogue"""
        welcome_back_dialogues = self.driver.find_elements(By.XPATH, "//div[@role='dialog' and @id='radix-:r7:']")
        if len(welcome_back_dialogues) == 0:
            return
        welcome_back_dialogue = welcome_back_dialogues[0]
        try:
            logging.info('Clicking on "Stay logged out"')
            welcome_back_dialogue.find_element(By.XPATH, "//a[starts-with(@class, 'cursor-pointer')]").click()
            logging.info("Waiting extra 5 seconds")
            time.sleep(5)
        except Exception as e:
            logging.warning(f'Unable to clock on "Stay logged out": {e}')

    def _remove_new_chat_button(self) -> None:
        """Removes "New chat" button because it intercepts side chat buttons"""
        # Expand histories
        expand_buttons = self.driver.find_elements(
            By.XPATH,
            '//button[@class="h-10 rounded-lg px-2.5 text-token-text-secondary focus-visible:outline-0 hover:bg-token-main-surface-secondary focus-visible:bg-token-main-surface-secondary"]',
        )
        if len(expand_buttons) != 0:
            logging.info("Expanding histories")
            expand_buttons[0].click()
            time.sleep(1)

        # Old version
        sticky_divs = self.driver.find_elements(By.XPATH, "//div[starts-with(@class, 'sticky')]")
        for sticky_div in sticky_divs:
            try:
                if "New chat" in sticky_div.get_attribute("innerText"):
                    logging.info('Removing "New chat" button')
                    self.driver.execute_script("arguments[0].remove();", sticky_div)
                    break
            except:
                pass

        # New version
        try:
            self.driver.execute_script("")
            logging.info('"New chat" button removed')
        except:
            pass

    def _wait_for_prompt_textarea(self) -> None:
        """Waits for prompt textarea to become visible and 1 extra second to make sure it's loaded and clickable"""
        logging.info("Waiting for page to load (waiting for prompt-textarea element)")
        WebDriverWait(self.driver, _WAIT_TIMEOUT).until(
            expected_conditions.presence_of_element_located((By.ID, "prompt-textarea"))
        )
        time.sleep(1)
        logging.info("Page loaded")

    def _wait_for_send_button(self) -> None:
        """Waits for send-button to become available"""
        logging.info("Waiting for send-button")
        WebDriverWait(self.driver, _WAIT_TIMEOUT).until(
            expected_conditions.presence_of_element_located((By.XPATH, "//*[@data-testid='send-button']"))
        )
        WebDriverWait(self.driver, _WAIT_TIMEOUT).until(
            expected_conditions.element_to_be_clickable((By.XPATH, "//*[@data-testid='send-button']"))
        )
        time.sleep(1)
        logging.info("send-button is available")

    def _scroll_to_bottom(self) -> None:
        """Scrolls to the bottom"""
        self.driver.execute_script(_SCROLL_TO_BOTTOM)

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
        """Automatically refreshes browser Page every self.auto_refresh_interval seconds, scrolls to bottom
        and saves cookies
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
                    logging.info("Refreshing current page")
                    self.driver.set_page_load_timeout(_WAIT_TIMEOUT)
                    self.driver.refresh()

                    # Wait for page to load
                    self._wait_for_prompt_textarea()

                    # Prevent "element not interactable" error
                    self._remove_new_chat_button()

                    # Scroll (just in case)
                    self._scroll_to_bottom()

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
