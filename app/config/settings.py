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

# 人脸识别配置
FACE_RECOGNITION_CONFIG = {
    'min_face_size': 64,
    'min_confidence': 0.8,
    'face_recognition_model': os.path.join(MODELS_DIR, 'face_recognition_model.pth'),
    'face_detection_model': os.path.join(MODELS_DIR, 'face_detection_model.pth'),
    'embedding_size': 512,
    'max_face_distance': 0.6  # 人脸匹配阈值
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