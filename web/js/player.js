/**
 * CineCloud Advanced Video Player
 * Features: Subtitle tracks, Audio tracks, Playback resume,
 * D-Pad / Keyboard controls, Scrubber timeline, Auto-hiding controls overlay.
 */

class CinePlayer {
  constructor() {
    this.container = document.getElementById("playerContainer");
    this.video = document.getElementById("cineVideo");
    this.controls = document.getElementById("playerControls");
    this.timelineWrap = document.getElementById("timelineWrap");
    this.timelineProgress = document.getElementById("timelineProgress");
    this.timelineBuffered = document.getElementById("timelineBuffered");
    this.currentTimeDisplay = document.getElementById("currentTimeDisplay");
    this.durationTimeDisplay = document.getElementById("durationTimeDisplay");
    this.playPauseBtn = document.getElementById("playPauseBtn");
    this.playIcon = document.getElementById("playIcon");
    this.pauseIcon = document.getElementById("pauseIcon");
    this.rewindBtn = document.getElementById("rewindBtn");
    this.forwardBtn = document.getElementById("forwardBtn");
    this.volumeBtn = document.getElementById("volumeBtn");
    this.volumeSlider = document.getElementById("volumeSlider");
    this.subtitleBtn = document.getElementById("subtitleBtn");
    this.subtitleMenu = document.getElementById("subtitleMenu");
    this.audioBtn = document.getElementById("audioBtn");
    this.audioMenu = document.getElementById("audioMenu");
    this.speedBtn = document.getElementById("speedBtn");
    this.speedMenu = document.getElementById("speedMenu");
    this.fullscreenBtn = document.getElementById("fullscreenBtn");
    this.playerExitBtn = document.getElementById("playerExitBtn");
    this.centerIndicator = document.getElementById("centerIndicator");
    this.resumePrompt = document.getElementById("playerResumePrompt");
    this.resumeYesBtn = document.getElementById("resumeYesBtn");
    this.resumeNoBtn = document.getElementById("resumeNoBtn");

    this.currentMovie = null;
    this.progressInterval = null;
    this.hideControlsTimer = null;
    this.isDraggingTimeline = false;
    this.savedWatchTime = 0;

    this.initEvents();
  }

