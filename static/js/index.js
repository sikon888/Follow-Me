async function deleteVideo(filename, button) {

    const confirmed = confirm(
        `Delete "${filename}" and its reference?`
    );

    if (!confirmed) {
        return;
    }

    button.disabled = true;
    button.textContent = "Deleting...";

    try {

        const response = await fetch(
            "/delete/" + encodeURIComponent(filename),
            {
                method: "POST"
            }
        );

        const contentType =
            response.headers.get("content-type");

        let data;

        if (
            contentType &&
            contentType.includes("application/json")
        ) {
            data = await response.json();
        } else {
            const text = await response.text();

            throw new Error(
                `Server returned ${response.status}: ${text}`
            );
        }

        if (!response.ok) {
            throw new Error(
                data.error || "Delete failed"
            );
        }

        if (data.status === "Deleted") {
            window.location.reload();
            return;
        }

        throw new Error("Delete failed");

    } catch (error) {

        console.error(
            "DELETE ERROR:",
            error
        );

        alert(
            "Cannot delete file: " +
            error.message
        );

        button.disabled = false;
        button.textContent = "Delete";
    }
}


document
    .querySelectorAll(".delete-button")
    .forEach(button => {

        button.addEventListener(
            "click",
            function () {

                deleteVideo(
                    button.dataset.filename,
                    button
                );
            }
        );
    });

// =========================================
// CAMERA STATUS
// =========================================

async function checkCameraStatus() {

    const statusBox =
        document.getElementById(
            "cameraStatus"
        );

    const statusText =
        document.getElementById(
            "cameraStatusText"
        );


    try {

        const response =
            await fetch(
                "/api/camera/status"
            );


        const data =
            await response.json();


        if (data.connected) {

            statusBox.classList.remove(
                "disconnected"
            );

            statusBox.classList.add(
                "connected"
            );

            statusText.textContent =
                "Connected";

        }

        else {

            statusBox.classList.remove(
                "connected"
            );

            statusBox.classList.add(
                "disconnected"
            );

            statusText.textContent =
                "Disconnected";

        }

    }

    catch (error) {

        statusBox.classList.remove(
            "connected"
        );

        statusBox.classList.add(
            "disconnected"
        );

        statusText.textContent =
            "Disconnected";

    }

}


// เช็กทันทีตอนเปิดหน้า
checkCameraStatus();


// เช็กใหม่ทุก 2 วินาที
setInterval(
    checkCameraStatus,
    2000
);
const youtubeForm = document.getElementById('youtubeSearchForm');
const youtubeSection = document.getElementById('youtubeSearchSection');
const youtubeResults = document.getElementById('youtubeResults');
const youtubeStatus = document.getElementById('youtubeSearchStatus');
const youtubeLink = document.getElementById('youtubeSearchLink');
let youtubeRequest = null;
document.getElementById('closeYoutubeSearch').addEventListener('click', () => {
    youtubeRequest?.abort();
    youtubeSection.hidden = true;
});
youtubeForm.addEventListener('submit', async event => {
    event.preventDefault();
    const query = document.getElementById('youtubeQuery').value.trim();
    if (!query) return;
    youtubeRequest?.abort();
    const controller = new AbortController();
    youtubeRequest = controller;
    const button = document.getElementById('youtubeSearchButton');
    button.disabled = true;
    youtubeSection.hidden = false;
    youtubeResults.replaceChildren();
    youtubeStatus.textContent = 'Searching YouTube...';
    youtubeLink.href = 'https://www.youtube.com/results?search_query=' + encodeURIComponent(query);
    youtubeLink.hidden = false;
    try {
        const response = await fetch('/api/youtube/search?q=' + encodeURIComponent(query), {signal: controller.signal});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'YouTube search failed.');
        for (const video of data.videos) {
            const card = document.createElement('article');
            card.className = 'youtube-result';
            const watch = document.createElement('a');
            watch.href = video.url;
            watch.target = '_blank';
            watch.rel = 'noopener noreferrer';
            const image = document.createElement('img');
            image.src = video.thumbnail;
            image.alt = '';
            image.loading = 'lazy';
            const title = document.createElement('h3');
            title.textContent = video.title;
            const channel = document.createElement('p');
            channel.textContent = video.channel;
            watch.append(image, title, channel);
            const save = document.createElement('button');
            save.type = 'button';
            save.className = 'youtube-save-button';
            save.textContent = 'Save Video';
            const message = document.createElement('p');
            message.setAttribute('role', 'status');
            const open = document.createElement('a');
            open.className = 'youtube-open-video';
            open.hidden = true;
            open.textContent = 'Open Video / Build Reference';
            save.addEventListener('click', () => saveYoutubeVideo(video.id, save, message, open));
            card.append(watch, save, message, open);
            youtubeResults.append(card);
        }
        youtubeStatus.textContent = data.videos.length ? 'Select a video to watch on YouTube.' : 'No videos found. Try another search.';
    } catch (error) {
        if (error.name !== 'AbortError') youtubeStatus.textContent = error.message;
    } finally {
        if (youtubeRequest === controller) button.disabled = false;
    }
});

async function saveYoutubeVideo(id, button, message, open) {
    button.disabled = true;
    button.textContent = 'Saving...';
    open.hidden = true;
    message.textContent = 'Starting download...';
    try {
        const endpoint = '/api/youtube/download/' + encodeURIComponent(id);
        let response = await fetch(endpoint, {method: 'POST'});
        let result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Cannot start download');
        while (result.status === 'Downloading') {
            message.textContent = `Downloading ${result.progress || 0}%`;
            await new Promise(resolve => setTimeout(resolve, 1000));
            response = await fetch(endpoint);
            result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Cannot check download');
        }
        if (result.status !== 'Saved') throw new Error(result.error || 'Download interrupted. Try again.');
        button.textContent = 'Saved';
        message.textContent = 'Saved to your playlist. Open the video to build a reference.';
        open.href = '/video/' + encodeURIComponent(result.filename);
        open.hidden = false;
    } catch (error) {
        message.textContent = error.message;
        button.disabled = false;
        button.textContent = 'Retry Save';
    }
}
