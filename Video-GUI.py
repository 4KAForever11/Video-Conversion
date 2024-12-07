import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QComboBox, QProgressBar, QFileDialog, QMessageBox,
                             QMenuBar, QMenu, QDialog, QFormLayout, QStyle,
                             QGroupBox, QDialogButtonBox)
from PySide6.QtCore import QThread, Signal, QSettings, Qt, QSize, QUrl
from PySide6.QtGui import QAction, QIcon, QDesktopServices
import ffmpeg
import cv2
import numpy as np
from moviepy.editor import VideoFileClip
import resources_rc  # 这个文件会由 pyside6-rcc 生成

# 获取当前文件所在目录的绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # 输出目录设置组
        output_group = QGroupBox("输出设置")
        group_layout = QFormLayout()
        
        self.output_path = QLineEdit()
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_output_dir)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.output_path)
        path_layout.addWidget(browse_btn)
        
        group_layout.addRow("默认输出目录:", path_layout)
        output_group.setLayout(group_layout)
        layout.addWidget(output_group)
        
        # 确定和取消按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # 加载已保存的设置
        self.settings = QSettings('VideoConverter', 'Settings')
        self.output_path.setText(self.settings.value('output_dir', ''))
        
    def browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_path.setText(dir_path)
            
    def save_settings(self):
        self.settings.setValue('output_dir', self.output_path.text())

class ConvertThread(QThread):
    progress = Signal(float)
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, input_file, output_file):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        
    def get_format_settings(self, output_file):
        """根据输出文件格式返回适当的编码器设置"""
        format_ext = output_file.lower().split('.')[-1]
        settings = {
            'mp4': {
                'vcodec': 'libx264',
                'acodec': 'aac',
                'strict': 'experimental'
            },
            'avi': {
                'vcodec': 'libx264',
                'acodec': 'mp3',
                'strict': 'experimental'
            },
            'mkv': {
                'vcodec': 'libx264',
                'acodec': 'aac',
                'strict': 'experimental'
            },
            'mov': {
                'vcodec': 'libx264',
                'acodec': 'aac',
                'strict': 'experimental'
            },
            'wmv': {
                'vcodec': 'msmpeg4',
                'acodec': 'wmav2',
                'strict': 'experimental'
            }
        }
        return settings.get(format_ext, {})
        
    def run(self):
        try:
            # 获取视频总时长
            probe = ffmpeg.probe(self.input_file)
            total_duration = float(probe['streams'][0]['duration'])
            
            # 获取输出格式的编码器设置
            format_settings = self.get_format_settings(self.output_file)
            
            # 设置ffmpeg命令
            stream = (
                ffmpeg
                .input(self.input_file)
                .output(self.output_file,
                       **format_settings,
                       **{
                           'loglevel': 'info',
                           'stats': None,
                           'b:v': '2500k',
                           'b:a': '192k',
                           'copyts': None,
                           'vsync': 0,
                       })
                .overwrite_output()
            )
            
            # 获取完整的ffmpeg命令用于调试
            cmd = ffmpeg.compile(stream)
            print(f"开始转换: {' '.join(cmd)}")
            
            process = stream.run_async(pipe_stdout=True, pipe_stderr=True)
            
            # 收集错误输出
            error_output = []
            last_progress = 0
            
            # 监控转换进度
            while process.poll() is None:
                line = process.stderr.readline().decode('utf8', errors='replace')
                if line:
                    print(f"FFmpeg output: {line.strip()}")
                    error_output.append(line)
                    
                    # 尝试从不同格式的时间信息中提取进度
                    try:
                        if "time=" in line:
                            # 提取时间信息
                            time_str = line.split("time=")[1].split()[0]
                            if time_str != 'N/A':
                                # 将时间转换为秒
                                if ":" in time_str:
                                    h, m, s = map(float, time_str.split(':'))
                                    current_seconds = h * 3600 + m * 60 + s
                                else:
                                    current_seconds = float(time_str)
                                
                                # 计算进度百分比
                                progress = min((current_seconds / total_duration) * 100, 99)
                                if progress > last_progress:
                                    self.progress.emit(progress)
                                    last_progress = progress
                                    print(f"转换进度: {progress:.1f}%")
                    except Exception as e:
                        print(f"Progress parsing error: {e}")
                        continue
            
            process.wait()
            
            if process.returncode != 0:
                error_msg = ''.join(error_output)
                print(f"转换失败: {error_msg}")
                raise Exception(f"转换失败。FFmpeg输出:\n{error_msg}")
            
            print("转换完成")
            self.progress.emit(100)
            self.finished.emit()
            
        except Exception as e:
            print(f"转换错误: {str(e)}")
            self.error.emit(str(e))
        finally:
            # 确保在线程结束时关闭所有资源
            if 'process' in locals():
                try:
                    process.kill()
                except:
                    pass

    def __del__(self):
        self.wait()

