// =========================================
// ELEMENTS
// =========================================

const videoInput =
    document.getElementById(
        "videoInput"
    );


const filenameText =
    document.getElementById(
        "filename"
    );


// =========================================
// FILE SELECT
// =========================================

videoInput.addEventListener(
    "change",
    function () {

        if (
            videoInput.files.length > 0
        ) {

            filenameText.textContent =
                videoInput.files[0].name;

        }

        else {

            filenameText.textContent =
                "ยังไม่ได้เลือกไฟล์";

        }

    }
);