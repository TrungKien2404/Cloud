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

def main():
    print_banner()
    
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
