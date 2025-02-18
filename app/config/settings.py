import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 数据目录
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(DATA_DIR, 'models')

# 日志配置
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# 人脸检测配置
FACE_DETECTION_CONFIG = {
    'min_detection_confidence': 0.5,
    'model_path': os.path.join(MODELS_DIR, 'face_detection_model.pth')
}


# 巡逻点位配置
PATROL_POINT_CONFIG = {
    'default_radius': 100,  # 默认巡逻点位半径
    'min_radius': 20,      # 最小半径
    'max_radius': 400      # 最大半径
}

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Ty123!@#",
    "database": "mall_monitor",
    "pool_name": "mall_monitor_pool",
    "pool_size": 5
}

# Face Recognition Settings
FACE_RECOGNITION_SETTINGS = {
    'face_match_tolerance': 0.8,  # 人脸匹配阈值，越小越严格
    'frame_process_interval': 1,   # 处理帧的间隔（秒）
    'recognition_cooldown': 300,   # 同一保安重新识别的冷却时间（秒）
    'min_face_size': 20,          # 最小人脸尺寸（像素）
    'display_font_scale': 0.5,    # 显示文字大小
    'display_font_thickness': 2,   # 显示文字粗细
    'face_box_color': (0, 255, 0),  # 已识别保安的人脸框颜色 (BGR)
    'unknown_face_box_color': (0, 0, 255),  # 未匹配人脸的框颜色 (BGR)
    'face_box_thickness': 2,      # 人脸框粗细
} 