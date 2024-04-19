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

import argparse
import logging
import json
import os
import sys

from lmao._version import __version__
from lmao.module_wrapper import MODULES, ModuleWrapper
from lmao.external_api import ExternalAPI

# Default configs directory path
_CONFIGS_DIR = "configs"

# Default server host
_HOST_DEFAULT = "localhost"

# Default port number
_PORT_DEFAULT = 1312


def logging_setup() -> None:
    """Sets up logging format and level"""
    # Logs formatter
    log_formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Setup logging into console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    # Add all handlers and setup level
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

    # Log test message
    logging.info("Logging setup is complete")


def parse_args() -> argparse.Namespace:
    """Parses cli arguments
    usage: lmao [-h] [-v] [-c CONFIGS] [-t TEST] [-i IP] [-p PORT] [-s SSL [SSL ...]] [--tokens TOKENS [TOKENS ...]]
        [--rate-limits-default RATE_LIMITS_DEFAULT [RATE_LIMITS_DEFAULT ...]]
        [--rate-limit-fast RATE_LIMIT_FAST] [--no-logging-init]

    Unofficial open APIs for popular LLMs with self-hosted redirect capability

    options:
    -h, --help            show this help message and exit
    -v, --version         show program's version number and exit
    -c CONFIGS, --configs CONFIGS
                            path to configs directory with each module config file (Default: configs)
    -t TEST, --test TEST  module name to test in cli instead of starting API server (eg. --test=chatgpt)
    -i IP, --ip IP        API server Host (IP) (Default: localhost)
    -p PORT, --port PORT  API server port (Default: 1312)
    -s SSL [SSL ...], --ssl SSL [SSL ...]
                            Paths to SSL certificate and private key (ex. --ssl "path/to/certificate.crt" "path/to/private.key")
    --tokens TOKENS [TOKENS ...]
                            API tokens to enable authorization (ex. --tokens "abcdefg12345" "AAAAATESTtest")
    --rate-limits-default RATE_LIMITS_DEFAULT [RATE_LIMITS_DEFAULT ...]
                            Rate limits for all API requests except /status and /stop (Default: --rate-limits-default "10/minute", "1/second")
    --rate-limit-fast RATE_LIMIT_FAST
                            Rate limit /status and /stop API requests (Default: "1/second")
    --no-logging-init     specify to bypass logging initialization (will be set automatically when using --test)

    Returns:
        argparse.Namespace: parsed arguments
    """

    # Example usage
    epilog = """examples:
  lmao --test=chatgpt
  lmao --ip="0.0.0.0" --port=1312
  lmao --ip="0.0.0.0" --port=1312 --no-logging-init
  lmao --ip "0.0.0.0" --port=1312 --ssl certificate.crt private.key --tokens myStrongRandomToken myStrongRandomToken2"""

    parser = argparse.ArgumentParser(
        prog="lmao",
        description="Unofficial open APIs for popular LLMs with self-hosted redirect capability",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "-c",
        "--configs",
        type=str,
        default=os.getenv("CONFIGS", _CONFIGS_DIR),
        required=False,
        help=f"path to configs directory with each module config file (Default: {os.getenv('CONFIG', _CONFIGS_DIR)})",
    )
    parser.add_argument(
        "-t",
        "--test",
        type=str or None,
        default=None,
        required=False,
        help=f"module name to test in cli instead of starting API server (eg. --test={MODULES[0]})",
    )
    parser.add_argument(
        "-i",
        "--ip",
        type=str,
        default=os.getenv("HOSTNAME", _HOST_DEFAULT),
        required=False,
        help=f"API server Host (IP) (Default: {os.getenv('HOSTNAME', _HOST_DEFAULT)})",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=int(os.getenv("PORT", str(_PORT_DEFAULT))),
        required=False,
        help=f"API server port (Default: {int(os.getenv('PORT', str(_PORT_DEFAULT)))})",
    )
    parser.add_argument(
        "-s",
        "--ssl",
        nargs="+",
        default=[],
        required=False,
        help='Paths to SSL certificate and private key (ex. --ssl "path/to/certificate.crt" "path/to/private.key")',
    )
    parser.add_argument(
        "--tokens",
        nargs="+",
        default=[],
        required=False,
        help='API tokens to enable authorization (ex. --tokens "abcdefg12345" "AAAAATESTtest")',
    )
    parser.add_argument(
        "--rate-limits-default",
        nargs="+",
        default=["10/minute", "1/second"],
        required=False,
        help='Rate limits for all API requests except /status and /stop (Default: --rate-limits-default "10/minute", "1/second")',
    )
    parser.add_argument(
        "--rate-limit-fast",
        type=str,
        default="1/second",
        required=False,
        help='Rate limit /status and /stop API requests (Default: "1/second")',
    )
    parser.add_argument(
        "--no-logging-init",
        action="store_true",
        required=False,
        help="specify to bypass logging initialization (will be set automatically when using --test)",
    )

    return parser.parse_args()


