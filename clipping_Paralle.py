import os
import cv2
import datetime
import multiprocessing
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from PIL import Image
import imagehash
from pathlib import Path

# Configuration
HASH_THRESHOLD = 4
BATCH_SIZE = 300
PADDING_HEIGHT = 28

# Crop Coordinates
CROP_Y1, CROP_Y2 = 877, 1051
CROP_X1, CROP_X2 = 1581, 1755

# Sub-box relative coordinates inside the crop
SUB_REL_Y1 = 938 - CROP_Y1  # 61
SUB_REL_Y2 = 992 - CROP_Y1  # 115
SUB_REL_X1 = 1640 - CROP_X1  # 59
SUB_REL_X2 = 1700 - CROP_X1  # 119

# Weapon RGB Color Range (66 to 82)
LOWER_RGB = np.array([66, 66, 66], dtype=np.uint8)
UPPER_RGB = np.array([82, 82, 82], dtype=np.uint8)


def format_timestamp(ms):
    if ms < 0:
        return "Unknown Time"
    td = datetime.timedelta(milliseconds=ms)
    return str(td)[:-3]


def process_frame_worker(data):
    """
    Worker function executed in parallel across CPU cores.
    Isolates weapon pixels (RGB 66-82), checks density, and hashes weapon mask.
    """
    frame_idx, timestamp_ms, cropped_frame = data

    # 1. Create binary mask isolating weapon pixels (RGB 66-82)
    weapon_mask = cv2.inRange(cropped_frame, LOWER_RGB, UPPER_RGB)

    # 2. Check if at least 10% of pixels in the sub-box belong to the weapon
    sub_box_mask = weapon_mask[SUB_REL_Y1:SUB_REL_Y2, SUB_REL_X1:SUB_REL_X2]
    weapon_pixel_ratio = (sub_box_mask > 0).mean()

    if weapon_pixel_ratio < 0.10:
        return frame_idx, timestamp_ms, cropped_frame, None, False

    # 3. Compute perceptual hash ONLY on the weapon mask (background ignored)
    pil_mask = Image.fromarray(weapon_mask)
    weapon_hash = imagehash.dhash(pil_mask)

    return frame_idx, timestamp_ms, cropped_frame, weapon_hash, True


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

    cores = multiprocessing.cpu_count()
    print(f"Processing video using {cores} CPU cores...")

    with ProcessPoolExecutor(max_workers=cores) as executor:
        while True:
            batch = []

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

            # Process batch in parallel
            for result in executor.map(process_frame_worker, batch):
                f_idx, ts_ms, cropped_frame, weapon_hash, valid_weapon = result

                if not valid_weapon:
                    continue

                # Deduplicate based solely on weapon mask similarity
                if last_saved_hash is not None:
                    hash_diff = weapon_hash - last_saved_hash
                    if hash_diff <= hash_threshold:
                        continue

                # Add black padding footer for timeline
                padded_frame = cv2.copyMakeBorder(
                    cropped_frame, 0, PADDING_HEIGHT, 0, 0,
                    borderType=cv2.BORDER_CONSTANT, value=[0, 0, 0]
                )

                time_str = format_timestamp(ts_ms)
                cv2.putText(
                    padded_frame, time_str, (8, cropped_frame.shape[0] + 19),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA
                )

                saved_count += 1
                output_filename = os.path.join(output_dir, f"frame_{saved_count:05d}.jpg")
                
                # Save with maximum JPEG quality (100)
                cv2.imwrite(output_filename, padded_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
                last_saved_hash = weapon_hash

            print(f"Processed {frame_count} frames... (Saved {saved_count} unique weapon frames)")

    cap.release()
    print(f"\nDone! Processed {frame_count} frames. Saved {saved_count} unique weapon crops to '{output_dir}'.")


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