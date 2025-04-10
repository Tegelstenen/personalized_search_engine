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
        this.volumeSlider = document.querySelector('.volume-slider');
        this.volumeProgress = document.querySelector('.volume-progress');
        this.volumeIcon = document.querySelector('.player-volume i');

        this.isDragging = false;
        this.previousVolume = 100;

        this.initializeEventListeners();
        this.startPeriodicUpdate();
    }

    initializeEventListeners() {
        // Play/Pause button
        document.getElementById('play-pause-button').addEventListener('click', () => this.togglePlayback());

        // Previous track button
        document.querySelector('.fa-backward').parentElement.addEventListener('click', () => this.previousTrack());

        // Next track button
        document.querySelector('.fa-forward').parentElement.addEventListener('click', () => this.nextTrack());

        // Volume control
        this.volumeSlider.addEventListener('mousedown', (e) => this.handleVolumeMouseDown(e));
        document.addEventListener('mousemove', (e) => this.handleVolumeMouseMove(e));
        document.addEventListener('mouseup', () => this.handleVolumeMouseUp());
        this.volumeIcon.addEventListener('click', () => this.toggleMute());
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

    async previousTrack() {
        try {
            const response = await fetch('/previous-track', { method: 'POST' });
            if (response.ok) {
                setTimeout(() => this.updateCurrentlyPlaying(), 300);
            } else {
                const data = await response.json();
                console.error('Error going to previous track:', data.error);
            }
        } catch (error) {
            console.error('Error going to previous track:', error);
        }
    }

    async nextTrack() {
        try {
            const response = await fetch('/next-track', { method: 'POST' });
            if (response.ok) {
                setTimeout(() => this.updateCurrentlyPlaying(), 300);
            } else {
                const data = await response.json();
                console.error('Error skipping to next track:', data.error);
            }
        } catch (error) {
            console.error('Error skipping to next track:', error);
        }
    }

    updateVolumeUI(volume) {
        this.volumeProgress.style.width = `${volume}%`;
        this.volumeIcon.className = 'fas ' + (
            volume === 0 ? 'fa-volume-mute' :
            volume < 30 ? 'fa-volume-off' :
            volume < 70 ? 'fa-volume-down' :
            'fa-volume-up'
        );
    }

    async setVolume(volume) {
        try {
            const response = await fetch('/set-volume', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ volume: Math.round(volume) })
            });
            if (!response.ok) {
                throw new Error('Failed to set volume');
            }
        } catch (error) {
            console.error('Error setting volume:', error);
        }
    }

    handleVolumeMouseDown(e) {
        this.isDragging = true;
        const rect = this.volumeSlider.getBoundingClientRect();
        const volume = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
        this.updateVolumeUI(volume);
        this.setVolume(volume);
    }

    handleVolumeMouseMove(e) {
        if (this.isDragging) {
            const rect = this.volumeSlider.getBoundingClientRect();
            const volume = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
            this.updateVolumeUI(volume);
            this.setVolume(volume);
        }
    }

    handleVolumeMouseUp() {
        this.isDragging = false;
    }

    toggleMute() {
        const currentWidth = parseFloat(this.volumeProgress.style.width) || 100;
        if (currentWidth > 0) {
            this.previousVolume = currentWidth;
            this.updateVolumeUI(0);
            this.setVolume(0);
        } else {
            this.updateVolumeUI(this.previousVolume);
            this.setVolume(this.previousVolume);
        }
    }
}

// Initialize player when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.spotifyPlayer = new SpotifyPlayer();
});
