// Tracking functionality for user interactions
class TrackingManager {
    // Class variable to store current session ID
    static currentSessionId = null;

    static setCurrentSession(sessionId) {
        TrackingManager.currentSessionId = sessionId;
        console.log(`Set current session ID: ${sessionId}`);

        // Store in sessionStorage for persistence
        sessionStorage.setItem('lastSearchSessionId', sessionId);
    }

    static async trackClick(itemText, interactionType = "click") {
        try {
            if (!TrackingManager.currentSessionId) {
                console.error('No session ID available for tracking');
                return;
            }

            const response = await fetch('/track-click', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    item_text: itemText,
                    item_type: "song",
                    interaction_type: interactionType,
                    session_id: TrackingManager.currentSessionId
                })
            });

            const data = await response.json();
            console.log(`Tracked ${interactionType} for "${itemText}" in session ${TrackingManager.currentSessionId}`);

            // Store the latest metrics in localStorage
            if (data.latest_metrics) {
                localStorage.setItem('latest_metrics', JSON.stringify(data.latest_metrics));
                console.log("Updated latest metrics:", data.latest_metrics);
            }

            // Notify any dashboard that might be open in another tab
            TrackingManager.notifyDashboardUpdate();
        } catch (error) {
            console.error(`Error tracking ${interactionType}:`, error);
        }
    }

    static async trackPlay(trackId, duration = 0) {
        try {
            if (!trackId || typeof trackId !== 'string') {
                console.error('Invalid track ID:', trackId);
                return;
            }

            if (!TrackingManager.currentSessionId) {
                console.error('No session ID available for tracking');
                return;
            }

            // First get the track details to get the item text
            const trackResponse = await fetch(`/get-spotify-track/${trackId}`);
            const trackData = await trackResponse.json();

            if (!trackData.track) {
                console.error('Could not get track details');
                return;
            }

            const track = trackData.track;
            const itemText = `${track.name} by ${track.artist}`;

            // Track the play as an interaction
            await fetch('/track-click', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    item_text: itemText,
                    item_type: "song",
                    interaction_type: "play",
                    session_id: TrackingManager.currentSessionId
                })
            });

            console.log(`Tracked play for "${itemText}" in session ${TrackingManager.currentSessionId}`);

            // Notify any dashboard that might be open in another tab
            TrackingManager.notifyDashboardUpdate();
        } catch (error) {
            console.error('Error tracking play:', error);
        }
    }

    // Method to notify dashboard of updates (using localStorage for cross-tab communication)
    static notifyDashboardUpdate() {
        // Update localStorage with a timestamp to trigger the storage event
        localStorage.setItem('dashboard_update', Date.now().toString());
        console.log("Dashboard update notification sent");
    }
}

// Remove session restoration code
window.TrackingManager = TrackingManager;
