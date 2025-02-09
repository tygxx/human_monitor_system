import cv2
import numpy as np
import face_recognition
from typing import List, Optional, Tuple

from app.utils.logger import logger
from app.config.settings import FACE_RECOGNITION_CONFIG

class FaceRecognizer:
    def __init__(self):
        self.min_face_size = FACE_RECOGNITION_CONFIG['min_face_size']
        self.min_confidence = FACE_RECOGNITION_CONFIG['min_confidence']
        logger.info("人脸识别模块初始化完成")

    def detect_faces(self, image: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray]]:
        """检测人脸并返回人脸图像和对应的特征向量"""
        try:
            # 转换为RGB格式（face_recognition需要）
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 检测人脸位置
            face_locations = face_recognition.face_locations(rgb_image)
            if not face_locations:
                return []
            
            results = []
            for face_location in face_locations:
                # 提取人脸区域
                top, right, bottom, left = face_location
                face_image = image[top:bottom, left:right]
                
                # 检查人脸大小
                if face_image.shape[0] < self.min_face_size or \
                   face_image.shape[1] < self.min_face_size:
                    continue
                
                # 提取人脸特征
                face_encoding = face_recognition.face_encodings(rgb_image, [face_location])[0]
                results.append((face_image, face_encoding))
            
            return results
            
        except Exception as e:
            logger.error(f"人脸检测失败: {str(e)}")
            return []

    def extract_face_embedding(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """从人脸图像中提取特征向量"""
        try:
            # 转换为RGB格式
            rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
            
            # 检测人脸位置
            face_locations = face_recognition.face_locations(rgb_image)
            if not face_locations:
                logger.warning("未检测到人脸")
                return None
            
            # 提取特征向量
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            if not face_encodings:
                logger.warning("无法提取人脸特征")
                return None
                
            return face_encodings[0]
            
        except Exception as e:
            logger.error(f"特征提取失败: {str(e)}")
            return None

    def compare_faces(self, face_embedding1: np.ndarray, 
                     face_embedding2: np.ndarray) -> float:
        """比较两个人脸特征向量的相似度"""
        try:
            # 使用face_recognition的内置函数计算距离
            distance = face_recognition.face_distance([face_embedding1], face_embedding2)[0]
            # 转换为相似度分数（距离越小，相似度越高）
            similarity = 1 - distance
            return float(similarity)
        except Exception as e:
            logger.error(f"人脸比对失败: {str(e)}")
            return 0.0 