# src/services/storage_service.py

import boto3
from botocore.exceptions import ClientError
import logging
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

class StorageService:
    BUCKET_NAME = "medisupply-visual-evidences" 
    VISUAL_EVIDENCE_BUCKET_PATH = "visits/visual_evidences" 

    s3_client = boto3.client('s3')

    @staticmethod
    def upload_file(file: FileStorage, visit_id: int) -> str:
        file_name = file.filename
        content_type = file.mimetype or 'application/octet-stream' 
        
        bucket_path = f"{StorageService.VISUAL_EVIDENCE_BUCKET_PATH}/{visit_id}/{file_name}"

        try:
            StorageService.s3_client.upload_fileobj(
                Fileobj=file.stream, 
                Bucket=StorageService.BUCKET_NAME, 
                Key=bucket_path,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'private'
                }
            )
            url_file = f"https://{StorageService.BUCKET_NAME}.s3.amazonaws.com/{bucket_path}"
            
            return url_file
            
        except ClientError as e:
            logger.error(f"Error de cliente S3 al subir {file_name} a {bucket_path}: {e}")
            raise Exception("Error en el servicio de almacenamiento (S3 Client Error)") from e
            
        except Exception as e:
            logger.error(f"Error inesperado al subir el archivo {file_name}: {e}")
            raise Exception("Error inesperado durante la subida de evidencia") from e