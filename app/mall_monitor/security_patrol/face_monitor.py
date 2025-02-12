import cv2
import numpy as np
from datetime import datetime, timedelta
import face_recognition
import os
import sys
from typing import Optional, Tuple, List, Dict

from app.utils.logger import logger
from app.utils.db_utils import execute_query, execute_update
from app.utils.cv_utils import draw_face_box
from app.config.settings import FACE_RECOGNITION_SETTINGS as FR_SETTINGS

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

    def start_video_file_monitor(self, camera_id: str, video_path: str):
        """从视频文件读取并进行人脸识别

        Args:
            camera_id: 摄像头ID
            video_path: 视频文件路径
        """
        try:
            video_path = str(video_path)  # 确保是字符串路径
            logger.info(f"正在打开视频文件: {video_path}")
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception(f"无法打开视频文件: {video_path}")
            
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            if fps == 0:  # 防止除以0错误
                fps = 30
            duration = total_frames / fps
            
            logger.info(f"视频信息 - 总帧数: {total_frames}, FPS: {fps}, "
                       f"时长: {duration:.1f}秒")
            
            # 检查是否有GUI环境
            has_gui = has_display()
            if has_gui:
                logger.info("检测到GUI环境，将显示处理画面")
                cv2.namedWindow('Face Monitor')
                frame_delay = int(1000 / fps)  # 每帧延迟的毫秒数
            else:
                logger.info("未检测到GUI环境，将以最快速度处理视频")
                frame_delay = 1
            
            frame_count = 0
            last_process_time = datetime.now()
            is_paused = False
            last_frame = None  # 保存最后一帧用于暂停显示
            
            while True:
                if not is_paused:
                    ret, frame = cap.read()
                    if not ret:
                        logger.info("视频读取完成")
                        break
                    
                    frame_count += 1
                    last_frame = frame.copy()  # 保存当前帧
                    
                    # 显示进度
                    progress = (frame_count / total_frames) * 100
                    if frame_count % fps == 0:  # 每秒更新一次日志
                        logger.info(f"处理进度: {progress:.1f}% "
                                  f"({frame_count}/{total_frames})")
                    
                    # 控制处理帧的频率
                    now = datetime.now()
                    if (now - last_process_time).total_seconds() < FR_SETTINGS['frame_process_interval']:
                        continue
                    last_process_time = now
                    
                    # 识别人脸
                    matched_faces, unmatched_faces = self._recognize_face(frame)
                    
                    # 处理未匹配的人脸
                    for face_location in unmatched_faces:
                        if has_gui:
                            frame = draw_face_box(
                                frame,
                                face_location,
                                "",  # 不显示文字
                                box_color=FR_SETTINGS['unknown_face_box_color'],
                                box_thickness=FR_SETTINGS['face_box_thickness']
                            )
                    
                    # 处理匹配到的人脸
                    for guard_id, face_location, guard_name in matched_faces:
                        if has_gui:
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
                    
                    if has_gui:
                        # 添加进度条
                        progress_bar_width = frame.shape[1] - 40
                        progress_x = int(progress_bar_width * (frame_count / total_frames))
                        cv2.rectangle(frame, (20, 20), (20 + progress_bar_width, 30), 
                                    (100, 100, 100), -1)
                        cv2.rectangle(frame, (20, 20), (20 + progress_x, 30), 
                                    (0, 255, 0), -1)
                        
                        # 显示时间信息
                        current_time = frame_count / fps
                        time_text = f"{int(current_time/60):02d}:{int(current_time%60):02d} / "
                        time_text += f"{int(duration/60):02d}:{int(duration%60):02d}"
                        cv2.putText(frame, time_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.6, (255, 255, 255), 2)
                
                if has_gui:
                    # 显示画面
                    cv2.imshow('Face Monitor', frame if not is_paused else last_frame)
                    
                    # 处理键盘事件
                    key = cv2.waitKey(0 if is_paused else frame_delay) & 0xFF
                    
                    if key == ord('q'):
                        logger.info("用户手动停止处理")
                        break
                    elif key == ord(' '):
                        is_paused = not is_paused
                        logger.info("视频已{}".format("暂停" if is_paused else "继续"))
                    elif key == ord(','):  # 后退5秒
                        current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                        target_frame = max(0, current_frame - fps * 5)
                        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                        frame_count = int(target_frame)
                    elif key == ord('.'):  # 前进5秒
                        current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                        target_frame = min(total_frames - 1, current_frame + fps * 5)
                        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                        frame_count = int(target_frame)
                    
        except Exception as e:
            logger.error(f"视频处理发生错误: {str(e)}")
            raise
            
        finally:
            cap.release()
            if has_gui:
                cv2.destroyAllWindows()
            logger.info("视频处理完成，资源已释放") 