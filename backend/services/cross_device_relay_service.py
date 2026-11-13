"""
Cross-Device File Relay Service.
Securely stages files for cross-device transfer between Windows and Android nodes.
"""

from __future__ import annotations
import os
import uuid
import time
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from backend.config.settings import settings
from backend.database.database import SessionLocal
from backend.database.models import CrossDeviceTransfer
from backend.models.device_schemas import CrossDeviceTransferMetadata

logger = logging.getLogger(__name__)


class CrossDeviceRelayService:
    def __init__(self):
        self.relay_dir = Path("data/relay")
        self.relay_dir.mkdir(parents=True, exist_ok=True)

    def stage_file_from_path(
        self,
        source_device_id: str,
        target_device_id: str,
        source_file_path: str
    ) -> CrossDeviceTransferMetadata:
        """
        Stages a local file into the relay cache for transfer to another device.
        """
        src = Path(source_file_path).resolve()
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Source file not found: {source_file_path}")

        transfer_id = f"relay_{uuid.uuid4().hex[:12]}"
        dest_filename = f"{transfer_id}_{src.name}"
        dest_path = self.relay_dir / dest_filename

        shutil.copy2(src, dest_path)
        file_size = dest_path.stat().st_size

        mime_type = "application/pdf" if src.suffix.lower() == ".pdf" else "application/octet-stream"

        with SessionLocal() as db:
            record = CrossDeviceTransfer(
                transfer_id=transfer_id,
                source_device_id=source_device_id,
                target_device_id=target_device_id,
                file_name=src.name,
                file_size_bytes=file_size,
                file_path=str(dest_path),
                mime_type=mime_type,
                status="ready_for_download"
            )
            db.add(record)
            db.commit()

        return CrossDeviceTransferMetadata(
            transfer_id=transfer_id,
            source_device_id=source_device_id,
            target_device_id=target_device_id,
            filename=src.name,
            file_size_bytes=file_size,
            mime_type=mime_type,
            status="ready_for_download",
            download_url=f"/api/relay/download/{transfer_id}",
            created_at=time.time()
        )

    def stage_file_from_bytes(
        self,
        source_device_id: str,
        target_device_id: str,
        filename: str,
        data: bytes
    ) -> CrossDeviceTransferMetadata:
        """
        Stages file content from memory or upload into the relay cache.
        """
        transfer_id = f"relay_{uuid.uuid4().hex[:12]}"
        dest_filename = f"{transfer_id}_{filename}"
        dest_path = self.relay_dir / dest_filename

        with open(dest_path, "wb") as f:
            f.write(data)

        file_size = len(data)
        mime_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"

        with SessionLocal() as db:
            record = CrossDeviceTransfer(
                transfer_id=transfer_id,
                source_device_id=source_device_id,
                target_device_id=target_device_id,
                file_name=filename,
                file_size_bytes=file_size,
                file_path=str(dest_path),
                mime_type=mime_type,
                status="ready_for_download"
            )
            db.add(record)
            db.commit()

        return CrossDeviceTransferMetadata(
            transfer_id=transfer_id,
            source_device_id=source_device_id,
            target_device_id=target_device_id,
            filename=filename,
            file_size_bytes=file_size,
            mime_type=mime_type,
            status="ready_for_download",
            download_url=f"/api/relay/download/{transfer_id}",
            created_at=time.time()
        )

    def get_staged_file(self, transfer_id: str) -> Optional[Tuple[Path, str, str]]:
        """
        Retrieves path, original filename, and mime type for a transfer ID.
        """
        with SessionLocal() as db:
            rec = db.query(CrossDeviceTransfer).filter(CrossDeviceTransfer.transfer_id == transfer_id).first()
            if not rec or not rec.file_path:
                return None
            p = Path(rec.file_path)
            if not p.exists():
                return None
            return (p, rec.file_name, rec.mime_type or "application/octet-stream")


cross_device_relay_service = CrossDeviceRelayService()
