import sys, os, signal, json, time
import matplotlib.pyplot as plt
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QFileDialog, QLabel, QTextEdit, QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import QTextEdit, QLabel

# Benchmarking and WER calculation functions
def calculate_wer(reference, hypothesis):
    reference_words = reference.split()
    hypothesis_words = hypothesis.split()
    
    # Calculate substitutions, deletions, insertions
    s = d = i = 0
    for ref, hyp in zip(reference_words, hypothesis_words):
        if ref != hyp:
            s += 1
    d = len(reference_words) - len(hypothesis_words)
    i = len(hypothesis_words) - len(reference_words)
    
    wer = (s + d + i) / len(reference_words) if len(reference_words) > 0 else 0
    return wer

class MeetingSummarizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Meeting Summarizer")
        self.setFixedSize(800, 600)
        
        # Benchmarking variables
        self.transcription_time = 0
        self.summarization_time = 0
        self.action_item_time = 0
        self.wer_score = 0

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Buttons
        self.button_layout = QHBoxLayout()
        layout.addLayout(self.button_layout)

        self.start_button = QPushButton("Start Recording")
        self.start_button.clicked.connect(self.start_recording)
        self.button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Recording")
        self.stop_button.clicked.connect(self.stop_recording)
        self.button_layout.addWidget(self.stop_button)

        self.summarize_button = QPushButton("Summarize")
        self.summarize_button.clicked.connect(self.summarize_recording)
        layout.addWidget(self.summarize_button)

        self.save_button = QPushButton("Save Summary")
        self.save_button.clicked.connect(self.save_summary)
        layout.addWidget(self.save_button)

        # Text Areas
        self.transcript_label = QLabel("Transcript:")
        layout.addWidget(self.transcript_label)
        self.transcript_edit = QTextEdit()
        layout.addWidget(self.transcript_edit)

        self.summary_label = QLabel("Summary:")
        layout.addWidget(self.summary_label)
        self.summary_edit = QTextEdit()
        layout.addWidget(self.summary_edit)
        
        self.action_label = QLabel("Action Items:")
        layout.addWidget(self.action_label)
        self.action_edit = QTextEdit()
        layout.addWidget(self.action_edit)

        self.log_label = QLabel("Logs:")
        layout.addWidget(self.log_label)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

        # Process
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        # Apply dark mode
        self.apply_dark_mode()

        # Add visualization area
        self.graph_widget = pg.PlotWidget()
        layout.addWidget(self.graph_widget)
        
        self.plot_benchmark_data()

    def apply_dark_mode(self):
        dark_style = """
            QWidget {
                background-color: #121212;
                color: #e0e0e0;
                font-family: Consolas;
            }
            QPushButton {
                background-color: #2a2a2a;
                border: 1px solid #3c3c3c;
                padding: 5px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #333;
            }
        """
        self.setStyleSheet(dark_style)

    def start_recording(self):
        output_filename, _ = QFileDialog.getSaveFileName(self, "Save Meeting Recording", filter="MP3 Files (*.mp3)")
        if not output_filename:
            return
        if not output_filename.endswith(".mp3"):
            output_filename += ".mp3"
        self.output_filename = output_filename
        self.process.start("python", ["cli.py", "record", self.output_filename])

    def stop_recording(self):
        os.kill(self.process.processId(), signal.SIGINT)
        self.process.waitForFinished(-1)

    def summarize_recording(self):
        audio_filename, _ = QFileDialog.getOpenFileName(self, "Select Audio File", filter="MP3 Files (*.mp3)")
        if not audio_filename:
            return
        self.output_filename = audio_filename
        self.transcript = ""
        self.summary = ""
        self.action_items = []
        self.transcript_edit.clear()
        self.summary_edit.clear()

        # Start benchmarking for transcription
        start_time = time.time()
        self.process.start("python", ["cli.py", "summarize", audio_filename])
        self.transcription_time = time.time() - start_time

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        lines = data.strip().splitlines()
        summary_flag = False
        action_flag = False
        summary_lines = []
        action_lines = []

        for line in lines:
            self.log_edit.append(line)
            if line.startswith("TRANSCRIPT:"):
                self.transcript += line[len("TRANSCRIPT:"):].strip() + "\n"
                self.transcript_edit.setPlainText(self.transcript)

            elif line.startswith("SUMMARY_START"):
                summary_flag = True
            elif line.startswith("SUMMARY_END"):
                summary_flag = False
                self.summary = "\n".join(summary_lines)
                self.summary_edit.setPlainText(self.summary)
                summary_lines = []

            elif line.startswith("ACTION_ITEMS_START"):
                action_flag = True
            elif line.startswith("ACTION_ITEMS_END"):
                action_flag = False
                self.action_items = action_lines[:]
                self.action_edit.setPlainText("\n".join(self.action_items))  # 🆕 update GUI
                action_lines = []

            elif summary_flag:
                summary_lines.append(line)
            elif action_flag:
                action_lines.append(line)

        # Benchmark for summarization
        start_time = time.time()
        # Simulate summarization here
        self.summarization_time = time.time() - start_time

        # Benchmark for action item extraction
        start_time = time.time()
        # Simulate action item extraction here
        self.action_item_time = time.time() - start_time

        # Calculate WER
        reference_transcript = "your reference transcript here"  # You should load or have a reference transcript
        self.wer_score = calculate_wer(reference_transcript, self.transcript)

        # Update visualization
        self.plot_benchmark_data()

    def plot_benchmark_data(self):
        # Plotting benchmarking results
        self.graph_widget.clear()

        # Categories and their corresponding times
        categories = ['Transcription', 'Summarization', 'Action Items']
        times = [self.transcription_time, self.summarization_time, self.action_item_time]

        # Convert categories to numeric indices for plotting
        x_values = range(len(categories))  # This will be [0, 1, 2]

        # Plot the data
        self.graph_widget.plot(x=x_values, y=times, pen='b', symbol='o')

        # Set x-axis labels to the category names
        self.graph_widget.getAxis('bottom').setTicks([[(i, categories[i]) for i in range(len(categories))]])

        # Set the plot title including WER score
        self.graph_widget.setTitle(f"Benchmarking - WER: {self.wer_score:.2f}")


    def handle_stderr(self):
        error = self.process.readAllStandardError().data().decode()
        self.log_edit.append(f"[STDERR] {error.strip()}")

    def process_finished(self):
        self.log_edit.append("✅ Process finished")

    def save_summary(self):
        if not self.transcript and not self.summary:
            QMessageBox.warning(self, "Nothing to Save", "No transcript or summary to save.")
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Output", filter="JSON Files (*.json)")
        if file_name:
            if not file_name.endswith(".json"):
                file_name += ".json"
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump({
                    "transcript": self.transcript.strip(),
                    "summary": self.summary.strip(),
                    "action_items": self.action_items
                }, f, indent=4)
            QMessageBox.information(self, "Saved", f"Summary saved to {file_name}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MeetingSummarizer()
    window.show()
    sys.exit(app.exec_())
