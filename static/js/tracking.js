class TrackingManager {
    static currentSessionId = null;

    static setCurrentSession(sessionId) {
        TrackingManager.currentSessionId = sessionId;
        console.log(`Set current session ID: ${sessionId}`);
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

            console.log(`Tracking play for track ${trackId} with duration ${duration} seconds`);

            const response = await fetch(`/track-play/${trackId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    duration: duration
                })
            });

            const data = await response.json();

            if (data.success) {
                console.log(`Successfully tracked play for track ${trackId} with ${duration} seconds`);
                TrackingManager.notifyDashboardUpdate();
            } else {
                console.error('Failed to track play:', data.error);
            }
        } catch (error) {
            console.error('Error tracking play:', error);
        }
    }

    static async trackLike(itemText) {
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
                    interaction_type: "like",
                    session_id: TrackingManager.currentSessionId
                })
            });

            const data = await response.json();
            console.log(`Tracked like for "${itemText}" in session ${TrackingManager.currentSessionId}`);

            TrackingManager.notifyDashboardUpdate();
        } catch (error) {
            console.error('Error tracking like:', error);
        }
    }

    // Method to notify dashboard of updates
    static notifyDashboardUpdate() {
        window.dispatchEvent(new CustomEvent('metrics_updated'));
    }
}

// Remove session restoration code
window.TrackingManager = TrackingManager;
