import cv2
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, ImageClip
from moviepy.editor import concatenate_videoclips
import os
from django.conf import settings

def combine_videos(output_dir, num_paragraphs):
    """
    Combines multiple video clips into a single video file.
    
    :param output_dir: Directory containing the input video files and where the output will be saved
    :param num_paragraphs: Number of video clips to combine
    """
    video_clips = []
    for i in range(1, num_paragraphs + 1):
        video_path = os.path.join(output_dir, f"final_output_paragraph_{i}.mp4")
        video = VideoFileClip(video_path)
        # Check if the video has audio
        if video.audio is None:
            print(f"Warning: Video {i} does not have audio.")
        video_clips.append(video)
    
    # Concatenate all video clips
    final_video = concatenate_videoclips(video_clips)
    
    # Ensure the final video has audio, create a silent track if necessary
    if final_video.audio is None:
        print("Warning: The combined video does not have audio. Creating a silent audio track.")
        final_video = final_video.set_audio(CompositeAudioClip([]))
    
    final_output_path = os.path.join(output_dir, "final_combined_video.mp4")
    # Write the final video to file
    final_video.write_videofile(final_output_path, codec="libx264", audio_codec="aac")
    
    # Close all video clips to free up resources
    for clip in video_clips:
        clip.close()
    
    print(f"All videos combined into: {final_output_path}")

def compose_background_with_scenes(output_dir, images):
    """
    Composes multiple images based on their z-index and coordinates.
    
    :param output_dir: Directory containing the image files
    :param images: List of image dictionaries containing path and coordinate information
    :return: Composed image or None if an error occurs
    """
    # Initialize a blank canvas (assuming 1024x1024 as the base size)
    canvas = np.zeros((1024, 1024, 4), dtype=np.uint8)
    
    # Sort images by z-index (lowest to highest)
    sorted_images = sorted(images, key=lambda x: x.get('z_index', 0))
    
    for img_info in sorted_images:
        img_path = os.path.join(output_dir, img_info["img_path"])
        
        # Read image
        with open(img_path, 'rb') as f:
            img_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
            img = cv2.imdecode(img_bytes, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"Error: Could not read image: {img_path}")
            continue
        
        # Convert to RGBA if necessary
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
        
        # Get coordinates
        top_left = img_info["top-left"]
        bottom_right = img_info["bottom-right"]
        width = bottom_right[0] - top_left[0]
        height = bottom_right[1] - top_left[1]
        
        # Resize image if necessary
        if img.shape[:2] != (height, width):
            img = cv2.resize(img, (width, height))
        
        # Create a mask for the image
        mask = img[:,:,3] / 255.0
        mask = np.dstack([mask]*3)
        
        # Blend the image onto the canvas
        canvas_section = canvas[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0], :3]
        img_rgb = img[:,:,:3]
        canvas[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0], :3] = \
            img_rgb * mask + canvas_section * (1 - mask)
        
        # Update alpha channel
        canvas[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0], 3] = \
            np.maximum(canvas[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0], 3], img[:,:,3])
    
    return cv2.cvtColor(canvas, cv2.COLOR_RGBA2RGB)

def replace_background(input_video, output_video, threshold, composed_background, crop_coords, placement_coords):
    """
    Replaces the background of a video with a composed background image.
    
    :param input_video: Path to the input video file
    :param output_video: Path to save the output video file
    :param threshold: Threshold for background removal
    :param composed_background: Composed background image
    :param crop_coords: Coordinates for cropping the input video
    :param placement_coords: Coordinates for placing the video on the background
    """
    cap = cv2.VideoCapture(input_video)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    x, y, w, h = crop_coords
    bg_height, bg_width = composed_background.shape[:2]
    px, py = placement_coords
    
    # Set up video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    temp_output = os.path.join(os.path.dirname(output_video), f'temp_{os.path.basename(output_video)}')
    out = cv2.VideoWriter(temp_output, fourcc, fps, (bg_width, bg_height), isColor=True)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process each frame
        frame = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        mask = np.where(gray < threshold, 0, 255).astype('uint8')
        blurred_mask = cv2.GaussianBlur(mask, (21, 21), 0).astype(float) / 255.0
        
        foreground = frame * blurred_mask[:,:,np.newaxis]
        bg_copy = composed_background.copy()
        
        # Blend foreground with background
        py_end, px_end = min(py + h, bg_height), min(px + w, bg_width)
        blend_h, blend_w = py_end - py, px_end - px
        
        alpha = 1 - blurred_mask[:blend_h, :blend_w, np.newaxis]
        bg_section = bg_copy[py:py_end, px:px_end]
        blended = bg_section * alpha + foreground[:blend_h, :blend_w]
        bg_copy[py:py_end, px:px_end] = blended
        
        out.write(cv2.cvtColor(bg_copy, cv2.COLOR_RGB2BGR))
    
    cap.release()
    out.release()
    
    # Add original audio to the processed video
    video = VideoFileClip(temp_output)
    audio = AudioFileClip(input_video)
    final_video = video.set_audio(audio)
    final_video.write_videofile(output_video, codec="libx264", audio_codec="aac")
    
    video.close()
    audio.close()
    os.remove(temp_output)



def create_videos_from_images_and_audio(manager):
    """
    Creates videos by combining background images, scene images, and audio (with or without avatar videos).
    
    :param manager: Manager object containing the storyboard and other necessary information
    """
    storyboard = manager.get_storyboard()
    output_dir = os.path.join(settings.BASE_DIR, 'generated', storyboard['random_id'])
    
    for idx, paragraph in enumerate(storyboard["storyboard"]):
        print(f"Processing paragraph {idx + 1}...")
        
        # Compose background with all images
        composed_background = compose_background_with_scenes(output_dir, paragraph["images"])
        if composed_background is None:
            print(f"Error: Failed to compose background for paragraph {idx + 1}")
            continue
        
        # Check if avatar is needed
        if paragraph.get("needAvatar", False):
            # Process video with avatar
            input_video = os.path.join(output_dir, paragraph["video"]["avatar_path"])
            output_video = os.path.join(output_dir, f"final_output_paragraph_{idx + 1}.mp4")
            crop_coords = (808, 147, 256, 883)
            placement_coords = (paragraph["video"]["x"], paragraph["video"]["y"])
            
            replace_background(input_video, output_video, 10, composed_background, crop_coords, placement_coords)
        else:
            # Create video from background image and audio
            output_video = os.path.join(output_dir, f"final_output_paragraph_{idx + 1}.mp4")
            audio_path = os.path.join(output_dir, paragraph["audio_path"])
            create_video_from_image_and_audio(composed_background, audio_path, output_video)
        
        print(f"Video processing complete for paragraph {idx + 1}")
    
    print("All videos processed successfully!")

    # Combine all videos into one final video
    num_paragraphs = len(storyboard["storyboard"])
    combine_videos(output_dir, num_paragraphs)
    
    print("Final combined video created successfully!")


# New function to create video from image and audio
def create_video_from_image_and_audio(image, audio_path, output_path, fps=24):
    """
    Creates a video from a static image and an audio file.
    
    :param image: The background image (numpy array)
    :param audio_path: Path to the audio file
    :param output_path: Path to save the output video
    :param fps: Frames per second for the output video (default is 24)
    """
    audio = AudioFileClip(audio_path)
    video = ImageClip(image).set_duration(audio.duration)
    video = video.set_audio(audio)
    video.fps = fps  # Set the fps for the video clip
    video.write_videofile(output_path, codec="libx264", audio_codec="aac")
    video.close()
    audio.close()

if __name__ == "__main__":
    create_videos_from_images_and_audio()
