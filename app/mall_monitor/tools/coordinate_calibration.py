import cv2
import json
import argparse
from typing import Dict, List, Tuple
from pathlib import Path

class CoordinateCalibrationTool:
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.points: List[Tuple[str, Tuple[int, int]]] = []
        self.current_point_name = ""
        
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.points.append((self.current_point_name, (x, y)))
            print(f"已标记点位 {self.current_point_name} 在坐标: ({x}, {y})")
    
    def calibrate(self, video_source):
        """
        视频源可以是摄像头索引（整数）或视频文件路径（字符串）
        """
        # 如果是字符串且文件不存在，报错
        if isinstance(video_source, str) and not Path(video_source).exists():
            raise FileNotFoundError(f"找不到视频文件: {video_source}")
            
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频源: {video_source}")
            
        window_name = f"Camera {self.camera_id} Calibration"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self.mouse_callback)
        
        print("\n=== 坐标标定工具 ===")
        print("操作说明：")
        print("1. 按 'n' 键输入新的巡逻点位名称")
        print("2. 用鼠标左键点击画面标记坐标")
        print("3. 按 'q' 键保存并退出")
        print("==================\n")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                # 如果是视频文件，循环播放
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                
            # 显示已标记的点
            for name, (x, y) in self.points:
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
                cv2.putText(frame, name, (x + 10, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('n'):
                self.current_point_name = input("输入巡逻点位名称: ")
        
        cap.release()
        cv2.destroyAllWindows()
        
        # 保存配置
        self.save_configuration()
    
    def save_configuration(self):
        config = {
            'camera_id': self.camera_id,
            'points': [
                {
                    'name': name,
                    'coordinates': {'x': x, 'y': y}
                }
                for name, (x, y) in self.points
            ]
        }
        
        filename = f'camera_{self.camera_id}_config.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"\n配置已保存到 {filename}")

def main():
    parser = argparse.ArgumentParser(description='摄像头坐标标定工具')
    parser.add_argument('camera_id', help='摄像头ID')
    parser.add_argument('--source', help='视频源（摄像头索引或视频文件路径）', default=0)
    args = parser.parse_args()
    
    # 尝试将source转换为整数（用于摄像头），如果失败则作为文件路径处理
    try:
        video_source = int(args.source)
    except ValueError:
        video_source = args.source
    
    try:
        tool = CoordinateCalibrationTool(args.camera_id)
        tool.calibrate(video_source)
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main() 