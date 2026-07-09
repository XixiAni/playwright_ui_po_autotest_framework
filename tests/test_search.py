import pytest
import allure
from playwright.sync_api import Page
from pages.search_page import SearchPage
from common.logger import get_logger
logger = get_logger("test_baidu")

# 可选参数(单用例重试) : @pytest.mark.flaky(reruns=3, reruns_delay=2)，生效优先级最高
@allure.feature("百度搜索模块")
@allure.story("关键词搜索场景")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("搜索Playwright UI自动化关键词，校验结果相关性")
@pytest.mark.smoke
@pytest.mark.regression
def test_baidu_search(page: Page) -> None:
    """百度搜索功能自动化测试用例
    
    业务流程：打开百度首页 → 执行关键词搜索 → 校验搜索结果包含目标关键字
    
    :param page: pytest function级夹具，独立标签页Page对象，自动注入
    :return: 无返回，断言失败直接抛出用例失败异常
    """
    logger.info("==================== 开始执行百度搜索用例 ====================")
    # 实例化百度页面对象
    baidu_page = SearchPage(page)
    # 执行业务操作
    baidu_page.open()
    baidu_page.search("Playwright UI自动化测试")
    # 获取结果并执行断言
    result_text: str = baidu_page.get_indexed_result_text(index=0)
    check_words: list[str] = ["playwright", "ui"]
    has_target: bool = any(word in result_text for word in check_words)    
    logger.info(f"断言校验：目标关键词{check_words}，页面文本：{result_text}，匹配结果：{has_target}")
    assert has_target, "搜索结果区域未检测到目标相关关键词"
    logger.info("==================== 百度搜索用例执行PASSED ====================")