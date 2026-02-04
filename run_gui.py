import os
import sys
import argparse

def get_app_dir():
    """Get the application directory."""
    if hasattr(sys, 'frozen'):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AI Subtitle Creator")
    parser.add_argument("--logs", action="store_true", help="Enable debug logging to debug_log.txt")
    args = parser.parse_args()
    
    log_file = None
    
    try:
        # Enable logging only if --logs flag is passed
        if args.logs:
            log_path = os.path.join(get_app_dir(), "debug_log.txt")
            log_file = open(log_path, "w", encoding="utf-8")
            sys.stdout = log_file
            sys.stderr = log_file
            print("=== Uygulama Başlatılıyor ===")
            print(f"Python: {sys.executable}")
            print(f"Çalışma dizini: {os.getcwd()}")
            print(f"Uygulama dizini: {get_app_dir()}")
        
        # Add bin folder to PATH so Whisper can find FFmpeg
        bin_dir = os.path.join(get_app_dir(), "bin")
        if os.path.exists(bin_dir):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            if args.logs:
                print(f"bin klasörü PATH'e eklendi: {bin_dir}")
        
        from auto_subtitle.gui import main, get_ffmpeg_path, get_ffprobe_path
        
        if args.logs:
            print(f"FFmpeg yolu: {get_ffmpeg_path()}")
            print(f"FFprobe yolu: {get_ffprobe_path()}")
            print(f"FFmpeg mevcut: {os.path.exists(get_ffmpeg_path())}")
            print(f"FFprobe mevcut: {os.path.exists(get_ffprobe_path())}")
            print("=== GUI Başlatılıyor ===")
            log_file.flush()
        
        main()
        
    except Exception as e:
        if args.logs and log_file:
            import traceback
            print(f"\n=== HATA ===")
            print(f"Hata tipi: {type(e).__name__}")
            print(f"Hata mesajı: {str(e)}")
            traceback.print_exc()
        else:
            # Show error in console if not logging
            import traceback
            traceback.print_exc()
    finally:
        if log_file:
            log_file.close()
