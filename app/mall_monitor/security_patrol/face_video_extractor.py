import cv2
import numpy as np
from datetime import datetime
import face_recognition
import os
from pathlib import Path
from typing import Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor
import threading

from app.utils.logger import logger
from app.config.settings import DATA_DIR, FACE_RECOGNITION_SETTINGS as FR_SETTINGS

# 创建全局线程锁用于保护face_recognition调用
face_recognition_lock = threading.Lock()

class FaceScreenshotExtractor:
    def __init__(self):
        # 创建输出目录
        self.output_dir = Path(DATA_DIR) / "face_screenshots"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置参数
        self.confidence_threshold = FR_SETTINGS['face_match_tolerance']
        self.screenshot_interval = 10  # 每隔多少秒保存一次截图
        self.num_threads = min(8, (os.cpu_count() or 4))  # 线程数
        self.batch_size = 32  # 批处理大小
        
        # 缓存目标人脸编码
        self.target_encoding = None
        self.last_screenshot_time = 0  # 上次截图的时间戳（秒）
    
    def _load_face_encoding(self, image_path: str) -> Optional[np.ndarray]:
        """加载目标人脸特征"""
        try:
            with face_recognition_lock:
                # 读取图片
                image = face_recognition.load_image_file(image_path)
                
                # 检测人脸
                face_locations = face_recognition.face_locations(image)
                if not face_locations:
                    raise ValueError("未在图片中检测到人脸")
                if len(face_locations) > 1:
                    raise ValueError("图片中包含多个人脸，请提供只包含一个人脸的图片")
                
                # 提取特征
                face_encodings = face_recognition.face_encodings(image, face_locations)
                if not face_encodings:
                    raise ValueError("无法提取人脸特征")
                    
                return face_encodings[0]
                
        except Exception as e:
            logger.error(f"加载人脸特征失败: {str(e)}")
            raise
    
    def _process_frame(self, frame: np.ndarray) -> Tuple[bool, float, List[tuple]]:
        """处理单帧，返回是否匹配、置信度和人脸位置"""
        try:
            # 转换为RGB格式
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            with face_recognition_lock:
                # 检测人脸
                face_locations = face_recognition.face_locations(rgb_frame)
                if not face_locations:
                    return False, 0.0, []
                    
                # 提取特征并匹配
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if not face_encodings:
                    return False, 0.0, []
                    
                matches = face_recognition.compare_faces(
                    [self.target_encoding],
                    face_encodings[0],
                    tolerance=self.confidence_threshold
                )
                
                if True in matches:
                    face_distances = face_recognition.face_distance([self.target_encoding], face_encodings[0])
                    return True, 1 - face_distances[0], face_locations
                    
                return False, 0.0, []
                
        except Exception as e:
            logger.error(f"处理帧时发生错误: {str(e)}")
            return False, 0.0, []
    
    def _save_screenshot(self, frame: np.ndarray, face_locations: List[tuple], 
                        current_time: float, confidence: float) -> str:
        """保存带有人脸框的截图"""
        try:
            # 在人脸周围画框
            for face_location in face_locations:
                top, right, bottom, left = face_location
                cv2.rectangle(frame, (left, top), (right, bottom), 
                            FR_SETTINGS['face_box_color'], 
                            FR_SETTINGS['face_box_thickness'])
                
                # 添加置信度文本
                text = f"Confidence: {confidence:.2f}"
                cv2.putText(frame, text, (left, top - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                           FR_SETTINGS['face_box_color'], 1)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"face_screenshot_{timestamp}.jpg"
            output_path = str(self.output_dir / filename)
            
            # 保存图片
            cv2.imwrite(output_path, frame)
            logger.info(f"保存截图: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"保存截图时发生错误: {str(e)}")
            return ""
    
    def process_video(self, face_image_path: str, video_path: str, show_process: bool = False) -> List[str]:
        """处理视频并保存人脸截图
        
        Args:
            face_image_path: 目标人脸图片路径
            video_path: 要分析的视频路径
            show_process: 是否显示处理过程
            
        Returns:
            保存的截图文件路径列表
        """
        try:
            # 1. 加载目标人脸特征
            logger.info("正在加载目标人脸特征...")
            self.target_encoding = self._load_face_encoding(face_image_path)
            
            # 2. 打开视频
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")
            
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            if fps == 0:
                fps = 30
            
            logger.info(f"开始处理视频 - 总帧数: {total_frames}, FPS: {fps}")
            
            # 3. 处理视频帧
            frame_count = 0
            screenshot_paths = []
            self.last_screenshot_time = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                current_time = frame_count / fps
                
                # 控制处理频率
                if current_time - self.last_screenshot_time >= self.screenshot_interval:
                    # 处理当前帧
                    has_target, confidence, face_locations = self._process_frame(frame)
                    
                    if has_target:
                        # 保存截图
                        screenshot_path = self._save_screenshot(
                            frame, face_locations, current_time, confidence)
                        if screenshot_path:
                            screenshot_paths.append(screenshot_path)
                            self.last_screenshot_time = current_time
                
                if show_process:
                    cv2.imshow('Processing Video', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                frame_count += 1
                if frame_count % fps == 0:
                    progress = (frame_count / total_frames) * 100
                    logger.info(f"处理进度: {progress:.1f}% ({frame_count}/{total_frames})")
            
            logger.info(f"视频处理完成，共保存 {len(screenshot_paths)} 张截图")
            return screenshot_paths
            
        except Exception as e:
            logger.error(f"处理视频时发生错误: {str(e)}")
            raise
            
        finally:
            if 'cap' in locals():
                cap.release()
            if show_process:
                cv2.destroyAllWindows() 