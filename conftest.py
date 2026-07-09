import pytest
import os
import sys
import time
import allure
import json
from playwright.sync_api import sync_playwright
from common.yaml_reader import YamlReader  # 【配置解耦改造】导入YAML读取工具
from common.logger import get_logger
logger = get_logger("conftest")

def pytest_addoption(parser):
    parser.addoption(
        "--env", # --env ：外部命令行输入的参数名，调用  pytest --env=test 
        action="store", # action="store" ：接收一个字符串值存入变量，最常用
        default="dev", # default="dev" ：不传参数时默认加载开发环境
        choices=["dev", "test", "prod"], # choices ：限制合法输入，输其他值直接报错拦截
        help="指定运行环境：dev / test / prod" # help ： pytest -h  帮助文档展示说明
    )

@pytest.fixture(scope="session")
def env(request):
    '''request：pytest内置夹具，可读取本次运行全部命令行、配置信息
    
    getoption("--env")：取出用户传入的环境标识字符串（dev/test/prod）
    '''
    env_name = request.config.getoption("--env")
    return env_name

def pytest_configure(config):
    """pytest启动生命周期钩子：全局仅执行1次
    
    负责初始化环境标识、加载全局重试配置、写入Allure配套元数据
    """
    # 初始化全局运行环境，全项目配置读取自动生效
    current_env = config.getoption("--env")
    YamlReader.set_current_env(current_env)

    # 空字典占位，保证后续Allure读取时变量必存在
    rerun_config = {}
    try:
        rerun_config = YamlReader.get("config.yaml", "rerun")
        if rerun_config.get("enable", False):
            # None兜底：区分插件默认0与用户手动传参0，避免覆盖用户输入
            user_rerun_input = config.getoption("reruns", None)
            user_delay_input = config.getoption("reruns_delay", None)

            if user_rerun_input is None:
                # 未手动传参，加载YAML全局重试配置
                config.option.reruns = rerun_config.get("max_times", 1)
                config.option.reruns_delay = rerun_config.get("delay", 1)
                logger.info(f"加载全局重试配置：最多重试{config.option.reruns}次，间隔{config.option.reruns_delay}秒")
            else:
                # 用户手动传参，YAML配置不生效
                if user_delay_input is not None:
                    logger.info(f"用户完整传入重试参数：最多重试{user_rerun_input}次，间隔{user_delay_input}秒")
                else:
                    logger.info(f"用户仅传入重试次数{user_rerun_input}，未指定间隔，采用插件原生默认0秒间隔（YAML全局配置不生效）")
    except Exception as e:
        # 读取异常兜底：关闭重试，保证后续Allure读取不报错
        rerun_config = {"enable": False, "max_times": 0, "delay": 0}
        logger.warning(f"读取重试配置失败，使用默认策略(不重试)，已自动补零rerun_config参数值，异常类型：{type(e)}，详情：{str(e)}")

    # 写入Allure报告配套元数据
    try:
        allure_result_dir = YamlReader.get("config.yaml", "report.allure_result_dir")
        os.makedirs(allure_result_dir, exist_ok=True)

        # 写入环境信息：标准Java Properties格式，键=值，每行一条
        env_file_path = os.path.join(allure_result_dir, "environment.properties")
        browser_config = YamlReader.get("config.yaml", "browser")
        viewport_config = YamlReader.get("config.yaml", "viewport")
        # 所有键名统一采用大驼峰英文命名(中文在特定环境会乱码)，符合 Java Properties 的通用命名规范，Allure 可正常解析显示。
        env_info = {
            "RunEnvironment": current_env,
            "Browser": "Microsoft Edge",
            "Headless": browser_config["headless"],
            "Viewport": f"{viewport_config['width']}x{viewport_config['height']}",
            "RerunEnable": rerun_config.get("enable", False),
            "MaxRerunTimes": rerun_config.get("max_times", 0),
            "PythonVersion": sys.version.split()[0],
            "PytestVersion": pytest.__version__
        }
        with open(env_file_path, "w", encoding="utf-8") as f:
            for key, value in env_info.items():
                f.write(f"{key}={value}\n")
        logger.info("Allure环境信息文件environment.properties写入完成")

        # 写入执行机信息：标准JSON格式，缩进格式化便于人工查看
        executor_file_path = os.path.join(allure_result_dir, "executor.json")
        executor_data = {
            "name": "本地Windows测试工作站",
            "type": "local",
            "buildName": "本地手动执行UI自动化用例",
            "reportName": "Playwright UI自动化测试报告",
            "url": ""
        }
        with open(executor_file_path, "w", encoding="utf-8") as f:
            json.dump(executor_data, f, ensure_ascii=False, indent=2)
        logger.info("Allure执行机信息文件executor.json写入完成")
    except Exception as e:
        logger.warning(f"写入Allure配套信息失败，不影响用例执行，异常：{type(e)}")

