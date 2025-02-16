import cv2
import numpy as np
from datetime import datetime, timedelta
import face_recognition
import os
import sys
from typing import Optional, Tuple, List, Dict
from concurrent.futures import ThreadPoolExecutor
import threading
from pathlib import Path
import tempfile
import shutil

from app.utils.logger import logger
from app.utils.db_utils import execute_query, execute_update
from app.utils.cv_utils import draw_face_box
from app.config.settings import FACE_RECOGNITION_SETTINGS as FR_SETTINGS
from app.utils.exceptions import VideoProcessError

def has_display() -> bool:
    """检查是否有GUI显示环境"""
    try:
        if sys.platform.startswith('linux'):
            # 检查是否有DISPLAY环境变量
            return bool(os.environ.get('DISPLAY'))
        # Windows和MacOS默认认为有显示环境
        return True
    except Exception:
        return False

class FaceMonitor:
    def __init__(self):
        self.known_face_encodings = []
        self.known_guard_info = {}  # 存储保安完整信息
        self.last_recognition_time = {}  # 记录每个保安最后一次识别时间
        self._load_guard_faces()
        
    def _load_guard_faces(self):
        """从数据库加载所有保安的人脸特征"""
        try:
            sql = """
                SELECT 
                    guard_id,
                    name,
                    gender,
                    phone,
                    face_feature,
                    register_time
                FROM guards 
                WHERE face_feature IS NOT NULL 
                    AND data_status = 1
                ORDER BY register_time DESC
            """
            results = execute_query(sql)
            
            for row in results:
                face_feature = np.frombuffer(row['face_feature'], dtype=np.float64)
                self.known_face_encodings.append(face_feature)
                
                # 存储保安完整信息
                self.known_guard_info[row['guard_id']] = {
                    'name': row['name'],
                    'gender': row['gender'],
                    'phone': row['phone'],
                    'face_encoding': face_feature,
                    'register_time': row['register_time']
                }
                
            logger.info(f"已加载 {len(self.known_guard_info)} 个保安的人脸特征")
            for guard_id, info in self.known_guard_info.items():
                logger.info(f"已加载保安信息 - ID: {guard_id}, 姓名: {info['name']}, "
                          f"注册时间: {info['register_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"加载保安人脸特征失败: {str(e)}")
            raise
    
    def _can_record_patrol(self, guard_id: str) -> bool:
        """检查是否可以记录巡逻"""
        now = datetime.now()
        if guard_id in self.last_recognition_time:
            last_time = self.last_recognition_time[guard_id]
            cooldown = timedelta(seconds=FR_SETTINGS['recognition_cooldown'])
            if now - last_time < cooldown:
                return False
        return True
    
    def _record_patrol(self, guard_id: str):
        """记录巡逻记录"""
        try:
            # 检查是否是有效的保安ID
            if guard_id not in self.known_guard_info:
                logger.warning(f"尝试记录未知保安ID的巡逻记录: {guard_id}")
                return
                
            # 检查冷却时间
            if not self._can_record_patrol(guard_id):
                return
                
            # 记录巡逻
            now = datetime.now()
            sql = """
                INSERT INTO patrol_records 
                    (guard_id, arrival_time) 
                VALUES 
                    (%s, %s)
            """
            execute_update(sql, (guard_id, now))
            
            # 更新最后识别时间
            self.last_recognition_time[guard_id] = now
            
            guard_name = self.known_guard_info[guard_id]['name']
            logger.info(f"已记录保安 {guard_name}(ID: {guard_id}) 的巡逻记录")
            
        except Exception as e:
            logger.error(f"记录巡逻记录失败: {str(e)}")
    
    def _recognize_face(self, frame: np.ndarray) -> Tuple[List[Tuple[str, tuple, str]], List[tuple]]:
        """识别画面中的人脸
        
        Returns:
            Tuple of:
            - List of (guard_id, face_location, name) for matched faces
            - List of face_location for unmatched faces
        """
        # 转换为RGB格式（face_recognition库需要）
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 定位人脸
        face_locations = face_recognition.face_locations(rgb_frame)
        if not face_locations:
            return [], []
            
        # 提取人脸特征
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        matched_faces = []
        unmatched_faces = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # 与已知人脸比对
            matches = face_recognition.compare_faces(
                self.known_face_encodings, 
                face_encoding,
                tolerance=FR_SETTINGS['face_match_tolerance']
            )
            
            if True in matches:
                # 找到匹配的保安
                guard_index = matches.index(True)
                guard_id = list(self.known_guard_info.keys())[guard_index]
                guard_name = self.known_guard_info[guard_id]['name']
                matched_faces.append((guard_id, face_location, guard_name))
                logger.info(f"识别到保安: {guard_name}(ID: {guard_id})")
            else:
                # 未匹配的人脸
                unmatched_faces.append(face_location)
                logger.debug("检测到未匹配的人脸")
                
        return matched_faces, unmatched_faces
    
    def start_local_camera_monitor(self, camera_id: str, camera_index: int = 0):
        """启动本地摄像头监控"""
        try:
            logger.info(f"正在启动本地摄像头 {camera_index} 的监控")
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                raise Exception(f"无法打开摄像头 {camera_index}")
            
            logger.info("摄像头已成功打开，开始监控...")
            last_process_time = datetime.now()
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # 控制处理帧的频率
                now = datetime.now()
                if (now - last_process_time).total_seconds() < FR_SETTINGS['frame_process_interval']:
                    continue
                last_process_time = now
                
                # 识别人脸
                matched_faces, unmatched_faces = self._recognize_face(frame)
                
                # 处理未匹配的人脸
                for face_location in unmatched_faces:
                    # 只绘制人脸框，不显示文字
                    frame = draw_face_box(
                        frame,
                        face_location,
                        "",  # 不显示文字
                        box_color=FR_SETTINGS['unknown_face_box_color'],
                        box_thickness=FR_SETTINGS['face_box_thickness']
                    )
                
                # 处理匹配到的人脸
                for guard_id, face_location, guard_name in matched_faces:
                    # 使用cv_utils绘制人脸框和中文文本
                    frame = draw_face_box(
                        frame,
                        face_location,
                        f"{guard_name} ({guard_id})",
                        box_color=FR_SETTINGS['face_box_color'],
                        box_thickness=FR_SETTINGS['face_box_thickness'],
                        font_size=int(FR_SETTINGS['display_font_scale'] * 48)  # 转换字体大小
                    )
                    
                    # 记录巡逻记录
                    self._record_patrol(guard_id)
                
                # 显示画面
                cv2.imshow('Face Monitor', frame)
                
                # 按q退出
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("收到退出信号，正在停止监控...")
                    break
                    
        except Exception as e:
            logger.error(f"摄像头监控发生错误: {str(e)}")
            raise
            
        finally:
            cap.release()
            cv2.destroyAllWindows()
            logger.info("监控已停止，资源已释放")

    def _process_frame_batch(self, frame_paths: List[Tuple[int, str]]) -> None:
        """处理一批帧图像文件
        
        Args:
            frame_paths: List of (frame_index, frame_path)
        """
        for frame_index, frame_path in frame_paths:
            try:
                # 读取帧
                frame = cv2.imread(frame_path)
                if frame is None:
                    continue
                    
                # 人脸识别
                matched_faces, unmatched_faces = self._recognize_face(frame)
                
                # 记录巡逻信息
                for guard_id, _, _ in matched_faces:
                    self._record_patrol(guard_id)
                    
            except Exception as e:
                logger.error(f"处理帧 {frame_index} 时发生错误: {str(e)}")
                continue

    def start_video_file_monitor(self, camera_id: str, video_path: str, force_no_gui: bool = False):
        """从视频文件读取并进行人脸识别和巡逻记录"""
        temp_dir = None
        try:
            # 1. 初始化视频捕获
            video_path = str(video_path)
            logger.info(f"正在打开视频文件: {video_path}")
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise VideoProcessError(f"无法打开视频文件: {video_path}")
            
            # 2. 获取视频基本信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            if fps == 0:
                fps = 30
            duration = total_frames / fps
            
            logger.info(f"视频信息 - 总帧数: {total_frames}, FPS: {fps}, "
                       f"时长: {duration:.1f}秒")
            
            # 3. GUI环境检测
            enable_gui = has_display() and not force_no_gui
            
            if enable_gui:
                # 4. GUI模式：使用原有的单线程处理方式
                logger.info("将显示处理画面")
                cv2.namedWindow('Face Monitor')
                
                frame_count = 0
                last_process_time = datetime.now()
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    frame_count += 1
                    
                    # 控制处理帧的频率
                    now = datetime.now()
                    if (now - last_process_time).total_seconds() < FR_SETTINGS['frame_process_interval']:
                        continue
                    last_process_time = now
                    
                    # 更新处理进度日志
                    if frame_count % fps == 0:
                        progress = (frame_count / total_frames) * 100
                        current_time = frame_count / fps
                        time_text = f"{int(current_time/60):02d}:{int(current_time%60):02d}"
                        logger.info(f"处理进度: {progress:.1f}% ({frame_count}/{total_frames}) - "
                                  f"当前时间: {time_text}")
                    
                    # 人脸识别
                    matched_faces, unmatched_faces = self._recognize_face(frame)
                    
                    # 处理未匹配的人脸
                    for face_location in unmatched_faces:
                        frame = draw_face_box(
                            frame,
                            face_location,
                            "",
                            box_color=FR_SETTINGS['unknown_face_box_color'],
                            box_thickness=FR_SETTINGS['face_box_thickness']
                        )
                    
                    # 处理匹配到的人脸
                    for guard_id, face_location, guard_name in matched_faces:
                        frame = draw_face_box(
                            frame,
                            face_location,
                            f"{guard_name} ({guard_id})",
                            box_color=FR_SETTINGS['face_box_color'],
                            box_thickness=FR_SETTINGS['face_box_thickness'],
                            font_size=int(FR_SETTINGS['display_font_scale'] * 48)
                        )
                        
                        # 记录巡逻记录
                        self._record_patrol(guard_id)
                    
                    # 显示画面
                    cv2.imshow('Face Monitor', frame)
                    
                    # 按q退出
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        logger.info("用户手动停止处理")
                        break
                
            else:
                # 5. 无GUI模式：使用多线程处理
                logger.info("将以最快速度处理视频")
                
                # 5.1 创建临时目录存储帧
                temp_dir = tempfile.mkdtemp(prefix="video_frames_")
                frame_paths = []
                frame_count = 0
                
                # 5.2 提取帧到临时目录
                logger.info("正在提取视频帧...")
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    frame_path = os.path.join(temp_dir, f"frame_{frame_count:06d}.jpg")
                    cv2.imwrite(frame_path, frame)
                    frame_paths.append((frame_count, frame_path))
                    frame_count += 1
                    
                    # 更新进度
                    if frame_count % fps == 0:
                        progress = (frame_count / total_frames) * 100
                        logger.info(f"帧提取进度: {progress:.1f}% ({frame_count}/{total_frames})")
                
                logger.info(f"帧提取完成，共 {frame_count} 帧")
                
                # 5.3 多线程处理帧
                batch_size = 32  # 每批处理的帧数
                num_threads = min(8, (os.cpu_count() or 4))  # 线程数
                
                logger.info(f"开始处理帧，使用 {num_threads} 个线程")
                
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    # 将帧分成批次
                    for i in range(0, len(frame_paths), batch_size):
                        batch = frame_paths[i:i + batch_size]
                        executor.submit(self._process_frame_batch, batch)
                        
                        # 更新进度
                        processed = min(i + batch_size, len(frame_paths))
                        progress = (processed / len(frame_paths)) * 100
                        logger.info(f"处理进度: {progress:.1f}% ({processed}/{len(frame_paths)})")
                
                logger.info("帧处理完成")
                
        except Exception as e:
            logger.error(f"视频处理发生错误: {str(e)}")
        
        finally:
            if 'cap' in locals():
                cap.release()
            if enable_gui:
                cv2.destroyAllWindows()
            # 清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.error(f"清理临时目录失败: {str(e)}")
            logger.info("视频处理完成，资源已释放")