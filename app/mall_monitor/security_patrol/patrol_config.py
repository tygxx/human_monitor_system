from dataclasses import dataclass
from typing import List, Tuple
from datetime import time

@dataclass
class Camera:
    """摄像头配置"""
    camera_id: str
    name: str
    location: str  # 摄像头位置描述
    resolution: Tuple[int, int]  # 摄像头分辨率

@dataclass
class PatrolPoint:
    """巡逻点位配置"""
    point_id: str
    name: str
    camera_id: str  # 关联的摄像头ID
    coordinates: Tuple[int, int]  # 在该摄像头画面中的坐标
    radius: int  # 判定范围半径（像素）

@dataclass
class PatrolRoute:
    """巡逻路线配置"""
    route_id: str
    name: str
    points: List[PatrolPoint]
    expected_duration: int  # 预期完成时间（分钟）

@dataclass
class PatrolSchedule:
    """巡逻时间表"""
    start_time: time
    end_time: time
    interval: int  # 巡逻间隔（分钟）

# 摄像头配置
CAMERAS = [
    Camera(
        camera_id="CAM_1F_GATE",
        name="一楼大门摄像头",
        location="一楼正门入口",
        resolution=(1920, 1080)
    ),
    Camera(
        camera_id="CAM_1F_WEST",
        name="一楼西侧摄像头",
        location="一楼西侧安全出口",
        resolution=(1920, 1080)
    ),
    # ... 其他摄像头配置
]

# 巡逻点位配置
PATROL_POINTS = [
    PatrolPoint(
        point_id="P1",
        name="正门入口检查点",
        camera_id="CAM_1F_GATE",
        coordinates=(960, 540),  # 在该摄像头画面中的位置
        radius=50
    ),
    PatrolPoint(
        point_id="P2",
        name="西侧安全出口检查点",
        camera_id="CAM_1F_WEST",
        coordinates=(800, 600),
        radius=50
    ),
    # ... 其他巡逻点位
]

# 巡逻路线配置
PATROL_ROUTES = [
    PatrolRoute(
        "R1",
        "一层主要路线",
        PATROL_POINTS,
        30  # 30分钟完成一轮巡逻
    )
]

# 巡逻时间表
PATROL_SCHEDULES = [
    PatrolSchedule(
        time(8, 0),   # 早上8点开始
        time(22, 0),  # 晚上10点结束
        60  # 每60分钟一轮巡逻
    )
]

# 检测配置
DETECTION_CONFIG = {
    'min_confidence': 0.7,  # 人员识别最小置信度
    'max_missing_time': 300,  # 允许的最大丢失时间（秒）
    'tracking_persistence': 30  # 跟踪持续时间（帧）
} 