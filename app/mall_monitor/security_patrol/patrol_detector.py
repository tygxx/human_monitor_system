import cv2
import numpy as np
import mediapipe as mp
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from app.utils.logger import logger
from app.utils.exceptions import FaceActionMonitorException
from .patrol_config import PatrolPoint, PatrolRoute, DETECTION_CONFIG, PATROL_POINTS
from .camera_manager import CameraManager, CameraInfo
from .patrol_point_manager import PatrolPointManager, PatrolPoint
from .guard_manager import GuardManager, GuardInfo
from app.utils.db_connection import with_db_connection

@dataclass
class SecurityGuard:
    """保安信息"""
    guard_id: str
    last_position: tuple
    last_seen: datetime
    current_route: Optional[str] = None
    visited_points: List[str] = None

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

    def detect_security_guards(self, frame: np.ndarray) -> List[SecurityGuard]:
        """检测画面中的保安"""
        try:
            # 转换颜色空间
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            detected_guards = []
            if results.pose_landmarks:
                # 获取人体中心点位置（使用臀部中心点作为位置参考）
                h, w, _ = frame.shape
                mid_hip = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_HIP]
                position = (int(mid_hip.x * w), int(mid_hip.y * h))

                # 创建或更新保安信息
                guard = SecurityGuard(
                    guard_id="G1",  # 简化版本，只跟踪一个保安
                    last_position=position,
                    last_seen=datetime.now(),
                    visited_points=[]
                )
                detected_guards.append(guard)

                # 在画面中绘制骨架（调试用）
                self.mp_drawing.draw_landmarks(
                    frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

            return detected_guards
        except Exception as e:
            logger.error(f"保安检测失败: {str(e)}")
            return []

    def check_patrol_point(self, guard: SecurityGuard, point: PatrolPoint) -> bool:
        """检查保安是否到达巡逻点"""
        distance = np.sqrt(
            (guard.last_position[0] - point.coordinates[0]) ** 2 +
            (guard.last_position[1] - point.coordinates[1]) ** 2
        )
        return distance <= point.radius

    def update_guard_status(self, frame: np.ndarray):
        """更新保安状态"""
        current_time = datetime.now()
        detected_guards = self.detect_security_guards(frame)

        # 更新现有保安的状态
        for guard in detected_guards:
            if guard.guard_id in self.active_guards:
                self.active_guards[guard.guard_id].last_position = guard.last_position
                self.active_guards[guard.guard_id].last_seen = current_time
            else:
                self.active_guards[guard.guard_id] = guard

        # 检查并移除长时间未见的保安
        guards_to_remove = []
        for guard_id, guard in self.active_guards.items():
            time_diff = (current_time - guard.last_seen).total_seconds()
            if time_diff > DETECTION_CONFIG['max_missing_time']:
                guards_to_remove.append(guard_id)
                logger.warning(f"保安 {guard_id} 已超过 {DETECTION_CONFIG['max_missing_time']} 秒未被检测到")

        for guard_id in guards_to_remove:
            del self.active_guards[guard_id]

    def process_frame(self, frame: np.ndarray):
        """处理视频帧"""
        try:
            if frame is None:
                raise ValueError("接收到空帧")
                
            self.update_guard_status(frame)
            # 在画面中标注保安位置和巡逻点
            self._draw_debug_info(frame)
            return frame
        except Exception as e:
            logger.error(f"帧处理失败: {str(e)}")
            return frame

    def _draw_debug_info(self, frame: np.ndarray):
        """在画面中绘制调试信息"""
        # 绘制巡逻点
        for point in PATROL_POINTS:
            cv2.circle(frame, point.coordinates, point.radius, (0, 255, 0), 2)
            cv2.putText(frame, point.name, 
                       (point.coordinates[0], point.coordinates[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # 绘制保安位置
        for guard in self.active_guards.values():
            cv2.circle(frame, guard.last_position, 5, (0, 0, 255), -1)
            cv2.putText(frame, f"Guard {guard.guard_id}", 
                       (guard.last_position[0], guard.last_position[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2) 