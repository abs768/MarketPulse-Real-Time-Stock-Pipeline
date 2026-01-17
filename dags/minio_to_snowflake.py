import os
import json
import boto3
import snowflake.connector
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "password123"
BUCKET = "bronze-transactions"
LOCAL_DIR = "/tmp/minio_downloads"
MAX_FILES_PER_RUN = int(os.getenv("MINIO_MAX_FILES", "250"))

SNOWFLAKE_USER = "bhavani"
SNOWFLAKE_PASSWORD = "Password@12345"
SNOWFLAKE_ACCOUNT = "bm47437.us-east-2.aws"
SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
SNOWFLAKE_DB = "STOCKS_MDS"
SNOWFLAKE_SCHEMA = "COMMON"

# Metadata file to track s3_key to local_path mapping
METADATA_FILE = os.path.join(LOCAL_DIR, "file_metadata.json")

def download_from_minio():
    """Download files from MinIO bucket"""
    logger.info("Starting MinIO download")
    os.makedirs(LOCAL_DIR, exist_ok=True)
    
    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    )

    continuation_token = None
    selected_objects = []

    while len(selected_objects) < MAX_FILES_PER_RUN:
        kwargs = {"Bucket": BUCKET, "MaxKeys": 1000}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        try:
            response = s3.list_objects_v2(**kwargs)
            contents = response.get("Contents", [])
            logger.info(f"list_objects_v2 response: {response}")
            logger.info(f"Objects in bucket: {[obj['Key'] for obj in contents]}")
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            raise
            
        contents = response.get("Contents", [])
        
        if not contents:
            logger.info("No objects found in bucket")
            break

        for obj in contents:
            key = obj["Key"]
            local_file = os.path.join(LOCAL_DIR, os.path.basename(key))
            
            try:
                s3.download_file(BUCKET, key, local_file)
                logger.info(f"Downloaded {key} -> {local_file}")
                selected_objects.append({"s3_key": key, "local_path": local_file})
            except Exception as e:
                logger.error(f"Failed to download {key}: {e}")
                continue

            if len(selected_objects) >= MAX_FILES_PER_RUN:
                break

        if len(selected_objects) >= MAX_FILES_PER_RUN:
            break

        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")
        else:
            break

    logger.info(f"Total files downloaded: {len(selected_objects)}")
    
    # Save metadata to file as backup
    with open(METADATA_FILE, 'w') as f:
        json.dump(selected_objects, f)
    logger.info(f"Saved metadata to {METADATA_FILE}")
    
    return selected_objects

