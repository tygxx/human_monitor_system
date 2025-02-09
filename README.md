# 商场人员行为监控系统

## 项目简介
基于计算机视觉的商场人员行为监控系统，实现保安巡逻监控、人脸识别和异常行为检测等功能。

## 环境配置

### 1. 创建并激活环境
```bash
# 创建 conda 环境
conda create -n human_monitor_system python=3.10
conda activate human_monitor_system

# pip去安装这两个依赖时，很容易因环境问题失败，所以使用conda安装
conda install -c conda-forge dlib
conda install -c conda-forge face_recognition

# 安装依赖
# pip install -r requirements.txt
# 安装基础依赖
pip install opencv-python numpy mediapipe

# 安装 PyTorch (根据您的系统选择 CPU 或 CUDA 版本)
pip install torch torchvision

# 安装其他工具库
pip install python-dateutil PyYAML mysql-connector-python

# 安装开发工具（可选）
pip install pytest black pylint
```

## 功能模块

### 1. 保安巡逻监控
- 多摄像头支持
- 巡逻路线检测
- 实时位置追踪
- 巡逻报告生成

## 开发指南

### 1. 项目结构
```
face_action_monitor/
├── app/                    # 应用程序主目录
│   ├── mall_monitor/      # 商场监控模块
│   │   ├── security_patrol/   # 保安巡逻模块
│   │   ├── common/           # 公共组件
│   │   └── tools/           # 工具脚本
│   ├── utils/             # 工具类
│   └── config/            # 配置文件
├── data/                  # 数据目录
│   ├── models/           # 模型文件
│   ├── samples/          # 样本数据
│   └── test_videos/      # 测试视频
└── logs/                 # 日志文件
```

### 2. 本地测试流程

#### 2.1 准备测试视频
1. 获取测试视频文件
2. 放入 `data/test_videos/` 目录：
    - gate_patrol.mp4 (大门摄像头)
    - west_patrol.mp4 (西侧摄像头)

#### 2.2 配置巡逻点位
```bash
# 配置大门摄像头巡逻点位
python -m app.mall_monitor.tools.coordinate_calibration CAM_1F_GATE --source data/test_videos/gate_patrol.mp4

# 配置西侧摄像头巡逻点位
python -m app.mall_monitor.tools.coordinate_calibration CAM_1F_WEST --source data/test_videos/west_patrol.mp4
```

标定工具使用说明：
1. 按 'n' 键：输入新的巡逻点位名称
2. 鼠标左键：点击画面标记坐标
3. 按 'q' 键：保存并退出

#### 2.3 运行测试程序
```bash
python -m app.mall_monitor.tools.test_patrol_detection
```

### 3. 配置文件说明
- 系统配置：`app/config/settings.py`
- 摄像头配置：`camera_*_config.json`

### 4. 日志系统
- 位置：`logs/` 目录
- 格式：按日期自动分割
- 输出：同时输出到控制台和文件

## 待开发功能
- [ ] 人脸识别模块
- [ ] 异常行为检测
- [ ] 实时告警系统
- [ ] 数据统计报表

## 注意事项
1. 确保测试视频分辨率与配置匹配
2. 坐标配置文件保存在项目根目录
3. 测试程序按 'q' 键退出
