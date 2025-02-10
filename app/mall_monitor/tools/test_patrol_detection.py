import cv2
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import threading
import queue
from app.utils.logger import logger
from app.mall_monitor.security_patrol.camera_manager import CameraManager
from app.mall_monitor.security_patrol.patrol_detector import PatrolDetector
from app.utils.cv_utils import put_chinese_text

class PatrolDetectionTester:
    def __init__(self):
        self.camera_manager = CameraManager()
        self.camera_id = None
        self.detector = None
        self.video_path = None
        self.frame_queue = queue.Queue(maxsize=30)  # 帧缓冲队列
        self.result_queue = queue.Queue(maxsize=30)  # 结果缓冲队列
        self.is_running = False
        self.display_width = 1280  # 显示宽度
        self.display_height = 720  # 显示高度
        self.original_size = None  # 原始视频尺寸

    def setup(self) -> bool:
        """初始化设置"""
        try:
            # 1. 输入并验证摄像头ID
            while True:
                self.camera_id = input("\n请输入摄像头ID (例如: CAM_1F_GATE): ").strip()
                if not self.camera_id:
                    print("摄像头ID不能为空")
                    continue
                
                # 检查摄像头是否存在
                camera = self.camera_manager.get_camera(self.camera_id)
                if not camera:
                    print(f"未找到摄像头配置: {self.camera_id}")
                    if not self._confirm("是否重新输入? (y/n): "):
                        return False
                    continue
                
                print(f"\n已找到摄像头: {camera.name}")
                break

            # 2. 输入并验证视频文件路径
            while True:
                self.video_path = input("\n请输入测试视频路径: ").strip()
                if not self.video_path:
                    print("视频路径不能为空")
                    continue
                
                # 检查文件是否存在
                if not Path(self.video_path).exists():
                    print(f"视频文件不存在: {self.video_path}")
                    if not self._confirm("是否重新输入? (y/n): "):
                        return False
                    continue
                
                # 验证视频文件是否可以打开
                cap = cv2.VideoCapture(self.video_path)
                if not cap.isOpened():
                    cap.release()
                    print(f"无法打开视频文件: {self.video_path}")
                    if not self._confirm("是否重新输入? (y/n): "):
                        return False
                    continue
                
                # 获取视频信息
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                self.original_size = (width, height)
                
                # 计算显示尺寸
                self._calculate_display_size(width, height)
                
                print(f"\n视频信息:")
                print(f"原始分辨率: {width}x{height}")
                print(f"显示分辨率: {self.display_width}x{self.display_height}")
                print(f"帧率: {fps}")
                
                if not self._confirm("确认使用该视频文件? (y/n): "):
                    continue
                break

            # 3. 初始化检测器
            self.detector = PatrolDetector(self.camera_id)
            if not self.detector.patrol_points:
                print(f"\n警告: 摄像头 {self.camera_id} 未配置巡逻点位")
                if not self._confirm("是否继续? (y/n): "):
                    return False

            return True

        except Exception as e:
            logger.error(f"设置失败: {str(e)}")
            print(f"\n设置失败: {str(e)}")
            return False

    def _calculate_display_size(self, width: int, height: int):
        """计算等比例缩放后的显示尺寸"""
        # 设置最大显示尺寸
        max_width = 1280
        max_height = 720
        
        # 计算缩放比例
        scale_w = max_width / width
        scale_h = max_height / height
        scale = min(scale_w, scale_h)
        
        if scale >= 1:  # 如果原始尺寸小于最大尺寸，保持原始尺寸
            self.display_width = width
            self.display_height = height
        else:  # 等比例缩放
            self.display_width = int(width * scale)
            self.display_height = int(height * scale)

    def _resize_frame(self, frame):
        """调整图像尺寸"""
        if frame.shape[1] != self.display_width or frame.shape[0] != self.display_height:
            frame = cv2.resize(frame, (self.display_width, self.display_height))
        return frame

    def _scale_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """坐标比例转换（显示坐标转换为原始坐标）"""
        orig_x = int(x * (self.original_size[0] / self.display_width))
        orig_y = int(y * (self.original_size[1] / self.display_height))
        return orig_x, orig_y

    def run(self):
        """运行测试"""
        if not self.detector or not self.video_path:
            print("请先完成设置")
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"无法打开视频文件: {self.video_path}")
            return

        logger.info(f"开始测试摄像头 {self.camera_id} 的巡逻检测")
        print(f"\n开始处理视频...")
        print("按 'q' 键退出\n")

        # 启动工作线程
        self.is_running = True
        read_thread = threading.Thread(target=self._read_frames, args=(cap,))
        process_thread = threading.Thread(target=self._process_frames)
        read_thread.start()
        process_thread.start()

        try:
            while self.is_running:
                if not self.result_queue.empty():
                    frame, results = self.result_queue.get()
                    display = self.draw_debug_info(frame, results)
                    
                    # 显示结果
                    cv2.imshow(f"Patrol Detection - {self.camera_id}", display)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.is_running = False
                        break
        except KeyboardInterrupt:
            self.is_running = False

        # 等待线程结束
        read_thread.join()
        process_thread.join()
        cap.release()
        cv2.destroyAllWindows()
        logger.info("测试结束")

    def _read_frames(self, cap):
        """读取视频帧的线程"""
        target_fps = 15  # 目标帧率
        frame_interval = 1.0 / target_fps  # 帧间隔时间
        last_frame_time = datetime.now()

        while self.is_running:
            current_time = datetime.now()
            elapsed = (current_time - last_frame_time).total_seconds()
            
            if elapsed < frame_interval:
                continue

            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            try:
                if not self.frame_queue.full():
                    self.frame_queue.put(frame, timeout=0.1)
                    last_frame_time = current_time
            except queue.Full:
                continue

    def _process_frames(self):
        """处理视频帧的线程"""
        while self.is_running:
            try:
                frame = self.frame_queue.get(timeout=0.1)
                results = self.detector.detect_frame(frame)
                
                # 清空结果队列，只保留最新的帧
                while not self.result_queue.empty():
                    try:
                        self.result_queue.get_nowait()
                    except queue.Empty:
                        break
                
                self.result_queue.put((frame, results))
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"处理帧时出错: {str(e)}")

    def draw_debug_info(self, frame, results):
        """绘制调试信息"""
        # 调整图像尺寸
        display = self._resize_frame(frame.copy())
        
        # 绘制巡逻点位（需要调整坐标）
        for point in self.detector.patrol_points:
            # 计算显示坐标
            display_x = int(point.coord_x * (self.display_width / self.original_size[0]))
            display_y = int(point.coord_y * (self.display_height / self.original_size[1]))
            display_radius = int(point.radius * (self.display_width / self.original_size[0]))
            
            # 绘制圆圈和点位名称
            cv2.circle(display, (display_x, display_y), display_radius, (0, 255, 0), 2)
            display = put_chinese_text(
                display, 
                point.name,
                (display_x - 20, display_y - 10),
                (0, 255, 0),
                'small'
            )
        
        # 绘制检测结果
        for point, guard in results:
            # 计算显示坐标
            display_x = int(point.coord_x * (self.display_width / self.original_size[0]))
            display_y = int(point.coord_y * (self.display_height / self.original_size[1]))
            
            # 显示保安信息
            display = put_chinese_text(
                display,
                guard.name,
                (display_x - 20, display_y - 40),
                (0, 0, 255)
            )
        
        # 显示时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display = put_chinese_text(
            display,
            timestamp,
            (10, 30),
            (0, 255, 0)
        )
        
        return display

    def _confirm(self, prompt: str) -> bool:
        """确认提示"""
        while True:
            response = input(prompt).strip().lower()
            if response in ['y', 'yes']:
                return True
            if response in ['n', 'no']:
                return False
            print("请输入 y 或 n")

def main():
    try:
        tester = PatrolDetectionTester()
        if tester.setup():
            tester.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        print(f"\n测试失败: {str(e)}")

if __name__ == "__main__":
    main() 