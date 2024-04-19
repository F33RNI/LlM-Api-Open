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

import atexit
import json
import logging
import ssl
import threading
from typing import Dict, List, Literal

from flask import Flask, request, Response, jsonify

from lmao.module_wrapper import (
    ModuleWrapper,
    STATUS_NOT_INITIALIZED,
    MODULES,
    STATUS_IDLE,
    STATUS_FAILED,
    STATUS_TO_STR,
)

# 401 error
NOT_AUTHORIZED_ERROR_TEXT = "Not authorized"


class ExternalAPI:
    def __init__(self, config: Dict, tokens: List or None = None):
        self.config = config
        self.tokens = tokens

        if not self.tokens or len(self.tokens) == 0:
            self.tokens = None
        if self.tokens:
            logging.info("Token-based authorization enabled")

        self.app = Flask(__name__)
        self.lock = threading.Lock()

        # name of module: class object
        self.modules = {}

        @self.app.route("/api/init", methods=["POST"])
        def init() -> tuple[Response, Literal]:
            """Begins module initialization
            Please call /api/status to check if module is initialized BEFORE calling /api/init
            And AFTER calling /api/init please call /api/status to check if module's initialization finished

            Request:
                {
                    "module": "name of module from MODULES",
                    "token": "optional token if --tokens argument provided"
                }

            Returns:
                tuple[Response, Literal]: {}, 200 if everything is ok
                or
                {"error": "Error message"}, 400 / 401 or 500 in case of error
            """
            try:
                # Parse request as JSON
                request_json = request.get_json()

                # Check token
                if self.tokens:
                    if "token" not in request_json or request_json["token"] not in self.tokens:
                        return (jsonify({"error": NOT_AUTHORIZED_ERROR_TEXT}), 401)

                # Extract and check module name
                module_name = request_json.get("module")
                if module_name is None:
                    return (jsonify({"error": '"module" not specified'}), 400)
                if module_name not in MODULES:
                    return (jsonify({"error": f"No module named {module_name}"}), 400)

                logging.info(f"/init request for module {module_name}")

                # Initialize class object
                if self.modules.get(module_name) is None:
                    # Read and check config
                    module_config = config.get(module_name)
                    if module_config is None:
                        logging.error(f"No config for {module_name}")
                        return (jsonify({"error": f"No config for {module_name}"}), 500)

                    # Initialize class object
                    self.modules[module_name] = ModuleWrapper(module_name, module_config)
                module = self.modules[module_name]

                # Check if already initialized
                if module.status != STATUS_NOT_INITIALIZED and module.status != STATUS_FAILED:
                    return (
                        jsonify(
                            {"error": f"Cannot initialize {module_name} with status {STATUS_TO_STR[module.status]}"}
                        ),
                        400,
                    )

                # Initialize in thread
                module.initialize()

                return jsonify({}), 200
            except Exception as e:
                logging.error(f"/init error: {e}")
                return jsonify({"error": e}), 500

        @self.app.route("/", methods=["POST"])
        @self.app.route("/index", methods=["POST"])
        @self.app.route("/index.html", methods=["POST"])
        @self.app.route("/index.php", methods=["POST"])
        @self.app.route("/api/status", methods=["POST"])
        def status() -> tuple[Response, Literal]:
            """Retrieves current status of all modules

            Request:
                {
                    "token": "optional token if --tokens argument provided"
                }

            Returns:
                tuple[Response, Literal]: [
                    {
                        "module": "Name of the module from MODULES",
                        "status_code": "Module's status code as integer",
                        "status_name": "Module's status as string",
                        "error": "Empty or module's error message",
                    }
                ], 200 if no errors while iterating modules
                or
                {"error": "Error message"}, 401 or 500 in case of error
            """
            try:
                # Check token
                if self.tokens:
                    request_json = request.get_json()
                    if "token" not in request_json or request_json["token"] not in self.tokens:
                        return (jsonify({"error": NOT_AUTHORIZED_ERROR_TEXT}), 401)

                # Read and add statuses
                statuses = []
                for module_name, module in self.modules.items():
                    try:
                        statuses.append(
                            {
                                "module": module_name,
                                "status_code": module.status,
                                "status_name": STATUS_TO_STR[module.status],
                                "error": module.error if module.error is not None else "",
                            }
                        )
                    except Exception as e:
                        logging.warning(f"Can't read {module_name} status: {e}")
                return jsonify(statuses), 200
            except Exception as e:
                logging.error(f"/status error: {e}")
                return jsonify({"error": e}), 500

        @self.app.route("/api/ask", methods=["POST"])
        def ask():
            """Initiates a request to the specified module and streams responses back
            Please call /api/status to check if module is initialized and not busy BEFORE calling /api/ask

            Request:
                For ChatGPT:
                    {
                        "chatgpt": {
                            "prompt": "Text request to send to the module",
                            "conversation_id": "Optional conversation ID (to continue existing chat) or empty for a new conversation",
                            "convert_to_markdown": true or false //(Optional flag for converting response to Markdown)
                        },
                        "token": "optional token if --tokens argument provided"
                    }
                For Microsoft Copilot:
                    {
                        "ms_copilot": {
                            "prompt": "Text request",
                            "image": image as base64 to include into request,
                            "conversation_id": "empty string or existing conversation ID",
                            "style": "creative" / "balanced" / "precise",
                            "convert_to_markdown": True or False,
                            "token": "optional token if --tokens argument provided"
                        },
                        "token": "optional token if --tokens argument provided"
                    }

            Yields: A stream of JSON objects containing module responses.
            For ChatGPT, each JSON object has the following structure:
                {
                    "finished": "True if it's the last response, False if not",
                    "message_id": "ID of the current message (from assistant)",
                    "response": "Actual response as text"
                }
            For Microsoft Copilot, each JSON object has the following structure:
                {
                    "finished": True if it's the last response, False if not,
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

            Returns: {"error": "Error message"}, 401 or 500 in case of error
            """
            try:
                # Parse request as JSON
                request_json = request.get_json()

                # Check token
                if self.tokens:
                    if "token" not in request_json or request_json["token"] not in self.tokens:
                        return (jsonify({"error": NOT_AUTHORIZED_ERROR_TEXT}), 401)

                # Check request
                if request_json is None or len(request_json.items()) == 0:
                    return (jsonify({"error": "Empty request"}), 400)

                # Extract prompt data
                module_name, prompt_request = list(request_json.items())[0]

                # Check module
                module = self.modules.get(module_name)
                if module is None:
                    return jsonify({"error": f"No {module_name} module defined. Please initialize one first"}), 400
                if module.status != STATUS_IDLE:
                    return jsonify({"error": f"{module_name} status is not {STATUS_TO_STR[STATUS_IDLE]}"}), 400

                # Response generator
                def _stream_response():
                    with self.lock:
                        for response in module.ask(prompt_request):
                            yield json.dumps(response) + "\n"

                logging.info(f"/ask request for module {module_name}")
                return Response(_stream_response(), content_type="application/json")

            except Exception as e:
                logging.error(f"/ask error: {e}")
                return jsonify({"error": e}), 500

        @self.app.route("/api/stop", methods=["POST"])
        def response_stop() -> tuple[Response, Literal]:
            """Stops the specified module's streaming response (stops yielding in /ask)

            Request:
                {
                    "module": "Name of the module from MODULES",
                    "token": "optional token if --tokens argument provided"
                }

            Returns:
                tuple[Response, Literal]: {}, 200 if the stream stopped successfully
                or
                {"error": "Error message"}, 400 / 401 or 500 in case of error
            """
            try:
                # Parse request as JSON
                request_json = request.get_json()

                # Check token
                if self.tokens:
                    if "token" not in request_json or request_json["token"] not in self.tokens:
                        return (jsonify({"error": NOT_AUTHORIZED_ERROR_TEXT}), 401)

                # Extract module name
                module_name = request_json.get("module")
                if module_name is None:
                    return jsonify({"error": '"module" not specified'}), 400

                # Check if module exists
                module = self.modules.get(module_name)
                if module is None:
                    return jsonify({"error": f"No {module_name} module defined. Please initialize one first"}), 400

                # Call response_stop in a safe way
                logging.info(f"/stop request for module {module_name}")
                module.response_stop()

                return jsonify({}), 200

            except Exception as e:
                logging.error(f"/stop error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/delete", methods=["POST"])
        def delete_conversation() -> tuple[Response, Literal]:
            """Clears module's conversation history
            Please call /api/status to check if module is initialized and not busy BEFORE calling /api/delete

            Request:
                {
                    // For ChatGPT
                    "module": {
                        "conversation_id": "ID of conversation to delete or empty to delete the top one"
                    },
                    "token": "optional token if --tokens argument provided"
                }

            Returns:
                tuple[Response, Literal]: {}, 200 if conversation deleted successfully
                or
                {"error": "Error message"}, 400 / 401 or 500 in case of error
            """
            try:
                # Parse request as JSON
                request_json = request.get_json()

                # Check token
                if self.tokens:
                    if "token" not in request_json or request_json["token"] not in self.tokens:
                        return (jsonify({"error": NOT_AUTHORIZED_ERROR_TEXT}), 401)

                # Check request
                if request_json is None or len(request_json.items()) == 0:
                    return (jsonify({"error": "Empty request"}), 400)

                # Extract prompt data
                module_name, conversation_data = list(request_json.items())[0]

                # Check module
                module = self.modules.get(module_name)
                if module is None:
                    return jsonify({"error": f"No {module_name} module defined. Please initialize one first"}), 400
                if module.status != STATUS_IDLE:
                    return jsonify({"error": f"{module_name} status is not {STATUS_TO_STR[STATUS_IDLE]}"}), 400

                # Call delete_conversation in a safe way
                logging.info(f"/delete request for module {module_name}")
                module.delete_conversation(conversation_data)

                return jsonify({}), 200

            except Exception as e:
                logging.error(f"/delete error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/close", methods=["POST"])
        def close():
            """Request module's session to close (in a separate thread)
            Please call /api/status to check if module is initialized and it's status is Idle or Failed

            Request:
                {
                    "module": "Name of the module from MODULES",
                    "token": "optional token if --tokens argument provided"
                }

            Returns:
                tuple[Response, Literal]: {}, 200 if requested successfully
                or
                {"error": "Error message"}, 400 / 401 or 500 in case of error
            """
            try:
                # Parse request as JSON
                request_json = request.get_json()

                # Check token
                if self.tokens:
                    if "token" not in request_json or request_json["token"] not in self.tokens:
                        return (jsonify({"error": NOT_AUTHORIZED_ERROR_TEXT}), 401)

                # Extract module name
                module_name = request_json.get("module")
                if module_name is None:
                    return jsonify({"error": '"module" not specified'}), 400

                # Check if module exists
                module = self.modules.get(module_name)
                if module is None:
                    return jsonify({"error": f"No {module_name} module defined. Please initialize one first"}), 400

                # Check module status
                if module.status != STATUS_IDLE and module.status != STATUS_FAILED:
                    return (
                        jsonify({"error": f"Cannot close {module_name} with status {STATUS_TO_STR[module.status]}"}),
                        400,
                    )

                # Call close in a safe way
                logging.info(f"/close request for module {module_name}")
                module.close(blocking=False)
                del self.modules[module_name]

                return jsonify({}), 200

            except Exception as e:
                logging.error(f"/close error: {e}")
                return jsonify({"error": str(e)}), 500

    def _close_modules(self) -> None:
        """Tries to close each module on exit"""
        if len(self.modules) != 0:
            logging.warning("Exit request")
        for module_name, module in self.modules.items():
            logging.info(f"Trying to close {module_name}")
            try:
                module.close(blocking=True)
            except Exception as e:
                logging.warning(f"Cannot close {module_name}: {e}")

    def run(self, host: str, port: int, certfile: str or None = None, keyfile: str or None = None):
        """Starts API server

        Args:
            host (str): server host (ip)
            port (int): server port
            certfile (str or None, optional): "path/to/certificate.crt" to enable SSL. Defaults to None
            keyfile (str or None, optional): "path/to/private.key" to enable SSL. Defaults to None
        """
        atexit.register(self._close_modules)
        if certfile and keyfile:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain(certfile=certfile, keyfile=keyfile)
            self.app.run(host=host, port=port, ssl_context=context, debug=False)
        else:
            self.app.run(host=host, port=port, debug=False)
