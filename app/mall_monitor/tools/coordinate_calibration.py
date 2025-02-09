import cv2
import numpy as np
import json
import argparse
from typing import Dict, List, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from app.utils.logger import logger
from app.mall_monitor.security_patrol.camera_manager import CameraManager
from app.mall_monitor.security_patrol.patrol_point_manager import PatrolPointManager
from app.config.settings import BASE_DIR

class CoordinateCalibrator:
    def __init__(self, camera_id: str, video_source: str):
        self.camera_id = camera_id
        self.video_source = video_source
        self.camera_manager = CameraManager()
        self.point_manager = PatrolPointManager()
        
        # 加载摄像头信息
        self.camera = self.camera_manager.get_camera(camera_id)
        if not self.camera:
            raise ValueError(f"未找到摄像头配置: {camera_id}")
            
        # 加载当前摄像头的巡逻点位
        self.points = self.point_manager.get_points_by_camera(camera_id)
        logger.info(f"已加载摄像头 {camera_id} 的 {len(self.points)} 个巡逻点位")
        
        # 标定状态
        self.current_point_name = ""
        self.calibrating = False
        
        # 加载中文字体
        try:
            # 尝试多个字体路径
            font_paths = [
                str(Path(BASE_DIR) / "resources" / "fonts" / "wqy-microhei.ttc"),
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
                "C:\\Windows\\Fonts\\simhei.ttf",
                "/System/Library/Fonts/PingFang.ttc"
            ]
            
            font_loaded = False
            for font_path in font_paths:
                try:
                    if Path(font_path).exists():
                        self.font = ImageFont.truetype(font_path, 20)
                        self.small_font = ImageFont.truetype(font_path, 16)
                        logger.info(f"成功加载字体: {font_path}")
                        font_loaded = True
                        break
                except Exception:
                    continue
            
            if not font_loaded:
                raise Exception("未找到可用的中文字体")
                
        except Exception as e:
            logger.warning(f"无法加载中文字体: {str(e)}，将使用默认字体")
            self.font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()

    def _cv2_add_chinese_text(self, img, text, position, font_size, color):
        """使用PIL添加中文文字到图片上"""
        # Convert to PIL Image
        cv2_im = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_im = Image.fromarray(cv2_im)
        
        # Draw text
        draw = ImageDraw.Draw(pil_im)
        font = self.font if font_size > 18 else self.small_font
        draw.text(position, text, font=font, fill=color)
        
        # Convert back to OpenCV format
        cv2_text_im = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
        return cv2_text_im

    def run(self):
        """运行标定工具"""
        cap = cv2.VideoCapture(self.video_source)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频源: {self.video_source}")

        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and self.calibrating:
                self._add_patrol_point(x, y)

        window_name = f"Calibration Tool - {self.camera_id}"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, mouse_callback)

        print(f"\n当前摄像头: {self.camera.name}")
        print(f"已配置点位数: {len(self.points)}")
        print("\n操作说明:")
        print("1. 按 'n' 键输入新点位名称")
        print("2. 点击画面选择点位坐标")
        print("3. 按 'q' 键退出程序\n")

        while True:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # 绘制现有点位
            display = self._draw_points(frame.copy())

            # 显示操作提示和信息
            if self.calibrating:
                display = self._cv2_add_chinese_text(
                    display, 
                    f"正在添加点位: {self.current_point_name}", 
                    (10, 30), 
                    20, 
                    (0, 255, 0)
                )
            else:
                display = self._cv2_add_chinese_text(
                    display,
                    "按 'n' 添加新点位, 'q' 退出",
                    (10, 30),
                    20,
                    (0, 255, 0)
                )

            # 显示摄像头信息
            display = self._cv2_add_chinese_text(
                display,
                f"摄像头: {self.camera.name}",
                (10, 60),
                20,
                (255, 255, 0)
            )
            display = self._cv2_add_chinese_text(
                display,
                f"点位数量: {len(self.points)}",
                (10, 90),
                20,
                (255, 255, 0)
            )

            cv2.imshow(window_name, display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('n'):
                self.current_point_name = input("\n请输入点位名称 (Enter point name): ")
                self.calibrating = True

        cap.release()
        cv2.destroyAllWindows()

    def _draw_points(self, frame: np.ndarray) -> np.ndarray:
        """绘制点位"""
        result = frame.copy()
        for point in self.points:
            # 绘制圆圈
            cv2.circle(result, (point.coord_x, point.coord_y), point.radius, (0, 255, 0), 2)
            
            # 使用PIL绘制中文点位名称
            result = self._cv2_add_chinese_text(
                result,
                point.name,
                (point.coord_x - 20, point.coord_y - 25),
                16,
                (0, 255, 0)
            )
            
            # 绘制坐标
            result = self._cv2_add_chinese_text(
                result,
                f"({point.coord_x}, {point.coord_y})",
                (point.coord_x - 20, point.coord_y + 5),
                16,
                (0, 255, 0)
            )
        return result

    def _add_patrol_point(self, x: int, y: int):
        """添加巡逻点位"""
        try:
            # 添加到数据库
            point_id = self.point_manager.add_point(
                camera_id=self.camera_id,
                name=self.current_point_name,
                coord_x=x,
                coord_y=y,
                description=f"{self.camera.name} - {self.current_point_name}"
            )
            
            if point_id:
                print(f"\nPoint added successfully: {self.current_point_name} ({x}, {y})")
                # 重新加载当前摄像头的点位
                self.points = self.point_manager.get_points_by_camera(self.camera_id)
                print(f"Current camera has {len(self.points)} points")
            else:
                print("\nFailed to add point")
            
            # 重置标定状态
            self.calibrating = False
            self.current_point_name = ""
            
        except Exception as e:
            logger.error(f"Failed to add point: {str(e)}")
            print("\nFailed to add point, check logs for details")

def main():
    parser = argparse.ArgumentParser(description='Patrol Point Calibration Tool')
    parser.add_argument('camera_id', help='Camera ID')
    parser.add_argument('--source', help='Video source path', required=True)
    args = parser.parse_args()

    try:
        calibrator = CoordinateCalibrator(args.camera_id, args.source)
        calibrator.run()
    except Exception as e:
        logger.error(f"Calibration error: {str(e)}")
        print(f"\nCalibration failed: {str(e)}")

if __name__ == "__main__":
    main() 