def load_to_snowflake(**kwargs):
    """Load files to Snowflake and clean up"""
    ti = kwargs["ti"]
    file_records = ti.xcom_pull(task_ids="download_minio")
    
    logger.info(f"Received file_records: type={type(file_records)}, length={len(file_records) if file_records else 0}")
    
    if file_records and len(file_records) > 0:
        logger.info(f"First item type: {type(file_records[0])}")
        logger.info(f"First item: {file_records[0]}")
    
    # If XCom failed or returned unexpected format, try loading from metadata file
    if not file_records or not isinstance(file_records, list):
        logger.warning("Invalid file_records from XCom, attempting to load from metadata file")
        try:
            with open(METADATA_FILE, 'r') as f:
                file_records = json.load(f)
            logger.info(f"Loaded {len(file_records)} records from metadata file")
        except Exception as e:
            logger.error(f"Failed to load metadata file: {e}")
            raise ValueError("Could not retrieve file records from XCom or metadata file")
    
    # Validate structure - handle both dict and string cases
    if file_records and isinstance(file_records[0], str):
        logger.warning("XCom returned strings instead of dicts, reconstructing from local files")
        # If we only have paths, we can't reliably get s3_key, so try metadata file first
        if os.path.exists(METADATA_FILE):
            try:
                with open(METADATA_FILE, 'r') as f:
                    file_records = json.load(f)
                logger.info(f"Reconstructed {len(file_records)} records from metadata file")
            except Exception as e:
                logger.error(f"Failed to load metadata file: {e}")
                raise
        else:
            # Fallback: reconstruct from strings (won't have s3_key for deletion)
            logger.warning("Metadata file not found, reconstructing without s3_keys")
            file_records = [
                {"s3_key": os.path.basename(path), "local_path": path} 
                for path in file_records if isinstance(path, str)
            ]
            logger.warning(f"Reconstructed {len(file_records)} records (s3_key will be basename only)")
            # Note: MinIO cleanup will use basename as key - this may fail if keys have paths
    
    if not file_records:
        logger.info("No files to load.")
        return
    
    # Validate we have proper dict structure
    if not isinstance(file_records[0], dict) or 's3_key' not in file_records[0]:
        logger.error(f"Invalid record structure: {file_records[0]}")
        raise ValueError("File records must be dictionaries with 's3_key' and 'local_path'")

    conn = None
    cur = None
    
    try:
        # Connect to Snowflake
        logger.info("Connecting to Snowflake")
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DB,
            schema=SNOWFLAKE_SCHEMA,
        )
        cur = conn.cursor()

        # Upload files to stage
        logger.info(f"Uploading {len(file_records)} files to Snowflake stage")
        successful_uploads = 0
        for i, record in enumerate(file_records, 1):
            local_path = record["local_path"]
            
            if not os.path.exists(local_path):
                logger.warning(f"Local file not found: {local_path}")
                continue
                
            try:
                logger.info(f"[{i}/{len(file_records)}] Uploading {local_path}")
                cur.execute(f"PUT 'file://{local_path}' @%bronze_stock_quotes_raw OVERWRITE=TRUE")
                successful_uploads += 1
            except Exception as e:
                logger.error(f"Failed to upload {local_path}: {e}")
                continue
        
        logger.info(f"Successfully uploaded {successful_uploads}/{len(file_records)} files")

        if successful_uploads == 0:
            logger.warning("No files were uploaded successfully")
            return

        # Execute COPY INTO
        logger.info("Executing COPY INTO bronze_stock_quotes_raw")
        result = cur.execute(
            """
            COPY INTO bronze_stock_quotes_raw
            FROM @%bronze_stock_quotes_raw
            FILE_FORMAT = (TYPE=JSON)
            ON_ERROR = 'CONTINUE'
            """
        )
        
        # Log results (simplified - just show what happened)
        result_count = 0
        for row in result:
            result_count += 1
            logger.info(f"COPY result: {row}")
        
        logger.info(f"COPY INTO completed with {result_count} result rows")

        # Clean up Snowflake stage
        logger.info("Cleaning up Snowflake stage")
        for record in file_records:
            stage_file = os.path.basename(record["local_path"])
            try:
                cur.execute(f"REMOVE @%bronze_stock_quotes_raw/{stage_file}")
                logger.info(f"Removed {stage_file} from stage")
            except Exception as e:
                logger.warning(f"Failed to remove {stage_file} from stage: {e}")

        logger.info("Snowflake load completed successfully")

    except Exception as e:
        logger.error(f"Error in Snowflake operations: {e}", exc_info=True)
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        logger.info("Snowflake connection closed")

    # Clean up MinIO and local files
    logger.info("Starting cleanup of MinIO and local files")
    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    )

    for record in file_records:
        local_path = record["local_path"]
        s3_key = record["s3_key"]

        # Delete from MinIO
        try:
            s3.delete_object(Bucket=BUCKET, Key=s3_key)
            logger.info(f"Deleted {s3_key} from MinIO")
        except Exception as e:
            logger.warning(f"Failed to delete {s3_key} from MinIO: {e}")

        # Delete local file
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"Deleted local file {local_path}")
        except Exception as e:
            logger.warning(f"Failed to remove {local_path}: {e}")
    
    # Clean up metadata file
    try:
        if os.path.exists(METADATA_FILE):
            os.remove(METADATA_FILE)
            logger.info("Deleted metadata file")
    except Exception as e:
        logger.warning(f"Failed to remove metadata file: {e}")

    logger.info("Cleanup completed")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 11, 28),
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "minio_to_snowflake",
    default_args=default_args,
    schedule_interval="*/1 * * * *",
    catchup=False,
    max_active_runs=1,  # Prevent concurrent runs
) as dag:

    task1 = PythonOperator(
        task_id="download_minio",
        python_callable=download_from_minio,
    )

    task2 = PythonOperator(
        task_id="load_snowflake",
        python_callable=load_to_snowflake,
        provide_context=True,
    )

    task1 >> task2
