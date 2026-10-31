# -*- coding: utf-8 -*-
# Entry point for the script. The routes and handlers are in lib/handlers
from lib import debug
from lib.utils.globalvars import script_router
from lib.error_handler import show_messages
# models build plugin urls too, so those routes have to be known here
from lib.handlers import plugin
from lib.handlers.script import ShokodiScript

if __name__ == '__main__':
    debug.debug_init()
    script = ShokodiScript()
    script_router.instance = script
    script.main()
    show_messages()
