import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from app.utils.logger import logger
from app.utils.db_connection import with_db_connection
from .camera_manager import CameraManager, CameraInfo
from .patrol_point_manager import PatrolPointManager, PatrolPoint
from .guard_manager import GuardManager, GuardInfo

class PatrolDetector:
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.camera_manager = CameraManager()
        self.point_manager = PatrolPointManager()
        self.guard_manager = GuardManager()
        
        # 加载摄像头信息
        self.camera = self.camera_manager.get_camera(camera_id)
        if not self.camera:
            raise ValueError(f"未找到摄像头配置: {camera_id}")
            
        # 加载巡逻点位
        self.patrol_points = self.point_manager.get_points_by_camera(camera_id)
        if not self.patrol_points:
            logger.warning(f"摄像头 {camera_id} 未配置巡逻点位")

    def detect_frame(self, frame: np.ndarray) -> List[Tuple[PatrolPoint, GuardInfo]]:
        """检测一帧图像中的巡逻情况"""
        try:
            # 检测人脸
            faces = self.guard_manager.face_recognizer.detect_faces(frame)
            if not faces:
                return []

            results = []
            for face_img, face_encoding in faces:
                # 识别保安身份
                guard = self._identify_guard(face_encoding)
                if not guard:
                    continue

                # 获取人脸中心点坐标
                face_center = self._get_face_center(face_img)
                
                # 检查是否在巡逻点位
                for point in self.patrol_points:
                    if self._is_in_patrol_point(face_center, point):
                        # 记录巡逻记录
                        self.point_manager.add_patrol_record(guard.guard_id, point.point_id)
                        results.append((point, guard))

            return results
            
        except Exception as e:
            logger.error(f"巡逻检测失败: {str(e)}")
            return []

    @with_db_connection
    def _identify_guard(self, face_encoding: np.ndarray, conn=None) -> Optional[GuardInfo]:
        """识别保安身份"""
        try:
            # 获取所有在职保安
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT * FROM guards 
                WHERE data_status = 1
            """
            cursor.execute(sql)
            
            max_similarity = 0
            matched_guard = None
            
            for row in cursor.fetchall():
                # 转换特征向量
                guard_feature = np.frombuffer(row['face_feature'], dtype=np.float64)
                
                # 计算相似度
                similarity = self.guard_manager.face_recognizer.compare_faces(
                    face_encoding, guard_feature
                )
                
                # 更新最佳匹配
                if similarity > max_similarity:
                    max_similarity = similarity
                    if similarity >= self.guard_manager.face_recognizer.min_confidence:
                        # 转换图片数据
                        face_image = None
                        if row['face_image']:
                            nparr = np.frombuffer(row['face_image'], np.uint8)
                            face_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        matched_guard = GuardInfo(
                            guard_id=row['guard_id'],
                            name=row['name'],
                            gender=row['gender'],
                            phone=row['phone'],
                            face_image=face_image,
                            face_feature=guard_feature,
                            register_time=row['register_time']
                        )
            
            if matched_guard:
                logger.info(f"识别到保安: {matched_guard.name} (相似度: {max_similarity:.2f})")
            
            return matched_guard
            
        except Exception as e:
            logger.error(f"保安身份识别失败: {str(e)}")
            return None

    def _get_face_center(self, face_img: np.ndarray) -> Tuple[int, int]:
        """获取人脸中心点坐标"""
        height, width = face_img.shape[:2]
        return (width // 2, height // 2)

    def _is_in_patrol_point(self, position: Tuple[int, int], point: PatrolPoint) -> bool:
        """检查位置是否在巡逻点位范围内"""
        x, y = position
        distance = np.sqrt((x - point.coord_x) ** 2 + (y - point.coord_y) ** 2)
        return distance <= point.radius

    def draw_patrol_points(self, frame: np.ndarray) -> np.ndarray:
        """在图像上绘制巡逻点位"""
        result = frame.copy()
        for point in self.patrol_points:
            # 绘制圆圈表示巡逻范围
            cv2.circle(result, (point.coord_x, point.coord_y), point.radius, (0, 255, 0), 2)
            # 绘制点位名称
            cv2.putText(result, point.name, (point.coord_x - 20, point.coord_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return result 