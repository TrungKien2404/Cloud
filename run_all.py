# -*- coding: utf-8 -*-
"""
Coordinator Script for Stock Prediction System
Author: Antigravity DeepMind Team
Description: 1-Click execution script to rule them all. 
Automatically checks and runs Ingestion, ETL, and Training if data is missing,
then concurrently launches FastAPI Backend and Streamlit Frontend with unified, clean logs.
"""

import os
import sys
import subprocess
import threading
import time
import signal

# ANSI terminal styling for rich premium developer experience
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    banner = f"""
{Colors.OKCYAN}{Colors.BOLD}====================================================================
 📈 STOCK PREDICTION SYSTEM - UNIFIED RUNNER
===================================================================={Colors.ENDC}
🤖 Designed by: Antigravity DeepMind Team
🚀 Mode: Single Command Execution
"""
    print(banner)

def run_command(command_list, step_name):
    """Utility to run a blocking script with real-time console feedback."""
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}▶ Running {step_name}...{Colors.ENDC}")
    print(f"{Colors.BOLD}Command:{Colors.ENDC} {' '.join(command_list)}")
    
    # We use sys.executable to ensure we run under the same virtual/active environment
    process = subprocess.Popen(
        command_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace'
    )
    
    # Print output in real-time
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            print(f"  {line.strip()}")
            
    rc = process.poll()
    if rc != 0:
        print(f"\n{Colors.FAIL}{Colors.BOLD}❌ {step_name} failed with exit code {rc}!{Colors.ENDC}")
        sys.exit(rc)
    else:
        print(f"{Colors.OKGREEN}✔ {step_name} completed successfully!{Colors.ENDC}")

def check_pipeline_dependencies():
    """Verify raw data, processed data, and models. Run pipelines if missing."""
    print(f"{Colors.BOLD}🔍 Validating Pipeline Dependencies...{Colors.ENDC}")
    
    # 1. Check Raw Data
    raw_data_file = os.path.join("data", "raw", "combined_stock_data.parquet")
    if not os.path.exists(raw_data_file):
        print(f"{Colors.WARNING}⚠️ Raw data parquet file not found at '{raw_data_file}'.{Colors.ENDC}")
        run_command([sys.executable, "run_ingestion.py"], "Step 1: Data Ingestion")
    else:
        print(f"  {Colors.OKGREEN}✓{Colors.ENDC} Raw data is available.")

    # 2. Check Processed Data
    processed_data_file = os.path.join("data", "processed", "processed_stock_data.parquet")
    if not os.path.exists(processed_data_file):
        print(f"{Colors.WARNING}⚠️ Processed data parquet file not found at '{processed_data_file}'.{Colors.ENDC}")
        run_command([sys.executable, "run_etl.py"], "Step 2: ETL Processing")
    else:
        print(f"  {Colors.OKGREEN}✓{Colors.ENDC} Processed data is available.")

    # 3. Check Models
    models_dir = "models"
    has_models = False
    if os.path.exists(models_dir):
        pkl_files = [f for f in os.listdir(models_dir) if f.endswith(".pkl")]
        if pkl_files:
            has_models = True
            print(f"  {Colors.OKGREEN}✓{Colors.ENDC} Found {len(pkl_files)} trained models in '{models_dir}'.")
            
    if not has_models:
        print(f"{Colors.WARNING}⚠️ No trained stock models (.pkl) found in '{models_dir}/'.{Colors.ENDC}")
        run_command([sys.executable, "run_training.py"], "Step 3: Model Training")

def log_reader(pipe, prefix, color):
    """Background worker thread to read subprocess logs and prefix them nicely."""
    try:
        for line in iter(pipe.readline, ''):
            if line:
                cleaned_line = line.strip()
                print(f"{color}{prefix}{Colors.ENDC} {cleaned_line}")
    except Exception:
        pass
    finally:
        pipe.close()

