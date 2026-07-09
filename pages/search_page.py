import allure
from playwright.sync_api import Page
from common.base_page import BasePage
from common.yaml_reader import YamlReader  # 【配置解耦改造】导入YAML读取工具
from common.logger import get_logger
logger = get_logger("baidu_page")

class SearchPage(BasePage):
    """百度首页页面对象类

    统一管理百度首页全部元素定位器，封装完整搜索业务流程
    """
    def __init__(self, page: Page) -> None:
        """复用父类初始化逻辑；从YAML加载当前页面定位配置

        :param page: Playwright Page页面对象
        """
        super().__init__(page)
        logger.info("初始化BaiduPage页面类，加载百度定位配置")
        # 读取合并后的定位器（公共基准 + 环境覆盖）
        locator_config = YamlReader.get_page_locators("search_page")
        # 页面URL从当前环境配置读取
        self.page_url = YamlReader.get_env("search_page.url")
        # 定位器实例化为Locator对象
        self.SEARCH_INPUT = self.page.locator(locator_config["search_input"])
        self.SEARCH_BUTTON = self.page.locator(locator_config["search_button"])
        self.RESULT_ITEM = self.page.locator(locator_config["result_item"])
        # 缓存第一条结果，减少.nth(0)调用次数
        self.FIRST_RESULT = self.RESULT_ITEM.nth(0)
        # 新增原始字符串缓存
        self._raw_search_input = locator_config["search_input"]
        self._raw_search_btn = locator_config["search_button"]
        self._raw_result = locator_config["result_item"]
        logger.info(f"百度页面配置加载完成，首页地址：{self.page_url}")

    @allure.step("打开百度首页")
    def open(self) -> None:
        """访问百度首页地址"""
        logger.info(f"访问百度首页地址：{self.page_url}")
        self.page.goto(self.page_url)
        logger.info("已打开百度首页")

    @allure.step("执行关键词搜索：{keyword}")
    def search(self, keyword: str) -> None:
        """完整百度搜索流程：关弹窗→输入关键词→点击搜索→等待结果渲染

        :param keyword: 搜索关键词
        """
        logger.info(f"启动完整搜索流程，搜索关键词：{keyword}")
        self.close_all_popups()
        self.wait_for_element(self.SEARCH_INPUT, state="attached")
        self.safe_fill(self.SEARCH_INPUT, keyword,raw_sel=self._raw_search_input) 
        # 可选：方法支持传入字符串 格式：self.safe_fill("#kw", "测试文本", raw_sel="#kw")
        self.safe_click(self.SEARCH_BUTTON,raw_sel=self._raw_search_btn)
        self.wait_for_element(self.FIRST_RESULT, state="visible") # 避免Locator实例引入的严格模式匹配多条导致报错
        logger.info("搜索结果区块已渲染完成")

    @allure.step("获取指定下标的搜索结果文本")
    def get_indexed_result_text(self, index: int = 0) -> str:
        """获取指定下标的搜索结果文本并转小写，供断言使用
        
        :param index: 搜索结果下标，默认0=第一条
        :return: 小写文本字符串
        """
        logger.info(f"获取第{index+1}条搜索结果文本")
        return self.get_element_text(self.RESULT_ITEM, index=index)
