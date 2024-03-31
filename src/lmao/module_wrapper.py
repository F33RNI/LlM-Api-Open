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

import base64
import logging
import threading
from collections.abc import Generator
from typing import Dict

from lmao.chatgpt.chatgpt_api import ChatGPTApi
from lmao.ms_copilot.ms_copilot_api import MSCopilotApi

STATUS_NOT_INITIALIZED = 0
STATUS_INITIALIZING = 1
STATUS_IDLE = 2
STATUS_BUSY = 3
STATUS_STOPPING = 4
STATUS_FAILED = -1

STATUS_TO_STR = ["Not initialized", "Initializing", "Idle", "Busy", "Stopping", "Failed"]

MODULES = ["chatgpt", "ms_copilot"]

# TODO: Implement multiprocessing instead of threading


class ModuleWrapper:
    def __init__(self, name: str, config: Dict) -> None:
        """Initializes any module's class object from MODULES

        Args:
            name (str): name of module to initialize (from MODULES)
            config (Dict): module's configuration (see each module docs for description)

        Raises:
            Exception: no module or object initialization error
        """
        if name not in MODULES:
            raise Exception(f"No module named {name}")
        self.name = name
        self.config = config

        self.status = STATUS_NOT_INITIALIZED
        self.error = None

        # Initialize module class
        logging.info(f"Initializing {name} class object")
        if self.name == "chatgpt":
            self._module_class = ChatGPTApi(self.config)
        elif self.name == "ms_copilot":
            self._module_class = MSCopilotApi(self.config)

    def initialize(self, blocking: bool = False, **kwargs) -> None:
        """Starts module's session without raising any error
        For error and status, please check self.status and self.error

        Args:
            blocking (bool, optional): True to call init from calling thread instead of separate one
        """

        def _initialization_thread() -> None:
            """Tries to start module's session without raising any error"""
            if not blocking:
                logging.info(f"{self.name} initialization thread started")
            self.status = STATUS_INITIALIZING
            try:
                self._module_class.session_start(**kwargs)
                self.status = STATUS_IDLE
            except Exception as e:
                logging.error(f"{self.name} initialization error", exc_info=e)
                self.status = STATUS_FAILED
                self.error = e

        if blocking:
            _initialization_thread()
        else:
            logging.info("Starting initialization thread")
            threading.Thread(target=_initialization_thread).start()

    def close(self, blocking: bool = False) -> None:
        """Closes module session without raising any error
        For error and status, please check self.status and self.error

        Args:
            blocking (bool, optional): True to call close from calling thread instead of separate one
        """

        def _closing_thread() -> None:
            """Tries to close module's session without raising any error"""
            if not blocking:
                logging.info(f"{self.name} closing thread started")
            self.status = STATUS_STOPPING
            try:
                self._module_class.session_close()
                self.status = STATUS_NOT_INITIALIZED
            except Exception as e:
                logging.error(f"Error closing {self.name} session", exc_info=e)
                self.status = STATUS_FAILED
                self.error = e

        if blocking:
            _closing_thread()
        else:
            logging.info("Starting closing thread")
            threading.Thread(target=_closing_thread).start()

    def ask(self, request: Dict) -> Generator[Dict]:
        """prompt_send() and response_read_stream() wrapper

        Args:
            request (Dict): request for module
            For chatgpt: {
                "prompt": "Text request",
                "conversation_id": "empty string or existing conversation ID",
                "convert_to_markdown": True or False
            }
            For ms_copilot: {
                "prompt": "Text request",
                "image": image as bytes or as base64 string or None,
                "conversation_id": "empty string or existing conversation ID",
                "style": "creative" / "balanced" / "precise",
                "convert_to_markdown": True or False
            }

        Raises:
            Exception: in case of prompt_send() or response_read_stream() error

        Yields:
            Generator[Dict]: response from module
            For chatgpt: {
                "finished": True if it's the last response, False if not,
                "conversation_id": ID of current conversation (from prompt_send),
                "message_id": "ID of current message (from assistant)",
                "response": "Actual response as text"
            }
            For ms_copilot: {
                "finished": True if it's the last response, False if not,
                "response": "response as text (or meta response)",
                "images": ["array of image URL's"],
                "caption": "images caption",
                "suggestions": ["array of suggestions of the requests"]
            }
        """
        self.status = STATUS_BUSY
        try:
            # Parse image and convert into bytes
            image = request.get("image")
            if image is not None:
                if isinstance(image, str):
                    logging.info("Decoding image from base64")
                    image = base64.b64decode(image)

            # Send request
            if self.name == "chatgpt":
                self._module_class.prompt_send(
                    prompt=request.get("prompt"), conversation_id=request.get("conversation_id")
                )
            elif self.name == "ms_copilot":
                self._module_class.prompt_send(
                    prompt=request.get("prompt"),
                    image=image,
                    conversation_id=request.get("conversation_id"),
                    style=request.get("style"),
                )

            # Re-yield response
            for response in self._module_class.response_read_stream(request.get("convert_to_markdown")):
                yield response

        # Clear status back to IDLE
        finally:
            self.status = STATUS_IDLE

    def response_stop(self) -> None:
        """Wrapper for response_stop() function

        Raises:
            Exception: module error
        """
        self.status = STATUS_BUSY
        try:
            self._module_class.response_stop()

            # Reset status
            self.status = STATUS_IDLE

        # Clear status back to IDLE and re-raise exception
        except Exception as e:
            self.status = STATUS_IDLE
            raise e

    def delete_conversation(self, conversation: Dict) -> None:
        """Wrapper for conversation_delete() function

        Args:
            conversation (Dict): conversation data to delete
            For chatgpt / ms_copilot: {
                "conversation_id": "ID of conversation to delete (in lower case)"
            }

        Raises:
            Exception: module error
        """
        self.status = STATUS_BUSY
        try:
            self._module_class.conversation_delete(conversation.get("conversation_id"))

        # Clear status back to IDLE
        finally:
            self.status = STATUS_IDLE
