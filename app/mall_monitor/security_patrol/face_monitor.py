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

    def start_video_file_monitor(self, camera_id: str, video_path: str, force_no_gui: bool = False):
        """从视频文件读取并进行人脸识别和巡逻记录

        该方法实现以下功能：
        1. 读取并解析视频文件
        2. 对视频帧进行人脸检测和识别
        3. 记录识别到的保安巡逻记录
        4. 支持GUI和非GUI两种处理模式
        5. GUI模式下支持视频播放控制（暂停、快进、后退）

        Args:
            camera_id (str): 摄像头ID，用于记录巡逻位置
            video_path (str): 视频文件路径，支持绝对路径和相对路径
            force_no_gui (bool, optional): 是否强制不显示GUI界面。
                                         即使在有GUI环境的情况下，设为True也不会显示界面，
                                         用于后台处理或服务器部署。默认为False。

        处理流程：
        1. 视频文件读取：
           - 打开视频文件
           - 获取视频基本信息（总帧数、帧率、时长）
           
        2. 环境检测：
           - 检查是否有GUI环境
           - 根据force_no_gui参数决定是否显示界面
           
        3. 帧处理：
           - 读取视频帧
           - 进行人脸检测和识别
           - 记录识别到的保安巡逻记录
           
        4. GUI模式特性：
           - 显示视频画面
           - 绘制人脸框和标注
           - 显示进度条和时间信息
           - 支持播放控制：
             * 空格键：暂停/继续
             * 左方向键：后退5秒
             * 右方向键：前进5秒
             * Q键：退出
           
        5. 非GUI模式特性：
           - 不显示界面，仅在后台处理
           - 定期输出处理进度日志
           - 以最快速度处理视频
           
        注意事项：
        1. 视频文件必须存在且格式正确
        2. 在非GUI模式下，所有界面相关的操作都会被跳过
        3. 程序可以通过Ctrl+C中断运行
        4. 所有异常都会被记录到日志中

        Raises:
            Exception: 当视频文件无法打开或处理过程中发生错误时抛出
        """
        try:
            # 1. 初始化视频捕获
            video_path = str(video_path)  # 确保是字符串路径
            logger.info(f"正在打开视频文件: {video_path}")
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception(f"无法打开视频文件: {video_path}")
            
            # 2. 获取视频基本信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            if fps == 0:  # 防止除以0错误
                fps = 30  # 使用默认帧率
            duration = total_frames / fps  # 计算视频总时长（秒）
            
            logger.info(f"视频信息 - 总帧数: {total_frames}, FPS: {fps}, "
                       f"时长: {duration:.1f}秒")
            
            # 3. GUI环境检测和初始化
            enable_gui = has_display() and not force_no_gui
            if enable_gui:
                logger.info("将显示处理画面")
                cv2.namedWindow('Face Monitor')  # 创建显示窗口
            else:
                logger.info("将以最快速度处理视频")
            
            # 4. 初始化处理状态变量
            frame_count = 0  # 当前处理的帧数
            is_paused = False  # 暂停状态标志
            last_frame = None  # 用于暂停时显示的帧
            
            # 5. 设置日志更新间隔（每秒更新一次）
            log_interval = fps  # 每隔一秒（fps帧）输出一次日志
            next_log_frame = log_interval  # 下一次输出日志的帧数
            
            # 6. 主处理循环
            while True:
                # 6.1 处理暂停状态
                if not is_paused:
                    # 读取视频帧
                    ret, frame = cap.read()
                    if not ret:  # 视频结束
                        logger.info("视频读取完成")
                        break
                    
                    frame_count += 1
                    
                    # 6.2 更新处理进度日志
                    if frame_count >= next_log_frame:
                        progress = (frame_count / total_frames) * 100
                        current_time = frame_count / fps
                        time_text = f"{int(current_time/60):02d}:{int(current_time%60):02d}"
                        logger.info(f"处理进度: {progress:.1f}% ({frame_count}/{total_frames}) - 当前时间: {time_text}")
                        next_log_frame = frame_count + log_interval
                    
                    # 6.3 人脸识别处理
                    matched_faces, unmatched_faces = self._recognize_face(frame)
                    
                    # 6.4 记录巡逻信息（无论是否有GUI都需要）
                    for guard_id, face_location, guard_name in matched_faces:
                        self._record_patrol(guard_id)
                    
                    # 6.5 GUI模式的显示处理
                    if enable_gui:
                        # 创建显示帧的副本
                        display_frame = frame.copy()
                        
                        # 绘制未匹配的人脸框
                        for face_location in unmatched_faces:
                            display_frame = draw_face_box(
                                display_frame,
                                face_location,
                                "",  # 不显示文字
                                box_color=FR_SETTINGS['unknown_face_box_color'],
                                box_thickness=FR_SETTINGS['face_box_thickness']
                            )
                        
                        # 绘制匹配到的人脸框和信息
                        for guard_id, face_location, guard_name in matched_faces:
                            display_frame = draw_face_box(
                                display_frame,
                                face_location,
                                f"{guard_name} ({guard_id})",
                                box_color=FR_SETTINGS['face_box_color'],
                                box_thickness=FR_SETTINGS['face_box_thickness'],
                                font_size=int(FR_SETTINGS['display_font_scale'] * 48)
                            )
                        
                        # 绘制进度条
                        progress_bar_width = display_frame.shape[1] - 40
                        progress_x = int(progress_bar_width * (frame_count / total_frames))
                        cv2.rectangle(display_frame, (20, 20), (20 + progress_bar_width, 30), 
                                    (100, 100, 100), -1)  # 背景
                        cv2.rectangle(display_frame, (20, 20), (20 + progress_x, 30), 
                                    (0, 255, 0), -1)  # 进度
                        
                        # 绘制时间信息
                        current_time = frame_count / fps
                        time_text = f"{int(current_time/60):02d}:{int(current_time%60):02d} / "
                        time_text += f"{int(duration/60):02d}:{int(duration%60):02d}"
                        cv2.putText(display_frame, time_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.6, (255, 255, 255), 2)
                        
                        # 更新显示帧
                        last_frame = display_frame
                        cv2.imshow('Face Monitor', display_frame)
                        
                        # 6.6 处理键盘控制事件
                        key = cv2.waitKey(1) & 0xFF
                        
                        if key == ord('q'):  # 退出
                            logger.info("用户手动停止处理")
                            break
                        elif key == ord(' '):  # 暂停/继续
                            is_paused = not is_paused
                            logger.info("视频已{}".format("暂停" if is_paused else "继续"))
                        elif key == 81 or key == 2:  # 左方向键，后退5秒
                            current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                            target_frame = max(0, current_frame - fps * 5)
                            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                            frame_count = int(target_frame)
                            next_log_frame = frame_count + (log_interval - frame_count % log_interval)
                            logger.info(f"后退5秒 -> {int(target_frame/fps)}秒")
                        elif key == 83 or key == 3:  # 右方向键，前进5秒
                            current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                            target_frame = min(total_frames - 1, current_frame + fps * 5)
                            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                            frame_count = int(target_frame)
                            next_log_frame = frame_count + (log_interval - frame_count % log_interval)
                            logger.info(f"前进5秒 -> {int(target_frame/fps)}秒")
                
                # 6.7 GUI模式下的暂停状态处理
                elif enable_gui:
                    cv2.imshow('Face Monitor', last_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("用户手动停止处理")
                        break
                    elif key == ord(' '):
                        is_paused = False
                        logger.info("视频已继续")
                    
        except Exception as e:
            logger.error(f"视频处理发生错误: {str(e)}")
            raise
            
        finally:
            # 7. 清理资源
            cap.release()  # 释放视频捕获资源
            if enable_gui:
                cv2.destroyAllWindows()  # 关闭所有OpenCV窗口
            logger.info("视频处理完成，资源已释放")