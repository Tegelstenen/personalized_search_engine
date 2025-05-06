document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const resultsDiv = document.getElementById('results');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error-message');
    const rankedResultsDiv = document.getElementById('ranked-results');

    let currentSessionId = null;


    restoreSearchState();

    function calculatePrecision(hits, k) {
        const likedItems = JSON.parse(sessionStorage.getItem('likedItems') || '[]');
        let relevantItems = 0;

        for (let i = 0; i < Math.min(k, hits.length); i++) {
            const hit = hits[i];
            const songArtist = hit.source.artist || hit.source.artistName || hit.source.name || 'Unknown artist';
            const itemText = `${hit.title} by ${songArtist}`;

            if (likedItems.includes(itemText)) {
                relevantItems++;
            }
        }

        return relevantItems / k;
    }

    function updatePrecisionMetrics(hits) {
        if (!currentSessionId) {
            console.error('No session ID available for precision update');
            return;
        }

        const precision5 = calculatePrecision(hits, 5);
        const precision10 = calculatePrecision(hits, 10);

        // Send updated metrics to server
        fetch('/update-precision', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                precision5: precision5,
                precision10: precision10,
                session_id: currentSessionId
            })
        }).catch(error => {
            console.error('Error updating precision metrics:', error);
        });
    }

    function displayRankedResults(hits, sessionId) {
        currentSessionId = sessionId;

        rankedResultsDiv.innerHTML = '';

        const resultsList = document.createElement('div');
        resultsList.className = 'results-grid';

        if (hits.length === 0) {
            const noResults = document.createElement('div');
            noResults.className = 'no-results';
            noResults.textContent = 'No songs found.';
            rankedResultsDiv.appendChild(noResults);
            return;
        }

        hits.forEach((hit) => {
            const resultItem = createResultCard(hit);
            resultsList.appendChild(resultItem);
        });

        rankedResultsDiv.appendChild(resultsList);

        // Add event listeners to all like buttons
        document.querySelectorAll('.like-button').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                const itemText = this.getAttribute('data-item-text');

                if (this.classList.contains('liked')) {
                    // Unlike: Remove liked class
                    this.classList.remove('liked');
                    this.innerHTML = '<i class="fas fa-thumbs-up"></i>';
                    window.TrackingManager.trackClick(itemText, "unlike");
                    removeLikedItem(itemText);
                } else {
                    // Like: Add liked class
                    this.classList.add('liked');
                    this.innerHTML = '<i class="fas fa-thumbs-up"></i>';
                    window.TrackingManager.trackClick(itemText, "like");
                    saveLikedItem(itemText);
                }

                updatePrecisionMetrics(hits);
            });

            // Restore liked state if it was previously liked
            const itemText = button.getAttribute('data-item-text');
            if (isLiked(itemText)) {
                button.classList.add('liked');
                button.innerHTML = '<i class="fas fa-thumbs-up"></i>';
            }
        });

        // Click tracking for all result cards
        document.querySelectorAll('.result-card').forEach(card => {
            const originalClickHandler = card.onclick;

            card.onclick = function(e) {
                const title = this.querySelector('.title').textContent;
                const subtitle = this.querySelector('.subtitle').textContent;
                const itemText = `${title} by ${subtitle}`;

                window.TrackingManager.trackClick(itemText, "click");

                if (originalClickHandler) {
                    originalClickHandler.call(this, e);
                }
            };
        });

        saveSearchResults(hits, sessionId);
        updatePrecisionMetrics(hits);
    }

    function createResultCard(result) {
        const card = document.createElement('div');
        card.className = 'result-card songs';

        const songArtist = result.source.artist || result.source.artistName || result.source.name || 'Unknown artist';
        const itemText = `${result.title} by ${songArtist}`;

        card.innerHTML = `
            <div class="result-content">
                <div class="title">${result.title}</div>
                <div class="subtitle">${songArtist}</div>
                <button class="like-button" data-item-text="${itemText}">
                    <i class="fas fa-thumbs-up"></i>
                </button>
            </div>
        `;

        card.addEventListener('click', () => {
            window.metadataDisplay.displaySongMetadata(result);
        });

        return card;
    }

    function saveSearchResults(hits, sessionId) {
        try {
            sessionStorage.setItem('lastSearchResults', JSON.stringify(hits));
            sessionStorage.setItem('lastSearchQuery', searchInput.value);
            sessionStorage.setItem('lastSessionId', sessionId);
            console.log('Search results saved for in-app navigation');
        } catch (e) {
            console.error('Error saving search results:', e);
        }
    }

    function restoreSearchState() {
        try {
            const lastResults = sessionStorage.getItem('lastSearchResults');
            const lastQuery = sessionStorage.getItem('lastSearchQuery');
            const lastSessionId = sessionStorage.getItem('lastSessionId');

            if (lastResults && lastQuery && lastSessionId) {
                console.log('Restoring search state for in-app navigation');
                searchInput.value = lastQuery;
                const hits = JSON.parse(lastResults);
                displayRankedResults(hits, lastSessionId);
                resultsDiv.style.display = 'block';
            }
        } catch (e) {
            console.error('Error restoring search state:', e);
        }
    }

    function saveLikedItem(itemText) {
        try {
            const likedItems = JSON.parse(sessionStorage.getItem('likedItems') || '[]');
            if (!likedItems.includes(itemText)) {
                likedItems.push(itemText);
                sessionStorage.setItem('likedItems', JSON.stringify(likedItems));
            }
        } catch (e) {
            console.error('Error saving liked item:', e);
        }
    }

    function removeLikedItem(itemText) {
        try {
            const likedItems = JSON.parse(sessionStorage.getItem('likedItems') || '[]');
            const index = likedItems.indexOf(itemText);
            if (index !== -1) {
                likedItems.splice(index, 1);
                sessionStorage.setItem('likedItems', JSON.stringify(likedItems));
            }
        } catch (e) {
            console.error('Error removing liked item:', e);
        }
    }

    function isLiked(itemText) {
        try {
            const likedItems = JSON.parse(sessionStorage.getItem('likedItems') || '[]');
            return likedItems.includes(itemText);
        } catch (e) {
            console.error('Error checking liked state:', e);
            return false;
        }
    }

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
            const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            if (data.error) {
                errorDiv.textContent = data.error;
                return;
            }

            if (data.session_id) {
                window.TrackingManager.setCurrentSession(data.session_id);
            }

            displayRankedResults(data.hits, data.session_id);
            resultsDiv.style.display = 'block';
        } catch (error) {
            errorDiv.textContent = 'An error occurred while searching. Please try again.';
        } finally {
            loadingDiv.style.display = 'none';
        }
    }
});
