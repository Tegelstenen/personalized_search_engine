// Top Items Display Handler
class TopItemsDisplay {
    constructor() {
        this.modal = document.getElementById('top-items-modal');
        this.showTopItemsBtn = document.getElementById('show-top-items');
        this.closeButton = document.querySelector('.close-modal');
        this.topTracksContainer = document.getElementById('top-tracks-container');
        this.topArtistsContainer = document.getElementById('top-artists-container');

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Show modal and fetch data when clicking the button
        this.showTopItemsBtn.addEventListener('click', () => {
            this.showModal();
            this.fetchTopItems();
        });

        // Close modal when clicking the close button
        this.closeButton.addEventListener('click', () => this.hideModal());

        // Close modal when clicking outside
        window.addEventListener('click', (event) => {
            if (event.target === this.modal) {
                this.hideModal();
            }
        });
    }

    showModal() {
        this.modal.style.display = 'block';
        // Small delay to trigger the transition
        setTimeout(() => {
            this.modal.classList.add('show');
        }, 10);
    }

    hideModal() {
        this.modal.classList.remove('show');
        // Wait for transition to complete before hiding
        setTimeout(() => {
            this.modal.style.display = 'none';
        }, 300);
    }

    fetchTopItems() {
        this.fetchTopTracks();
        this.fetchTopArtists();
    }

    async fetchTopTracks() {
        try {
            const response = await fetch('/top-tracks');
            const data = await response.json();

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            this.topTracksContainer.innerHTML = data.tracks.map(this.createTopTrackCard).join('');
        } catch (error) {
            console.error('Error fetching top tracks:', error);
            this.topTracksContainer.innerHTML = '<p class="error">Failed to load top tracks</p>';
        }
    }

    async fetchTopArtists() {
        try {
            const response = await fetch('/top-artists');
            const data = await response.json();

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            this.topArtistsContainer.innerHTML = data.artists.map(this.createTopArtistCard).join('');
        } catch (error) {
            console.error('Error fetching top artists:', error);
            this.topArtistsContainer.innerHTML = '<p class="error">Failed to load top artists</p>';
        }
    }

    createTopTrackCard(track) {
        return `
            <div class="top-item-card">
                <img src="${track.image || '/static/default-album.png'}" alt="${track.title}" class="top-item-image">
                <div class="top-item-content">
                    <h3>${track.title}</h3>
                    <p>${track.artist}</p>
                </div>
            </div>
        `;
    }

    createTopArtistCard(artist) {
        return `
            <div class="top-item-card">
                <img src="${artist.image || '/static/default-artist.png'}" alt="${artist.name}" class="top-item-image">
                <div class="top-item-content">
                    <h3>${artist.name}</h3>
                    <p>${artist.genres[0] || ''}</p>
                </div>
            </div>
        `;
    }
}

// Initialize top items handler when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.topItemsDisplay = new TopItemsDisplay();
});
