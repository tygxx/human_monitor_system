import sys
from pathlib import Path
from app.utils.db_utils import execute_query
from app.mall_monitor.security_patrol.face_monitor import FaceMonitor
from app.utils.logger import logger
from app.config.settings import DATA_DIR

"""
# 人脸识别测试
python -m app.mall_monitor.tools.face_recognition_test
"""

def get_camera_info(camera_id: str) -> dict:
    """查询摄像头信息"""
    sql = """
        SELECT camera_id, name, location, resolution_width, resolution_height, fps 
        FROM cameras 
        WHERE camera_id = %s AND data_status = 1
    """
    result = execute_query(sql, (camera_id,))
    return result[0] if result else None

def main():
    try:
        print("\n=== 人脸识别测试 ===")
        
        # 1. 输入摄像头ID
        camera_id = input("请输入摄像头ID: ").strip()
        if not camera_id:
            print("错误：摄像头ID不能为空")
            sys.exit(1)
            
        # 2. 查询摄像头信息
        camera_info = get_camera_info(camera_id)
        if not camera_info:
            print(f"错误：未找到摄像头 {camera_id} 或摄像头已禁用")
            sys.exit(1)
            
        print(f"\n找到摄像头: {camera_info['name']} ({camera_info['location']})")
        
        # 3. 选择视频源类型
        print("\n请选择视频源类型：")
        print("1. 本地摄像头")
        print("2. 网络摄像头 (暂未实现)")
        print("3. 本地视频文件")
        
        source_type = input("\n请输入选项 (1-3): ").strip()
        
        monitor = FaceMonitor()
        
        if source_type == "1":
            # 本地摄像头模式
            camera_index = int(input("\n请输入本地摄像头索引 (默认0): ").strip() or "0")
            
            print("\n开始监控...")
            print("按 'q' 键退出")
            
            monitor.start_local_camera_monitor(
                camera_id=camera_info['camera_id'],
                camera_index=camera_index
            )
            
        elif source_type == "3":
            # 本地视频文件模式
            print("\n请选择视频文件：")
            print(f"默认视频目录: {DATA_DIR}/test_videos/")
            
            # 确保视频目录存在
            video_dir = Path(DATA_DIR) / "test_videos"
            video_dir.mkdir(parents=True, exist_ok=True)
            
            video_path = input("\n请输入视频文件路径: ").strip()
            if not video_path:
                print("错误：视频文件路径不能为空")
                sys.exit(1)
                
            # 如果输入的不是绝对路径，则假设是相对于test_videos目录的路径
            if not Path(video_path).is_absolute():
                video_path = video_dir / video_path
                
            if not Path(video_path).exists():
                print(f"错误：找不到视频文件 {video_path}")
                sys.exit(1)
                
            print("\n开始处理视频...")
            print("按 'q' 键退出，空格键暂停")
            
            monitor.start_video_file_monitor(
                camera_id=camera_info['camera_id'],
                video_path=str(video_path)
            )
            
        else:
            print("该功能暂未实现")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        print(f"\n发生错误: {str(e)}")

if __name__ == '__main__':
    main() 