import os
import importlib.util
import logging
from typing import List, Any

logger = logging.getLogger("capsule.plugins")

class PluginManager:
    """
    Dynamically loads Python plugins from the plugins/ directory and allows executing custom hooks.
    """
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), plugins_dir)
        self.plugins = []
        self._load_plugins()

    def _load_plugins(self):
        if not os.path.exists(self.plugins_dir):
            return
            
        for filename in os.listdir(self.plugins_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                plugin_name = filename[:-3]
                file_path = os.path.join(self.plugins_dir, filename)
                
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.plugins.append(module)
                    logger.info(f"Loaded plugin: {plugin_name}")
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_name}: {e}")

    async def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        Executes a specific hook (function) across all loaded plugins.
        """
        results = []
        for plugin in self.plugins:
            if hasattr(plugin, hook_name):
                func = getattr(plugin, hook_name)
                try:
                    import inspect
                    if inspect.iscoroutinefunction(func):
                        res = await func(*args, **kwargs)
                    else:
                        res = func(*args, **kwargs)
                    results.append(res)
                except Exception as e:
                    logger.error(f"Error executing hook {hook_name} in plugin {plugin.__name__}: {e}")
        return results

# Singleton instance
plugin_manager = PluginManager()
