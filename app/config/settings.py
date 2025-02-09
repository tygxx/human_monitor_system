import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 数据目录
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(DATA_DIR, 'models')
SAMPLES_DIR = os.path.join(DATA_DIR, 'samples')

# 日志配置
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# 视频处理配置
VIDEO_CONFIG = {
    'frame_rate': 30,
    'resolution': (640, 480)
}

# 人脸检测配置
FACE_DETECTION_CONFIG = {
    'min_detection_confidence': 0.5,
    'model_path': os.path.join(MODELS_DIR, 'face_detection_model.pth')
}

# 动作识别配置
ACTION_RECOGNITION_CONFIG = {
    'min_detection_confidence': 0.5,
    'model_path': os.path.join(MODELS_DIR, 'action_recognition_model.pth')
}

# 测试视频配置
TEST_VIDEO_CONFIG = {
    'CAM_1F_GATE': {
        'video_path': os.path.join(BASE_DIR, 'data', 'test_videos', 'gate_patrol.mp4'),
        'fps': 30,
        'resolution': (1099, 844)
    },
    'CAM_1F_WEST': {
        'video_path': os.path.join(BASE_DIR, 'data', 'test_videos', 'west_patrol.mp4'),
        'fps': 30,
        'resolution': (855, 1452)
    }
}

# 保安数据存储目录
GUARD_DATA_DIR = os.path.join(DATA_DIR, 'guards')

# 人脸识别配置
FACE_RECOGNITION_CONFIG = {
    'min_face_size': 64,
    'min_confidence': 0.8,
    'face_recognition_model': os.path.join(MODELS_DIR, 'face_recognition_model.pth'),
    'face_detection_model': os.path.join(MODELS_DIR, 'face_detection_model.pth'),
    'embedding_size': 512,
    'max_face_distance': 0.6  # 人脸匹配阈值
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