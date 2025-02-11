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
    # 最小人脸尺寸（像素）
    # - 检测到的人脸区域如果小于这个尺寸会被过滤掉
    # - 用于过滤远处或模糊的人脸，提高识别准确性
    'min_face_size': 64,
    
    # 人脸匹配的最小置信度阈值（范围 0-1）
    # - 人脸特征相似度需要大于这个值才会被认为是同一个人
    # - 值越大匹配要求越严格，但可能增加漏检的概率
    # - 建议范围：0.7-0.9
    'min_confidence': 0.8,
    
    # 人脸识别模型文件路径
    # - 用于提取人脸特征向量的深度学习模型
    'face_recognition_model': os.path.join(MODELS_DIR, 'face_recognition_model.pth'),
    
    # 人脸检测模型文件路径
    # - 用于定位图像中的人脸位置
    'face_detection_model': os.path.join(MODELS_DIR, 'face_detection_model.pth'),
    
    # 人脸特征向量的维度
    # - 用于存储人脸的特征表示
    # - 该维度由模型结构决定，通常为128或512
    'embedding_size': 512,
    
    # 人脸匹配的最大距离阈值
    # - 两个人脸特征向量之间的欧氏距离阈值
    # - 距离小于此值时认为是同一个人
    # - 与 min_confidence 相反，值越小要求越严格
    # - 建议范围：0.4-0.7
    'max_face_distance': 0.6
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