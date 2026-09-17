import datetime
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import imagehash
from PIL import Image

# Configuration
HASH_THRESHOLD = 4
BATCH_SIZE = 300  # Frames per batch in RAM
PADDING_HEIGHT = 28  # Height of the black footer bar for the timestamp

# Crop Coordinates (Top Left: 1582, 873 | Bottom Right: 1755, 1083)
CROP_Y1 = 850
CROP_Y2 = 1045
CROP_X1 = 1582
CROP_X2 = 1755


def format_timestamp(ms):
    """Converts milliseconds into a readable HH:MM:SS.mmm string."""
    if ms < 0:
        return "Unknown Time"
    td = datetime.timedelta(milliseconds=ms)
    return str(td)[:-3]


def is_hud_present(cropped_frame):
    """
    Checks if the circular wheel HUD is active by detecting the bright 'Q' and 'E'
    indicator boxes in the top corners of the cropped area.
    """
    if cropped_frame is None or cropped_frame.size == 0:
        return False

    gray = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Define regions where Q (top-left) and E (top-right) boxes reside
    q_region = gray[0 : int(h * 0.25), 0 : int(w * 0.35)]
    e_region = gray[0 : int(h * 0.25), int(w * 0.65) : w]

    # Count bright white pixels (above 220 intensity)
    q_bright = (q_region > 220).sum()
    e_bright = (e_region > 220).sum()

    # Both indicator boxes must be present (adjust threshold if necessary)
    return q_bright > 30 and e_bright > 30


def process_frame_worker(data):
    """
    Worker function executed across CPU cores.
    Checks HUD presence and computes perceptual hash.
    """
    frame_idx, timestamp_ms, cropped_frame = data

    # 1. Check if the circle/HUD is present
    hud_visible = is_hud_present(cropped_frame)
    if not hud_visible:
        return frame_idx, timestamp_ms, cropped_frame, None, False

    # 2. Compute difference hash on the valid HUD crop
    rgb_crop = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_crop)
    current_hash = imagehash.dhash(pil_img)

    return frame_idx, timestamp_ms, cropped_frame, current_hash, True


def extract_and_deduplicate(output_dir, video_path, hash_threshold=4):
    if not os.path.exists(video_path):
        print(f"Error: Video file '{video_path}' not found.")
        return

    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    frame_count = 0
    saved_count = 0
    skipped_hud_count = 0
    last_saved_hash = None

    cores = multiprocessing.cpu_count()
    print(f"Processing video using {cores} CPU cores...")

    with ProcessPoolExecutor(max_workers=cores) as executor:
        while True:
            batch = []

            # 1. Producer: Read sequential frames and crop them
            for _ in range(BATCH_SIZE):
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                cropped_frame = frame[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2]
                timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)

                batch.append((frame_count, timestamp_ms, cropped_frame))

            if not batch:
                break

            # 2. Workers: Evaluate HUD visibility & hashes in parallel
            for result in executor.map(process_frame_worker, batch):
                f_idx, ts_ms, cropped_frame, current_hash, hud_visible = result

                # Skip frames where HUD is not visible
                if not hud_visible:
                    skipped_hud_count += 1
                    continue

                # Deduplicate consecutive identical/similar frames
                if last_saved_hash is not None:
                    hash_diff = current_hash - last_saved_hash
                    if hash_diff <= hash_threshold:
                        continue

                # 3. Add black padding at the bottom for the timeline bar
                padded_frame = cv2.copyMakeBorder(
                    cropped_frame,
                    top=0,
                    bottom=PADDING_HEIGHT,
                    left=0,
                    right=0,
                    borderType=cv2.BORDER_CONSTANT,
                    value=[0, 0, 0],  # Black color
                )

                # 4. Overlay timestamp inside the padded area
                time_str = format_timestamp(ts_ms)
                text_position = (8, cropped_frame.shape[0] + 19)
                cv2.putText(
                    padded_frame,
                    time_str,
                    text_position,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 0),  # Green text
                    1,
                    cv2.LINE_AA,
                )

                # 5. Save frame
                saved_count += 1
                output_filename = os.path.join(
                    output_dir, f"frame_{saved_count:05d}.jpg"
                )
                cv2.imwrite(output_filename, padded_frame)

                last_saved_hash = current_hash

            print(
                f"Processed {frame_count} frames... (Saved {saved_count} unique HUD crops)"
            )

    cap.release()
    print(f"\nDone! Processed {frame_count} total frames.")
    print(f"Filtered out {skipped_hud_count} non-HUD frames.")
    print(f"Saved {saved_count} unique cropped frames to '{output_dir}'.")


if __name__ == "__main__":
    video = Path(
        r"C:\Program Files (x86)\Steam\userdata\279248004\gamerecordings\video\bg_1938090_20260917_000457\output.mp4"
    )
    ws = Path(__file__).parent

    extract_and_deduplicate(
        output_dir=ws / "images",
        video_path=video,
        hash_threshold=HASH_THRESHOLD,
    )
