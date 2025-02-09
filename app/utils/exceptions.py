class FaceActionMonitorException(Exception):
    """基础异常类"""
    pass

class VideoProcessError(FaceActionMonitorException):
    """视频处理相关错误"""
    pass

class FaceDetectionError(FaceActionMonitorException):
    """人脸检测相关错误"""
    pass

class ActionRecognitionError(FaceActionMonitorException):
    """动作识别相关错误"""
    pass

class ConfigError(FaceActionMonitorException):
    """配置相关错误"""
    pass 