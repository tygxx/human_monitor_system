import cv2
import numpy as np
import face_recognition
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from app.utils.logger import logger
from app.utils.exceptions import FaceDetectionError
from app.utils.db_utils import execute_update

class GuardRegistration:
    def __init__(self):
        self.face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    def register_from_camera(self, guard_id: str, name: str, gender: str, phone: str) -> bool:
        """从摄像头录入保安信息"""
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise FaceDetectionError("无法打开摄像头")

            while True:
                ret, frame = cap.read()
                if not ret:
                    continue

                # 显示预览窗口
                preview_frame = frame.copy()
                faces = self.face_detector.detectMultiScale(frame, 1.3, 5)
                
                for (x, y, w, h) in faces:
                    cv2.rectangle(preview_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                cv2.imshow('Face Registration', preview_frame)
                key = cv2.waitKey(1)

                # 按空格保存照片
                if key == 32 and len(faces) == 1:  # 32是空格键的ASCII码
                    face_image = frame
                    face_feature = self._extract_face_feature(frame)
                    if face_feature is not None:
                        success = self._save_guard_info(
                            guard_id, name, gender, phone, face_image, face_feature
                        )
                        cap.release()
                        cv2.destroyAllWindows()
                        return success
                
                # 按ESC取消
                elif key == 27:  # 27是ESC键的ASCII码
                    break

            cap.release()
            cv2.destroyAllWindows()
            return False
            
        except Exception as e:
            logger.error(f"摄像头录入失败: {str(e)}")
            return False

    def register_from_image(self, guard_id: str, name: str, gender: str, 
                          phone: str, image_path: str) -> bool:
        """从照片录入保安信息"""
        try:
            # 读取图片
            image = cv2.imread(image_path)
            if image is None:
                raise FaceDetectionError(f"无法读取图片: {image_path}")

            # 提取人脸特征
            face_feature = self._extract_face_feature(image)
            if face_feature is None:
                raise FaceDetectionError("未检测到人脸或人脸特征提取失败")

            # 保存信息
            return self._save_guard_info(
                guard_id, name, gender, phone, image, face_feature
            )

        except Exception as e:
            logger.error(f"照片录入失败: {str(e)}")
            return False

    def _extract_face_feature(self, image: np.ndarray) -> Optional[np.ndarray]:
        """提取人脸特征向量"""
        try:
            # 转换为RGB格式（face_recognition库需要）
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 检测人脸位置
            face_locations = face_recognition.face_locations(rgb_image)
            if not face_locations or len(face_locations) != 1:
                return None
            
            # 提取人脸特征
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            if not face_encodings:
                return None
                
            return face_encodings[0]

        except Exception as e:
            logger.error(f"人脸特征提取失败: {str(e)}")
            return None

    def _save_guard_info(self, guard_id: str, name: str, gender: str, 
                        phone: str, face_image: np.ndarray, 
                        face_feature: np.ndarray) -> bool:
        """保存保安信息到数据库"""
        try:
            # 将图片和特征向量转换为二进制
            _, img_encoded = cv2.imencode('.jpg', face_image)
            img_bytes = img_encoded.tobytes()
            feature_bytes = face_feature.tobytes()

            # 构建SQL语句
            sql = """
                INSERT INTO guards (guard_id, name, gender, phone, face_image, 
                                  face_feature, register_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                guard_id, name, gender, phone, img_bytes, 
                feature_bytes, datetime.now()
            )

            # 执行插入
            execute_update(sql, params)
            logger.info(f"成功录入保安信息: {name} (ID: {guard_id})")
            return True

        except Exception as e:
            logger.error(f"保存保安信息失败: {str(e)}")
            return False 