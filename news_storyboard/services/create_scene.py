import cv2
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip
import os
from django.conf import settings

def compose_background_with_scene(background_image, scene_image, scene_coords):
    with open(background_image, 'rb') as f:
        background_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
        background = cv2.imdecode(background_bytes, cv2.IMREAD_UNCHANGED)
    if background is None:
        print(f"Error: Could not read background image: {background_image}")
        return None
    background = cv2.cvtColor(background, cv2.COLOR_BGR2RGB)
    
    with open(scene_image, 'rb') as f:
        scene_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
        scene = cv2.imdecode(scene_bytes, cv2.IMREAD_UNCHANGED)
    if scene is None:
        print(f"Error: Could not read scene image: {scene_image}")
        return None
    
    scene = cv2.cvtColor(scene, cv2.COLOR_BGRA2RGBA if scene.shape[2] == 4 else cv2.COLOR_BGR2RGBA)
    
    top_left, top_right, bottom_right, bottom_left = scene_coords
    width = top_right[0] - top_left[0]
    height = bottom_left[1] - top_left[1]
    scene_resized = cv2.resize(scene, (width, height))
    
    for c in range(3):
        background[top_left[1]:bottom_left[1], top_left[0]:top_right[0], c] = (
            background[top_left[1]:bottom_left[1], top_left[0]:top_right[0], c] * (1 - scene_resized[:,:,3]/255.0) + 
            scene_resized[:,:,c] * (scene_resized[:,:,3]/255.0)
        )
    
    return background

def replace_background(input_video, output_video, threshold, composed_background, crop_coords, placement_coords):
    cap = cv2.VideoCapture(input_video)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    x, y, w, h = crop_coords
    bg_height, bg_width = composed_background.shape[:2]
    px, py = placement_coords
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    temp_output = os.path.join(os.path.dirname(output_video), f'temp_{os.path.basename(output_video)}')
    out = cv2.VideoWriter(temp_output, fourcc, fps, (bg_width, bg_height), isColor=True)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        mask = np.where(gray < threshold, 0, 255).astype('uint8')
        blurred_mask = cv2.GaussianBlur(mask, (21, 21), 0).astype(float) / 255.0
        
        foreground = frame * blurred_mask[:,:,np.newaxis]
        bg_copy = composed_background.copy()
        
        py_end, px_end = min(py + h, bg_height), min(px + w, bg_width)
        blend_h, blend_w = py_end - py, px_end - px
        
        alpha = 1 - blurred_mask[:blend_h, :blend_w, np.newaxis]
        bg_section = bg_copy[py:py_end, px:px_end]
        blended = bg_section * alpha + foreground[:blend_h, :blend_w]
        bg_copy[py:py_end, px:px_end] = blended
        
        out.write(cv2.cvtColor(bg_copy, cv2.COLOR_RGB2BGR))
    
    cap.release()
    out.release()
    
    video = VideoFileClip(temp_output)
    audio = AudioFileClip(input_video)
    final_video = video.set_audio(audio)
    final_video.write_videofile(output_video, codec="libx264", audio_codec="aac")
    
    video.close()
    audio.close()
    os.remove(temp_output)

def create_videos_from_images_and_audio(manager):
    storyboard = manager.get_storyboard()
    output_dir = os.path.join(settings.BASE_DIR, 'generated', storyboard['random_id'])
    
    for idx, paragraph in enumerate(storyboard["storyboard"]):
        print(f"Processing paragraph {idx + 1}...")
        
        background_image = os.path.join(output_dir, paragraph["images"][0]["img_path"])
        scene_image = os.path.join(output_dir, paragraph["images"][1]["img_path"])
        scene_coords = [
            paragraph["images"][1]["top-left"],
            paragraph["images"][1]["top-right"],
            paragraph["images"][1]["bottom-right"],
            paragraph["images"][1]["bottom-left"]
        ]
        
        composed_background = compose_background_with_scene(background_image, scene_image, scene_coords)
        if composed_background is None:
            print(f"Error: Failed to compose background for paragraph {idx + 1}")
            continue
        
        input_video = os.path.join(output_dir, paragraph["video"]["avatar_path"])
        output_video = os.path.join(output_dir, f"final_output_paragraph_{idx + 1}.mp4")
        crop_coords = (808, 147, 256, 883)
        placement_coords = (paragraph["video"]["x"], paragraph["video"]["y"])
        
        replace_background(input_video, output_video, 10, composed_background, crop_coords, placement_coords)
        
        print(f"Video processing complete for paragraph {idx + 1}")
    
    print("All videos processed successfully!")

if __name__ == "__main__":
    create_videos_from_images_and_audio()