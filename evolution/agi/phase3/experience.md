# 经验学习机制

## 经验分类
1. **任务经验** - 完成特定任务的方法
2. **错误经验** - 犯过的错误和教训
3. **用户经验** - 用户的偏好和习惯
4. **环境经验** - 环境特性和限制

## 经验记录格式
```json
{
  "id": "exp-{timestamp}",
  "type": "success|failure|observation",
  "context": {
    "task": "任务描述",
    "environment": "环境信息",
    "user_state": "用户状态"
  },
  "action": "采取的行动",
  "result": "结果",
  "lesson": "学到的教训",
  "confidence": 0.0-1.0,
  "reuse_count": 0,
  "last_used": "timestamp"
}
```

## 学习策略
1. **重复学习** - 多次遇到相同情况强化记忆
2. **类比学习** - 从相似情况推导
3. **试错学习** - 尝试不同方法找到最优
4. **观察学习** - 从用户行为学习