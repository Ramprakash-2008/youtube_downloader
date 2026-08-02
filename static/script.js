/* =========================================================
   CYBERTUBE DOWNLOADER
   MAIN JAVASCRIPT
   LIVE DOWNLOAD PROGRESS
   ========================================================= */


/* =========================================================
   ELEMENTS
   ========================================================= */

const urlInput = document.getElementById("youtube-url");
const fetchBtn = document.getElementById("fetch-btn");

const videoCard = document.getElementById("video-card");
const videoTitle = document.getElementById("video-title");
const videoDuration = document.getElementById("video-duration");

const formatSelect = document.getElementById("format");
const qualitySelect = document.getElementById("quality");

const downloadBtn = document.getElementById("download-btn");

const progressFill = document.getElementById("progress-fill");
const percentage = document.getElementById("percentage");
const statusText = document.getElementById("status");

const speedText = document.getElementById("speed");
const etaText = document.getElementById("eta");


/* =========================================================
   STATE
   ========================================================= */

let currentVideo = null;
let downloading = false;

let progressTimer = null;
let currentDownloadId = null;


/* =========================================================
   PAGE LOAD
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    resetProgress();

    if (videoCard) {
        videoCard.classList.add("hidden");
    }

});


/* =========================================================
   FETCH VIDEO
   ========================================================= */

async function fetchVideo() {

    const url = urlInput ? urlInput.value.trim() : "";

    if (!url) {

        showError(
            "Please paste a YouTube URL first."
        );

        return;
    }


    removeMessages();


    if (fetchBtn) {

        fetchBtn.disabled = true;
        fetchBtn.textContent = "FETCHING...";

    }


    setStatus(
        "Fetching video information...",
        10
    );


    try {

        const response = await fetch(
            "/fetch",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    url: url
                })
            }
        );


        const data = await response.json();


        if (!response.ok || !data.success) {

            throw new Error(
                data.error ||
                "Unable to fetch video information."
            );

        }


        currentVideo = data;


        displayVideoInfo(data);


        setStatus(
            "Video information loaded.",
            100
        );


    } catch (error) {

        console.error(
            "FETCH ERROR:",
            error
        );


        showError(
            error.message ||
            "Failed to fetch video information."
        );


        resetProgress();


    } finally {

        if (fetchBtn) {

            fetchBtn.disabled = false;
            fetchBtn.textContent = "FETCH";

        }

    }

}


/* =========================================================
   DISPLAY VIDEO INFORMATION
   ========================================================= */

function displayVideoInfo(data) {

    if (!videoCard) {
        return;
    }


    if (videoTitle) {

        videoTitle.textContent =
            data.title ||
            "Unknown title";

    }


    if (videoDuration) {

        videoDuration.textContent =
            data.duration ||
            "Unknown";

    }


    const thumbnail =
        videoCard.querySelector(
            ".thumbnail-wrapper img"
        );


    if (thumbnail && data.thumbnail) {

        thumbnail.src =
            data.thumbnail;

        thumbnail.alt =
            data.title ||
            "Video thumbnail";

    }


    const source =
        videoCard.querySelector(
            ".video-source"
        );


    if (source) {

        source.textContent =
            data.channel ||
            "YOUTUBE";

    }


    const channel =
        document.getElementById(
            "video-channel"
        );


    if (channel) {

        channel.textContent =
            data.channel ||
            "YouTube";

    }


    videoCard.classList.remove(
        "hidden"
    );

}


/* =========================================================
   START DOWNLOAD
   ========================================================= */

