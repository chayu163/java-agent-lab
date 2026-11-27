# 谁接到 `run`，谁决定是否再做一步？

[ToolCallAgent.run](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/agent/toolcall.py#L253-L258) · 首先进入的方法：

```python
async def run(self, request: Optional[str] = None) -> str:
    """Run the agent with cleanup when done."""
    try:
        return await super().run(request)
    finally:
        await self.cleanup()
```

[BaseAgent.run](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/agent/base.py#L131-L141) · 委托目标中的循环入口：

```python
if request:
    self.update_memory("user", request)

results: List[str] = []
async with self.state_context(AgentState.RUNNING):
    while self.current_step < self.max_steps and self.state != AgentState.FINISHED:
        self.current_step += 1
        logger.info(f"Executing step {self.current_step}/{self.max_steps}")
        step_result = await self.step()
```
