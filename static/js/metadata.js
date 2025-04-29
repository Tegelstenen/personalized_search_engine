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

    async displayArtistMetadata(result) {
        const artistData = result.source.member || result.source;
        const artistUrl = this.getArtistUrl(artistData);
        const instruments = this.formatInstruments(artistData.instruments);
        const artistImage = result.image || '/static/default-artist.png';

        const content = `
            <div class="metadata-header">
                <img src="${artistImage}" alt="${result.title}" class="metadata-image artist-image">
                <div class="metadata-title">
                    <h3>${result.source.member ? 'Artist Information' : 'Band Information'}</h3>
                    <h2>${result.title}</h2>
                </div>
            </div>
            <div class="metadata-details">
                ${artistData.realName && artistData.realName !== artistData.name ?
                    `<p><strong>Real Name:</strong> ${artistData.realName}</p>` : ''}
                ${this.getBiography(artistData)}
                ${artistUrl ? `<p><strong>More Info:</strong> <a href="${artistUrl}" target="_blank">${artistUrl}</a></p>` : ''}
                ${instruments ? `<p><strong>Instruments:</strong> ${instruments}</p>` : ''}
                ${artistData.birthDate ? `<p><strong>Birth Date:</strong> ${artistData.birthDate}</p>` : ''}
                ${artistData.subject ? `<p><strong>Categories:</strong> ${artistData.subject.join(', ')}</p>` : ''}
                ${this.getNameVariations(artistData)}
            </div>
            <div id="spotify-artist" class="spotify-match">
                <h4>On Spotify</h4>
                <div class="match-content">Loading...</div>
            </div>
            <div id="artist-songs" class="artist-songs">
                <h4>Songs found on Spotify</h4>
                <div class="songs-list">Loading...</div>
            </div>`;

        this.contentDiv.innerHTML = content;
        this.showModal();

        // Create a descriptive text for tracking
        const artistDescription = `${result.title}` +
                                 `${artistData.realName && artistData.realName !== artistData.name ? ` (${artistData.realName})` : ''}` +
                                 `${instruments ? `, ${instruments}` : ''}` +
                                 `${artistData.subject ? `, ${artistData.subject.join(', ')}` : ''}`;
        await window.TrackingManager.trackClick(artistDescription, "artist");

        // Fetch additional data
        await Promise.all([
            this.fetchSpotifyArtist(result.title),
            this.fetchArtistSongs(result.title)
        ]);
    }

    async displayAlbumMetadata(result) {
        const albumImage = result.image || '/static/default-album.png';

        const content = `
            <div class="metadata-header">
                <img src="${albumImage}" alt="${result.title}" class="metadata-image album-image">
                <div class="metadata-title">
                    <h3>Album Information</h3>
                    <h2>${result.title}</h2>
                    <p class="metadata-subtitle">by ${result.source.artist_name || result.source.name || "Unknown Artist"}</p>
                </div>
            </div>
            <div class="metadata-details">
                ${result.source.genre ? `<p><strong>Genre:</strong> ${result.source.genre}</p>` : ''}
                ${result.source.dateRelease ? `<p><strong>Release Date:</strong> ${result.source.dateRelease}</p>` : ''}
                ${result.source.country ? `<p><strong>Country:</strong> ${result.source.country}</p>` : ''}
            </div>
            <div id="spotify-album" class="spotify-match">
                <h4>On Spotify</h4>
                <div class="match-content">Loading...</div>
            </div>
        `;

        this.contentDiv.innerHTML = content;
        this.showModal();

        // Create a descriptive text for tracking
        const albumDescription = `${result.title} by ${result.source.artist_name || result.source.name || "Unknown Artist"}` +
                                `${result.source.genre ? `, ${result.source.genre}` : ''}` +
                                `${result.source.dateRelease ? `, ${result.source.dateRelease}` : ''}` +
                                `${result.source.country ? `, ${result.source.country}` : ''}`;
        await window.TrackingManager.trackClick(albumDescription, "album");

        // Fetch Spotify album data
        const searchQuery = `${result.title} ${result.source.artist_name || result.source.name || ''}`.trim();
        await this.fetchSpotifyAlbum(searchQuery);
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

    // Helper methods for formatting data
    getArtistUrl(artistData) {
        if (artistData.urlWikipedia) return artistData.urlWikipedia;
        if (artistData.urlWikidata) return artistData.urlWikidata;
        if (artistData.urls && artistData.urls.length > 0) return artistData.urls[0];
        return '';
    }

    formatInstruments(instruments) {
        return instruments ? instruments.map(instrument =>
            instrument.charAt(0).toUpperCase() + instrument.slice(1)).join(', ') : '';
    }

    getBiography(artistData) {
        if (artistData.dbp_abstract) return `<p><strong>Biography:</strong> ${artistData.dbp_abstract}</p>`;
        if (artistData.abstract) return `<p><strong>Biography:</strong> ${artistData.abstract}</p>`;
        return '';
    }

    getNameVariations(artistData) {
        return artistData.nameVariations && artistData.nameVariations.length > 0 ?
            `<p><strong>Also Known As:</strong> ${artistData.nameVariations.join(', ')}</p>` : '';
    }

    // API calls to fetch additional data
    async fetchSpotifyArtist(artistName) {
        try {
            const response = await fetch(`/search-spotify-artist/${encodeURIComponent(artistName)}`);
            const data = await response.json();
            const container = document.querySelector('.match-content');

            if (!container) return; // Modal might be closed

            if (data.error) {
                container.innerHTML = `<p class="error">${data.error}</p>`;
                return;
            }

            const artist = data.artist;
            container.innerHTML = this.createSpotifyArtistCard(artist);
        } catch (error) {
            console.error('Error fetching Spotify artist:', error);
            const container = document.querySelector('.match-content');
            if (container) {
                container.innerHTML = '<p class="error">Failed to load Spotify artist</p>';
            }
        }
    }

    async fetchArtistSongs(artistName) {
        try {
            const response = await fetch(`/artist-songs/${encodeURIComponent(artistName)}`);
            const data = await response.json();

            if (!document.getElementById('artist-songs')) return; // Modal might be closed

            const songsList = document.querySelector('.songs-list');
            if (data.error) {
                songsList.innerHTML = `<p class="error">${data.error}</p>`;
                return;
            }
            if (!data.tracks || data.tracks.length === 0) {
                songsList.innerHTML = '<p>No songs found</p>';
                return;
            }

            this.displaySpotifyMatches(data.tracks, songsList);
        } catch (error) {
            console.error('Error fetching songs:', error);
            const songsList = document.querySelector('.songs-list');
            if (songsList) {
                songsList.innerHTML = '<p class="error">Failed to load songs</p>';
            }
        }
    }

    async fetchSpotifyAlbum(searchQuery) {
        try {
            const response = await fetch(`/search-spotify-album/${encodeURIComponent(searchQuery)}`);
            const data = await response.json();
            const container = document.querySelector('.match-content');

            if (!container) return; // Modal might be closed

            if (data.error) {
                container.innerHTML = `<p class="error">${data.error}</p>`;
                return;
            }

            const album = data.album;
            container.innerHTML = this.createSpotifyAlbumCard(album);
        } catch (error) {
            console.error('Error fetching Spotify album:', error);
            const container = document.querySelector('.match-content');
            if (container) {
                container.innerHTML = '<p class="error">Failed to load Spotify album</p>';
            }
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

    // UI Components
    createSpotifyArtistCard(artist) {
        return `
            <div class="songs-grid">
                <div class="song-item">
                    <img src="${artist.image || '/static/default-artist.png'}" alt="${artist.name}" class="song-image">
                    <div class="song-info">
                        <h5>${artist.name}</h5>
                        <p>${artist.genres.slice(0, 3).join(', ')}</p>
                        <p>${artist.followers.toLocaleString()} followers • ${artist.popularity}% popularity</p>
                        <button class="play-song-btn" onclick="window.open('${artist.external_url}', '_blank')">
                            <i class="fab fa-spotify"></i> Open in Spotify
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    createSpotifyAlbumCard(album) {
        return `
            <div class="songs-grid">
                <div class="song-item">
                    <img src="${album.image || '/static/default-album.png'}" alt="${album.name}" class="song-image">
                    <div class="song-info">
                        <h5>${album.name}</h5>
                        <p>By ${album.artist}</p>
                        <p>${album.total_tracks} tracks • Released: ${album.release_date}</p>
                        <button class="play-song-btn" onclick="window.open('${album.external_url}', '_blank')">
                            <i class="fab fa-spotify"></i> Open in Spotify
                        </button>
                    </div>
                </div>
            </div>
        `;
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
});