class WatermarkRemoverThread(QThread):
    progress = Signal(float)
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, input_file, output_file, watermark_mask=None):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.watermark_mask = watermark_mask
        
    def run(self):
        try:
            video_clip = VideoFileClip(self.input_file)
            total_frames = int(video_clip.duration * video_clip.fps)
            current_frame = 0
            
            def process_frame(frame):
                nonlocal current_frame
                current_frame += 1
                # 只在未达到100%时发送进度信号
                if current_frame < total_frames:
                    self.progress.emit((current_frame / total_frames) * 100)
                return self.remove_watermark(frame)
            
            processed_video = video_clip.fl_image(process_frame)
            processed_video.write_videofile(
                self.output_file,
                audio_codec='aac',
                audio_bitrate='192k',
                preset='slow',
                threads=4
            )
            
            video_clip.close()
            processed_video.close()
            
            # 最后一次进度更新和完成信号一起发送
            self.progress.emit(100)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            
    def remove_watermark(self, frame):
        """改进的水印去除方法"""
        frame_float = frame.astype(np.float32) / 255.0
        
        mask_region = self.watermark_mask > 0
        
        kernel = np.ones((5,5), np.uint8)
        expanded_mask = cv2.dilate(self.watermark_mask, kernel, iterations=2)
        sample_region = expanded_mask > 0
        
        for c in range(3):
            channel = frame_float[:,:,c]
            
            surrounding_pixels = channel[sample_region & ~mask_region]
            if len(surrounding_pixels) > 0:
                mean_value = np.mean(surrounding_pixels)
                std_value = np.std(surrounding_pixels)
                
                texture = np.random.normal(mean_value, std_value, channel[mask_region].shape)
                
                channel[mask_region] = np.clip(texture, 0, 1)
        
        result = cv2.inpaint(
            (frame_float * 255).astype(np.uint8),
            self.watermark_mask,
            3,
            cv2.INPAINT_TELEA
        )
        
        return np.clip(result, 0, 255).astype(np.uint8)

class VideoConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频处理工具")
        self.setMinimumWidth(600)
        self.settings = QSettings('VideoConverter', 'Settings')
        
        # 使用绝对路径加载图标
        icon_path = os.path.join(CURRENT_DIR, "icons", "video.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 文件选择组
        file_group = QGroupBox("输入文件")
        file_layout = QHBoxLayout()
        
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("请选择要转换的视频文件...")
        
        self.browse_button = QPushButton("浏览文件")
        self.browse_button.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.browse_button.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.browse_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 转换设置组
        convert_group = QGroupBox("转换设置")
        convert_layout = QHBoxLayout()
        
        self.format_label = QLabel("输出格式:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "avi", "mkv", "mov", "wmv"])
        
        convert_layout.addWidget(self.format_label)
        convert_layout.addWidget(self.format_combo)
        convert_layout.addStretch()
        convert_group.setLayout(convert_layout)
        layout.addWidget(convert_group)
        
        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # 转换按钮
        self.convert_button = QPushButton("开始转换")
        self.convert_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.convert_button.clicked.connect(self.convert)
        self.convert_button.setMinimumHeight(40)
        layout.addWidget(self.convert_button)
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 设置菜单项
        settings_action = QAction(QIcon(self.style().standardIcon(QStyle.SP_FileDialogListView)), "设置", self)
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)
        
        # 退出菜单项
        exit_action = QAction(QIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton)), "退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        # 水印去除菜单项
        watermark_action = QAction(QIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton)), "去除水印", self)
        watermark_action.triggered.connect(self.show_watermark_remover)
        tools_menu.addAction(watermark_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        # 关于菜单项
        about_action = QAction(QIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation)), "关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            dialog.save_settings()
            
    def show_about(self):
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("关于")
        about_dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(about_dialog)
        
        # 添加标题和版本信息
        title_label = QLabel("视频处理工具 v1.0")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 添加描述
        desc_label = QLabel("一个简单的视频处理工具，支持格式转换和去除水印功能")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 添加作者信息
        author_label = QLabel("作者: 4KAForever11")
        layout.addWidget(author_label)
        
        # 添加GitHub按钮
        github_button = QPushButton("GitHub")
        github_button.setIcon(QIcon(":/icons/github.svg"))
        github_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/4KAForever11")))
        github_button.setMinimumHeight(40)
        github_button.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手型光标
        layout.addWidget(github_button)
        
        # 添加确定按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(about_dialog.accept)
        layout.addWidget(button_box)
        
        about_dialog.exec()
        
    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv)"
        )
        if file_name:
            self.file_input.setText(file_name)
            
    def get_output_path(self, input_file, format):
        # 首先检查设置中的输出目录
        output_dir = self.settings.value('output_dir', '')
        if not output_dir:
            # 如果没有设置输出目录，让用户选择保存位置
            file_name = os.path.basename(input_file)
            base_name = os.path.splitext(file_name)[0]
            output_file, _ = QFileDialog.getSaveFileName(
                self,
                "保存转换后的文件",
                f"{base_name}.{format}",
                f"视频文件 (*.{format})"
            )
            return output_file if output_file else None
        else:
            # 使用设置的输出目录
            file_name = os.path.basename(input_file)
            base_name = os.path.splitext(file_name)[0]
            return os.path.join(output_dir, f"{base_name}.{format}")
            
    def convert(self):
        input_file = self.file_input.text()
        if not input_file:
            QMessageBox.warning(self, "警告", "请先选择输入文件！")
            return
            
        output_format = self.format_combo.currentText()
        output_file = self.get_output_path(input_file, output_format)
        
        if not output_file:
            return
            
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.convert_button.setEnabled(False)
        
        # 创建并启动转换线程
        self.convert_thread = ConvertThread(input_file, output_file)
        self.convert_thread.progress.connect(self.update_progress)
        self.convert_thread.finished.connect(self.conversion_finished)
        self.convert_thread.error.connect(self.conversion_error)
        self.convert_thread.start()
        
    def update_progress(self, value):
        if value <= 100:  # 确保进度值不超过100
            self.progress_bar.setValue(int(value))
        
    def conversion_finished(self):
        self.progress_bar.hide()  # 完成时直接隐藏进度条
        self.convert_button.setEnabled(True)
        QMessageBox.information(self, "成功", "视频转换完成！")
        
    def conversion_error(self, error_msg):
        self.progress_bar.hide()
        self.convert_button.setEnabled(True)
        QMessageBox.critical(self, "错误", f"转换失败: {error_msg}")

    def show_watermark_remover(self):
        self.watermark_remover = WatermarkRemover(self)
        self.watermark_remover.show()

    def closeEvent(self, event):
        # 确保在关闭窗口时停止所有正在运行的线程
        if hasattr(self, 'convert_thread') and self.convert_thread.isRunning():
            self.convert_thread.terminate()
            self.convert_thread.wait()
        event.accept()

