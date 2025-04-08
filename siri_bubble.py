import sys
import random
import math
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property, QPoint, Signal, Slot
from PySide6.QtGui import QPainter, QColor, QPainterPath, QBrush, QPen
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel

class VoiceWaveform(QWidget):
    """Widget that displays animated voice waveforms similar to Siri"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 100)
        
        # Waveform properties
        self.waveform_height = 40
        self.num_bars = 20
        self.bar_spacing = 4
        self.bars = [0] * self.num_bars
        self.target_heights = [0] * self.num_bars
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_waveform)
        
        # States
        self.is_listening = False
        self.is_speaking = False
        self.is_processing = False
        
        # Colors
        self.listening_color = QColor(0, 122, 255)  # Apple blue
        self.speaking_color = QColor(88, 86, 214)   # Purple
        self.processing_color = QColor(52, 199, 89) # Green
        self.idle_color = QColor(142, 142, 147)     # Gray
        
        self.current_color = self.idle_color
        self._pulse_phase = 0
        
    def set_listening(self, listening):
        """Set the widget to listening state with voice level animation"""
        self.is_listening = listening
        self.is_speaking = False
        self.is_processing = False
        
        if listening:
            self.current_color = self.listening_color
            self.timer.start(50)  # Update every 50ms
        else:
            self.reset_state()
            
    def set_speaking(self, speaking):
        """Set the widget to speaking state with voice output animation"""
        self.is_speaking = speaking
        self.is_listening = False
        self.is_processing = False
        
        if speaking:
            self.current_color = self.speaking_color
            self.timer.start(50)
        else:
            self.reset_state()
            
    def set_processing(self, processing):
        """Set the widget to processing state with pulsing animation"""
        self.is_processing = processing
        self.is_listening = False
        self.is_speaking = False
        
        if processing:
            self.current_color = self.processing_color
            self.timer.start(70)
        else:
            self.reset_state()
            
    def reset_state(self):
        """Reset to idle state"""
        if not (self.is_listening or self.is_speaking or self.is_processing):
            self.current_color = self.idle_color
            self.timer.stop()
            self.bars = [0] * self.num_bars
            self.update()
    
    def update_waveform(self):
        """Update the waveform animation based on current state"""
        if self.is_listening:
            # Simulate microphone input with random heights
            for i in range(self.num_bars):
                # Random height with temporal coherence (smoother changes)
                self.target_heights[i] = min(self.waveform_height, 
                                           max(5, self.target_heights[i] + random.uniform(-8, 8)))
                # Gradually move toward target height
                self.bars[i] += (self.target_heights[i] - self.bars[i]) * 0.3
                
        elif self.is_speaking:
            # Simulate speech output pattern
            for i in range(self.num_bars):
                if i % 2 == 0:  # Alternate bars for wave-like pattern
                    self.target_heights[i] = random.uniform(10, self.waveform_height)
                else:
                    self.target_heights[i] = random.uniform(5, self.waveform_height - 10)
                # Smoother transitions
                self.bars[i] += (self.target_heights[i] - self.bars[i]) * 0.4
                
        elif self.is_processing:
            # Create a pulsing circle effect
            pulse = (math.sin(self.pulse_phase) + 1) / 2  # 0 to 1
            height = 5 + pulse * (self.waveform_height - 10)
            
            # Create a circular pattern
            for i in range(self.num_bars):
                angle = 2 * math.pi * i / self.num_bars
                phase_offset = 2 * math.pi * (i / self.num_bars)
                bar_pulse = (math.sin(self.pulse_phase + phase_offset) + 1) / 2
                self.bars[i] = 5 + bar_pulse * (self.waveform_height - 10)
            
            self.pulse_phase += 0.15
                
        self.update()  # Trigger repaint
        
    @property
    def pulse_phase(self):
        return self._pulse_phase
        
    @pulse_phase.setter
    def pulse_phase(self, value):
        self._pulse_phase = value
    
    def paintEvent(self, event):
        """Draw the waveform bars"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate total width needed for bars
        total_width = self.num_bars * (self.bar_spacing + 2)
        
        # Center bars horizontally and vertically
        start_x = (self.width() - total_width) // 2
        center_y = self.height() // 2
        
        # Draw each bar
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.current_color))
        
        for i, height in enumerate(self.bars):
            x = start_x + i * (self.bar_spacing + 2)
            y = center_y - height // 2
            
            # Draw rounded bar
            painter.drawRoundedRect(x, y, 2, height, 1, 1)


