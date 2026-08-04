# Research Paths bilingual author-review checklist

Automated checks establish data integrity, linkage, and public isolation. They
do not approve the research narrative. Review pages from
`.review/research-paths.json` in `.preview-site/`; keep every item
`ready_for_review` until the relevant row below is complete.

## English review

- [x] The opening question is understandable without reading the paper list,
  while the later sections retain enough detail for a researcher.
- [x] Every parallel list contains concepts at the same level. Model
  representations, learning signals, evaluation criteria, and execution
  components are connected by an explicit causal or system relationship rather
  than placed side by side without explanation.
- [x] Reward-based visual post-training is not described as environment
  interaction, and coherent video generation is not described as an
  action-conditioned world model without stating the additional requirements.
- [x] The stated progression is historically and technically defensible. Each
  paper relationship explains relevance without inventing a direct inheritance.
- [x] The longer arc distinguishes labels from a fixed dataset, reward estimates
  on model-generated outputs, and verified state transitions collected through
  action in an environment. It acknowledges that scale is powerful and that
  reinforcement learning can still overfit a narrow reward or environment.
- [x] The first three arc cards broaden the modelled content; the fourth changes
  the optimization setting. Visual post-training is presented as a bridge toward,
  not an instance of, continual learning through environment interaction.
- [x] Tachikuma is framed as an earlier personal research motivation, not as a
  current publication, a completed autonomous system, or evidence of machine
  consciousness.
- [x] The digital-agent and physical-agent horizons are ambitious but concrete:
  memory, tools, feedback, verification, and environment design are named rather
  than replacing a research argument with an AGI slogan.
- [x] The visual-generation RL survey remains background context in the full
  publication catalog rather than a central Path contribution; ELP, VrR-VG,
  SEEG, Uni-Inter, and other primary papers carry the research narrative.
- [x] `we` refers to a collaborative paper contribution and does not imply
  sole or lead authorship; no personal anecdote or motivation is invented.
- [x] Older work is framed retrospectively. The page distinguishes what a
  paper established then, what still holds, and what later work changes.
- [x] The “boundaries” section keeps tasks, datasets, signals, and claims that
  cannot be combined honestly separate.
- [x] Every technical or evaluative claim is supported by the visible page and
  the linked publication record; proxy scores are not presented as capability.
- [x] The Research hub keeps Rain One Go and Food-Ingredient as earlier or
  adjacent work rather than forcing them into a main path.
- [x] The homepage summary and Research hub are approved together. Each Path
  may be approved separately, but its English and Chinese versions are a pair.
- [x] Canonical, language alternates, structured data, path roles, publication
  links, and approved Research Note links describe the same visible content.
- [x] Desktop 1440×900 and mobile 390×844 review shows no document, card,
  timeline, table, or navigation overflow.

## 中文审阅

- [x] 开头能够让未读论文的研究者快速理解核心问题，后续部分保留必要的技术细节。
- [x] 每组并列表述都处于同一概念层级；模型表示、学习信号、评价标准和执行组件之间必须写明因果或系统关系，不能直接堆在一起。
- [x] 奖励驱动的视觉后训练不被写成环境交互学习；连贯视频生成也不被直接等同于以行动为条件的世界模型，缺失条件需要明确说明。
- [x] 研究演进在时间与技术关系上成立；每篇论文都说明“为何相关”，不虚构直接继承关系。
- [x] 宏观脉络清楚区分“拟合一个极大的固定分布”和“通过交互产生新经验”；既承认规模化的作用，也说明强化学习仍可能过拟合狭窄的奖励或环境。
- [x] Tachikuma 被准确表述为早期个人研究动机，不被包装成当前论文、已经完成的自主系统或机器具有意识的证据。
- [x] 数字智能体与物理智能体的长期方向既有野心也足够具体，明确涉及记忆、工具、反馈、验证和环境设计，而不是只使用 AGI 口号。
- [x] 视觉生成强化学习综述只作为完整论文目录中的背景资料，不被突出为研究路径的核心贡献；主线由 ELP、VrR-VG、SEEG、Uni-Inter 和其他原创论文承担。
- [x] 合著工作使用协作式、中性的表述，不暗示个人独立或主导完成，也不添加未经证实的经历。
- [x] 较早工作采用回顾性框架，区分当时建立的结论、今天仍成立的部分和后来视角的变化。
- [x] “不能硬合的边界”准确区分任务、数据、训练信号和结论范围。
- [x] 可见页面中的技术与评估判断能够由论文记录支撑，不把代理分数直接等同于真实能力。
- [x] Research 总览把 Rain One Go 与 Food-Ingredient 保留为早期或相邻工作，不强行并入三条主线。
- [x] 首页研究简介与 Research 总览作为一组审批；单条路径可独立审批，但中英文必须同时通过。
- [x] 中英文信息等价，而非机械逐句直译；标题、角色、论文关系、边界与开放问题没有实质遗漏。
- [x] 在 1440×900 与 390×844 下检查导航、卡片、时间线和表格，没有页面级横向溢出。

## Approval queue / 审批队列

| Page pair | Status | Continuity | Contribution voice | Boundaries | Bilingual equivalence | Responsive | Publish approval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Homepage + Research hub / 首页与研究总览 | `published` | [x] | [x] | [x] | [x] | [x] | [x] |
| Video Generation and World Models / 视频生成与世界模型 | `published` | [x] | [x] | [x] | [x] | [x] | [x] |
| Trustworthy Visual Generation Post-Training / 可信视觉生成后训练 | `published` | [x] | [x] | [x] | [x] | [x] | [x] |
| Semantic Motion and Embodied Interaction / 语义动作与具身交互 | `published` | [x] | [x] | [x] | [x] | [x] | [x] |

After approval, move only the approved bilingual record into
`data/research-paths.json`, set `status` to `published`, add the real
`published_on` date, and remove it from `.review/research-paths.json`. Move the
hub only after the homepage and both hub languages are approved together. Run
the public build and full tests; verify that only approved URLs enter the
sitemap, feeds, machine-readable files, and IndexNow dry-run payload.
