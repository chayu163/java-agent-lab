# 按调用 ID 回填结果

[ToolCallAgent.act：执行](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/agent/toolcall.py#L142-L146)。`await` 在循环体内：

```python
for command in self.tool_calls:
    # Reset base64_image for each tool call
    self._current_base64_image = None

    result = await self.execute_tool(command)
```

[同一循环：回填](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/agent/toolcall.py#L155-L161)。工具名可以重复，调用 ID 来自当前 `command`：

```python
tool_msg = Message.tool_message(
    content=result,
    tool_call_id=command.id,
    name=command.function.name,
)
self.memory.add_message(tool_msg)
```
