# 两种超时等待的不是同一个对象

[PythonExecute.execute](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/tool/python_execute.py#L64-L75) · 宿主机子进程：

```python
proc.start()
proc.join(timeout)

# timeout process
if proc.is_alive():
    proc.terminate()
    proc.join(1)
    return {
        "observation": f"Execution timeout after {timeout} seconds",
        "success": False,
    }
return dict(result)
```

[AsyncDockerizedTerminal](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/app/sandbox/core/terminal.py#L206-L211) · 仅摘取等待读取容器输出的分支：

```python
if timeout:
    result = await asyncio.wait_for(read_output(), timeout)
else:
    result = await read_output()

return result.strip()
```
