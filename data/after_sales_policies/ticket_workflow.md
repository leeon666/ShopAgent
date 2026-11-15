# 售后工单状态机

版本：2026.1

售后工单允许的标准状态：

- `pending`：刚创建，尚未开始研判。
- `agent_review`：Agent 已接单并开始核查。
- `waiting_customer`：等待用户补充照片、视频或其他信息。
- `waiting_approval`：已生成高风险执行提案，等待管理员审批。
- `approved`：管理员批准提案，尚未完成最终执行。
- `rejected`：管理员拒绝提案。
- `resolved`：售后动作已经完成并有执行记录。
- `cancelled`：用户或管理员取消。

合法主干路径：

`pending -> agent_review -> waiting_customer -> agent_review -> waiting_approval -> approved -> resolved`

禁止从 `pending` 直接跳到 `approved` 或 `resolved`。高风险动作只能由确定性业务服务执行，模型只能创建提案。

