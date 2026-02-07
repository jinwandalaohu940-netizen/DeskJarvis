"""
Email Reader Module - Handles fetching and searching emails via IMAP
"""

import imaplib
import email
from email.header import decode_header
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class EmailReader:
    def __init__(self, imap_server: str, imap_port: int = 993):
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.mail = None

    def connect(self, email_user: str, email_pass: str) -> bool:
        """Connect and login to IMAP server"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.mail.login(email_user, email_pass)
            logger.info(f"Successfully connected to IMAP: {self.imap_server}")
            return True
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            return False

    def _select_mailbox(self, folder: str = "INBOX") -> bool:
        """
        智能文件夹选择器 (Protocol E)
        优先级：INBOX -> 收件箱 -> 已发送 -> [GMAIL]/ALL MAIL
        """
        if not self.mail:
            return False
        
        # 1. 尝试直接选择用户指定的文件夹
        try:
            status, _ = self.mail.select(folder)
            if status == 'OK':
                return True
        except:
            pass

        # 2. 如果失败，开始“盲猜”逻辑
        fallbacks = ["INBOX", "收件箱", "已发送", "SENT", "[GMAIL]/ALL MAIL", "Junk"]
        for fb in fallbacks:
            if fb.lower() == folder.lower():
                continue
            try:
                status, _ = self.mail.select(fb)
                if status == 'OK':
                    logger.info(f"文件夹选择回退：{folder} -> {fb}")
                    return True
            except:
                continue
        
        # 3. 最后手段：列出所有文件夹并尝试第一个
        try:
            status, folder_list = self.mail.list()
            if status == 'OK':
                for f_info in folder_list:
                    f_name = f_info.decode().split(' "/" ')[-1].strip('"')
                    if f_name not in fallbacks:
                        status, _ = self.mail.select(f_name)
                        if status == 'OK':
                            logger.info(f"最终回退：使用文件夹 {f_name}")
                            return True
        except:
            pass
            
        return False

    def search_emails(self, query: str = "ALL", folder: str = "INBOX", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for emails matching the query.
        Returns a list of metadata (id, subject, from, date).
        使用 BODY.PEEK[HEADER.FIELDS] 替代 RFC822，提升性能，避免阻塞。
        """
        if not self.mail:
            return []

        if not self._select_mailbox(folder):
            logger.error(f"无法选择文件夹: {folder}")
            return []

        try:
            # USE UID SEARCH to get stable identifiers
            status, messages = self.mail.uid('search', None, query)
            
            if status != 'OK':
                logger.error(f"UID Search failed: {status}")
                return []

            email_ids = messages[0].split()
            # Get latest emails first
            email_ids = list(reversed(email_ids))[:limit]
            
            results = []
            for e_id in email_ids:
                # Ensure e_id is string
                uid_str = e_id.decode() if isinstance(e_id, bytes) else str(e_id)
                
                # 使用 BODY.PEEK[HEADER.FIELDS] 仅拉取头部，极大提升速度，避免阻塞
                status, msg_data = self.mail.uid('fetch', uid_str, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])')
                if status != 'OK' or not msg_data or msg_data[0] is None:
                    continue
                
                # Parse header
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                subject = self._decode_mime_header(msg.get("Subject", "No Subject"))
                sender = self._decode_mime_header(msg.get("From", "Unknown"))
                date = msg.get("Date", "")
                
                results.append({
                    "id": uid_str,
                    "subject": subject,
                    "from": sender,
                    "date": date
                })
            
            return results
        except Exception as e:
            logger.error(f"Error during email search: {e}")
            return []

    def download_attachments(self, msg_id: str, save_dir: str, folder: str = "INBOX", file_type: Optional[str] = None, limit: Optional[int] = None) -> List[str]:
        """Download attachments from an email with optional type filtering and limit"""
        if not self.mail:
            return []

        if not self._select_mailbox(folder):
            logger.error(f"无法选择文件夹: {folder}")
            return []

        # Ensure msg_id is string (Protocol UID Type)
        uid_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)

        try:
            # Use UID FETCH
            status, msg_data = self.mail.uid('fetch', uid_str, '(RFC822)')
            if status != 'OK':
                logger.error(f"UID Fetch failed for {uid_str}: {status}")
                return []

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            os_save_dir = Path(save_dir).expanduser().resolve()
            os_save_dir.mkdir(parents=True, exist_ok=True)
            
            saved_paths = []
            download_count = 0
            
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if filename:
                    # Decode filename
                    filename = self._decode_mime_header(filename)
                    
                    # Extension Filter
                    if file_type:
                        ext = Path(filename).suffix.lower().lstrip('.')
                        if ext != file_type.lower().lstrip('.'):
                            continue
                            
                    # Limit Filter
                    if limit and download_count >= limit:
                        break
                        
                    filepath = os_save_dir / filename
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    
                    saved_paths.append(str(filepath))
                    download_count += 1
            
            return saved_paths
        except Exception as e:
            logger.error(f"Error downloading attachments: {e}")
            return []

    def get_email_content(self, msg_id: str, folder: str = "INBOX") -> Dict[str, Any]:
        """
        Fetch full content of an email by ID.
        统一返回结构，确保即使失败也包含 body 键，防止 'NoneType' object is not subscriptable 错误。
        使用 BODY.PEEK[] 获取正文，避免意外改变邮件未读状态。
        """
        # 统一返回结构，确保即使失败也包含所有必需键
        res = {"id": msg_id, "subject": "", "from": "", "body": "", "date": "", "error": None}
        
        if not self.mail:
            res["error"] = "Connection error"
            return res

        if not self._select_mailbox(folder):
            res["error"] = "Mailbox selection failed"
            return res

        # Ensure msg_id is string
        uid_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)

        try:
            # 使用 BODY.PEEK[] 获取正文，避免意外改变邮件未读状态
            status, msg_data = self.mail.uid('fetch', uid_str, '(BODY.PEEK[])')
            if status != 'OK' or not msg_data:
                res["error"] = f"Failed to fetch content for {uid_str}: {status}"
                return res

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            subject = self._decode_mime_header(msg.get("Subject", ""))
            sender = self._decode_mime_header(msg.get("From", ""))
            date = msg.get("Date", "")
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        body = payload.decode(errors='ignore') if payload else ""
                        break
            else:
                payload = msg.get_payload(decode=True)
                body = payload.decode(errors='ignore') if payload else ""
            
            res.update({
                "subject": subject,
                "from": sender,
                "body": body,
                "date": date
            })
            return res
        except Exception as e:
            logger.error(f"Error fetching email content: {e}")
            res["error"] = str(e)
            return res

    def manage_email(self, msg_id: str, action: str, target_folder: Optional[str] = None, current_folder: str = "INBOX") -> bool:
        """Move, archive, or mark email as read"""
        if not self.mail:
            return False

        if not self._select_mailbox(current_folder):
            logger.error(f"无法选择文件夹: {current_folder}")
            return False

        # Ensure msg_id is string
        uid_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)

        try:
            if action == "mark_read":
                # Use UID STORE
                self.mail.uid('store', uid_str, '+FLAGS', '\\Seen')
                return True
            elif action == "move" and target_folder:
                # Use UID COPY
                result = self.mail.uid('copy', uid_str, target_folder)
                if result[0] == 'OK':
                    # Use UID STORE for deletion
                    self.mail.uid('store', uid_str, '+FLAGS', '\\Deleted')
                    self.mail.expunge()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error managing email: {e}")
            return False

    def _decode_mime_header(self, header: str) -> str:
        """强化版 MIME 头部解码，处理复杂的编码格式"""
        if not header:
            return ""
        try:
            decoded_list = decode_header(header)
            result = ""
            for content, encoding in decoded_list:
                if isinstance(content, bytes):
                    try:
                        # 尝试使用指定的编码，如果失败则尝试 utf-8 或 gbk
                        result += content.decode(encoding or 'utf-8', errors='ignore')
                    except Exception:
                        result += content.decode('gbk', errors='ignore')
                else:
                    result += content
            return result
        except Exception as e:
            logger.warning(f"Decoding header failed: {e}")
            return str(header)

    def disconnect(self):
        if self.mail:
            try:
                self.mail.logout()
            except:
                pass
            self.mail = None
