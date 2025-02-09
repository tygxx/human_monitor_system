import os
import json
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

from app.utils.logger import logger
from app.config.settings import GUARD_DATA_DIR
from app.utils.db_utils import with_db_connection
from .face_recognition import FaceRecognizer

@dataclass
class GuardInfo:
    """保安基本信息"""
    guard_id: str
    name: str
    gender: Optional[str] = None
    phone: Optional[str] = None
    face_image: Optional[np.ndarray] = None
    face_feature: Optional[np.ndarray] = None
    register_time: Optional[datetime] = None

class GuardManager:
    def __init__(self):
        self.face_recognizer = FaceRecognizer()

    @with_db_connection
    def register_guard(self, name: str, face_image: np.ndarray, 
                      gender: Optional[str] = None, phone: Optional[str] = None, 
                      conn = None) -> str:
        """注册新保安"""
        try:
            # 提取人脸特征向量
            face_feature = self.face_recognizer.extract_face_embedding(face_image)
            if face_feature is None:
                raise ValueError("未能提取到有效的人脸特征")

            # 生成保安ID
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM guards")
            count = cursor.fetchone()[0]
            guard_id = f"G{count + 1:03d}"

            # 准备图片和特征数据
            _, img_encoded = cv2.imencode('.jpg', face_image)
            img_bytes = img_encoded.tobytes()
            feature_bytes = face_feature.tobytes()

            # 插入数据库
            sql = """
                INSERT INTO guards (guard_id, name, gender, phone, face_image, face_feature)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (guard_id, name, gender, phone, img_bytes, feature_bytes))
            conn.commit()
            
            logger.info(f"成功注册保安: {name} (ID: {guard_id})")
            return guard_id
            
        except Exception as e:
            logger.error(f"注册保安失败: {str(e)}")
            raise

    @with_db_connection
    def get_guard(self, guard_id: str, conn = None) -> Optional[GuardInfo]:
        """获取保安信息"""
        try:
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT * FROM guards 
                WHERE guard_id = %s AND data_status = 1
            """
            cursor.execute(sql, (guard_id,))
            data = cursor.fetchone()
            
            if not data:
                return None

            # 转换图片和特征数据
            face_image = None
            if data['face_image']:
                nparr = np.frombuffer(data['face_image'], np.uint8)
                face_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            face_feature = None
            if data['face_feature']:
                face_feature = np.frombuffer(data['face_feature'], dtype=np.float64)

            return GuardInfo(
                guard_id=data['guard_id'],
                name=data['name'],
                gender=data['gender'],
                phone=data['phone'],
                face_image=face_image,
                face_feature=face_feature,
                register_time=data['register_time']
            )
            
        except Exception as e:
            logger.error(f"获取保安信息失败: {str(e)}")
            return None

    def _load_guards(self):
        """加载所有保安信息"""
        try:
            if not os.path.exists(GUARD_DATA_DIR):
                os.makedirs(GUARD_DATA_DIR)
                return

            for guard_file in Path(GUARD_DATA_DIR).glob("*.json"):
                with open(guard_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 加载人脸特征向量
                    embeddings = []
                    for emb_file in Path(GUARD_DATA_DIR).glob(f"{data['guard_id']}_*.npy"):
                        embedding = np.load(emb_file)
                        embeddings.append(embedding)
                    
                    guard = GuardInfo(
                        guard_id=data['guard_id'],
                        name=data['name'],
                        face_feature=data['face_feature'],
                        register_time=datetime.fromisoformat(data['register_time']),
                        gender=data['gender'],
                        phone=data['phone']
                    )
                    self.guards[guard.guard_id] = guard
                    
            logger.info(f"成功加载 {len(self.guards)} 个保安信息")
        except Exception as e:
            logger.error(f"加载保安信息失败: {str(e)}")

    def _save_guard_info(self, guard: GuardInfo):
        """保存保安信息到文件"""
        data = {
            'guard_id': guard.guard_id,
            'name': guard.name,
            'gender': guard.gender,
            'phone': guard.phone,
            'register_time': guard.register_time.isoformat()
        }
        
        filename = os.path.join(GUARD_DATA_DIR, f"{guard.guard_id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def update_guard_status(self, guard_id: str, status: str):
        """更新保安状态"""
        if guard_id in self.guards:
            self.guards[guard_id].status = status
            self._save_guard_info(self.guards[guard_id])
            logger.info(f"更新保安 {guard_id} 状态为: {status}") 