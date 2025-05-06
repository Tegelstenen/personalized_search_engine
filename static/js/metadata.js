// Metadata Display Handler
class MetadataDisplay {
    constructor() {
        this.modal = document.getElementById('metadata-modal');
        this.closeButton = document.querySelector('.close-metadata-modal');
        this.contentDiv = document.getElementById('metadata-content');

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Close metadata modal when clicking the close button
        this.closeButton.addEventListener('click', () => this.hideModal());

        // Close metadata modal when clicking outside
        window.addEventListener('click', (event) => {
            if (event.target === this.modal) {
                this.hideModal();
            }
        });
    }

    showModal() {
        this.modal.style.display = 'block';
        setTimeout(() => {
            this.modal.classList.add('show');
        }, 10);
    }

    hideModal() {
        this.modal.classList.remove('show');
        setTimeout(() => {
            this.modal.style.display = 'none';
        }, 300);
    }

    async displaySongMetadata(result) {
        const content = `
            <div class="metadata-header song-metadata-header">
                <div class="song-icon">
                    <i class="fas fa-music"></i>
                </div>
                <div class="metadata-title">
                    <h3>Song Information</h3>
                    <h2>${result.title}</h2>
                    <p class="metadata-subtitle">by ${result.source.artist || result.source.name || "Unknown Artist"}</p>
                </div>
            </div>
            <div class="metadata-details">
                ${result.source.albumTitle ? `<p><strong>Album:</strong> ${result.source.albumTitle}</p>` : ''}
                ${result.source.album_genre ? `<p><strong>Genre:</strong> ${result.source.album_genre}</p>` : ''}
                ${result.source.bpm ? `<p><strong>BPM:</strong> ${result.source.bpm}</p>` : ''}
                ${result.source.language ? `<p><strong>Language:</strong> ${result.source.language}</p>` : ''}
                ${result.preview ? `
                    <div class="preview-player">
                        <strong>Preview:</strong>
                        <audio controls src="${result.preview}"></audio>
                    </div>
                ` : ''}
                ${result.source.lyrics ? `<div class="lyrics-section"><strong>Lyrics:</strong><div class="lyrics">${result.source.lyrics}</div></div>` : ''}
            </div>
            <div id="spotify-matches" class="artist-songs">Loading Spotify matches...</div>
        `;

        this.contentDiv.innerHTML = content;
        this.showModal();

        // Create descriptive text for tracking
        const trackText = `${result.title} by ${result.source.artist || result.source.name || "Unknown Artist"}` +
                         `${result.source.albumTitle ? ` from ${result.source.albumTitle}` : ''}` +
                         `${result.source.album_genre ? ` (${result.source.album_genre})` : ''}` +
                         `${result.source.lyrics ? ` ${result.source.lyrics}` : ''}`;

        await window.TrackingManager.trackClick(trackText, "song");

        // Fetch Spotify track data
        const spotifyUrl = result.source.urlSpotify;
        if (spotifyUrl) {
            const trackId = spotifyUrl.split('track/')[1];
            if (trackId) {
                await this.fetchSpotifyTrack(trackId);
            }
        } else {
            await this.searchSpotifyTracks(result.title + ' ' + (result.source.artist || result.source.name || ''));
        }
    }

    async fetchSpotifyTrack(trackId) {
        try {
            const response = await fetch(`/get-spotify-track/${trackId}`);
            const data = await response.json();

            if (data.error) {
                document.getElementById('spotify-matches').innerHTML = `<p class="error">${data.error}</p>`;
                return;
            }

            this.displaySpotifyMatches([data.track]);
        } catch (error) {
            console.error('Error fetching Spotify track:', error);
            document.getElementById('spotify-matches').innerHTML = '<p class="error">Failed to load Spotify track</p>';
        }
    }

    async searchSpotifyTracks(searchQuery) {
        try {
            const response = await fetch(`/search-spotify-tracks/${encodeURIComponent(searchQuery)}`);
            const data = await response.json();

            if (data.error) {
                document.getElementById('spotify-matches').innerHTML = `<p class="error">${data.error}</p>`;
                return;
            }

            this.displaySpotifyMatches(data.tracks);
        } catch (error) {
            console.error('Error searching Spotify tracks:', error);
            document.getElementById('spotify-matches').innerHTML = '<p class="error">Failed to search Spotify tracks</p>';
        }
    }

    displaySpotifyMatches(tracks, targetContainer = null) {
        const container = targetContainer || document.getElementById('spotify-matches');
        if (!tracks || tracks.length === 0) {
            container.innerHTML = '<p>No matches found</p>';
            return;
        }

        container.innerHTML = `
            <div class="songs-grid">
                ${tracks.map(track => `
                    <div class="song-item">
                        <img src="${track.image || '/static/default-album.png'}" alt="${track.title}" class="song-image">
                        <div class="song-info">
                            <h5>${track.title}</h5>
                            <p>${track.artist} • ${track.album}</p>
                            <button class="play-song-btn" data-uri="${track.id}">
                                <i class="fas fa-play"></i> Play
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        // Add event listeners for play buttons
        const playButtons = container.querySelectorAll('.play-song-btn');
        playButtons.forEach(button => {
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                const trackId = button.dataset.uri;
                try {
                    const response = await fetch('/play-track', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ track_id: trackId })
                    });
                    if (!response.ok) {
                        throw new Error('Failed to play track');
                    }
                    // Update the currently playing display
                    setTimeout(() => window.spotifyPlayer.updateCurrentlyPlaying(), 500);
                } catch (error) {
                    console.error('Error playing track:', error);
                }
            });
        });
    }
}

// Initialize metadata handler when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.metadataDisplay = new MetadataDisplay();

    // Add event listeners for like buttons
    document.addEventListener('click', async (event) => {
        if (event.target.closest('.like-button')) {
            const button = event.target.closest('.like-button');
            const itemText = button.dataset.itemText;

            await window.TrackingManager.trackLike(itemText);
            button.innerHTML = '<i class="fas fa-heart"></i>';
            button.classList.add('liked');
        }
    });
});
