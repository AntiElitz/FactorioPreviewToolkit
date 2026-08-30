from src.FactorioPreviewToolkit.shared.config import Config
from src.FactorioPreviewToolkit.uploader.base_uploader import BaseUploader
from src.FactorioPreviewToolkit.uploader.ftp_uploader import FtpUploader
from src.FactorioPreviewToolkit.uploader.local_sync_uploader import LocalSyncUploader
from src.FactorioPreviewToolkit.uploader.rclone_uploader import RcloneUploader
from src.FactorioPreviewToolkit.uploader.skip_uploader import SkipUploader


def get_uploader() -> BaseUploader:
    """
    Returns the configured uploader instance based on the upload_method in config.
    Raises an error if the method is unsupported or disabled.
    """
    match Config.get().upload_method:
        case "rclone":
            return RcloneUploader()
        case "ftp":
            return FtpUploader()
        case "local_sync":
            return LocalSyncUploader()
        case "skip":
            return SkipUploader()
        case other:
            raise ValueError(f"Unsupported upload method: {other}")
