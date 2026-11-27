# 达到步数上限也走普通返回路径

[BaseAgent.run](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/agent/base.py#L149-L154) · 前四行在状态上下文内，最后两行在上下文外：

```python
    if self.current_step >= self.max_steps:
        self.current_step = 0
        self.state = AgentState.IDLE
        results.append(f"Terminated: Reached max steps ({self.max_steps})")
await SANDBOX_CLIENT.cleanup()
return "\n".join(results) if results else "No steps executed"
```
