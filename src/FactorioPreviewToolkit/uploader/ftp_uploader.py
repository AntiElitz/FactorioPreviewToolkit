import ftplib
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from src.FactorioPreviewToolkit.shared.config import Config
from src.FactorioPreviewToolkit.shared.shared_constants import constants
from src.FactorioPreviewToolkit.shared.structured_logger import log, log_section
from src.FactorioPreviewToolkit.shared.user_facing_error import UserFacingError
from src.FactorioPreviewToolkit.uploader.base_uploader import BaseUploader

# The config for a viewer hosted in the same folder as the previews: images sit next to
# index.html, and the planet list is the JSON the uploader keeps refreshing.
_HOSTED_VIEWER_CONFIG = """// Written by the Factorio Preview Toolkit on every upload. Local edits are overwritten.
const viewerConfig = {
  planetPreviewSourceTemplate: "{planet}.png",
  planetPreviewSources: {},
  planetNamesSource: "remote_planet_names.json",

  overview: {
    visibleSideCells: 4,
    autoScrollSeconds: 0
  },

  showCopyMapStringButton: true,
  autoRefreshSeconds: 10,
  defaultTab: "auto",
  defaultZoom: { default: 1.5, aquilo: 3 }
};
"""

# ftplib.all_errors covers Error, OSError and EOFError, but a connection that was already
# closed locally leaves 'sock' as None, and ftplib then raises AttributeError from
# 'self.sock.sendall'. That is the ordinary idle-timeout case, so it has to be caught too.
_TRANSFER_ERRORS = ftplib.all_errors + (AttributeError,)


