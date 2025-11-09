from typing import List, Dict, Any, Optional
from src.domain.interfaces import UserRepository, StorageServiceInterface
from src.domain.entities import User
from werkzeug.datastructures import FileStorage
import logging
logger = logging.getLogger(__name__)

class GetClientUsersUseCase:
    """
    Caso de uso: Obtener usuarios con rol CLIENT.
    Depende de UserRepository (patrón de inyección de dependencias).
    """

    def __init__(self, user_repository: UserRepository, storage_service: StorageServiceInterface):
        self.repository = user_repository
        self.storage_service = storage_service

    def execute(self) -> List[Dict[str, Any]]:
        """
        Ejecuta la lógica de negocio para obtener la lista de usuarios CLIENT.
        """
        # 1. Obtener usuarios con rol CLIENT (Usando el Repositorio)
        users = self.repository.get_users_by_role('CLIENT')

        # 2. Si no hay usuarios
        if not users:
            return []

        # 3. Formatear datos según necesidades del negocio
        formatted_users = []
        for user in users:
            formatted_users.append({
                "user_id": user.user_id,
                "name": user.name,
                "last_name": user.last_name,
                "password": user.password,
                "identification": user.identification,
                "phone": user.phone,
                "address": user.address,
                "latitude": user.latitude,
                "longitude": user.longitude,
                "rol": user.role.value if hasattr(user.role, 'value') else user.role
            })

        return formatted_users

    def execute_by_seller(self, seller_id: int) -> List[Dict[str, Any]]:
        """
        Ejecuta la lógica de negocio para obtener la lista de usuarios CLIENT.
        """
        # 1. Obtener usuarios con rol CLIENT (Usando el Repositorio)
        users = self.repository.get_users_by_seller(seller_id)

        # 2. Si no hay usuarios
        if not users:
            return []

        # 3. Formatear datos según necesidades del negocio
        formatted_users = []
        for user in users:
            formatted_users.append({
                "client_id": user.client_id,
                "nit": user.nit,
                "phone": user.phone,
                "name": user.perfil,
                "address": user.address,
                "latitude": user.latitude,
                "longitude": user.longitude,
                "rol": user.role.value if hasattr(user.role, 'value') else user.role
            })

        return formatted_users

    def get_user_by_id(self, client_id: int) -> Optional[Dict[str, Any]]:
        """Llama al repositorio para obtener el perfil."""
        return self.repository.db_get_client_data(client_id)

    def get_visit_by_id(self, visit_id: int):
        """
        Recupera una visita por su ID desde el repositorio.
        Retorna None si no existe.
        """
        visit = self.repository.get_by_id(visit_id)
        return visit

    def upload_visit_evidences(self, visit_id: int, files: List[FileStorage]) -> List[Dict[str, Any]]:
        """
        Logica de negocio para procesar, subir y registrar las evidencias de una visita.
        """
        visit = self.repository.get_visit_by_id(visit_id)
        if visit is None:
            raise ValueError(f"La visita con ID {visit_id} no existe en el sistema.")

        saved_evidences = []

        for i, file in enumerate(files):
            file_name = file.filename
            content_type = file.mimetype

            file_type = "photo"
            if 'video' in content_type:
                file_type = "video"
            elif 'image' in content_type:
                file_type = "photo"

            logger.info(f"Procesando archivo {i+1}/{len(files)}: '{file_name}' (Tipo: {file_type}, Content-Type: {content_type}).")

            try:
                logger.debug(f"Subiendo archivo {file_name} a S3 (Bucket: {self.storage_service.BUCKET_NAME})...")

                url_file = self.storage_service.upload_file(
                    file=file,
                    visit_id=visit_id
                )

                db_data = {
                    "visit_id": visit_id,
                    "type": file_type,
                    "url_file": url_file,
                    "description": file_name,
                }

                new_evidence_data = self.repository.save_evidence(
                    visit_id=db_data['visit_id'],
                    url=db_data['url_file'],
                    type=db_data['type']
                )
                saved_evidences.append(new_evidence_data)

            except Exception as e:
                logger.error(f"Fallo en el almacenamiento o registro del archivo '{file_name}'.", exc_info=True)
                raise Exception(f"Fallo en el almacenamiento del archivo {file_name}") from e

        return saved_evidences