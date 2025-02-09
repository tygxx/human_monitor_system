import cv2
import numpy as np
import os
from pathlib import Path
from typing import List
from app.mall_monitor.security_patrol.guard_manager import GuardManager
from app.utils.logger import logger

def capture_face_image() -> np.ndarray:
    """通过摄像头拍摄人脸照片"""
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise ValueError("无法打开摄像头")
            
        print("\n请按空格键拍照")
        print("按 'q' 退出\n")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
                
            cv2.imshow("Camera", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                return None
            elif key == ord(' '):
                return frame.copy()
                
    except Exception as e:
        logger.error(f"拍摄照片时发生错误: {str(e)}")
        return None
    finally:
        cap.release()
        cv2.destroyAllWindows()

def load_face_images(image_dir: str) -> List[np.ndarray]:
    """从指定目录加载人脸照片"""
    face_images = []
    supported_formats = {'.jpg', '.jpeg', '.png', '.bmp'}
    
    try:
        image_path = Path(image_dir)
        if not image_path.exists():
            raise ValueError(f"目录不存在: {image_dir}")
            
        # 获取所有图片文件
        image_files = [f for f in image_path.iterdir() 
                      if f.suffix.lower() in supported_formats]
        
        if not image_files:
            raise ValueError(f"目录中没有支持的图片文件: {image_dir}")
            
        print(f"\n在目录中找到 {len(image_files)} 个图片文件")
        
        # 加载图片
        for img_file in image_files[:5]:  # 最多使用5张照片
            image = cv2.imread(str(img_file))
            if image is not None:
                face_images.append(image)
                print(f"已加载: {img_file.name}")
            
    except Exception as e:
        logger.error(f"加载照片时发生错误: {str(e)}")
        
    return face_images

def register_new_guard():
    """交互式保安注册工具"""
    try:
        print("\n=== 保安注册系统 ===")
        name = input("请输入保安姓名: ")
        gender = input("请输入性别 (male/female): ")
        phone = input("请输入联系电话: ")
        
        print("\n请选择注册方式：")
        print("1. 通过摄像头拍摄照片")
        print("2. 使用已有照片")
        choice = input("请输入选择 (1/2): ")
        
        face_image = None
        if choice == "1":
            face_image = capture_face_image()
        elif choice == "2":
            image_path = input("\n请输入照片路径: ")
            face_image = cv2.imread(image_path)
        else:
            print("无效的选择")
            return
        
        if face_image is None:
            print("未获取到有效的照片，注册失败")
            return
            
        # 显示预览
        print("\n预览照片... 按任意键继续，'q' 取消注册")
        cv2.imshow("Preview", face_image)
        
        key = cv2.waitKey(0) & 0xFF
        cv2.destroyAllWindows()
        
        if key == ord('q'):
            print("已取消注册")
            return
            
        # 注册保安
        guard_manager = GuardManager()
        guard_id = guard_manager.register_guard(
            name=name,
            face_image=face_image,
            gender=gender if gender in ['male', 'female'] else None,
            phone=phone
        )
        print(f"\n注册成功！保安ID: {guard_id}")
        
    except Exception as e:
        logger.error(f"注册过程中发生错误: {str(e)}")
        print("注册失败，请查看日志了解详细信息")

def main():
    while True:
        register_new_guard()
        
        choice = input("\n是否继续注册下一个保安？(y/n): ")
        if choice.lower() != 'y':
            break
    
    print("\n注册程序已结束")

if __name__ == "__main__":
    main() 