class WatermarkRemover(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("视频水印去除")
        self.setMinimumWidth(600)
        self.watermark_mask = None
        self.settings = QSettings('VideoConverter', 'Settings')
        
        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 文件选择组
        file_group = QGroupBox("输入文件")
        file_layout = QHBoxLayout()
        
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("请选择要处理的视频文件...")
        
        self.browse_button = QPushButton("浏览文件")
        self.browse_button.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.browse_button.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.browse_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 水印选择按钮
        self.select_watermark_button = QPushButton("选择水印区域")
        self.select_watermark_button.clicked.connect(self.select_watermark)
        layout.addWidget(self.select_watermark_button)
        
        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # 处理按钮
        self.process_button = QPushButton("开始处理")
        self.process_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.process_button.clicked.connect(self.process_video)
        self.process_button.setMinimumHeight(40)
        layout.addWidget(self.process_button)
        
    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv)"
        )
        if file_name:
            self.file_input.setText(file_name)
            
    def select_watermark(self):
        input_file = self.file_input.text()
        if not input_file:
            QMessageBox.warning(self, "警告", "请先选择输入文件！")
            return
            
        try:
            video_clip = VideoFileClip(input_file)
            frame = self.get_first_valid_frame(video_clip)
            
            # 将视频帧调整为720p显示
            display_height = 720
            scale_factor = display_height / frame.shape[0]
            display_width = int(frame.shape[1] * scale_factor)
            display_frame = cv2.resize(frame, (display_width, display_height))
            
            # 修改这部分，使用英文显示
            instructions = "Select the watermark area and press SPACE or ENTER"
            font = cv2.FONT_HERSHEY_SIMPLEX
            # 添加黑色背景以提高文字可读性
            cv2.rectangle(display_frame, (5, 5), (600, 40), (0, 0, 0), -1)
            cv2.putText(display_frame, instructions, (10, 30), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            
            # 设置窗口名称为英文
            cv2.namedWindow("Select Watermark Area")
            r = cv2.selectROI("Select Watermark Area", display_frame, False)
            cv2.destroyAllWindows()
            
            r_original = (
                int(r[0] / scale_factor), 
                int(r[1] / scale_factor), 
                int(r[2] / scale_factor), 
                int(r[3] / scale_factor)
            )
            
            self.watermark_mask = self.generate_watermark_mask(video_clip, r_original)
            video_clip.close()
            
            QMessageBox.information(self, "成功", "水���区域选择完成！")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"选择水印区域时出错: {str(e)}")
            video_clip.close()
            
    def get_first_valid_frame(self, video_clip, threshold=10, num_frames=10):
        total_frames = int(video_clip.fps * video_clip.duration)
        frame_indices = [int(i * total_frames / num_frames) for i in range(num_frames)]
        
        for idx in frame_indices:
            frame = video_clip.get_frame(idx / video_clip.fps)
            if frame.mean() > threshold:
                return frame
        
        return video_clip.get_frame(0)
        
    def detect_watermark_adaptive(self, frame, roi):
        roi_frame = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]
        gray_frame = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        _, binary_frame = cv2.threshold(gray_frame, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        mask = np.zeros_like(frame[:, :, 0], dtype=np.uint8)
        mask[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]] = binary_frame
        
        return mask
        
    def generate_watermark_mask(self, video_clip, roi, num_frames=10, min_frame_count=7):
        total_frames = int(video_clip.duration * video_clip.fps)
        frame_indices = [int(i * total_frames / num_frames) for i in range(num_frames)]
        
        frames = [video_clip.get_frame(idx / video_clip.fps) for idx in frame_indices]
        masks = [self.detect_watermark_adaptive(frame, roi) for frame in frames]
        
        final_mask = sum((mask == 255).astype(np.uint8) for mask in masks)
        final_mask = np.where(final_mask >= min_frame_count, 255, 0).astype(np.uint8)
        
        kernel = np.ones((5, 5), np.uint8)
        return cv2.dilate(final_mask, kernel)
        
    def get_output_path(self, input_file):
        # 首先检查设置中的输出目录
        output_dir = self.settings.value('output_dir', '')
        if not output_dir:
            # 如果没有设置输出目录，让用户选择保存位置
            file_name = os.path.basename(input_file)
            base_name = os.path.splitext(file_name)[0]
            output_file, _ = QFileDialog.getSaveFileName(
                self,
                "保存处理后的视频",
                f"{base_name}_无水印.mp4",
                "视频文件 (*.mp4)"
            )
            return output_file if output_file else None
        else:
            # 使用设置的输出目录
            file_name = os.path.basename(input_file)
            base_name = os.path.splitext(file_name)[0]
            return os.path.join(output_dir, f"{base_name}_无水印.mp4")
        
    def process_video(self):
        if self.watermark_mask is None:
            QMessageBox.warning(self, "警告", "请先选择水印区域！")
            return
        
        input_file = self.file_input.text()
        if not input_file:
            QMessageBox.warning(self, "警告", "请选择输入文件！")
            return
            
        # 使用新的输出路径获取方法
        output_file = self.get_output_path(input_file)
        
        if not output_file:
            return
            
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.process_button.setEnabled(False)
        
        # 创建并启动处理线程
        self.process_thread = WatermarkRemoverThread(input_file, output_file, self.watermark_mask)
        self.process_thread.progress.connect(self.update_progress)
        self.process_thread.finished.connect(self.process_finished)
        self.process_thread.error.connect(self.process_error)
        self.process_thread.start()
        
    def update_progress(self, value):
        self.progress_bar.setValue(int(value))
        
    def process_finished(self):
        self.progress_bar.setValue(100)  # 确保进度条显示100%
        self.progress_bar.hide()
        self.process_button.setEnabled(True)
        QMessageBox.information(self, "成功", "视频水印去除完成！")
        
    def process_error(self, error_msg):
        self.progress_bar.hide()
        self.process_button.setEnabled(True)
        QMessageBox.critical(self, "错误", f"处理失败: {error_msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    window = VideoConverter()
    window.show()
    sys.exit(app.exec())