class SiriBubbleWindow(QMainWindow):
    """Main window implementing a floating Siri-like bubble interface"""
    
    def __init__(self):
        super().__init__()
        
        # Window setup - frameless and always on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Main bubble widget
        self.bubble_widget = QWidget()
        self.setCentralWidget(self.bubble_widget)
        
        # Layout
        layout = QVBoxLayout(self.bubble_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Word display label
        self.word_label = QLabel("Ready")
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                background: rgba(0, 0, 0, 0);
            }
        """)
        
        # Waveform widget
        self.waveform = VoiceWaveform()
        
        # Add widgets to layout
        layout.addWidget(self.word_label)
        layout.addWidget(self.waveform)
        
        # Size and position
        self.resize(250, 150)
        screen_geometry = QApplication.primaryScreen().geometry()
        self.move(screen_geometry.width() - self.width() - 50, 
                 screen_geometry.height() - self.height() - 100)
        
        # Bubble state
        self.expanded = False
        self.dragging = False
        self.offset = QPoint()
        
    def paintEvent(self, event):
        """Draw the bubble background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create bubble background path
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 25, 25)
        
        # Set semi-transparent background
        painter.fillPath(path, QColor(30, 30, 30, 230))
        
        # Draw subtle border
        painter.setPen(QPen(QColor(200, 200, 200, 30), 1))
        painter.drawPath(path)
        
    def mousePressEvent(self, event):
        """Handle mouse press for dragging the bubble"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.position().toPoint()
            
    def mouseMoveEvent(self, event):
        """Move the bubble with mouse drag"""
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(self.mapToGlobal(event.position().toPoint() - self.offset))
            
    def mouseReleaseEvent(self, event):
        """End dragging on mouse release"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            
    def mouseDoubleClickEvent(self, event):
        """Toggle expanded state on double click"""
        self.toggle_expanded()
        
    def toggle_expanded(self):
        """Toggle between expanded and collapsed states"""
        self.expanded = not self.expanded
        if self.expanded:
            # Expand to full size
            self.animation = QPropertyAnimation(self, b"geometry")
            self.animation.setDuration(300)
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(self.geometry().adjusted(-100, -50, 100, 50))
            self.animation.setEasingCurve(QEasingCurve.OutCubic)
            self.animation.start()
        else:
            # Collapse to small size
            self.animation = QPropertyAnimation(self, b"geometry")
            self.animation.setDuration(300)
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(self.geometry().adjusted(100, 50, -100, -50))
            self.animation.setEasingCurve(QEasingCurve.OutCubic)
            self.animation.start()
    
    # Public methods for controlling the bubble
    def set_word(self, word):
        """Set the displayed word"""
        self.word_label.setText(word)
        
    def start_listening(self):
        """Start listening animation"""
        self.word_label.setText("Listening...")
        self.waveform.set_listening(True)
        
    def start_processing(self):
        """Start processing animation"""
        self.word_label.setText("Processing...")
        self.waveform.set_listening(False)
        self.waveform.set_processing(True)
        
    def start_speaking(self, text=None):
        """Start speaking animation with optional text"""
        if text:
            self.word_label.setText(text)
        else:
            self.word_label.setText("Speaking...")
        self.waveform.set_processing(False)
        self.waveform.set_speaking(True)
        
    def reset(self):
        """Reset to idle state"""
        self.word_label.setText("Ready")
        self.waveform.set_speaking(False)
        self.waveform.set_processing(False)
        self.waveform.set_listening(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SiriBubbleWindow()
    window.show()
    sys.exit(app.exec())