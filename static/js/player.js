// Spotify Player Controls
class SpotifyPlayer {
    constructor() {
        this.playerBar = document.getElementById('player-bar');
        this.playPauseIcon = document.getElementById('play-pause-icon');
        this.playerSongName = document.getElementById('player-song-name');
        this.playerArtistName = document.getElementById('player-artist-name');
        this.playerAlbumArt = document.getElementById('player-album-art');
        this.progressBar = document.getElementById('song-progress');
        this.currentTimeSpan = document.getElementById('current-time');
        this.totalTimeSpan = document.getElementById('total-time');

        this.currentTrackId = null;
        this.playStartTime = null;
        this.trackPlayInterval = null;

        this.initializeEventListeners();
        this.startPeriodicUpdate();
    }

    initializeEventListeners() {
        // Play/Pause button
        document.getElementById('play-pause-button').addEventListener('click', () => this.togglePlayback());
    }

    formatTime(ms) {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    async updateCurrentlyPlaying() {
        try {
            const response = await fetch('/currently-playing');
            const data = await response.json();

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            const trackName = data.track_name;
            const artistName = data.artist_name;
            const image = data.image;
            const isPlaying = data.is_playing;
            const progress = data.progress;
            const duration = data.duration;

            // Update interaction for the previous track when track changes
            if (data.track_id && data.track_id !== this.currentTrackId) {
                if (this.currentTrackId && this.playStartTime) {
                    const oldTrackDuration = (Date.now() - this.playStartTime) / 1000;
                    console.log(`Track changed! Logging play duration for previous track: ${oldTrackDuration} seconds`);
                    window.TrackingManager.trackPlay(this.currentTrackId, oldTrackDuration);
                }
                this.currentTrackId = data.track_id;
                this.playStartTime = isPlaying ? Date.now() : null;
                console.log(`New track detected: ${trackName}. Play state: ${isPlaying ? 'playing' : 'paused'}`);
            } else if (data.track_id && this.currentTrackId === data.track_id) {
                // Update start time when play state changes
                if (isPlaying && !this.playStartTime) {
                    this.playStartTime = Date.now();
                    console.log(`Track resumed: ${trackName}, starting timer`);
                } else if (!isPlaying && this.playStartTime) {
                    // Track paused, log the duration so far
                    const pausedDuration = (Date.now() - this.playStartTime) / 1000;
                    console.log(`Track paused: ${trackName}, logging duration: ${pausedDuration} seconds`);
                    window.TrackingManager.trackPlay(this.currentTrackId, pausedDuration);
                    this.playStartTime = null;
                }
            }

            if (trackName && artistName) {
                this.playerBar.classList.remove('hidden');
                this.playerBar.classList.add('visible');
                this.playerSongName.textContent = trackName;
                this.playerArtistName.textContent = artistName;
            } else {
                this.playerBar.classList.add('hidden');
                this.playerBar.classList.remove('visible');
            }

            if (image) {
                this.playerAlbumArt.src = image;
            }

            // Update play/pause button
            if (isPlaying) {
                this.playPauseIcon.classList.remove('fa-play');
                this.playPauseIcon.classList.add('fa-pause');
            } else {
                this.playPauseIcon.classList.remove('fa-pause');
                this.playPauseIcon.classList.add('fa-play');
            }

            // Update progress bar
            if (duration > 0) {
                const progressPercent = (progress / duration) * 100;
                this.progressBar.style.width = `${progressPercent}%`;
            } else {
                this.progressBar.style.width = '0%';
            }

            // Update time displays
            this.currentTimeSpan.textContent = this.formatTime(progress);
            this.totalTimeSpan.textContent = this.formatTime(duration);

        } catch (error) {
            console.error('Error updating player:', error);
        }
    }

    startPeriodicUpdate() {
        this.updateCurrentlyPlaying();
        setInterval(() => this.updateCurrentlyPlaying(), 3000);
    }

    async togglePlayback() {
        try {
            const response = await fetch('/toggle-playback', { method: 'POST' });
            if (response.ok) {
                this.updateCurrentlyPlaying();
            }
        } catch (error) {
            console.error('Error toggling playback:', error);
        }
    }
}

// Initialize player when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.spotifyPlayer = new SpotifyPlayer();

    // Track when user leaves the page to log final play duration
    window.addEventListener('beforeunload', () => {
        if (window.spotifyPlayer.currentTrackId && window.spotifyPlayer.playStartTime) {
            const finalDuration = (Date.now() - window.spotifyPlayer.playStartTime) / 1000;
            console.log(`Page unloading, logging final play duration: ${finalDuration} seconds`);
            // Use sendBeacon to make sure the request goes through even as page unloads
            navigator.sendBeacon(
                `/track-play/${window.spotifyPlayer.currentTrackId}`,
                JSON.stringify({ duration: finalDuration })
            );
        }
    });
});
