import pytest
import allure
from playwright.sync_api import Page
from pages.search_page import SearchPage
from common.yaml_reader import YamlReader
from common.logger import get_logger

logger = get_logger("test_search_param")

# 前置：读取全部测试用例数据，提取用例名用于ids展示
ALL_CASES = YamlReader.get_test_data("search_data.yaml", "search_cases")
def _build_param_cases(cases: list[dict]) -> list:
    """根据YAML数据中的marks字段动态生成带标签的参数列表

    :param cases: 测试用例数据列表

    :return: 带pytest标记的参数列表
    """
    param_list = []
    for case in cases:
        marks = [getattr(pytest.mark, m) for m in case.get("marks", ["regression"])]
        param_list.append(pytest.param(case, id=case["case_id"], marks=marks))
    return param_list
PARAM_CASES = _build_param_cases(ALL_CASES)
@allure.feature("百度搜索模块")
@allure.story("数据驱动批量搜索场景")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("case_data", PARAM_CASES)
def test_search_parametrize(page: Page, case_data: dict) -> None:
    """数据驱动百度搜索批量用例
    
    测试数据全部来自 data/search_data.yaml，新增用例仅需追加YAML配置
    
    :param page: function级页面夹具
    :param case_data: 单组测试数据字典，包含case_name、keyword、expect_words
    """
    # 动态设置Allure用例标题
    allure.dynamic.title(case_data["case_name"])
    logger.info(f"==================== 开始执行参数化用例：{case_data['case_name']} ====================")

    # 实例化页面对象
    search_page = SearchPage(page)

    # 执行业务流程
    search_page.open()
    search_page.search(case_data["keyword"])

    # 断言逻辑：多关键词匹配
    result_text: str = search_page.get_indexed_result_text(index=0)
    check_words = case_data["expect_words"]
    has_target: bool = any(word in result_text for word in check_words)

    logger.info(f"断言校验：目标关键词{check_words}，页面文本：{result_text}，匹配结果：{has_target}")
    assert has_target, f"搜索结果未检测到目标关键词：{check_words}"
    logger.info(f"==================== 参数化用例执行PASSED：{case_data['case_id']} ====================")