import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.utils.logger import logger
from app.utils.exceptions import FaceActionMonitorException
from .patrol_config import PatrolPoint, PatrolRoute, DETECTION_CONFIG

@dataclass
class SecurityGuard:
    """保安信息"""
    guard_id: str
    last_position: tuple
    last_seen: datetime
    current_route: Optional[str] = None
    visited_points: List[str] = None

class PatrolDetector:
    def __init__(self):
        self.active_guards: Dict[str, SecurityGuard] = {}
        self._load_models()
        
    def _load_models(self):
        """加载必要的检测模型"""
        try:
            # TODO: 这里需要根据实际选用的模型来实现
            # 可以使用 MediaPipe 或其他人体检测模型
            pass
        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            raise FaceActionMonitorException("模型加载失败")

    def detect_security_guards(self, frame: np.ndarray) -> List[SecurityGuard]:
        """检测画面中的保安"""
        try:
            # TODO: 实现保安检测逻辑
            # 1. 人体检测
            # 2. 制服识别
            # 3. 返回检测到的保安列表
            pass
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