@pytest.fixture(scope="session")
def browser():
    """全局浏览器夹具（会话级）

    统一启动、关闭系统Edge浏览器，所有测试用例共享同一个浏览器进程

    优先使用配置的本地浏览器路径，路径不存在则自动降级为系统Edge自动识别

    生命周期：整个测试运行周期仅创建1次，全部用例执行完毕后自动销毁
    """
    logger.info("===== 会话级browser夹具开始初始化 =====")
    # 【配置解耦改造】从全局配置读取浏览器启动参数
    browser_config = YamlReader.get("config.yaml", "browser")
    exe_path = browser_config.get("executable_path", "")
    headless = browser_config["headless"]
    launch_args = browser_config["args"]
    
    # with上下文管理器：自动管理Playwright底层驱动，运行结束自动释放资源
    with sync_playwright() as playwright_obj:
        # 启动Chromium内核浏览器，复用系统Edge规避官方浏览器安装权限问题
        if exe_path and  os.path.exists(exe_path):
            logger.info(f"使用指定路径启动Edge：{exe_path}，无头模式：{headless}") 
            browser_instance = playwright_obj.chromium.launch(
                executable_path=exe_path,
                headless=headless,
                args=launch_args
            )
        else:
            logger.warning("未找到指定浏览器路径，自动降级为系统Edge自动识别模式启动")
            browser_instance = playwright_obj.chromium.launch(
                channel="msedge",
                headless=headless,
                args=launch_args
            )
        logger.info("Edge浏览器进程启动成功")
        # yield：分割前置初始化和后置销毁逻辑，向下层夹具传递浏览器实例
        yield browser_instance
        # 后置操作：所有测试用例执行完成后，关闭浏览器进程
        logger.info("全部用例执行完毕，准备关闭浏览器进程")
        browser_instance.close()
        logger.info("===== 会话级browser夹具销毁完成 =====")

@pytest.fixture(scope="function")
def context(browser):
    """浏览器上下文夹具（用例级）

    统一管理会话级配置，每条用例独立上下文，Cookie/缓存完全隔离
    """
    logger.info("----- function级context夹具初始化 -----")
    viewport_config = YamlReader.get("config.yaml", "viewport")
    # 创建独立上下文，统一配置视口
    context_instance = browser.new_context(
        viewport=viewport_config,
        ignore_https_errors=True
    )
    logger.info(f"上下文视口设置：宽{viewport_config['width']} 高{viewport_config['height']}")
    # 上下文级注入JS，所有页面自动生效
    context_instance.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
    """)
    context_instance.add_init_script("""
        window.addEventListener('resize', e => {
            e.preventDefault();
            window.resizeTo(1920, 1080);
        })
    """)
    logger.info("完成反爬虫JS注入与窗口锁定逻辑")
    logger.info("上下文初始化完成，交付context实例")
    yield context_instance
    logger.info("当前用例执行结束，关闭浏览器上下文")
    context_instance.close()
    logger.info("----- function级context夹具销毁完成 -----")


@pytest.fixture(scope="function")
def page(context):
    """单页面对象夹具（用例级）

    依赖：上层context全局浏览器夹具

    作用：每条测试用例分配独立标签页

    生命周期：每条用例执行前创建，执行完毕自动关闭
    """
    logger.info("----- function级page夹具初始化 -----")
    page_instance = context.new_page()
    # 配置注入在context中已完成，page无需重复注入
    page_instance.wait_for_timeout(200)
    logger.info("页面初始化等待完成，交付page实例给用例")
    # yield：向测试用例传递页面对象
    yield page_instance
    # 后置操作：关闭当前页面，清理缓存数据
    logger.info("当前用例执行结束，关闭页面标签页")
    page_instance.close()
    logger.info("----- function级page夹具销毁完成 -----")


# 【新增】全局钩子：用例执行失败自动截图并挂载到Allure报告
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # pylint: disable=unused-argument
    """pytest内置包装型钩子

    监听用例全生命周期执行结果，用例失败时自动截图并挂载到Allure报告
    """
    # yield前：预留日志、进度条等扩展位；执行到yield时交出控制权，运行pytest原生报告逻辑
    outcome = yield
    # yield后：原生逻辑执行完毕，获取执行结果
    report = outcome.get_result()

    # 仅处理call阶段（业务代码执行阶段）的失败，跳过setup/teardown阶段
    if report.when == "call" and report.failed:
        logger.error(f"用例[{item.nodeid}]业务代码执行失败，进入自动截图逻辑")
        # 读取报告配置
        report_config = YamlReader.get("config.yaml", "report")
        auto_screenshot = report_config["auto_screenshot"]
        screenshot_dir = report_config["screenshot_dir"]
        if not auto_screenshot:
            logger.info("配置中关闭自动截图，跳过截图流程")
            return

        # 获取当前用例的page夹具实例，无page夹具的用例直接跳过
        try:
            page = item.funcargs["page"]
        except KeyError:
            logger.warning(f"用例[{item.nodeid}]未注入page夹具，无法截图")
            return

        # 创建截图目录
        os.makedirs(screenshot_dir, exist_ok=True)
        # 并发场景增加进程标识，避免文件名冲突覆盖
        worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master") # PYTEST_XDIST_WORKER为pytest-xdist插件自动注入的环境变量，标识当前执行进程；master命名兜底，覆盖单进程默认值None，区分多进程gw前缀，规范命名
        # 生成带时间戳的截图文件名，避免覆盖
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_name = f"{worker_id}_{item.name}_{timestamp}.png"
        screenshot_path = os.path.join(screenshot_dir, screenshot_name)
        logger.info(f"失败截图保存路径：{screenshot_path}")
        # 截取完整页面
        page.screenshot(path=screenshot_path, full_page=True)

        logger.info("页面截图完成，开始挂载至Allure报告")
        # 将截图挂载到Allure报告
        with open(screenshot_path, "rb") as f:
            allure.attach(
                f.read(),
                name="失败页面截图",
                attachment_type=allure.attachment_type.PNG
            )
        logger.info("截图附件挂载Allure成功")