from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from app.utils.logger import logger
from app.utils.db_utils import with_db_connection
from datetime import datetime
from app.config.settings import PATROL_POINT_CONFIG

@dataclass
class PatrolPoint:
    """巡逻点位信息"""
    point_id: int
    camera_id: str
    name: str
    coord_x: int
    coord_y: int
    radius: int
    description: str

class PatrolPointManager:
    def __init__(self):
        self.points = {}
        self._load_points()

    @with_db_connection
    def _load_points(self, conn=None) -> None:
        """从数据库加载巡逻点位"""
        try:
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT * FROM patrol_points 
                WHERE data_status = 1
            """
            cursor.execute(sql)
            for row in cursor.fetchall():
                point = PatrolPoint(
                    point_id=row['point_id'],
                    camera_id=row['camera_id'],
                    name=row['name'],
                    coord_x=row['coord_x'],
                    coord_y=row['coord_y'],
                    radius=row['radius'],
                    description=row['description']
                )
                self.points[point.point_id] = point
            
            logger.info(f"成功加载 {len(self.points)} 个巡逻点位")
        except Exception as e:
            logger.error(f"加载巡逻点位失败: {str(e)}")
            raise

    @with_db_connection
    def get_points_by_camera(self, camera_id: str, conn=None) -> List[PatrolPoint]:
        """获取指定摄像头的所有巡逻点位"""
        try:
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT * FROM patrol_points 
                WHERE camera_id = %s AND data_status = 1
            """
            cursor.execute(sql, (camera_id,))
            
            points = []
            for row in cursor.fetchall():
                point = PatrolPoint(
                    point_id=row['point_id'],
                    camera_id=row['camera_id'],
                    name=row['name'],
                    coord_x=row['coord_x'],
                    coord_y=row['coord_y'],
                    radius=row['radius'],
                    description=row['description']
                )
                points.append(point)
            
            return points
        except Exception as e:
            logger.error(f"获取摄像头点位失败: {str(e)}")
            return []

    @with_db_connection
    def add_patrol_record(self, guard_id: str, point_id: int, conn=None) -> bool:
        """添加巡逻记录
        Args:
            guard_id: 保安ID
            point_id: 巡逻点位ID
        Returns:
            bool: 是否添加成功
        """
        try:
            cursor = conn.cursor()
            sql = """
                INSERT INTO patrol_records (guard_id, point_id, arrival_time)
                VALUES (%s, %s, NOW())
            """
            cursor.execute(sql, (guard_id, point_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加巡逻记录失败: {str(e)}")
            return False

    @with_db_connection
    def add_point(self, camera_id: str, name: str, coord_x: int, coord_y: int, 
                 description: str = "", radius: int = None, conn=None) -> Optional[int]:
        """添加巡逻点位"""
        try:
            # 使用配置文件中的默认半径
            if radius is None:
                radius = PATROL_POINT_CONFIG['default_radius']
            
            # 确保半径在有效范围内
            radius = max(PATROL_POINT_CONFIG['min_radius'], 
                        min(radius, PATROL_POINT_CONFIG['max_radius']))
            
            cursor = conn.cursor()
            sql = """
                INSERT INTO patrol_points (camera_id, name, coord_x, coord_y, radius, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (camera_id, name, coord_x, coord_y, radius, description))
            point_id = cursor.lastrowid
            conn.commit()
            
            # 更新本地缓存
            point = PatrolPoint(
                point_id=point_id,
                camera_id=camera_id,
                name=name,
                coord_x=coord_x,
                coord_y=coord_y,
                radius=radius,
                description=description
            )
            self.points[point_id] = point
            
            logger.info(f"成功添加巡逻点位: {name} (ID: {point_id}, 半径: {radius})")
            return point_id
            
        except Exception as e:
            logger.error(f"添加巡逻点位失败: {str(e)}")
            return None

    @with_db_connection
    def get_patrol_records(self, start_time: datetime = None, end_time: datetime = None,
                          guard_id: str = None, point_id: int = None, 
                          conn=None) -> List[Dict]:
        """查询巡逻记录"""
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 构建查询条件
            conditions = ["r.data_status = 1"]
            params = []
            
            if start_time:
                conditions.append("r.arrival_time >= %s")
                params.append(start_time)
            if end_time:
                conditions.append("r.arrival_time <= %s")
                params.append(end_time)
            if guard_id:
                conditions.append("r.guard_id = %s")
                params.append(guard_id)
            if point_id:
                conditions.append("r.point_id = %s")
                params.append(point_id)
            
            # 构建SQL
            sql = """
                SELECT r.*, g.name as guard_name, p.name as point_name, 
                       p.camera_id, c.name as camera_name
                FROM patrol_records r
                JOIN guards g ON r.guard_id = g.guard_id
                JOIN patrol_points p ON r.point_id = p.point_id
                JOIN cameras c ON p.camera_id = c.camera_id
                WHERE {}
                ORDER BY r.arrival_time DESC
            """.format(" AND ".join(conditions))
            
            cursor.execute(sql, params)
            records = cursor.fetchall()
            
            logger.info(f"查询到 {len(records)} 条巡逻记录")
            return records
            
        except Exception as e:
            logger.error(f"查询巡逻记录失败: {str(e)}")
            return [] 