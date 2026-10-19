// =========================================
// VIDEO DATA
// =========================================

const videoFilename =
    document
        .getElementById(
            "videoData"
        )
        .dataset
        .filename;


// =========================================
// ELEMENTS
// =========================================

const saveButton =
    document.getElementById(
        "saveButton"
    );


const statusText =
    document.getElementById(
        "status"
    );


const referenceText =
    document.getElementById(
        "reference"
    );


const errorText =
    document.getElementById(
        "error"
    );


// =========================================
// SAVE REFERENCE
// =========================================

async function saveReference() {

    saveButton.disabled =
        true;


    saveButton.textContent =
        "Processing...";


    statusText.textContent =
        "Processing";


    referenceText.textContent =
        "";


    errorText.textContent =
        "";


    try {

        const response =
            await fetch(

                "/save/" +
                encodeURIComponent(
                    videoFilename
                ),

                {
                    method:
                        "POST"
                }

            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Cannot start processing"
            );

        }


        checkStatus();

    }

    catch (error) {

        console.error(
            "SAVE ERROR:",
            error
        );


        statusText.textContent =
            "Error";


        errorText.textContent =
            error.message;


        saveButton.disabled =
            false;


        saveButton.textContent =
            "Save Reference";

    }

}


// =========================================
// CHECK STATUS
// =========================================

async function checkStatus() {

    try {

        const response =
            await fetch(

                "/status/" +
                encodeURIComponent(
                    videoFilename
                )

            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Cannot check status"
            );

        }


        statusText.textContent =
            data.status;


        // ---------------------------------
        // PROCESSING
        // ---------------------------------

        if (
            data.status ===
            "Processing"
        ) {

            setTimeout(
                checkStatus,
                1000
            );

            return;
        }


        // ---------------------------------
        // SAVED
        // ---------------------------------

        if (
            data.status ===
            "Saved"
        ) {

            saveButton.textContent =
                "Rebuild Reference";


            if (data.reference) {

                referenceText.textContent =
                    "Reference: " +
                    data.reference;

            }

        }


        // ---------------------------------
        // ERROR
        // ---------------------------------

        else if (
            data.status ===
            "Error"
        ) {

            errorText.textContent =
                data.error ||
                "Processing failed";


            saveButton.textContent =
                "Try Again";

        }


        // ---------------------------------
        // NOT SAVED
        // ---------------------------------

        else {

            saveButton.textContent =
                "Save Reference";

        }


        saveButton.disabled =
            false;

    }

    catch (error) {

        console.error(
            "STATUS ERROR:",
            error
        );


        statusText.textContent =
            "Error";


        errorText.textContent =
            error.message;


        saveButton.disabled =
            false;


        saveButton.textContent =
            "Save Reference";

    }

}


// =========================================
// SAVE BUTTON EVENT
// =========================================

saveButton.addEventListener(
    "click",
    saveReference
);


// =========================================
// INITIAL STATUS
// =========================================

const initialStatus =
    statusText
        .textContent
        .trim();


if (
    initialStatus ===
    "Processing"
) {

    saveButton.disabled =
        true;


    saveButton.textContent =
        "Processing...";


    checkStatus();

}


else if (
    initialStatus ===
    "Saved"
) {

    saveButton.textContent =
        "Rebuild Reference";

}
// Draw the saved pixel coordinates against the video's actual presentation time.
const skeletonButton = document.getElementById('skeletonButton');
const skeletonCanvas = document.getElementById('referenceSkeleton');
const previewVideo = document.querySelector('.video-player');
const skeletonContext = skeletonCanvas.getContext('2d');
const skeletonHint = document.getElementById('skeletonHint');
const skeletonEdges = [[0,1],[0,2],[1,3],[2,4],[5,6],[5,7],[7,9],
    [6,8],[8,10],[5,11],[6,12],[11,12],[11,13],[13,15],[12,14],[14,16]];
let skeletonData = null;
let skeletonVisible = false;
let skeletonLoading = false;

function updateSkeletonAvailability() {
    skeletonButton.disabled = skeletonLoading || statusText.textContent.trim() !== 'Saved';
    if (statusText.textContent.trim() !== 'Saved') {
        skeletonData = null;
        skeletonVisible = false;
        skeletonCanvas.hidden = true;
        skeletonHint.hidden = true;
        skeletonButton.textContent = 'Show Skeleton';
        skeletonButton.setAttribute('aria-pressed', 'false');
    }
}
new MutationObserver(updateSkeletonAvailability).observe(statusText, {childList: true, subtree: true});
updateSkeletonAvailability();

