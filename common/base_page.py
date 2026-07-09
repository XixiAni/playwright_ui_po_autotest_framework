import allure
from playwright.sync_api import Page,Locator
from common.yaml_reader import YamlReader  # 【配置解耦改造】导入YAML读取工具
from common.logger import get_logger
# 初始化当前模块日志对象
logger = get_logger("base_page")

class BasePage:
    """所有页面对象的基础父类

    封装全页面通用底层操作：分级智能等待、双层容错输入/点击、批量关闭弹窗、文本读取

    所有业务页面类继承本类，复用通用稳定能力
    """
    def __init__(self, page: Page) -> None:
        """初始化页面对象，绑定playwright页面实例

        :param page: Playwright同步模式Page对象
        """
        self.page: Page = page
        # 【配置解耦改造】从YAML读取通用弹窗选择器与全局超时配置
        self.common_close_selectors: list[str] = YamlReader.get("locators.yaml", "common.popup_close_selectors")
        self._default_element_timeout = YamlReader.get("config.yaml", "timeout.element_wait")
        self._default_popup_timeout = YamlReader.get("config.yaml", "timeout.popup_wait")
        self._default_input_timeout = YamlReader.get("config.yaml", "timeout.input_visible")
        self._default_click_timeout = YamlReader.get("config.yaml", "timeout.click_visible")
        logger.info("BasePage实例初始化完成，加载弹窗选择器、全局超时参数与操作级重试配置")

    def _to_locator(self, selector_or_locator: str | Locator) -> Locator:
        """私有方法：统一将字符串选择器或Locator转为Locator对象"""
        if isinstance(selector_or_locator, Locator):
            return selector_or_locator
        return self.page.locator(selector_or_locator)
    
    def _get_raw_selector(self, selector_or_locator: str | Locator) -> str:
        """工具方法：统一拿到原始字符串选择器，不修改外部变量"""
        if isinstance(selector_or_locator, str):
            return selector_or_locator
        # Playwright无公开API获取Locator选择器，禁止读取私有_selector，返回None标识不可用
        logger.warning("Locator类型无法提取原始选择器，JS兜底将不可用")
        return None
    @allure.step("等待元素：{selector_or_locator}，状态：{state}")
    def wait_for_element(self, selector_or_locator: str | Locator, state: str = "visible", timeout: int = None) -> None:
        """分级智能等待元素挂载/可见
        
        :param selector_or_locator: 目标元素CSS选择器或Locator对象
        :param state: 等待状态，attached=仅DOM挂载；visible=DOM存在且页面可见
        :param timeout: 最大等待超时，单位ms；不传则使用全局配置默认值
        """
        locator = self._to_locator(selector_or_locator)
        use_timeout = timeout if timeout is not None else self._default_element_timeout
        logger.info(f"开始等待元素，选择器：{selector_or_locator}，状态：{state}，超时时间：{use_timeout}ms")
        try:
            # Locator对象使用wait_for方法，替代原Page级的wait_for_selector
            locator.wait_for(state=state, timeout=use_timeout)
            logger.info(f"元素等待完成，选择器：{selector_or_locator}，状态：{state}")
        except Exception as e:
            logger.error(f"元素等待超时失败，选择器：{selector_or_locator}，状态：{state}，异常信息：{str(e)}") # 移除 exc_info=True 参数，防止堆栈输出过长；仅保留此处str(e)，其余改为type(e)防止输出过长
            raise
    
    @allure.step("自动关闭页面弹窗")
    def close_all_popups(self) -> None:
        """循环遍历通用弹窗关闭按钮，找不到对应弹窗直接跳过
        """
        logger.info("执行批量关闭弹窗逻辑")
        for selector in self.common_close_selectors:
            try:
                locator = self._to_locator(selector)
                locator.click(timeout=self._default_popup_timeout)
                logger.info(f"成功关闭弹窗：{selector}")
            except Exception:
                logger.debug(f"未匹配到弹窗{selector}，跳过")
                continue

    @allure.step("安全输入：{selector_or_locator}，内容：{text}")
    def safe_fill(self, selector_or_locator: str | Locator, text: str, visible_timeout: int = None,raw_sel: str = None) -> None:
        """三层容错输入：可见原生输入 → 挂载强制输入 → JS注入兜底

        解决元素被CSS隐藏导致原生fill校验失败问题
        
        解决元素动态隐藏导致的长时间等待超时问题，适配DOM挂载但视觉隐藏的输入框
        
        :param selector_or_locator: 输入框CSS选择器或Locator对象
        :param text: 目标输入文本
        :param visible_timeout: 原生操作等待可见超时，单位ms
        :param raw_sel: 原始字符串选择器，用于JS兜底输入
        """
        locator = self._to_locator(selector_or_locator)
        full_visible_timeout = visible_timeout if visible_timeout is not None else self._default_input_timeout
        fast_timeout = full_visible_timeout // 2  # 一阶短超时，快速试错
        logger.info(f"启动分层输入流程，选择器：{selector_or_locator}，待输入内容：{text}，完整可见等待配置上限：{full_visible_timeout}ms，一阶短超时上限：{fast_timeout}ms")
        # 第一阶：短超时等待可见，适配正常渲染输入框
        try:
            self.wait_for_element(locator, state="visible", timeout=fast_timeout)
            locator.focus()
            locator.fill(text)
            logger.info(f"一阶可见模式：原生输入成功，选择器：{selector_or_locator}，内容：{text}")
            return
        except Exception as e:
            logger.warning(f"一阶段可见输入失败，进入二阶段强制输入，异常：{type(e)}")
        # 第二阶：进等待DOM挂载，force强制输入，适配动态隐藏输入框
        try:
            self.wait_for_element(locator, state="attached", timeout=full_visible_timeout)
            locator.focus(force=True)
            locator.fill(text)
            logger.info(f"二阶挂载模式：强制输入成功，选择器：{selector_or_locator}，内容：{text}")
            return
        except Exception as e:
            logger.warning(f"二阶段挂载强制输入失败，进入JS兜底，异常：{type(e)}")        
        # JS分支优先使用外部传入的raw_sel，不再读取Locator
        # 第三阶：JS最终兜底：有原始选择器 raw_sel 入参则执行，执行成功直接return，不抛异常
        if raw_sel and isinstance(raw_sel, str):
            try:
                self.page.evaluate(
                    """([sel, value]) => {
                        const el = document.querySelector(sel);
                        if(el){el.value = value;el.dispatchEvent(new Event('input'));}
                    }""",
                    [raw_sel, text]
                )
                logger.info(f"JS兜底输入完成：{text}，原始选择器：{raw_sel}")
                return
            except Exception as js_err:
                logger.warning(f"JS兜底执行异常，详情：{js_err}")
        raise TimeoutError(f"元素{selector_or_locator}三层兜底输入全部失败，操作终止，完整可见等待配置上限：{full_visible_timeout}ms")    
    @allure.step("安全点击元素：{selector_or_locator}")
    def safe_click(self, selector_or_locator: str | Locator, visible_timeout: int = None, raw_sel: str = None) -> None:
        """三层容错点击：可见原生点击 → 挂载强制点击 → JS注入兜底
        
        解决元素动态隐藏导致的长时间等待超时问题，适配DOM挂载但视觉隐藏的元素
     
        :param selector_or_locator: 目标元素CSS选择器或Locator对象
        :param visible_timeout: 完整可见等待可见超时，单位ms
        :param raw_sel: 原始字符串选择器，用于JS兜底点击
        """
        locator = self._to_locator(selector_or_locator)
        full_visible_timeout = visible_timeout if visible_timeout is not None else self._default_click_timeout
        fast_timeout = full_visible_timeout // 2  # 一阶短超时，快速试错
        
        logger.info(f"启动分层点击流程，选择器：{selector_or_locator}，完整可见等待配置上限：{full_visible_timeout}ms，一阶短超时上限：{fast_timeout}ms")
        # 操作级重试：原生点击多次重试，失败再走JS兜底
        # 第一阶：短超时等待可见，适配正常渲染元素
        try:
            self.wait_for_element(locator, state="visible", timeout=fast_timeout)
            locator.click()
            logger.info(f"一阶可见模式：原生点击成功，选择器：{selector_or_locator}")
            return
        except Exception as e:
            logger.warning(f"一阶段可见点击失败，进入二阶段强制点击，异常：{type(e)}")
        # 第二阶：进等待DOM挂载，force强制点击，适配动态隐藏元素
        try:
            self.wait_for_element(locator, state="attached", timeout=full_visible_timeout)
            locator.click(force=True)
            logger.info(f"二阶挂载模式：强制点击成功，选择器：{selector_or_locator}")
            return
        except Exception as e:
            logger.warning(f"二阶段挂载强制点击失败，进入JS兜底，异常：{type(e)}")
        # JS兜底：使用创建Locator对象的原始信息字符串缓存raw_selector，避免Locator私有属性不可读,参数传参方式注入，自动转义特殊字符
        # 第三阶：JS最终兜底：有原始选择器 raw_sel 入参则执行，执行成功直接return，不抛异常
        if raw_sel and isinstance(raw_sel, str):
            try:
                self.page.evaluate(
                    """(sel) => {
                        document.querySelector(sel).click();
                    }""",
                    raw_sel
                )
                logger.info(f"JS兜底点击完成，原始选择器：{raw_sel}")
                return
            except Exception as js_err:
                logger.warning(f"JS兜底执行异常，详情：{js_err}")
        raise TimeoutError(f"元素{selector_or_locator}三层兜底点击全部失败，操作终止，完整可见等待配置上限：{full_visible_timeout}ms")
    @allure.step("获取元素文本：{selector_or_locator}，下标：{index}")
    def get_element_text(self, selector_or_locator: str | Locator, index: int = 0) -> str:
        """获取指定下标元素文本，统一转为小写消除断言干扰

        :param selector_or_locator: 目标元素CSS选择器或定位器
        :param index: 匹配元素下标，默认取第一条
        :return: 小写文本字符串
        """
        locator = self._to_locator(selector_or_locator)
        logger.info(f"获取元素文本，选择器：{selector_or_locator}，下标：{index}")
        try:
            text_content = locator.nth(index).text_content()
            lower_text = text_content.lower()
            logger.info(f"获取文本成功，原始文本：{text_content}，小写处理后：{lower_text}")
            return lower_text
        except Exception as e:
            logger.error(f"获取元素文本失败，选择器：{selector_or_locator}，下标：{index}，异常：{type(e)}")  # 移除exc_info=True
            raise

    @allure.step("判断元素是否可见：{selector_or_locator}")
    def is_element_visible(self, selector_or_locator: str | Locator, timeout: int = None) -> bool:
        """判断元素是否可见，返回布尔值，不抛出异常

        :param selector_or_locator: 目标元素CSS选择器或定位器
        :param timeout: 等待超时，单位ms；不传则使用全局默认值
        :return: True=可见；False=不可见
        """
        locator = self._to_locator(selector_or_locator)
        use_timeout = timeout if timeout is not None else self._default_element_timeout
        logger.info(f"判断元素可见性，选择器：{locator}，超时：{use_timeout}ms")
        try:
            # Locator的is_visible仅接收timeout参数，无需传入自身
            result = locator.is_visible(timeout=use_timeout)
            logger.info(f"元素可见性判断结果：{locator} = {result}")
            return result
        except Exception as e:
            logger.warning(f"元素可见性判断异常，选择器：{selector_or_locator}，异常：{type(e)}")
            return False
    @allure.step("获取元素属性：{selector_or_locator}，属性：{attr_name}")
    def get_element_attribute(self, selector_or_locator: str | Locator, attr_name: str, timeout: int = None) -> str | None:
        """获取目标元素的指定属性值

        :param selector_or_locator: 目标元素CSS选择器或定位器
        :param attr_name: 属性名，如value、href、class
        :param timeout: 等待超时，单位ms
        :return: 属性值字符串；元素不存在/属性不存在返回None
         """
        locator = self._to_locator(selector_or_locator)
        use_timeout = timeout if timeout is not None else self._default_element_timeout
        logger.info(f"获取元素属性，选择器：{locator}，属性：{attr_name}")
        try:
            attr_value = locator.get_attribute(attr_name, timeout=use_timeout)
            logger.info(f"元素属性获取成功：{locator}.{attr_name} = {attr_value}")
            return attr_value
        except Exception as e:
            logger.error(f"元素属性获取失败，选择器：{selector_or_locator}，属性：{attr_name}，异常：{type(e)}")
            raise
    @allure.step("刷新当前页面")
    def refresh_page(self) -> None:
        """刷新当前页面，等价浏览器F5
        """
        logger.info("执行页面刷新操作")
        self.page.reload()
        logger.info("页面刷新完成")
    @allure.step("获取当前页面标题")
    def get_page_title(self) -> str:
        """获取当前页面标题

        :return: 页面标题文本
        """
        title = self.page.title()
        logger.info(f"获取页面标题：{title}")
        return title
    @allure.step("获取当前页面URL")
    def get_page_url(self) -> str:
        """获取当前页面完整URL

        :return: 页面URL字符串
        """
        url = self.page.url
        logger.info(f"获取页面URL：{url}")
        return url
    @allure.step("页面后退")
    def page_go_back(self) -> None:
        """浏览器后退操作，返回上一页
        """
        logger.info("执行页面后退操作")
        self.page.go_back()
        logger.info("页面后退完成")
    @allure.step("页面前进")
    def page_go_forward(self) -> None:
        """浏览器前进操作，进入下一页
        """
        logger.info("执行页面前进操作")
        self.page.go_forward()
        logger.info("页面前进完成")