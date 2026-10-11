"""核心模块。

注意：此处不主动 import llm/config 子模块，避免与 app.utils.logger 形成循环导入。
各模块请直接使用：
    from app.core.config import settings
    from app.core.llm import llm_client
"""

