"""Ponto de entrada do Hugging Face Space (SDK Gradio) e execução local: `python app.py`."""

from lily.logging_utils import setup_logging
from lily.ui import build_app

setup_logging()
demo = build_app()

if __name__ == "__main__":
    demo.launch()
