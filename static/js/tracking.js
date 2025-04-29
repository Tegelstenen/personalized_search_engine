// Tracking functionality for user interactions
class TrackingManager {
    static async trackClick(itemText, itemType = "song") {
        try {
            await fetch('/track-click', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    item_text: itemText,
                    item_type: itemType
                })
            });
        } catch (error) {
            console.error('Error tracking click:', error);
        }
    }

    static async trackPlay(trackId, duration = 0) {
        try {
            if (!trackId || typeof trackId !== 'string') {
                console.error('Invalid track ID:', trackId);
                return;
            }

            await fetch('/track-play/' + trackId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ duration: duration })
            });
        } catch (error) {
            console.error('Error tracking play:', error);
        }
    }
}

window.TrackingManager = TrackingManager;
