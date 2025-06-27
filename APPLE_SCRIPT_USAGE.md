# Apple Script Tools 使用说明

本项目包含了从 tiny-agent 移植过来的 Apple Script 工具，用于在 MacOS 上进行系统集成。

## 已修复的问题

1. 修复了所有文件中的导入路径错误：
   - 从 `src.tiny_agent.run_apple_script` 改为 `minion_agent.tools.run_apple_script`
   - 从 `src.tiny_agent.models` 改为本地枚举类

2. 添加了缺失的依赖：
   - `beautifulsoup4>=4.9.0` (用于 notes.py)
   - `TransportationOptions` 枚举类 (用于 maps.py)

## 可用工具

### 1. 日历工具 (Calendar)
- `create_calendar_event()` - 创建日历事件

### 2. 提醒工具 (Reminders)  
- `create_reminder()` - 创建提醒事项

### 3. 笔记工具 (Notes)
- `create_note()` - 创建笔记
- `open_note()` - 打开现有笔记
- `append_to_note()` - 向笔记添加内容

### 4. 邮件工具 (Mail)
- `compose_email()` - 撰写邮件
- `reply_to_email()` - 回复邮件
- `forward_email()` - 转发邮件
- `get_email_content()` - 获取邮件内容

### 5. 联系人工具 (Contacts)
- `get_contact_phone()` - 获取联系人电话号码
- `get_contact_email()` - 获取联系人邮箱地址

### 6. 短信工具 (SMS)
- `send_sms()` - 发送短信

### 7. 地图工具 (Maps)
- `open_location_maps()` - 在地图中打开位置
- `get_directions_maps()` - 获取路线指引

### 8. Spotlight 搜索工具
- `spotlight_search_open()` - 使用 Spotlight 搜索并打开应用或文件

### 9. Zoom 工具
- `get_meeting_link()` - 创建 Zoom 会议链接

## 使用示例

### 基本用法

```python
from minion_agent.tools.apple_script_tools import (
    create_reminder,
    create_note,
    compose_email
)

# 创建提醒
result = create_reminder(
    name="开会提醒",
    due_date="2024-01-15 15:00:00",
    notes="下午3点团队会议"
)

# 创建笔记
result = create_note(
    name="会议记录",
    content="今天的会议要点：..."
)

# 撰写邮件
result = compose_email(
    recipients=["example@email.com"],
    subject="测试邮件",
    content="这是一封测试邮件"
)
```

### 在 Minion Agent 中使用

```python
from minion_agent import MinionAgent, AgentConfig, AgentFramework
from minion_agent.tools.apple_script_tools import *

agent_config = AgentConfig(
    tools=[
        create_calendar_event,
        create_reminder,
        create_note,
        compose_email,
        # ... 其他工具
    ]
)

agent = await MinionAgent.create_async(AgentFramework.SMOLAGENTS, agent_config)
result = await agent.run_async("帮我创建一个明天下午3点的会议提醒")
```

## 注意事项

1. 这些工具只能在 MacOS 系统上使用
2. 需要相应的应用程序已安装并具有适当的权限
3. 首次使用时可能需要授予 AppleScript 权限
4. 时间格式使用 "YYYY-MM-DD HH:MM:SS" 格式

## 测试

运行 `test_apple_script.py` 来测试基本功能：

```bash
python test_apple_script.py
```

运行完整的 agent 示例：

```bash
python example_apple_script.py
``` 