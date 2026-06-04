# Databricks notebook source
# ====================================================================
# DATABRICKS NOTEBOOK - STEP 5: ORCHESTRATION PIPELINE
# ====================================================================
# Path: /Workspace/stock-prediction/05_run_pipeline
# Description: Chạy tuần tự các bước trong Databricks stock prediction pipeline
# ====================================================================

# COMMAND ----------

import os
import sys
import logging

# Đảm bảo các luồng stdout/stderr trên Windows luôn sử dụng mã hóa UTF-8 để chống lỗi Unicode/charmap
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("05_run_pipeline")

# COMMAND ----------

# ========== ENVIRONMENT DETECTION ==========
IS_DATABRICKS = "DATABRICKS_RUNTIME_VERSION" in os.environ

# COMMAND ----------

# ========== RUN PIPELINE STEPS ==========
print("=" * 60)
print("🚀 RUNNING FULL STOCK PREDICTION PIPELINE")
print("=" * 60 + "\n")

steps = [
    ("01_ingestion", "Step 1: Data Ingestion (Yahoo Finance -> Delta/Parquet)"),
    ("02_feature_engineering", "Step 2: Feature Engineering (Technical Indicators & Splits)"),
    ("03_train_models", "Step 3: Model Training (Train 5 ML Models -> Select Best Model)"),
    ("04_batch_prediction", "Step 4: Batch Prediction (Generate Predictions for Next Day)")
]

if IS_DATABRICKS:
    # Chạy trên Databricks bằng dbutils
    try:
        # Lấy dbutils từ globals (mặc định có sẵn trên Databricks notebook)
        dbutils = globals().get("dbutils")
        if dbutils is None:
            # Import dự phòng
            from pyspark.dbutils import DBUtils
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.getOrCreate()
            dbutils = DBUtils(spark)
            
        for notebook_name, description in steps:
            print(f"▶ Kích hoạt {description}...")
            # dbutils.notebook.run() nhận đường dẫn tương đối hoặc tuyệt đối
            # Ta truyền timeout là 1800 giây (30 phút) cho mỗi bước
            result = dbutils.notebook.run(notebook_name, 1800)
            print(f"✅ {notebook_name} hoàn thành! Kết quả: {result}\n")
            
        print("✓ HỆ THỐNG PIPELINE DATABRICKS ĐÃ CHẠY HOÀN TẤT THÀNH CÔNG!")
        
    except Exception as e:
        logger.error(f"❌ Lỗi trong quá trình chạy Pipeline trên Databricks: {e}")
        raise e
else:
    # Chạy cục bộ bằng Python (để lập trình viên dễ test mà không cần Databricks)
    print("ℹ️ Đang chạy ở chế độ cục bộ (Local Fallback)...")
    notebook_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    
    for notebook_name, description in steps:
        notebook_path = os.path.join(notebook_dir, f"{notebook_name}.py")
        if not os.path.exists(notebook_path):
            notebook_path = os.path.join(".", "notebooks", f"{notebook_name}.py")
            
        print(f"▶ Kích hoạt cục bộ: {description} (Đường dẫn: {notebook_path})...")
        
        try:
            # Thực thi file Python trực tiếp trong context hiện tại
            with open(notebook_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
                
            # Loại bỏ các lệnh magic của Databricks như %pip và %magic để tránh SyntaxError cục bộ
            clean_lines = []
            for line in code_content.split('\n'):
                if line.strip().startswith('%pip') or line.strip().startswith('%magic') or line.strip().startswith('%%'):
                    clean_lines.append("# " + line)
                else:
                    clean_lines.append(line)
            
            clean_code = '\n'.join(clean_lines)
            
            # Exec code
            exec(clean_code, globals())
            print(f"✅ {notebook_name} hoàn thành cục bộ thành công!\n")
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi chạy bước {notebook_name} cục bộ: {e}")
            raise e
            
    print("✓ HỆ THỐNG PIPELINE CỤC BỘ ĐÃ CHẠY HOÀN TẤT THÀNH CÔNG!")

# COMMAND ----------

print("\n" + "="*60)
print("🏁 FULL ORCHESTRATION PIPELINE COMPLETED")
print("="*60)