function drawReferenceSkeleton() {
    if (!skeletonVisible || !skeletonData || !previewVideo.videoWidth) return;
    const width = previewVideo.videoWidth;
    const height = previewVideo.videoHeight;
    // Match object-fit: contain, including letterboxing and the video border.
    const scale = Math.min(previewVideo.clientWidth / width, previewVideo.clientHeight / height);
    skeletonCanvas.style.width = `${width * scale}px`;
    skeletonCanvas.style.height = `${height * scale}px`;
    skeletonCanvas.style.left = `${previewVideo.offsetLeft + previewVideo.clientLeft + (previewVideo.clientWidth - width * scale) / 2}px`;
    skeletonCanvas.style.top = `${previewVideo.offsetTop + previewVideo.clientTop + (previewVideo.clientHeight - height * scale) / 2}px`;
    if (skeletonCanvas.width !== width || skeletonCanvas.height !== height) {
        skeletonCanvas.width = width;
        skeletonCanvas.height = height;
    }
    skeletonContext.clearRect(0, 0, width, height);
    const times = skeletonData.timestamps;
    let low = 0, high = times.length;
    while (low < high) {
        const mid = (low + high) >>> 1;
        if (times[mid] <= previewVideo.currentTime) low = mid + 1;
        else high = mid;
    }
    if (!low) return;
    const pose = skeletonData.skeleton[low - 1];
    const valid = index => pose[index][2] >= 0.3;
    skeletonHint.textContent = pose.some((point) => point[2] >= 0.3)
        ? 'Showing saved reference skeleton.'
        : 'No pose detected in this frame. Play or seek the video to see the skeleton.';
    skeletonContext.lineWidth = Math.max(3, width / 220);
    skeletonContext.strokeStyle = '#54ffb0';
    skeletonContext.fillStyle = '#fff';
    skeletonContext.shadowColor = '#000';
    skeletonContext.shadowBlur = 4;
    for (const [a, b] of skeletonEdges) {
        if (!valid(a) || !valid(b)) continue;
        skeletonContext.beginPath();
        skeletonContext.moveTo(pose[a][0], pose[a][1]);
        skeletonContext.lineTo(pose[b][0], pose[b][1]);
        skeletonContext.stroke();
    }
    pose.forEach((point, i) => {
        if (!valid(i)) return;
        skeletonContext.beginPath();
        skeletonContext.arc(point[0], point[1], Math.max(4, width / 160), 0, Math.PI * 2);
        skeletonContext.fill();
    });
}

skeletonButton.addEventListener('click', async () => {
    if (skeletonLoading) return;
    if (!skeletonVisible) {
        skeletonLoading = true;
        skeletonButton.disabled = true;
        skeletonButton.textContent = 'Loading Skeleton...';
        try {
            const response = await fetch('/api/reference-skeleton/' + encodeURIComponent(videoFilename));
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Cannot load reference skeleton');
            // A rebuild may have started while the request was in flight.
            if (statusText.textContent.trim() !== 'Saved') return;
            skeletonData = data;
            skeletonVisible = true;
            errorText.textContent = '';
        } catch (error) {
            errorText.textContent = error.message;
        } finally {
            skeletonLoading = false;
            updateSkeletonAvailability();
        }
    } else {
        skeletonVisible = false;
    }
    skeletonCanvas.hidden = !skeletonVisible;
    skeletonHint.hidden = !skeletonVisible;
    skeletonButton.textContent = skeletonVisible ? 'Hide Skeleton' : 'Show Skeleton';
    skeletonButton.setAttribute('aria-pressed', String(skeletonVisible));
    drawReferenceSkeleton();
});
for (const event of ['loadedmetadata', 'seeked', 'timeupdate', 'pause']) {
    previewVideo.addEventListener(event, drawReferenceSkeleton);
}
new ResizeObserver(drawReferenceSkeleton).observe(previewVideo);
function previewFrame() {
    drawReferenceSkeleton();
    if (previewVideo.requestVideoFrameCallback) previewVideo.requestVideoFrameCallback(previewFrame);
    else requestAnimationFrame(previewFrame);
}
previewFrame();

const renameReferenceForm = document.getElementById('renameReferenceForm');
renameReferenceForm.addEventListener('submit', async event => {
    event.preventDefault();
    const button = document.getElementById('renameReferenceButton');
    const message = document.getElementById('renameReferenceStatus');
    button.disabled = true;
    message.textContent = 'Saving...';
    try {
        const response = await fetch('/api/reference-name/' + encodeURIComponent(videoFilename), {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: document.getElementById('referenceName').value})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Cannot save name');
        document.querySelector('.filename').textContent = data.name;
        document.getElementById('referenceName').value = data.name;
        document.title = data.name;
        message.textContent = 'Reference name saved.';
    } catch (error) {
        message.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});
