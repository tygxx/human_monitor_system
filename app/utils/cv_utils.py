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

def put_chinese_text(img: np.ndarray, text: str, position: tuple, 
                    font_size: int = 24, color: tuple = (0, 255, 0)) -> np.ndarray:
    """在OpenCV图像上绘制中文文本
    
    Args:
        img: OpenCV图像(numpy.ndarray)
        text: 要绘制的文本
        position: 文本位置，格式为(x, y)
        font_size: 字体大小，默认24
        color: 字体颜色，格式为(B,G,R)，默认绿色
        
    Returns:
        添加文本后的图像
    """
    # 字体文件路径
    font_path = Path(BASE_DIR) / "resources" / "fonts" / "wqy-microhei.ttc"
    
    if not font_path.exists():
        raise FileNotFoundError(f"找不到字体文件: {font_path}")
    
    # OpenCV图像转PIL图像
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    # 创建绘图对象
    draw = ImageDraw.Draw(pil_img)
    
    # 加载字体
    font = ImageFont.truetype(str(font_path), font_size)
    
    # 绘制文本
    draw.text(position, text, font=font, fill=color[::-1])  # PIL颜色顺序是RGB
    
    # PIL图像转回OpenCV图像
    cv2_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    return cv2_img

def draw_face_box(img: np.ndarray, face_location: tuple, text: str, 
                  box_color: tuple = (0, 255, 0), box_thickness: int = 2,
                  font_size: int = 24) -> np.ndarray:
    """在图像上绘制人脸框和文本
    
    Args:
        img: OpenCV图像
        face_location: 人脸位置(top, right, bottom, left)
        text: 要显示的文本
        box_color: 框的颜色(B,G,R)
        box_thickness: 框的粗细
        font_size: 字体大小
        
    Returns:
        处理后的图像
    """
    top, right, bottom, left = face_location
    
    # 绘制人脸框
    cv2.rectangle(img, (left, top), (right, bottom), box_color, box_thickness)
    
    # 计算文本位置（框的上方）
    text_x = left
    text_y = max(0, top - font_size - 5)  # 确保不会超出图像上边界
    
    # 绘制中文文本
    img = put_chinese_text(
        img, 
        text, 
        (text_x, text_y),
        font_size=font_size,
        color=box_color
    )
    
    return img 