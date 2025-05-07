document.addEventListener('DOMContentLoaded', function() {
    const lineChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Search Number'
                }
            },
            y: {
                beginAtZero: true,
                title: {
                    display: true,
                    text: 'Number of Likes'
                }
            }
        },
        plugins: {
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return context.dataset.label + ': ' + context.parsed.y;
                    }
                }
            },
            legend: {
                position: 'top'
            }
        }
    };

    let precisionChart;
    let genreChart;
    let artistChart;
    let metricsOverTime = window.initialMetricsOverTime || {};
    let searchNumbers = metricsOverTime['search_numbers'] || [];

    function createCharts() {
        if (document.getElementById('precisionLineChart')) {
            const precisionData = {
                labels: searchNumbers,
                datasets: [
                    {
                        label: 'Likes per Search',
                        data: metricsOverTime['likes_per_search'] || [],
                        type: 'bar',
                        backgroundColor: '#1db954',
                        borderColor: '#1db954',
                        borderWidth: 1
                    },
                    {
                        label: 'Cumulative Likes',
                        data: metricsOverTime['cumulative_likes'] || [],
                        type: 'line',
                        borderColor: '#b3b3b3',  // Spotify gray
                        backgroundColor: 'rgba(179, 179, 179, 0.1)',  // Semi-transparent gray
                        fill: false,
                        tension: 0.1
                    }
                ]
            };

            console.log('Creating precision chart with data:', precisionData);

            precisionChart = new Chart(document.getElementById('precisionLineChart'), {
                type: 'bar',
                data: precisionData,
                options: lineChartOptions
            });
        }

        // Initialize genre distribution chart with empty data
        if (document.getElementById('genreDistributionChart')) {
            const genreData = {
                labels: ['No data yet'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['#b3b3b3'],  // Spotify gray for empty state
                    borderWidth: 0
                }]
            };

            genreChart = new Chart(document.getElementById('genreDistributionChart'), {
                type: 'pie',
                data: genreData,
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'right',
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    if (context.label === 'No data yet') {
                                        return 'Start playing songs to see your genre distribution';
                                    }
                                    return context.label + ': ' + context.raw + ' plays';
                                }
                            }
                        }
                    }
                }
            });

            // Fetch initial genre data
            fetchGenreStats();
        }

        // Initialize artist trends chart with empty data
        const artistTrendsCanvas = document.getElementById('artistTrendsChart');
        if (artistTrendsCanvas && !artistChart) {  // Only create if it doesn't exist
            const artistData = {
                labels: ['No data yet'],
                datasets: [{
                    label: 'Play Count',
                    data: [0],
                    backgroundColor: '#1DB954',  // Spotify green
                    borderColor: '#191414',
                    borderWidth: 1
                }]
            };

            artistChart = new Chart(artistTrendsCanvas, {
                type: 'bar',
                data: artistData,
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Play Count'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Artists'
                            }
                        }
                    }
                }
            });

            // Fetch initial artist data
            fetchArtistStats();
        }
    }

    async function fetchGenreStats() {
        try {
            const response = await fetch('/genre-stats');
            if (response.ok) {
                const data = await response.json();
                if (data.success && genreChart) {
                    if (data.labels.length === 0) {
                        // If no data, show empty state
                        genreChart.data.labels = ['No data yet'];
                        genreChart.data.datasets[0].data = [1];
                        genreChart.data.datasets[0].backgroundColor = ['#b3b3b3'];
                    } else {
                        // Update with real data
                        genreChart.data.labels = data.labels;
                        genreChart.data.datasets[0].data = data.data;
                        genreChart.data.datasets[0].backgroundColor = [
                            '#1DB954',  // Spotify green
                            '#00ff00',  // Neon green
                            '#191414',  // Spotify black
                            '#b3b3b3',  // Spotify gray
                            '#ffffff'   // White
                        ];
                    }
                    genreChart.update();
                }
            } else {
                console.error('Error fetching genre stats:', response.statusText);
            }
        } catch (error) {
            console.error('Error fetching genre stats:', error);
        }
    }

    async function fetchArtistStats() {
        try {
            const response = await fetch('/artist-stats');
            if (response.ok) {
                const data = await response.json();
                if (data.success && artistChart) {
                    if (data.labels.length === 0) {
                        // If no data, show empty state
                        artistChart.data.labels = ['No data yet'];
                        artistChart.data.datasets[0].data = [0];
                        artistChart.data.datasets[0].backgroundColor = ['#b3b3b3'];  // Spotify gray for empty state
                    } else {
                        // Update with real data
                        artistChart.data.labels = data.labels;
                        artistChart.data.datasets[0].data = data.data;
                        // Use the same color scheme as the pie chart
                        artistChart.data.datasets[0].backgroundColor = [
                            '#1DB954',  // Spotify green
                            '#b3b3b3',  // Spotify gray
                            '#00ff00',  // Neon green
                            '#191414',  // Spotify black
                            '#ffffff',  // White
                            '#1DB954',  // Spotify green
                            '#b3b3b3',  // Spotify gray
                            '#00ff00',  // Neon green
                            '#191414',  // Spotify black
                            '#ffffff',  // White
                        ];
                    }
                    artistChart.update();
                }
            } else {
                console.error('Error fetching artist stats:', response.statusText);
            }
        } catch (error) {
            console.error('Error fetching artist stats:', error);
        }
    }

    function updateCharts(newData, metadata) {
        metricsOverTime = newData;
        searchNumbers = newData['search_numbers'] || [];

        console.log('Updating charts with data:', newData);

        if (precisionChart) {
            precisionChart.data.labels = searchNumbers;
            precisionChart.data.datasets[0].data = newData['likes_per_search'] || [];
            precisionChart.data.datasets[1].data = newData['cumulative_likes'] || [];
            console.log('Chart updated with labels:', precisionChart.data.labels);
            console.log('Likes per search data:', precisionChart.data.datasets[0].data);
            console.log('Cumulative likes data:', precisionChart.data.datasets[1].data);
            precisionChart.update('none');
        }

        // Update genre and artist stats when metrics are updated
        fetchGenreStats();
        fetchArtistStats();

        if (metadata) {
            updateTotalMetrics(metadata);
        }
    }

    function updateTotalMetrics(data) {
        const totalSearchesElement = document.getElementById('total-searches-value');
        const totalInteractionsElement = document.getElementById('total-interactions-value');
        const topSongElement = document.getElementById('top-song');
        const topAlbumElement = document.getElementById('top-album');
        const topArtistElement = document.getElementById('top-artist');
        const topSongDurationElement = document.querySelector('#top-song + .chart-description');

        if (totalSearchesElement && data.total_searches !== undefined) {
            totalSearchesElement.textContent = data.total_searches;
        }

        if (totalInteractionsElement && data.total_interactions !== undefined) {
            totalInteractionsElement.textContent = data.total_interactions;
        }

        console.log('Most played song data:', data.most_played_song);

        if (topSongElement && data.most_played_song) {
            const song = data.most_played_song;
            if (song.song === "No songs played yet") {
                topSongElement.textContent = song.song;
                if (topSongDurationElement) {
                    topSongDurationElement.textContent = '';
                }
            } else {
                topSongElement.textContent = `${song.song}`;
                if (topSongDurationElement) {
                    topSongDurationElement.textContent = `by ${song.artist} • ${song.duration} min`;
                }
            }
        }

        if (topAlbumElement && data.most_liked_album) {
            const album = data.most_liked_album;
            if (album.album === "No albums liked yet") {
                topAlbumElement.textContent = album.album;
            } else {
                topAlbumElement.textContent = album.album;
            }
        }

        if (topArtistElement && data.most_liked_artist) {
            const artist = data.most_liked_artist;
            if (artist.artist === "No artists liked yet") {
                topArtistElement.textContent = artist.artist;
            } else {
                topArtistElement.textContent = artist.artist;
            }
        }
    }

    async function fetchMetrics() {
        try {
            // Add a timestamp to prevent caching
            const timestamp = new Date().getTime();
            const response = await fetch(`/latest-metrics?_=${timestamp}`);
            if (response.ok) {
                const data = await response.json();
                console.log("Fetched metrics:", data);

                // Extract the data for updating charts
                const metadata = {
                    total_searches: data.total_searches,
                    total_interactions: data.total_interactions,
                    most_played_song: data.most_played_song,
                    most_liked_album: data.most_liked_album,
                    most_liked_artist: data.most_liked_artist
                };

                updateCharts(data.metrics_over_time, metadata);

                // Update the timestamp to indicate when data was refreshed
                if (document.getElementById('last-updated')) {
                    const now = new Date();
                    document.getElementById('last-updated').textContent =
                        `Last updated: ${now.toLocaleTimeString()}`;
                }
            } else {
                console.error('Error fetching metrics:', response.statusText);
            }
        } catch (error) {
            console.error('Error fetching metrics:', error);
        }
    }

    createCharts();

    // Listen for custom metrics update events
    window.addEventListener('metrics_updated', function() {
        console.log('Received metrics update notification');
        fetchMetrics();
    });

    // Refresh when visibility changes
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            console.log('Dashboard tab became visible, fetching latest metrics');
            fetchMetrics();
        }
    });

    // Initial fetch when the page loads
    fetchMetrics();

    // Refresh metrics every 5 seconds (shorter interval for more responsive updates)
    setInterval(fetchMetrics, 5000);
});
