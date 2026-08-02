from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import uuid
import threading
import shutil

app = Flask(__name__)

# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_DIR = os.path.join(
    BASE_DIR,
    "downloads"
)

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Render normally has ffmpeg available if installed
# through the Render environment.
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "")

download_jobs = {}


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok"
    })


# =========================================================
# FFMPEG CHECK
# =========================================================

def ffmpeg_available():
    """
    Check whether FFmpeg is available.
    """

    if FFMPEG_PATH:
        return os.path.exists(
            os.path.join(
                FFMPEG_PATH,
                "ffmpeg.exe"
            )
        ) or os.path.exists(
            os.path.join(
                FFMPEG_PATH,
                "ffmpeg"
            )
        )

    return shutil.which("ffmpeg") is not None


# =========================================================
# FORMAT DURATION
# =========================================================

def format_duration(seconds):

    if not seconds:
        return "Unknown"

    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"

    return f"{minutes}:{secs:02d}"


# =========================================================
# COMMON YT-DLP OPTIONS
# =========================================================

def get_base_options():

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }

    if FFMPEG_PATH:
        options["ffmpeg_location"] = FFMPEG_PATH

    return options


# =========================================================
# FETCH VIDEO INFORMATION
# =========================================================

@app.route("/fetch", methods=["POST"])
def fetch_video():

    data = request.get_json(silent=True) or {}

    url = data.get("url", "").strip()

    if not url:

        return jsonify({
            "success": False,
            "error": "Please enter a YouTube URL."
        }), 400

    try:

        options = get_base_options()

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

        return jsonify({

            "success": True,

            "title": info.get(
                "title",
                "Unknown title"
            ),

            "duration": format_duration(
                info.get("duration")
            ),

            "thumbnail": info.get(
                "thumbnail",
                ""
            ),

            "channel": info.get(
                "uploader",
                "YouTube"
            )

        })

    except Exception as e:

        error_message = str(e)

        print(
            "FETCH ERROR:",
            error_message
        )

        if (
            "Sign in to confirm" in error_message
            or "not a bot" in error_message
        ):

            error_message = (
                "YouTube is currently requiring "
                "additional verification for this request. "
                "Please try again later or use a different "
                "supported source."
            )

        return jsonify({

            "success": False,

            "error": error_message

        }), 500


# =========================================================
# PROGRESS HOOK
# =========================================================

def progress_hook(data, job_id):

    status = data.get("status")

    if status == "downloading":

        total = (
            data.get("total_bytes")
            or data.get("total_bytes_estimate")
            or 0
        )

        downloaded = (
            data.get("downloaded_bytes")
            or 0
        )

        if total > 0:

            progress = (
                downloaded / total
            ) * 100

            progress = max(
                0,
                min(progress, 99)
            )

        else:

            progress = 0

        speed = data.get("speed")

        eta = data.get("eta")

        if speed:

            if speed >= 1024 * 1024:

                speed_text = (
                    f"{speed / 1024 / 1024:.2f} MB/s"
                )

            else:

                speed_text = (
                    f"{speed / 1024:.1f} KB/s"
                )

        else:

            speed_text = "--"

        if eta is not None:

            eta_text = f"{eta}s"

        else:

            eta_text = "--"

        download_jobs[job_id] = {

            "status": "downloading",

            "progress": round(
                progress,
                1
            ),

            "speed": speed_text,

            "eta": eta_text

        }

    elif status == "finished":

        download_jobs[job_id] = {

            "status": "processing",

            "progress": 99,

            "speed": "--",

            "eta": "--"

        }


# =========================================================
# DOWNLOAD WORKER
# =========================================================

