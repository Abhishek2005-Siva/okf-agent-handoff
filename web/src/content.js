export default {
  name: 'OKF Agent Handoff',
  repo: 'https://github.com/Abhishek2005-Siva/okf-agent-handoff',
  eyebrow: 'Research prototype',
  tagline: 'Hand off knowledge between AI agents as a graph, not a pile of documents.',
  description:
    'Agent A turns research material into an Open Knowledge Format (OKF) bundle of concepts, metadata, provenance and typed relationships. Agent B reads that bundle and answers questions by walking the graph across multiple hops.',
  stack: ['Python', 'OpenAI', 'scikit-learn', 'Knowledge graph'],
  notice:
    'This is a showcase page. The agents and benchmarks run locally from the repository. The benchmark is a small curated set and not a general performance claim.',
  steps: [
    { title: 'Research material', text: 'Source notes and documents go in as plain research input.' },
    { title: 'Agent A builds the bundle', text: 'Extracts concepts, metadata, provenance and explicit relationships into an OKF knowledge bundle.' },
    { title: 'Agent B traverses', text: 'Loads the bundle and follows typed relationships across one to four hops.' },
    { title: 'Answer with a path', text: 'Responds to the question and reports the relationship path it used.' },
  ],
  stats: {
    title: 'Benchmark: OKF path retrieval',
    items: [
      { value: '0.51', label: 'Path recall, depth 0' },
      { value: '0.77', label: 'Path recall, depth 1' },
      { value: '0.90', label: 'Path recall, depth 2' },
      { value: '0.98', label: 'Path recall, depth 3' },
      { value: '1.00', label: 'Path recall, depth 4' },
    ],
    note: '12 curated questions, average path recall by traversal depth, from the repository README.',
  },
  features: [
    { title: 'Typed relationships', text: 'Edges such as implemented_using or runs_on are stored explicitly, so the ordered path between concepts is preserved.' },
    { title: 'Portable bundle', text: 'The knowledge lives in a self-contained bundle with provenance, so another agent can consume it without the original documents.' },
    { title: 'Multi-hop retrieval', text: 'Traverse up to four hops to recover paths that similarity search alone does not establish.' },
    { title: 'Honest baselines', text: 'Ships a single-document baseline and a RAG-style benchmark to compare against.' },
  ],
  startNote: 'Needs Python and an OpenAI API key in a .env file. See the README for the full setup.',
  quickstart: `git clone https://github.com/Abhishek2005-Siva/okf-agent-handoff
cd okf-agent-handoff
pip install -r requirements.txt

python agent_a.py            # build the OKF knowledge bundle
python agent_b.py            # ask questions via graph traversal
python benchmark_retrieval.py`,
}
