import os
import cv2
import datetime
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from PIL import Image
import imagehash
from pathlib import Path

# Configuration
HASH_THRESHOLD = 4
BATCH_SIZE = 300  # Number of frames to hold in memory per multiprocessing batch

# Crop Coordinates (Top Left: 1582, 873 | Bottom Right: 1755, 1083)
CROP_Y1 = 873
CROP_Y2 = 1083
CROP_X1 = 1582
CROP_X2 = 1755


def format_timestamp(ms):
    """Converts milliseconds into a readable HH:MM:SS.mmm string."""
    if ms < 0:
        return "Unknown Time"
    td = datetime.timedelta(milliseconds=ms)
    return str(td)[:-3]


def compute_hash(data):
    """
    Worker function mapped across CPU cores.
    Must be at the top level for Windows multiprocessing to pickle it.
    """
    frame_idx, timestamp_ms, cropped_frame = data

    # Convert OpenCV BGR frame to PIL Image
    rgb_crop = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_crop)

    # Compute difference hash
    current_hash = imagehash.dhash(pil_img)

    return frame_idx, timestamp_ms, cropped_frame, current_hash


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
    last_saved_hash = None

    # Get total CPU cores available
    cores = multiprocessing.cpu_count()
    print(f"Processing video using {cores} CPU cores...")

    # Start the multiprocessing pool
    with ProcessPoolExecutor(max_workers=cores) as executor:
        while True:
            batch = []

            # 1. Producer: Read a batch of frames sequentially
            for _ in range(BATCH_SIZE):
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1

                # Crop immediately so we pass less data through RAM to the workers
                cropped_frame = frame[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2]
                timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)

                batch.append((frame_count, timestamp_ms, cropped_frame))

            if not batch:
                break  # End of video reached

            # 2. Workers: Compute hashes in parallel, returning them in exact order
            for result in executor.map(compute_hash, batch):
                f_idx, ts_ms, cropped_frame, current_hash = result

                # 3. Consumer: Check for duplicates sequentially
                if last_saved_hash is not None:
                    hash_diff = current_hash - last_saved_hash
                    if hash_diff <= hash_threshold:
                        continue  # Skip duplicate

                # 4. Save unique frame
                time_str = format_timestamp(ts_ms)
                text_position = (5, cropped_frame.shape[0] - 10)

                cv2.putText(
                    cropped_frame,
                    time_str,
                    text_position,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )

                saved_count += 1
                output_filename = os.path.join(
                    output_dir, f"frame_{saved_count:05d}.jpg"
                )
                cv2.imwrite(output_filename, cropped_frame)

                # Update the sequential state tracker
                last_saved_hash = current_hash

            print(
                f"Processed {frame_count} frames... (Saved {saved_count} unique crops)"
            )

    cap.release()
    print(f"\nDone! Processed {frame_count} total frames.")
    print(f"Saved {saved_count} unique cropped frames to '{output_dir}'.")


if __name__ == "__main__":
    # Ensure this points to the new output.mp4 file you generated with FFmpeg
    video = Path(
        r"C:\Program Files (x86)\Steam\userdata\279248004\gamerecordings\video\bg_1938090_20260917_000457\output.mp4"
    )
    ws = Path(__file__).parent

    extract_and_deduplicate(
        output_dir=ws / "images",
        video_path=video,
        hash_threshold=HASH_THRESHOLD,
    )
