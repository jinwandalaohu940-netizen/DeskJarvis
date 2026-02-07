"""
File Compressor Module

支持文件和文件夹压缩为zip格式
"""

import logging
import zipfile
from pathlib import Path
from typing import List, Union

logger = logging.getLogger(__name__)


class FileCompressor:
    """文件压缩器"""
    
    @staticmethod
    def compress_files(
        files: List[Union[str, Path]],
        output_path: Union[str, Path],
        compression_type: str = "zip"
    ) -> str:
        """
        压缩文件或文件夹为zip
        
        Args:
            files: 文件或文件夹路径列表
            output_path: 输出zip文件路径
            compression_type: 压缩类型（目前只支持zip）
        
        Returns:
            压缩后的文件路径
        
        Raises:
            FileNotFoundError: 如果文件不存在
            ValueError: 如果压缩类型不支持
        """
        if compression_type != "zip":
            raise ValueError(f"不支持的压缩类型: {compression_type}")
        
        output_path = Path(output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"开始压缩 {len(files)} 个文件/文件夹...")
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    file_path = Path(file_path).expanduser().resolve()
                    
                    if not file_path.exists():
                        raise FileNotFoundError(f"文件不存在: {file_path}")
                    
                    if file_path.is_file():
                        # 添加单个文件
                        zipf.write(file_path, arcname=file_path.name)
                        logger.debug(f"已添加文件: {file_path.name}")
                    elif file_path.is_dir():
                        # 递归添加文件夹
                        for item in file_path.rglob("*"):
                            if item.is_file():
                                # 保持文件夹结构
                                arcname = item.relative_to(file_path.parent)
                                zipf.write(item, arcname=arcname)
                                logger.debug(f"已添加文件: {arcname}")
            
            file_size = output_path.stat().st_size
            logger.info(f"✅ 压缩完成: {output_path} ({file_size / 1024 / 1024:.2f} MB)")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"压缩失败: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_compressed_size(file_path: Union[str, Path]) -> int:
        """
        获取压缩文件大小（字节）
        
        Args:
            file_path: 压缩文件路径
        
        Returns:
            文件大小（字节）
        """
        return Path(file_path).stat().st_size
