# 视频处理工具

一个简单而功能强大的视频处理工具，支持视频格式转换和水印去除功能。

## 功能特点

- 视频格式转换
  - 支持多种常见视频格式（MP4, AVI, MKV, MOV, WMV）之间的互相转换
  - 保持原视频质量
  - 实时显示转换进度
  - 可自定义输出目录

- 视频水印去除
  - 可视化水印区域选择
  - 智能水印检测
  - 高质量水印去除
  - 保持视频其他部分清晰度


### 项目结构

```
Video-Conversion/
├── Video-GUI.py # 主程序
├── resources_rc.py # 资源文件
├── create_ico.py # 图标生成脚本
├── requirements.txt # 依赖列表
└── icons/ # 图标资源目录
├── video.svg
└── github.svg
```

## 依赖项

- Python 3.8+
- PySide6
- FFmpeg-python
- OpenCV-Python
- Moviepy
- Numpy

## 使用说明

### 视频格式转换

1. 点击"浏览文件"选择需要转换的视频
2. 从下拉菜单选择目标格式
3. 点击"开始转换"
4. 等待转换完成

### 水印去除

1. 从"工具"菜单选择"去除水印"
2. 选择需要处理的视频文件
3. 点击"选择水印区域"并在预览窗口中框选水印位置
4. 点击"开始处理"
5. 等待处理完成

## 设置

- 在菜单"设置"中可以：
  - 设置默认输出目录



## 安装说明

### 方法一：直接使用

1. 从 [Releases](https://github.com/4KAForever11/Video-Conversion/releases) 下载最新版本的可执行文件
2. 双击运行 `Video-Processing-Tool.exe`

### 方法二：从源码运行

1. 克隆仓库

```bash
git clone https://github.com/4KAForever11/Video-Conversion.git

cd Video-Conversion
```

2. 安装依赖

```bash
pip install -r requirements.txt
``` 

3. 运行 `Video-GUI.py`

```bash
python Video-GUI.py
```

## 注意事项

- 请确保安装了所有依赖项，否则可能会导致程序无法正常运行。
- 请确保安装了FFmpeg，否则可能会导致视频格式转换失败。



## 贡献指南

欢迎提交 Pull Request 或创建 Issue。

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 作者

- [@4KAForever11](https://github.com/4KAForever11)

## 更新日志

### v1.0.0 (2024-12-08)
- 初始版本发布
- 实现基础视频格式转换功能
- 实现水印去除功能
