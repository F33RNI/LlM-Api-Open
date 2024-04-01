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

/**
 * Call this from python script to check if this file is injected
 * @returns true
 */
function isParseInjected() {
    return true;
}

/**
 * Creates random string
 * https://stackoverflow.com/a/1349426
 * @param {*} length length of string
 * @returns random string of length length
 */
function makeid(length) {
    let result = "";
    const characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    const charactersLength = characters.length;
    let counter = 0;
    while (counter < length) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
        counter += 1;
    }
    return result;
}

/**
 * @returns array of cib-chat-turn elements or an empty array in case of error
 */
function getCibChatTurns() {
    try {
        return [...document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-conversation-main").shadowRoot.querySelectorAll("#cib-chat-main > cib-chat-turn")];
    } catch (e) { }
    return [];
}

/**
 * @returns last message group where source is "bot" or null if no last bot message available. Can raise an error
 */
function getLastMessageGroupBot() {
    // Get chat turns and ignore empty array
    const cibChatTurns = getCibChatTurns();
    if (cibChatTurns.length === 0) {
        return null;
    }

    // Use only last chat turn
    const cibChatTurnLast = cibChatTurns[cibChatTurns.length - 1];

    // Get message groups and ignore empty list
    const responseMessageGroups = cibChatTurnLast.shadowRoot.querySelectorAll("cib-message-group.response-message-group");
    if (responseMessageGroups.length === 0) {
        return null;
    }

    // Use only the last message group
    const responseMessageGroupLast = responseMessageGroups[responseMessageGroups.length - 1];

    // Check source
    if (responseMessageGroupLast.getAttribute("source") === "bot") {
        return responseMessageGroupLast;
    }
    return null;
}

/**
 * @returns total number of messages where source is "bot" without raising any error
 */
function countMessagesBot() {
    let counter = 0;
    try {
        const cibChatTurns = getCibChatTurns();
        for (const cibChatTurn of cibChatTurns) {
            const responseMessageGroups = cibChatTurn.shadowRoot.querySelectorAll("cib-message-group.response-message-group");
            for (const responseMessageGroup of responseMessageGroups) {
                const cibMessages = responseMessageGroup.shadowRoot.querySelectorAll("cib-message");

                // Find bot's message
                for (const cibMessage of cibMessages) {
                    if (cibMessage.getAttribute("source") === "bot") {
                        counter++;
                    }
                }
            }
        }
    }

    // Just log an error
    catch (error) {
        console.error(error);
    }
    return counter;
}

/**
 * Parses code blocks and KaTeX, replaces inner HTML with placeholder (ex. "{CODE_BLOCK_fKGojDdEJ62s28nE}")
 * and appends their placeholders and content into codeBlocks
 * @param {*} element each child of assistant's response (recursively)
 * @param {*} codeBlocks dictionary for formatting {"placeholder": "code block content", ...}
 */
function preformatRecursion(element, codeBlocks) {
    // Code block
    if (element.tagName === "CIB-CODE-BLOCK") {
        try {
            // Extract clipboard data (actual code)
            const codeText = element.getAttribute("clipboard-data");

            // Extract language
            const codeLanguage = element.getAttribute("code-lang");

            // Create placeholder CODE_BLOCK_random16symbols (ex. CODE_BLOCK_fKGojDdEJ62s28nE)
            const placeholder = "CODE_BLOCK_" + makeid(16) + "";

            // Append for future formatting
            codeBlocks[placeholder] = codeText;

            // Replace content with placeholder
            element.outerHTML = "<pre><code lang='" + codeLanguage + "'>{" + placeholder + "}</code></pre>";
        }

        // Log error
        catch (error) {
            console.error(error);
        }
    }

    // KaTeX -> convert into annotation for future markdown parsing
    else if (element.className === "katex-block" || element.className === "katex") {
        try {
            const annotation = element.getElementsByTagName("annotation")[0].innerHTML;
            if (element.className === "katex-block") {
                const placeholder = "CODE_BLOCK_" + makeid(16) + "";
                codeBlocks[placeholder] = annotation;
                element.outerHTML = "<pre><code lang='latex'>{" + placeholder + "}</code></pre>";
            } else {
                element.outerHTML = "<code>" + annotation + "</code>";
            }
        }

        // Log error
        catch (error) {
            console.error(error);
        }
    }

    // Replace SUP citations with number in brackets (ex. [1])
    else if (element.tagName === "SUP" && element.className === "citation-sup") {
        try {
            const supParent = element.parentElement;
            if (supParent.tagName === "A" && supParent.getAttribute("href") !== null) {
                const supID = element.innerText;
                supParent.innerHTML = " [" + supID + "]";
            }
        }

        // Log error
        catch (error) {
            console.error(error);
        }
    }

    // Other element -> split into children and perform the same recursion
    else {
        for (const child of element.children) {
            preformatRecursion(child, codeBlocks);
        }
    }
}

/**
 * Parses last bot's message
 * @returns parsed bot's message as json with the following keys:
 * finalized: true or false - finalized attribute from the last message
 * images: [] - array of image URLs
 * caption: image caption as string
 * text: text response itself as HTML string
 * code_blocks: {"placeholder": "code block content", ...}
 */
function parseMessages() {
    // Gel all last bot's messages and ignore empty list
    const lastMessageGroupBot = getLastMessageGroupBot();
    if (lastMessageGroupBot.length === 0) {
        return {};
    }

    const result = {};

    const cibMessages = lastMessageGroupBot.shadowRoot.querySelectorAll("cib-message");

    // Get finalized attribute from the last message
    if (cibMessages.length !== 0) {
        result.finalized = cibMessages[cibMessages.length - 1].getAttribute("finalized") !== null;
    }

    // Parse each message block
    for (const cibMessage of cibMessages) {
        // Image response
        if (cibMessage.getAttribute("content") === "IMAGE") {
            // iframe inner document
            const iframeDocument = cibMessage.shadowRoot.querySelector("cib-shared > iframe").contentWindow.document;

            // Extract image caption from title
            try {
                const caption = iframeDocument.querySelector("#gir_async > a").getAttribute("title");
                result.caption = caption;
            } catch (error) {
                console.error(error);
            }

            // Parse image tags (extract clean links)
            result.images = [];
            const images = iframeDocument.getElementsByClassName("mimg");
            for (const image of images) {
                if (image.tagName !== "IMG" || !image.getAttribute("src")) {
                    continue;
                }
                const imageSrcClean = image.getAttribute("src").split("?")[0];
                result.images.push(imageSrcClean);
            }
        }

        // Meta response (ex. "Analyzing the image: Privacy blur hides faces from Copilot")
        else if (cibMessage.getAttribute("type") === "meta") {
            const metaContent = cibMessage.shadowRoot.querySelector("div.content");
            if (metaContent !== null) {
                result.meta = metaContent.innerText;
            }
        }

        // Text response
        else if (cibMessage.getAttribute("type") === "text") {
            // Get and check for text block
            const textBlock = cibMessage.shadowRoot.querySelector("cib-shared > div > div > div.ac-textBlock");
            if (textBlock !== null) {
                // Create a copy
                const textBlockClone = textBlock.cloneNode(true);

                // Find and fix code blocks
                // {"code block placeholder": "code block content", ...}
                const codeBlocks = {};
                for (const child of textBlockClone.children) {
                    preformatRecursion(child, codeBlocks);
                }

                if (result.text === undefined) {
                    result.text = textBlockClone.innerHTML;
                } else {
                    result.text += textBlockClone.innerHTML;
                }
                result.code_blocks = codeBlocks;
            }

            // No text block
            else {
                const textMessageContent = cibMessage.shadowRoot.querySelector("cib-shared > div.content.text-message-content");
                if (textMessageContent !== null) {
                    if (result.text === undefined) {
                        result.text = "<p>" + textMessageContent.innerText + "</p>";
                    } else {
                        result.text += "<p>" + textMessageContent.innerText + "</p>";
                    }
                }
            }
        }

        // Parse attributions
        let attributions = cibMessage.shadowRoot.querySelector("cib-message-attributions");
        if (attributions === null) {
            continue;
        }
        attributions = attributions.shadowRoot.querySelector("div > div.attribution-container > div.attribution-items");
        if (attributions === null) {
            continue;
        }
        attributions = attributions.getElementsByTagName("cib-attribution-item");
        if (attributions.length !== 0) {
            result.attributions = [];
            for (const attribution of attributions) {
                try {
                    const url = attribution.shadowRoot.querySelector("a.attribution-item").getAttribute("href");
                    const name = attribution.shadowRoot.querySelector("a.attribution-item > span.text-container").innerText;
                    result.attributions.push({ name, url });
                }

                // Just log an error
                catch (error) {
                    console.error(error);
                }
            }
        }
    }

    return result;
}

/**
 * Parses suggestion buttons without raising any error
 * @returns arrays of suggestions
 */
function parseSuggestions() {
    const suggestions = [];
    try {
        const suggestionItems = document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-conversation-main").shadowRoot.querySelector("div > div.scroller-positioner > div > cib-suggestion-bar").shadowRoot.querySelectorAll("ul > li > cib-suggestion-item");
        for (const suggestion of suggestionItems) {
            const button = suggestion.shadowRoot.querySelector("button");
            console.log(button);
            suggestions.push(button.innerText);
        }
    }

    // Just log an error
    catch (error) {
        console.error(error);
    }
    return suggestions;
}

/**
 * Finds captcha iframe, counts bot messages, parses response, parses suggestions or checks if response is finished
 * @param {string} action "captcha", "count", "parse", "suggestions" or "finished"
 * @returns action result or { "error": "exception text" }
 */
function actionHandle(action) {
    try {
        // Return captcha's iframe or null if no captcha without raising any error
        if (action === "captcha") {
            try {
                const lastMessageGroupBot = getLastMessageGroupBot();
                const cibMessages = lastMessageGroupBot.shadowRoot.querySelectorAll("cib-message");
                const cibMessageLast = cibMessages[cibMessages.length - 1];
                if (cibMessageLast.getAttribute("content") === "captcha") {
                    return cibMessageLast.shadowRoot.querySelector("iframe");
                }
            }

            // Just log an error
            catch (error) {
                console.error(error);
            }

            return null;
        }

        // Count number of bot's messages -> return number directly, because countMessagesBot() cannot raise any error
        else if (action === "count") {
            return countMessagesBot();
        }

        // Parse response -> return JSON
        else if (action === "parse") {
            return parseMessages();
        }

        // Parse suggestions return array directly, because parseSuggestions() cannot raise any error
        else if (action === "suggestions") {
            return parseSuggestions();
        }

        // Check if response finished
        else if (action === "finished") {
            // Check for "Stop responding button"
            const stopRespondingBtn = document.querySelector("#b_sydConvCont > cib-serp").shadowRoot.querySelector("#cib-action-bar-main").shadowRoot.querySelector("div > cib-typing-indicator").shadowRoot.querySelector("#stop-responding-button");
            if (stopRespondingBtn !== null && !stopRespondingBtn.disabled) {
                return false;
            }

            // Button is disabled -> check for image loading
            const lastMessageGroupBot = getLastMessageGroupBot();
            const cibMessages = lastMessageGroupBot.shadowRoot.querySelectorAll("cib-message");
            for (const cibMessage of cibMessages) {
                if (cibMessage.getAttribute("content") !== "IMAGE") {
                    continue;
                }
                const cibMessageIframe = cibMessage.shadowRoot.querySelector("cib-shared > iframe");
                if (cibMessageIframe === null) {
                    continue;
                }
                const iframeDocument = cibMessageIframe.contentWindow.document;
                if (iframeDocument.querySelector("#giloader").getAttribute("style") === "display: flex;") {
                    return false;
                }
            }
            return true;
        }
    }

    // Log and return error as string
    catch (error) {
        console.error(error);
        return { error: "" + error };
    }
}
