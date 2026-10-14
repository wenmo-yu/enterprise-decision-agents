import { CloudServerOutlined, DatabaseOutlined, FileSearchOutlined, SafetyCertificateOutlined } from "@ant-design/icons";

const agents = [
  {
    icon: <CloudServerOutlined aria-hidden />,
    name: "外部情报专家",
    detail: "行业动态、竞争信息、政策规则与外部事件"
  },
  {
    icon: <DatabaseOutlined aria-hidden />,
    name: "经营问数专家",
    detail: "调用独立问数服务，取得已校验的经营事实"
  },
  {
    icon: <FileSearchOutlined aria-hidden />,
    name: "内部知识专家",
    detail: "制度文档、业务复盘、资料与私有知识库"
  },
  {
    icon: <SafetyCertificateOutlined aria-hidden />,
    name: "证据审查专家",
    detail: "检查关键结论的来源、时间范围与待验证项"
  }
];

export function AgentTopology() {
  return (
    <section className="console-panel topology-panel" aria-labelledby="topology-title">
      <div className="panel-heading">
        <div>
          <span className="panel-kicker">ROUTING MAP</span>
          <h2 id="topology-title">多智能体路由</h2>
        </div>
      </div>
      <div className="agent-hub">
        <div className="main-agent-node">
          <span>MAIN</span>
          <strong>调度主智能体</strong>
        </div>
        <div className="agent-links" aria-hidden>
          <span />
          <span />
          <span />
          <span />
        </div>
        <div className="agent-node-list">
          {agents.map((agent) => (
            <div className="agent-node" key={agent.name}>
              <div className="agent-node-icon">{agent.icon}</div>
              <div>
                <strong>{agent.name}</strong>
                <p>{agent.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
