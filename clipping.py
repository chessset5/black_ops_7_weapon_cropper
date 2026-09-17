import os
import cv2
from PIL import Image
import imagehash
from pathlib import Path

# Configuration
HASH_THRESHOLD = 4  # Lower = stricter matching, higher = looser matching


def extract_and_deduplicate(output_dir, video_path, hash_threshold=4):
    if not os.path.exists(video_path):
        print(f"Error: Video file '{video_path}' not found.")
        return

    # Set up output directory under 'images/' relative to video directory
    video_dir = os.path.dirname(os.path.abspath(video_path))
    # output_dir = os.path.join(video_dir, "images")
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    frame_count = 0
    saved_count = 0
    last_saved_hash = None

    print("Processing video frames...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Convert OpenCV BGR frame to PIL Image for imagehash
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)

        # Compute difference hash (dhash)
        current_hash = imagehash.dhash(pil_img)

        # Check if current frame is a duplicate of the last saved frame
        if last_saved_hash is not None:
            hash_diff = current_hash - last_saved_hash
            if hash_diff <= hash_threshold:
                # Skip duplicate frame
                continue

        # Save frame sequentially to maintain chronological order
        saved_count += 1
        output_filename = os.path.join(output_dir, f"frame_{saved_count:05d}.jpg")
        cv2.imwrite(output_filename, frame)

        # Update the hash of the last unique frame saved
        last_saved_hash = current_hash

    cap.release()
    print(f"Done! Processed {frame_count} total frames.")
    print(f"Saved {saved_count} unique frames to '{output_dir}'.")


if __name__ == "__main__":
    video = Path(
        r"C:\Program Files (x86)\Steam\userdata\279248004\gamerecordings\video\bg_1938090_20260917_000457\session.mpd"
    )
    ws: Path = Path(__file__).parent
    extract_and_deduplicate(
        output_dir=ws / "images",
        video_path=video,
        hash_threshold=HASH_THRESHOLD,
    )
