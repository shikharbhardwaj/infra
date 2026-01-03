// Minimal JavaScript enhancements for Replay Hub

// Log app initialization
console.log('Replay Hub initialized');

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Press '/' to focus search
    if (e.key === '/' && document.getElementById('searchInput')) {
        e.preventDefault();
        document.getElementById('searchInput').focus();
    }

    // Press 'Escape' to clear search
    if (e.key === 'Escape' && document.getElementById('searchInput')) {
        document.getElementById('searchInput').value = '';
        document.getElementById('searchInput').dispatchEvent(new Event('input'));
    }
});

// Video player enhancements
document.addEventListener('DOMContentLoaded', function() {
    const video = document.getElementById('videoPlayer');

    if (video) {
        // Remember playback position
        const videoPath = video.src;
        const savedTime = localStorage.getItem(`playback_${videoPath}`);

        if (savedTime) {
            video.currentTime = parseFloat(savedTime);
        }

        // Save playback position periodically
        video.addEventListener('timeupdate', function() {
            localStorage.setItem(`playback_${videoPath}`, video.currentTime);
        });

        // Clear playback position when video ends
        video.addEventListener('ended', function() {
            localStorage.removeItem(`playback_${videoPath}`);
        });

        // Keyboard controls for video
        document.addEventListener('keydown', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return; // Don't interfere with form inputs
            }

            switch(e.key) {
                case ' ':
                    e.preventDefault();
                    video.paused ? video.play() : video.pause();
                    break;
                case 'ArrowLeft':
                    video.currentTime -= 5;
                    break;
                case 'ArrowRight':
                    video.currentTime += 5;
                    break;
                case 'f':
                    if (video.requestFullscreen) {
                        video.requestFullscreen();
                    }
                    break;
                case 'm':
                    video.muted = !video.muted;
                    break;
            }
        });
    }
});