  initEvents() {
    // Play / Pause
    this.playPauseBtn.addEventListener("click", () => this.togglePlay());
    this.video.addEventListener("click", () => this.togglePlay());

    // Exit
    this.playerExitBtn.addEventListener("click", () => this.close());

    // Seeking
    this.rewindBtn.addEventListener("click", () => this.seekBy(-10));
    this.forwardBtn.addEventListener("click", () => this.seekBy(10));

    // Timeline Drag / Click
    this.timelineWrap.addEventListener("click", (e) => this.seekToPosition(e));

    // Video Progress & Duration
    this.video.addEventListener("timeupdate", () => this.onTimeUpdate());
    this.video.addEventListener("loadedmetadata", () => this.onMetadataLoaded());
    this.video.addEventListener("progress", () => this.updateBufferProgress());
    this.video.addEventListener("ended", () => this.onEnded());

    // Volume
    this.volumeSlider.addEventListener("input", (e) => {
      this.video.volume = parseFloat(e.target.value);
      this.video.muted = this.video.volume === 0;
    });
    this.volumeBtn.addEventListener("click", () => {
      this.video.muted = !this.video.muted;
      this.volumeSlider.value = this.video.muted ? 0 : this.video.volume;
    });

    // Subtitles Menu
    this.subtitleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.closeAllMenus();
      this.subtitleMenu.classList.toggle("open");
    });

    // Audio Tracks Menu
    this.audioBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.closeAllMenus();
      this.audioMenu.classList.toggle("open");
    });

    // Speed Menu
    this.speedBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.closeAllMenus();
      this.speedMenu.classList.toggle("open");
    });

    this.speedMenu.querySelectorAll(".menu-item").forEach(item => {
      item.addEventListener("click", () => {
        const speed = parseFloat(item.dataset.speed);
        this.video.playbackRate = speed;
        this.speedBtn.textContent = `${speed}x`;
        this.speedMenu.querySelectorAll(".menu-item").forEach(i => i.classList.remove("active"));
        item.classList.add("active");
        this.speedMenu.classList.remove("open");
      });
    });

    // Fullscreen
    this.fullscreenBtn.addEventListener("click", () => this.toggleFullscreen());

    // Auto-hide controls overlay
    const resetTimer = () => {
      this.showControls();
      clearTimeout(this.hideControlsTimer);
      if (!this.video.paused) {
        this.hideControlsTimer = setTimeout(() => this.hideControls(), 3500);
      }
    };

    this.container.addEventListener("mousemove", resetTimer);
    this.container.addEventListener("keydown", resetTimer);

    // Close menus on outside click
    document.addEventListener("click", () => this.closeAllMenus());

    // Keyboard Shortcuts for Web and TV
    window.addEventListener("keydown", (e) => {
      if (this.container.style.display === "none") return;

      if (e.code === "Space" || e.key === " ") {
        e.preventDefault();
        this.togglePlay();
      } else if (e.code === "ArrowLeft" && e.target.tagName !== "INPUT") {
        e.preventDefault();
        this.seekBy(-10);
      } else if (e.code === "ArrowRight" && e.target.tagName !== "INPUT") {
        e.preventDefault();
        this.seekBy(10);
      } else if (e.code === "ArrowUp") {
        e.preventDefault();
        this.adjustVolume(0.1);
      } else if (e.code === "ArrowDown") {
        e.preventDefault();
        this.adjustVolume(-0.1);
      } else if (e.key === "f" || e.key === "F") {
        this.toggleFullscreen();
      } else if (e.key === "m" || e.key === "M") {
        this.video.muted = !this.video.muted;
      }
    });

    // Resume Prompt handlers
    this.resumeYesBtn.addEventListener("click", () => {
      this.video.currentTime = this.savedWatchTime;
      this.resumePrompt.style.display = "none";
      this.video.play();
    });

    this.resumeNoBtn.addEventListener("click", () => {
      this.video.currentTime = 0;
      this.resumePrompt.style.display = "none";
      this.video.play();
    });
  }

  showControls() {
    this.controls.classList.remove("hidden");
    this.container.style.cursor = "default";
  }

  hideControls() {
    if (this.video.paused) return;
    this.controls.classList.add("hidden");
    this.container.style.cursor = "none";
    this.closeAllMenus();
  }

  closeAllMenus() {
    this.subtitleMenu.classList.remove("open");
    this.audioMenu.classList.remove("open");
    this.speedMenu.classList.remove("open");
  }

  flashIndicator(iconSvgPath) {
    const icon = document.getElementById("centerIndicatorIcon");
    if (iconSvgPath) {
      icon.innerHTML = `<path d="${iconSvgPath}"/>`;
    }
    this.centerIndicator.classList.add("flash");
    setTimeout(() => {
      this.centerIndicator.classList.remove("flash");
    }, 400);
  }

  togglePlay() {
    if (this.video.paused || this.video.ended) {
      this.video.play();
      this.playIcon.style.display = "none";
      this.pauseIcon.style.display = "block";
      this.flashIndicator("M8 5v14l11-7z");
    } else {
      this.video.pause();
      this.playIcon.style.display = "block";
      this.pauseIcon.style.display = "none";
      this.flashIndicator("M6 19h4V5H6v14zm8-14v14h4V5h-4z");
      this.showControls();
    }
  }

  seekBy(seconds) {
    this.video.currentTime = Math.max(0, Math.min(this.video.duration || 0, this.video.currentTime + seconds));
    if (seconds > 0) {
      this.flashIndicator("M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z");
    } else {
      this.flashIndicator("M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z");
    }
  }

  adjustVolume(delta) {
    let newVol = Math.max(0, Math.min(1, this.video.volume + delta));
    this.video.volume = newVol;
    this.video.muted = newVol === 0;
    this.volumeSlider.value = newVol;
  }

  seekToPosition(e) {
    const rect = this.timelineWrap.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    if (this.video.duration) {
      this.video.currentTime = pos * this.video.duration;
    }
  }

  onTimeUpdate() {
    if (!this.video.duration) return;
    const current = this.video.currentTime;
    const duration = this.video.duration;

    const percent = (current / duration) * 100;
    this.timelineProgress.style.width = `${percent}%`;
    this.currentTimeDisplay.textContent = this.formatTime(current);
  }

  updateBufferProgress() {
    if (this.video.buffered.length > 0 && this.video.duration) {
      const bufferedEnd = this.video.buffered.end(this.video.buffered.length - 1);
      const percent = (bufferedEnd / this.video.duration) * 100;
      this.timelineBuffered.style.width = `${percent}%`;
    }
  }

  onMetadataLoaded() {
    this.durationTimeDisplay.textContent = this.formatTime(this.video.duration);
  }

  onEnded() {
    this.playIcon.style.display = "block";
    this.pauseIcon.style.display = "none";
    this.showControls();
    this.saveProgress(true);
  }

  formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return "00:00:00";
    const sec = Math.floor(seconds);
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  toggleFullscreen() {
    if (!document.fullscreenElement) {
      this.container.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
  }

  loadMovie(movie) {
    this.currentMovie = movie;
    document.getElementById("playerMovieTitle").textContent = movie.title;
    document.getElementById("playerMovieRes").textContent = movie.resolution || "1080p Full HD";

    // Clear old subtitle tracks
    while (this.video.firstChild) {
      this.video.removeChild(this.video.firstChild);
    }

    // Set Stream URL
    const token = localStorage.getItem("cinecloud_token");
    let streamUrl = movie.video_path;
    if (!streamUrl.startsWith("http")) {
      streamUrl = `/api/stream/${movie.id}`;
      if (token) {
        streamUrl += `?token=${encodeURIComponent(token)}`;
      }
    }
    this.video.src = streamUrl;

    // Build Subtitles Menu & Tracks
    this.setupSubtitles(movie);

    // Build Audio Tracks Menu
    this.setupAudioTracks(movie);

    // Show Container
    this.container.style.display = "flex";
    this.showControls();

    // Check watch progress for resume
    this.checkResumeProgress(movie);

    // Start auto-sync watch progress every 5 seconds
    if (this.progressInterval) clearInterval(this.progressInterval);
    this.progressInterval = setInterval(() => this.saveProgress(false), 5000);

    // Focus play button for TV navigation
    if (window.tvNav && window.tvNav.isTvMode) {
      setTimeout(() => window.tvNav.setFocus(this.playPauseBtn), 500);
    }
  }

  setupSubtitles(movie) {
    this.subtitleMenu.innerHTML = `<div class="menu-item active" data-sub="off">Subtitles: Off</div>`;
    const subtitles = movie.subtitles || [];

    subtitles.forEach((sub, idx) => {
      // Add track element
      const track = document.createElement("track");
      track.kind = "subtitles";
      track.label = sub.label;
      track.srclang = sub.language_code;
      track.src = sub.file_path.startsWith("http") ? sub.file_path : sub.file_path;
      this.video.appendChild(track);

      // Add to menu
      const item = document.createElement("div");
      item.className = "menu-item";
      item.dataset.sub = idx;
      item.textContent = sub.label;
      item.addEventListener("click", () => {
        for (let i = 0; i < this.video.textTracks.length; i++) {
          this.video.textTracks[i].mode = (i === idx) ? "showing" : "disabled";
        }
        this.subtitleMenu.querySelectorAll(".menu-item").forEach(m => m.classList.remove("active"));
        item.classList.add("active");
        this.subtitleMenu.classList.remove("open");
      });
      this.subtitleMenu.appendChild(item);
    });

    this.subtitleMenu.querySelector('[data-sub="off"]').addEventListener("click", () => {
      for (let i = 0; i < this.video.textTracks.length; i++) {
        this.video.textTracks[i].mode = "disabled";
      }
      this.subtitleMenu.querySelectorAll(".menu-item").forEach(m => m.classList.remove("active"));
      this.subtitleMenu.querySelector('[data-sub="off"]').classList.add("active");
      this.subtitleMenu.classList.remove("open");
    });
  }

  setupAudioTracks(movie) {
    this.audioMenu.innerHTML = "";
    const audioTracks = movie.audio_tracks || [
      { id: 1, label: "Original Audio (Stereo)", language_code: "en" }
    ];

    audioTracks.forEach((track, idx) => {
      const item = document.createElement("div");
      item.className = `menu-item ${idx === 0 ? "active" : ""}`;
      item.textContent = track.label;
      item.addEventListener("click", () => {
        this.audioMenu.querySelectorAll(".menu-item").forEach(m => m.classList.remove("active"));
        item.classList.add("active");
        document.getElementById("playerMovieAudio").textContent = track.label;
        this.audioMenu.classList.remove("open");
      });
      this.audioMenu.appendChild(item);
    });
  }

  async checkResumeProgress(movie) {
    this.savedWatchTime = 0;
    this.resumePrompt.style.display = "none";

    const token = localStorage.getItem("cinecloud_token");
    if (!token) {
      this.video.play().catch(() => {});
      return;
    }

    try {
      const res = await fetch(`/api/progress/${movie.id}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.progress && !data.progress.is_completed && data.progress.current_time > 15) {
        this.savedWatchTime = data.progress.current_time;
        document.getElementById("resumePromptText").textContent = 
          `Resume watching from ${this.formatTime(this.savedWatchTime)}?`;
        this.resumePrompt.style.display = "flex";
        if (window.tvNav && window.tvNav.isTvMode) {
          window.tvNav.setFocus(this.resumeYesBtn);
        }
      } else {
        this.video.play().catch(() => {});
      }
    } catch (e) {
      this.video.play().catch(() => {});
    }
  }

  async saveProgress(isCompleted = false) {
    if (!this.currentMovie || !this.video.duration) return;
    const token = localStorage.getItem("cinecloud_token");
    if (!token) return;

    try {
      await fetch(`/api/progress/${this.currentMovie.id}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          currentTime: this.video.currentTime,
          duration: this.video.duration,
          isCompleted: isCompleted
        })
      });
    } catch (e) {
      // Background sync
    }
  }

  close() {
    this.saveProgress(false);
    if (this.progressInterval) clearInterval(this.progressInterval);
    this.video.pause();
    this.video.src = "";
    this.container.style.display = "none";
    if (document.fullscreenElement) {
      document.exitFullscreen?.().catch(() => {});
    }
    // Refresh continue watching rail
    if (window.cineApp) {
      window.cineApp.loadCategories();
    }
  }
}

window.cinePlayer = new CinePlayer();