class FtpUploader(BaseUploader):
    """
    Uploads the previews to an FTP server, for anyone who has web hosting rather than a
    cloud drive.

    FTP has no concept of a share link, so unlike the rclone uploader this one cannot ask
    the server for a URL - the public address is built from 'ftp_public_base_url', which
    must point at the same folder the files are uploaded to.
    """

    def __init__(self) -> None:
        self._connection: ftplib.FTP | None = None

    def upload_all(self) -> None:
        """
        Uploads everything, then closes the connection.
        """
        try:
            super().upload_all()
        finally:
            self._disconnect()

    def upload_single(self, local_path: Path, remote_filename: str) -> str:
        """
        Uploads one file and returns its public URL.
        """
        config = Config.get()

        with log_section(f"📡 Uploading {local_path.name} to {config.ftp_host}..."):
            try:
                self._store(local_path, remote_filename)
            except _TRANSFER_ERRORS as first_error:
                # Servers drop idle connections, and a full run takes many minutes, so a
                # dead connection is expected rather than exceptional. Reconnect once.
                log.warning(f"⚠️ FTP transfer failed ({first_error}). Reconnecting and retrying.")
                self._disconnect()
                try:
                    self._store(local_path, remote_filename)
                except UserFacingError:
                    raise
                except _TRANSFER_ERRORS as second_error:
                    raise UserFacingError(
                        f"Could not upload '{remote_filename}' to the FTP server\n\n"
                        f"The server said: {second_error}\n\n"
                        f"What to check in config.ini:\n"
                        f"  - that the account may write in "
                        f"'{config.ftp_remote_dir or 'the login folder'}'\n"
                        f"  - 'ftp_remote_dir', in case it points somewhere unexpected\n"
                        f"  - that the account has space left on the server"
                    ) from second_error
            log.info("✅ Upload complete.")

        url = self._public_url(remote_filename)
        log.info(f"🔗 Public URL: {url}")
        return url

    def _store(self, local_path: Path, remote_filename: str) -> None:
        """
        Sends one file to the server over the (possibly newly opened) connection.
        """
        connection = self._connect()
        with local_path.open("rb") as file:
            connection.storbinary(f"STOR {remote_filename}", file)

    def _connect(self) -> ftplib.FTP:
        """
        Returns the open connection, opening and preparing one if needed.
        """
        if self._connection is not None:
            return self._connection

        config = Config.get()
        with log_section(f"🔌 Connecting to {config.ftp_host}:{config.ftp_port}..."):
            connection: ftplib.FTP
            if config.ftp_use_tls:
                connection = ftplib.FTP_TLS()
            else:
                log.warning(
                    "⚠️ 'ftp_use_tls' is off - the password and files are sent unencrypted."
                )
                connection = ftplib.FTP()

            try:
                connection.connect(config.ftp_host, config.ftp_port, timeout=30)
            except (TimeoutError, OSError) as e:
                # Nothing answered at all, so a setting is the suspect - most often SFTP
                # (port 22), which is a different protocol entirely.
                raise UserFacingError(
                    f"Could not reach the FTP server {config.ftp_host}:{config.ftp_port}\n\n"
                    f"The server did not answer: {e}\n\n"
                    f"What to check in config.ini:\n"
                    f"  - 'ftp_host' and 'ftp_port' (plain FTP is normally port 21)\n"
                    f"  - that your provider really offers FTP. If they only offer SFTP,\n"
                    f"    usually on port 22, this uploader cannot use it: SFTP is a\n"
                    f"    different protocol. Use 'upload_method = rclone' with an sftp\n"
                    f"    remote instead.\n"
                    f"  - that a firewall is not blocking outgoing connections"
                ) from e

            try:
                connection.login(config.ftp_user, config.ftp_password)
                if isinstance(connection, ftplib.FTP_TLS):
                    connection.prot_p()  # encrypt the data channel too, not just the login
            except (ftplib.error_perm, ftplib.error_proto) as e:
                if config.ftp_use_tls:
                    raise UserFacingError(
                        f"The FTP server refused the encrypted connection or the login\n\n"
                        f"The server said: {e}\n\n"
                        f"What to check in config.ini:\n"
                        f"  - if your provider does not support FTPS, set\n"
                        f"    'ftp_use_tls = false'. The password and the files are then\n"
                        f"    sent unencrypted, so prefer an account that can only write\n"
                        f"    to the preview folder.\n"
                        f"  - 'ftp_user' and 'ftp_password'"
                    ) from e
                raise UserFacingError(
                    f"The FTP server refused the login\n\n"
                    f"The server said: {e}\n\n"
                    f"Check 'ftp_user' and 'ftp_password' in config.ini."
                ) from e

            connection.set_pasv(True)

            self._connection = connection
            self._change_to_remote_dir(connection, config.ftp_remote_dir)
            log.info("✅ Connected.")

        return connection

    @staticmethod
    def _change_to_remote_dir(connection: ftplib.FTP, remote_dir: str) -> None:
        """
        Moves into the target folder, creating the parts that do not exist yet.
        """
        for part in [segment for segment in remote_dir.replace("\\", "/").split("/") if segment]:
            try:
                connection.cwd(part)
            except ftplib.error_perm:
                log.info(f"📁 Creating remote folder '{part}'.")
                try:
                    connection.mkd(part)
                    connection.cwd(part)
                except ftplib.error_perm as e:
                    raise UserFacingError(
                        f"Could not open or create the folder '{part}' on the FTP server\n\n"
                        f"The server said: {e}\n\n"
                        f"'ftp_remote_dir' in config.ini is '{remote_dir}', which is read\n"
                        f"relative to the folder the login lands in. What to check:\n"
                        f"  - that the path is right, and does not repeat a folder the\n"
                        f"    login already starts in\n"
                        f"  - that the account may create folders there"
                    ) from e

    def prepare_remote(self, planet_names: list[str]) -> str:
        """
        Puts the viewer itself next to the previews, so the upload folder is a working
        page rather than a directory listing of PNG files.

        This is what web hosting can do and a cloud drive cannot: the images, the planet
        list and the viewer all live at the same address, so 'ftp_public_base_url' is the
        whole setup - no fork, no GitHub Pages, no copying links by hand.
        """
        self._upload_viewer_files()
        self._delete_all_remote_previews()
        return super().prepare_remote(planet_names)

    def _upload_viewer_files(self) -> None:
        """
        Uploads index.html, the stylesheet, the scripts and a matching viewer config.
        """
        if not Config.get().ftp_upload_viewer:
            return

        viewer_dir = constants.VIEWER_DIR
        if not viewer_dir.is_dir():
            log.warning(f"⚠️ Viewer folder not found at '{viewer_dir}' - not uploading it.")
            return

        with log_section("🌐 Uploading the viewer next to the previews..."):
            for name in ("index.html", "style.css", "favicon.svg"):
                source = viewer_dir / name
                if source.exists():
                    self._store(source, name)

            for source in sorted((viewer_dir / "js").glob("*.js")):
                self._store_in_subfolder(source, source.name, "js")

            self._store_text(_HOSTED_VIEWER_CONFIG, "viewer_config.js")
            log.info(f"✅ Viewer available at {Config.get().ftp_public_base_url}")

    def _delete_all_remote_previews(self) -> None:
        """
        Removes every uploaded preview image, including planets this run no longer covers,
        so the folder never keeps images from an older map or an older mod set.
        """
        connection = self._connect()
        try:
            names = [name for name in connection.nlst() if name.lower().endswith(".png")]
        except _TRANSFER_ERRORS as e:
            log.warning(f"⚠️ Could not list the remote folder ({e}) - not clearing old images.")
            return

        for name in names:
            try:
                connection.delete(name)
            except _TRANSFER_ERRORS as e:
                log.warning(f"⚠️ Could not delete '{name}' on the server: {e}")
        if names:
            log.info(f"🗑️ Removed {len(names)} preview image(s) from the previous run.")

    def delete_remote_preview(self, planet: str) -> None:
        """
        Already handled in bulk by _delete_all_remote_previews().
        """

    def _store_in_subfolder(self, local_path: Path, remote_filename: str, subfolder: str) -> None:
        """
        Uploads a file into a subfolder of the target folder, then returns to the target.
        """
        connection = self._connect()
        self._change_to_remote_dir(connection, subfolder)
        try:
            with local_path.open("rb") as file:
                connection.storbinary(f"STOR {remote_filename}", file)
        finally:
            connection.cwd("..")

    def _store_text(self, text: str, remote_filename: str) -> None:
        """
        Uploads a small generated text file, without writing it to disk first.
        """
        connection = self._connect()
        connection.storbinary(f"STOR {remote_filename}", BytesIO(text.encode("utf-8")))

    @staticmethod
    def _public_url(remote_filename: str) -> str:
        """
        Builds the public URL of an uploaded file from the configured base URL.
        """
        base = Config.get().ftp_public_base_url.rstrip("/")
        return f"{base}/{quote(remote_filename)}"

    def _disconnect(self) -> None:
        """
        Closes the connection, ignoring a server that already hung up.
        """
        if self._connection is None:
            return
        try:
            self._connection.quit()
        except _TRANSFER_ERRORS:
            try:
                self._connection.close()
            except _TRANSFER_ERRORS:
                pass
        finally:
            self._connection = None