async function startDownload() {

    if (downloading) {
        return;
    }


    const url =
        urlInput
            ? urlInput.value.trim()
            : "";


    if (!url) {

        showError(
            "Please enter a YouTube URL."
        );

        return;

    }


    if (!currentVideo) {

        showError(
            "Please click FETCH before downloading."
        );

        return;

    }


    const format =
        formatSelect
            ? formatSelect.value
            : "mp4";


    const quality =
        qualitySelect
            ? qualitySelect.value
            : "720p";


    downloading = true;


    removeMessages();

    stopProgressPolling();

    currentDownloadId = null;

    resetProgress();


    if (downloadBtn) {

        downloadBtn.disabled = true;

        downloadBtn.innerHTML =
            '<span class="download-icon">⏳</span> DOWNLOADING...';

    }


    setStatus(
        "Starting download...",
        0
    );


    try {

        const response =
            await fetch(
                "/download",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        url: url,

                        format: format,

                        quality: quality

                    })

                }
            );


        const data =
            await response.json();


        if (!response.ok || !data.success) {

            throw new Error(
                data.error ||
                "Unable to start download."
            );

        }


        /*
         * Save job ID
         */

        currentDownloadId =
            data.job_id;


        /*
         * Start live progress
         */

        startProgressPolling();


    } catch (error) {

        console.error(
            "DOWNLOAD ERROR:",
            error
        );


        showError(
            error.message ||
            "Download failed."
        );


        downloading = false;

        restoreDownloadButton();

    }

}


/* =========================================================
   START PROGRESS POLLING
   ========================================================= */

function startProgressPolling() {

    stopProgressPolling();


    /*
     * Check immediately
     */

    checkDownloadProgress();


    /*
     * Then check every 500ms
     */

    progressTimer =
        setInterval(
            checkDownloadProgress,
            500
        );

}


/* =========================================================
   CHECK DOWNLOAD PROGRESS
   ========================================================= */

async function checkDownloadProgress() {

    if (!currentDownloadId) {
        return;
    }


    try {

        const response =
            await fetch(
                "/progress/" +
                encodeURIComponent(
                    currentDownloadId
                ),
                {
                    cache: "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                "Unable to read download progress."
            );

        }


        const data =
            await response.json();


        /*
         * PROGRESS
         */

        const progress =
            Number(
                data.progress || 0
            );


        setProgress(
            progress
        );


        /*
         * SPEED
         */

        if (speedText) {

            speedText.textContent =
                data.speed ||
                "—";

        }


        /*
         * ETA
         */

        if (etaText) {

            etaText.textContent =
                data.eta
                    ? "ETA " + data.eta
                    : "—";

        }


        /* -----------------------------------------
           STARTING
           ----------------------------------------- */

        if (
            data.status ===
            "starting"
        ) {

            setStatus(
                "Preparing download...",
                progress
            );

        }


        /* -----------------------------------------
           DOWNLOADING
           ----------------------------------------- */

        else if (
            data.status ===
            "downloading"
        ) {

            let message =
                "Downloading...";


            if (data.speed &&
                data.speed !== "--") {

                message +=
                    " " +
                    data.speed;

            }


            if (data.eta &&
                data.eta !== "--") {

                message +=
                    " • ETA " +
                    data.eta;

            }


            setStatus(
                message,
                progress
            );

        }


        /* -----------------------------------------
           PROCESSING
           ----------------------------------------- */

        else if (
            data.status ===
            "processing"
        ) {

            setStatus(
                "Processing video...",
                progress
            );


            if (speedText) {
                speedText.textContent = "—";
            }


            if (etaText) {
                etaText.textContent = "Processing";
            }

        }


        /* -----------------------------------------
           COMPLETED
           ----------------------------------------- */

        else if (
            data.status ===
            "completed"
        ) {

            stopProgressPolling();


            setProgress(
                100
            );


            setStatus(
                "Download completed!",
                100
            );


            if (speedText) {
                speedText.textContent = "—";
            }


            if (etaText) {
                etaText.textContent = "Complete";
            }


            /*
             * Download file to browser
             */

            if (data.file) {

                downloadFile(
                    data.file
                );

            }


            showSuccess(
                data.title ||
                (
                    currentVideo
                        ? currentVideo.title
                        : "Your video"
                )
            );


            downloading = false;

            restoreDownloadButton();


            currentDownloadId = null;


            return;

        }


        /* -----------------------------------------
           ERROR
           ----------------------------------------- */

        else if (
            data.status ===
            "error"
        ) {

            stopProgressPolling();


            throw new Error(
                data.error ||
                "Download failed."
            );

        }


    } catch (error) {

        console.error(
            "PROGRESS ERROR:",
            error
        );


        stopProgressPolling();


        showError(
            error.message ||
            "Download failed."
        );


        downloading = false;

        currentDownloadId = null;

        restoreDownloadButton();

    }

}


