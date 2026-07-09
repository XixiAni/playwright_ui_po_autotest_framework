from common.logger import get_logger
logger = get_logger("assert_utils")

class AssertUtils:
    """公共断言工具类

    封装通用断言逻辑，统一日志埋点与失败提示
    """
    @staticmethod
    def assert_any_contains(text: str, keywords: list[str], desc: str = "文本关键词匹配") -> None:
        """断言文本中包含任意一个目标关键词

        :param text: 待校验的源文本
        :param keywords: 目标关键词列表
        :param desc: 断言场景描述，用于日志与报错信息
        """
        logger.info(f"执行断言[{desc}]：目标关键词 {keywords}，源文本长度 {len(text)}")
        has_target = any(word in text for word in keywords)
        assert has_target, f"{desc}失败，未检测到任意目标关键词：{keywords}"
        logger.info(f"断言通过[{desc}]：匹配到目标关键词")

    @staticmethod
    def assert_all_contains(text: str, keywords: list[str], desc: str = "文本全关键词匹配") -> None:
        """断言文本中包含全部目标关键词

        :param text: 待校验的源文本
        :param keywords: 目标关键词列表
        :param desc: 断言场景描述
        """
        logger.info(f"执行断言[{desc}]：目标关键词 {keywords}，源文本长度 {len(text)}")
        all_match = all(word in text for word in keywords)
        assert all_match, f"{desc}失败，未全部匹配目标关键词：{keywords}"
        logger.info(f"断言通过[{desc}]：全部关键词匹配成功")

    @staticmethod
    def assert_equal(actual, expect, desc: str = "值相等校验") -> None:
        """断言两个值相等

        :param actual: 实际值
        :param expect: 期望值
        :param desc: 断言场景描述
        """
        logger.info(f"执行断言[{desc}]：期望值 {expect}，实际值 {actual}")
        assert actual == expect, f"{desc}失败，期望：{expect}，实际：{actual}"
        logger.info(f"断言通过[{desc}]：值匹配一致")

    @staticmethod
    def assert_not_empty(obj, desc: str = "非空校验") -> None:
        """断言对象非空（非None、非空字符串、非空列表/字典）
        
        :param obj: 待校验对象
        :param desc: 断言场景描述
        """
        logger.info(f"执行断言[{desc}]")
        assert obj, f"{desc}失败，对象为空"
        logger.info(f"断言通过[{desc}]：对象非空")
