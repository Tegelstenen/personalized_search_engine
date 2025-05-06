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

        console.log('Updating charts with new data:', newData);

        if (precisionChart) {
            precisionChart.data.labels = searchNumbers;
            precisionChart.data.datasets[0].data = newData['precision@5'] || [];
            precisionChart.data.datasets[1].data = newData['precision@10'] || [];
            precisionChart.update('none');
        }

        if (metadata) {
            updateTotalMetrics(metadata);
            sessionStorage.setItem('dashboardMetrics', JSON.stringify({
                metrics_over_time: newData,
                latest_metrics: metadata.latest_metrics,
                total_searches: metadata.total_searches,
                total_interactions: metadata.total_interactions,
                timestamp: new Date().toISOString()
            }));
        }
    }

    function updateTotalMetrics(data) {
        const totalSearchesElement = document.getElementById('total-searches');
        const totalInteractionsElement = document.getElementById('total-interactions');

        if (totalSearchesElement && data.total_searches !== undefined) {
            totalSearchesElement.textContent = data.total_searches;
        }

        if (totalInteractionsElement && data.total_interactions !== undefined) {
            totalInteractionsElement.textContent = data.total_interactions;
        }
    }

    async function fetchMetrics() {
        try {
            // Check if we have recent cached metrics (from the last 5 seconds)
            const cachedData = sessionStorage.getItem('dashboardMetrics');
            if (cachedData) {
                const parsedCache = JSON.parse(cachedData);
                const cacheTime = new Date(parsedCache.timestamp);
                const now = new Date();
                const cacheAgeMs = now - cacheTime;

                // If cache is fresh (less than 5 seconds old), use it
                if (cacheAgeMs < 5000) {
                    console.log("Using cached metrics data");
                    updateCharts(parsedCache.metrics_over_time, parsedCache);
                    return;
                }
            }

            // Use the new dedicated endpoint for faster updates
            const response = await fetch('/latest-metrics');
            if (response.ok) {
                const data = await response.json();
                console.log("Fetched metrics:", data);

                // Extract the data for updating charts
                const metadata = {
                    total_searches: data.total_searches,
                    total_interactions: data.total_interactions
                };

                updateCharts(data.metrics_over_time, metadata);

                // Also update the timestamp to indicate when data was refreshed
                if (document.getElementById('last-updated')) {
                    const now = new Date();
                    document.getElementById('last-updated').textContent =
                        `Last updated: ${now.toLocaleTimeString()}`;
                }
            }
        } catch (error) {
            console.error('Error fetching metrics:', error);

            // If fetching fails, try to use cached data regardless of age
            try {
                const cachedData = sessionStorage.getItem('dashboardMetrics');
                if (cachedData) {
                    const parsedCache = JSON.parse(cachedData);
                    console.log("Using cached metrics data due to fetch error");
                    updateCharts(parsedCache.metrics_over_time, parsedCache);

                    if (document.getElementById('last-updated')) {
                        document.getElementById('last-updated').textContent =
                            `Last updated: ${new Date(parsedCache.timestamp).toLocaleTimeString()} (cached)`;
                    }
                }
            } catch (cacheError) {
                console.error('Error using cached metrics:', cacheError);
            }
        }
    }

    createCharts();

    // Setup localStorage event listener for cross-tab communication
    window.addEventListener('storage', function(e) {
        // Only react to dashboard update events
        if (e.key === 'dashboard_update') {
            console.log('Received dashboard update notification');
            fetchMetrics();
        }
    });


    // Also fetch when the dashboard becomes visible again
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            console.log('Dashboard tab became visible, fetching latest metrics');
            fetchMetrics();
        }
    });

    // Initial fetch when the page loads
    fetchMetrics();
});
