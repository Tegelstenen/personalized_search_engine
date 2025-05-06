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
                max: 1.0,
                ticks: {
                    callback: function(value) {
                        return (value * 100) + '%';
                    }
                },
                title: {
                    display: true,
                    text: 'Score'
                }
            }
        },
        plugins: {
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return context.dataset.label + ': ' + (context.parsed.y * 100).toFixed(2) + '%';
                    }
                }
            },
            legend: {
                position: 'top'
            }
        }
    };

    let precisionChart;
    let metricsOverTime = window.initialMetricsOverTime || {};
    let searchNumbers = metricsOverTime['search_numbers'] || [];

    function createCharts() {
        if (document.getElementById('precisionLineChart')) {
            const precisionData = {
                labels: searchNumbers,
                datasets: [
                    {
                        label: 'Precision@5',
                        data: metricsOverTime['precision@5'] || [],
                        borderColor: '#1db954',
                        backgroundColor: 'rgba(29, 185, 84, 0.1)',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Precision@10',
                        data: metricsOverTime['precision@10'] || [],
                        borderColor: '#3e7d32',
                        backgroundColor: 'rgba(62, 125, 50, 0.1)',
                        fill: false,
                        tension: 0.1
                    }
                ]
            };

            console.log('Creating precision chart with data:', precisionData);

            precisionChart = new Chart(document.getElementById('precisionLineChart'), {
                type: 'line',
                data: precisionData,
                options: lineChartOptions
            });
        }
    }

    function updateCharts(newData, metadata) {
        metricsOverTime = newData;
        searchNumbers = newData['search_numbers'] || [];

        console.log('Updating charts with data:', newData);

        if (precisionChart) {
            precisionChart.data.labels = searchNumbers;
            precisionChart.data.datasets[0].data = newData['precision@5'] || [];
            precisionChart.data.datasets[1].data = newData['precision@10'] || [];
            console.log('Chart updated with labels:', precisionChart.data.labels);
            console.log('Precision@5 data:', precisionChart.data.datasets[0].data);
            console.log('Precision@10 data:', precisionChart.data.datasets[1].data);
            precisionChart.update('none');
        }

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
