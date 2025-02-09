from typing import Dict, List, Optional
from dataclasses import dataclass
from app.utils.logger import logger
from app.utils.db_utils import with_db_connection

@dataclass
class CameraInfo:
    """摄像头信息"""
    camera_id: str
    name: str
    location: str
    resolution_width: int
    resolution_height: int
    fps: int

class CameraManager:
    def __init__(self):
        self.cameras = {}
        self._load_cameras()

    @with_db_connection
    def _load_cameras(self, conn=None) -> None:
        """从数据库加载摄像头配置"""
        try:
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT * FROM cameras 
                WHERE data_status = 1
            """
            cursor.execute(sql)
            for row in cursor.fetchall():
                camera = CameraInfo(
                    camera_id=row['camera_id'],
                    name=row['name'],
                    location=row['location'],
                    resolution_width=row['resolution_width'],
                    resolution_height=row['resolution_height'],
                    fps=row['fps']
                )
                self.cameras[camera.camera_id] = camera
            
            logger.info(f"成功加载 {len(self.cameras)} 个摄像头配置")
        except Exception as e:
            logger.error(f"加载摄像头配置失败: {str(e)}")
            raise

    @with_db_connection
    def get_camera(self, camera_id: str, conn=None) -> Optional[CameraInfo]:
        """获取摄像头信息"""
        try:
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT * FROM cameras 
                WHERE camera_id = %s AND data_status = 1
            """
            cursor.execute(sql, (camera_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return CameraInfo(
                camera_id=row['camera_id'],
                name=row['name'],
                location=row['location'],
                resolution_width=row['resolution_width'],
                resolution_height=row['resolution_height'],
                fps=row['fps']
            )
        except Exception as e:
            logger.error(f"获取摄像头信息失败: {str(e)}")
            return None

    def get_all_cameras(self) -> List[CameraInfo]:
        """获取所有摄像头信息"""
        return list(self.cameras.values()) 