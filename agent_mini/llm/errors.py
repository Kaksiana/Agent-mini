"""LLM 错误类型。"""


class LLMError(Exception):
    """LLM 调用错误基类。"""

    code = "LLM_ERROR"
    http_status = 502

    def __init__(self, message: str) -> None:
        """保存可读错误消息。"""
        super().__init__(message)
        self.message = message


class LLMProtocolError(LLMError):
    """上游响应结构或终止原因不合法。"""

    code = "LLM_PROTOCOL_ERROR"


class LLMEmptyResponseError(LLMError):
    """上游没有返回有效答案。"""

    code = "LLM_EMPTY_RESPONSE"


class LLMOutputTruncatedError(LLMError):
    """上游输出被截断。"""

    code = "LLM_OUTPUT_TRUNCATED"


class LLMOutputRejectedError(LLMError):
    """上游输出被拒绝。"""

    code = "LLM_OUTPUT_REJECTED"


class LLMAuthError(LLMError):
    """上游鉴权失败。"""

    code = "LLM_AUTH"


class LLMBadRequestError(LLMError):
    """上游请求参数不合法。"""

    code = "LLM_BAD_REQUEST"


class LLMTimeoutError(LLMError):
    """上游调用超时。"""

    code = "LLM_TIMEOUT"
    http_status = 408


class LLMRateLimitError(LLMError):
    """上游限流且重试耗尽。"""

    code = "LLM_RATE_LIMITED"
    http_status = 429


class LLMServerError(LLMError):
    """上游服务端错误且重试耗尽。"""

    code = "LLM_SERVER_ERROR"


class LLMConnectionError(LLMError):
    """上游连接失败。"""

    code = "LLM_CONNECTION_ERROR"
