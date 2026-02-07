"""
OCR Helper for CAPTCHA Recognition and Text Extraction

依赖: 
- ddddocr: pip install ddddocr (验证码识别)
- pytesseract: pip install pytesseract (通用OCR，需要系统安装Tesseract)
"""

import logging
from typing import Optional
import base64

logger = logging.getLogger(__name__)


class OCRHelper:
    """OCR助手，用于识别验证码和提取文本"""
    
    def __init__(self):
        """初始化OCR助手（延迟加载ddddocr和Tesseract）"""
        self.ocr = None  # ddddocr实例
        self.tesseract_available = False  # Tesseract是否可用
        self._initialized = False
        logger.info("OCR助手已创建（延迟初始化）")
    
    def _ensure_initialized(self) -> bool:
        """
        确保OCR引擎已初始化
        
        Returns:
            True 如果初始化成功，False 如果失败
        """
        if self._initialized:
            return self.ocr is not None
        
        # 初始化 ddddocr（验证码识别）
        try:
            import ddddocr
            self.ocr = ddddocr.DdddOcr(show_ad=False)
            logger.info("✅ ddddocr 初始化成功")
        except ImportError:
            logger.warning("⚠️ ddddocr 未安装，验证码识别将回退到用户输入")
            logger.info("💡 安装方法: pip install ddddocr")
            self.ocr = None
        except Exception as e:
            logger.error(f"❌ ddddocr 初始化失败: {e}")
            self.ocr = None
        
        # 检查 Tesseract OCR（通用文本提取）
        try:
            import pytesseract
            from PIL import Image
            import io
            # 尝试运行 tesseract --version 检查是否安装
            pytesseract.get_tesseract_version()
            
            # 检查中文语言包是否可用
            try:
                langs = pytesseract.get_languages()
                has_chinese = 'chi_sim' in langs
                if has_chinese:
                    logger.info("✅ Tesseract OCR 可用（通用文本提取，支持中文）")
                else:
                    logger.warning("⚠️  Tesseract OCR 可用，但未安装中文语言包（chi_sim）")
                    logger.info("💡 安装中文语言包: brew install tesseract-lang (macOS) 或 apt-get install tesseract-ocr-chi-sim (Linux)")
            except Exception:
                # 如果无法获取语言列表，假设可用但可能没有中文包
                logger.info("✅ Tesseract OCR 可用（通用文本提取）")
                logger.info("💡 如需中文支持，请安装中文语言包: brew install tesseract-lang")
            
            self.tesseract_available = True
        except Exception as e:
            self.tesseract_available = False
            logger.debug(f"Tesseract OCR 不可用: {e}（可选，不影响基本功能）")
            logger.info("💡 如需更好的文本提取，可安装: brew install tesseract tesseract-lang && pip install pytesseract pillow")
        
        self._initialized = True
        return self.ocr is not None
    
    def recognize_captcha(self, image_base64: str, confidence_check: bool = True) -> Optional[str]:
        """
        识别验证码
        
        Args:
            image_base64: base64编码的图片（可包含data:image前缀）
            confidence_check: 是否进行置信度检查（长度、字符合法性）
        
        Returns:
            识别结果文本，失败返回None
        """
        if not self._ensure_initialized():
            return None
        
        if not self.ocr:
            return None
        
        try:
            # 移除 data:image 前缀
            if "base64," in image_base64:
                image_base64 = image_base64.split("base64,")[1]
            
            # 解码
            image_bytes = base64.b64decode(image_base64)
            
            # 识别
            result = self.ocr.classification(image_bytes)
            
            if not result or len(result) == 0:
                logger.warning("OCR识别结果为空")
                return None
            
            result = result.strip()
            
            # 置信度检查
            if confidence_check:
                # 检查1: 长度合理（验证码通常4-6位）
                if len(result) < 3 or len(result) > 8:
                    logger.warning(f"OCR识别结果长度异常: {len(result)} ({result})")
                    return None
                
                # 检查2: 只包含字母数字（过滤乱码）
                if not result.replace(" ", "").isalnum():
                    logger.warning(f"OCR识别结果包含非法字符: {result}")
                    return None
            
            logger.info(f"✅ OCR识别成功: {result} (长度: {len(result)})")
            return result
                
        except Exception as e:
            logger.error(f"❌ OCR识别失败: {e}", exc_info=True)
            return None
    
    def extract_text(self, image_base64: str) -> Optional[str]:
        """
        提取图片中的所有文本（通用OCR，不限制长度和字符类型）
        
        优先使用 Tesseract OCR（如果可用），否则回退到 ddddocr
        
        Args:
            image_base64: base64编码的图片（可包含data:image前缀）
        
        Returns:
            提取的文本，失败返回None
        """
        if not self._ensure_initialized():
            return None
        
        try:
            # 移除 data:image 前缀
            if "base64," in image_base64:
                image_base64 = image_base64.split("base64,")[1]
            
            # 解码
            image_bytes = base64.b64decode(image_base64)
            
            # 优先尝试 Tesseract OCR（更强大的通用OCR）
            if self.tesseract_available:
                try:
                    import pytesseract
                    from PIL import Image
                    import io
                    
                    # 将字节转换为PIL Image
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # 使用 Tesseract 提取文本（支持中英文）
                    # 配置：使用中文+英文，保持布局
                    try:
                        # 检查中文语言包是否可用
                        langs = pytesseract.get_languages()
                        if 'chi_sim' in langs:
                            lang = 'chi_sim+eng'  # 中文简体 + 英文
                        else:
                            lang = 'eng'  # 仅英文（中文语言包未安装）
                            logger.warning("⚠️  中文语言包未安装，仅使用英文识别")
                    except Exception:
                        # 如果无法获取语言列表，尝试使用中文+英文，失败则降级
                        lang = 'chi_sim+eng'
                    
                    result = pytesseract.image_to_string(
                        image,
                        lang=lang,
                        config='--psm 6'  # 假设统一文本块
                    )
                    
                    if result and len(result.strip()) > 0:
                        result = result.strip()
                        logger.info(f"✅ Tesseract OCR文本提取成功（长度: {len(result)}）")
                        return result
                    else:
                        logger.debug("Tesseract OCR 未提取到文本，尝试 ddddocr")
                except Exception as e:
                    logger.debug(f"Tesseract OCR 提取失败，回退到 ddddocr: {e}")
            
            # 回退到 ddddocr（主要用于验证码，对复杂场景效果有限）
            if self.ocr:
                result = self.ocr.classification(image_bytes)
                
                if not result or len(result) == 0:
                    logger.warning("OCR文本提取结果为空")
                    return None
                
                result = result.strip()
                
                # 如果提取的文字很少（少于10个字符），可能是 ddddocr 的限制
                if len(result) < 10:
                    logger.warning(f"⚠️ ddddocr 提取的文字较少（{len(result)}字符），可能不完整")
                    logger.info("💡 建议：安装 Tesseract OCR 以获得更好的文本提取效果（brew install tesseract && pip install pytesseract pillow）")
                
                logger.info(f"✅ ddddocr OCR文本提取成功（长度: {len(result)}）")
                return result
            else:
                logger.warning("⚠️ OCR不可用（ddddocr和Tesseract均不可用）")
                return None
                
        except Exception as e:
            logger.error(f"❌ OCR文本提取失败: {e}", exc_info=True)
            return None
    
    def is_available(self) -> bool:
        """
        检查OCR是否可用
        
        Returns:
            True 如果可用
        """
        return self._ensure_initialized() and self.ocr is not None
