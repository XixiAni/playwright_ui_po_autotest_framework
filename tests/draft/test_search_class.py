import pytest
import allure
from pages.search_page import SearchPage
from common.logger import get_logger
from common.assert_utils import AssertUtils

logger = get_logger("test_search_class")

@allure.feature("百度搜索模块")
@allure.story("类组织多场景搜索【仅作框架补充，业务禁用】")
class TestSearch:
    """百度搜索场景测试类

    演示Test类组织用例范式，同模块用例聚合管理，复用类级页面对象
    
    重要说明：class级夹具存在页面全局共享、数据污染问题
    1. 多条用例共用同一个页面，操作后页面状态不会重置

    2. 不支持数据驱动参数化、失败自动截图功能

    3. 正式业务回归统一使用function单用例隔离范式
    """
# 注意：类级夹具会导致用例间共享页面数据，适合无状态的查询类场景，数据隔离要求高的场景仍用function级(test_search.py/test_search_parametrize.py)
    @pytest.fixture(scope="class", autouse=True)
    def class_search_page(self, browser):
        """类级页面夹具：整个Test类执行前后仅创建/销毁1次页面
        适合同页面多查询场景，减少重复新建页面的开销，存在状态污染风险
        """
        logger.info("===== 类级page夹具初始化 =====")
        page_instance = browser.new_page()
        search_page = SearchPage(page_instance)
        search_page.open()
        # 交付页面对象给当前类所有用例
        yield search_page
        # 后置：关闭页面
        logger.info("===== 类级page夹具销毁 =====")
        page_instance.close()

    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("类用例：UI自动化关键词搜索校验")
    def test_search_ui_auto(self, class_search_page: SearchPage) -> None:
        """测试UI自动化关键词搜索场景
        """
        logger.info("开始执行：UI自动化关键词搜索用例")
        class_search_page.search("Playwright UI自动化测试")
        result_text = class_search_page.get_indexed_result_text(index=0)
        AssertUtils.assert_any_contains(
            text=result_text,
            keywords=["playwright", "ui"],
            desc="UI自动化搜索结果校验"
        )
        logger.info("用例执行通过：UI自动化关键词搜索")

    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("类用例：Python编程关键词搜索校验")
    def test_search_python(self, class_search_page: SearchPage) -> None:
        """测试Python关键词搜索场景
        """
        logger.info("开始执行：Python编程关键词搜索用例")
        class_search_page.search("Python自动化测试")
        result_text = class_search_page.get_indexed_result_text(index=0)
        AssertUtils.assert_any_contains(
            text=result_text,
            keywords=["python", "自动化"],
            desc="Python搜索结果校验"
        )
        logger.info("用例执行通过：Python编程关键词搜索")

    '''@allure.severity(allure.severity_level.MINOR)
    @allure.title("类用例：页面标题正确性校验")
    def test_page_title(self, class_search_page: SearchPage) -> None:
        """测试百度首页标题正确性
        """
        logger.info("开始执行：页面标题校验用例")
        title = class_search_page.get_page_title()
        AssertUtils.assert_equal(
            actual=title,
            expect="百度一下，你就知道",
            desc="首页标题校验"
        )
        logger.info("用例执行通过：页面标题校验")
    '''