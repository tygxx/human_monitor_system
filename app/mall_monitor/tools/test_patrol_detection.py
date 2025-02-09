import cv2
import time
from app.mall_monitor.common.video_processor import VideoProcessor
from app.mall_monitor.security_patrol.patrol_detector import PatrolDetector
from app.mall_monitor.security_patrol.patrol_analyzer import PatrolAnalyzer
from app.utils.logger import logger

def run_test():
    video_processor = VideoProcessor()
    patrol_detector = PatrolDetector()
    patrol_analyzer = PatrolAnalyzer()

    try:
        while True:
            # 处理每个摄像头的画面
            for camera_id in video_processor.video_captures.keys():
                result = video_processor.get_frame(camera_id)
                if result is None:
                    continue

                ret, frame = result
                
                # 处理画面
                processed_frame = patrol_detector.process_frame(frame)
                
                # 显示处理后的画面
                cv2.imshow(f"Camera {camera_id}", processed_frame)

            # 按'q'退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # 模拟实际帧率
            time.sleep(1/30)  # 30 FPS

    except KeyboardInterrupt:
        logger.info("测试程序被用户中断")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
    finally:
        video_processor.release()

if __name__ == "__main__":
    run_test() 