def download_worker(
    url,
    format_type,
    quality,
    job_id
):

    file_id = str(uuid.uuid4())

    try:

        # -------------------------------------------------
        # Validate quality
        # -------------------------------------------------

        try:

            height = int(
                quality.replace("p", "")
            )

        except Exception:

            height = 720

        # -------------------------------------------------
        # Output
        # -------------------------------------------------

        output_template = os.path.join(
            DOWNLOAD_DIR,
            f"{file_id}.%(ext)s"
        )

        # -------------------------------------------------
        # Base options
        # -------------------------------------------------

        options = {

            "outtmpl":
                output_template,

            "quiet":
                True,

            "no_warnings":
                True,

            "noplaylist":
                True,

            "progress_hooks": [

                lambda data:
                progress_hook(
                    data,
                    job_id
                )

            ]

        }

        # -------------------------------------------------
        # FFmpeg
        # -------------------------------------------------

        if FFMPEG_PATH:

            options[
                "ffmpeg_location"
            ] = FFMPEG_PATH

        # -------------------------------------------------
        # MP3
        # -------------------------------------------------

        if format_type == "mp3":

            if not ffmpeg_available():

                raise Exception(
                    "FFmpeg is required for MP3 "
                    "conversion but was not found."
                )

            options.update({

                "format":
                    "bestaudio/best",

                "postprocessors": [

                    {
                        "key":
                            "FFmpegExtractAudio",

                        "preferredcodec":
                            "mp3",

                        "preferredquality":
                            "192"
                    }

                ]

            })

        # -------------------------------------------------
        # MP4
        # -------------------------------------------------

        else:

            # Prefer a single MP4 stream when possible.
            # This avoids requiring a merge for every download.

            options.update({

                "format":
                    (
                        f"best[ext=mp4]"
                        f"[height<={height}]/"
                        f"best[height<={height}]/"
                        f"best"
                    ),

                "merge_output_format":
                    "mp4"

            })

        # -------------------------------------------------
        # Download
        # -------------------------------------------------

        download_jobs[job_id] = {

            "status":
                "starting",

            "progress":
                0,

            "speed":
                "--",

            "eta":
                "--"

        }

        print(
            f"STARTING DOWNLOAD: {job_id}"
        )

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

        title = info.get(
            "title",
            "download"
        )

        # -------------------------------------------------
        # Find generated file
        # -------------------------------------------------

        matching_files = [

            filename

            for filename in os.listdir(
                DOWNLOAD_DIR
            )

            if filename.startswith(file_id)

        ]

        if not matching_files:

            raise Exception(
                "Download finished but the output "
                "file could not be located."
            )

        filename = matching_files[0]

        # -------------------------------------------------
        # Complete
        # -------------------------------------------------

        download_jobs[job_id] = {

            "status":
                "completed",

            "progress":
                100,

            "speed":
                "--",

            "eta":
                "0",

            "file":
                filename,

            "title":
                title

        }

        print(
            f"DOWNLOAD COMPLETED: {filename}"
        )

    except Exception as e:

        error_message = str(e)

        print(
            "DOWNLOAD ERROR:",
            error_message
        )

        # -------------------------------------------------
        # Friendly YouTube verification error
        # -------------------------------------------------

        if (
            "Sign in to confirm" in error_message
            or "not a bot" in error_message
        ):

            error_message = (
                "YouTube is currently requiring "
                "additional verification for this request. "
                "The server cannot complete this download "
                "without YouTube verification."
            )

        # -------------------------------------------------
        # FFmpeg error
        # -------------------------------------------------

        elif "ffmpeg" in error_message.lower():

            error_message = (
                "FFmpeg is required for this video format "
                "but was not found on the server."
            )

        download_jobs[job_id] = {

            "status":
                "error",

            "progress":
                0,

            "speed":
                "--",

            "eta":
                "--",

            "error":
                error_message

        }


# =========================================================
# START DOWNLOAD
# =========================================================

@app.route("/download", methods=["POST"])
def start_download():

    data = request.get_json(silent=True) or {}

    url = data.get(
        "url",
        ""
    ).strip()

    format_type = data.get(
        "format",
        "mp4"
    )

    quality = data.get(
        "quality",
        "720p"
    )

    if not url:

        return jsonify({

            "success":
                False,

            "error":
                "No URL provided."

        }), 400

    if format_type not in (
        "mp4",
        "mp3"
    ):

        return jsonify({

            "success":
                False,

            "error":
                "Invalid format."

        }), 400

    job_id = str(
        uuid.uuid4()
    )

    download_jobs[job_id] = {

        "status":
            "starting",

        "progress":
            0,

        "speed":
            "--",

        "eta":
            "--"

    }

    thread = threading.Thread(

        target=download_worker,

        args=(

            url,
            format_type,
            quality,
            job_id

        ),

        daemon=True

    )

    thread.start()

    return jsonify({

        "success":
            True,

        "job_id":
            job_id

    })


# =========================================================
# LIVE PROGRESS
# =========================================================

@app.route(
    "/progress/<job_id>"
)
def get_progress(job_id):

    job = download_jobs.get(
        job_id
    )

    if not job:

        return jsonify({

            "success":
                False,

            "error":
                "Download job not found."

        }), 404

    return jsonify({

        "success":
            True,

        **job

    })


# =========================================================
# SERVE FILE
# =========================================================

@app.route(
    "/file/<filename>"
)
def serve_file(filename):

    safe_filename = os.path.basename(
        filename
    )

    filepath = os.path.join(
        DOWNLOAD_DIR,
        safe_filename
    )

    if not os.path.isfile(filepath):

        return jsonify({

            "success":
                False,

            "error":
                "File not found."

        }), 404

    return send_file(

        filepath,

        as_attachment=True

    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )
