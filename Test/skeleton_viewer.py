import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from pathlib import Path

# =========================
# CONFIG
# =========================

REFERENCE_FOLDER = Path("reference_library")

# ใส่ชื่อไฟล์ที่ต้องการดู
FILE_NAME = "snaptik_7372751698168679681_v3_normalized.npy"

CONF_THRESHOLD = 0.3

# ความเร็ว animation
INTERVAL = 33  # ms ≈ 30 FPS


# =========================
# COCO SKELETON
# =========================

CONNECTIONS = [
    (0, 1), (0, 2),
    (1, 3), (2, 4),

    (5, 6),

    (5, 7), (7, 9),
    (6, 8), (8, 10),

    (5, 11), (6, 12),

    (11, 12),

    (11, 13), (13, 15),
    (12, 14), (14, 16)
]


# =========================
# LOAD FILE
# =========================

file_path = REFERENCE_FOLDER / FILE_NAME

if not file_path.is_file():
    raise FileNotFoundError(
        f"Cannot find: {file_path}"
    )

data = np.load(file_path)

print("Loaded:", file_path)
print("Shape:", data.shape)
print("Frames:", len(data))


if data.ndim != 3 or data.shape[1:] != (17, 3):
    raise ValueError(
        "Skeleton file must have shape (frames, 17, 3)"
    )


# =========================
# FIGURE
# =========================

fig, ax = plt.subplots()

ax.set_title(FILE_NAME)

ax.set_aspect("equal")

ax.set_xlim(-3, 3)
ax.set_ylim(3, -3)

ax.set_xlabel("X")
ax.set_ylabel("Y")

ax.grid(True, alpha=0.2)


# keypoints
scatter = ax.scatter([], [], s=35)

# skeleton lines
lines = []

for _ in CONNECTIONS:
    line, = ax.plot([], [], linewidth=2)
    lines.append(line)


# frame text
frame_text = ax.text(
    0.02,
    0.97,
    "",
    transform=ax.transAxes,
    verticalalignment="top"
)


# =========================
# UPDATE
# =========================

def update(frame_number):

    skeleton = data[frame_number]

    xy = skeleton[:, :2]

    confidence = skeleton[:, 2]

    valid = confidence >= CONF_THRESHOLD


    # -------------------------
    # Draw points
    # -------------------------

    visible_points = xy[valid]

    if len(visible_points) > 0:
        scatter.set_offsets(visible_points)
    else:
        scatter.set_offsets(
            np.empty((0, 2))
        )


    # -------------------------
    # Draw connections
    # -------------------------

    for line, (point_a, point_b) in zip(
        lines,
        CONNECTIONS
    ):

        if (
            confidence[point_a] >= CONF_THRESHOLD
            and
            confidence[point_b] >= CONF_THRESHOLD
        ):

            x = [
                xy[point_a, 0],
                xy[point_b, 0]
            ]

            y = [
                xy[point_a, 1],
                xy[point_b, 1]
            ]

            line.set_data(x, y)

        else:

            line.set_data([], [])


    # -------------------------
    # Frame number
    # -------------------------

    frame_text.set_text(
        f"Frame: {frame_number + 1} / {len(data)}"
    )


    return [
        scatter,
        frame_text,
        *lines
    ]


# =========================
# ANIMATION
# =========================

animation = FuncAnimation(
    fig,
    update,
    frames=len(data),
    interval=INTERVAL,
    blit=False,
    repeat=True
)

plt.show()