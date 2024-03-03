# 🕊️ LLM-API-Open (LMAO)

| <img src="brandbook/Logo.png" height="auto" width="128" alt="PetalFlow logo"> | <h3>Unofficial open APIs for popular LLMs with self-hosted redirect capability</h3> |
| ----------------------------------------------------------------------------- | :---------------------------------------------------------------------------------: |

----------

## ❓ WAT

> 🕊️ LLM-API-Open (LMAO) allows for the free and universal utilization of popular Large Language Models (LLM).
> This is achieved using browser automation. LLM-API-Open (LMAO) launches a browser in headless mode and controls a website as if a real user were using it.
> This enables the use of popular LLMs that usually don't offer easy and free access to their official APIs
>
> 🔥 Additionally, LLM-API-Open (LMAO) is capable of creating its **own API server** to which any other apps can send requests.
> In other words, you can utilize LLM-API-Open (LMAO) both as a **Python package** and as an **API proxy** for any of your apps!

----------

## 🚧 LLM-API-Open is under heavy development

> 😔 Currently, LLM-API-Open has **only 1 module**: ChatGPT
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

### ⚙️ 1. Download / build / install LLM-API-Open

There is 4 general ways to get LLM-API-Open

#### ⚙️ Install via `pip`

- Install from GitHub directly

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

1. Download `config.json` from this repo
2. Open it in any editor and change the config of the modules you'll use
3. Specify path to `config.json` with `-c path/to/config.json` argument

----------

## 📦 Python package example

```python
import logging
import json

from lmao.module_wrapper import ModuleWrapper

# Initialize logging in a simplest way
logging.basicConfig(level=logging.INFO)

# Load and parse config
with open("config.json", "r", encoding="utf-8") as file:
    config = json.loads(file.read())
module_config = next((module_config for module_config in config if module_config.get("module") == "chatgpt"), None)

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

```shell
$ lmao --help        
usage: lmao [-h] [-v] [-c CONFIG] [-t TEST] [-i IP] [-p PORT] [--no-logging-init]

Unofficial open APIs for popular LLMs with self-hosted redirect capability

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -c CONFIG, --config CONFIG
                        path to config.json file (Default: config.json)
  -t TEST, --test TEST  module name to test in cli instead of starting API server (eg.
                        --test=chatgpt)
  -i IP, --ip IP        API server Host (IP) (Default: localhost)
  -p PORT, --port PORT  API server port (Default: 1312)
  --no-logging-init     specify to bypass logging initialization (will be set automatically when
                        using --test)

examples:
  lmao --test=chatgpt
  lmao --ip="0.0.0.0" --port=1312
  lmao --ip="0.0.0.0" --port=1312 --no-logging-init
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

## 🌐 API example using CURL

### Start server

```shell
$ lmao --config "config.json" --ip "0.0.0.0" --port "1312" 
2024-03-02 13:43:52 INFO     Logging setup is complete
2024-03-02 13:43:52 INFO     Loading config.json
 * Serving Flask app 'lmao.external_api'
 * Debug mode: off
2024-03-02 13:43:52 INFO     WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:1312
 * Running on http://192.168.0.3:1312
2024-03-02 13:43:52 INFO     Press CTRL+C to quit
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

```json
{
    "module": "name of module from MODULES"
}
```

**Returns:**

- ✔️ If everything is ok: status code `200` and `{}` body
- ❌ In case of an error: status code `400` or `500` and `{"error": "Error message"}` body

**Example:**

```shell
$ curl --request POST --header "Content-Type: application/json" --data '{"module": "chatgpt"}' http://localhost:1312/api/init
{}
```

----------

### 🌐 Status `/api/status`

Retrieves the current status of all modules

**Request (GET or POST):**

```json
{}
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

- ❌ In case of an modules iteration error: status code `500` and `{"error": "Error message"}` body

**Example:**

```shell
$ curl --request GET http://localhost:1312/api/status
[{"error":"","module":"chatgpt","status_code":2,"status_name":"Idle"}]
```

----------

### 🌐 Send request and get stream response `/api/ask`

Initiates a request to the specified module and streams responses back

> Please call `/api/status` to check if the module is initialized and not busy **BEFORE** calling `/api/ask`
>
> To stop the stream, please call `/api/stop`

**Request (POST):**

```text
{
    // For ChatGPT
    "chatgpt": {
        "prompt": "Text request to send to the module",
        "conversation_id": "Optional conversation ID (to continue existing chat) or empty for a new conversation",
        "convert_to_markdown": true or false (Optional flag for converting response to Markdown)
    }
}
```

**Yields:**

- ✔️ A stream of JSON objects containing module responses

> For ChatGPT, each JSON object has the following structure:

```text
{
    "finished": true if it's the last response false if not,
    "message_id": "ID of the current message (from assistant)",
    "response": "Actual response as text"
}
```

**Returns:**

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

```json
{
    "module": "Name of the module from MODULES"
}
```

**Returns:**

- ✔️ If the stream stopped successfully: status code `200` and `{}` body
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

**Request:**

For ChatGPT:

```json
{
    "chatgpt": {
        "conversation_id": "ID of conversation to delete or empty to delete the top one"
    }
}
```

**Returns:**

- ✔️ If conversation deleted successfully: status code `200` and `{}` body
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

**Request:**

```json
{
    "module": "Name of the module from MODULES"
}
```

**Returns:**

- ✔️ If requested successfully: status code `200` and `{}` body
- ❌ In case of an error: status code `400` or `500` and `{"error": "Error message"}` body
