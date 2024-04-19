# 🕊️ LLM-API-Open (LMAO)

| <img src="https://github.com/F33RNI/LlM-Api-Open/blob/main/brandbook/Logo.png?raw=true" height="auto" width="128" alt="LLM-API-Open logo"> | <h3>Unofficial open APIs for popular LLMs with self-hosted redirect capability</h3> |
| ------------------------------------------------------------------------------------------------------------------------------------------ | :---------------------------------------------------------------------------------: |

----------

## ❓ WAT

> 🕊️ LLM-API-Open (LMAO) allows for the free and universal utilization of popular Large Language Models (LLM).
> This is achieved using browser automation. LLM-API-Open (LMAO) launches a browser in headless mode and controls a website as if a real user were using it.
> This enables the use of popular LLMs that usually don't offer easy and free access to their official APIs
>
> 🔥 Additionally, LLM-API-Open (LMAO) is capable of creating its **own API server** to which any other apps can send requests.
> In other words, you can utilize LLM-API-Open (LMAO) both as a **Python package** and as an **API proxy** for any of your apps!

----------

## 🚧 LLM-API-Open is development

> Due to my studies, I don't have much time to work on the project 😔
>
> Currently, LLM-API-Open has only **2** modules: **ChatGPT** and **Microsoft Copilot**
>
> 📈 But it is possible to add other popular online LLMs *(You can wait, or make a pull-request yourself)*
>
> 📄 Documentation is also under development! Consider reading docstring for now

----------

## 😋 Support project

- BTC: `bc1qd2j53p9nplxcx4uyrv322t3mg0t93pz6m5lnft`
- ETH: `0x284E6121362ea1C69528eDEdc309fC8b90fA5578`
- ZEC: `t1Jb5tH61zcSTy2QyfsxftUEWHikdSYpPoz`

