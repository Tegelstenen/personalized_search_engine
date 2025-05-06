document.addEventListener('DOMContentLoaded', function() {
    // Chart configuration
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

    // Initialize with empty data if no server data is available
    function createCharts() {
        if (document.getElementById('precisionLineChart')) {
            const precisionData = {
                labels: [],
                datasets: [
                    {
                        label: 'Precision@5',
                        data: [],
                        borderColor: '#1db954',
                        backgroundColor: 'rgba(29, 185, 84, 0.1)',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Precision@10',
                        data: [],
                        borderColor: '#3e7d32',
                        backgroundColor: 'rgba(62, 125, 50, 0.1)',
                        fill: false,
                        tension: 0.1
                    }
                ]
            };

            console.log('Creating initial precision chart');

            precisionChart = new Chart(document.getElementById('precisionLineChart'), {
                type: 'line',
                data: precisionData,
                options: lineChartOptions
            });
        }
    }

    // Update chart data when new data is fetched
    function updateCharts(newData, metadata) {
        console.log('Updating charts with data:', newData);

        if (precisionChart && newData) {
            const searchNumbers = newData['search_numbers'] || [];
            const precision5Data = newData['precision@5'] || [];
            const precision10Data = newData['precision@10'] || [];

            precisionChart.data.labels = searchNumbers;
            precisionChart.data.datasets[0].data = precision5Data;
            precisionChart.data.datasets[1].data = precision10Data;
            precisionChart.update();

            console.log('Chart updated with labels:', searchNumbers);
            console.log('Precision@5 data:', precision5Data);
            console.log('Precision@10 data:', precision10Data);
        } else {
            console.warn('Chart or data unavailable for update');
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

        if (totalSearchesElement && data.total_searches !== undefined) {
            totalSearchesElement.textContent = data.total_searches;
        }

        if (totalInteractionsElement && data.total_interactions !== undefined) {
            totalInteractionsElement.textContent = data.total_interactions;
        }

        if (topSongElement && data.most_played_song) {
            const song = data.most_played_song;
            if (song.song === "No songs played yet") {
                topSongElement.textContent = song.song;
            } else {
                topSongElement.textContent = song.song;
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
            console.log('Fetching metrics from /latest-metrics');
            const response = await fetch('/latest-metrics');

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

                // Also update the timestamp to indicate when data was refreshed
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

    // Initialize charts and fetch data
    createCharts();
    fetchMetrics();

    // Listen for custom metrics update events
    window.addEventListener('metrics_updated', function() {
        console.log('Received metrics update notification');
        fetchMetrics();
    });

    // Also fetch when the dashboard becomes visible again
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            console.log('Dashboard tab became visible, fetching latest metrics');
            fetchMetrics();
        }
    });

    // Refresh metrics every 10 seconds
    setInterval(fetchMetrics, 10000);
});
