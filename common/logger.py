import os
import logging
from datetime import datetime

# 项目根目录定位
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 日志文件夹路径
LOG_DIR = os.path.join(BASE_DIR, "logs")
# 按日期拆分日志文件
LOG_FILE_NAME = f"{datetime.now().strftime('%Y-%m-%d')}.log"
LOG_FILE_PATH = os.path.join(LOG_DIR, LOG_FILE_NAME)

# 自动创建logs目录，不存在则递归生成
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 日志格式化模板
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志基础配置（根logger全局配置：文件输出 + 控制台输出）
logging.basicConfig(
    filename=LOG_FILE_PATH,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    level=logging.INFO,
    filemode="a",  # 追加写入，不覆盖历史日志
    encoding="utf-8"
)

# 控制台输出处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
console_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(console_handler)

def get_logger(name: str = "ui_auto_frame") -> logging.Logger:
    """获取日志实例，各模块传入自身文件名区分日志来源

    :param name: 调用模块名称，如base_page、conftest、test_baidu
    :return: Logger对象
    """
    logger = logging.getLogger(name)
    # 子logger复用根logger的handler，通过传播机制输出，不重复添加
    # 已淘汰策略
    '''
    if not logger.handlers:
        logger.addHandler(console_handler)
    会导致如下输出(节选)
    2026-06-26 22:50:03 - yaml_reader - INFO - 读取配置节点，文件：config.yaml，路径：timeout.element_wait
    2026-06-26 22:50:03 - yaml_reader - INFO - 读取配置节点，文件：config.yaml，路径：timeout.element_wait
    2026-06-26 22:50:03 - yaml_reader - INFO - 匹配到配置缓存，直接返回：D:\2026.3.4 python 练习 py. 存储\项目二-Playwright UI自动化框架\config\config.yaml
    2026-06-26 22:50:03 - yaml_reader - INFO - 匹配到配置缓存，直接返回：D:\2026.3.4 python 练习 py. 存储\项目二-Playwright UI自动化框架\config\config.yaml
    2026-06-26 22:50:03 - yaml_reader - INFO - 配置读取成功：timeout.element_wait = 10000
    2026-06-26 22:50:03 - yaml_reader - INFO - 配置读取成功：timeout.element_wait = 10000
    2026-06-26 22:50:03 - yaml_reader - INFO - 读取配置节点，文件：config.yaml，路径：timeout.popup_wait
    2026-06-26 22:50:03 - yaml_reader - INFO - 读取配置节点，文件：config.yaml，路径：timeout.popup_wait
    '''
    logger.propagate = True
    return logger
