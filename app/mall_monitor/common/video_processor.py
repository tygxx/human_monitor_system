import cv2
from typing import Dict, Optional
from app.utils.logger import logger
from app.config.settings import TEST_VIDEO_CONFIG

class VideoProcessor:
    def __init__(self):
        self.video_captures: Dict[str, cv2.VideoCapture] = {}
        self.init_video_sources()

    def init_video_sources(self):
        """初始化视频源"""
        for camera_id, config in TEST_VIDEO_CONFIG.items():
            try:
                cap = cv2.VideoCapture(config['video_path'])
                if not cap.isOpened():
                    logger.error(f"无法打开视频文件: {config['video_path']}")
                    continue
                self.video_captures[camera_id] = cap
                logger.info(f"成功加载摄像头 {camera_id} 的测试视频")
            except Exception as e:
                logger.error(f"加载视频源失败 {camera_id}: {str(e)}")

    def get_frame(self, camera_id: str) -> Optional[tuple]:
        """获取指定摄像头的下一帧"""
        if camera_id not in self.video_captures:
            return None

        cap = self.video_captures[camera_id]
        ret, frame = cap.read()

        # 如果视频结束，循环播放
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()

        if ret:
            return ret, frame
        return None

    def release(self):
        """释放所有视频资源"""
        for cap in self.video_captures.values():
            cap.release()
        cv2.destroyAllWindows() 