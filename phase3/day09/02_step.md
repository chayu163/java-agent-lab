# 一个步骤内部的分支

[ReActAgent.step](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/agent/react.py#L33-L38) · 注意 `return` 退出的是哪个方法：

```python
async def step(self) -> str:
    """Execute a single step: think and act."""
    should_act = await self.think()
    if not should_act:
        return "Thinking complete - no action needed"
    return await self.act()
```
