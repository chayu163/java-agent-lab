# 用样例会话替换外部平台

[boss-agent-cli · build_automation_adapter](https://github.com/can4hou6joeng4/boss-agent-cli/blob/56db2a7/src/boss_agent_cli/automation/adapters.py#L40-L56) · 这是对照项目的工厂分支，不是 OpenManus 的工具：

```python
if sample_conversations is not None:
    from boss_agent_cli.automation.mock_adapter import (
        MockRecruiterAutomationPlatform,
    )

    return MockRecruiterAutomationPlatform(platform_name, sample_conversations)
```

条件是 `is not None`，因此空列表也会选择样例适配器。「有意提供零条会话」不同于「没有提供样例」。