def main():
    # Generate and parse arguments
    args = parse_args()

    # Initialize logging
    if not args.no_logging_init and not args.test:
        logging_setup()

    # Load configs
    logging.info(f"Loading config files from {args.configs} directory")
    config = {}
    for file in os.listdir(args.configs):
        # Parse only .json files
        if file.lower().endswith(".json"):
            # Extract name of module
            module_name_from_file = os.path.splitext(os.path.basename(file))[0]

            # Parse and merge
            logging.info(f"Adding config of {module_name_from_file} module")
            with open(os.path.join(args.configs, file), "r", encoding="utf-8") as file_:
                module_config = json.loads(file_.read())
            config[module_name_from_file] = module_config

    # --test mode
    if args.test:
        # Convert to lowercase and strip (just in case)
        args.test = args.test.lower().strip()
        logging.info(f"Starting test mode of {args.test} module")

        # Initialize
        try:
            logging.info("Initializing module")
            module_config = config.get(args.test)
            module = ModuleWrapper(args.test, module_config)
            module.initialize(blocking=True)
            if module.error:
                raise Exception(str(module.error))
        except Exception as e:
            logging.error(f"{args.test} initialization error", exc_info=e)
            return

        # Read and process each user request
        conversation_id = None
        logging.info("Test mode started. Press CTRL+C to stop")
        while True:
            try:
                # Read prompt
                print("User > ", end="", flush=True)
                prompt = input().strip()
                if not prompt:
                    print("", flush=True)
                    continue

                # Stream response
                try:
                    print(f"{args.test} > ", end="", flush=True)
                    response_text_prev = ""
                    for response in module.ask(
                        {"prompt": prompt, "conversation_id": conversation_id, "convert_to_markdown": True}
                    ):
                        conversation_id = response.get("conversation_id")
                        response_text = response.get("response").strip()

                        # Check if it's a new request
                        if response_text == response_text_prev:
                            continue

                        # Check if not empty
                        if not response_text:
                            response_text_prev = response_text
                            continue

                        # Stream difference
                        response_text_printable = response_text
                        if response_text_printable.startswith(response_text_prev):
                            response_text_printable = response_text_printable[len(response_text_prev) :]
                        print(response_text_printable, end="", flush=True)

                        # Save for next cycle
                        response_text_prev = response_text

                    print("", flush=True)

                except Exception as e:
                    logging.error(f"{args.test} error", exc_info=e)

            except (SystemExit, KeyboardInterrupt):
                logging.warning("Interrupted")
                break

        # Close module
        try:
            logging.info("Closing module")
            module.error = None
            module.close(blocking=True)
            if module.error:
                raise Exception(str(module.error))
        except Exception as e:
            logging.error(f"Error closing {args.test}", exc_info=e)
            return

    # Start API server if no --test mode specified
    else:
        if args.ssl and len(args.ssl) < 2:
            logging.error("Please provide paths to both .crt and .key files")
            return

        api = ExternalAPI(
            config,
            rate_limits_default=args.rate_limits_default,
            rate_limit_fast=args.rate_limit_fast,
            tokens=args.tokens,
        )
        if args.ssl and len(args.ssl) == 2:
            api.run(args.ip, args.port, certfile=args.ssl[0], keyfile=args.ssl[1])
        else:
            api.run(args.ip, args.port)


if __name__ == "__main__":
    main()
