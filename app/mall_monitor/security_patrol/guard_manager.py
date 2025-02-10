import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from app.utils.logger import logger
from app.utils.db_utils import with_db_connection
from .face_recognition import FaceRecognizer

@dataclass
class GuardInfo:
    """保安信息"""
    guard_id: str
    name: str
    gender: str
    phone: str
    face_image: Optional[np.ndarray]
    face_feature: np.ndarray
    register_time: datetime

class GuardManager:
    def __init__(self):
        self.face_recognizer = FaceRecognizer()

    @with_db_connection
    def register_guard(self, name: str, gender: str, phone: str, 
                      face_image: np.ndarray, conn=None) -> Optional[str]:
        """注册新保安"""
        try:
            # 检测人脸并提取特征
            faces = self.face_recognizer.detect_faces(face_image)
            if not faces or len(faces) > 1:
                raise ValueError("图片中未检测到人脸或包含多个人脸")
            
            face_img, face_feature = faces[0]
            
            # 生成保安ID
            guard_id = f"G{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 编码图片数据
            _, img_encoded = cv2.imencode('.jpg', face_image)
            
            # 保存到数据库
            cursor = conn.cursor()
            sql = """
                INSERT INTO guards (guard_id, name, gender, phone, face_image, face_feature)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                guard_id,
                name,
                gender,
                phone,
                img_encoded.tobytes(),
                face_feature.tobytes()
            ))
            conn.commit()
            
            logger.info(f"成功注册保安: {name} (ID: {guard_id})")
            return guard_id
            
        except Exception as e:
            logger.error(f"注册保安失败: {str(e)}")
            return None

    @with_db_connection
    def get_guard(self, guard_id: str, conn=None) -> Optional[GuardInfo]:
        """获取保安信息"""
        try:
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT * FROM guards 
                WHERE guard_id = %s AND data_status = 1
            """
            cursor.execute(sql, (guard_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            # 转换图片数据
            face_image = None
            if row['face_image']:
                nparr = np.frombuffer(row['face_image'], np.uint8)
                face_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 转换特征向量
            face_feature = np.frombuffer(row['face_feature'], dtype=np.float64)
            
            return GuardInfo(
                guard_id=row['guard_id'],
                name=row['name'],
                gender=row['gender'],
                phone=row['phone'],
                face_image=face_image,
                face_feature=face_feature,
                register_time=row['register_time']
            )
            
        except Exception as e:
            logger.error(f"获取保安信息失败: {str(e)}")
            return None

    @with_db_connection
    def list_guards(self, conn=None) -> List[GuardInfo]:
        """获取所有在职保安列表"""
        try:
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT * FROM guards 
                WHERE data_status = 1
                ORDER BY register_time DESC
            """
            cursor.execute(sql)
            
            guards = []
            for row in cursor.fetchall():
                # 转换图片数据
                face_image = None
                if row['face_image']:
                    nparr = np.frombuffer(row['face_image'], np.uint8)
                    face_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # 转换特征向量
                face_feature = np.frombuffer(row['face_feature'], dtype=np.float64)
                
                guards.append(GuardInfo(
                    guard_id=row['guard_id'],
                    name=row['name'],
                    gender=row['gender'],
                    phone=row['phone'],
                    face_image=face_image,
                    face_feature=face_feature,
                    register_time=row['register_time']
                ))
            
            return guards
            
        except Exception as e:
            logger.error(f"获取保安列表失败: {str(e)}")
            return []

    def update_guard_status(self, guard_id: str, status: str):
        """更新保安状态"""
        if guard_id in self.guards:
            self.guards[guard_id].status = status
            self._save_guard_info(self.guards[guard_id])
            logger.info(f"更新保安 {guard_id} 状态为: {status}") 