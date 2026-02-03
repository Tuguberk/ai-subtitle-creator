from setuptools import setup, find_packages

setup(
    version="1.0",
    name="ai_subtitle_creator",
    packages=find_packages(),

    author="tuguberk",
    install_requires=[
        'openai-whisper',
        'ffmpeg-python',
        'pyyaml',
        'PyQt6',
    ],
    description="AI-powered GUI tool to automatically generate and embed styled subtitles into videos",
    entry_points={
        'console_scripts': ['ai-subtitle=auto_subtitle.gui:main'],
    },
    include_package_data=True,
)
