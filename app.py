from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import uuid
import threading
import time
from dotenv import load_dotenv

load_dotenv()

FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "").strip()
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

# =========================================================
# FFMPEG
# =========================================================
#
# LOCAL WINDOWS:
# Set environment variable:
#
# FFMPEG_PATH=D:\app\ffmpeg-8.0.1-essentials_build\bin
#
# RENDER:
# Leave FFMPEG_PATH empty if ffmpeg is installed
# and available in PATH.
#
# =========================================================



# =========================================================
# DOWNLOAD JOB STORAGE
# =========================================================

download_jobs = {}

jobs_lock = threading.Lock()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


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

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }

        if FFMPEG_PATH:
            options["ffmpeg_location"] = FFMPEG_PATH

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

        # -------------------------------------------------
        # DURATION
        # -------------------------------------------------

        duration = info.get("duration")

        if duration:

            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60

            if hours > 0:

                duration_text = (
                    f"{hours}:{minutes:02d}:{seconds:02d}"
                )

            else:

                duration_text = (
                    f"{minutes}:{seconds:02d}"
                )

        else:

            duration_text = "Unknown"

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "title": info.get(
                "title",
                "Unknown title"
            ),

            "duration": duration_text,

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

        print("FETCH ERROR:", e)

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# UPDATE PROGRESS
# =========================================================

def update_job(job_id, **values):

    with jobs_lock:

        if job_id in download_jobs:

            download_jobs[job_id].update(values)


# =========================================================
# PROGRESS HOOK
# =========================================================

def progress_hook(data, job_id):

    status = data.get("status")

    # -----------------------------------------------------
    # DOWNLOADING
    # -----------------------------------------------------

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

        # -------------------------------------------------
        # PERCENTAGE
        # -------------------------------------------------

        if total > 0:

            percentage = (
                downloaded / total
            ) * 100

            percentage = max(
                0,
                min(percentage, 99)
            )

        else:

            percentage = 0

        # -------------------------------------------------
        # SPEED
        # -------------------------------------------------

        speed = data.get("speed")

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

        # -------------------------------------------------
        # ETA
        # -------------------------------------------------

        eta = data.get("eta")

        if eta is not None:

            if eta >= 60:

                minutes = eta // 60
                seconds = eta % 60

                eta_text = (
                    f"{minutes}m {seconds}s"
                )

            else:

                eta_text = f"{eta}s"

        else:

            eta_text = "--"

        # -------------------------------------------------
        # UPDATE JOB
        # -------------------------------------------------

        update_job(

            job_id,

            status="downloading",

            progress=round(
                percentage,
                1
            ),

            speed=speed_text,

            eta=eta_text

        )

    # -----------------------------------------------------
    # DOWNLOAD FINISHED / PROCESSING
    # -----------------------------------------------------

    elif status == "finished":

        update_job(

            job_id,

            status="processing",

            progress=99,

            speed="--",

            eta="--"

        )


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
        # QUALITY
        # -------------------------------------------------

        try:

            height = int(
                quality.replace("p", "")
            )

        except:

            height = 720

        # -------------------------------------------------
        # OUTPUT
        # -------------------------------------------------

        output_template = os.path.join(

            DOWNLOAD_DIR,

            f"{file_id}.%(ext)s"

        )

        # -------------------------------------------------
        # COMMON OPTIONS
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
        # FFMPEG
        # -------------------------------------------------

        if FFMPEG_PATH:

            options[
                "ffmpeg_location"
            ] = FFMPEG_PATH

        # -------------------------------------------------
        # MP3
        # -------------------------------------------------

        if format_type == "mp3":

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

            options.update({

                "format":
                    (
                        f"bv*[height<={height}]+ba/b"
                    ),

                "merge_output_format":
                    "mp4"

            })

        # -------------------------------------------------
        # STARTING
        # -------------------------------------------------

        update_job(

            job_id,

            status="starting",

            progress=0,

            speed="--",

            eta="--"

        )

        # -------------------------------------------------
        # DOWNLOAD
        # -------------------------------------------------

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(

                url,

                download=True

            )

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        title = info.get(
            "title",
            "download"
        )

        # -------------------------------------------------
        # FIND OUTPUT FILE
        # -------------------------------------------------

        matching_files = [

            file

            for file in os.listdir(
                DOWNLOAD_DIR
            )

            if file.startswith(file_id)

        ]

        if not matching_files:

            raise Exception(
                "Download completed but the file was not found."
            )

        filename = matching_files[0]

        # -------------------------------------------------
        # COMPLETE
        # -------------------------------------------------

        update_job(

            job_id,

            status="completed",

            progress=100,

            speed="--",

            eta="0",

            file=filename,

            title=title

        )

        print(
            f"DOWNLOAD COMPLETED: {filename}"
        )

    except Exception as e:

        print(
            "DOWNLOAD ERROR:",
            e
        )

        update_job(

            job_id,

            status="error",

            progress=0,

            speed="--",

            eta="--",

            error=str(e)

        )


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

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not url:

        return jsonify({

            "success": False,

            "error":
                "No URL provided."

        }), 400

    if format_type not in (
        "mp4",
        "mp3"
    ):

        return jsonify({

            "success": False,

            "error":
                "Invalid format."

        }), 400

    # -----------------------------------------------------
    # CREATE JOB
    # -----------------------------------------------------

    job_id = str(
        uuid.uuid4()
    )

    with jobs_lock:

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

    # -----------------------------------------------------
    # START BACKGROUND THREAD
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # RETURN JOB ID IMMEDIATELY
    # -----------------------------------------------------

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
    "/progress/<job_id>",
    methods=["GET"]
)
def get_progress(job_id):

    with jobs_lock:

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

        result = dict(job)

    return jsonify({

        "success":
            True,

        **result

    })


# =========================================================
# SERVE DOWNLOADED FILE
# =========================================================

@app.route(
    "/file/<filename>",
    methods=["GET"]
)
def serve_file(filename):

    # -----------------------------------------------------
    # SECURITY
    # -----------------------------------------------------

    safe_filename = os.path.basename(
        filename
    )

    filepath = os.path.join(

        DOWNLOAD_DIR,

        safe_filename

    )

    # -----------------------------------------------------
    # CHECK FILE
    # -----------------------------------------------------

    if not os.path.isfile(filepath):

        return jsonify({

            "success":
                False,

            "error":
                "File not found."

        }), 404

    # -----------------------------------------------------
    # SEND FILE
    # -----------------------------------------------------

    return send_file(

        filepath,

        as_attachment=True,

        download_name=safe_filename

    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({

        "status":
            "ok"

    })


# =========================================================
# CLEAN OLD FILES
# =========================================================

def cleanup_old_files():

    while True:

        try:

            now = time.time()

            for filename in os.listdir(
                DOWNLOAD_DIR
            ):

                filepath = os.path.join(

                    DOWNLOAD_DIR,

                    filename

                )

                if not os.path.isfile(filepath):
                    continue

                # Delete files older than 1 hour
                if (
                    now -
                    os.path.getmtime(filepath)
                    > 3600
                ):

                    try:

                        os.remove(filepath)

                        print(
                            f"Deleted old file: {filename}"
                        )

                    except Exception as e:

                        print(
                            "Cleanup error:",
                            e
                        )

        except Exception as e:

            print(
                "Cleanup thread error:",
                e
            )

        time.sleep(600)


# =========================================================
# START CLEANUP THREAD
# =========================================================

cleanup_thread = threading.Thread(

    target=cleanup_old_files,

    daemon=True

)

cleanup_thread.start()


# =========================================================
# LOCAL DEVELOPMENT
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