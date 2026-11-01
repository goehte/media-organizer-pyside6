import queue
import sys
import threading
from pathlib import Path
from PIL import Image
import pillow_heif
from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()


class WorkerSignals(QObject):
  """Signals used to safely communicate between background thread and UI."""

  log_message = Signal(str)
  finished = Signal()


class MediaOrganizerWindow(QMainWindow):

  def __init__(self):
    super().__init__()
    self.setWindowTitle("HEIC Converter & Video Organizer")
    self.resize(750, 550)
    self.setMinimumSize(600, 400)

    # Queue and signals for safe multi-threading
    self.signals = WorkerSignals()
    self.signals.log_message.connect(self.append_log)
    self.signals.finished.connect(self.processing_finished)

    self.init_ui()

  def init_ui(self):
    central_widget = QWidget()
    self.setCentralWidget(central_widget)

    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(12)

    # Title label
    title_label = QLabel("Media Organizer (HEIC Converter & Video Mover)")
    title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
    main_layout.addWidget(title_label)

    # Directory selection layout
    dir_layout = QHBoxLayout()
    self.dir_input = QLineEdit()
    self.dir_input.setPlaceholderText("Select or enter target directory...")
    self.dir_input.setStyleSheet("padding: 6px; font-size: 12px;")
    dir_layout.addWidget(self.dir_input)

    browse_btn = QPushButton("Browse")
    browse_btn.setStyleSheet("padding: 6px 14px; font-size: 12px;")
    browse_btn.clicked.connect(self.select_directory)
    dir_layout.addWidget(browse_btn)

    main_layout.addLayout(dir_layout)

    # Start processing button
    self.start_btn = QPushButton("Start Processing")
    self.start_btn.setStyleSheet(
        "background-color: #2e7d32; color: white; font-weight: bold; font-size:"
        " 14px; padding: 10px;"
    )
    self.start_btn.clicked.connect(self.start_processing_thread)
    main_layout.addWidget(self.start_btn)

    # Status log area
    log_label = QLabel("Status Log:")
    log_label.setStyleSheet("font-weight: bold; font-size: 12px;")
    main_layout.addWidget(log_label)

    self.log_area = QTextEdit()
    self.log_area.setReadOnly(True)
    self.log_area.setStyleSheet(
        "font-family: Consolas; font-size: 11px; background-color: #f9f9f9;"
        " border: 1px solid #ccc;"
    )
    main_layout.addWidget(self.log_area)

  def select_directory(self):
    dir_path = QFileDialog.getExistingDirectory(
        self, "Select Target Directory"
    )
    if dir_path:
      self.dir_input.setText(dir_path)

  def append_log(self, message):
    self.log_area.append(message)
    # Scroll to bottom automatically
    scrollbar = self.log_area.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())

  def start_processing_thread(self):
    target_folder = self.dir_input.text().strip()
    if not target_folder:
      self.append_log("Error: Please select a target directory first.")
      return

    root_path = Path(target_folder)
    if not root_path.exists() or not root_path.is_dir():
      self.append_log("Error: The specified directory does not exist.")
      return

    # Disable button and clear logs during execution
    self.start_btn.setEnabled(False)
    self.start_btn.setStyleSheet(
        "background-color: #cccccc; color: #666666; font-weight: bold; font-size:"
        " 14px; padding: 10px;"
    )
    self.log_area.clear()

    # Run processing tasks in background thread
    threading.Thread(
        target=self.run_processing_tasks, args=(root_path,), daemon=True
    ).start()

  def run_processing_tasks(self, root_path):
    try:
      self.signals.log_message.emit(
          f"=== Starting processing in: {root_path} ===\n"
      )

      # --- TASK 1: HEIC Conversion & Organization ---
      self.signals.log_message.emit("--- [1/2] Processing HEIC files ---")
      heic_files = []
      for path in root_path.glob("**/*"):
        if path.is_file() and path.suffix.lower() == ".heic":
          if "HEIC" in path.parts:
            continue
          heic_files.append(path)

      if not heic_files:
        self.signals.log_message.emit("No new HEIC files found to process.")
      else:
        for heic_path in heic_files:
          parent_dir = heic_path.parent
          jpg_path = parent_dir / f"{heic_path.stem}.jpg"
          heic_subfolder = parent_dir / "HEIC"

          if jpg_path.exists():
            heic_subfolder.mkdir(exist_ok=True)
            destination = heic_subfolder / heic_path.name
            if heic_path.exists():
              heic_path.rename(destination)
            self.signals.log_message.emit(
                f"Skipped conversion (JPG exists): {heic_path.name}"
            )
            continue

          try:
            with Image.open(heic_path) as img:
              img.convert("RGB").save(jpg_path, "JPEG", quality=90)
            self.signals.log_message.emit(
                f"Successfully converted: {heic_path.name} -> {jpg_path.name}"
            )

            heic_subfolder.mkdir(exist_ok=True)
            destination = heic_subfolder / heic_path.name
            heic_path.rename(destination)
            self.signals.log_message.emit(
                f"Moved original to backup:"
                f" {destination.relative_to(root_path)}"
            )
          except Exception as e:
            self.signals.log_message.emit(
                f"Error processing {heic_path.name}: {e}"
            )

      # --- TASK 2: Video Organization ---
      self.signals.log_message.emit(
          "\n--- [2/2] Processing Video files (.mov, .mp4) ---"
      )
      video_files = []
      for path in root_path.glob("**/*"):
        if path.is_file() and path.suffix.lower() in (".mov", ".mp4"):
          if "Video" in path.parts:
            continue
          video_files.append(path)

      if not video_files:
        self.signals.log_message.emit("No new Video files found to process.")
      else:
        moved_count = 0
        source_folders = set()
        for video_path in video_files:
          parent_dir = video_path.parent
          video_subfolder = parent_dir / "Video"

          try:
            video_subfolder.mkdir(exist_ok=True)
            destination = video_subfolder / video_path.name

            if destination.exists():
              base = video_path.stem
              ext = video_path.suffix
              counter = 1
              while destination.exists():
                destination = video_subfolder / f"{base}_{counter}{ext}"
                counter += 1

            video_path.rename(destination)
            self.signals.log_message.emit(
                f"Moved video: {video_path.relative_to(root_path)} ->"
                f" {destination.relative_to(root_path)}"
            )
            moved_count += 1
            source_folders.add(parent_dir)
          except Exception as e:
            self.signals.log_message.emit(
                f"Error processing {video_path.name}: {e}"
            )

        self.signals.log_message.emit(
            f"\nVideos summary: {moved_count} files from"
            f" {len(source_folders)} folders moved."
        )

      self.signals.log_message.emit(
          "\n=== All tasks completed successfully! ==="
      )

    except Exception as general_error:
      self.signals.log_message.emit(f"Critical Error: {general_error}")

    finally:
      self.signals.finished.emit()

  def processing_finished(self):
    self.start_btn.setEnabled(True)
    self.start_btn.setStyleSheet(
        "background-color: #2e7d32; color: white; font-weight: bold; font-size:"
        " 14px; padding: 10px;"
    )


if __name__ == "__main__":
  app = QApplication(sys.argv)
  window = MediaOrganizerWindow()
  window.show()
  try:
    sys.exit(app.exec())
  except KeyboardInterrupt:
    print("\nApplication closed by user.")