/* =========================================================
   STOP PROGRESS POLLING
   ========================================================= */

function stopProgressPolling() {

    if (progressTimer !== null) {

        clearInterval(
            progressTimer
        );

        progressTimer = null;

    }

}


/* =========================================================
   SET PROGRESS
   ========================================================= */

function setProgress(value) {

    value =
        Number(value);


    if (isNaN(value)) {
        value = 0;
    }


    value =
        Math.max(
            0,
            Math.min(
                100,
                value
            )
        );


    if (progressFill) {

        progressFill.style.width =
            value + "%";

    }


    if (percentage) {

        percentage.textContent =
            Math.round(value) +
            "%";

    }

}


/* =========================================================
   SET STATUS
   ========================================================= */

function setStatus(
    message,
    progress = null
) {

    if (statusText) {

        statusText.textContent =
            message;

    }


    if (progress !== null) {

        setProgress(
            progress
        );

    }

}


/* =========================================================
   RESET PROGRESS
   ========================================================= */

function resetProgress() {

    setProgress(
        0
    );


    if (statusText) {

        statusText.textContent =
            "READY TO DOWNLOAD";

    }


    if (speedText) {

        speedText.textContent =
            "—";

    }


    if (etaText) {

        etaText.textContent =
            "—";

    }

}


/* =========================================================
   DOWNLOAD FILE
   ========================================================= */

function downloadFile(filename) {

    if (!filename) {
        return;
    }


    const link =
        document.createElement(
            "a"
        );


    link.href =
        "/file/" +
        encodeURIComponent(
            filename
        );


    link.download =
        filename;


    link.style.display =
        "none";


    document.body.appendChild(
        link
    );


    link.click();


    link.remove();

}


/* =========================================================
   RESTORE DOWNLOAD BUTTON
   ========================================================= */

function restoreDownloadButton() {

    if (!downloadBtn) {
        return;
    }


    downloadBtn.disabled =
        false;


    downloadBtn.innerHTML =
        '<span class="download-icon">↓</span> DOWNLOAD';

}


/* =========================================================
   SUCCESS MESSAGE
   ========================================================= */

function showSuccess(title) {

    removeMessages();


    /*
     * If your HTML already has
     * #success-card, use it.
     */

    const existingCard =
        document.getElementById(
            "success-card"
        );


    if (existingCard) {

        existingCard.classList.remove(
            "hidden"
        );


        const titleElement =
            document.getElementById(
                "success-title"
            );


        if (titleElement) {

            titleElement.textContent =
                title ||
                "Your file is ready.";

        }


        return;

    }


    /*
     * Fallback dynamic card
     */

    const card =
        document.createElement(
            "div"
        );


    card.className =
        "success-card";


    card.id =
        "success-message";


    card.innerHTML = `

        <div class="success-icon">
            ✓
        </div>

        <div class="success-content">

            <strong>
                DOWNLOAD SUCCESSFUL
            </strong>

            <p>
                ${escapeHTML(title)}
            </p>

        </div>

    `;


    const progressSection =
        document.querySelector(
            ".progress-section"
        );


    if (progressSection) {

        progressSection
            .insertAdjacentElement(
                "afterend",
                card
            );

    }

}


/* =========================================================
   ERROR MESSAGE
   ========================================================= */

