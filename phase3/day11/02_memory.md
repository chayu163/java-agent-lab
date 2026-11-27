# 消息保留窗口

[Memory](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/schema.py#L159-L168) · 单条追加路径。切片单位是消息，不是订单、步骤或 token：

```python
class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)

    def add_message(self, message: Message) -> None:
        """Add a message to memory"""
        self.messages.append(message)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]
```
