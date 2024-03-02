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
 * @returns array of valid <li> tags (conversations)
 */
function getValidLiTags() {
    // Final array
    const validTags = [];

    // List all possibly valid tags
    const liTags = document.getElementsByTagName("li");
    for (const liTag of liTags) {
        // Check parent
        if (liTag.parentElement === undefined || liTag.parentElement.tagName !== "OL") continue;

        // Get <a> tags
        const aTags = liTag.getElementsByTagName("a");

        // Check size
        if (aTags.length === 0) continue;

        // Check for href attribute
        if (!aTags[0].hasAttribute("href")) continue;

        // Check for buttons
        if (liTag.getElementsByTagName("button").length === 0) continue;

        // Seems ok -> append to the array
        validTags.push(liTag);
    }

    // Sort array by Y position (just in case)
    if (validTags.length > 1) {
        return Array.from(validTags).sort((a, b) => {
            const aRect = a.getBoundingClientRect();
            const bRect = b.getBoundingClientRect();
            return aRect.top - bRect.top;
        });
    }

    // Return without sorting
    return validTags;
}

/**
 * Recursively searches for conversation in side menu and returns it's expand menu button
 * @param {string} conversationId ID of conversation to look for
 * @returns expand menu button
 */
function conversationSearch(conversationId) {
    // Log conversation ID
    console.log("Searching " + conversationId + " recursively");
    try {
        // List all currently visible chats (right menu)
        const chatBlocks = document.querySelectorAll(".relative.mt-5");
        if (chatBlocks.length === 0) {
            throw new Error("No chats found");
        }

        // List all chat containers
        const chatLis = getValidLiTags();

        // Check length
        if (chatLis.length === 0) {
            throw new Error(`No li tags found! Chat with conversation ID ${conversationId} doesn't exist`);
        }

        // Look in each <li> tag
        for (const chatLi of chatLis) {
            // Scroll to it
            chatLi.scrollIntoView(true);

            // Get the first <a> tag
            const chatA = chatLi.getElementsByTagName("a")[0];

            // Extract chat link
            const chatHref = chatA.getAttribute("href");

            // Check if it's our conversation that we need to delete
            if (!chatHref.endsWith(conversationId)) continue;

            // List all expand menu buttons
            for (const chatExpandButton of chatLi.getElementsByTagName("button")) {
                // Check for aria-haspopup attribute
                if (!chatExpandButton.hasAttribute("aria-haspopup")) continue;
                const chatExpandButtonAriaHaspopup = chatExpandButton.getAttribute("aria-haspopup");
                if (chatExpandButtonAriaHaspopup === "menu") {
                    // Focus on <a> tag
                    // chatA.focus();

                    // Click into <a> tag (to open conversation)
                    // chatA.click();

                    // Return <a> tag and expand button
                    callback([chatA, chatExpandButton]);

                    // Exit from recursion
                    console.log("Expand button found successfully");
                    return;
                }
            }
        }

        // Get chats before start scrolling
        const chatLisBefore = getValidLiTags();
        console.log("Found " + chatLisBefore.length + " <li> tags before starting scrolling");

        // Wait for new elements to appear or timeout (5 seconds)
        let scrolledToFirst = false;
        const timeStarted = Date.now();
        const spinnerInterval = setInterval(function () {
            try {
                // Get new <li> tags
                const chatLisAfter = getValidLiTags();

                // New tags or timeout
                if (chatLisAfter.length !== chatLisBefore.length || Date.now() - timeStarted > 5000) {
                    clearInterval(spinnerInterval);
                    console.log("Scroll finished");

                    // Check if we found new tags
                    if (chatLisAfter.length === chatLisBefore.length) {
                        throw new Error(`Timeout waiting for new <li> tags 
                or chat with conversation ID ${conversationId} doesn't exist`);
                    }

                    // Log number of new <li> tags
                    console.log("Found " + chatLisAfter.length + " <li> tags after scrolling");

                    // Call self again (recursion)
                    conversationSearch(conversationId);
                }

                // No new elements
                else {
                    if (!scrolledToFirst) {
                        // Scroll and focus on the first element
                        chatLisAfter[0].scrollIntoView(true);
                        chatLisAfter[0].getElementsByTagName("a")[0].focus();
                        scrolledToFirst = true;

                        // Wait 100 ms
                        setTimeout(() => {
                            // Scroll to the last element
                            chatLisAfter[chatLisAfter.length - 1].scrollIntoView(true);
                            chatLisAfter[chatLisAfter.length - 1].getElementsByTagName("a")[0].focus();
                        }, 100);
                    }

                    // Scroll and focus to the last element
                    else {
                        chatLisAfter[chatLisAfter.length - 1].scrollIntoView(true);
                        chatLisAfter[chatLisAfter.length - 1].getElementsByTagName("a")[0].focus();
                    }
                }
            } catch (error) {
                // Log and return error
                console.error(error);
                callback("" + error);
            }
        }, 200);
    } catch (error) {
        // Log and return error
        console.error(error);
        callback("" + error);
    }
}

// Enter recursion
conversationSearch(arguments[0]);
