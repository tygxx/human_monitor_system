import cv2
import numpy as np
from datetime import datetime, timedelta
import face_recognition
from typing import Optional, Tuple, List, Dict

from app.utils.logger import logger
from app.utils.db_utils import execute_query, execute_update
from app.utils.cv_utils import draw_face_box
from app.config.settings import FACE_RECOGNITION_SETTINGS as FR_SETTINGS

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