import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from app.config.settings import BASE_DIR
from app.utils.logger import logger

class TextRenderer:
    _instance = None
    _font = None
    _small_font = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if TextRenderer._font is None:
            self._init_fonts()
    
    def _init_fonts(self):
        """初始化字体"""
        try:
            # 尝试多个字体路径
            font_paths = [
                str(Path(BASE_DIR) / "resources" / "fonts" / "wqy-microhei.ttc"),
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
                "C:\\Windows\\Fonts\\simhei.ttf",
                "/System/Library/Fonts/PingFang.ttc"
            ]
            
            for font_path in font_paths:
                try:
                    if Path(font_path).exists():
                        TextRenderer._font = ImageFont.truetype(font_path, 20)
                        TextRenderer._small_font = ImageFont.truetype(font_path, 16)
                        logger.info(f"成功加载字体: {font_path}")
                        return
                except Exception:
                    continue
            
            logger.warning("未找到可用的中文字体，将使用默认字体")
            TextRenderer._font = ImageFont.load_default()
            TextRenderer._small_font = ImageFont.load_default()
            
        except Exception as e:
            logger.error(f"字体初始化失败: {str(e)}")
            TextRenderer._font = ImageFont.load_default()
            TextRenderer._small_font = ImageFont.load_default()

    def put_text(self, img: np.ndarray, text: str, position: tuple, 
                color: tuple = (0, 255, 0), font_size: str = 'normal') -> np.ndarray:
        """在图片上绘制中文文字
        Args:
            img: OpenCV图像
            text: 要绘制的文字
            position: 文字位置 (x, y)
            color: 文字颜色 (B, G, R)
            font_size: 字体大小 'small' 或 'normal'
        Returns:
            绘制文字后的图像
        """
        try:
            # 转换颜色空间
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            
            # 创建绘图对象
            draw = ImageDraw.Draw(pil_img)
            
            # 选择字体大小
            font = self._small_font if font_size == 'small' else self._font
            
            # 绘制文字
            draw.text(position, text, font=font, fill=color[::-1])  # PIL颜色顺序为RGB
            
            # 转回OpenCV格式
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            logger.error(f"文字绘制失败: {str(e)}")
            # 如果失败则使用OpenCV默认方式
            return cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX,
                             0.5 if font_size == 'small' else 0.7, color, 1)

def put_chinese_text(img, text, position, color=(0, 255, 0), font_size='normal'):
    """便捷方法用于绘制中文文字"""
    return TextRenderer.get_instance().put_text(img, text, position, color, font_size) 