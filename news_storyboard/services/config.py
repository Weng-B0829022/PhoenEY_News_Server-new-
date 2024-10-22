HALF_CONFIG = {
    # 定義圖片在影片各個 scene 中的坐標
    # 這些坐標用於定位圖片在影片中的位置
    "scene_place_coordinates": {
        "top_left": [685, 65],  # 圖片左上角的坐標
        "top_right": [1635, 65],  # 圖片右上角的坐標
        "bottom_right": [1635, 770],  # 圖片右下角的坐標
        "bottom_left": [685, 770],  # 圖片左下角的坐標
    },
    # 設定影片尺寸
    # 這是影片的寬度和高度
    "canvas_size": (1705, 959),
    # 欲裁減 avatar 位置的 x, y, w, h
    # 定義裁減 avatar 圖片的區域
    "crop_coords": (760, 110, 450, 485),# x, y, w, h
    # avatar 位置
    # 定義 avatar 圖片在影片中的位置
    "avatar_place_coordinates": {
        "top_left": [65, 65],  # avatar 左上角的坐標
        "top_right": [655, 65],  # avatar 右上角的坐標
        "bottom_right": [655, 770],  # avatar 右下角的坐標
        "bottom_left": [65, 770],  # avatar 左下角的坐標
    },
    # 設定背景圖片及其屬性
    "background": {
        "file": "background_half.jpg",  # 背景圖片文件名
        "top_left": [0, 0],  # 背景圖片的左上角坐標
        "top_right": [1705, 0],  # 背景圖片的右上角坐標
        "bottom_right": [1705, 959],  # 背景圖片的右下角坐標
        "bottom_left": [0, 959],  # 背景圖片的左下角坐標
        "z_index": -1,  # 背景圖片的 z_index，控制層次順序
    },
    # 設定標題圖片及其屬性
    "title": {
        "top_left": [130, 790],  # 標題圖片的左上角坐標
        "top_right": [930, 790],  # 標題圖片的右上角坐標
        "bottom_right": [930, 890],  # 標題圖片的右下角坐標
        "bottom_left": [130, 890],  # 標題圖片的左下角坐標
        "z_index": 100,  # 標題圖片的 z_index，控制層次順序
    }
}

FULL_CONFIG = {
    # 定義 full 配置
    # 這裡可以根據需要定義 FULL_CONFIG 的具體內容
    # 例如：
    "scene_place_coordinates": {
        "top_left": [111, 97],  # 圖片左上角的坐標
        "top_right": [1324, 183],  # 圖片右上角的坐標
        "bottom_right": [1324, 816],  # 圖片右下角的坐標
        "bottom_left": [111, 902],  # 圖片左下角的坐標
    },
    "canvas_size": (1920, 1080),  # 影片的寬度和高度
    "crop_coords": (760, 110, 450, 970),  # 定義裁減 avatar 圖片的區域 x, y, w, h
    "avatar_place_coordinates": {
        "top_left": [1420, 280],  # avatar 左上角的坐標
        "top_right": [1690, 280],  # avatar 右上角的坐標
        "bottom_right": [1690, 980],  # avatar 右下角的坐標
        "bottom_left": [1420, 980],  # avatar 左下角的坐標
    },
    "background": {
        "file": "background_full.jpg",  # 背景圖片文件名
        "top_left": [0, 0],  # 背景圖片的左上角坐標
        "top_right": [1920, 0],  # 背景圖片的右上角坐標
        "bottom_right": [1920, 1080],  # 背景圖片的右下角坐標
        "bottom_left": [0, 1080],  # 背景圖片的左下角坐標
        "z_index": -1,  # 背景圖片的 z_index，控制層次順序
    },
    "title": {
        "top_left": [230, 1000],  # 標題圖片的左上角坐標
        "top_right": [1240, 1000],  # 標題圖片的右上角坐標
        "bottom_right": [1240, 1080],  # 標題圖片的右下角坐標
        "bottom_left": [240, 1080],  # 標題圖片的左下角坐標
        "z_index": 100,  # 標題圖片的 z_index，控制層次順序
    }
}
