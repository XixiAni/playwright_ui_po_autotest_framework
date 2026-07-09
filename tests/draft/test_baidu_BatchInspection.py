from playwright.sync_api import Page
from pages.search_page import SearchPage

def test_baidu_search_batch(page: Page) -> None:
    """百度搜索结果批量校验测试用例

    循环校验前N条搜索结果是否包含目标关键词，单条失败不终止整体执行

    :param page: pytest function级夹具，独立标签页Page对象，自动注入
    :return: 无返回，批量执行完成后输出整体统计结果
    """
    baidu_page = SearchPage(page)
    baidu_page.open()
    baidu_page.search("Playwright UI自动化测试")

    check_words: list[str] = ["playwright", "ui"]
    check_count: int = 10  # 校验前10条，可按需调整
    pass_count: int = 0
    fail_count: int = 0

    for index in range(check_count):
        try:
            result_text: str = baidu_page.get_indexed_result_text(index=index)
            has_target: bool = any(word in result_text for word in check_words)
            
            if has_target:
                print(f"第{index+1}条结果：Passed")
                pass_count += 1
            else:
                print(f"第{index+1}条结果：Failed，文本摘要：{result_text[:50]}...") # 截取前50个字符作为摘要
                fail_count += 1
        except Exception as e:
            print(f"第{index+1}条结果：获取失败，原因：{str(e)}")
            fail_count += 1

    print(f"\n批量校验完成：共{check_count}条，通过{pass_count}条，失败{fail_count}条")
