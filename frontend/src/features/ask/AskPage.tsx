/** 问数会话页（核心 UX）：输入问题 → SSE 流式呈现意图/子目标/答案。 */
import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Input,
  Row,
  Space,
  Spin,
  Steps,
  Tag,
  Typography,
} from "antd";
import { SendOutlined } from "@ant-design/icons";
import { useMutation } from "@tanstack/react-query";
import { submitQuestion } from "../../api/questions";
import { useQuestionStream } from "../../hooks/useQuestionStream";
import { useSessionStore } from "../../stores/session";
import { AnswerPanel } from "../../components/AnswerPanel";
import { AnswerChart } from "../../components/charts/AnswerChart";
import type { QuestionCreate } from "../../api/schemas";

const { Text } = Typography;

const EXAMPLES = [
  "上月GMV是多少",
  "近30天各品类的退款率",
  "上月退款率环比",
  "为什么退款率环比上升了，是哪个大区导致的",
  "本月GMV、订单数和退款率",
];

export function AskPage() {
  const [question, setQuestion] = useState("");
  const roles = useSessionStore((s) => s.roles);
  const [questionId, setQuestionId] = useState<string | null>(null);
  const stream = useQuestionStream(questionId);

  const submit = useMutation({
    mutationFn: (q: string) => {
      const body: QuestionCreate = { question: q, roles };
      return submitQuestion(body);
    },
    onSuccess: (out) => {
      setQuestionId(out.question_id);
    },
  });

  const onAsk = (q?: string) => {
    const text = (q ?? question).trim();
    if (!text || submit.isPending) return;
    setQuestion(text);
    setQuestionId(null);
    submit.mutate(text);
  };

  return (
    <Row gutter={16}>
      <Col xs={24} lg={16}>
        <Card title="问数分析" style={{ marginBottom: 16 }}>
          <Input.TextArea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="用自然语言问数，例如：上月GMV是多少"
            autoSize={{ minRows: 2, maxRows: 5 }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                onAsk();
              }
            }}
          />
          <div style={{ marginTop: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Space wrap size={[8, 8]}>
              {EXAMPLES.map((ex) => (
                <Tag
                  key={ex}
                  style={{ cursor: "pointer" }}
                  onClick={() => {
                    setQuestion(ex);
                    onAsk(ex);
                  }}
                >
                  {ex}
                </Tag>
              ))}
            </Space>
            <Button
              type="primary"
              icon={<SendOutlined />}
              loading={submit.isPending}
              onClick={() => onAsk()}
            >
              提问
            </Button>
          </div>
        </Card>

        {stream.status === "running" && (
          <Card title="正在分析…" style={{ marginBottom: 16 }}>
            <RunProgress level={stream.level} subgoals={stream.subgoals} />
          </Card>
        )}

        {stream.blocked && (
          <Alert
            type="warning"
            showIcon
            message="请求已被安全护栏拦截"
            description={stream.blocked.detail}
            style={{ marginBottom: 16 }}
          />
        )}

        {stream.clarification && !stream.answer && stream.status !== "running" && (
          <Alert
            type="warning"
            showIcon
            message="需要补充信息"
            description={stream.clarification}
            style={{ marginBottom: 16 }}
          />
        )}

        {stream.error && (
          <Alert type="error" showIcon message="分析失败" description={stream.error} style={{ marginBottom: 16 }} />
        )}

        {stream.answer ? (
          <Card title={`结果 · ${stream.answer.level ?? ""}`}>
            <AnswerPanel answer={stream.answer} />
            <AnswerChart chart={stream.answer.chart} />
          </Card>
        ) : (
          stream.status === "done" && (
            <Card>
              <Empty description="已完成，但未产生答案" />
            </Card>
          )
        )}
      </Col>

      <Col xs={24} lg={8}>
        <Card title="分析过程" size="small">
          {stream.status === "idle" ? (
            <Empty description="提交问题后，这里会展示意图识别与子目标执行过程" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <RunProgress level={stream.level} subgoals={stream.subgoals} verbose />
          )}
        </Card>
      </Col>
    </Row>
  );
}

function RunProgress({
  level,
  subgoals,
  verbose = false,
}: {
  level: string | null;
  subgoals: Array<{ id: string; name: string; kind: string; status: string }>;
  verbose?: boolean;
}) {
  if (verbose) {
    return (
      <Steps
        direction="vertical"
        size="small"
        current={subgoals.filter((s) => s.status === "ok").length}
        items={[
          { title: "意图识别", description: level ? <Tag color="geekblue">{level}</Tag> : <Spin size="small" />, status: level ? "finish" : "process" },
          ...subgoals.map((s) => ({
            title: `${s.name}（${s.kind}）`,
            description: s.status,
            status: s.status === "ok" ? ("finish" as const) : s.status === "failed" ? ("error" as const) : ("process" as const),
          })),
        ]}
      />
    );
  }
  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <div className="dq-subgoal-step">
        <Text type="secondary">意图等级</Text>
        {level ? <Tag color="geekblue">{level}</Tag> : <Spin size="small" />}
      </div>
      {subgoals.map((s) => (
        <div key={s.id} className="dq-subgoal-step">
          <Text type="secondary">{s.name}</Text>
          {s.status === "ok" ? (
            <Tag color="green">完成</Tag>
          ) : s.status === "failed" ? (
            <Tag color="red">失败</Tag>
          ) : (
            <Spin size="small" />
          )}
        </div>
      ))}
    </Space>
  );
}
