import sys
from pathlib import Path
from app.utils.db_utils import execute_query
from app.mall_monitor.security_patrol.face_monitor import FaceMonitor
from app.utils.logger import logger

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
        print("3. 本地视频文件 (暂未实现)")
        
        source_type = input("\n请输入选项 (1-3): ").strip()
        
        if source_type == "1":
            # 本地摄像头模式
            camera_index = int(input("\n请输入本地摄像头索引 (默认0): ").strip() or "0")
            
            monitor = FaceMonitor()
            print("\n开始监控...")
            print("按 'q' 键退出")
            
            monitor.start_local_camera_monitor(
                camera_id=camera_info['camera_id'],
                camera_index=camera_index
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