function showError(message) {

    removeMessages();


    /*
     * If HTML already has
     * #error-card, use it.
     */

    const existingCard =
        document.getElementById(
            "error-card"
        );


    if (existingCard) {

        existingCard.classList.remove(
            "hidden"
        );


        const errorMessage =
            document.getElementById(
                "error-message"
            );


        if (errorMessage) {

            errorMessage.textContent =
                message ||
                "Something went wrong.";

        }


        return;

    }


    /*
     * Fallback dynamic card
     */

    const card =
        document.createElement(
            "div"
        );


    card.className =
        "error-card";


    card.id =
        "error-message";


    card.innerHTML = `

        <div class="error-icon">
            !
        </div>

        <div>

            <strong>
                DOWNLOAD ERROR
            </strong>

            <p>
                ${escapeHTML(message)}
            </p>

        </div>

    `;


    const progressSection =
        document.querySelector(
            ".progress-section"
        );


    if (progressSection) {

        progressSection
            .insertAdjacentElement(
                "afterend",
                card
            );

    }

}


/* =========================================================
   REMOVE MESSAGES
   ========================================================= */

function removeMessages() {

    const dynamicSuccess =
        document.getElementById(
            "success-message"
        );


    const dynamicError =
        document.getElementById(
            "error-message"
        );


    if (dynamicSuccess) {

        dynamicSuccess.remove();

    }


    /*
     * Hide HTML success card
     */

    const successCard =
        document.getElementById(
            "success-card"
        );


    if (successCard) {

        successCard.classList.add(
            "hidden"
        );

    }


    /*
     * Hide HTML error card
     */

    const errorCard =
        document.getElementById(
            "error-card"
        );


    if (errorCard) {

        errorCard.classList.add(
            "hidden"
        );

    }

}


/* =========================================================
   DOWNLOAD ANOTHER
   ========================================================= */

function downloadAnother() {

    stopProgressPolling();


    currentDownloadId =
        null;


    downloading =
        false;


    removeMessages();


    currentVideo =
        null;


    resetProgress();


    if (videoCard) {

        videoCard.classList.add(
            "hidden"
        );

    }


    if (urlInput) {

        urlInput.value =
            "";

        urlInput.focus();

    }


    if (fetchBtn) {

        fetchBtn.disabled =
            false;

        fetchBtn.textContent =
            "FETCH";

    }


    restoreDownloadButton();


    window.scrollTo({

        top: 0,

        behavior: "smooth"

    });

}


/* =========================================================
   BACK TO HOME
   ========================================================= */

function goHome() {

    stopProgressPolling();


    currentDownloadId =
        null;


    window.location.href =
        "/";

}


/*
 * Your HTML currently uses goBack()
 * instead of goHome().
 *
 * Keep this alias so the BACK button works.
 */

function goBack() {

    goHome();

}


/* =========================================================
   ENTER KEY
   ========================================================= */

if (urlInput) {

    urlInput.addEventListener(
        "keydown",
        function(event) {

            if (
                event.key === "Enter" &&
                fetchBtn &&
                !fetchBtn.disabled
            ) {

                fetchVideo();

            }

        }
    );

}


/* =========================================================
   FORMAT CHANGE
   ========================================================= */

if (formatSelect) {

    formatSelect.addEventListener(
        "change",
        function() {

            if (
                this.value ===
                "mp3"
            ) {

                if (qualitySelect) {

                    qualitySelect.disabled =
                        true;

                }

            } else {

                if (qualitySelect) {

                    qualitySelect.disabled =
                        false;

                }

            }

        }
    );

}


/* =========================================================
   INITIAL FORMAT STATE
   ========================================================= */

if (
    formatSelect &&
    qualitySelect
) {

    qualitySelect.disabled =
        formatSelect.value ===
        "mp3";

}


/* =========================================================
   ESCAPE HTML
   ========================================================= */

function escapeHTML(text) {

    const div =
        document.createElement(
            "div"
        );


    div.textContent =
        text;


    return div.innerHTML;

}