def ensure_ollama():
    """Tự động kiểm tra, tải, cài đặt và khởi động Ollama cùng mô hình qwen2.5:1.5b cục bộ."""
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}🔍 Đang kiểm tra trợ lý AI cục bộ (Ollama)...{Colors.ENDC}")
    
    # 1. Kiểm tra xem Ollama có sẵn trong PATH không
    ollama_installed = False
    try:
        res = subprocess.run(["where", "ollama"], capture_output=True, text=True)
        if res.returncode == 0:
            ollama_installed = True
    except Exception:
        pass
        
    # Kiểm tra đường dẫn mặc định trên Windows nếu lệnh 'where' thất bại
    local_appdata = os.getenv("LOCALAPPDATA", "")
    default_exe = os.path.join(local_appdata, "Programs", "Ollama", "ollama.exe")
    if not ollama_installed and os.path.exists(default_exe):
        ollama_installed = True
        os.environ["PATH"] += os.pathsep + os.path.dirname(default_exe)
        
    # 2. Nếu chưa cài đặt -> Tải và cài đặt tự động
    if not ollama_installed:
        print(f"{Colors.WARNING}⚠️ Trợ lý AI cục bộ (Ollama) chưa được cài đặt trên hệ thống.{Colors.ENDC}")
        print(f"{Colors.OKBLUE}📥 Đang tự động tải bộ cài đặt OllamaSetup.exe từ trang chủ (ollama.com)...{Colors.ENDC}")
        
        installer_path = "OllamaSetup.exe"
        try:
            import urllib.request
            url = "https://ollama.com/download/OllamaSetup.exe"
            
            # Hiển thị tiến trình tải
            def report_progress(block_num, block_size, total_size):
                percent = int(block_num * block_size * 100 / total_size)
                percent = min(100, percent)
                sys.stdout.write(f"\r  Đang tải: {percent}% [{(block_num*block_size)/(1024*1024):.1f} MB / {total_size/(1024*1024):.1f} MB]")
                sys.stdout.flush()
                
            urllib.request.urlretrieve(url, installer_path, report_progress)
            print(f"\n{Colors.OKGREEN}✓ Tải bộ cài thành công! Đang tự động cài đặt chế độ im lặng (Silent Setup)...{Colors.ENDC}")
            
            # Cài đặt silent mode (mất khoảng 5-10 giây)
            subprocess.run([installer_path, "/silent"], check=True)
            print(f"{Colors.OKGREEN}✓ Cài đặt Ollama thành công!{Colors.ENDC}")
            
            # Xóa file installer sau khi cài đặt xong
            if os.path.exists(installer_path):
                os.remove(installer_path)
                
            if os.path.exists(default_exe):
                os.environ["PATH"] += os.pathsep + os.path.dirname(default_exe)
                ollama_installed = True
                
        except Exception as e:
            print(f"\n{Colors.FAIL}❌ Lỗi tải/cài đặt Ollama: {str(e)}{Colors.ENDC}")
            print(f"{Colors.WARNING}👉 Vui lòng tải và cài đặt thủ công tại: https://ollama.com{Colors.ENDC}")
            return
            
    # 3. Kiểm tra xem Ollama đã chạy chưa
    import requests
    ollama_running = False
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=1.0)
        if r.status_code == 200:
            ollama_running = True
    except Exception:
        pass
        
    # 4. Nếu chưa chạy -> Tự động khởi động ngầm
    if not ollama_running:
        print(f"{Colors.OKBLUE}🚀 Trợ lý AI đang tắt. Đang tự động khởi chạy tiến trình Ollama ngầm...{Colors.ENDC}")
        try:
            # Chạy 'ollama serve' ngầm không hiển thị cửa sổ CMD (creationflags=0x08000000)
            if sys.platform.startswith("win"):
                subprocess.Popen(["ollama", "serve"], creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            # Chờ Ollama khởi động
            for i in range(12):
                time.sleep(1.0)
                try:
                    r = requests.get("http://localhost:11434/api/tags", timeout=1.0)
                    if r.status_code == 200:
                        ollama_running = True
                        print(f"  {Colors.OKGREEN}✓{Colors.ENDC} Trợ lý AI cục bộ đã được kích hoạt thành công!")
                        break
                except:
                    pass
            if not ollama_running:
                print(f"{Colors.WARNING}⚠️ Trợ lý AI khởi động chậm. Có thể bạn cần chạy ứng dụng Ollama thủ công.{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}❌ Không thể kích hoạt Ollama ngầm: {str(e)}{Colors.ENDC}")
            
    # 5. Kiểm tra mô hình qwen2.5:1.5b và tải nếu thiếu
    if ollama_running:
        print(f"{Colors.BOLD}🔍 Đang kiểm tra mô hình ngôn ngữ 'qwen2.5:1.5b'...{Colors.ENDC}")
        has_model = False
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=1.5)
            if r.status_code == 200:
                models = [m.get("name") for m in r.json().get("models", [])]
                if any("qwen2.5:1.5b" in m for m in models):
                    has_model = True
                    print(f"  {Colors.OKGREEN}✓{Colors.ENDC} Mô hình 'qwen2.5:1.5b' đã sẵn sàng.")
        except Exception:
            pass
            
        if not has_model:
            print(f"{Colors.WARNING}⚠️ Thiếu mô hình 'qwen2.5:1.5b'. Đang tải tự động từ thư viện Ollama...{Colors.ENDC}")
            print(f"{Colors.BOLD}Tiến trình tải mô hình (Lưu ý: Chỉ tải duy nhất 1 lần đầu tiên):{Colors.ENDC}")
            try:
                subprocess.run(["ollama", "pull", "qwen2.5:1.5b"], check=True)
                print(f"{Colors.OKGREEN}✓ Tải mô hình 'qwen2.5:1.5b' thành công!{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.FAIL}❌ Không thể tải mô hình tự động: {str(e)}{Colors.ENDC}")

