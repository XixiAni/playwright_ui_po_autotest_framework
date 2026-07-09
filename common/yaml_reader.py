import yaml
import os
import re
from typing import Any
from common.logger import get_logger
logger = get_logger("yaml_reader")

class YamlReader:
    """YAML配置文件通用读取工具

    支持文件缓存，避免重复IO；支持点式语法读取嵌套配置

    扩展：支持多环境配置读取与全局环境切换
    扩展：支持${VAR_NAME}格式环境变量占位符自动替换
    """
    _cache: dict[str, dict] = {}
    _current_env: str = "dev"  # 全局运行环境，默认dev

    @classmethod
    def set_current_env(cls, env_name: str) -> None:
        """设置全局运行环境，影响后续 get_env 读取的配置文件

        :param env_name: 环境名，如 dev/test/prod
        """
        cls._current_env = env_name
        logger.info(f"全局运行环境已设置为：{env_name}")

    @classmethod
    def _replace_env_var(cls, value: Any) -> Any:
        """替换字符串中的 ${VAR_NAME} 格式环境变量占位符

        兼容YAML文件内所有数据类型

        非字符串类型直接返回；环境变量不存在则保留原占位符

        :param value: 点式读取的值，可能是字符串、数字、布尔、列表、字典等

        :return: 替换字符串，其他类型返回原值
        """
        if not isinstance(value, str):
            return value
        pattern = r"\$\{([\w-]+)\}"
        def _replace(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0)) 
        return re.sub(pattern, _replace, value) 

    @classmethod
    def _get_config_path(cls, filename: str) -> str:
        """拼接配置文件绝对路径，规避执行路径不同导致的文件找不到问题

        :param filename: 配置文件名，如 config.yaml
        :return: 配置文件完整绝对路径
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, "config", filename)
        logger.debug(f"拼接配置文件完整路径：{full_path}")
        return full_path

    @classmethod
    def _get_env_file_path(cls, env_name: str) -> str:
        """拼接环境配置文件绝对路径

        :param env_name: 环境名
        :return: 环境yaml文件完整绝对路径
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, "config", "env", f"{env_name}.yaml")
        logger.debug(f"拼接环境配置文件路径：{full_path}")
        return full_path

    @classmethod
    def _get_by_dot_path(cls, data: dict, key_path: str, error_prefix: str = "") -> Any:
        """私有通用方法：按点式路径从字典中取值

        :param data: 数据源字典
        :param key_path: 点分隔的配置路径
        :param error_prefix: 异常信息前缀，用于区分不同类型文件的报错
        :return: 配置对应的值
        """
        keys = key_path.split(".")
        current_node = data
        for key in keys:
            if key not in current_node:
                err_msg = f"{error_prefix}完整路径 [{key_path}]，当前层级缺失字段 [{key}]"
                logger.error(err_msg)
                raise KeyError(err_msg)
            current_node = current_node[key]
        logger.info(f"配置读取成功：{key_path} = {current_node}")
        # 替换环境变量占位符
        current_node = cls._replace_env_var(current_node)
        return current_node

    @classmethod
    def read_file(cls, filename: str) -> dict:
        """读取完整YAML文件，支持缓存

        :param filename: 配置文件名
        :return: 配置文件对应的字典
        """
        file_path = cls._get_config_path(filename)
        if file_path in cls._cache:
            logger.info(f"匹配到配置缓存，直接返回：{file_path}")
            return cls._cache[file_path]
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            cls._cache[file_path] = data
            logger.info(f"配置文件 {filename} 读取完成，存入缓存")
            return data
        except FileNotFoundError as e:
            logger.error(f"配置文件不存在：{file_path}，异常：{str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"读取YAML文件异常：{file_path}，异常：{str(e)}", exc_info=True)
            raise

    @classmethod
    def read_env_config(cls, env_name: str = None) -> dict:
        """读取指定环境的完整配置，支持缓存

        :param env_name: 环境名，不传则使用当前全局环境
        :return: 环境配置字典
        """
        use_env = env_name if env_name else cls._current_env
        file_path = cls._get_env_file_path(use_env)
        if file_path in cls._cache:
            logger.info(f"匹配到环境配置缓存，直接返回：{file_path}")
            return cls._cache[file_path]
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            cls._cache[file_path] = data
            logger.info(f"环境配置文件 {use_env}.yaml 读取完成，存入缓存")
            return data
        except FileNotFoundError as e:
            logger.error(f"环境配置文件不存在：{file_path}，异常：{str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"读取环境配置文件异常：{file_path}，异常：{str(e)}", exc_info=True)
            raise

    @classmethod
    def get_page_locators(cls, page_module: str) -> dict:
        """获取指定页面模块的完整定位器配置（公共定位器 + 环境覆盖）

        环境配置优先级高于公共配置，同名字段自动覆盖
        
        :param page_module: 页面模块名，如 search_page
        :return: 合并后的完整定位器字典
        """
        # 1. 读取公共基准定位器
        common_locators = cls.get("locators.yaml", page_module)
        # 2. 尝试读取环境差异化定位器，无则为空字典
        try:
            env_locators = cls.get_env(page_module)
        except KeyError:
            env_locators = {}
         # 3. 合并：环境配置覆盖公共配置
        final_locators = {**common_locators, **env_locators}
        if env_locators:
            logger.info(f"页面[{page_module}]定位器合并完成，环境覆盖{len(env_locators)}个字段")
        else:
            logger.info(f"页面[{page_module}]无环境特殊定位器，复用公共配置")
        return final_locators

    @classmethod
    def get(cls, filename: str, key_path: str) -> Any:
        """按点式路径读取嵌套配置，例如 get("config.yaml", "browser.headless")
        
        :param filename: 配置文件名
        :param key_path: 点分隔的配置路径
        :return: 配置对应的值
        """
        logger.info(f"读取配置节点，文件：{filename}，路径：{key_path}")
        data = cls.read_file(filename)
        return cls._get_by_dot_path(data, key_path, error_prefix="配置读取失败：")

    @classmethod
    def get_env(cls, key_path: str, env_name: str = None) -> Any:
        """按点式路径读取当前环境配置，例如 get_env("baidu_page.url")

        :param key_path: 点分隔的配置路径
        :param env_name: 可选，指定环境，不传则使用全局环境
        :return: 配置对应的值
         """
        use_env = env_name if env_name else cls._current_env
        logger.info(f"读取环境配置节点，环境：{use_env}，路径：{key_path}")
        data = cls.read_env_config(use_env)
        return cls._get_by_dot_path(data, key_path, error_prefix=f"环境配置读取失败：环境[{use_env}]，")
    
    @classmethod
    def _get_test_data_path(cls, filename: str) -> str:
        """拼接测试数据文件绝对路径

        :param filename: 测试数据文件名，如 search_data.yaml
        :return: 数据文件完整绝对路径
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, "data", filename)
        logger.debug(f"拼接测试数据文件完整路径：{full_path}")
        return full_path

    @classmethod
    def get_test_data(cls, filename: str, key_path: str = None) -> Any:
        """读取测试数据文件，支持点式路径取值，复用全局缓存

        :param filename: 测试数据文件名，如 search_data.yaml
        :param key_path: 点分隔的配置路径，不传则返回完整文件内容
        :return: 测试数据对应的值
        """
        file_path = cls._get_test_data_path(filename)
        logger.info(f"读取测试数据，文件：{filename}，路径：{key_path if key_path else '使用全量数据'}")

        # 复用缓存逻辑：已读取过直接返回
        if file_path in cls._cache:
            logger.info(f"匹配到测试数据缓存，直接返回：{file_path}")
            data = cls._cache[file_path]
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                cls._cache[file_path] = data
                logger.info(f"测试数据文件 {filename} 读取完成，存入缓存")
            except FileNotFoundError as e:
                logger.error(f"测试数据文件不存在：{file_path}，异常：{str(e)}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"读取测试数据文件异常：{file_path}，异常：{str(e)}", exc_info=True)
                raise

        # 未指定路径则返回全量数据
        if not key_path:
            return data
        # 调用通用点式取值方法
        return cls._get_by_dot_path(data, key_path, error_prefix="测试数据读取失败：")
