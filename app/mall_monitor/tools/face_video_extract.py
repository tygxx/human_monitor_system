import sys
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import argparse

from app.mall_monitor.security_patrol.face_video_extractor import FaceScreenshotExtractor
from app.utils.logger import logger
from app.config.settings import DATA_DIR

"""
人脸截图提取工具

使用方式：
1. 图形界面模式：
   python -m app.mall_monitor.tools.face_video_extract

2. 命令行模式：
   python -m app.mall_monitor.tools.face_video_extract --face-image path/to/face.jpg --video path/to/video.mp4
"""

def select_file(title: str, filetypes: list) -> str:
    """使用文件选择对话框选择文件"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=filetypes
    )
    
    return file_path

def process_video(face_image_path: str, video_path: str, show_process: bool = False) -> None:
    """处理视频并提取人脸截图"""
    try:
        # 验证文件路径
        if not os.path.exists(face_image_path):
            raise FileNotFoundError(f"找不到人脸图片: {face_image_path}")
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"找不到视频文件: {video_path}")
            
        # 处理视频
        extractor = FaceScreenshotExtractor()
        screenshot_paths = extractor.process_video(
            face_image_path=face_image_path,
            video_path=video_path,
            show_process=show_process
        )
        
        # 显示结果
        if screenshot_paths:
            success_msg = f"处理完成！已保存 {len(screenshot_paths)} 张截图到 {extractor.output_dir} 目录"
            logger.info(success_msg)
            print(success_msg)
        else:
            warning_msg = "在视频中未找到匹配的人脸"
            logger.warning(warning_msg)
            print(warning_msg)
                
    except Exception as e:
        error_msg = f"处理过程中发生错误: {str(e)}"
        logger.error(error_msg)
        print(f"错误: {error_msg}", file=sys.stderr)
        raise

def gui_mode():
    """图形界面模式"""
    try:
        root = tk.Tk()
        root.withdraw()
        
        # 1. 选择人脸图片
        logger.info("请选择包含目标人脸的图片文件...")
        face_image_path = filedialog.askopenfilename(
            title="选择人脸图片",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png"),
                ("所有文件", "*.*")
            ]
        )
        
        if not face_image_path:
            logger.error("未选择人脸图片，退出程序")
            return
            
        # 2. 选择视频文件
        logger.info("请选择要分析的视频文件...")
        video_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.avi *.mkv"),
                ("所有文件", "*.*")
            ]
        )
        
        if not video_path:
            logger.error("未选择视频文件，退出程序")
            return
            
        # 3. 询问是否显示处理过程
        show_process = messagebox.askyesno(
            "选项",
            "是否显示视频处理过程？\n(显示处理过程可能会降低处理速度)"
        )
        
        root.destroy()  # 关闭所有窗口
        
        # 4. 处理视频
        process_video(face_image_path, video_path, show_process)
        
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        sys.exit(1)

def cli_mode(args):
    """命令行模式"""
    try:
        # 处理相对路径
        face_image_path = args.face_image
        video_path = args.video
        
        # 如果是相对路径，则相对于对应的默认目录
        if not os.path.isabs(face_image_path):
            face_image_path = os.path.join(DATA_DIR, "face_samples", face_image_path)
        if not os.path.isabs(video_path):
            video_path = os.path.join(DATA_DIR, "test_videos", video_path)
            
        # 处理视频
        process_video(face_image_path, video_path, args.show_process)
        
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        sys.exit(1)

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="人脸截图提取工具")
    parser.add_argument("--face-image", help="人脸图片路径")
    parser.add_argument("--video", help="视频文件路径")
    parser.add_argument("--show-process", action="store_true", help="是否显示处理过程")
    
    args = parser.parse_args()
    
    # 根据参数决定运行模式
    if args.face_image and args.video:
        # 命令行模式
        cli_mode(args)
    else:
        # 图形界面模式
        gui_mode()

if __name__ == "__main__":
    main() 