/**
 * Copyright (c) 2024 Fern Lane
 *
 * This file is part of LlM-Api-Open (LMAO) project.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

// driver.execute_async_script() callback
const callback = arguments[arguments.length - 1];

/**
 * Tries to click on "See all recent chats" button without raising any error
 */
function expandChats() {
    try {
        const seeAllBtn = document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-conversation-main > cib-side-panel").shadowRoot.querySelector("div.main > div.threads-container > div > div > button");
        if (seeAllBtn !== null) {
            seeAllBtn.click();
        }
    }

    // Just log and error
    catch (error) {
        console.error(error);
    }
}

/**
 * Tries to find chat by it's name. Please call expandChats() first and wait ~500ms
 * @param {string} conversationID unique name of chat
 * @param {boolean} strictEqual true to chatName === conversationID, false to chatName.includes(conversationID);
 * @returns shadowRoot of the chat container or null if not found
 */
function searchCibThreadContainer(conversationID, strictEqual) {
    // Array of all containers
    const cibThreads = document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-conversation-main > cib-side-panel").shadowRoot.querySelectorAll("#cib-threads-container > cib-thread");
    for (const cibThread of cibThreads) {
        cibThread.scrollIntoViewIfNeeded(true);
        const cibThreadShadowRoot = cibThread.shadowRoot;
        // const loadChatBtn = cibThreadShadowRoot.querySelector("div > div > button");
        // loadChatBtn.focus();
        const chatName = cibThreadShadowRoot.querySelector("#name").innerText;
        if ((strictEqual && chatName === conversationID) || (!strictEqual && chatName.includes(conversationID))) {
            return cibThreadShadowRoot;
        }
    }
    console.error("No conversation with id: " + conversationID);
    return null;
}

/**
 * Focuses on chat container -> waits 100ms -> presses rename button -> waits 500ms
 * -> renames and confirms -> return the same conversation ID
 * @param {string} conversationID new unique chat name
 */
function startRenameMode(conversationID) {
    const cibThreadContainer = document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-conversation-main > cib-side-panel").shadowRoot.querySelector("#cib-threads-container > cib-thread:nth-child(1)").shadowRoot;
    const loadChatBtn = cibThreadContainer.querySelector("div > div > button");
    loadChatBtn.focus();

    setTimeout(function () {
        try {
            const cibThreadContainer_ = document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-conversation-main > cib-side-panel").shadowRoot.querySelector("#cib-threads-container > cib-thread:nth-child(1)").shadowRoot;
            const renameBtn = cibThreadContainer_.querySelector("div > div > div.controls > button.edit.icon-button");
            renameBtn.click();

            setTimeout(function () {
                try {
                    renameChatAndConfirm(conversationID);
                    callback("" + conversationID);
                }

                // Log and return error as string
                catch (error) {
                    console.error(error);
                    callback("" + error);
                }
            }, 500);
        }

        // Log and return error as string
        catch (error) {
            console.error(error);
            callback("" + error);
        }
    }, 100);
}

/**
 * Renames last chat and confirms it's name (call startRenameMode() before)
 * @param {string} conversationID new unique chat name
 */
function renameChatAndConfirm(conversationID) {
    const cibThreadContainer = document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-conversation-main > cib-side-panel").shadowRoot.querySelector("#cib-threads-container > cib-thread:nth-child(1)").shadowRoot;
    const threadNameInput = cibThreadContainer.querySelector("div > div > div.description > input");
    threadNameInput.value = conversationID;
    const confirmBtn = cibThreadContainer.querySelector("div > div > div.controls > button.confirm.icon-button");
    confirmBtn.click();
}

// Extract arguments (action, conversation ID)
// Action can be "load", "delete" or "rename"
const action = arguments[0];
const conversationID = arguments[1];

try {
    // Open conversation (load it)
    if (action === "load") {
        // Expand all chats -> wait 500ms -> find conversation -> open it -> return the same conversation ID or "null"
        expandChats();
        setTimeout(function () {
            const cibThreadContainer = searchCibThreadContainer(conversationID, true);
            if (cibThreadContainer === null) {
                callback("" + null);
            }

            const loadChatBtn = cibThreadContainer.querySelector("div > div > button");
            loadChatBtn.focus();
            loadChatBtn.click();
            callback("" + conversationID);
        }, 500);
    }

    // Delete conversation
    else if (action === "delete") {
        // Expand all chats -> wait 500ms -> find conversation -> delete it -> return the same conversation ID or "null"
        expandChats();
        setTimeout(function () {
            const cibThreadContainer = searchCibThreadContainer(conversationID, false);
            if (cibThreadContainer === null) {
                callback("" + null);
            }

            const loadChatBtn = cibThreadContainer.querySelector("div > div > button");
            loadChatBtn.focus();
            const deleteChatBtn = cibThreadContainer.querySelector("div > div > div.controls > button.delete.icon-button");
            deleteChatBtn.click();
            callback("" + conversationID);
        }, 500);
    }

    // Rename conversation
    else if (action === "rename") {
        startRenameMode(conversationID);
    }
}

// Log and return error as string
catch (error) {
    console.error(error);
    callback("" + error);
}
