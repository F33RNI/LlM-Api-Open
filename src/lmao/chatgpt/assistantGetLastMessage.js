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
function isGetLastMessageInjected() {
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
 * Parses code blocks, replaces inner HTML with placeholder (ex. "{CODE_BLOCK_fKGojDdEJ62s28nE}")
 * and appends their placeholders and content into codeBlocks
 * @param {*} element each child of assistant's response (recursively)
 * @param {*} codeBlocks dictionary for formatting {"placeholder": "code block content", ...}
 */
function preformatRecursion(element, codeBlocks) {
    // Code block
    if (element.tagName === "PRE") {
        try {
            // Extract rendered text
            let codeText = element.innerText;

            // Extract language and actual code from languageCopy codeactual code
            const codeLanguage = codeText.split("Copy code")[0].replace("\n", "").replace("\\n", "");

            // Extract actual code block content
            codeText = codeText.slice(codeLanguage.length + 9);

            // Create placeholder CODE_BLOCK_random16symbols (ex. CODE_BLOCK_fKGojDdEJ62s28nE)
            const placeholder = "CODE_BLOCK_" + makeid(16) + "";

            // Append for future formatting
            codeBlocks[placeholder] = codeText;

            // Replace content with placeholder
            element.innerHTML = "<code lang='" + codeLanguage + "'>{" + placeholder + "}</code>";
        }

        // For now just log an error
        catch (error) {
            console.log(error);
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
 * Tries to read and format the last assistant message
 * @param {boolean} raw false to use preformatRecursion(), true to return as is
 * @returns [assistantMessageID, responseContainerClassName, responseContainer.innerHTML, codeBlocks (as JSON)] or null
 */
function conversationGetLastMessage(raw) {
    try {
        // Select all assistant messages
        const assistantMessages = document.querySelectorAll("[data-message-author-role='assistant']");
        if (assistantMessages.length > 0) {
            // Get last one
            const assistantMessage = assistantMessages[assistantMessages.length - 1];

            // Extract message ID
            const assistantMessageID = assistantMessage.getAttribute("data-message-id");

            // Extract actual response parent
            const responseContainer = assistantMessage.firstChild.firstChild.cloneNode(true);

            // result-thinking or result-streaming or markdown
            const responseContainerClassName = responseContainer.className;

            // {"code block placeholder": "code block content", ...}
            const codeBlocks = {};

            // Parse each code block if now raw
            if (!raw) {
                for (const child of responseContainer.children) {
                    preformatRecursion(child, codeBlocks);
                }
            }

            // message ID, result-thinking or result-streaming or markdown, parsed code blocks, code blocks content
            return [assistantMessageID,
                responseContainerClassName,
                responseContainer.innerHTML,
                codeBlocks];
        }
    }

    // For now just log an error
    catch (error) {
        console.log(error);
    }

    return null;
}
