from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap

import os
from ..widgets.custom_buttons import CategoryButton
from ..styles.stylesheets import Stylesheets
from ..styles.dimensions import Dimensions
from config.settings import AppSettings

class MainPage(QWidget):
    def __init__(self, translator, category_callback, exit_callback):
        super().__init__()
        self.translator = translator
        self.category_callback = category_callback
        self.exit_callback = exit_callback
        
        self.current_bg_index = 0  # Initialize background state
        self.background_images = []
        self.load_background_images()
        
        self.init_ui()