def main():
    print_banner()
    
    # Tự động cài đặt và cấu hình AI cục bộ
    ensure_ollama()
    
    # Step A: Validate pipeline is ready
    check_pipeline_dependencies()
    
    # Step B: Start concurrent services
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}===================================================================={Colors.ENDC}")
    print(f"{Colors.OKCYAN}{Colors.BOLD}🚀 Launching Backend & Frontend Concurrently...{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{Colors.BOLD}===================================================================={Colors.ENDC}\n")
    
    # Define execution commands
    backend_cmd = [sys.executable, "-m", "uvicorn", "api.api_service:app", "--host", "127.0.0.1", "--port", "8000"]
    frontend_cmd = ["npm", "run", "dev"]
    
    print(f"{Colors.BOLD}API Server:{Colors.ENDC} Port 8000 (swagger docs at http://127.0.0.1:8000/docs)")
    print(f"{Colors.BOLD}React Frontend:{Colors.ENDC} Port 5173 (url: http://localhost:5173)")
    print(f"{Colors.WARNING}Press Ctrl+C to terminate both servers concurrently.{Colors.ENDC}\n")
    
    # Start subprocesses
    # We set stdout/stderr to PIPE to prefix them
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    backend_proc = subprocess.Popen(
        backend_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace',
        env=env
    )
    
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd="frontend-react",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace',
        env=env,
        shell=sys.platform.startswith("win")
    )
    
    # Start logging threads
    t_backend = threading.Thread(target=log_reader, args=(backend_proc.stdout, "[API]", Colors.OKBLUE), daemon=True)
    t_frontend = threading.Thread(target=log_reader, args=(frontend_proc.stdout, "[DASH]", Colors.HEADER), daemon=True)
    
    t_backend.start()
    t_frontend.start()
    
    # Graceful shutdown handler
    def shutdown_servers(signum, frame):
        print(f"\n\n{Colors.WARNING}⏹ Received termination signal. Shutting down servers...{Colors.ENDC}")
        
        # Terminate processes
        for p, name in [(backend_proc, "API"), (frontend_proc, "Streamlit")]:
            if p.poll() is None:
                print(f"  Stopping {name} server...")
                p.terminate()
                
        # Wait a moment for gentle termination, force kill if they persist
        time.sleep(1.5)
        for p, name in [(backend_proc, "API"), (frontend_proc, "React")]:
            if p.poll() is None:
                print(f"  Force stopping {name} server...")
                p.kill()
                
        print(f"\n{Colors.OKGREEN}✔ Both servers stopped successfully. Safe to close terminal.{Colors.ENDC}")
        sys.exit(0)
        
    # Register Ctrl+C and exit signals
    signal.signal(signal.SIGINT, shutdown_servers)
    signal.signal(signal.SIGTERM, shutdown_servers)
    
    # Keep main thread alive and monitor processes
    try:
        while True:
            # If any of the servers crashes or exits, shut down the other and exit
            bp_status = backend_proc.poll()
            fp_status = frontend_proc.poll()
            
            if bp_status is not None:
                print(f"\n{Colors.FAIL}❌ Backend API Server exited unexpectedly with code {bp_status}!{Colors.ENDC}")
                shutdown_servers(None, None)
            if fp_status is not None:
                print(f"\n{Colors.FAIL}❌ React Frontend exited unexpectedly with code {fp_status}!{Colors.ENDC}")
                shutdown_servers(None, None)
                
            time.sleep(1.0)
    except KeyboardInterrupt:
        shutdown_servers(None, None)

if __name__ == "__main__":
    main()
