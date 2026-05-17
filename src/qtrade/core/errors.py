class QTradeError(Exception):
    """QTrade 系统的基础异常类"""

    pass


class DataError(QTradeError):
    """数据处理相关错误，如数据缺失、格式错误等"""

    pass


class ConfigError(QTradeError):
    """配置加载或解析错误"""

    pass


class OrderError(QTradeError):
    """订单相关错误，如订单无效、资金不足等"""

    pass


class BrokerError(QTradeError):
    """券商接口交互错误"""

    pass


class RiskError(QTradeError):
    """风控拦截错误"""

    pass
