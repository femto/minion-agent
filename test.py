from datetime import timedelta, datetime

from minion_agent.tools.apple_script_tools import create_reminder

now = datetime.now()
tomorrow = now + timedelta(days=1)
reminder_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
reminder_str = reminder_time.strftime("%Y-%m-%d %H:%M:%S")
reminder_result = create_reminder(
  name="开会提醒",
  due_date=reminder_str,
  notes="明天下午3点会议",
  list_name="",   # 默认列表
  priority=5,     # 普通优先级
  all_day=False
)
print(f"提醒创建结果: {reminder_result}")