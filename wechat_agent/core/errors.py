class WechatAgentError(Exception):
    """Base error."""


class PlatformNotImplemented(WechatAgentError):
    pass


class ActionFailed(WechatAgentError):
    pass


class VerificationFailed(WechatAgentError):
    pass

