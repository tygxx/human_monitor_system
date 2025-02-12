import argparse
import sys
from pathlib import Path

from app.mall_monitor.security_patrol.guard_registration import GuardRegistration
from app.utils.logger import logger

"""
# 从摄像头录入
python -m app.mall_monitor.tools.register_guard --mode camera

# 从照片录入
python -m app.mall_monitor.tools.register_guard --mode image --image-path /path/to/photo.jpg

"""

def main():
    parser = argparse.ArgumentParser(description='保安信息录入工具')
    parser.add_argument('--mode', choices=['camera', 'image'], required=True,
                      help='录入模式：camera-摄像头录入，image-照片录入')
    parser.add_argument('--image-path', help='照片路径（仅照片录入模式需要）')
    
    args = parser.parse_args()
    
    # 创建注册器实例
    registrator = GuardRegistration()
    
    try:
        # 获取基本信息
        print("\n=== 保安信息录入 ===")
        guard_id = input("请输入保安ID: ").strip()
        name = input("请输入姓名: ").strip()
        gender = input("请输入性别 (male/female): ").strip().lower()
        phone = input("请输入联系电话: ").strip()
        
        # 验证输入
        if not all([guard_id, name, gender, phone]):
            print("错误：所有字段都必须填写")
            sys.exit(1)
        if gender not in ['male', 'female']:
            print("错误：性别必须是 male 或 female")
            sys.exit(1)
            
        success = False
        if args.mode == 'camera':
            print("\n请看向摄像头，确保光线充足...")
            print("按空格键拍照，按ESC取消")
            success = registrator.register_from_camera(guard_id, name, gender, phone)
        else:  # image mode
            if not args.image_path:
                print("错误：照片录入模式需要指定照片路径")
                sys.exit(1)
            
            image_path = Path(args.image_path)
            if not image_path.exists():
                print(f"错误：找不到照片文件 {args.image_path}")
                sys.exit(1)
                
            success = registrator.register_from_image(
                guard_id, name, gender, phone, str(image_path)
            )
        
        if success:
            print(f"\n成功录入保安 {name} 的信息！")
        else:
            print("\n录入失败，请重试")
            
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        logger.error(f"录入过程发生错误: {str(e)}")
        print(f"\n发生错误: {str(e)}")

if __name__ == '__main__':
    main() 