/**
 * CineCloud Admin Studio & Resumable Uploader
 * Supports large video chunking from mobile phones & laptops.
 */

class CineAdmin {
  constructor() {
    this.dropZone = document.getElementById("dropZone");
    this.movieFileInput = document.getElementById("movieFileInput");
    this.selectedFileInfo = document.getElementById("selectedFileInfo");
    this.uploadProgressWrap = document.getElementById("uploadProgressWrap");
    this.uploadProgressBar = document.getElementById("uploadProgressBar");
    this.uploadStatusText = document.getElementById("uploadStatusText");
    this.uploadPercentText = document.getElementById("uploadPercentText");
    this.uploadForm = document.getElementById("uploadMovieForm");
    this.adminMovieList = document.getElementById("adminMovieList");
    this.refreshAdminBtn = document.getElementById("refreshAdminBtn");

    this.currentFile = null;
    this.uploadedVideoData = null;
    this.initEvents();
  }

  initEvents() {
    if (!this.dropZone) return;

    // Click to select (prevent event loop)
    this.dropZone.addEventListener("click", () => this.movieFileInput.click());
    this.movieFileInput.addEventListener("click", (e) => e.stopPropagation());

    // File selected
    this.movieFileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        this.handleFileSelected(e.target.files[0]);
      }
    });

    // Drag and drop
    this.dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      this.dropZone.style.borderColor = "var(--accent-cyan)";
      this.dropZone.style.background = "rgba(6, 182, 212, 0.1)";
    });

    this.dropZone.addEventListener("dragleave", () => {
      this.dropZone.style.borderColor = "rgba(6, 182, 212, 0.4)";
      this.dropZone.style.background = "rgba(6, 182, 212, 0.03)";
    });

    this.dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      this.dropZone.style.borderColor = "rgba(6, 182, 212, 0.4)";
      this.dropZone.style.background = "rgba(6, 182, 212, 0.03)";
      if (e.dataTransfer.files.length > 0) {
        this.handleFileSelected(e.dataTransfer.files[0]);
      }
    });

    // Form submit
    this.uploadForm.addEventListener("submit", (e) => this.handleFormSubmit(e));

    // Refresh
    if (this.refreshAdminBtn) {
      this.refreshAdminBtn.addEventListener("click", () => this.loadAdminMovies());
    }
  }

  handleFileSelected(file) {
    this.currentFile = file;
    this.selectedFileInfo.style.display = "block";
    this.selectedFileInfo.textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;

    // Auto-fill title if empty
    const titleInput = document.getElementById("movieTitleInput");
    if (!titleInput.value) {
      const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[\._\-]/g, " ");
      titleInput.value = cleanName.charAt(0).toUpperCase() + cleanName.slice(1);
    }
  }

  async uploadFileInChunks(file) {
    const CHUNK_SIZE = 2 * 1024 * 1024; // 2 MB chunks
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    const uploadId = "up_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
    const token = localStorage.getItem("cinecloud_token");

    this.uploadProgressWrap.style.display = "block";
    this.uploadStatusText.textContent = "Uploading video chunks to cloud...";

    for (let i = 0; i < totalChunks; i++) {
      const start = i * CHUNK_SIZE;
      const end = Math.min(file.size, start + CHUNK_SIZE);
      const chunk = file.slice(start, end);

      const formData = new FormData();
      formData.append("chunk", chunk, `part_${i}.bin`);
      formData.append("uploadId", uploadId);
      formData.append("chunkIndex", i);
      formData.append("totalChunks", totalChunks);
      formData.append("filename", file.name);

      const headers = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/upload/chunk", {
        method: "POST",
        headers: headers,
        body: formData
      });

      if (!res.ok) {
        throw new Error("Failed to upload chunk " + (i + 1) + "/" + totalChunks);
      }

      const data = await res.json();
      const percent = Math.round(((i + 1) / totalChunks) * 100);
      this.uploadProgressBar.style.width = `${percent}%`;
      this.uploadPercentText.textContent = `${percent}%`;
      this.uploadStatusText.textContent = `Uploading chunks: ${i + 1}/${totalChunks} (${percent}%)...`;

      if (data.complete) {
        this.uploadStatusText.textContent = "Upload complete! Processing video metadata...";
        return data;
      }
    }
  }

  async handleFormSubmit(e) {
    e.preventDefault();
    let token = localStorage.getItem("cinecloud_token");
    if (!token) {
      // Auto-authenticate as admin for seamless single-user personal streaming
      try {
        const loginRes = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: "admin", password: "admin123" })
        });
        const loginData = await loginRes.json();
        if (loginData.token) {
          token = loginData.token;
          localStorage.setItem("cinecloud_token", token);
          if (window.cineApp) window.cineApp.checkAuth();
        }
      } catch (err) {
        console.warn("Auto-login error", err);
      }
    }

    const submitBtn = document.getElementById("saveMovieSubmitBtn");
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>Uploading...</span>`;

    const title = document.getElementById("movieTitleInput").value;
    const year = parseInt(document.getElementById("movieYearInput").value) || 2025;
    const genre = document.getElementById("movieGenreInput").value;
    const rating = parseFloat(document.getElementById("movieRatingInput").value) || 8.0;
    const desc = document.getElementById("movieDescInput").value;
    let posterUrl = document.getElementById("moviePosterInput").value;
    let backdropUrl = document.getElementById("movieBackdropInput").value;
    const isFeatured = document.getElementById("movieFeaturedInput").checked;

    let videoPath = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4";
    let resolution = "1080p Full HD";
    let duration = 5400;
    let fileSize = 1500000000;

    // If a local video file was selected, upload it in chunks first
    if (this.currentFile) {
      try {
        const uploadResult = await this.uploadFileInChunks(this.currentFile);
        videoPath = uploadResult.video_path;
        resolution = uploadResult.resolution || resolution;
        duration = uploadResult.duration || duration;
        fileSize = uploadResult.file_size || fileSize;
        if (!posterUrl && uploadResult.auto_poster) {
          posterUrl = uploadResult.auto_poster;
        }
      } catch (err) {
        alert("Upload error: " + err.message);
        return;
      }
    }

    // Default poster fallback if left blank
    if (!posterUrl) {
      posterUrl = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=600&q=80";
    }
    if (!backdropUrl) {
      backdropUrl = posterUrl;
    }

    // Save Movie to Database
    try {
      const res = await fetch("/api/movies", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          title: title,
          release_year: year,
          genre: genre,
          rating: rating,
          description: desc,
          poster_url: posterUrl,
          backdrop_url: backdropUrl,
          video_path: videoPath,
          resolution: resolution,
          duration: duration,
          file_size: fileSize,
          is_featured: isFeatured
        })
      });

      const data = await res.json();
      if (data.success) {
        window.cineApp.showToast(`Movie "${title}" successfully published!`);
        this.uploadForm.reset();
        this.selectedFileInfo.style.display = "none";
        this.uploadProgressWrap.style.display = "none";
        this.currentFile = null;
        this.loadAdminMovies();
        window.cineApp.loadCategories();
      } else {
        alert("Error saving movie: " + data.message);
      }
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>Upload & Save Movie</span>`;
    }
  }

  async loadAdminMovies() {
    try {
      const res = await fetch("/api/movies?limit=100");
      const data = await res.json();
      this.renderAdminMovies(data.movies || []);
    } catch (e) {
      console.error(e);
    }
  }

  renderAdminMovies(movies) {
    this.adminMovieList.innerHTML = "";
    if (movies.length === 0) {
      this.adminMovieList.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 2rem;">No movies uploaded yet.</div>`;
      return;
    }

    movies.forEach(movie => {
      const row = document.createElement("div");
      row.style.cssText = `
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        padding: 0.8rem 1.25rem;
        gap: 1rem;
      `;

      row.innerHTML = `
        <div style="display: flex; align-items: center; gap: 1rem;">
          <img src="${movie.poster_url || '/assets/default-poster.jpg'}" style="width: 45px; height: 60px; object-fit: cover; border-radius: 4px;" alt="">
          <div>
            <div style="font-weight: 700; color: #fff;">${movie.title} (${movie.release_year})</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${movie.genre} • ${movie.resolution} • Rating: ${movie.rating}</div>
          </div>
        </div>
        <div style="display: flex; gap: 0.75rem;">
          <button class="btn btn-secondary" onclick="window.cineApp.openMovieModal(${movie.id})" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;">Preview</button>
          <button class="btn btn-secondary" onclick="window.cineAdmin.deleteMovie(${movie.id})" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; color: #ef4444; border-color: rgba(239, 68, 68, 0.3);">Delete</button>
        </div>
      `;

      this.adminMovieList.appendChild(row);
    });
  }

  async deleteMovie(movieId) {
    if (!confirm("Are you sure you want to delete this movie from CineCloud?")) return;
    const token = localStorage.getItem("cinecloud_token");
    try {
      const res = await fetch(`/api/movies/${movieId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        window.cineApp.showToast("Movie deleted successfully");
        this.loadAdminMovies();
        window.cineApp.loadCategories();
      }
    } catch (e) {
      alert("Delete failed: " + e.message);
    }
  }
}

window.cineAdmin = new CineAdmin();
