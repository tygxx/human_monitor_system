-- 创建数据库
CREATE DATABASE IF NOT EXISTS mall_monitor DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mall_monitor;

-- 摄像头配置表
CREATE TABLE cameras (
    camera_id VARCHAR(20) PRIMARY KEY COMMENT '摄像头ID',
    name VARCHAR(50) NOT NULL COMMENT '摄像头名称',
    location VARCHAR(100) COMMENT '安装位置',
    resolution_width INT COMMENT '分辨率宽',
    resolution_height INT COMMENT '分辨率高',
    fps INT DEFAULT 30 COMMENT '帧率',
    data_status TINYINT(1) DEFAULT 1 COMMENT '数据状态：1-有效 0-删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) COMMENT='摄像头配置表';

-- 保安信息表
CREATE TABLE guards (
    guard_id VARCHAR(20) PRIMARY KEY COMMENT '保安ID',
    name VARCHAR(50) NOT NULL COMMENT '姓名',
    gender ENUM('male', 'female') COMMENT '性别',
    phone VARCHAR(20) COMMENT '联系电话',
    face_image MEDIUMBLOB COMMENT '人脸照片',
    face_feature BLOB COMMENT '人脸特征向量',
    data_status TINYINT(1) DEFAULT 1 COMMENT '数据状态：1-有效 0-删除',
    register_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) COMMENT='保安信息表';

-- 巡逻记录表
CREATE TABLE patrol_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    guard_id VARCHAR(20) NOT NULL COMMENT '保安ID',
    arrival_time DATETIME NOT NULL COMMENT '到达时间',
    data_status TINYINT(1) DEFAULT 1 COMMENT '数据状态：1-有效 0-删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guard_id) REFERENCES guards(guard_id)
) COMMENT='巡逻记录表';

-- 添加索引
ALTER TABLE patrol_records ADD INDEX idx_guard_point (guard_id, point_id);

-- 插入测试数据：摄像头
INSERT INTO cameras (camera_id, name, location, resolution_width, resolution_height, fps) VALUES
('CAM_1F_GATE', '一楼大门', '一楼大门入口', 1099, 844, 30),
('CAM_1F_WEST', '一楼西侧', '一楼西侧走廊', 855, 1452, 30);
