/**
 * CineCloud Android TV 10-Foot Remote Control & Spatial Navigation Engine
 * Provides remote-friendly D-pad navigation (Up, Down, Left, Right, OK, Back)
 * for Android TV boxes, Fire TV sticks, TV browsers, and Leanback WebView.
 */

class TVNavEngine {
  constructor() {
    this.isTvMode = false;
    this.currentFocusedElement = null;
    this.audioCtx = null;
    this.init();
  }

  init() {
    // Detect TV user agent or hash parameter
    const isTvUserAgent = /Android TV|SmartTV|AppleTV|BRAVIA|HbbTV|NetCast|Tizen|POV_TV|CrKey|Roku/i.test(navigator.userAgent);
    const hasTvHash = window.location.hash.includes("tv");
    
    if (isTvUserAgent || hasTvHash) {
      this.enableTvMode();
    }

    // Bind Remote & Keyboard events
    window.addEventListener("keydown", (e) => this.handleKeyDown(e));

    // Watch for click outside / mouse movement to gracefully toggle focus modes
    window.addEventListener("mousemove", () => {
      // If mouse is moved on laptop, keep TV mode active if explicit, but don't force focus lock
    });
  }

  enableTvMode() {
    this.isTvMode = true;
    document.body.classList.add("tv-mode-active");
    const tvBtn = document.getElementById("tvModeBtn");
    if (tvBtn) {
      tvBtn.classList.add("active");
      tvBtn.querySelector("span").textContent = "TV Mode: ON";
    }

    // Auto-focus first navigable item
    setTimeout(() => {
      const firstNav = document.querySelector(".tv-nav-item, .movie-card");
      if (firstNav) {
        this.setFocus(firstNav);
      }
    }, 400);

    console.log("📺 CineCloud Android TV Remote Navigation Activated");
  }

  disableTvMode() {
    this.isTvMode = false;
    document.body.classList.remove("tv-mode-active");
    if (this.currentFocusedElement) {
      this.currentFocusedElement.classList.remove("tv-focused");
    }
    const tvBtn = document.getElementById("tvModeBtn");
    if (tvBtn) {
      tvBtn.classList.remove("active");
      tvBtn.querySelector("span").textContent = "TV Mode";
    }
  }

  toggleTvMode() {
    if (this.isTvMode) {
      this.disableTvMode();
    } else {
      this.enableTvMode();
    }
  }

  playNavFeedback() {
    try {
      if (!this.audioCtx) {
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(440, this.audioCtx.currentTime);
      gain.gain.setValueAtTime(0.04, this.audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.05);
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
      osc.start();
      osc.stop(this.audioCtx.currentTime + 0.05);
    } catch (e) {
      // Audio feedback optional
    }
  }

  setFocus(el) {
    if (!el) return;
    if (this.currentFocusedElement) {
      this.currentFocusedElement.classList.remove("tv-focused");
    }
    this.currentFocusedElement = el;
    el.classList.add("tv-focused");
    el.focus({ preventScroll: true });

    // Smooth scroll into view
    el.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "center"
    });

    this.playNavFeedback();
  }

  getNavigableElements() {
    // Only query visible elements
    const candidates = Array.from(document.querySelectorAll(
      ".tv-nav-item, .movie-card, .btn, input, select, textarea, .ctrl-btn"
    )).filter(el => {
      // Must not be hidden or in a hidden container
      const style = window.getComputedStyle(el);
      return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetParent !== null;
    });

    // If modal is open, confine navigation inside modal
    const openModal = document.querySelector(".modal-backdrop.open");
    if (openModal) {
      return candidates.filter(el => openModal.contains(el));
    }

    // If video player is open, confine to video player controls
    const playerContainer = document.getElementById("playerContainer");
    if (playerContainer && playerContainer.style.display !== "none") {
      return candidates.filter(el => playerContainer.contains(el));
    }

    return candidates;
  }

  handleKeyDown(e) {
    const key = e.key;
    const keyCode = e.keyCode;

    // Standard TV Remote Key Codes
    const DPAD_UP = 19;
    const DPAD_DOWN = 20;
    const DPAD_LEFT = 21;
    const DPAD_RIGHT = 22;
    const DPAD_CENTER = 23;
    const ANDROID_BACK = 4;

    const isUp = key === "ArrowUp" || keyCode === DPAD_UP;
    const isDown = key === "ArrowDown" || keyCode === DPAD_DOWN;
    const isLeft = key === "ArrowLeft" || keyCode === DPAD_LEFT;
    const isRight = key === "ArrowRight" || keyCode === DPAD_RIGHT;
    const isEnter = key === "Enter" || keyCode === DPAD_CENTER || key === "Select";
    const isBack = key === "Escape" || key === "Backspace" || keyCode === ANDROID_BACK;

    // Handle back button
    if (isBack) {
      // Check if player is open
      const player = document.getElementById("playerContainer");
      if (player && player.style.display !== "none") {
        e.preventDefault();
        window.cinePlayer.close();
        return;
      }
      // Check if modal is open
      const openModal = document.querySelector(".modal-backdrop.open");
      if (openModal) {
        e.preventDefault();
        openModal.classList.remove("open");
        return;
      }
    }

    // Check if user is typing in an input
    if (document.activeElement && (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA")) {
      if (!isUp && !isDown) return; // Allow typing in search or forms
    }

    if (isEnter) {
      if (this.currentFocusedElement) {
        this.currentFocusedElement.click();
      }
      return;
    }

    if (!isUp && !isDown && !isLeft && !isRight) {
      return;
    }

    e.preventDefault();

    const elements = this.getNavigableElements();
    if (elements.length === 0) return;

    if (!this.currentFocusedElement || !elements.includes(this.currentFocusedElement)) {
      this.setFocus(elements[0]);
      return;
    }

    const currentRect = this.currentFocusedElement.getBoundingClientRect();
    let bestCandidate = null;
    let minDistance = Infinity;

    for (const el of elements) {
      if (el === this.currentFocusedElement) continue;
      const rect = el.getBoundingClientRect();

      let isEligible = false;
      let primaryDelta = 0;
      let secondaryDelta = 0;

      if (isRight) {
        isEligible = rect.left >= currentRect.left + 5;
        primaryDelta = rect.left - currentRect.left;
        secondaryDelta = Math.abs(rect.top - currentRect.top);
      } else if (isLeft) {
        isEligible = rect.right <= currentRect.right - 5;
        primaryDelta = currentRect.right - rect.right;
        secondaryDelta = Math.abs(rect.top - currentRect.top);
      } else if (isDown) {
        isEligible = rect.top >= currentRect.top + 5;
        primaryDelta = rect.top - currentRect.top;
        secondaryDelta = Math.abs(rect.left - currentRect.left);
      } else if (isUp) {
        isEligible = rect.bottom <= currentRect.bottom - 5;
        primaryDelta = currentRect.bottom - rect.bottom;
        secondaryDelta = Math.abs(rect.left - currentRect.left);
      }

      if (isEligible) {
        // Weighted Manhattan distance prioritizing the primary directional axis
        const dist = primaryDelta + (secondaryDelta * 2.2);
        if (dist < minDistance) {
          minDistance = dist;
          bestCandidate = el;
        }
      }
    }

    if (bestCandidate) {
      this.setFocus(bestCandidate);
    }
  }
}

window.tvNav = new TVNavEngine();