- Or by my music on [🟦 bandcamp](https://f3rni.bandcamp.com/)

----------

## 🏗️ Getting started

> ⚠️ Will not work with Python **3.13** or later due to `imghdr`

### ⚙️ 1. Download / build / install LLM-API-Open

There is 4 general ways to get LLM-API-Open

#### ⚙️ Install via `pip`

- Install from PyPi

    ```shell
    pip install llm-api-open
    ```

- **Or** install from GitHub directly

    ```shell
    pip install git+https://github.com/F33RNI/LLM-API-Open.git
    ```

- **Or** clone repo and install

    ```shell
    git clone https://github.com/F33RNI/LLM-API-Open.git
    cd LLM-API-Open

    python -m venv venv
    source venv/bin/activate

    pip install .
    ```

#### ⬇️ Download cli version from **releases**

<https://github.com/F33RNI/LLM-API-Open/releases/latest>

#### 🔨 Build cli version from source using PyInstaller

```shell
git clone https://github.com/F33RNI/LLM-API-Open.git
cd LLM-API-Open

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

pyinstaller lmao.spec

dist/lmao --help
```

#### 💻 Use source as is

```shell
git clone https://github.com/F33RNI/LLM-API-Open.git
cd LLM-API-Open

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export PYTHONPATH=./src:$PYTHONPATH
export PYTHONPATH=./src/lmao:$PYTHONPATH
python -m main --help
```

### 🔧 2. Configure LLM-API-Open

1. Download `configs` directory from this repo
2. Open `.json` files of modules you need in any editor and change it as you need
3. Specify path to `configs` directory with `-c path/to/configs` argument

----------

## 📦 Python package example

```python
import logging
import json

from lmao.module_wrapper import ModuleWrapper

# Initialize logging in a simplest way
logging.basicConfig(level=logging.INFO)

# Load config
with open("path/to/configs/chatgpt.json", "r", encoding="utf-8") as file:
    module_config = json.loads(file.read())

# Initialize module
module = ModuleWrapper("chatgpt", module_config)
module.initialize(blocking=True)

# Ask smth
conversation_id = None
for response in module.ask({"prompt": "Hi! Who are you?", "convert_to_markdown": True}):
    conversation_id = response.get("conversation_id")
    response_text = response.get("response")
    print(response_text, end="\n\n")

# Delete conversation
module.delete_conversation({"conversation_id": conversation_id})

# Close (unload) module
module.close(blocking=True)
```

----------

## 💻 CLI example

```text
$ lmao --help        
usage: lmao [-h] [-v] [-c CONFIGS] [-t TEST] [-i IP] [-p PORT] [-s SSL [SSL ...]] [--tokens TOKENS [TOKENS ...]] [--rate-limits-default RATE_LIMITS_DEFAULT [RATE_LIMITS_DEFAULT ...]]
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

examples:
  lmao --test=chatgpt
  lmao --ip="0.0.0.0" --port=1312
  lmao --ip="0.0.0.0" --port=1312 --no-logging-init
  lmao --ip "0.0.0.0" --port=1312 --ssl certificate.crt private.key --tokens myStrongRandomToken myStrongRandomToken2
```

```shell
$ lmao --test=chatgpt
WARNING:root:Error adding cookie oai-did
WARNING:root:Error adding cookie ajs_anonymous_id
WARNING:root:Error adding cookie oai-allow-ne
User > Hi!    
chatgpt > Hello! How can I assist you today?
```

----------

## 🌐 API example

### Start server

> Please see `🔒 HTTPS server and token-based authorization` section for more info about HTTPS server and tokens

```shell
$ lmao --configs "configs" --ip "0.0.0.0" --port "1312" 
2024-03-30 23:14:50 INFO     Logging setup is complete
2024-03-30 23:14:50 INFO     Loading config files from configs directory
2024-03-30 23:14:50 INFO     Adding config of ms_copilot module
2024-03-30 23:14:50 INFO     Adding config of chatgpt module
 * Serving Flask app 'lmao.external_api'
 * Debug mode: off
2024-03-30 23:14:50 INFO     WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:1312
 * Running on http://192.168.0.3:1312
2024-03-30 23:14:50 INFO     Press CTRL+C to quit
...
```

#### 🐍 Python (requests)

```python
import logging
import time
from typing import Dict

import requests

# API URL
BASE_URL = "http://localhost:1312/api"

# Timeout for each request
TIMEOUT = 60

# Initialize logging in a simplest way
logging.basicConfig(level=logging.INFO)


def post(endpoint: str, data: Dict):
    """POST request wrapper"""
    response_ = requests.post(f"{BASE_URL}/{endpoint}", json=data, timeout=TIMEOUT, stream=endpoint == "ask")
    if endpoint != "ask":
        try:
            logging.info(f"{endpoint.capitalize()} Response: {response_.status_code}. Data: {response_.json()}")
        except Exception:
            logging.info(f"{endpoint.capitalize()} Response: {response_.status_code}")
    else:
        logging.info(f"{endpoint.capitalize()} Response: {response_.status_code}")
    return response_


def get(endpoint: str):
    """GET request wrapper"""
    response_ = requests.get(f"{BASE_URL}/{endpoint}", timeout=TIMEOUT)
    logging.info(f"{endpoint.capitalize()} Response: {response_.status_code}. Data: {response_.json()}")
    return response_


# Initialize module
response = post("init", {"module": "chatgpt"})

# Read module's status and wait until it's initialized (in Idle)
logging.info("Waiting for module initialization")
while True:
    response = get("status")
    chatgpt_status_code = response.json()[0].get("status_code")
    if chatgpt_status_code == 2:
        break
    time.sleep(1)

# Ask and read stream response
response = post("ask", {"chatgpt": {"prompt": "Hi! Please write a long text about AI", "convert_to_markdown": True}})
logging.info("Stream Response:")
for line in response.iter_lines():
    if line:
        logging.info(line.decode("utf-8"))

# Delete last conversation
response = post("delete", {"chatgpt": {"conversation_id": ""}})

# Close module (uninitialize it)
response = post("close", {"module": "chatgpt"})
```

#### 🌐 CURL

For CURL examples please read `📄 API docs` section

----------

## 📄 API docs

> ⚠️ Documentation is still under development!

### 🌐 Module initialization `/api/init`

Begins module initialization (in a separate, non-blocking thread)

> Please call `/api/status` to check if the module is initialized **BEFORE** calling `/api/init`.
>
> After calling `/api/init`, please call `/api/status` to **check if the module's initialization finished.**

**Request (POST):**

> Maximum content length: `100 bytes`. Default rate limits: `10/minute`, `1/second`

- Without authorization

    ```json
    {
        "module": "name of module from MODULES"
    }
    ```

- With authorization

    > Please see `🔒 HTTPS server and token-based authorization` section for more info

    ```json
    {
        "module": "name of module from MODULES",
        "token": "YourStrongRandomToken from --tokens argument"
    }
    ```

**Returns:**

- ✔️ If everything is ok: status code `200` and `{}` body
- ❌ Error codes `429`, `401` or `413` in case of rate limit, wrong token or too large request
- ❌ In case of other error: status code `400` or `500` and `{"error": "Error message"}` body

**Example:**

```shell
$ curl --request POST --header "Content-Type: application/json" --data '{"module": "chatgpt"}' http://localhost:1312/api/init
{}
```

----------

### 🌐 Status `/api/status`

Retrieves the current status of all modules

**Request (POST):**

> Maximum content length: `100 bytes`. Default rate limits: `1/second`

- Without authorization

    ```json
    {}
    ```

- With authorization

    > Please see `🔒 HTTPS server and token-based authorization` section for more info

    ```json
    {
        "token": "YourStrongRandomToken from --tokens argument"
    }
    ```

**Returns:**

- ✔️ If no errors during modules iteration: status code `200` and

```json
[
    {
        "module": "Name of the module from MODULES",
        "status_code": "Module's status code as an integer",
        "status_name": "Module's status as a string",
        "error": "Empty or module's error message"
    },
]
```

- ❌ Error codes `429`, `401` or `413` in case of rate limit, wrong token or too large request
- ❌ In case of an modules iteration error: status code `500` and `{"error": "Error message"}` body

**Example:**

```shell
$ curl --request POST --header "Content-Type: application/json" --data '{}' http://localhost:1312/api/status
[{"error":"","module":"chatgpt","status_code":2,"status_name":"Idle"}]
```

----------

### 🌐 Send request and get stream response `/api/ask`

Initiates a request to the specified module and streams responses back

> Please call `/api/status` to check if the module is initialized and not busy **BEFORE** calling `/api/ask`
>
> To stop the stream, please call `/api/stop`

**Request (POST):**

> Maximum content length: `100 bytes`. Default rate limits: `10/minute`, `1/second`

- Without authorization

    > For **ChatGPT**:

    ```text
    {
        "chatgpt": {
            "prompt": "Text request to send to the module",
            "conversation_id": "Optional conversation ID (to continue existing chat) or empty for a new conversation",
            "convert_to_markdown": true or false //(Optional flag for converting response to Markdown)
        }
    }
    ```

    > For **Microsoft Copilot**:

    ```text
    {
        "ms_copilot": {
            "prompt": "Text request",
            "image": image as base64 to include into request,
            "conversation_id": "empty string or existing conversation ID",
            "style": "creative" / "balanced" / "precise",
            "convert_to_markdown": True or False
        }
    }
    ```

- With authorization

    > Please see `🔒 HTTPS server and token-based authorization` section for more info

    > For **ChatGPT**:

    ```text
    {
        "chatgpt": {
            "prompt": "Text request to send to the module",
            "conversation_id": "Optional conversation ID (to continue existing chat) or empty for a new conversation",
            "convert_to_markdown": true or false //(Optional flag for converting response to Markdown)
        },
        "token": "YourStrongRandomToken from --tokens argument"
    }
    ```

    > For **Microsoft Copilot**:

    ```text
    {
        "ms_copilot": {
            "prompt": "Text request",
            "image": image as base64 to include into request,
            "conversation_id": "empty string or existing conversation ID",
            "style": "creative" / "balanced" / "precise",
            "convert_to_markdown": True or False
        },
        "token": "YourStrongRandomToken from --tokens argument"
    }
    ```

**Yields:**

- ✔️ A stream of JSON objects containing module responses

> For **ChatGPT**, each JSON object has the following structure:

```text
{
    "finished": "True if it's the last response, False if not",
    "message_id": "ID of the current message (from assistant)",
    "response": "Actual response as text"
}
```

> For **Microsoft Copilot**, each JSON object has the following structure:

```text
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
```

**Returns:**

- ❌ Error codes `429`, `401` or `413` in case of rate limit, wrong token or too large request
- ❌ In case of error: status code `500` and `{"error": "Error message"}` body

**Example:**

```shell
$ curl --request POST --header "Content-Type: application/json" --data '{"chatgpt": {"prompt": "Hi! Who are you?", "convert_to_markdown": true}}' http://localhost:1312/api/ask
{"finished": false, "conversation_id": "1033be5b-d37d-46b3-b47c-9548da5b192c", "message_id": "00d9cc0d-c4d9-484d-a8e5-9c78eaf2a0e1", "response": "Hello! I'm ChatGPT, an AI developed by O"}
...
{"finished": true, "conversation_id": "1033be5b-d37d-46b3-b47c-9548da5b192c", "message_id": "00d9cc0d-c4d9-484d-a8e5-9c78eaf2a0e1", "response": "Hello! I'm ChatGPT, an AI developed by OpenAI. I'm here to help answer your questions, engage in conversation, provide information, or assist you with anything else you might need. How can I assist you today?"}
```

----------

### 🌐 Stop stream response `/api/stop`

Stops the specified module's streaming response (stops yielding from `/api/ask`)

**Request (POST):**

> Maximum content length: `100 bytes`. Default rate limits: `1/second`

- Without authorization

    ```json
    {
        "module": "Name of the module from MODULES"
    }
    ```

- With authorization

    > Please see `🔒 HTTPS server and token-based authorization` section for more info

    ```json
    {
        "module": "Name of the module from MODULES",
        "token": "YourStrongRandomToken from --tokens argument"
    }
    ```

**Returns:**

- ✔️ If the stream stopped successfully: status code `200` and `{}` body
- ❌ Error codes `429`, `401` or `413` in case of rate limit, wrong token or too large request
- ❌ In case of an error: status code `400` or `500` and `{"error": "Error message"}` body

**Example:**

```shell
$ curl --request POST --header "Content-Type: application/json" --data '{"module": "chatgpt"}' http://localhost:1312/api/stop
{}
```

----------

### 🌐 Delete conversation `/api/delete`

Clears the module's conversation history

> Please call `/api/status` to check if the module is initialized and not busy **BEFORE** calling `/api/delete`

**Request (POST):**

> Maximum content length: `500 bytes`. Default rate limits: `10/minute`, `1/second`

- Without authorization

    > For **ChatGPT**:

    ```json
    {
        "chatgpt": {
            "conversation_id": "ID of conversation to delete or empty to delete the top one"
        }
    }
    ```

    > For **Microsoft Copilot**:

    ```json
    {
        "ms_copilot": {
            "conversation_id": "ID of conversation to delete or empty to delete the top one"
        }
    }
    ```

- With authorization

    > Please see `🔒 HTTPS server and token-based authorization` section for more info

    > For **ChatGPT**:

    ```json
    {
        "chatgpt": {
            "conversation_id": "ID of conversation to delete or empty to delete the top one"
        },
        "token": "YourStrongRandomToken from --tokens argument"
    }
    ```

    > For **Microsoft Copilot**:

    ```json
    {
        "ms_copilot": {
            "conversation_id": "ID of conversation to delete or empty to delete the top one"
        },
        "token": "YourStrongRandomToken from --tokens argument"
    }
    ```

**Returns:**

- ✔️ If conversation deleted successfully: status code `200` and `{}` body
- ❌ Error codes `429`, `401` or `413` in case of rate limit, wrong token or too large request
- ❌ In case of an error: status code `400` or `500` and `{"error": "Error message"}` body

**Example:**

```shell
$ curl --request POST --header "Content-Type: application/json" --data '{"chatgpt": {"conversation_id": "1033be5b-d37d-46b3-b47c-9548da5b192c"}}' http://localhost:1312/api/delete
{}
```

----------

### 🌐 Close module `/api/close`

Requests the module's session to close (in a separate, non-blocking thread)

> Please call `/api/status` to check if the module is initialized and its status is Idle or Failed **BEFORE** calling `/api/close`
>
> After calling `/api/close`, please call `/api/status` to **check if the module's closing finished**

**Request (POST):**

> Maximum content length: `500 bytes`. Default rate limits: `10/minute`, `1/second`

- Without authorization

    ```json
    {
        "module": "Name of the module from MODULES"
    }
    ```

- With authorization

    > Please see `🔒 HTTPS server and token-based authorization` section for more info

    ```json
    {
        "module": "Name of the module from MODULES",
        "token": "YourStrongRandomToken from --tokens argument"
    }
    ```

**Returns:**

- ✔️ If requested successfully: status code `200` and `{}` body
- ❌ Error codes `429`, `401` or `413` in case of rate limit, wrong token or too large request
- ❌ In case of an error: status code `400` or `500` and `{"error": "Error message"}` body

----------

## 🔒 HTTPS server and token-based authorization

> ⚠️ Better use proper SSL service and redirect to local port
>
> ⚠️ Don't use token-based authorization with bare HTTP (without any SSL). It's not safe!

It's possible to start SSL (HTTPS) server instead of HTTP. For that, provide `--ssl` argument with path to certificate file and path to private key file.

Example:

```shell
$ lmao --configs "configs" --ip "0.0.0.0" --port "1312" --ssl certificate.crt private.key
2024-04-19 02:09:10 INFO     Logging setup is complete
2024-04-19 02:09:10 INFO     Loading config files from configs directory
2024-04-19 02:09:10 INFO     Adding config of ms_copilot module
2024-04-19 02:09:10 INFO     Adding config of chatgpt module
2024-04-19 02:09:10 WARNING  No tokens provided. Everyone can use API
2024-04-19 02:09:10 INFO     Rate limits for all API requests except /status and /stop: 10/minute, 1/second
2024-04-19 02:09:10 INFO     Rate limits /status and /stop API requests: 1/second
 * Serving Flask app 'lmao.external_api'
 * Debug mode: off
2024-04-19 02:09:10 INFO     WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on https://127.0.0.1:1312
 * Running on https://192.168.0.3:1312
2024-04-19 02:09:10 INFO     Press CTRL+C to quit
...
```

Also you can enable token-based authorization. For that, provide `--tokens-use` argument with a list of some strong random tokens. Requests that provided these tokens can access `/status`, `/ask`, `/stop` and `/delete`. For `/init` and `/stop`, provide `--tokens-manage` argument with a list of some REALLY strong random tokens

⚠️ Make sure you provided at least one token to `--tokens-manage` if you're using `--tokens-use`. Otherwise **EVERYONE CAN ACCESS** `/init` and `/stop`

Example (tokens for `/status`, `/ask`, `/stop` and `/delete`: `naixae3eeNao6suu`, `kahMeixoo9un9OhR`. Token for `/init` and `/stop`: `ofi2ohRi8maish4x`):

```shell
$ lmao --configs "configs" --ip "0.0.0.0" --port "1312" --ssl certificate.crt private.key --tokens-use naixae3eeNao6suu kahMeixoo9un9OhR --tokens-manage ofi2ohRi8maish4x
2024-04-19 02:07:02 INFO     Logging setup is complete
2024-04-19 02:07:02 INFO     Loading config files from configs directory
2024-04-19 02:07:02 INFO     Adding config of ms_copilot module
2024-04-19 02:07:02 INFO     Adding config of chatgpt module
2024-04-19 02:07:02 INFO     Token-based authorization enabled. Provided 2 tokens-use
2024-04-19 02:07:02 INFO     Token-based authorization enabled. Provided 1 tokens-manage
2024-04-19 02:07:02 INFO     Rate limits for all API requests except /status and /stop: 10/minute, 1/second
2024-04-19 02:07:02 INFO     Rate limits /status and /stop API requests: 1/second
 * Serving Flask app 'lmao.external_api'
 * Debug mode: off
2024-04-19 02:07:02 INFO     WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:1312
 * Running on http://192.168.0.3:1312
2024-04-19 02:07:02 INFO     Press CTRL+C to quit
...
```
