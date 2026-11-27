# 截图跨过两层接口

[适配器测试](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/tests/tools/test_browser_use_mcp.py#L77-L97) · `tool` 使用返回文字和图片的假 MCP 会话：

```python
result = await tool.execute()

assert result.output == "done"
assert result.base64_image == "cG5n"
```

[消息测试](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/tests/tools/test_browser_use_mcp.py#L100-L116) · 另一个测试向 Agent 注册本地图像工具，再检查历史。两段不是同一次浏览器操作：

```python
await agent.act()

tool_message, image_message = agent.memory.messages
assert getattr(tool_message.role, "value", tool_message.role) == "tool"
assert tool_message.base64_image is None
assert getattr(image_message.role, "value", image_message.role) == "user"
assert image_message.base64_image == "cG5n"
```
