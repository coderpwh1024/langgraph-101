竖版 3:4 手绘教育信息图（sketch-notes 卡通手绘风格），与系列同一手绘风格、同一马卡龙配色。

【整体风格】手绘抖动线条，暖奶油纸张背景，马卡龙彩色圆角块，珊瑚红强调；填色留边；手写体中文。

【标题】顶部手写大标题：「人在回路 · 中断与恢复」。

【主体内容】flow 左右双栏对照流程图，中间放一个手绘「checkpointer 存档桶/磁盘」图标作为枢纽：

左栏「第一次 invoke」（淡蓝块，自上而下）：
用户：发邮件 → LLM 决定调用 send_mail → 工具内 interrupt() ⏸ 暂停 → 存档状态(thread_id) → 返回 __interrupt__ → 程序展示待审信息。

右栏「第二次 invoke」（薄荷绿块，自上而下）：
Command(resume=决策) → 从 checkpointer 恢复现场 → interrupt() 返回 resume 的值 → 三向分叉 approve / reject / edit → 发送 / 拒绝 / 改后发送 → 返回最终响应。

中央 checkpointer 存档桶用珊瑚红高亮，两栏之间画手绘弯箭头连接（暂停存档 → 恢复读取）。

底部手写关键点小字：「两次 invoke 用同一个 thread_id，断点精确恢复 ✅」。

【装饰】角落小星星、对勾。不要渲染颜色名称作为可见文字。
