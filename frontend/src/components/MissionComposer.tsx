import { PlayCircleOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { Button, Input } from "antd";

const { TextArea } = Input;

const presets = [
  "分析本月华南区域收入下降的可能原因：结合经营数据、外部事件和内部资料给出行动建议。",
  "结合内部业务复盘和公开信息，整理一份经营诊断 Markdown 报告。",
  "查询数据库中的收入、客户数与利润率信息，分析区域经营机会，并输出研究结论。"
];

interface MissionComposerProps {
  query: string;
  isRunning: boolean;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
}

export function MissionComposer({
  query,
  isRunning,
  onQueryChange,
  onSubmit
}: MissionComposerProps) {
  return (
    <section className="console-panel composer-panel" aria-labelledby="composer-title">
      <div className="panel-heading">
        <div>
          <span className="panel-kicker">MISSION INPUT</span>
          <h2 id="composer-title">发起研搜任务</h2>
        </div>
        <ThunderboltOutlined className="panel-heading-icon" aria-hidden />
      </div>

      <TextArea
        aria-label="研搜任务"
        className="mission-textarea"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="输入要交给 DeepAgents 的任务，例如：查询机器人信息，并生成 Markdown 和 PDF 文件。"
        autoSize={{ minRows: 7, maxRows: 12 }}
        disabled={isRunning}
      />

      <div className="preset-grid" aria-label="任务模板">
        {presets.map((preset) => (
          <button
            className="preset-chip"
            type="button"
            key={preset}
            onClick={() => onQueryChange(preset)}
            disabled={isRunning}
          >
            {preset}
          </button>
        ))}
      </div>

      <Button
        block
        className="launch-button"
        disabled={isRunning}
        icon={<PlayCircleOutlined />}
        loading={isRunning}
        onClick={onSubmit}
        size="large"
        type="primary"
      >
        {isRunning ? "任务执行中" : "启动主智能体"}
      </Button>
    </section>
  );
}
