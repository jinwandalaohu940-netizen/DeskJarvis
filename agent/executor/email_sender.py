"""
Email Sender Module

支持通过SMTP发送邮件，包括附件
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import List, Union, Optional

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器"""
    
    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        use_tls: bool = True
    ):
        """
        初始化邮件发送器
        
        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            use_tls: 是否使用TLS加密
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.use_tls = use_tls
        logger.info(f"邮件发送器已初始化: {smtp_server}:{smtp_port}")
    
    def send_email(
        self,
        sender_email: str,
        sender_password: str,
        recipient: Union[str, List[str]],
        subject: str,
        body: str,
        attachments: Optional[List[Union[str, Path]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False
    ) -> dict:
        """
        发送邮件
        
        Args:
            sender_email: 发件人邮箱
            sender_password: 发件人密码（或应用专用密码）
            recipient: 收件人（单个或列表）
            subject: 邮件主题
            body: 邮件正文
            attachments: 附件文件路径列表
            cc: 抄送列表
            bcc: 密送列表
            html: 邮件正文是否为HTML格式
        
        Returns:
            {"success": bool, "message": str}
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient if isinstance(recipient, str) else ", ".join(recipient)
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ", ".join(cc)
            if bcc:
                msg['Bcc'] = ", ".join(bcc)
            
            # 添加正文
            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, content_type, 'utf-8'))
            
            # 添加附件
            if attachments:
                for file_path in attachments:
                    file_path = Path(file_path).expanduser().resolve()
                    
                    if not file_path.exists():
                        logger.warning(f"附件不存在，跳过: {file_path}")
                        continue
                    
                    # 检查文件大小（25MB限制）
                    file_size = file_path.stat().st_size
                    if file_size > 25 * 1024 * 1024:  # 25MB
                        logger.warning(f"附件过大（{file_size / 1024 / 1024:.2f}MB），可能被拒绝: {file_path.name}")
                    
                    with open(file_path, 'rb') as f:
                        part = MIMEApplication(f.read(), Name=file_path.name)
                        part['Content-Disposition'] = f'attachment; filename="{file_path.name}"'
                        msg.attach(part)
                        logger.info(f"已添加附件: {file_path.name} ({file_size / 1024:.2f} KB)")
            
            # 连接SMTP服务器并发送
            logger.info(f"正在连接SMTP服务器: {self.smtp_server}:{self.smtp_port}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                server.login(sender_email, sender_password)
                logger.info("✅ SMTP登录成功")
                
                # 发送邮件
                recipients_list = [recipient] if isinstance(recipient, str) else recipient
                if cc:
                    recipients_list.extend(cc)
                if bcc:
                    recipients_list.extend(bcc)
                
                server.send_message(msg)
                logger.info(f"✅ 邮件已发送到: {msg['To']}")
            
            return {
                "success": True,
                "message": f"邮件已成功发送到 {msg['To']}",
                "data": {
                    "recipient": msg['To'],
                    "subject": subject,
                    "attachments_count": len(attachments) if attachments else 0
                }
            }
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP认证失败: {e}. 请检查邮箱和密码（可能需要使用应用专用密码）"
            logger.error(error_msg)
            return {"success": False, "message": error_msg, "data": None}
            
        except smtplib.SMTPException as e:
            error_msg = f"SMTP错误: {e}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg, "data": None}
            
        except Exception as e:
            error_msg = f"发送邮件失败: {e}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg, "data": None}
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        简单的邮箱格式验证
        
        Args:
            email: 邮箱地址
        
        Returns:
            True 如果格式有效
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
