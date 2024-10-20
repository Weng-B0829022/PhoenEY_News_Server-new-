import json
import os
from queue import Queue
from threading import Thread
from django.conf import settings

class StoryboardManager:
    def __init__(self, file_path, random_id, initial_storyboard=None):
        self.file_path = os.path.join(settings.BASE_DIR, file_path, 'story_board.json')
        print(self.file_path)
        
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        if initial_storyboard is None:
            initial_storyboard = {}
        
        # 修改 initial_storyboard，確保只有前兩個段落的 needAvatar 為 True
        if "storyboard" in initial_storyboard:
            for i, paragraph in enumerate(initial_storyboard["storyboard"]):
                paragraph["needAvatar"] = i < 2  # True for first two paragraphs, False for others
        
        self.storyboard = initial_storyboard or self.load_storyboard()
        self.storyboard['random_id'] = random_id
        print(self.storyboard)
        
        if not isinstance(self.storyboard, dict) or "storyboard" not in self.storyboard:
            self.storyboard = {"title": "", "storyboard": [], "random_id": random_id}
        
        self.save_storyboard()
        
        self.queue = Queue()
        self.thread = Thread(target=self._process_queue)
        self.thread.daemon = True
        self.thread.start()

    def load_storyboard(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                if isinstance(data, dict) and "storyboard" in data:
                    # 確保載入的 storyboard 也遵循 needAvatar 規則
                    for i, paragraph in enumerate(data["storyboard"]):
                        paragraph["needAvatar"] = i < 2
                    return data
                else:
                    print(f"Warning: Loaded data is not in the correct format. Resetting to empty storyboard.")
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in {self.file_path}. Resetting to empty storyboard.")
        return {"title": "", "storyboard": []}

    def save_storyboard(self):
        if not isinstance(self.storyboard, dict) or "storyboard" not in self.storyboard:
            print(f"Error: storyboard is not in the correct format. Not saving.")
            return
        try:
            with open(self.file_path, 'w', encoding='utf-8') as file:
                json.dump(self.storyboard, file, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving storyboard: {str(e)}")

    def _process_queue(self):
        while True:
            action, args = self.queue.get()
            if action == "update_paragraph":
                self._update_paragraph(*args)
            elif action == "add_audio_path":
                self._add_audio_path(*args)
            elif action == "add_video":
                self._add_video(*args)
            self.queue.task_done()

    def update_paragraph(self, paragraph_index, new_data):
        self.queue.put(("update_paragraph", (paragraph_index, new_data)))

    def add_audio_path(self, paragraph_index, audio_path):
        self.queue.put(("add_audio_path", (paragraph_index, audio_path)))

    def add_video(self, paragraph_index, video):
        self.queue.put(("add_video", (paragraph_index, video)))

    def _update_paragraph(self, paragraph_index, new_data):
        if not isinstance(self.storyboard, dict) or "storyboard" not in self.storyboard:
            print("Error: storyboard is not in the correct format")
            return
        if paragraph_index < len(self.storyboard["storyboard"]):
            self.storyboard["storyboard"][paragraph_index].update(new_data)
        else:
            new_paragraph = {
                "paragraph": f"{paragraph_index + 1:02d}",
                "duration": "",
                "calculatedDuration": 0,
                "imageDescription": "",
                "voiceover": "",
                "characterCount": 0,
                "needAvatar": paragraph_index < 2  # True for first two paragraphs, False for others
            }
            new_paragraph.update(new_data)
            self.storyboard["storyboard"].append(new_paragraph)
        
        # 確保 needAvatar 規則始終被遵守
        self.storyboard["storyboard"][paragraph_index]["needAvatar"] = paragraph_index < 2
        
        self.save_storyboard()

    def _add_audio_path(self, paragraph_index, audio_path):
        if not isinstance(self.storyboard, dict) or "storyboard" not in self.storyboard:
            print("Error: storyboard is not in the correct format")
            return
        if paragraph_index < len(self.storyboard["storyboard"]):
            self.storyboard["storyboard"][paragraph_index]["audio_path"] = audio_path
            self.save_storyboard()

    def _add_video(self, paragraph_index, video):
        if not isinstance(self.storyboard, dict) or "storyboard" not in self.storyboard:
            print("Error: storyboard is not in the correct format")
            return
        if paragraph_index < len(self.storyboard["storyboard"]):
            self.storyboard["storyboard"][paragraph_index]["video"] = video
            self.save_storyboard()

    def set_image_config(self, img_path, top_left, top_right, bottom_right, bottom_left, z_index=-1):
        self.img_config =  {
            "img_path": img_path,
            "top_left": top_left,
            "top_right": top_right,
            "bottom_right": bottom_right,
            "bottom_left": bottom_left,
            "z_index": z_index
        }
    def add_config_to_all_paragraphs(self):
        if not self.img_config:
            print("Error: Background configuration not set. Use set_background_config() first.")
            return
        for paragraph in self.storyboard["storyboard"]:
            if "images" not in paragraph:
                paragraph["images"] = []

            # 檢查是否已有圖片，並添加背景到最後而不覆蓋
            paragraph["images"].insert(0, self.img_config)

        self.save_storyboard()

    def get_storyboard(self):
        return self.storyboard

    def wait_for_queue(self):
        self.queue.join()
