import os
import cv2
import datetime
from PIL import Image
import imagehash
from pathlib import Path

# Configuration
HASH_THRESHOLD = 4  # Lower = stricter matching, higher = looser matching

# Crop Coordinates (Top Left: 1582, 873 | Bottom Right: 1755, 1083)
# Note: Using 1083 instead of 1038 to ensure the bounding box covers the largest Y axis requested
CROP_Y1 = 873
CROP_Y2 = 1038
CROP_X1 = 1582
CROP_X2 = 1755


def format_timestamp(ms):
    """Converts milliseconds into a readable HH:MM:SS.mmm string."""
    if ms < 0:
        return "Unknown Time"
    td = datetime.timedelta(milliseconds=ms)
    # Format to keep it concise and include milliseconds
    return str(td)[:-3]


def extract_and_deduplicate(output_dir, video_path, hash_threshold=4):
    if not os.path.exists(video_path):
        print(f"Error: Video file '{video_path}' not found.")
        return

    os.makedirs(output_dir, exist_ok=True)

    os.chdir(os.path.dirname(video_path))

    # OpenCV will use FFmpeg backend to read the session.mpd and parse the .m4s chunks
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print("Error: Could not open video/mpd stream.")
        return

    frame_count = 0
    saved_count = 0
    last_saved_hash = None

    print("Processing video frames and cropping...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # 1. Crop the frame to the specified bottom-left coordinates
        # OpenCV frames are numpy arrays indexed via [y1:y2, x1:x2]
        cropped_frame = frame[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2]

        # 2. Convert cropped OpenCV BGR frame to PIL Image for imagehash
        rgb_crop = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_crop)

        # 3. Compute difference hash (dhash) on the CROP only
        current_hash = imagehash.dhash(pil_img)

        # 4. Check if current cropped frame is a duplicate
        if last_saved_hash is not None:
            hash_diff = current_hash - last_saved_hash
            if hash_diff <= hash_threshold:
                # Skip duplicate frame
                continue

        # 5. Get the timestamp from the video stream
        timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        time_str = format_timestamp(timestamp_ms)

        # 6. Overlay the timestamp onto the cropped image
        # Positioned at the bottom left of the crop
        text_position = (5, cropped_frame.shape[0] - 10)
        cv2.putText(
            cropped_frame,
            time_str,
            text_position,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,  # Font scale
            (0, 255, 0),  # Color (Green)
            1,  # Thickness
            cv2.LINE_AA,
        )

        # 7. Save frame sequentially to maintain chronological order
        saved_count += 1
        output_filename = os.path.join(output_dir, f"frame_{saved_count:05d}.jpg")
        cv2.imwrite(output_filename, cropped_frame)

        # Update the hash of the last unique frame saved
        last_saved_hash = current_hash

    cap.release()
    print(f"Done! Processed {frame_count} total frames.")
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
