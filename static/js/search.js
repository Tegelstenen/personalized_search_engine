document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const resultsDiv = document.getElementById('results');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error-message');
    const rankedResultsDiv = document.getElementById('ranked-results');
    const filterButtons = document.querySelectorAll('.filter-btn');

    // Current active filter
    let activeFilter = 'all';

    // Set up filter buttons
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons
            filterButtons.forEach(btn => btn.classList.remove('active'));

            // Add active class to clicked button
            button.classList.add('active');

            // Set active filter
            activeFilter = button.getAttribute('data-filter');

            // If there are already results, refilter them
            if (resultsDiv.style.display === 'block') {
                performSearch();
            }
        });
    });

    function displayRankedResults(hits) {
        rankedResultsDiv.innerHTML = '';

        const resultsList = document.createElement('div');
        resultsList.className = 'results-grid';

        // Filter hits based on activeFilter
        const filteredHits = activeFilter === 'all'
            ? hits
            : hits.filter(hit => hit.type === activeFilter);

        if (filteredHits.length === 0) {
            const noResults = document.createElement('div');
            noResults.className = 'no-results';
            noResults.textContent = `No ${activeFilter === 'all' ? '' : activeFilter} results found.`;
            rankedResultsDiv.appendChild(noResults);
            return;
        }

        filteredHits.forEach((hit, index) => {
            const resultItem = document.createElement('div');
            resultItem.className = `result-card ${hit.type}`;

            let resultContent = '';
            switch(hit.type) {
                case 'artists':
                    resultContent = `
                        <img src="${hit.image || '/static/default-artist.png'}" alt="${hit.title}" class="result-image">
                        <div class="result-content">
                            <div class="title">${hit.title}</div>
                            <div class="subtitle">Artist</div>
                        </div>
                    `;
                    break;
                case 'albums':
                    // Get artist name from source if available
                    const albumArtist = hit.source.artist_name || hit.source.name || 'Unknown artist';
                    resultContent = `
                        <img src="${hit.image || '/static/default-album.png'}" alt="${hit.title}" class="result-image">
                        <div class="result-content">
                            <div class="title">${hit.title}</div>
                            <div class="subtitle">Album • ${albumArtist}</div>
                        </div>
                    `;
                    break;
                case 'songs':
                    // Get artist name from source if available
                    const songArtist = hit.source.artist || hit.source.artistName || hit.source.name || 'Unknown artist';
                    resultContent = `
                        <div class="result-content song-content">
                            <div class="title">${hit.title}</div>
                            <div class="subtitle">${songArtist}</div>
                        </div>
                    `;
                    resultItem.classList.add('song-result-card');
                    break;
            }

            resultItem.innerHTML = resultContent;

            // Add click event to show metadata
            resultItem.addEventListener('click', async () => {
                switch(hit.type) {
                    case 'artists':
                        window.metadataDisplay.displayArtistMetadata(hit);
                        break;
                    case 'albums':
                        window.metadataDisplay.displayAlbumMetadata(hit);
                        break;
                    case 'songs':
                        window.metadataDisplay.displaySongMetadata(hit);
                        break;
                }
            });

            resultsList.appendChild(resultItem);
        });

        rankedResultsDiv.appendChild(resultsList);
    }

    // Event listeners and updates
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    async function performSearch() {
        const query = searchInput.value.trim();

        if (!query) {
            resultsDiv.style.display = 'none';
            return;
        }

        loadingDiv.style.display = 'block';
        resultsDiv.style.display = 'none';
        errorDiv.textContent = '';

        try {
            const response = await fetch(`/search?q=${encodeURIComponent(query)}&filter=${activeFilter}`);
            const data = await response.json();

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            if (data.error) {
                errorDiv.textContent = data.error;
                return;
            }

            displayRankedResults(data.hits);
            resultsDiv.style.display = 'block';
        } catch (error) {
            errorDiv.textContent = 'An error occurred while searching. Please try again.';
        } finally {
            loadingDiv.style.display = 'none';
        }
    }
}); 