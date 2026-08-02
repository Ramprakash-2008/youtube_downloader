# ⚡ CyberTube Downloader

> A modern, fast and responsive YouTube media downloader built with Flask, yt-dlp and FFmpeg.

CyberTube Downloader is a web-based media downloader that allows users to paste a YouTube URL, fetch video information, select the desired format and quality, and download the media directly through their browser.

The application features a cyber-themed user interface with real-time download progress, download speed, ETA, video information and responsive design.

---

## 🚀 Live Demo

🌐 **Live Application:**  
Coming soon

📦 **GitHub Repository:**  
https://github.com/Ramprakash-2008/YoutubeDownloader

---

## ✨ Features

### 🎬 Video Information

- Paste a YouTube URL
- Fetch video information before downloading
- Display video title
- Display video duration
- Display channel/uploader
- Display video thumbnail

### 📥 Media Download

- Download videos as MP4
- Download audio as MP3
- Select video quality
- Supports multiple resolutions
- Automatic format selection using `yt-dlp`
- FFmpeg-based video/audio merging

### 📊 Live Download Progress

CyberTube provides real-time download information including:

- Download percentage
- Download speed
- Estimated time remaining
- Download status
- Processing status
- Completion notification

The frontend continuously communicates with the Flask backend to retrieve the current download status.

### 🖥️ Modern Interface

- Cyber-themed UI
- Responsive design
- Dark interface
- Animated elements
- Clean download workflow
- Mobile-friendly layout
- No unnecessary file browser/browse option

### 🔒 Security Considerations

- Environment variables for configuration
- `.env` excluded from Git
- Safe filename handling
- Path traversal protection
- Server-side download processing

---

# 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| 🐍 Python | Backend programming |
| 🌐 Flask | Web framework |
| 📺 yt-dlp | Media extraction and downloading |
| 🎞️ FFmpeg | Video/audio processing |
| HTML5 | Page structure |
| CSS3 | User interface |
| JavaScript | Frontend logic & live progress |
| Git | Version control |
| GitHub | Source code hosting |

---

# 📂 Project Structure

```text
YoutubeDownloader/
│
├── app.py
│
├── requirements.txt
├── Procfile
├── .gitignore
├── .env
│
├── templates/
│   └── index.html
│
├── static/
│   ├── style.css
│   └── script.js
│
└── downloads/
