"""
Reflector Component - AI Error Analysis & Self-Healing

Responsibility:
- Analyze execution failures
- Determine if the error is recoverable
- Propose a fixed step (Self-Healing)
"""

import logging
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from openai import OpenAI
from agent.tools.config import Config

logger = logging.getLogger(__name__)

@dataclass
class ReflectorResult:
    is_retryable: bool
    modified_step: Optional[Dict[str, Any]]
    reason: str

class Reflector:
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self.provider = config.provider.lower()
        self.model = config.model
        
        api_key = config.api_key
        logger.info(f"Reflector: config.provider='{config.provider}', config.api_key exists={'Yes' if api_key else 'No'}")
        
        if not api_key:
            logger.warning("Reflector: No API Key found. Self-healing disabled.")
            return

        try:
            p_clean = self.provider.strip().lower()
            if p_clean == "claude":
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
                logger.info(f"Reflector initialized with Anthropic client (Provider: {p_clean})")
            elif p_clean == "deepseek":
                self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                logger.info(f"Reflector initialized with DeepSeek client (Base URL: {self.client.base_url})")
            elif p_clean == "grok":
                self.client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
                logger.info(f"Reflector initialized with Grok client (Base URL: {self.client.base_url})")
            else:
                # Default to OpenAI
                self.client = OpenAI(api_key=api_key)
                logger.info(f"Reflector initialized with DEFAULT OpenAI client (Provider: '{p_clean}', Base URL: {self.client.base_url})")
        except Exception as e:
            logger.warning(f"Reflector initialization failed (Self-healing disabled): {e}")

    def analyze_failure(
        self, 
        step: Dict[str, Any], 
        error_message: str, 
        context_summary: str = ""
    ) -> ReflectorResult:
        """
        Analyze the failed step and error to propose a fix.
        """
        if not self.client:
            return ReflectorResult(False, None, "Reflector not configured (No API Key)")

        logger.info(f"Reflector process started for step: {step.get('action')}")
        
        prompt = self._build_reflection_prompt(step, error_message, context_summary)
        
        try:
            if self.provider == "claude":
                # Anthropic API call
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    system="You are an expert Python Debugger and Agentic Planner. Your goal is to fix failed automation steps. Respond ONLY with a JSON object.",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                )
                content = response.content[0].text
            else:
                # OpenAI / DeepSeek / Grok API call
                kwargs = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are an expert Python Debugger and Agentic Planner. Your goal is to fix failed automation steps. Respond ONLY with a JSON object."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                }
                
                # DeepSeek and newer OpenAI models support JSON mode
                if self.provider in ["openai", "deepseek"]:
                    kwargs["response_format"] = {"type": "json_object"}
                
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content

            # Parse JSON with fallback extraction
            try:
                result_json = json.loads(content)
            except json.JSONDecodeError:
                # Manual extraction if AI included preamble/postamble
                import re
                match = re.search(r'(\{.*\})', content, re.DOTALL)
                if match:
                    result_json = json.loads(match.group(1))
                else:
                    raise
            
            return ReflectorResult(
                is_retryable=result_json.get("is_retryable", False),
                modified_step=result_json.get("modified_step"),
                reason=result_json.get("reason", "No reason provided")
            )
            
        except Exception as e:
            logger.error(f"Reflector analysis failed: {e}", exc_info=True)
            return ReflectorResult(False, None, f"Reflector Error: {e}")

    def _build_reflection_prompt(self, step: Dict[str, Any], error: str, context: str) -> str:
        return f"""
The following agent step failed during execution.
Please analyze the error and provide a fixed version of the step if possible.

**Failed Step**:
{json.dumps(step, indent=2, ensure_ascii=False)}

**Error Message**:
{error}

**Context**:
{context}

**Instructions**:
1. Analyze why the step failed (e.g., SyntaxError, FileNotFoundError, Invalid Parameter).
2. If the error is specific to Python script content (e.g., SyntaxError, missing import), rewrite the 'code' or 'script' parameter in the `modified_step`.
3. If the path was wrong, try to correct it based on common conventions or safety rules (e.g. use `~/Desktop`).
4. **Important**: Return a JSON object with the following structure:
{{
    "is_retryable": boolean,      // Can we try again with a fix?
    "reason": "string",           // Brief explanation of the fix
    "modified_step": object|null  // The complete, corrected step object (or null if not retryable)
}}

**Rules for Fixes**:
- If it's a Python Syntax Error, fix the code.
- If it's a "File Not Found" for a screenshot/download, ensure the path exists or use a more robust path.
- Keep the `type` of the step the same unless the tool itself was wrong.

**⚠️ NON-RETRYABLE ERRORS (Set is_retryable: false)**:
These errors require **user configuration** and cannot be fixed by modifying the step:
- **Configuration errors**: Missing API Key, wrong provider/model configuration (e.g., "DeepSeek 不支持视觉功能", "VLM不可用：未配置API Key")
- **Missing dependencies**: Missing Python packages that require manual installation (e.g., "ddddocr 未安装", "pip install ddddocr")
- **System requirements**: Missing system tools or permissions that require user action
- **Invalid configuration**: Provider/model mismatch (e.g., using DeepSeek for vision tasks)

**When you see these errors**:
- Set `is_retryable: false`
- Set `modified_step: null`
- In `reason`, explain: "This error requires user configuration. [具体说明需要用户做什么]"

**Examples of NON-RETRYABLE errors**:
- "VLM不可用：DeepSeek 不支持视觉功能" → `is_retryable: false` (用户需要切换模型)
- "OCR不可用：ddddocr 未安装" → `is_retryable: false` (用户需要安装依赖)
- "视觉分析失败：VLM和OCR均不可用" + 包含配置建议 → `is_retryable: false` (用户需要配置)

**⚠️ CRITICAL: Parameter Extraction Rules**:
- **NEVER use placeholders** like `[REPLACE_WITH_ACTUAL_APP_NAME]`, `extract_from_context_or_ask_user`, or any text containing `[ ]` brackets.
- **ALWAYS extract real values** from the `Context` or `Failed Step`:
  - If `app_name` is missing, extract it from the original instruction in Context (e.g., "打开汽水音乐" → "汽水音乐").
  - If `file_path` is missing, extract it from Context or use safe defaults (e.g., `~/Desktop`).
  - If you cannot find the real value in Context, set `is_retryable: false` and explain why.
- **Forbidden patterns** (DO NOT USE):
  - `[REPLACE_WITH_ACTUAL_APP_NAME]`
  - `extract_from_context_or_ask_user`
  - `[ANY_TEXT_IN_BRACKETS]`
  - `placeholder`, `TODO`, `FIXME`
- **If a required parameter is missing and cannot be extracted**:
  - Set `is_retryable: false`
  - In `reason`, explain: "Cannot extract [parameter_name] from context. User must provide it explicitly."
- **Example of CORRECT fix**:
  - Error: "缺少app_name参数"
  - Context: "用户指令: 打开汽水音乐"
  - Fix: `{{"params": {{"app_name": "汽水音乐"}}}}` ✅
- **Example of WRONG fix**:
  - Fix: `{{"params": {{"app_name": "[REPLACE_WITH_ACTUAL_APP_NAME]"}}}}` ❌
"""
