import sys
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QComboBox, QLabel, 
                           QCheckBox, QSlider, QColorDialog, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen
import pyaudio

class AudioVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Visualizer")
        self.setGeometry(100, 100, 1200, 800)
        
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.RATE = 44100
        self.p = pyaudio.PyAudio()
        
        self.input_devices = self.get_input_devices()
        self.current_device_index = None
        
        self.layout_type = "circle"
        self.pattern = "0"
        self.style = "line"
        self.color = QColor(0, 255, 255)
        self.background_color = QColor(0, 255, 0)
        self.transparent_background = True
        self.frequency_range = [0, 255]
        self.is_running = False
        self.noise_gate = 0.001
        
        self.setup_ui()
        
        self.stream = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)

    def get_input_devices(self):
        devices = []
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': device_info['name'],
                    'info': device_info
                })
        return devices
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout()
        
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        self.canvas = VisualizerCanvas(self)
        left_layout.addWidget(self.canvas)
        
        controls_layout = QHBoxLayout()
        
        device_layout = QVBoxLayout()
        device_label = QLabel("Input Device:")
        self.device_combo = QComboBox()
        for device in self.input_devices:
            self.device_combo.addItem(device['name'], device['index'])
        self.device_combo.currentIndexChanged.connect(self.update_input_device)
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo)
        
        layout_type_layout = QVBoxLayout()
        layout_label = QLabel("Visualization Type:")
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["圓形圖", "直方圖"])
        self.layout_combo.currentTextChanged.connect(self.update_layout)
        layout_type_layout.addWidget(layout_label)
        layout_type_layout.addWidget(self.layout_combo)

        pattern_layout = QVBoxLayout()
        pattern_label = QLabel("Pattern:")
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(["Pattern 0", "Pattern 1"])
        self.pattern_combo.currentIndexChanged.connect(self.update_pattern)
        pattern_layout.addWidget(pattern_label)
        pattern_layout.addWidget(self.pattern_combo)

        style_layout = QVBoxLayout()
        style_label = QLabel("Style:")
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Line", "Dot"])
        self.style_combo.currentTextChanged.connect(self.update_style)
        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo)
        
        controls_layout.addLayout(device_layout)
        controls_layout.addLayout(layout_type_layout)
        controls_layout.addLayout(pattern_layout)
        controls_layout.addLayout(style_layout)
        left_layout.addLayout(controls_layout)
        
        left_widget.setLayout(left_layout)
        
        right_widget = QWidget()
        right_widget.setFixedWidth(300)
        right_layout = QVBoxLayout()
        
        self.toggle_button = QPushButton("Start Visualizer")
        self.toggle_button.clicked.connect(self.toggle_visualizer)
        right_layout.addWidget(self.toggle_button)
        
        color_label = QLabel("Visualization Color")
        self.color_button = QPushButton()
        self.color_button.setStyleSheet(f"background-color: {self.color.name()}")
        self.color_button.clicked.connect(self.choose_color)
        right_layout.addWidget(color_label)
        right_layout.addWidget(self.color_button)
        
        background_label = QLabel("Background Settings")
        self.transparent_checkbox = QCheckBox("Transparent Background")
        self.transparent_checkbox.setChecked(True)
        self.transparent_checkbox.stateChanged.connect(self.update_background)
        
        self.background_button = QPushButton()
        self.background_button.setStyleSheet(f"background-color: {self.background_color.name()}")
        self.background_button.clicked.connect(self.choose_background_color)
        self.background_button.setEnabled(not self.transparent_background)
        
        right_layout.addWidget(background_label)
        right_layout.addWidget(self.transparent_checkbox)
        right_layout.addWidget(self.background_button)
        
        freq_label = QLabel("Frequency Range")
        self.min_freq_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_freq_slider = QSlider(Qt.Orientation.Horizontal)
        
        self.min_freq_slider.setRange(0, 255)
        self.max_freq_slider.setRange(0, 255)
        self.min_freq_slider.setValue(0)
        self.max_freq_slider.setValue(255)
        
        self.min_freq_slider.valueChanged.connect(self.update_frequency_range)
        self.max_freq_slider.valueChanged.connect(self.update_frequency_range)
        
        right_layout.addWidget(freq_label)
        right_layout.addWidget(QLabel("Min Frequency"))
        right_layout.addWidget(self.min_freq_slider)
        right_layout.addWidget(QLabel("Max Frequency"))
        right_layout.addWidget(self.max_freq_slider)

        noise_gate_label = QLabel("Noise Gate")
        self.noise_gate_slider = QSlider(Qt.Orientation.Horizontal)
        self.noise_gate_slider.setRange(0, 100)
        self.noise_gate_slider.setValue(int(self.noise_gate * 10000))
        self.noise_gate_slider.valueChanged.connect(self.update_noise_gate)
        self.noise_gate_value_label = QLabel(f"Noise Gate: {self.noise_gate:.4f}")
        
        right_layout.addWidget(noise_gate_label)
        right_layout.addWidget(self.noise_gate_slider)
        right_layout.addWidget(self.noise_gate_value_label)
        
        right_widget.setLayout(right_layout)
        
        layout.addWidget(left_widget)
        layout.addWidget(right_widget)
        
        central_widget.setLayout(layout)

    def update_input_device(self, index):
        if self.is_running:
            self.stop_visualizer()
        self.current_device_index = self.device_combo.currentData()
        if self.is_running:
            self.start_visualizer()

    def toggle_visualizer(self):
        if not self.is_running:
            self.start_visualizer()
        else:
            self.stop_visualizer()
    
    def start_visualizer(self):
        try:
            device_index = self.device_combo.currentData()
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.CHUNK
            )
            self.is_running = True
            self.toggle_button.setText("Stop Visualizer")
            self.timer.start(16)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not start audio stream: {str(e)}")
            self.is_running = False
    
    def stop_visualizer(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.is_running = False
        self.toggle_button.setText("Start Visualizer")
        self.timer.stop()
        self.canvas.update()

    def update_layout(self, text):
        self.layout_type = "circle" if text == "圓形圖" else "histogram"
        self.canvas.update()
    
    def update_pattern(self, index):
        self.pattern = str(index)
        self.canvas.update()
    
    def update_style(self, text):
        self.style = text.lower()
    
    def choose_color(self):
        color = QColorDialog.getColor(self.color)
        if color.isValid():
            self.color = color
            self.color_button.setStyleSheet(f"background-color: {color.name()}")
    
    def choose_background_color(self):
        color = QColorDialog.getColor(self.background_color)
        if color.isValid():
            self.background_color = color
            self.background_button.setStyleSheet(f"background-color: {color.name()}")
    
    def update_background(self, state):
        self.transparent_background = bool(state)
        self.background_button.setEnabled(not self.transparent_background)
    
    def update_frequency_range(self):
        self.frequency_range = [
            self.min_freq_slider.value(),
            self.max_freq_slider.value()
        ]

    def update_noise_gate(self):
        self.noise_gate = self.noise_gate_slider.value() / 10000
        self.noise_gate_value_label.setText(f"Noise Gate: {self.noise_gate:.4f}")
    
    def closeEvent(self, event):
        self.stop_visualizer()
        self.p.terminate()
        event.accept()

class VisualizerCanvas(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumSize(600, 400)
    
    def paintEvent(self, event):
        if not self.parent.is_running:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.parent.transparent_background:
            painter.eraseRect(self.rect())
        else:
            painter.fillRect(self.rect(), self.parent.background_color)
        
        if self.parent.stream:
            try:
                data = self.parent.stream.read(self.parent.CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.float32)
                
                audio_data = np.where(np.abs(audio_data) < self.parent.noise_gate, 0, audio_data)
                
                if np.max(np.abs(audio_data)) > self.parent.noise_gate:
                    fft_data = np.abs(np.fft.fft(audio_data)[:256])
                    processed_data = np.zeros(256)
                    start_freq, end_freq = self.parent.frequency_range
                    frequency_step = (end_freq - start_freq) / len(processed_data)
                    
                    for i in range(len(processed_data)):
                        if self.parent.pattern == "0":
                            data_index = int(start_freq + i * frequency_step)
                        else:
                            lower_half_length = len(fft_data) // 2
                            data_index = i % lower_half_length
                            
                        if 0 <= data_index < len(fft_data):
                            processed_data[i] = fft_data[data_index]
                    
                    max_val = np.max(processed_data)
                    if max_val > 0:
                        normalized_data = (processed_data / max_val * 255).astype(int)
                    else:
                        normalized_data = np.zeros(256)
                else:
                    normalized_data = np.zeros(256)
                
                if self.parent.layout_type == "circle":
                    self.draw_circle_visualization(painter, normalized_data)
                else:
                    if self.parent.pattern == "0":
                        self.draw_basic_histogram(painter, normalized_data)
                    else:
                        self.draw_pattern_one_histogram(painter, normalized_data)
            except Exception as e:
                print(f"Error reading audio data: {e}")
    
    def draw_circle_visualization(self, painter, data):
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) // 3
        
        pen = QPen(self.parent.color, 1, Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        
        for i in range(len(data)):
            angle = (i / len(data)) * 2 * np.pi
            value = data[i] / 3
            
            x1 = center_x + radius * np.cos(angle)
            y1 = center_y + radius * np.sin(angle)
            x2 = center_x + (radius + value) * np.cos(angle)
            y2 = center_y + (radius + value) * np.sin(angle)
            
            if self.parent.style == "line":
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            else:
                painter.drawEllipse(int(x2) - 2, int(y2) - 2, 4, 4)

    def draw_basic_histogram(self, painter, data):
        num_bars = len(data)
        available_width = self.width() * 0.8
        bar_width = available_width / num_bars
        margin_x = self.width() * 0.1
        margin_y = self.height() * 0.1
        max_height = self.height() * 0.8
        
        painter.setPen(self.parent.color)
        
        for i in range(num_bars):
            height = (data[i] / 255) * max_height
            x = margin_x + i * bar_width
            y = self.height() - margin_y - height
            
            if self.parent.style == "line":
                painter.drawRect(int(x), int(y), 
                               max(1, int(bar_width * 0.8)),
                               int(height))
            else:
                painter.drawEllipse(int(x + bar_width/2 - 2), 
                                  int(y - 2), 
                                  4, 4)

    def draw_pattern_one_histogram(self, painter, data):
        lower_half_length = len(data) // 2
        available_width = self.width() * 0.8
        bar_width = available_width / lower_half_length
        margin_x = self.width() * 0.1
        margin_y = self.height() * 0.1
        max_height = self.height() * 0.8
        
        painter.setPen(self.parent.color)
        
        for i in range(lower_half_length):
            height = (data[i] / 255) * max_height
            x = margin_x + i * bar_width
            y = self.height() - margin_y - height
            
            if self.parent.style == "line":
                painter.drawRect(int(x), int(y), 
                               max(1, int(bar_width * 0.8)),
                               int(height))
            else:
                painter.drawEllipse(int(x + bar_width/2 - 2), 
                                  int(y - 2), 
                                  4, 4)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioVisualizer()
    window.show()
    sys.exit(app.exec())