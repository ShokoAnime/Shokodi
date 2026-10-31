# -*- coding: utf-8 -*-
# Entry point for the plugin. The routes and handlers are in lib/handlers
from lib.utils.globalvars import plugin_router
from lib.error_handler import show_messages
# the plugin links to script routes (context menus, etc), so those have to be known here too
from lib.handlers import script
from lib.handlers.plugin import ShokodiPlugin

if __name__ == '__main__':
    plugin = ShokodiPlugin()
    plugin_router.instance = plugin
    plugin.main()
    show_messages()
