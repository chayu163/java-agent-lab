# 按工具名找到对象

[ToolCollection](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/tool/tool_collection.py#L15-L23) · 构造索引：

```python
def __init__(self, *tools: BaseTool):
    self.tools = tools
    self.tool_map = {tool.name: tool for tool in tools}
```

同一类中，模型看到的是描述：

```python
def to_params(self) -> List[Dict[str, Any]]:
    return [tool.to_param() for tool in self.tools]
```

[ToolCollection.execute](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/tool/tool_collection.py#L25-L35) · 应用才调用对象：

```python
tool = self.tool_map.get(name)
if not tool:
    return ToolFailure(error=f"Tool {name} is invalid")
try:
    result = await tool(**tool_input)
    return result
except ToolError as e:
    return ToolFailure(error=e.message)
```
