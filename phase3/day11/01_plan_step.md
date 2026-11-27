# 派发计划步骤与标记完成是两次操作

[PlanningFlow.execute](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/flow/planning.py#L111-L125) · 外层循环的一段：

```python
self.current_step_index, step_info = await self._get_current_step_info()

# Exit if no more steps or plan completed
if self.current_step_index is None:
    result += await self._finalize_plan()
    break

# Execute current step with appropriate agent
step_type = step_info.get("type") if step_info else None
executor = self.get_executor(step_type)
step_result = await self._execute_step(executor, step_info)
result += step_result + "\n"
```

[PlanningFlow._execute_step](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/flow/planning.py#L294-L304) · 下面的 `executor.run` 才进入 Agent 的内层循环：

```python
try:
    step_result = await executor.run(step_prompt)

    # Mark the step as completed after successful execution
    await self._mark_step_completed()

    return step_result
except Exception as e:
    logger.error(f"Error executing step {self.current_step_index}: {e}")
    return f"Error executing step {self.current_step_index}: {str(e)}"
```
