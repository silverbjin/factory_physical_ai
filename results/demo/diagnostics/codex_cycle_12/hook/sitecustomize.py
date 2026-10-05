import sys, asyncio, os
if "launch" in sys.argv and os.path.basename(sys.argv[0]) == "ros2":
    for name in ("subprocess_exec", "subprocess_shell"):
        original=getattr(asyncio.BaseEventLoop,name)
        def wrap(fn):
            async def spawn(self,*args,**kwargs):
                kwargs["close_fds"]=True
                return await fn(self,*args,**kwargs)
            return spawn
        setattr(asyncio.BaseEventLoop,name,wrap(original))
    print("DEMO_DIAGNOSTIC: launch children close_fds=True",flush=True)
